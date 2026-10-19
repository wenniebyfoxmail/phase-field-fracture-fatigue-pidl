"""Mac-only code packaging/materialization check; never import scientific code.

The exported root commit has no parent/base prerequisites and contains only
explicit Python/text paths from one committed development source. This repairs
deployment packaging; it does not execute or change the scientific method.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def build(source, out):
    root = Path(__file__).resolve().parents[2]
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')

    def cmd(args, *, input=None, index=False):
        options = dict(env, GIT_INDEX_FILE=str(out/'snapshot.index')) if index else env
        return subprocess.check_output(args, input=input, text=True, cwd=root,
                                       env=options, timeout=30).strip()

    assert cmd(['git', 'hash-object', str(Path(__file__).resolve())]) == cmd(['git', 'rev-parse', source+':tools/s04_e011_fn776/build_code_package.py'])
    assert len(source) == 40
    assert cmd(['git', 'rev-parse', source+'^{commit}']) == source
    exact = {'.gitignore', 'AGENTS.md', 'SENS_tensile/run_native_q4_one_step_matrix.py',
             'SENS_tensile/field_computation.py',
             'tools/s04_e011_fn776/worker.py', 'tools/s04_e011_fn776/square_root.py',
             'tools/s04_e011_fn776/static_checks.py', 'tools/s04_e011_fn776/guard.py',
             'tools/s04_e011_fn776/build_code_package.py', 'tools/s04_e011_fn776/verify_code_package.py',
             'docs/research/S04/S04-E011/uv_head_c1_solver_d3_20261019/inputs_fn776.json',
             'docs/research/S04/S04-E011/uv_head_c1_solver_d3_20261019/protocol_fn776.md',
             'docs/research/S04/S04-E011/uv_head_c1_solver_d3_20261019/mechanics_ast.json',
             'docs/research/S04/S04-E011/uv_head_c1_solver_d3_20261019/deployment_fn776.md'}
    rows = []
    local_modules = {}
    for line in cmd(['git', 'ls-tree', '-r', source]).splitlines():
        left, path = line.split('\t')
        mode, kind, blob = left.split()
        if path.endswith('.py') and Path(path).parent.as_posix() in (
                'source', 'SENS_tensile', 'tools/s04_e011_fn776'):
            local_modules.setdefault(Path(path).stem, []).append(path)
        if path not in exact and not (path.startswith('source/') and path.endswith('.py')):
            continue
        assert kind == 'blob' and mode in ('100644', '100755')
        assert '\n' not in path and '\t' not in path
        size = int(cmd(['git', 'cat-file', '-s', blob]))
        rows.append(dict(path=path, mode=mode, blob=blob, bytes=size))
    assert exact <= {row['path'] for row in rows}
    worker_blob = cmd(['git', 'rev-parse', source+':tools/s04_e011_fn776/worker.py'])
    mechanics = {}
    for row in rows:
        if row['path'].startswith(('source/', 'SENS_tensile/')):
            original_blob = cmd(['git', 'rev-parse', '3dfef418828e53632b3a5c90521ab8989dbf9673:'+row['path']])
            assert row['blob'] == original_blob, 'frozen mechanics changed: '+row['path']
            mechanics[row['path']] = original_blob
    manifest = dict(development_source=source, locked_science_worker_blob=worker_blob, frozen_mechanics_blobs=mechanics,
                    local_module_catalog=local_modules,
                    import_entrypoints=['tools/s04_e011_fn776/'+name+'.py' for name in
                                        ('worker', 'guard', 'square_root', 'build_code_package', 'verify_code_package', 'static_checks')],
                    source_repository='wenniebyfoxmail/phase-field-fracture-fatigue-pidl',
                    scope='code-only self-contained FN776 GPU7 snapshot; no scientific payload', files=rows)
    text = json.dumps(manifest, indent=2)+'\n'
    provenance_blob = cmd(['git', 'hash-object', '-w', '--stdin'], input=text)
    cmd(['git', 'read-tree', '--empty'], index=True)
    entries = ''.join(row['mode']+' '+row['blob']+'\t'+row['path']+'\n' for row in rows)
    entries += '100644 '+provenance_blob+'\tSOURCE_PROVENANCE.json\n'
    cmd(['git', 'update-index', '--index-info'], input=entries, index=True)
    tree = cmd(['git', 'write-tree'], index=True)
    snapshot = cmd(['git', 'commit-tree', tree, '-m', 'Self-contained FN776 GPU7 code snapshot from '+source])
    ref = 'refs/codex/fn776-gpu7-'+source[:12]
    cmd(['git', 'update-ref', ref, snapshot, '0'*40])
    bundle = out/'code.bundle'
    cmd(['git', 'bundle', 'create', str(bundle), ref])
    cmd(['git', 'bundle', 'verify', str(bundle)])
    materialized = out/'materialized/code'
    materialized.mkdir(parents=True)
    cmd(['git', 'init', str(materialized)])
    cmd(['git', '-C', str(materialized), 'fetch', str(bundle), ref])
    cmd(['git', '-C', str(materialized), 'checkout', '--detach', snapshot])
    result = json.loads(cmd([sys.executable, '-B', str(materialized/'tools/s04_e011_fn776/verify_code_package.py'),
                             '--code', str(materialized), '--expected-source', snapshot]))
    raw = bundle.read_bytes()  # Code-only transfer artifact, no scientific array.
    assert len(raw) < 10*1024**2, 'keep code bundle inside the100MiB overall output envelope'
    receipt = dict(status='self_contained_code_package_verified', development_source=source,
                   producer_source=snapshot, bundle_ref=ref, bundle=str(bundle),
                   bundle_bytes=len(raw), bundle_sha256=hashlib.sha256(raw).hexdigest(),
                   prerequisites=[], materialization=result)
    (out/'package_receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    build(a.source, a.out.resolve())
