"""Verify a self-contained CODE-only snapshot. No scientific or numeric imports."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def check_local_imports(code, manifest):
    """Traverse AST only, including imports inside functions; execute no module.

    The canonical catalog includes omitted modules, so missing local imports
    cannot silently become third-party imports. Explicit entrypoints cover
    subprocess-launched scripts. External package availability is not tested.
    """
    catalog = manifest['local_module_catalog']
    selected = {row['path'] for row in manifest['files']}
    pending = list(manifest['import_entrypoints'])
    seen, external = set(), set()
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        assert path in selected, 'missing local module: '+path
        seen.add(path)
        tree = ast.parse((code/path).read_text(), filename=path)
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 0, 'unhandled reachable relative import: '+path
                names = [node.module] if node.module else []
            for name in names:
                module = name.split('.')[0]
                if module in catalog:
                    candidates = catalog[module]
                    assert len(candidates) == 1, 'ambiguous local import: '+module
                    dependency = candidates[0]
                    assert dependency in selected, 'missing local module: '+dependency+' imported by '+path
                    pending.append(dependency)
                else:
                    external.add(module)
    return dict(reachable_local_paths=sorted(seen), external_modules=sorted(external),
                method='AST only; no numeric imports or calls')


def verify(code, expected):
    if sys.flags.optimize:
        raise RuntimeError('assertion checks require Python optimization disabled')
    code = code.resolve()
    env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')

    def git(*args, optional=False):
        result = subprocess.run(['git', '-C', str(code), *args], env=env,
                                text=True, capture_output=True, timeout=15)
        if result.returncode and not (optional and result.returncode == 1):
            raise RuntimeError('Git code-package check failed: '+repr(args)+result.stderr)
        return result.stdout.strip()

    assert len(expected) == 40 and git('rev-parse', 'HEAD') == expected
    assert not git('status', '--porcelain', '--untracked-files=all')
    assert git('rev-list', '--parents', '-n', '1', 'HEAD').split() == [expected], 'snapshot must be a root commit'
    assert git('config', '--get', 'core.sparseCheckout', optional=True) not in ('true', '1')
    assert not git('config', '--get', 'extensions.partialClone', optional=True)
    assert not git('config', '--get-regexp', r'remote\..*\.promisor', optional=True)
    common = Path(git('rev-parse', '--git-common-dir'))
    common = common if common.is_absolute() else code / common
    assert not (common / 'objects/info/alternates').exists(), 'no borrowed object store'
    git('fsck', '--full', '--strict')
    manifest_path = code / 'SOURCE_PROVENANCE.json'
    assert not manifest_path.is_symlink()
    manifest = json.loads(manifest_path.read_text())
    rows = manifest['files']
    expected_paths = {row['path'] for row in rows} | {'SOURCE_PROVENANCE.json'}
    assert len(expected_paths) == len(rows)+1
    assert set(git('ls-files').splitlines()) == expected_paths
    actual_paths = set()
    for base, dirs, files in os.walk(code):
        if Path(base) == code and '.git' in dirs:
            dirs.remove('.git')
        for directory in dirs:
            assert not (Path(base)/directory).is_symlink()
        for name in files:
            path = Path(base)/name
            assert not path.is_symlink()
            actual_paths.add(path.relative_to(code).as_posix())
    assert actual_paths == expected_paths, 'no extra materialized file, even if ignored'
    for row in rows:
        path = code / row['path']
        assert path.suffix in ('.py', '.json', '.md') or row['path'] == '.gitignore'
        raw = path.read_bytes()  # Only the enumerated CODE/text files, never science paths.
        assert len(raw) == row['bytes']
        assert bool(path.stat().st_mode & 0o111) == (row['mode'] == '100755')
        blob = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        assert blob == row['blob'], row['path']
        if path.suffix == '.py':
            ast.parse(raw.decode('utf-8'), filename=row['path'])
    worker = next(row for row in rows if row['path'] == 'tools/s04_e011_fn776/worker.py')
    assert worker['blob'] == manifest['locked_science_worker_blob']
    audit = manifest['runtime_cap_audit']
    assert audit['modified_worker_blob'] == worker['blob']
    assert audit['baseline_worker_blob'] == 'adb8c050b5330026cc120f47f14244ab040af028'
    assert audit['allowed_delta'].startswith('remove self wall/RSS/CUDA/output caps only')
    row_blobs = {row['path']: row['blob'] for row in rows}
    for path, blob in manifest['locked_solver_blobs'].items():
        assert row_blobs[path] == blob, 'reviewed solver blob mismatch: '+path
    for path, blob in manifest['frozen_mechanics_blobs'].items():
        assert row_blobs[path] == blob, 'frozen mechanics blob mismatch: '+path
    imports = check_local_imports(code, manifest)
    return dict(status='code_materialization_verified', source=expected,
                development_source=manifest['development_source'], root_commit=True,
                files=len(expected_paths), selected_code_bytes=sum(r['bytes'] for r in rows),
                full_fsck=True, sparse=False, partial_clone=False, external_object_store=False,
                worker_blob=worker['blob'], local_import_closure=imports,
                scientific_arrays_accessed=0, numeric_imports_or_calls=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.code, args.expected_source), indent=2))
