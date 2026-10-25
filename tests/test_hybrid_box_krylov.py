"""Small given-matrix controls only; no project fields/native FEM/large saved J."""
import itertools
import numpy as np
from scipy import sparse
import pytest
from hybrid_box_residual_subproblem import Budget,Model,solve_box_model
from hybrid_box_krylov import face_mask,boundary_step


def run_case(J,F,*,steps=8,limit=100,observe=None,solver='active_face_cg'):
    J=np.asarray(J,float);F=np.asarray(F,float);n=J.shape[1]
    m=Model(sparse.csc_matrix(J),F,np.ones(len(F)),np.ones(n),Budget(actions=limit))
    base=dict(u=np.zeros(2),d=np.full(n-1,.4));free=np.array([1]);dofs=np.array([0]);values=np.zeros(1);lower=np.full(n-1,.2);crack=np.zeros(n-1,bool)
    pn=np.linalg.lstsq(J,-F,rcond=None)[0]
    p=solve_box_model(m,base,free,dofs,values,lower,crack,.1,pn,
        stage_observer=observe,solver=solver,krylov_steps=steps)
    return p,m,pn


def box_oracle(J,F):
    """Independent exhaustive face enumeration for n<=4, given quadratic only."""
    best=np.inf;bestx=None;n=J.shape[1]
    for code in itertools.product([-1,0,1],repeat=n):
        fixed=np.array(code)!=0;free=~fixed;x=.1*np.array(code,dtype=float)
        if np.any(free):x[free]=np.linalg.lstsq(J[:,free],-F-J[:,fixed]@x[fixed],rcond=None)[0]
        if np.all(abs(x)<=.1+1e-14):
            q=.5*sum((F+J@x)**2)
            if q<best:best=q;bestx=x.copy()
    return best,bestx


def test_constrained_coupled_step_beats_bad_clipped_Newton_and_PG2():
    J=np.array([[1.,10.],[0.,1.]]);F=np.array([0.,-1.]);events=[]
    def observe(name,p,best,meta):
        events.append((name,None if p is None else p['pred_lower']if 'pred_lower'in p else None,meta.copy()))
        if name=='Krylov_complete'and meta['retained_as_best']:assert np.array_equal(best['p'],p['p'])
    p,m,pn=run_case(J,F,observe=observe);old,_,_=run_case(J,F,solver='pg2_optional');opt,x=box_oracle(J,F)
    assert .5*sum((F+J@np.clip(pn,-.1,.1))**2)>.5*sum(F**2)
    assert p['model_value']<old['model_value']and p['model_value']-opt<1e-12
    assert p['actual_TR_norm']<=.1 and p['pred_lower']>=p['cauchy_pred_lower']>0
    assert m.budget.used<=100 and m.budget.updates<=16
    assert any(x[2].get('boundary_truncated')for x in events)
    assert p['subproblem_optimality_certified']is False


@pytest.mark.parametrize('J,F',[
 ([[2.,.2],[.3,1.]],[-.02,.03]),
 ([[1.,2.,0.],[0.,1.,1.],[.1,0.,2.]],[.1,-.5,.2]),
 ([[1.,1.,0.],[0.,0.,1.]],[-.3,.4]),
])
def test_small_SPD_and_semidefinite_models_are_feasible_and_Cauchy_protected(J,F):
    J=np.array(J);F=np.array(F);p,m,_=run_case(J,F);opt,_=box_oracle(J,F)
    assert p['model_value']>=opt-1e-14 and p['actual_TR_norm']<=.1
    assert p['pred_lower']>=p['cauchy_pred_lower']and np.all(p['d']>=.2)and np.all(p['d']<=1)
    assert m.budget.used<=100 and m.budget.updates<=16


def test_original_bound_active_components_release_for_inward_gradient():
    lo=np.array([0.,0.,1.,0.]);hi=np.array([1.,1.,1.,1.]);x=np.array([0.,1.,1.,.5]);g=np.array([-2.,3.,-4.,1.])
    assert np.array_equal(face_mask(x,g,lo,hi),[True,True,False,True])
    assert np.array_equal(face_mask(x,-g,lo,hi),[False,False,False,True])
    assert boundary_step(np.array([.2,.8]),np.array([1.,-2.]),np.ones(2),np.zeros(2),np.ones(2))==.4


def test_action_reserve_returns_certified_best_without_overrun():
    p,m,_=run_case([[1.,10.],[0.,1.]],[0.,-1.],limit=30)
    assert p['krylov_status']=='action_reserve'and m.budget.used<=30
    assert p['pred_lower']>=p['cauchy_pred_lower']>0 and p['krylov_iterations']==0


@pytest.mark.parametrize('failure',[RuntimeError('invalid range'),OSError('failed IO')])
def test_true_refinement_errors_propagate(failure,monkeypatch):
    monkeypatch.setattr(Model,'scaled_action',lambda *a:(_ for _ in ()).throw(failure))
    with pytest.raises(type(failure),match=str(failure)):run_case([[1.,10.],[0.,1.]],[0.,-1.])


def test_stage_IO_failure_stops_before_optional_candidate():
    stages=[]
    def observe(name,*args):
        stages.append(name)
        if name=='Krylov_complete':raise OSError('stage persistence')
    with pytest.raises(OSError,match='stage persistence'):run_case([[1.,10.],[0.,1.]],[0.,-1.],observe=observe)
    assert not any(x.startswith('optional_Newton')for x in stages)


def test_invalid_solver_and_krylov_caps_and_policy_identity():
    from dataclasses import asdict
    from hybrid_coupled_acceleration import CouplingSettings
    from hybrid_incremental import digest_config
    with pytest.raises(ValueError):run_case([[1.,0.],[0.,1.]],[.1,.1],steps=9)
    with pytest.raises(ValueError):CouplingSettings(box_subproblem_solver='unknown')
    a=CouplingSettings(mode='box_residual_trust');b=CouplingSettings(mode='box_residual_trust',box_subproblem_solver='active_face_cg')
    assert digest_config(asdict(a))!=digest_config(asdict(b))


def test_no_certified_curvature_returns_best_not_root(monkeypatch):
    monkeypatch.setattr(Model,'scaled_action',lambda self,v:np.zeros(len(self.F)))
    p,m,_=run_case([[1.,10.],[0.,1.]],[0.,-1.])
    assert p['krylov_status']=='computed_curvature_unresolved'
    assert p['pred_lower']>=p['cauchy_pred_lower']>0 and not p['subproblem_optimality_certified']


def test_shared_budget_not_reset_between_radius_attempts():
    J=np.array([[1.,10.],[0.,1.]]);F=np.array([0.,-1.]);p,m,pn=run_case(J,F);used=m.budget.used;updates=m.budget.updates
    base=dict(u=np.zeros(2),d=np.array([.4]))
    try:
        solve_box_model(m,base,np.array([1]),np.array([0]),np.zeros(1),np.array([.2]),np.zeros(1,bool),.025,pn,solver='active_face_cg')
    except RuntimeError as e:assert 'budget'in str(e)
    assert used<=m.budget.used<=100 and updates<=m.budget.updates<=16


def test_all_refinement_stages_and_typed_failure_use_latest_best(monkeypatch):
    import hybrid_box_residual_subproblem as sub
    from hybrid_representable_box import CandidateUncertified
    real=sub.feasible_candidate;calls=[];last=[None];cauchy=[None];failed=[]
    def candidate(*a,**kw):
        calls.append(1)
        if len(calls)==3:raise CandidateUncertified('finite qualification',dict(exact_comparisons=0,exact_CPU_seconds=0.),dict(candidate_x=np.zeros(2)))
        return real(*a,**kw)
    def observe(name,p,best,meta):
        if name=='Cauchy_certified':cauchy[0]=best['p'].copy()
        if name=='Krylov_complete'and meta['retained_as_best']:last[0]=best['p'].copy()
        if name in ['Krylov_gradient_start','Krylov_start','Krylov_unqualified','Krylov_end']and last[0]is not None:
            assert np.array_equal(best['p'],last[0])
        if name=='Krylov_unqualified':failed.append(best['p'].copy())
    monkeypatch.setattr(sub,'feasible_candidate',candidate)
    with pytest.raises(CandidateUncertified):run_case([[1.,10.],[0.,1.]],[0.,-1.],observe=observe)
    assert failed and last[0]is not None and not np.array_equal(cauchy[0],failed[0])


def test_normal_end_stage_uses_final_improved_best():
    last=[None];end=[None]
    def observe(name,p,best,meta):
        if name=='Krylov_complete'and meta['retained_as_best']:last[0]=best['p'].copy()
        if name=='Krylov_end':end[0]=best['p'].copy()
    run_case([[1.,10.],[0.,1.]],[0.,-1.],observe=observe)
    assert last[0]is not None and np.array_equal(last[0],end[0])


def near_boundary_case(solver,observe=None):
    # Cauchy lands just inside the damage lower bound. The next gradient
    # still points outwards there, while the displacement remains free.
    J=sparse.csc_matrix([[1.,-1.],[0.,2.]])
    m=Model(J,np.array([.5,.55]),np.ones(2),np.ones(2),Budget())
    base=dict(u=np.zeros(2),d=np.array([.1]))
    p=solve_box_model(m,base,np.array([1]),np.array([0]),np.zeros(1),np.zeros(1),
        np.zeros(1,bool),.1,np.zeros(2),solver=solver,stage_observer=observe)
    return p,m


def test_projected_path_crosses_tiny_first_bound_without_freezing_other_components():
    before=[];after=[]
    old,_=near_boundary_case('active_face_cg',lambda n,p,b,m:before.append((n,m)))
    new,m=near_boundary_case('active_face_projected_cg',lambda n,p,b,m:after.append((n,m)))
    first=next(meta for name,meta in before if name=='Krylov_before_model')
    assert first['alpha_bound']<1e-12*first['alpha_cg']
    assert new['pred_lower']>old['pred_upper']
    assert new['model_value']<old['model_value'] and new['d'][0]>=0
    assert new['actual_TR_norm']<=.1 and new['pred_lower']>=new['cauchy_pred_lower']
    assert m.budget.used<=100 and m.budget.updates<=16
    assert any(meta.get('projected_path') for name,meta in after if name=='Krylov_complete')
    assert new['subproblem_optimality_certified']is False


def test_projected_retry_keeps_certified_best_and_shared_limits(monkeypatch):
    real=Model.evaluate;seen=[]
    def no_improvement(self,*a,**kw):
        result=real(self,*a,**kw);seen.append(result)
        if len(seen)>1:result.update(pred_lower=-1.,pred_upper=1.)
        return result
    monkeypatch.setattr(Model,'evaluate',no_improvement)
    p,m=near_boundary_case('active_face_projected_cg')
    assert np.array_equal(p['p'],seen[0]['p'])
    assert p['pred_lower']==p['cauchy_pred_lower']>0
    assert m.budget.used<=100 and m.budget.updates<=16 and len(seen)>2


def test_projected_path_has_distinct_policy_identity():
    from dataclasses import asdict
    from hybrid_coupled_acceleration import CouplingSettings
    from hybrid_incremental import digest_config
    a=CouplingSettings(mode='box_residual_trust',box_subproblem_solver='active_face_cg')
    b=CouplingSettings(mode='box_residual_trust',box_subproblem_solver='active_face_projected_cg')
    assert digest_config(asdict(a))!=digest_config(asdict(b))
