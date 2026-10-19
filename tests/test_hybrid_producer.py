"""Producer contracts using artificial data/processes; no scientific solve/fit."""
import copy
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import numpy as np
import pytest

from hybrid_inputs import blocked_to_interleaved,native_dofs_to_canonical,sha256
from hybrid_incremental import solve_step,StepFailure
from hybrid_producer_common import classical_guess,verify_package,object_sha,write_json
from run_hybrid_producer import validate_card,supervise,outcome
from test_hybrid_incremental import AlgebraicBackend,state,settings


def card():
    return json.loads((Path(__file__).resolve().parents[1]/'docs/research/S04/hybrid_constrained_design_20261019/execution_card_v2.json').read_text())


def test_native_dof_vector_and_boundary_permutation_are_consistent():
    native=np.array([10.,20.,30.,100.,200.,300.])
    canonical=blocked_to_interleaved(native)
    assert np.array_equal(canonical,[10,100,20,200,30,300])
    dofs=np.array([0,2,3,5])
    assert np.array_equal(canonical[native_dofs_to_canonical(dofs,3)],native[dofs])
    with pytest.raises(ValueError):native_dofs_to_canonical(np.array([1.]),3)


def test_prediction_context_is_the_common_initial_field_not_final_field():
    p=solve_step(AlgebraicBackend(),state(),np.array([0]),np.array([0.]),
                 next_load_id='next',settings=settings(),return_prediction_context=True)
    u,psi=p.prediction_context
    assert np.all(u==0) and np.all(psi==0)
    assert np.max(p.state.displacement)>.39
    assert not u.flags.writeable


def test_sum_and_l2_criteria_do_not_silently_relax_native_acceptance():
    class BadL2(AlgebraicBackend):
        def force_audit(self,*args):
            return dict(force_inf=0.,force_l2=2e-8,force_scaled=0.,boundary_inf=0.)
    with pytest.raises(StepFailure,match='iteration cap'):
        solve_step(BadL2(),state(),np.array([0]),np.array([0.]),next_load_id='next',settings=settings(max_outer=1))


def test_classical_extrapolation_has_fixed_predecessor_lower():
    old=state(np.full(4,.4));previous=state(np.full(4,.2))
    assert np.allclose(classical_guess(old,previous,3.,2.,1.),.6)
    assert np.array_equal(classical_guess(old,previous,0.,2.,1.),old.damage)


def test_exact_card_and_training_before_test_boundary():
    c=card();validate_card(c)
    bad=copy.deepcopy(c);bad['phases'][3],bad['phases'][4]=bad['phases'][4],bad['phases'][3]
    with pytest.raises(ValueError,match='ordering'):validate_card(bad)
    bad=copy.deepcopy(c);bad['budget']['gpu_hours']=13
    with pytest.raises(ValueError,match='resource'):validate_card(bad)


def test_package_hash_tamper_is_rejected(tmp_path):
    p=tmp_path/'kernel.py';p.write_text('pass\n')
    files={'kernel.py':sha256(p)};m=dict(files=files,artifact_id=object_sha(files))
    verify_package(tmp_path,m);p.write_text('changed\n')
    with pytest.raises(RuntimeError,match='bytes differ'):verify_package(tmp_path,m)


def test_watchdog_only_stops_its_spawned_group_on_hard_cap(tmp_path):
    c=card();archive=tmp_path/'archive';archive.mkdir()
    proc=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
    with pytest.raises(RuntimeError,match='hard wall cap'):
        supervise(proc,dict(id='unit',kind='replay',gpu=False,wall_seconds=1e-9),c,tmp_path,archive,
                  dict(wall_seconds=0.,gpu_seconds=0.,start_monotonic=perf_counter()))
    assert proc.poll() is not None


def test_history_mismatch_blocks_acceleration_even_if_field_and_time_pass(tmp_path):
    c=card()
    for name in ['train_A','train_B','validation','test_reference','test_classical','test_hybrid']:
        write_json(tmp_path/name/'summary.json',dict(completed=True,f_min=.5))
    metrics=dict(mean_J=0.,max_J=0.,max_A_relative=.8,max_r_relative=0.,max_f_rms=0.,max_reaction_relative=0.)
    write_json(tmp_path/'analysis/summary.json',dict(methods={'test_hybrid':metrics}))
    totals={'phases':{name:{'wall_seconds':100.} for name in ['native_replay','train_A','train_B','validation','training','test_reference','test_classical','test_hybrid','analysis']}}
    totals['phases']['test_hybrid']['wall_seconds']=50.
    result=outcome(c,tmp_path,totals)
    assert result['online_speed_pass'] and not result['quality_pass']
    assert not result['supports_neural_online_acceleration']


def test_detached_launcher_reservation_prevents_duplicate_spawn(tmp_path,monkeypatch):
    import launch_hybrid_detached as launch
    from types import SimpleNamespace
    c=card();c['run_root']=str(tmp_path);c['archive_root']=str(tmp_path/'archive')
    cp=tmp_path/'card.json';write_json(cp,c)
    m=dict(files={},artifact_id=object_sha({}));mp=tmp_path/'package.json';write_json(mp,m)
    rp=tmp_path/'review.json';write_json(rp,dict(verdict='REVIEW_PASS',card_sha256=sha256(cp),artifact_id=m['artifact_id']))
    calls=[]
    def fake_spawn(*args,**kwargs):
        assert kwargs['start_new_session'] is True
        calls.append(args);return SimpleNamespace(pid=12345)
    monkeypatch.setattr(launch.platform,'system',lambda:'Linux')
    monkeypatch.setattr(launch.subprocess,'Popen',fake_spawn)
    monkeypatch.setattr(sys,'argv',['launch','--card',str(cp),'--package',str(mp),'--review',str(rp),'--inputs',str(tmp_path)])
    launch.main()
    with pytest.raises(FileExistsError):launch.main()
    assert len(calls)==1


def test_first_postspawn_event_write_failure_reaps_owned_worker(tmp_path,monkeypatch):
    import run_hybrid_producer as run
    archive=tmp_path/'archive';archive.mkdir()
    processes=[];spawn=run.subprocess.Popen
    def record_spawn(*args,**kwargs):
        proc=spawn(*args,**kwargs);processes.append(proc);return proc
    def fail_event(*args):raise OSError('injected first receipt IO fault')
    monkeypatch.setattr(run.subprocess,'Popen',record_spawn)
    monkeypatch.setattr(run,'append_event',fail_event)
    with pytest.raises(OSError,match='receipt IO'):
        run.run_owned_worker([sys.executable,'-c','import time;time.sleep(30)'],tmp_path,None,tmp_path/'worker.log',
                             dict(id='unit',kind='replay',gpu=False,wall_seconds=30),card(),tmp_path,archive,
                             dict(wall_seconds=0.,gpu_seconds=0.,start_monotonic=perf_counter()))
    assert len(processes)==1 and processes[0].poll() is not None


def test_recovery_inspection_reports_truncated_prefix_and_isolates_bad_store(tmp_path):
    from inspect_hybrid_run import inspect
    from hybrid_transaction import StateStore
    good=tmp_path/'a';good.mkdir()
    StateStore(good/'latest.npz').initialize(state())
    (good/'events.jsonl').write_text('{"step":0}\n{"step":')
    bad=tmp_path/'b';bad.mkdir();(bad/'latest.npz').write_bytes(b'corrupt')
    rows=inspect(tmp_path)
    assert len(rows)==2 and rows[0]['version']==0
    assert rows[0]['last_journal_step']==0 and rows[0]['journal_errors'][0]['line']==2
    assert rows[0]['reconciliation_needed'] and rows[1]['reconciliation_needed']
    assert 'inspection_error' in rows[1]


def test_shared_replay_analysis_budget_is_cumulative(tmp_path):
    c=card();archive=tmp_path/'archive';archive.mkdir()
    proc=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],start_new_session=True)
    with pytest.raises(RuntimeError,match='shared replay and analysis'):
        supervise(proc,dict(id='analysis',kind='analysis',gpu=False,wall_seconds=14400),c,tmp_path,archive,
                  dict(wall_seconds=0.,gpu_seconds=0.,shared_analysis_seconds=14400.,start_monotonic=perf_counter()))
    assert proc.poll() is not None


def test_portable_geometry_matches_independent_lapack_and_linear_patch():
    from hybrid_kinematics import build_portable_native_q4_kinematics
    from native_q4_damage_qp import build_native_q4_kinematics
    points=np.array([[0.,0.],[1.2,.1],[1.,1.3],[-.1,.9]])
    cells=np.array([[0,1,2,3]])
    p=build_portable_native_q4_kinematics(points,cells);old=build_native_q4_kinematics(points,cells)
    assert np.max(np.abs(p.b_matrices-old.b_matrices))<1e-14
    assert np.max(np.abs(p.det_jacobians-old.det_jacobians))<1e-14
    u=np.column_stack((2*points[:,0]+3*points[:,1],-points[:,0]+4*points[:,1])).ravel()
    strain=np.einsum('egij,ej->egi',p.b_matrices,u[p.element_dofs])
    assert np.max(np.abs(strain-np.array([2.,4.,2.])))<1e-14
