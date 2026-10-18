"""Verify a self-contained CODE-only snapshot. No scientific or numeric imports."""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess


def verify(code, expected):
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
    worker = next(row for row in rows if row['path'] == 'tools/s04_e011_pc16/worker.py')
    assert worker['blob'] == manifest['locked_science_worker_blob']
    return dict(status='code_materialization_verified', source=expected,
                development_source=manifest['development_source'], root_commit=True,
                files=len(expected_paths), selected_code_bytes=sum(r['bytes'] for r in rows),
                full_fsck=True, sparse=False, partial_clone=False, external_object_store=False,
                worker_blob=worker['blob'], scientific_arrays_accessed=0, numeric_imports_or_calls=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.code, args.expected_source), indent=2))
