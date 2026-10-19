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
    return json.loads((Path(__file__).resolve().parents[1]/'docs/research/S04/hybrid_constrained_design_20261019/execution_card_v1.json').read_text())


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
