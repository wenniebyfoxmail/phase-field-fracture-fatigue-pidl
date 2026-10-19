"""Artificial unit/interface data only. No real states, profiles or producer IO."""
from pathlib import Path
import json,os
from dataclasses import replace
import numpy as np
import pytest
from hybrid_kinematics import build_portable_native_q4_kinematics
from hybrid_mechanics import MechanicsWorkspace
from hybrid_incremental import SolverSettings
from damage_conditioned_equilibrium import assemble_amor_stiffness,solve_amor_equilibrium
from hybrid_work_trace import PersistentWorkTrace,EvidenceWriteError
from hybrid_diagnostics import compare_diagnostics,plot_fields
from hybrid_history import AcceptedState
from test_hybrid_producer import card
from hybrid_producer_common import write_json


def fixture():
    kin=build_portable_native_q4_kinematics(np.array([[0,0],[1.2,.1],[1,1.3],[-.1,.9]]),np.array([[0,1,2,3]]))
    m=dict(youngs_modulus=1.,poisson_ratio=.3,residual_stiffness=0.,thickness=1.)
    return kin,m


def test_cached_assembly_matches_independent_legacy_for_tension_compression_and_damage():
    k,m=fixture();w=MechanicsWorkspace(k,m)
    for sign in (1.,-1.):
        u=(sign*k.points).ravel();d=np.array([.1,.3,.8,.2])
        assert np.max(abs((w.assemble(d,u)-assemble_amor_stiffness(k,d,u,**m)).toarray()))<1e-13


def test_warm_solution_and_exact_numeric_cache_invalidation():
    k,m=fixture();w=MechanicsWorkspace(k,m);d=np.zeros(4);bc=np.array([0,1,2,3,5,7]);v=np.array([0.,0.,0.,0.,.02,.02])
    s=SolverSettings(force_scale=1.,damage_gradient_scale=1.)
    cold=solve_amor_equilibrium(k,d,bc,v,**m,residual_tolerance=s.force_tolerance)
    u,a=w.solve(d,bc,v,s);warm,b=w.solve(d,bc,v,s,initial_u=u)
    assert np.max(abs(u-cold.displacement))<1e-12 and np.max(abs(u-warm))<1e-12
    assert b['factorizations']==0 and b['factor_reuses']>=1
    _,changed=w.solve(np.full(4,.2),bc,v,s,initial_u=u)
    assert changed['factorizations']>=1
    assert not b['symbolic_factor_reuse']


def test_persistent_trace_precedes_work_and_preserves_failure(tmp_path):
    p=tmp_path/'work.jsonl';t=PersistentWorkTrace(p,'unit',1)
    def fail():
        assert json.loads(p.read_text().splitlines()[-1])['event']=='start'
        raise RuntimeError('artificial block failure')
    with pytest.raises(RuntimeError):t.call('factorization',fail)
    rows=[json.loads(x) for x in p.read_text().splitlines()]
    assert [x['event'] for x in rows]==['start','end'] and rows[-1]['status']=='failed'


def test_guard_signals_before_report_filesystem_failure(tmp_path,monkeypatch):
    import hybrid_deadline_guard as g
    a,b=os.pipe();c,d=os.pipe();fds=iter((a,c));kills=[]
    monkeypatch.setattr(g.sys,'platform','linux')
    monkeypatch.setattr(g.os,'pidfd_open',lambda pid:next(fds),raising=False)
    monkeypatch.setattr(g.os,'getpgid',lambda pid:pid)
    def kill(pid,sig):kills.append((pid,sig));os.write(b,b'x')
    monkeypatch.setattr(g.signal,'pidfd_send_signal',kill,raising=False)
    import socket
    left,right=socket.socketpair(socket.AF_UNIX,socket.SOCK_DGRAM)
    monkeypatch.setattr(g.tempfile,'mkstemp',lambda **kw:(_ for _ in ()).throw(OSError('report blocked/fails')))
    with pytest.raises(OSError):g.guard_loop(123,456,left.detach(),-1.,120.,tmp_path/'report.json')
    assert kills and kills[0][0]==a
    right.close();os.close(b);os.close(d)


def test_classical_quality_failure_blocks_joint_speed_claim(tmp_path):
    from run_hybrid_producer import outcome
    for n in ['train_A','train_B','validation','test_reference','test_classical','test_hybrid']:write_json(tmp_path/n/'summary.json',dict(f_min=.5))
    good=dict(mean_J=0.,max_J=0.,max_A_relative=0.,max_r_relative=0.,max_f_rms=0.,max_reaction_relative=0.)
    write_json(tmp_path/'analysis/summary.json',dict(methods={'test_hybrid':good,'test_classical':dict(good,max_J=.5)}))
    totals={'phases':{n:{'wall_seconds':100.} for n in ['native_replay','train_A','train_B','validation','training','test_reference','test_classical','test_hybrid','analysis']}}
    totals['phases']['test_hybrid']['wall_seconds']=50.
    result=outcome(card(),tmp_path,totals)
    assert result['quality_pass'] and result['online_speed_pass'] and not result['matched_quality']['test_classical']
    assert not result['supports_neural_online_acceleration']


def test_failure_retains_sampled_peak(tmp_path,monkeypatch):
    import run_hybrid_producer as r
    import subprocess,sys
    p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
    archive=tmp_path/'archive';archive.mkdir();usage={}
    def broken(*args):raise OSError('injected monitor IO')
    monkeypatch.setattr(r,'write_json',broken)
    with pytest.raises(OSError):r.supervise(p,dict(id='unit',kind='replay',gpu=False,wall_seconds=100),card(),tmp_path,archive,dict(start_monotonic=r.perf_counter(),gpu_seconds=0.),usage=usage)
    assert p.poll() is not None and usage['peak_rss_bytes']>=0 and 'termination_seconds' in usage and 'storage' in usage


def test_posthoc_diagnostics_and_common_scale_render_artificial_only(tmp_path):
    from hybrid_incremental import NativeQ4Backend
    k,m=fixture();b=NativeQ4Backend(k,np.zeros(4,bool));zero=np.zeros((1,4));one=np.ones((1,4))
    old=AcceptedState(np.zeros(8),np.zeros(4),zero,zero,one,np.zeros((1,4)),0,0,b.mesh_id,b.physics_id,'artificial')
    s=replace(old,displacement=np.array([0,0,0,0,0,.01,0,.01]),damage=np.array([0,.2,.7,.3]))
    d=compare_diagnostics(b,s,s,old,old)
    assert d['raw_rms']==0 and d['active_rms']==0 and d['front_hausdorff']==0 and d['support_iou']==1
    plot_fields(b,[s,old,s],4,tmp_path,dict(scope='ARTIFICIAL UNIT ARRAYS; display check only, no scientific result'))
    assert (tmp_path/'fields_step0004.md').exists() and (tmp_path/'fields_step0004.png').stat().st_size>100


def test_guard_ready_failure_reaps_both_owned_processes(tmp_path,monkeypatch):
    import run_hybrid_producer as r
    import subprocess,sys
    processes=[];spawn=subprocess.Popen
    def collect(*args,**kw):
        p=spawn(*args,**kw);processes.append(p);return p
    monkeypatch.setattr(r.subprocess,'Popen',collect)
    monkeypatch.setattr(r,'wait_guard_ready',lambda fd:(_ for _ in ()).throw(RuntimeError('guardian ready injected failure')))
    archive=tmp_path/'archive';archive.mkdir()
    with pytest.raises(RuntimeError,match='ready injected'):
        r.run_owned_worker([sys.executable,'-c','import time;time.sleep(30)'],tmp_path,None,tmp_path/'log',
                           dict(id='unit',kind='replay',gpu=False,wall_seconds=100),card(),tmp_path,archive,
                           dict(start_monotonic=r.perf_counter(),gpu_seconds=0.))
    assert len(processes)==2 and all(p.poll() is not None for p in processes)


def test_inspection_identifies_nested_inflight_work(tmp_path):
    from inspect_hybrid_run import inspect
    from hybrid_transaction import StateStore
    from test_hybrid_incremental import state
    p=tmp_path/'phase';p.mkdir();StateStore(p/'latest.npz').initialize(state())
    (p/'events.jsonl').write_text('{"step":0}\n')
    t=PersistentWorkTrace(p/'work_trace.jsonl','phase',1)
    t.emit(dict(event='start',block_id=0,kind='common_mechanics'))
    t.emit(dict(event='start',block_id=1,kind='mechanical.factorization'))
    row=inspect(tmp_path)[0]
    assert not row['reconciliation_needed'] and row['work_evidence_incomplete']
    assert [x['kind'] for x in row['unfinished_work_blocks']]==['common_mechanics','mechanical.factorization']


def test_no_samples_are_unknown_not_measured_zero(tmp_path):
    import run_hybrid_producer as r
    class Exited:
        returncode=0
        def poll(self):return 0
    usage={}
    result=r.supervise(Exited(),dict(id='unit',kind='replay',gpu=False,wall_seconds=100),card(),tmp_path,tmp_path,
                       dict(start_monotonic=r.perf_counter(),gpu_seconds=0.),usage=usage)
    assert result['peak_rss_bytes'] is None and result['peak_gpu_mib'] is None
    assert usage['rss_sample_count']==0 and not usage['rss_observed'] and usage['gpu_status']=='not_applicable'


def test_diagnostic_energy_scales_with_thickness_artificial_only():
    from hybrid_incremental import NativeQ4Backend
    from hybrid_diagnostics import fields
    k,_=fixture();b=NativeQ4Backend(k,np.zeros(4,bool));b3=NativeQ4Backend(k,np.zeros(4,bool),thickness=3.)
    z=np.zeros((1,4));one=np.ones((1,4))
    state=AcceptedState(np.array([0,0,0,0,0,.01,0,.01]),np.full(4,.2),z,z,one,z,0,0,b.mesh_id,b.physics_id,'artificial')
    a=fields(b,state,state)['diag'];c=fields(b3,state,state)['diag']
    for name in ('elastic_energy','fracture_energy','total_energy'):assert c[name]==pytest.approx(3*a[name])


@pytest.mark.parametrize('finished,expected',[(119.99,None),(120.02,'late step completion')])
def test_queued_step_completion_is_drained_before_timeout(tmp_path,monkeypatch,finished,expected):
    import hybrid_deadline_guard as g
    a,b=os.pipe();c,d=os.pipe();fds=iter((a,c))
    class FakeSocket:
        n=0
        def setblocking(self,value):pass
        def close(self):pass
        def recv(self,size):
            self.n+=1
            if self.n==1:return json.dumps(dict(event='step_start',step=1,started=0.)).encode()
            if self.n==3:return json.dumps(dict(event='step_done',step=1,finished=finished)).encode()
            raise BlockingIOError()
    sock=FakeSocket();times=iter([0.,0.,0.,120.01])
    monkeypatch.setattr(g.sys,'platform','linux')
    monkeypatch.setattr(g.os,'pidfd_open',lambda pid:next(fds),raising=False)
    monkeypatch.setattr(g.socket,'socket',lambda **kw:sock)
    monkeypatch.setattr(g.time,'monotonic',lambda:next(times,120.01))
    monkeypatch.setattr(g.select,'select',lambda readers,*args:([a] if readers==[a] or sock.n>=4 else [sock],[],[]))
    report=tmp_path/'guard.json';g.guard_loop(123,456,99,1000.,120.,report)
    result=json.loads(report.read_text());assert result['reason']==expected and sock.n>=3
    os.close(b);os.close(d)


@pytest.mark.parametrize('next_step',[False,True])
def test_worker_exit_rejects_missing_step_done(tmp_path,monkeypatch,next_step):
    """Artificial controller only: exit cannot certify an unfinished step."""
    import hybrid_deadline_guard as g
    a,b=os.pipe();c,d=os.pipe();fds=iter((a,c))
    messages=[dict(event='step_start',step=1,started=0.)]
    if next_step:messages += [dict(event='step_done',step=1,finished=20.),dict(event='step_start',step=2,started=21.)]
    class FakeSocket:
        def setblocking(self,value):pass
        def close(self):pass
        def recv(self,size):
            if messages:return json.dumps(messages.pop(0)).encode()
            raise BlockingIOError()
    sock=FakeSocket()
    monkeypatch.setattr(g.sys,'platform','linux')
    monkeypatch.setattr(g.os,'pidfd_open',lambda pid:next(fds),raising=False)
    monkeypatch.setattr(g.socket,'socket',lambda **kw:sock)
    monkeypatch.setattr(g.time,'monotonic',lambda:30.)
    monkeypatch.setattr(g.select,'select',lambda *args:([a],[],[]))
    report=tmp_path/'exit_guard.json';g.guard_loop(123,456,99,1000.,120.,report)
    result=json.loads(report.read_text())
    assert result['reason']=='incomplete step completion at worker exit'
    assert result['status']=='deadline_or_control_stop'
    assert result['active']['step']==(2 if next_step else 1)
    os.close(b);os.close(d)
