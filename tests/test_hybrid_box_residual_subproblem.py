"""Artificial LS/model and one-element derivative checks, no project inputs."""
import numpy as np
import pytest
from scipy import sparse
from hybrid_box_residual_subproblem import (Budget,Model,freeze_variable_metric,
    solve_box_model,feasible_candidate,original_natural_jacobian,dot_bound)


def fixture(J=None,F=None,radius=.1):
    J=sparse.csc_matrix([[1.,2.],[.5,-1.]])if J is None else sparse.csc_matrix(J)
    F=np.array([.1,-.2])if F is None else np.asarray(F)
    w=np.array([.5,2.]);b=Budget();D=freeze_variable_metric(J,w,b)
    m=Model(J,F,w,D,b);base=dict(u=np.array([0.,.02]),d=np.array([.4]))
    return m,base,np.array([1]),np.array([0]),np.array([0.]),np.array([.2]),np.array([False]),radius


def test_feasible_Cauchy_lower_bound_and_bounded_improvement():
    m,base,free,dofs,values,lower,crack,radius=fixture()
    pn=np.linalg.solve(m.J.toarray(),-m.F)
    p=solve_box_model(m,base,free,dofs,values,lower,crack,radius,pn)
    true=np.longdouble(.5)*np.sum(np.asarray(m.r,dtype=np.longdouble)**2)-np.longdouble(.5)*np.sum((np.asarray(m.r,dtype=np.longdouble)+np.asarray(m.w,dtype=np.longdouble)*(np.asarray(m.J.toarray(),dtype=np.longdouble)@np.asarray(p['cauchy_p'],dtype=np.longdouble)))**2)
    assert true>=p['cauchy_required_bound']>0
    assert p['pred_lower']>=p['cauchy_pred_lower']and p['cauchy_model_lower_bound']>=p['cauchy_required_bound']
    assert p['actual_TR_norm']<=radius and p['d'][0]>=lower[0]and p['u'][0]==0
    assert m.budget.used<=100 and m.budget.updates<=16


def test_actual_step_inside_TR_after_rounding_and_precrack_fixed():
    base=dict(u=np.array([0.,.03]),d=np.array([.948720755500172,1.]))
    D=np.ones(3);radius=9.765625e-5
    y=np.array([radius,radius,-radius]);p=feasible_candidate(y,base,D,np.array([1]),np.array([0]),np.array([0.]),np.array([.8,1.]),np.array([False,True]),radius)
    assert np.max(abs(D*p['p']))<=radius
    assert p['d'][1]==1 and p['u'][0]==0
    assert p['inward_ulp_corrections']>0


def test_zero_projected_gradient_nonzero_F_is_not_a_root():
    m,base,free,dofs,values,lower,crack,radius=fixture([[1.,1.],[0.,0.]],[0.,1.])
    with pytest.raises(RuntimeError,match='zero projected model gradient'):
        solve_box_model(m,base,free,dofs,values,lower,crack,radius,np.zeros(2))
    assert m.q0>0


@pytest.mark.parametrize('bad',[0.,-1.,np.inf,np.nan,1e-320])
def test_invalid_positive_variable_metric_is_rejected(bad):
    with pytest.raises(RuntimeError):Model(sparse.eye(2,format='csc'),np.ones(2),np.ones(2),np.array([1.,bad]),Budget())


def test_underflow_is_explicit_stop_not_zero_gradient():
    with pytest.raises(RuntimeError,match='underflow'):
        freeze_variable_metric(sparse.eye(2,format='csc')*1e-200,np.ones(2),Budget())


def test_zero_metric_column_and_zero_J_cannot_be_used():
    with pytest.raises(RuntimeError):freeze_variable_metric(sparse.csc_matrix([[1.,0.],[0.,0.]]),np.ones(2),Budget())


def test_actions_and_updates_fail_before_exceeding_caps():
    b=Budget();b.action('J',88)
    assert b.used==100
    with pytest.raises(RuntimeError,match='action budget'):b.action('JT')
    for _ in range(16):b.update()
    with pytest.raises(RuntimeError,match='update budget'):b.update()
    with pytest.raises(ValueError):Budget(101,16)
    with pytest.raises(ValueError):Budget(100,17)


def test_sparse_J_JT_adjoint_and_complete_model_action():
    rng=np.random.default_rng(74);J=sparse.csc_matrix(rng.normal(size=(6,4)));w=np.linspace(.4,2.,6);D=np.linspace(.5,1.5,4);b=Budget();m=Model(J,rng.normal(size=6),w,D,b)
    v=rng.normal(size=4);z=rng.normal(size=6)
    mv=w*(J@(v/D));mtv=m.gradient(z)
    left,le=dot_bound(mv,z);right,re=dot_bound(v,mtv)
    assert abs(left-right)<=le+re
    e=m.evaluate(v/D)
    assert np.allclose(e['residual'],m.r+w*(J@(v/D)),rtol=0,atol=0)


@pytest.mark.parametrize('alpha',[10.,.005])
def test_original_natural_J_and_JT_from_native_nonzero_Ru_fatigue_branches(alpha):
    from test_hybrid_guarded_coupling import native_old
    from test_hybrid_incremental import settings
    from hybrid_coupled_block import block_direction
    from hybrid_coupled_acceleration import CouplingSettings
    from hybrid_joint_trust import model_residual
    b,old=native_old(alpha=alpha);d=np.array([.15,.2,.3,.12]);u=np.array([0.,0.,.03,.01,.04,.02,.01,.03]);dofs=np.array([0,1,2,3,5,7]);psi,q=b.trial(old,u,d);qp=b.damage_problem(psi,q.fatigue,old)
    dd,info,m=block_direction(b,old,dict(u=u,d=d,qp=qp,q=q),dofs,settings(),CouplingSettings(mode='box_residual_trust'),lambda k,f:f(),lambda:1.,lambda e:None,return_model=True)
    J=original_natural_jacobian(m,1.);p=np.linspace(-.01,.02,J.shape[1]);expected=np.r_[model_residual(m,p[:2],p[2:],1.)[0]-m['Ru'],model_residual(m,p[:2],p[2:],1.)[1]-m['F']]
    assert np.allclose(J@p,expected,atol=1e-17,rtol=1e-12)
    z=np.linspace(.02,-.03,J.shape[0]);a,ea=dot_bound(J@p,z);c,ec=dot_bound(p,J.T@z);assert abs(a-c)<=ea+ec
    assert np.linalg.norm(m['Ru'])>0 and info['passed']


def test_active_identity_release_and_fixed_damage_rows():
    m=dict(A=sparse.eye(1,format='csc'),B=sparse.csc_matrix([[1.,2.,3.]]),C=sparse.csc_matrix([[4.],[5.],[6.]]),D=sparse.diags([7.,8.,9.],format='csc'),inactive=np.array([True,False,False]))
    J=original_natural_jacobian(m,2.).toarray()
    assert np.array_equal(J[1],[2.,3.5,0.,0.])
    assert np.array_equal(J[2],[0.,0.,1.,0.])and np.array_equal(J[3],[0.,0.,0.,1.])


@pytest.mark.parametrize('fault',['pivot','physical','none'])
def test_box_route_original_final_QP_history_gate_and_no_trial_mechanics(monkeypatch,fault):
    import hybrid_joint_trust as jt
    from test_hybrid_joint_trust import controller
    from test_hybrid_incremental import settings
    from hybrid_incremental import solve_step,StepFailure
    from hybrid_coupled_acceleration import CouplingSettings
    b,old=controller(monkeypatch);original=jt.block_direction;rows=[];before=old.fingerprint()
    def add_rd(*a,**kw):
        dd,info,m=original(*a,**kw);m['Rd']=a[2]['qp'].hessian@a[2]['d']+a[2]['qp'].linear
        return dd,info,m
    monkeypatch.setattr(jt,'block_direction',add_rd)
    if fault=='pivot':monkeypatch.setattr(b.mechanics_workspace,'certify_factor',lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('bad original current pivot')))
    if fault=='physical':
        real=b.mechanics
        def bad(*a,**kw):
            u,i=real(*a,**kw)
            if b.mechanics_calls==2:u[1:]+=.1
            return u,i
        monkeypatch.setattr(b,'mechanics',bad)
    def run():return solve_step(b,old,np.array([0]),np.array([0.]),next_load_id='artificial',settings=settings(),coupling=CouplingSettings(mode='box_residual_trust'),iteration_observer=rows.append)
    if fault!='none':
        with pytest.raises(StepFailure):run()
    else:
        p=run();assert p.certificate['true_final_QP']and p.certificate['m_accept']<=1
        assert any(x['event']=='box_trial_before'and x['cauchy_required_bound']>0 for x in rows)
    assert b.mechanics_calls==2 and old.fingerprint()==before


def test_rejected_subproblem_reuses_one_outer_and_shared_finite_budget(monkeypatch):
    import hybrid_joint_trust as jt
    from test_hybrid_joint_trust import controller
    from test_hybrid_incremental import settings
    from hybrid_incremental import solve_step,StepFailure
    from hybrid_coupled_acceleration import CouplingSettings
    b,old=controller(monkeypatch);original=jt.block_direction;rows=[];calls=[]
    def block(*a,**kw):
        calls.append(1);dd,info,m=original(*a,**kw)
        m['Rd']=a[2]['qp'].hessian@a[2]['d']+a[2]['qp'].linear
        return dd,info,m
    monkeypatch.setattr(jt,'block_direction',block)
    real=jt.objective;n=[0]
    def reject(*a,**kw):
        n[0]+=1
        return real(*a,**kw)if n[0]==1 else (1e6,(5e5,5e5))
    monkeypatch.setattr(jt,'objective',reject)
    with pytest.raises(StepFailure,match='finite update budget|action budget|Cauchy'):
        solve_step(b,old,np.array([0]),np.array([0.]),next_load_id='artificial',settings=settings(),
            coupling=CouplingSettings(mode='box_residual_trust'),iteration_observer=rows.append)
    assert len(calls)==1 and b.mechanics_calls==1
    updates=[x['subproblem_updates']for x in rows if 'subproblem_updates'in x]
    assert updates==sorted(updates)and max(updates)<=16
    assert all(x['action_count_upper']<=100 for x in rows if 'action_count_upper'in x)
    assert any(x['event']=='work_point_rollback'for x in rows)


@pytest.mark.parametrize('scale',[1.1,1.2,1.3])
def test_exact_real_TR_bound_does_not_accept_rounded_product(scale):
    from fractions import Fraction as Q
    base=dict(u=np.zeros(2),d=np.array([.4]));D=np.array([scale,1.]);radius=.1
    c=feasible_candidate(np.array([radius,0.]),base,D,np.array([1]),np.array([0]),np.array([0.]),np.array([.2]),np.array([False]),radius)
    exact=Q(float(D[0]))*(Q(float(c['u'][1]))-Q(float(base['u'][1])))
    assert abs(exact)<=Q(radius)and c['actual_TR_norm']<=radius
    assert c['inward_ulp_corrections']>0


def test_two_difference_tail_in_actual_model_and_Cauchy_bound():
    from fractions import Fraction as Q
    from hybrid_box_residual_subproblem import exact_difference
    x=np.array([.1]);base=np.array([1e-30]);high,tail=exact_difference(x,base)
    assert Q(float(high[0]))+Q(float(tail[0]))==Q(float(x[0]))-Q(float(base[0]))
    assert tail[0]!=0
    m,_,*_=fixture();p=np.array([.01,-.02]);tail=np.array([1e-20,-2e-20])
    before=m.budget.used;e=m.evaluate(p,tail)
    assert m.budget.used-before==4
    J=m.J.toarray();r=[Q(float(v))for v in m.r];v=[]
    for i in range(2):v.append(Q(float(m.w[i]))*sum((Q(float(J[i,j]))*(Q(float(p[j]))+Q(float(tail[j])))for j in range(2)),Q(0)))
    pred=-sum((r[i]*v[i]+v[i]*v[i]/2 for i in range(2)),Q(0))
    assert Q(e['pred_lower'])<=pred<=Q(e['pred_upper'])


def test_scaled_gradient_division_underflow_cannot_become_zero():
    m=Model(sparse.diags([1e150,2e-154],format='csc'),np.ones(2),np.ones(2),np.full(2,1e150),Budget())
    with pytest.raises(RuntimeError,match='range|underflow|subnormal'):
        m.gradient(np.array([0.,2e-154]))


def test_Cauchy_division_and_Newton_scaling_underflow_explicit_stop():
    from hybrid_box_residual_subproblem import divide,multiply
    with pytest.raises(RuntimeError):divide(np.array([1e-300]),1e100,'test')
    with pytest.raises(RuntimeError):multiply(np.array([1e-300]),np.array([1e-100]),'test')
