"""Artificial one-element derivatives and controller faults, not project FEM."""
from dataclasses import replace
import numpy as np
import pytest
from hybrid_incremental import NativeQ4Backend,solve_step,StepFailure
from hybrid_history import AcceptedState,fatigue_factor,trial_history
from hybrid_coupled_acceleration import CouplingSettings
from hybrid_damage import NodalQP
from hybrid_reduced_tangent import coupled_blocks,natural_residual,reduced_direction
from scipy import sparse
from test_hybrid_incremental import one_element,settings


def native_old(alpha=.005,acc=.01):
    b=NativeQ4Backend(one_element(),np.zeros(4,bool),gc=.001,length_scale=.1,alpha_t=alpha)
    A=np.full((1,4),acc)
    s=AcceptedState(np.zeros(8),np.zeros(4),A,np.zeros((1,4)),
        fatigue_factor(A,alpha,2.),np.zeros((1,4)),0,0,b.mesh_id,b.physics_id,'artificial')
    return b,s


@pytest.mark.parametrize('sign',[1.,-1.])
@pytest.mark.parametrize('loading',[True,False])
@pytest.mark.parametrize('fatigue',[True,False])
def test_original_residual_block_derivatives(sign,loading,fatigue):
    b,old=native_old(alpha=.005 if fatigue else 10.,acc=.01)
    if not loading:old=replace(old,driver=np.full((1,4),10.))
    d=np.array([.12,.24,.3,.18]);u=sign*np.array([0.,0.,.23,.01,.25,.17,.02,.19])
    du=np.array([.03,-.02,.01,.04,-.03,.02,.04,-.01]);dd=np.array([.2,-.1,.3,-.15])
    psi,q=b.trial(old,u,d);qp=b.damage_problem(psi,q.fatigue,old)
    B,C,D=coupled_blocks(b,old,u,d,qp,q)
    A=b.mechanics_workspace.assemble(d,u)
    def residual(u,d):
        psi,q=b.trial(old,u,d);p=b.damage_problem(psi,q.fatigue,old)
        return b.mechanics_workspace.assemble(d,u)@u,p.hessian@d+p.linear
    h=1e-6;plus=residual(u+h*du,d+h*dd);minus=residual(u-h*du,d-h*dd)
    assert np.allclose((plus[0]-minus[0])/(2*h),A@du+B@dd,atol=2e-10,rtol=2e-7)
    assert np.allclose((plus[1]-minus[1])/(2*h),C@du+D@dd,atol=2e-10,rtol=2e-7)
    if fatigue and loading:assert not np.allclose(C.toarray(),B.T.toarray(),atol=1e-8)
    else:assert np.array_equal(C.toarray(),B.T.toarray())


def test_projection_releases_wrong_sign_lower_and_upper_and_fixes_old_one():
    d=np.array([.2,1.,.2,1.,1.]);lo=np.array([.2,.2,.2,.2,1.])
    F,I=natural_residual(d,np.array([-1.,1.,1.,-1.,-10.]),lo,10.)
    assert I.tolist()==[True,True,False,False,False]
    assert F[-1]==0 and F[0]<0 and F[1]>0


@pytest.mark.parametrize('boundary',['loading_equal','threshold_equal','trace_zero'])
def test_declared_one_sided_branch_derivative(boundary):
    b,old=native_old(alpha=.5 if boundary=='threshold_equal' else .005)
    d=np.full(4,.2);u=np.array([0.,0.,.125,0.,.125,.125,0.,.125])
    du=np.zeros(8);dd=np.full(4,.1)
    psi,q=b.trial(old,u,d)
    if boundary=='loading_equal':old=replace(old,driver=q.driver)
    elif boundary=='threshold_equal':
        old=replace(old,driver=q.driver/2,accumulated=np.full((1,4),b.alpha_t)-q.driver/2,
            fatigue=np.ones((1,4)))
        assert np.array_equal(b.trial(old,u,d)[1].accumulated,np.full((1,4),b.alpha_t))
    else:
        u=np.array([0.,0.,.125,0.,.125,-.125,0.,-.125]);du=.02*b.kin.points.ravel()
    psi,q=b.trial(old,u,d);qp=b.damage_problem(psi,q.fatigue,old)
    B,C,D=coupled_blocks(b,old,u,d,qp,q);A=b.mechanics_workspace.assemble(d,u)
    def R(u,d):
        psi,q=b.trial(old,u,d);p=b.damage_problem(psi,q.fatigue,old)
        return b.mechanics_workspace.assemble(d,u)@u,p.hessian@d+p.linear
    h=1e-7;r0=R(u,d);r1=R(u+h*du,d+h*dd)
    assert np.allclose((r1[0]-r0[0])/h,A@du+B@dd,atol=2e-9,rtol=2e-6)
    assert np.allclose((r1[1]-r0[1])/h,C@du+D@dd,atol=2e-9,rtol=2e-6)


def test_current_A_schur_direction_matches_dense_reduced_jacobian():
    b,old=native_old(alpha=10.);s=settings();d=np.array([.15,.2,.3,.12])
    dofs=np.array([0,1,2,3,5,7]);values=np.array([0.,0.,0.,0.,.3,.3])
    u,_=b.mechanics(d,dofs,values,s)
    psi,q=b.trial(old,u,d);qp=b.damage_problem(psi,q.fatigue,old)
    point=dict(d=d,u=u,qp=qp,q=q)
    p=CouplingSettings(mode='guarded_vi_newton');events=[]
    direction,info=reduced_direction(b,old,point,dofs,s,p,lambda k,f:f(),lambda:1.,events.append)
    B,C,D=coupled_blocks(b,old,u,d,qp,q)
    free=np.setdiff1d(np.arange(8),dofs);A=b.mechanics_workspace.assemble(d,u).toarray()
    S=D.toarray()-C.toarray()[:,free]@np.linalg.solve(A[np.ix_(free,free)],B.toarray()[free])
    F,I=natural_residual(d,qp.hessian@d+qp.linear,old.damage,s.damage_gradient_scale)
    J=np.eye(4);J[I]=S[I]/s.damage_gradient_scale
    assert np.linalg.norm(J@direction+F)<=1e-3*np.linalg.norm(F)*1.001
    assert info['fixed_current_A_inverse'] and info['true_residual']<=info['target']*(1+1e-10)


class ControllerBackend(NativeQ4Backend):
    """Analytic d=.2+.5u, u=d; tangent/pivots explicitly mocked separately."""
    def mechanics(self,d,*args,**kwargs):return np.repeat(d,2),dict(iterations=1)
    def trial(self,old,u,d):
        psi=np.full((1,4),u[0]);return psi,trial_history(old,np.full((1,4),d[0]),psi,alpha_t=10.,power=2.)
    def damage_problem(self,psi,f,old):
        return NodalQP(sparse.eye(4,format='csc'),np.full(4,-(.2+.5*psi[0,0])),old.damage,np.ones(4),'unit')
    def force_audit(self,*a):return dict(force_inf=0.,force_l2=0.,force_scaled=0.,boundary_inf=0.)


def controller(monkeypatch):
    b=ControllerBackend(one_element(),np.zeros(4,bool),alpha_t=10.)
    z=np.zeros((1,4));old=AcceptedState(np.zeros(8),np.zeros(4),z,z,np.ones((1,4)),z,
        0,0,b.mesh_id,b.physics_id,'artificial')
    monkeypatch.setattr(b.mechanics_workspace,'certify_factor',lambda *a,**kw:dict(current_matrix_pivot_qualified=True))
    return b,old


def test_no_QP_newton_work_is_NA_and_final_real_QP_is_required(monkeypatch):
    import hybrid_guarded_coupling as g
    b,old=controller(monkeypatch);rows=[];before=old.fingerprint()
    monkeypatch.setattr(g,'reduced_direction',lambda b,o,p,*a:(.4-p['d'],{}))
    p=solve_step(b,old,np.array([0]),np.array([0.]),next_load_id='unit',settings=settings(),
        coupling=CouplingSettings(mode='guarded_vi_newton',schur_trigger_ratio=.1),iteration_observer=rows.append)
    newton=next(x for x in rows if x.get('evaluation')=='reduced_VI_Newton')
    assert newton['m_work']<1 and newton['m_accept'] is None and newton['fatigue_residual'] is None
    assert newton['qp_operation_component']=='NA'
    assert p.certificate['true_final_QP'] and p.certificate['coupling_work']['qp_calls']==2
    assert p.certificate['m_accept']<=1 and np.array_equal(p.field_evidence['f_solve_gp'],np.ones((1,4)))
    assert old.fingerprint()==before and p.state.version==1 and p.state.load_index==1


def test_rejected_candidates_restore_best_and_all_count_to_one_cap(monkeypatch):
    import hybrid_guarded_coupling as g
    b,old=controller(monkeypatch);rows=[];before=old.fingerprint();cache_states={}
    real=b.mechanics
    def changed_cache(d,*a,**kw):
        result=real(d,*a,**kw);w=b.mechanics_workspace
        w.factor_key=d.tobytes();w.factor_domain=('unit',d.tobytes());w.factor=object()
        cache_states[d.tobytes()]=(w.factor_key,w.factor,w.factor_domain)
        return result
    monkeypatch.setattr(b,'mechanics',changed_cache)
    def observe(row):
        rows.append(row)
        if row['event']=='fresh_evaluation' and row['kept_as_iteration_point']:
            w=b.mechanics_workspace
            cache_states[('outer',row['outer'])]=(w.factor_key,w.factor,w.factor_domain)
        if row['event']=='work_point_rollback':
            w=b.mechanics_workspace;expected=cache_states[('outer',row['restored_outer'])]
            assert w.factor_key==expected[0] and w.factor is expected[1] and w.factor_domain==expected[2]
    monkeypatch.setattr(g,'reduced_direction',lambda b,o,p,*a:(np.full(4,-.1),{}))
    with pytest.raises(StepFailure,match='fresh candidate budget'):
        solve_step(b,old,np.array([0]),np.array([0.]),next_load_id='unit',settings=settings(max_outer=7),
            coupling=CouplingSettings(mode='guarded_vi_newton',schur_trigger_ratio=.1),iteration_observer=observe)
    evaluations=[x for x in rows if x['event']=='fresh_evaluation'];assert len(evaluations)==7
    kept=[x for x in evaluations if x['kept_as_iteration_point']]
    assert all(b['m_work']<a['m_work'] for a,b in zip(kept,kept[1:]))
    rollback=[x for x in rows if x['event']=='work_point_rollback'];assert len(rollback)==4
    assert all(x['restored_outer']==2 for x in rollback)
    assert old.fingerprint()==before and old.version==0


def test_nested_mechanics_diagnostic_keeps_solver_on_parent_row(monkeypatch):
    import hybrid_guarded_coupling as g
    b,old=controller(monkeypatch);real=b.mechanics
    def diagnostic(d,*a,**kw):
        if getattr(b,'mechanics_diagnostics',None):b.mechanics_diagnostics(dict(kind='unit_gmres'))
        return real(d,*a,**kw)
    monkeypatch.setattr(b,'mechanics',diagnostic)
    monkeypatch.setattr(g,'reduced_direction',lambda b,o,p,*a:(.4-p['d'],{}))
    p=solve_step(b,old,np.array([0]),np.array([0.]),next_load_id='unit',settings=settings(),
        coupling=CouplingSettings(mode='guarded_vi_newton',schur_trigger_ratio=.1),iteration_observer=lambda row:None)
    assert all('solver' in row for row in p.work if row['kind']=='mechanics_re_equilibration')
    assert all('solver' not in row for row in p.work if row['kind']=='iteration_evidence')


def test_final_current_pivot_failure_cannot_return_proposal(monkeypatch):
    import hybrid_guarded_coupling as g
    b,old=controller(monkeypatch)
    monkeypatch.setattr(g,'reduced_direction',lambda b,o,p,*a:(.4-p['d'],{}))
    monkeypatch.setattr(b.mechanics_workspace,'certify_factor',lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('bad current pivot')))
    with pytest.raises(StepFailure,match='bad current pivot'):
        solve_step(b,old,np.array([0]),np.array([0.]),next_load_id='unit',settings=settings(),
            coupling=CouplingSettings(mode='guarded_vi_newton',schur_trigger_ratio=.1))
    assert old.version==0


def test_successful_anderson_is_not_disabled_by_three_or_five_lifetime_uses(monkeypatch):
    from hybrid_coupled_acceleration import ProjectedAnderson
    b,old=controller(monkeypatch)
    def bounded_proposal(self):
        if len(self.history)<2 or self.proposals>=self.policy.max_proposals:return None,dict(reason='cap_or_history')
        x,g,_=self.history[-1];self.proposals+=1
        return g+.5*(g-x),dict(reason='artificial_contracting_secant')
    monkeypatch.setattr(ProjectedAnderson,'propose',bounded_proposal)
    p=solve_step(b,old,np.array([0]),np.array([0.]),next_load_id='unit',settings=settings(),
        coupling=CouplingSettings(mode='guarded_vi_newton',schur_trigger_ratio=.99))
    assert p.certificate['coupling_work']['proposals']>5
    assert p.certificate['coupling_work']['kept_accelerated_maps']>5
    assert p.certificate['coupling_work']['newton_directions']==0 and p.certificate['true_final_QP']
