"""Tiny metadata/array fixtures; no project field forward or optimizer runs."""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/s04_e036"))
import run_paired_windows as runner
import score_paired_windows as scorer
from window_inputs import optimizer_work, predecessor_key, sha256, state_key


def test_fem_residual_override_does_not_change_pidl_policy(monkeypatch):
    common = {"acceptance_config": {"history_atol": 2e-6, "history_rtol": 2e-6}}
    problem = SimpleNamespace(common=common, native_x=None, cells=None, native_area=None,
                              mat=None, model=None, penalty=None, fatigue=None)
    captured = []
    monkeypatch.setattr(runner, "make_sent_final_residual_check",
                        lambda **kwargs: captured.append(kwargs["config"]) or (lambda _: None))
    runner.WindowProblem.residual(problem, None, history_atol=1e-10, history_rtol=0.)
    runner.WindowProblem.residual(problem, None)
    assert captured == [dict(history_atol=1e-10, history_rtol=0.),
                         dict(history_atol=2e-6, history_rtol=2e-6)]
    assert common["acceptance_config"] == captured[1]
    with pytest.raises(ValueError, match="only history-policy override"):
        runner.WindowProblem.residual(problem, None, history_atol=1e-10)


def _target_fixture(tmp_path):
    key = state_key("synthetic", 20, 4)
    previous = predecessor_key("synthetic", 20, 4)
    mesh_digest = "a" * 64
    sources = {}
    for name in ("source_checkpoint", "predecessor_checkpoint", "native_residual_evidence", "checkpoint_readback_evidence"):
        path = tmp_path / name
        path.write_bytes(name.encode())
        sources[name] = dict(path=str(path), sha256=sha256(path))
    arrays = {name: np.zeros((2,) if name in {"u", "v", "d", "old_damage"} else (1, 4), dtype=np.float64)
              for name in scorer._FIELDS}
    arrays["f_solve"][:] = arrays["f_commit"][:] = 1.
    snapshot = tmp_path / "target.npz"
    np.savez(snapshot, **arrays, state_key_json=json.dumps(key), predecessor_key_json=json.dumps(previous),
             ordered_mesh_sha256_f32_i64=mesh_digest,
             source_checkpoint_sha256=sources["source_checkpoint"]["sha256"],
             predecessor_checkpoint_sha256=sources["predecessor_checkpoint"]["sha256"])
    admission = tmp_path / "admission.json"
    admission.write_text(json.dumps(dict(schema="s04_e036_target_admission_v1", accepted=True,
        solver_policy=dict(u_tol=1e-6,joint_tol=4e-4),
        native_residual_checked=True, checkpoint_readback_verified=True, state_key=key,
        predecessor_key=previous, snapshot_sha256=sha256(snapshot),
        ordered_mesh_sha256_f32_i64=mesh_digest, **sources)))
    spec = {name: dict(path=str(path), sha256=sha256(path)) for name, path in
            (("snapshot", snapshot), ("admission", admission))}
    expected = {name: torch.from_numpy(arrays[source]) for name, source in
                (("damage", "old_damage"), ("history", "old_history"), ("active_driver", "old_active_driver"))}
    return spec, key, sources["predecessor_checkpoint"]["sha256"], expected


@pytest.mark.parametrize("fresh_history_error,accepted", [(0., True), (5e-11, True), (5e-8, False)])
def test_target_replay_uses_native_history_tolerance_not_pidl_tolerance(tmp_path, fresh_history_error, accepted):
    spec, key, predecessor_sha, old = _target_fixture(tmp_path)
    calls = []
    def residual(field, **policy):
        calls.append(policy)
        return lambda context: {"accepted": fresh_history_error <= policy["history_atol"]}
    problem = SimpleNamespace(x=[0, 1], cells=[0], common={"ordered_mesh_sha256_f32_i64": "a" * 64},
                              device=torch.device("cpu"), residual=residual)
    kwargs = dict(expected_predecessor_sha256=predecessor_sha, expected_old=old)
    if accepted:
        _, receipt = scorer.load_target(spec, tmp_path, key, problem, **kwargs)
        assert receipt["history_atol"] == 1e-10 and receipt["history_rtol"] == 0.
    else:
        with pytest.raises(ValueError, match="failed fresh physical"):
            scorer.load_target(spec, tmp_path, key, problem, **kwargs)
    assert calls == [dict(history_atol=1e-10, history_rtol=0.)]


def test_current_step_equal_work_can_have_different_window_work():
    first, second = optimizer_work(400, 200), optimizer_work(400, 600)
    report = scorer.work_comparison(first, second)
    assert report["current_step_equal_work"] is True
    assert report["cumulative_window_equal_work"] is False
    assert scorer._verified_work(first, 400, 200) == first
    with pytest.raises(ValueError, match="optimizer work"):
        scorer._verified_work(first, 400, 600)
    with pytest.raises(ValueError, match="predecessor work"):
        scorer._verified_work(first, 400, None)


def test_equal_cumulative_work_does_not_imply_current_step_equal_work():
    report = scorer.work_comparison(optimizer_work(200, 400), optimizer_work(400, 200))
    assert report["current_step_equal_work"] is False
    assert report["cumulative_window_equal_work"] is True


def _snapshot_fixture(tmp_path):
    source = tmp_path / "source" / "example.py"
    source.parent.mkdir()
    source.write_text("# synthetic provenance fixture; never executed\n")
    files = {"source/example.py": sha256(source)}
    snapshot = dict(schema="s04_e036_source_snapshot_v1", source_commit="a" * 40, files=files)
    (tmp_path / "source_snapshot.json").write_text(json.dumps(snapshot))
    return files, source


def test_standalone_snapshot_is_verified_without_git(tmp_path):
    files, _ = _snapshot_fixture(tmp_path)
    receipt = runner.source_provenance(tmp_path, files)
    assert receipt["source_kind"] == "standalone_snapshot"
    assert receipt["source_commit"] == "a" * 40
    assert receipt["git_head"] is None


def test_snapshot_rejects_runtime_drift_unlisted_module_and_missing_lock(tmp_path):
    files, source = _snapshot_fixture(tmp_path)
    with pytest.raises(ValueError, match="complete implementation lock"):
        runner.source_provenance(tmp_path, dict(files, missing="b" * 64))
    unlisted = source.with_name("added.py")
    unlisted.write_text("# unlisted fixture\n")
    with pytest.raises(ValueError, match="unlocked executable"):
        runner.source_provenance(tmp_path, files)
    unlisted.unlink()
    source.write_text("# changed fixture\n")
    with pytest.raises(ValueError, match="file mismatch"):
        runner.source_provenance(tmp_path, files)


def test_absent_git_never_silently_discards_source_provenance(tmp_path):
    with pytest.raises(ValueError, match="own Git checkout"):
        runner.source_provenance(tmp_path, {})


def _tightening_fixture():
    standard=dict(u_tol=1e-6,joint_tol=4e-4);tight=dict(u_tol=1e-8,joint_tol=4e-6)
    spec=dict(state_slot='c83/s4',target={},standard_policy=standard,tightened_policy=tight)
    target=dict(old_damage=torch.zeros(2,dtype=torch.float64),old_history=torch.zeros((1,4),dtype=torch.float64),
                old_active_driver=torch.zeros((1,4),dtype=torch.float64),
                predecessor_source_sha256='a'*64,native_solver_policy=standard)
    return spec,target


@pytest.mark.parametrize('cycle,substep',[(1,2),(1,4),(83,2),(83,4)])
def test_d3_tightening_is_state_specific_same_native_predecessor_not_general_floor(monkeypatch,cycle,substep):
    spec,target=_tightening_fixture();seen={}
    spec['state_slot']=f'c{cycle}/s{substep}'
    def load(spec_,root,key,problem,**kwargs):
        seen.update(kwargs)
        return {},dict(native_solver_policy=spec['tightened_policy'],physical_replay=dict(metrics={
            'u_residual_l2':1e-9,'phase_box_kkt_l2':1e-6}))
    monkeypatch.setattr(scorer,'load_target',load)
    monkeypatch.setattr(scorer,'target_readout',lambda *_:{})
    monkeypatch.setattr(scorer,'physical_gap',lambda *_:{'synthetic_fixture':True})
    monkeypatch.setattr(scorer,'primitive_gap',lambda *_:{'J':0.})
    result=scorer.tightening_readout(spec,Path('.'),state_key('synthetic',cycle,substep),None,target,None,{})
    assert result['status']=='verified_same_predecessor_sensitivity'
    assert seen['expected_predecessor_sha256']=='a'*64
    assert seen['expected_old']['damage'] is target['old_damage']
    assert 'not an error bound' in result['scope']
    with pytest.raises(ValueError,match='another state'):
        scorer.tightening_readout(spec,Path('.'),state_key('synthetic',84-cycle,substep),None,target,None,{})


def test_reference_tightening_requires_exact_independent_four_slot_map():
    empty={slot:None for slot in ('c1/s2','c1/s4','c83/s2','c83/s4')}
    assert scorer.tightening_map(empty)==empty
    spec,_=_tightening_fixture()
    declared=dict(empty,**{'c83/s4':spec})
    assert scorer.tightening_map(declared)==declared
    for invalid in (None,spec,dict(empty,extra=None),{'c83/s4':spec}):
        with pytest.raises(ValueError,match='exactly four'):
            scorer.tightening_map(invalid)
    with pytest.raises(ValueError,match='slot differs'):
        scorer.tightening_map(dict(empty,**{'c1/s4':spec}))


def test_reference_tightening_does_not_choose_an_unplanned_tolerance():
    spec,target=_tightening_fixture()
    spec['tightened_policy']['u_tol']=1e-7
    with pytest.raises(ValueError,match='exact predeclared'):
        scorer.tightening_readout(spec,Path('.'),state_key('synthetic',83,4),None,target,None,{})


@pytest.mark.parametrize('failure',['solver_policy','fresh_residual'])
def test_tightening_needs_actual_stricter_run_policy_and_fresh_residual(monkeypatch,failure):
    spec,target=_tightening_fixture()
    receipt=dict(native_solver_policy=(spec['standard_policy'] if failure=='solver_policy' else spec['tightened_policy']),
        physical_replay=dict(metrics={'u_residual_l2':(1e-7 if failure=='fresh_residual' else 1e-9),
                                       'phase_box_kkt_l2':1e-6}))
    monkeypatch.setattr(scorer,'load_target',lambda *args,**kwargs:({},receipt))
    with pytest.raises(ValueError):
        scorer.tightening_readout(spec,Path('.'),state_key('synthetic',83,4),None,target,None,{})


@pytest.mark.parametrize('policy',[None,{'u_tol':1e-7,'joint_tol':4e-5}])
def test_target_requires_predeclared_actual_solver_policy(tmp_path,policy):
    spec,key,predecessor_sha,old=_target_fixture(tmp_path)
    admission=Path(spec['admission']['path']);doc=json.loads(admission.read_text())
    doc['solver_policy']=policy;admission.write_text(json.dumps(doc));spec['admission']['sha256']=sha256(admission)
    with pytest.raises(ValueError,match='solver_policy'):
        scorer.load_target(spec,tmp_path,key,None,expected_predecessor_sha256=predecessor_sha,expected_old=old)


@pytest.mark.parametrize('consistent',[True,False])
def test_rejected_snapshot_keeps_physical_diagnostics_without_accepted_improvement(tmp_path,monkeypatch,consistent):
    step=tmp_path/'s4';folder=step/'snapshots';folder.mkdir(parents=True)
    key=state_key('synthetic',20,4)
    fields=dict(u=torch.zeros(2),v=torch.zeros(2),d=torch.zeros(2),active_driver=torch.zeros((1,4)),
                displacement=torch.tensor([key['displacement']]))
    old=dict(damage=torch.zeros(2),history=torch.zeros((1,4)),active_driver=torch.zeros((1,4)))
    context=dict(fields,old_damage=old['damage'],old_history=old['history'],old_active_driver=old['active_driver'],
        trial_history=torch.zeros((1,4)),f_solve=torch.ones((1,4)),f_commit=torch.ones((1,4)),state_token='fixture')
    record=dict(accepted=False,residual_accepted=False,f_converged=True)
    counts=optimizer_work(200,0)
    payload=dict(event=dict(event='outer',context=context,record=record),state_key=key,common_problem={},arm='P1',
                 updates=200,optimizer_work=counts,network_state={},
                 objective_precision=runner.objective_precision_record(old,context['f_solve']))
    torch.save(payload,folder/'outer.pt')
    (step/'snapshot_index.json').write_text(json.dumps([dict(event='outer',file='outer.pt',updates=200,optimizer_work=counts)]))
    receipt=dict(accepted=False,fresh_current_state=True,state_token='fixture',metrics=dict(fresh_history_consistent=consistent,
        u_residual_l2=1.,phase_box_kkt_l2=2.))
    problem=SimpleNamespace(common={},device=torch.device('cpu'),field=lambda *_:None,state=lambda _:fields,
                            residual=lambda _:lambda _:receipt)
    monkeypatch.setattr(scorer,'native_readout',lambda *args:dict(synthetic=True))
    monkeypatch.setattr(scorer,'physical_gap',lambda *args:dict(native_gp_errors={'raw':{'absolute_rms':.5}}))
    result,errors=scorer._diagnostic_snapshots(step,key,'P1',problem,old,0,{})
    if consistent:
        assert not errors and result[200]['accepted_comparison'] is False
        assert result[200]['fresh_acceptance']['accepted'] is False
        assert result[200]['saved_controller_record']==record
        assert result[200]['physical']['native_gp_errors']['raw']['absolute_rms']==.5
    else:
        assert not result and 'history is not reproduced' in errors[0]['reason']


def test_old_state_precision_is_preserved_and_loss_cast_is_explicit(monkeypatch):
    native=np.array([.123456789123,.234567891234],dtype=np.float64)
    arrays=dict(damage=native,history=np.full((1,4),.6123456789123),active_driver=np.full((1,4),.023456789123),
                u=np.zeros(2),v=np.zeros(2))
    p=SimpleNamespace(device=torch.device('cpu'),native_x=torch.tensor([[0.,0.],[0.,1.]],dtype=torch.float64),
        cells=torch.zeros((1,4),dtype=torch.long),native_area=torch.ones(1),mat=None,model=None,
        common={'fixed_damage_nodes_zero_based':[]},fatigue={'history_driver_reduction':{}})
    monkeypatch.setattr(runner,'get_psi_plus_per_elem',lambda *args,**kwargs:torch.from_numpy(arrays['active_driver']))
    old=runner.WindowProblem.old_state(p,arrays,{'displacement':0.})
    for name in old:
        assert old[name].dtype==torch.float64
        np.testing.assert_array_equal(old[name].numpy(),arrays[name])
    f=torch.full((1,4),.6123456789123,dtype=torch.float64)
    record=runner.objective_precision_record(old,f)
    assert record['fields']['damage']['float32_roundtrip_maxdelta']>0
    assert record['fields']['f_solve']['float32_roundtrip_maxdelta']>0
    assert record['fields']['damage']['actually_cast_for_energy'] is True
    assert record['fields']['history']['actually_cast_for_energy'] is False
