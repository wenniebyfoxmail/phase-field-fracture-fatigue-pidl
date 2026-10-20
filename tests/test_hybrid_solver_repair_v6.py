"""Artificial Q4/algebraic/fault checks only; no project data or training."""
from dataclasses import asdict
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
from hybrid_coupled_acceleration import CouplingSettings,ProjectedAnderson
from hybrid_incremental import solve_step,StepFailure,NativeQ4Backend
from hybrid_mechanics import MechanicsWorkspace
from hybrid_history import trial_history
from test_hybrid_performance import fixture
from test_hybrid_incremental import AlgebraicBackend,state,settings,one_element


def setup():
    k,m=fixture();w=MechanicsWorkspace(k,m)
    bc=np.array([0,1,2,3,5,7]);v=np.array([0.,0.,0.,0.,.02,.02]);s=settings()
    u,info=w.solve(np.zeros(4),bc,v,s)
    return w,bc,v,s,u


def test_monotone_requires_real_strict_progress_not_half_reduction():
    p=CouplingSettings(mode='projected_anderson_monotone',max_rejections=3)
    assert p.trial_improves(6.81,9.88)
    assert not p.trial_improves(9.88,9.88) and not p.trial_improves(10.,9.88)
    assert not CouplingSettings(mode='projected_anderson').trial_improves(6.81,9.88)
    with pytest.raises(RuntimeError):p.trial_improves(np.nan,1.)


def test_rejection_does_not_permanently_disable_reaccumulated_history(monkeypatch):
    old=state();before=old.fingerprint();rows=[];real=ProjectedAnderson.propose;injected=[False]
    def first_bad(self):
        if len(self.history)>=2 and not injected[0]:
            injected[0]=True;self.proposals+=1
            return np.full(4,.95),dict(reason='artificial_bad_feasible_trial')
        return real(self)
    monkeypatch.setattr(ProjectedAnderson,'propose',first_bad)
    p=solve_step(AlgebraicBackend(),old,np.array([0]),np.array([0.]),next_load_id='unit',settings=settings(),
                 coupling=CouplingSettings(mode='projected_anderson_monotone',max_rejections=3),iteration_observer=rows.append)
    decisions=[r for r in rows if r['event']=='iteration_decision']
    rejected=next(r for r in decisions if r['rejection_reason'])
    assert rejected['next_guess']['reason']=='restored_baseline'
    assert 2<=p.certificate['coupling_work']['proposals']<=3
    assert old.fingerprint()==before and p.state.version==1


def test_recycled_current_residual_matches_direct_without_false_exact_key():
    w,bc,v,s,u=setup();old_key=w.factor_key;old_factor=w.factor
    d=np.array([.12,.2,.3,.05])
    recycled,info=w.solve(d,bc,v,s,initial_u=u,strategy='recycled_gmres')
    direct,_=MechanicsWorkspace(w.kin,w.material).solve(d,bc,v,s,initial_u=u)
    assert np.max(abs(recycled-direct))<1e-10
    assert info['krylov_successes']>=1 and info['factorizations']==0
    assert info['krylov_matvecs']>0 and info['preconditioner_applications']>0
    assert info['krylov_last_true_residual']<=info['krylov_last_target']
    assert w.factor_key==old_key and w.factor is old_factor
    cert=w.certify_factor(d,recycled,bc)
    assert cert['current_matrix_pivot_qualified'] and not cert['current_exact_factor_reused']
    assert w.factor_key!=old_key


@pytest.mark.parametrize('code',[0,4])
def test_gmres_bad_true_residual_or_nonconvergence_refactors_once(monkeypatch,code):
    import hybrid_mechanics as hm
    w,bc,v,s,u=setup()
    monkeypatch.setattr(hm,'gmres',lambda A,b,**kwargs:(np.zeros_like(b),code))
    result,info=w.solve(np.full(4,.2),bc,v,s,initial_u=u,strategy='recycled_gmres')
    assert info['krylov_fallbacks']==1 and info['factorizations']==1
    assert np.isfinite(result).all()


def test_nonfinite_krylov_is_failure_not_refactor_rescue(monkeypatch):
    import hybrid_mechanics as hm
    w,bc,v,s,u=setup();old=w.factor_key
    monkeypatch.setattr(hm,'gmres',lambda A,b,**kwargs:(np.full_like(b,np.nan),0))
    with pytest.raises(RuntimeError,match='nonfinite Krylov'):
        w.solve(np.full(4,.2),bc,v,s,initial_u=u,strategy='recycled_gmres')
    assert w.factor_key==old


def test_changed_free_domain_never_preconditions_with_incompatible_lu(monkeypatch):
    import hybrid_mechanics as hm
    w,bc,v,s,u=setup()
    monkeypatch.setattr(hm,'gmres',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('incompatible preconditioner')))
    newbc=np.array([0,1,2,3,4,5,7]);newv=np.array([0,0,0,0,0,.02,.02])
    _,info=w.solve(np.full(4,.2),newbc,newv,s,initial_u=u,strategy='recycled_gmres')
    assert info['krylov_attempts']==0 and info['factorizations']>=1


def test_consistent_singular_current_matrix_cannot_borrow_old_healthy_pivots(monkeypatch):
    w,bc,v,s,u=setup()
    assert w.pivot_ratio(w.factor)>1e-14
    matrix=sparse.eye(8,format='csr').tolil();matrix[6,6]=0.
    monkeypatch.setattr(w,'assemble',lambda d,u:matrix.tocsr())
    with pytest.raises(RuntimeError):w.certify_factor(np.zeros(4),u,bc)


def test_final_factor_failure_prevents_proposal_and_history_advance(monkeypatch):
    b=NativeQ4Backend(one_element(),np.zeros(4,bool))
    from hybrid_history import AcceptedState
    old=AcceptedState(np.zeros(8),np.zeros(4),np.zeros((1,4)),np.zeros((1,4)),np.ones((1,4)),np.zeros((1,4)),0,0,b.mesh_id,b.physics_id,'unit')
    before=old.fingerprint()
    monkeypatch.setattr(b.mechanics_workspace,'certify_factor',lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('current matrix singular')))
    with pytest.raises(StepFailure,match='current matrix singular'):
        solve_step(b,old,np.array([0,1,2,3,5,7]),np.array([0,0,0,0,.001,.001]),next_load_id='unit',settings=settings(),
                   coupling=CouplingSettings(mode='projected_anderson_monotone',mechanics_solver='recycled_gmres',max_rejections=3))
    assert old.fingerprint()==before and old.version==0


def test_monotone_fatigue_below_one_remains_single_trial_from_accepted_state(tmp_path):
    class Fatigue(AlgebraicBackend):
        def trial(self,old,u,d):
            psi=np.full((1,4),u[0])
            return psi,trial_history(old,np.full((1,4),d[0]),psi,alpha_t=.05,power=2.)
    old=state();before=old.fingerprint();coupling=CouplingSettings(mode='projected_anderson_monotone',max_rejections=3)
    p=solve_step(Fatigue(),old,np.array([0]),np.array([0.]),next_load_id='unit',settings=settings(),coupling=coupling)
    assert p.state.fatigue.max()<1. and old.fingerprint()==before
    assert np.allclose(p.state.accumulated,(1-p.state.damage[0])**2*p.state.damage[0])
    assert np.max(abs(p.field_evidence['f_solve_gp']-p.state.fatigue))<=settings().fatigue_tolerance
    from hybrid_state_contract import bind_proposal,step_context
    from hybrid_transaction import StateStore
    from test_hybrid_state_contract import context_inputs
    c,s,dofs,bc=context_inputs();c['coupling']=asdict(coupling)
    p=bind_proposal(p,step_context(c,s,p.state,1,dofs,bc))
    store=StateStore(tmp_path/'state.npz');store.initialize(old,context=step_context(c,s,old,0,dofs,bc));store.commit(p)
    accepted,_=store.load();assert accepted.version==1 and accepted.fingerprint()==p.state.fingerprint()


def test_v6_card_changes_only_engineering_limit_not_physical_thresholds():
    from copy import deepcopy
    from test_hybrid_producer import card
    from run_hybrid_producer import validate_card
    c=card();c['numerical_solver_revision']='coupled-recycle-v6';c['solver']['wall_seconds']=300.
    c['coupling']=asdict(CouplingSettings(mode='projected_anderson_monotone',mechanics_solver='recycled_gmres',max_rejections=3))
    validate_card(c)
    bad=deepcopy(c);bad['solver']['force_tolerance']=1e-7
    with pytest.raises(ValueError):validate_card(bad)
    bad=deepcopy(c);bad['coupling']['max_proposals']=5
    with pytest.raises(ValueError):validate_card(bad)
    bad=deepcopy(c);bad.pop('numerical_solver_revision')
    with pytest.raises(ValueError):validate_card(bad)
    bad=deepcopy(c);bad['phases'][1]['coupling']={}
    with pytest.raises(ValueError):validate_card(bad)


def test300_second_deadline_not_reset_by_iteration_evidence(monkeypatch):
    import hybrid_incremental as hi
    clock=[0.];monkeypatch.setattr(hi,'perf_counter',lambda:clock[0])
    def delayed(record):clock[0]=300.01
    old=state();identity=old.fingerprint()
    with pytest.raises(StepFailure,match='wall cap'):
        solve_step(AlgebraicBackend(),old,np.array([0]),np.array([0.]),next_load_id='unit',
            settings=settings(wall_seconds=300.),coupling=CouplingSettings(mode='projected_anderson_monotone',max_rejections=3),iteration_observer=delayed)
    assert old.fingerprint()==identity and old.version==0
