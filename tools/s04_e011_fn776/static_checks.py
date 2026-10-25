"""FN776-r7 static checks: AST/text/Git only; no mock or runtime exercise."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

BASELINE = 'f1ed1ed969b10637fa774b3a0cc29aa24b2b7f92'
RUN = 'pf_s04e011_uvh_c1_fn776_r7_20261025'
CARD = 'S04-E011-UVH-C1-FN776-CARD-r7'
INDEX = 'S04-E011-FN776-r7-A1'
RESOURCE_REVISION = 'GPU7-FN776-shared-r2-uvicorn28011'
THIRD_SERVICE = {
    'pid': 651952,
    'start_ticks': 541746716,
    'uids': [0, 0, 0, 0],
    'cmdline_sha256': 'be18325d0086a499e503b772c5a74d63a708299a314533ef5711f5cf5b853808',
    'cgroup_sha256': 'a1e3fcdf826b0ef154308aec0ff2d84eabf72cd221b321f5f1db06e001ee468e',
    'baseline_MiB': 5638,
    'maximum_MiB': 6144,
    'description': 'root Docker-scoped python -m uvicorn app.main:app --host 0.0.0.0 --port 28011 --workers 1',
    'utc': '2026-10-25T17:10:13+00:00',
}


def blob(raw):
    return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()


def worker_expected(root):
    prior=subprocess.check_output(['git','show',BASELINE+':tools/s04_e011_fn776/worker.py'],cwd=root,text=True)
    changes=(
("""    limits, pc = contract['budget'], contract['fn776']
    torch.cuda.reset_peak_memory_stats()
    torch.cuda.set_per_process_memory_fraction(
        limits['gpu_reserved_bytes'] / torch.cuda.get_device_properties(0).total_memory)
""", """    pc = contract['fn776']
    torch.cuda.reset_peak_memory_stats()
"""),
("""    def check_work():
        if elapsed() >= limits['work_seconds']:
            raise StopBudget('science_deadline_840s')
        if torch.cuda.max_memory_reserved() > limits['gpu_reserved_bytes']:
            raise RuntimeError('GPU reserved memory cap')
""", """    def check_work():
        # The explicit authorization has no self wall-time or CUDA-memory ceiling.
        # Preserve this call-site hook so the fixed accounting structure is unchanged.
        return None
"""),
("""        check_work()
        if phase in ('curvature', 'trials') and elapsed() >= limits['opt_no_new_eval_seconds']:
            raise StopBudget('optimization_deadline_600s')
        if used[phase] + cost > allowances[phase] or sum(used.values()) + cost > allowances['total']:
""", """        check_work()
        if used[phase] + cost > allowances[phase] or sum(used.values()) + cost > allowances['total']:
"""),
("""    def opt_check():
        check_work()
        if elapsed() >= limits['opt_no_new_eval_seconds']:
            raise StopBudget('optimizer_deadline_600s')
""", """    def opt_check():
        check_work()
"""),
("""    except StopBudget as reason:
        stop = str(reason)
        # No fresh science after its hard deadline; retain the partial trace.
        if elapsed() >= limits['work_seconds']:
            raise
""", """    except StopBudget as reason:
        stop = str(reason)
"""),
    )
    for old,new in changes:
        assert prior.count(old)==1
        prior=prior.replace(old,new)
    return prior


def check(root):
    assert not sys.flags.optimize
    folder=root/'docs/research/S04/S04-E011/uv_head_c1_solver_d3_20261019'
    original=json.loads((folder/'inputs_fn776.json').read_text())
    current=json.loads((folder/'inputs_fn776_r7.json').read_text())
    preserved=('protocol','files','fn776','work_ledger','rcond','relative_gain_screen','cycle','substep','load','FEM_outer','source_base')
    for key in preserved:
        assert current[key]==original[key],key
    assert current['run_id']==RUN
    assert current['resource_revision']==RESOURCE_REVISION
    assert 'budget' not in current
    assert current['execution_resource_policy']['self_resource_ceiling']=='none'
    assert current['execution_resource_policy']['self_resource_enforcement']=='none'
    assert current['execution_resource_policy']['algorithmic_scope_is_not_a_resource_ceiling'] is True
    policy=current['resource_policy']; old_policy=original['resource_policy']
    assert set(policy)==set(old_policy)|{'minimum_host_available_kB','minimum_data2_free_bytes'}
    for key in old_policy:
        if key!='services':
            assert policy[key]==old_policy[key],key
    assert policy['services']==old_policy['services']+[THIRD_SERVICE]
    assert policy['minimum_host_available_kB']==16*1024*1024
    assert policy['minimum_data2_free_bytes']==5*1024**3
    assert current['control_plane']['card_id']==CARD
    assert current['control_plane']['approval_index']==INDEX
    assert current['control_plane']['readonly_preflight_seconds']==60
    assert current['control_plane']['resource_policy_changed'] is True
    assert 'self_resource_limits' in current['control_plane']
    worker=(root/'tools/s04_e011_fn776/worker.py').read_text()
    assert worker==worker_expected(root), 'worker numerical code changed outside reviewed resource-cap deletion'
    for forbidden in ("contract['budget']",'work_seconds','opt_no_new_eval_seconds',"limits['gpu_reserved_bytes']",'set_per_process_memory_fraction'):
        assert forbidden not in worker,forbidden
    square=root/'tools/s04_e011_fn776/square_root.py'
    original_square=subprocess.check_output(['git','show',BASELINE+':tools/s04_e011_fn776/square_root.py'],cwd=root)
    assert square.read_bytes()==original_square
    parsed={}
    for path in (root/'tools/s04_e011_fn776').glob('*.py'):
        raw=path.read_text();tree=ast.parse(raw,filename=str(path));parsed[path.name]=tree
        for node in tree.body:
            if isinstance(node,(ast.Import,ast.ImportFrom)):
                modules=[a.name for a in node.names] if isinstance(node,ast.Import) else [node.module]
                assert all(m.split('.')[0] not in ('numpy','torch','scipy','matplotlib') for m in modules)
    remote=parsed['remote_control_r2.py']
    embedded=next(n.value.args[0].value for n in remote.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CONTRACT' for t in n.targets))
    assert json.loads(embedded)==current
    guard=parsed['guard.py']
    for name in ('digest','service_identity','gpu_snapshot'):
        a=next(n for n in guard.body if isinstance(n,ast.FunctionDef) and n.name==name)
        b=next(n for n in remote.body if isinstance(n,ast.FunctionDef) and n.name==name)
        assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False),name
    for path in (root/'tools/s04_e011_fn776/guard.py',root/'tools/s04_e011_fn776/remote_control_r2.py',root/'tools/s04_e011_fn776/control_r2.py',root/'tools/s04_e011_fn776/verify_retrieval_r2.py',root/'tools/s04_e011_fn776/build_code_package.py'):
        raw=path.read_text()
        for forbidden in ("contract['budget']",'gpu_process_bytes','100MiB','10*1024**2'):
            assert forbidden not in raw,(path.name,forbidden)
    mechanics={}
    for path in ('SENS_tensile/run_native_q4_one_step_matrix.py','SENS_tensile/field_computation.py'):
        raw=(root/path).read_bytes();prior=subprocess.check_output(['git','show','3dfef418828e53632b3a5c90521ab8989dbf9673:'+path],cwd=root)
        assert raw==prior,path;mechanics[path]=blob(raw)
    return dict(status='DIFF_STATIC_PASS',worker_blob=blob(worker.encode()),square_root_blob=blob(square.read_bytes()),
                frozen_mechanics_blobs=mechanics,preserved_contract_keys=list(preserved),parsed_modules=len(parsed),
                resource_helper_AST_unchanged=True,self_resource_limits='none',
                shared_safety='GPU UUID/exact three-service identity/free margin plus host RAM/data2 free margin',
                third_service=THIRD_SERVICE,
                checks='AST/text/Git only; no SSH, payload decoding, numeric import or runtime validation',
                SSH=False,scientific_payload_access=False,numerical_calls=False)


if __name__=='__main__':
    print(json.dumps(check(Path(__file__).resolve().parents[2]),indent=2))
