"""Algebraic contracts only: no project data, training or new FEM run."""
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest
from scipy import sparse
import torch

from hybrid_history import AcceptedState, trial_history, fatigue_factor
from hybrid_damage import NodalQP, assemble_nodal_qp, kkt_audit, solve_nodal_qp
from hybrid_incremental import NativeQ4Backend, SolverSettings, StepFailure, solve_step
from hybrid_transaction import StateStore, CommitUncertain
from hybrid_network import DamageGraphPredictor, FrozenGraphInterface, FEATURES, features_for, mesh_graph
from native_q4_damage_qp import build_native_q4_kinematics


def state(d=None):
    d = np.zeros(4) if d is None else d
    return AcceptedState(np.zeros(8), d, np.zeros((1,4)), np.zeros((1,4)),
                         np.ones((1,4)), np.array([17.]), 0, 0, "mesh", "physics", "initial")


def test_trial_idempotence_and_unloading_current_driver():
    old = state()
    q = trial_history(old, np.zeros((1,4)), np.full((1,4), 2.), alpha_t=.5, power=2)
    assert np.array_equal(q.accumulated, np.full((1,4), 2.))
    assert np.allclose(q.fatigue, np.full((1,4), .16), rtol=0., atol=1e-16)
    again = trial_history(old, np.zeros((1,4)), np.full((1,4), 2.), alpha_t=.5, power=2)
    assert np.array_equal(q.accumulated, again.accumulated)
    accepted = replace(old, accumulated=q.accumulated, driver=q.driver, fatigue=q.fatigue)
    unload = trial_history(accepted, np.zeros((1,4)), np.full((1,4), .1), alpha_t=.5, power=2)
    assert np.array_equal(unload.accumulated, q.accumulated)
    assert np.all(unload.driver == .1)
    with pytest.raises(ValueError):
        old.damage.setflags(write=True)
    with pytest.raises(ValueError):
        trial_history(replace(old, fatigue=np.zeros((1,4))), np.zeros((1,4)), np.ones((1,4)), alpha_t=.5,power=2)


def test_full_nodal_release_fixed_elimination_and_fresh_kkt():
    qp = NodalQP(sparse.eye(4,format="csc"), np.array([2., -2., -.6, 0.]),
                 np.array([.2, .3, .1, 1.]), np.ones(4), "algebraic")
    x, info = solve_nodal_qp(qp, np.ones(4), eps=1e-10,max_iter=10000,time_limit=1.)
    assert np.allclose(x, [.2,1.,.6,1.],atol=1e-9)
    assert x[-1] == 1.
    assert kkt_audit(qp,x,gradient_scale=1.,bound_tolerance=1e-9)["kkt_scaled_inf"] < 1e-8
    changed = replace(qp,linear=np.array([2.,-2.,-.8,0.]),identity="new-final-operator")
    assert kkt_audit(changed,x,gradient_scale=1.,bound_tolerance=1e-9)["kkt_scaled_inf"] > .19


def one_element():
    return build_native_q4_kinematics(np.array([[0,0],[1,0],[1,1],[0,1.]]),np.array([[0,1,2,3]]))


def test_nodal_assembly_energy_scale_and_old_lower():
    kin = one_element()
    lower=np.array([1.,.2,.1,.3]); crack=np.array([True,False,False,False])
    qp=assemble_nodal_qp(kin,np.full((1,4),.7),np.ones((1,4)),lower,crack,w1=1.,length_scale=.01)
    assert np.array_equal(qp.lower,lower)
    assert qp.lower[0] == qp.upper[0] == 1.
    bad=lower.copy();bad[0]=.9
    with pytest.raises(ValueError,match="precrack"):
        assemble_nodal_qp(kin,np.ones((1,4)),np.ones((1,4)),bad,crack,w1=1.,length_scale=.01)
    a=assemble_nodal_qp(kin,np.full((1,4),.7),np.ones((1,4)),lower,crack,w1=1.,length_scale=.01,thickness=3.)
    assert np.allclose(a.hessian.toarray(),3*qp.hessian.toarray())
    assert np.allclose(a.linear,3*qp.linear)


class AlgebraicBackend:
    # Coupled fixed point d = .2 + .5*u, u=d, solution d=.4.
    crack=np.zeros(4,bool)
    def validate_state(self, old):
        pass
    def mechanics(self,d,dofs,values,settings):
        return np.repeat(d,2), {"iterations":1}
    def trial(self,old,u,d):
        psi=np.full((1,4),u[0])
        q=trial_history(old,np.full((1,4),d[0]),psi,alpha_t=10.,power=2.)
        return psi,q
    def damage_problem(self,psi,f,old):
        target=.2+.5*psi[0,0]
        return NodalQP(sparse.eye(4,format="csc"),np.full(4,-target),old.damage,np.ones(4),str(target))
    def force_audit(self,u,d,dofs,values,settings):
        return dict(force_inf=0.,force_l2=0.,force_scaled=0.,boundary_inf=0.)


def settings(**kwargs):
    return SolverSettings(force_scale=1.,damage_gradient_scale=1.,**kwargs)


def proposal(**kwargs):
    return solve_step(AlgebraicBackend(),state(),np.array([0]),np.array([0.]),
                      next_load_id="next",settings=settings(),**kwargs)


def test_coupled_acceptance_is_fresh_and_history_not_inner_accumulated():
    old=state(); before=old.fingerprint()
    p=solve_step(AlgebraicBackend(),old,np.array([0]),np.array([0.]),next_load_id="next",settings=settings())
    assert np.allclose(p.state.damage,.4,atol=3e-7)
    assert p.certificate["outer"] > 10
    assert old.fingerprint()==before and old.version==0 and p.state.version==1
    # history uses FINAL field once, not the sum of >10 iterative trials.
    assert np.allclose(p.state.accumulated,(1-p.state.damage[0])**2*p.state.damage[0])
    assert p.certificate["damage"]["kkt_scaled_inf"] < 1e-7
    assert sum(w["kind"]=="fresh_final_damage_assembly" for w in p.work)==p.certificate["outer"]


def test_cap_failure_and_invalid_nn_fallback_do_not_advance_state():
    old=state()
    with pytest.raises(StepFailure,match="iteration cap") as err:
        solve_step(AlgebraicBackend(),old,np.array([0]),np.array([0.]),next_load_id="next",settings=settings(max_outer=1))
    assert old.version==0 and err.value.work
    class Bad:
        model_id="bad"
        def predict(self,*args):return np.full(4,np.nan)
    p=proposal(predictor=Bad())
    assert any(w["kind"]=="initial_guess_fallback" for w in p.work)
    assert p.certificate['model_id']=='NN_OFF'
    assert p.certificate['attempted_model_id']=='bad'
    assert p.certificate['initialization_source']=='classical_fallback'


def test_transaction_single_commit_stale_reject_restart_and_write_failure(tmp_path,monkeypatch):
    import hybrid_transaction as tx
    store=StateStore(tmp_path/"accepted.npz")
    store.initialize(state())
    p=proposal(); original=store.load()[0].fingerprint()
    real_replace=tx.os.replace
    def fail(*args):raise OSError("disk fault")
    monkeypatch.setattr(tx.os,"replace",fail)
    with pytest.raises(OSError,match="disk fault"):store.commit(p)
    assert store.load()[0].fingerprint()==original
    monkeypatch.setattr(tx.os,"replace",real_replace)
    store.commit(p)
    restored,meta=StateStore(store.path).load()
    assert restored.fingerprint()==p.state.fingerprint() and meta["certificate"]["passed"]
    with pytest.raises(RuntimeError,match="stale"):store.commit(p)
    assert restored.version==1


def test_post_replace_fsync_fault_is_uncertain_not_false_rollback(tmp_path,monkeypatch):
    import hybrid_transaction as tx
    store=StateStore(tmp_path/"accepted.npz");store.initialize(state());p=proposal()
    fsync=tx.os.fsync; calls=[]
    def fault(fd):
        calls.append(fd)
        if len(calls)==2:raise OSError("directory fault")
        return fsync(fd)
    monkeypatch.setattr(tx.os,"fsync",fault)
    with pytest.raises(CommitUncertain):store.commit(p)
    assert store.load()[0].fingerprint()==p.state.fingerprint()


def test_features_graph_shapes_and_random_model_is_refused():
    kin=one_element();backend=NativeQ4Backend(kin,np.zeros(4,bool))
    old=replace(state(),mesh_id=backend.mesh_id,physics_id=backend.physics_id)
    x=features_for(backend,old,np.zeros(8),np.zeros((1,4)),np.array([0,1]),np.array([0.,.1]))
    assert x.shape==(4,len(FEATURES)) and np.isfinite(x).all()
    edge,mapping,coarse=mesh_graph(kin.points,kin.cells,backend.length_scale)
    model=DamageGraphPredictor(len(FEATURES))
    # Structural forward only, no optimizer/backward/model or scientific data.
    with torch.inference_mode():out=model(torch.tensor(x,dtype=torch.float32),edge,mapping,coarse)
    assert out.shape==(4,) and torch.isfinite(out).all()
    with pytest.raises(ValueError,match="untrained"):
        FrozenGraphInterface(model,backend,manifest={},mean=np.zeros(len(FEATURES)),scale=np.ones(len(FEATURES)))


def test_label_metadata_missing_contract_cannot_be_qualified():
    from tools.audit_hybrid_labels import qualify_transition
    result=qualify_transition({"domain":"nodal-K-v1","load_index_in":0,"load_index_out":1},
                              physics_id="p",mesh_id="m",settings_id="s")
    assert not result['metadata_eligible']
    assert 'input_accepted_verified' in result['missing_or_mismatched']
    assert not result['array_qualification_performed_here']


@pytest.mark.parametrize('identity',[None,'',17])
def test_unidentified_predictor_is_rejected_before_any_mechanics(identity):
    class Unidentified:
        model_id=identity
        def predict(self,*args):raise AssertionError('must not run')
    with pytest.raises(StepFailure,match='model_id') as err:
        proposal(predictor=Unidentified())
    assert not err.value.work


def test_predictor_receives_immutable_integer_dofs_and_receipt_binds_used_model():
    class Indexed:
        model_id='identified-unit-initializer'
        def predict(self,old,u,psi,load,dofs,values):
            assert dofs.dtype==np.int64 and not dofs.flags.writeable
            assert u[dofs].shape==values.shape
            return np.full(4,.1)
    p=proposal(predictor=Indexed())
    assert p.certificate['model_id']=='identified-unit-initializer'
    assert p.certificate['initialization_source']=='neural'
