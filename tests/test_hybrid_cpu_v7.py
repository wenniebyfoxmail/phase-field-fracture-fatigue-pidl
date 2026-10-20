"""Offline control/serialization tests only. Never spawn producer or SSH."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import zipfile
import pytest
from hybrid_producer_common import lossless_snapshot
from hybrid_transaction import StateStore
from test_hybrid_state_contract import bound
import run_hybrid_cpu_budgeted as cpu


def card():
    p=Path(__file__).resolve().parents[1]/'docs/research/S04/hybrid_constrained_design_20261019/solver_repair_v7/prepare_packet.py'
    spec=importlib.util.spec_from_file_location('v7_packet',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.make_card()


def test_exact_single_trajectory_CPU_budget_and_physical_settings():
    c=card();cpu.validate(c)
    assert c['budget']['primary_gib']+c['budget']['archive_gib']+c['budget']['local_retrieval_gib']==16
    assert c['phases'][0]['cycles']*len(c['base_load_cycle'])==600
    assert c['phases'][0]['role']=='reference' and c['budget']['training_fits']==0


@pytest.mark.parametrize('defect',['gpu','extra_case','steps','fresh_cap','tol','clock','storage','authority','disabled'])
def test_invalid_envelope_never_validates(defect):
    c=card()
    if defect=='gpu':c['phases'][0]['gpu']=True
    elif defect=='extra_case':c['phases'].append(deepcopy(c['phases'][0]))
    elif defect=='steps':c['phases'][0]['cycles']=121
    elif defect=='fresh_cap':c['solver']['max_outer']=101
    elif defect=='tol':c['solver']['damage_tolerance']=2e-7
    elif defect=='clock':c['package_start_epoch']+=1
    elif defect=='storage':c['budget']['archive_gib']=15
    elif defect=='authority':c['authority']['authority_type']='agent_inference'
    elif defect=='disabled':c['execution_enabled']=False
    with pytest.raises(RuntimeError):cpu.validate(c)


def test_lossless_snapshot_preserves_D13_all_arrays_and_certificate(tmp_path):
    old,p,initial=bound();store=StateStore(tmp_path/'state.npz');store.initialize(old,context=initial);store.commit(p)
    dest=tmp_path/'snapshot.npz';lossless_snapshot(store.path,dest)
    state,meta=StateStore(dest).load()
    assert state.fingerprint()==p.state.fingerprint() and meta['certificate']==store.load()[1]['certificate']
    with zipfile.ZipFile(dest) as z:assert all(x.compress_type==zipfile.ZIP_DEFLATED for x in z.infolist())
    with zipfile.ZipFile(store.path) as a,zipfile.ZipFile(dest) as b:
        assert set(a.namelist())==set(b.namelist())
        assert all(a.read(name)==b.read(name) for name in a.namelist())


def test_snapshot_replace_failure_preserves_previous_file(tmp_path,monkeypatch):
    import hybrid_producer_common as common
    import numpy as np
    source=tmp_path/'source.npz';dest=tmp_path/'snapshot.npz'
    np.savez(source,value=np.arange(4));dest.write_bytes(b'previous')
    monkeypatch.setattr(common.os,'replace',lambda *a:(_ for _ in ()).throw(OSError('replace failed')))
    with pytest.raises(OSError):lossless_snapshot(source,dest)
    assert dest.read_bytes()==b'previous' and not list(tmp_path.glob('.snapshot-*'))


def test_admission_exception_still_leaves_terminal_without_worker(tmp_path,monkeypatch):
    for name in ['execution_card.json','source_manifest.json','execution_review.json']:
        (tmp_path/name).write_text(json.dumps(card() if name=='execution_card.json' else {}))
    monkeypatch.setattr(cpu,'ROOT',tmp_path)
    monkeypatch.setattr(cpu,'supervise_cpu',lambda *a:(_ for _ in ()).throw(RuntimeError('admission failed')))
    monkeypatch.setattr(cpu.sys,'argv',['cpu','--supervise'])
    with pytest.raises(RuntimeError,match='admission failed'):cpu.main()
    r=json.loads((tmp_path/'terminal.json').read_text())
    assert not r['worker_started'] and r['automatic_retry'] is False


def test_reserved_unknown_launch_never_spawns_again(tmp_path,monkeypatch):
    (tmp_path/'launch_reservation.json').write_text('{}')
    monkeypatch.setattr(cpu,'verify',lambda *a:None)
    monkeypatch.setattr(cpu.platform,'system',lambda:'Linux')
    monkeypatch.setattr(cpu.socket,'gethostname',lambda:'GPUServer8')
    monkeypatch.setattr(cpu,'ARCHIVE',tmp_path/'absent_archive')
    c=card();monkeypatch.setattr(cpu,'time',lambda:c['package_start_epoch']+10)
    monkeypatch.setattr(cpu.subprocess,'Popen',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('must not spawn')))
    with pytest.raises(FileExistsError):cpu.launch(tmp_path,c,{}, {})


def test_preparation_charge_exhaustion_refuses_before_reservation(tmp_path,monkeypatch):
    monkeypatch.setattr(cpu,'verify',lambda *a:None)
    monkeypatch.setattr(cpu.platform,'system',lambda:'Linux')
    monkeypatch.setattr(cpu.socket,'gethostname',lambda:'GPUServer8')
    monkeypatch.setattr(cpu,'ARCHIVE',tmp_path/'absent_archive')
    c=card();monkeypatch.setattr(cpu,'time',lambda:c['package_start_epoch']+13800)
    with pytest.raises(RuntimeError,match='budget exhausted'):cpu.launch(tmp_path,c,{}, {})
    assert not (tmp_path/'launch_reservation.json').exists()


def resource_fixture(monkeypatch):
    from types import SimpleNamespace
    import run_hybrid_producer as producer
    class Proc:
        pid=20
        returncode=0
        calls=0
        def poll(self):
            self.calls+=1
            return None if self.calls==1 else 0
    def process(pid,rss):return SimpleNamespace(pid=pid,memory_info=lambda:SimpleNamespace(rss=rss,vms=rss))
    supervisor=process(10,100);worker=process(20,200);guardian=process(30,50)
    supervisor.children=lambda recursive:[worker,guardian]
    monkeypatch.setattr(producer.psutil,'Process',lambda pid:supervisor)
    monkeypatch.setattr(producer,'sleep',lambda _:None)
    monkeypatch.setattr(producer,'write_json',lambda *a:None)
    monkeypatch.setattr(producer,'bytes_under',lambda p:0)
    return producer,Proc()


def test_resource_monitor_accounts_full_owned_tree(tmp_path,monkeypatch):
    r,proc=resource_fixture(monkeypatch);usage={}
    result=r.supervise(proc,dict(id='train_A',gpu=False,kind='trajectory',wall_seconds=100),
        card(),tmp_path,tmp_path/'archive',dict(start_monotonic=r.perf_counter(),gpu_seconds=0.,resource_owner_pid=10),usage)
    assert result['peak_rss_bytes']==350 and usage['aggregate_vms_bytes']==350 and usage['resource_scope_pid']==10


def test_final_storage_scan_catches_excess_even_before_first_live_scan(tmp_path,monkeypatch):
    r,proc=resource_fixture(monkeypatch)
    def sizes(path):
        return 8*2**30 if path==tmp_path/'archive' else 0
    monkeypatch.setattr(r,'bytes_under',sizes)
    with pytest.raises(RuntimeError,match='final attributed storage'):
        r.supervise(proc,dict(id='train_A',gpu=False,kind='trajectory',wall_seconds=100),
            card(),tmp_path,tmp_path/'archive',dict(start_monotonic=r.perf_counter(),gpu_seconds=0.,resource_owner_pid=10),{})


def test_owned_tree_VMS_cap_is_separate_from_RSS(tmp_path,monkeypatch):
    from types import SimpleNamespace
    r,proc=resource_fixture(monkeypatch)
    monkeypatch.setattr(r.psutil,'Process',lambda pid:SimpleNamespace(pid=pid,children=lambda recursive:[],
        memory_info=lambda:SimpleNamespace(rss=100,vms=33*2**30)))
    with pytest.raises(RuntimeError,match='address-space cap'):
        r.supervise(proc,dict(id='train_A',gpu=False,kind='trajectory',wall_seconds=100),
            card(),tmp_path,tmp_path/'archive',dict(start_monotonic=r.perf_counter(),gpu_seconds=0.,resource_owner_pid=10),{})


def test_step_boundary_storage_headroom_and_final_cap(tmp_path,monkeypatch):
    import run_hybrid_producer as r
    from hybrid_producer_worker import trajectory_storage_check
    c=card();root=tmp_path/'root';archive=tmp_path/'archive'
    monkeypatch.setattr(r,'bytes_under',lambda p:7*2**30-64*2**20 if p==archive else 0)
    with pytest.raises(RuntimeError,match='headroom'):trajectory_storage_check(c,root,archive,True)
    trajectory_storage_check(c,root,archive,False)
    monkeypatch.setattr(r,'bytes_under',lambda p:8*2**30 if p==archive else 0)
    with pytest.raises(RuntimeError):trajectory_storage_check(c,root,archive,False)


def test_retained_dependency_bytes_closure_and_symlinks(tmp_path,monkeypatch):
    deps=tmp_path/'deps';deps.mkdir();(deps/'module.py').write_text('identity')
    manifest=tmp_path/'retained.json';manifest.write_text(json.dumps(dict(files={'module.py':cpu.digest(deps/'module.py')})))
    c=dict(retained_deps_manifest='retained.json',retained_deps_manifest_sha256=cpu.digest(manifest))
    monkeypatch.setattr(cpu,'DEPS',deps);cpu.verify_retained_deps(tmp_path,c)
    (deps/'module.py').write_text('changed')
    with pytest.raises(RuntimeError,match='bytes differ'):cpu.verify_retained_deps(tmp_path,c)
    (deps/'module.py').write_text('identity');(deps/'extra.py').write_text('extra')
    with pytest.raises(RuntimeError):cpu.verify_retained_deps(tmp_path,c)
    (deps/'extra.py').unlink();(deps/'extra.pyc').write_bytes(b'cached')
    with pytest.raises(RuntimeError,match='bytecode'):cpu.verify_retained_deps(tmp_path,c)
    (deps/'extra.pyc').unlink();(deps/'__pycache__').mkdir()
    with pytest.raises(RuntimeError,match='cache'):cpu.verify_retained_deps(tmp_path,c)
    (deps/'__pycache__').rmdir();(deps/'alias').symlink_to(tmp_path,target_is_directory=True)
    with pytest.raises(RuntimeError,match='symlink'):cpu.verify_retained_deps(tmp_path,c)


@pytest.mark.parametrize('bad_source',[False,True])
def test_receiver_copies_only_reviewed_same_host_OSQP_bytes_before_one_launch(tmp_path,monkeypatch,bad_source):
    import io,tarfile
    from types import SimpleNamespace
    import receive_hybrid_cpu_v7 as rx
    root=tmp_path/'run';archive=tmp_path/'archive';old=tmp_path/'retained';old.mkdir()
    (old/'module.py').write_bytes(b'old original OSQP standin\n')
    (old/'__pycache__').mkdir();(old/'__pycache__/ignored.pyc').write_bytes(b'not copied/imported')
    deps=json.dumps(dict(files={'module.py':rx.sha((old/'module.py').read_bytes())})).encode()
    sources={'tools/run_hybrid_cpu_budgeted.py':b'raise AssertionError("test must mock launch")\n',
             'deps_manifest.json':deps}
    files={k:rx.sha(v) for k,v in sources.items()}
    artifact=rx.sha(json.dumps(files,sort_keys=True,allow_nan=False).encode())
    c=dict(run_root=str(root),archive_root=str(archive),execution_enabled=True,
        retained_deps_manifest='deps_manifest.json',retained_deps_manifest_sha256=rx.sha(deps))
    cb=json.dumps(c).encode();review=dict(verdict='REVIEW_PASS',artifact_id=artifact,card_sha256=rx.sha(cb))
    payload={'source_manifest.json':json.dumps(dict(files=files,artifact_id=artifact)).encode(),
        'execution_card.json':cb,'execution_review.json':json.dumps(review).encode()}
    payload.update({'code/'+k:v for k,v in sources.items()})
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w:gz') as t:
        for name,data in payload.items():
            item=tarfile.TarInfo(name);item.size=len(data);t.addfile(item,io.BytesIO(data))
    raw=buffer.getvalue()
    if bad_source:(old/'module.py').write_bytes(b'changed')
    monkeypatch.setattr(rx,'ROOT',root);monkeypatch.setattr(rx,'ARCHIVE',archive);monkeypatch.setattr(rx,'OLD_DEPS',old)
    monkeypatch.setattr(rx.socket,'gethostname',lambda:'GPUServer8')
    monkeypatch.setattr(rx.pwd,'getpwnam',lambda _:SimpleNamespace(pw_uid=rx.os.geteuid()))
    monkeypatch.setattr(rx.os.path,'ismount',lambda p:True)
    monkeypatch.setattr(rx.sys,'stdin',SimpleNamespace(buffer=io.BytesIO(raw)))
    monkeypatch.setattr(rx.sys,'argv',['rx',rx.sha(raw)])
    launched=[]
    monkeypatch.setattr(rx.subprocess,'check_output',lambda *a,**kw:(launched.append(a) or '{"state":"spawned","pid":123}'))
    if bad_source:
        with pytest.raises(RuntimeError,match='source differs'):rx.main()
        assert not launched and (root/'dispatch_reservation.json').exists()
    else:
        rx.main();assert len(launched)==1
        assert (root/'deps/module.py').read_bytes()==(old/'module.py').read_bytes()
        assert not (root/'deps/__pycache__').exists()
        assert (old/'__pycache__/ignored.pyc').read_bytes()==b'not copied/imported'
