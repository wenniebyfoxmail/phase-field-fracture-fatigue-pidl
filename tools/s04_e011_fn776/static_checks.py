"""FN776-r4 diff checks: AST/text/Git only; no mock or runtime exercise."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def check(root):
    assert not sys.flags.optimize
    folder=root/'docs/research/S04/S04-E011/uv_head_c1_solver_d3_20261019'
    original=json.loads((folder/'inputs_fn776.json').read_text()) if (folder/'inputs_fn776.json').exists() else None
    current=json.loads((folder/'inputs_fn776_r4.json').read_text())
    preserved=('protocol','files','budget','fn776','work_ledger','resource_policy','resource_revision','rcond','relative_gain_screen','cycle','substep','load','FEM_outer','source_base')
    if original is not None:
        for key in preserved:assert current[key]==original[key],key
    assert current['run_id']=='pf_s04e011_uvh_c1_fn776_r4_20261024'
    assert current['control_plane']['diagnostic_reserve_bytes']==1024**2
    assert current['control_plane']['guard_sampled_payload_stop_bytes']==current['budget']['output_bytes']-2*1024**2
    assert current['control_plane']['readonly_preflight_seconds']==60
    frozen={}
    for name in ('worker.py','square_root.py'):
        path='tools/s04_e011_fn776/'+name
        raw=(root/path).read_bytes()
        if (root/'SOURCE_PROVENANCE.json').exists():
            expected=json.loads((root/'SOURCE_PROVENANCE.json').read_text())['locked_solver_blobs'][path]
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==expected,path
        else:
            prior=subprocess.check_output(['git','show','f1ed1ed969b10637fa774b3a0cc29aa24b2b7f92:'+path],cwd=root)
            assert raw==prior,path
        frozen[path]=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    parsed={}
    for path in (root/'tools/s04_e011_fn776').glob('*.py'):
        tree=ast.parse(path.read_text(),filename=str(path));parsed[path.name]=tree
        for node in tree.body:
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                modules=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module]
                assert all(m.split('.')[0] not in ('numpy','torch','scipy','matplotlib') for m in modules)
    remote=parsed['remote_control_r2.py']
    embedded=next(n.value.args[0].value for n in remote.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CONTRACT' for t in n.targets))
    assert json.loads(embedded)==current
    # Preflight reuses exact reviewed GPU/identity helper AST; only command logging changes.
    guard=parsed['guard.py']
    for name in ('digest','service_identity','gpu_snapshot'):
        a=next(n for n in guard.body if isinstance(n,ast.FunctionDef) and n.name==name)
        b=next(n for n in remote.body if isinstance(n,ast.FunctionDef) and n.name==name)
        assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False),name
    return dict(status='DIFF_STATIC_PASS',frozen_solver_blobs=frozen,preserved_contract_keys=list(preserved),
                parsed_modules=len(parsed),resource_helper_AST_unchanged=True,
                control_budget='1MiB control +98MiB sampled producer payload +1MiB producer terminal <=100MiB',
                checks='AST/text/Git only; no mocked subprocess/resource check, numeric import or runtime validation',
                SSH=False,scientific_payload_access=False,numerical_calls=False)


if __name__=='__main__':
    print(json.dumps(check(Path(__file__).resolve().parents[2]),indent=2))
