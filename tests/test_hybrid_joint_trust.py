"""Artificial algebra/controller contracts; no project mesh/data or producer."""
from dataclasses import replace
from types import SimpleNamespace
import numpy as np
import pytest
from scipy import sparse
import hybrid_joint_trust as jt
from hybrid_incremental import NativeQ4Backend,solve_step,StepFailure
from hybrid_history import AcceptedState,trial_history,fatigue_factor
from hybrid_damage import NodalQP
from hybrid_coupled_acceleration import CouplingSettings
from test_hybrid_incremental import one_element,settings
from test_hybrid_guarded_coupling import native_old


def test_fixed_operator_scales_and_separate_objective():
    weights=jt.frozen_weights([4.,9.],[16.,25.],2.)
    assert np.array_equal(weights[0],[.5,1/3]) and np.array_equal(weights[1],[.5,.4])
    phi,parts=jt.objective(np.array([2.,3.]),np.array([2.,2.5]),weights)
    assert phi==2 and parts==(1.,1.)
    for bad in [0.,-1.,np.nan,np.inf]:
        with pytest.raises(RuntimeError):jt.frozen_weights([bad],[1.],1.)


def test_severe_projection_model_uses_actual_B_cross_term_and_active_rows():
    base=dict(u=np.array([0.,1.]),d=np.array([.8,.3,1.]))
    dd=np.array([.8,-.9,-.2]);free=np.array([1]);lo=np.array([.75,.2,1.]);crack=lo==1
    u,d,su,sd,info=jt.projected_step(base,np.array([.2]),dd,free,np.array([0]),np.array([0.]),lo,crack,1.,1.)
    model=dict(A=sparse.csc_matrix([[2.]]),B=sparse.csc_matrix([[3.,4.,5.]]),
        C=sparse.csc_matrix([[1.],[2.],[3.]]),D=sparse.eye(3,format='csc'),
        Ru=np.array([.1]),F=np.array([.2,.3,0.]),inactive=np.array([True,False,False]))
    ru,f=jt.model_residual(model,su,sd,2.)
    assert np.array_equal(d,[1.,.2,1.]) and u[0]==0
    assert np.allclose(ru,.1+2*su+3*sd[0]+4*sd[1]+5*sd[2])
    assert abs(ru[0]-(.1+2*su[0]+float((model['B']@dd)[0])))>.1
    assert np.allclose(f,[.2+(su[0]+sd[0])/2,.3+sd[1],sd[2]])
    assert info['projection_change_inf']>.5 and info['projected_step_norm']==pytest.approx(.2)


@pytest.mark.parametrize('model,actual,keep,new',[(.5,.4,True,.2),(.5,.95,True,.025),(.5,1.1,False,.025),(1.,.5,False,.025)])
def test_ratio_and_actual_step_radius(model,actual,keep,new):
    k,r,info=jt.trust_decision(1.,model,actual,.1,.1,.25)
    assert k==keep and r==pytest.approx(new)
    if model<1:assert info['rho']==pytest.approx((1-actual)/(1-model))
    with pytest.raises(RuntimeError):jt.trust_decision(1.,model,np.nan,.1,.1,.25)


class JointController(NativeQ4Backend):
    def mechanics(self,d,dofs,values,s,initial_u=None):
        self.mechanics_calls+=1;u=np.full(8,float(np.mean(d)));u[dofs]=values
        return u,dict(iterations=1)
    def trial(self,old,u,d):
        psi=np.full((1,4),.02+float(np.mean(u[1:]))**2)
        return psi,trial_history(old,np.full((1,4),np.mean(d)),psi,alpha_t=self.alpha_t,power=2.)
    def damage_problem(self,psi,f,old):
        # Recover the analytic mean displacement on the nonnegative test branch.
        mean=np.sqrt(max(float(psi[0,0])-.02,0.))
        return NodalQP(sparse.eye(4,format='csc'),np.full(4,-(.02+.5*mean)),old.damage,np.ones(4),'artificial')
    def force_audit(self,u,d,dofs,values,s,*,include_vector=False):
        ru=u[1:]-np.mean(d);norm=float(np.linalg.norm(ru))
        r=dict(force_inf=float(np.max(abs(ru))),force_l2=norm,force_scaled=float(np.max(abs(ru))),boundary_inf=0.)
        if include_vector:r.update(free_residual=ru,original_matrix=sparse.eye(8,format='csc'))
        return r


def controller(monkeypatch,alpha=10.):
    b=JointController(one_element(),np.zeros(4,bool),alpha_t=alpha);b.mechanics_calls=0
    z=np.zeros((1,4));A=np.full((1,4),.01)
    old=AcceptedState(np.zeros(8),np.zeros(4),A,z,fatigue_factor(A,alpha,2.),z,0,0,b.mesh_id,b.physics_id,'artificial')
    monkeypatch.setattr(b.mechanics_workspace,'certify_factor',lambda *a,**kw:dict(current_matrix_pivot_qualified=True))
    def direction(backend,old,p,dofs,s,policy,*args,**kwargs):
        A=sparse.eye(7,format='csc');B=sparse.csc_matrix(-np.ones((7,4))/4)
        C=sparse.csc_matrix(-.5*np.ones((4,7))/7);D=sparse.eye(4,format='csc')
        grad=p['qp'].hessian@p['d']+p['qp'].linear
        F,I=jt.natural_residual(p['d'],grad,old.damage,s.damage_gradient_scale)
        matrix=sparse.bmat([[A,B],[C,D]]).toarray();x=np.linalg.solve(matrix,-np.r_[p['Ru'],grad])
        return x[7:],dict(passed=True),dict(A=A,B=B,C=C,D=D,Ru=p['Ru'],F=F,inactive=I,free_dofs=np.arange(1,8),du=x[:7])
    monkeypatch.setattr(jt,'block_direction',direction)
    return b,old


def run(b,old,rows=None,**kw):
    return solve_step(b,old,np.array([0]),np.array([0.]),next_load_id='artificial',settings=settings(**kw),
        coupling=CouplingSettings(mode='joint_projected_trust'),iteration_observer=None if rows is None else rows.append)


@pytest.mark.parametrize('alpha',[10.,.005])
def test_joint_work_never_mechanically_eliminated_final_QP_history_required(monkeypatch,alpha):
    b,old=controller(monkeypatch,alpha);rows=[];before=old.fingerprint();snap=[]
    b.joint_trial_observer=lambda meta,v:snap.append((meta,{k:x.copy() for k,x in v.items()}))
    p=run(b,old,rows)
    assert np.allclose(p.state.damage,.04,atol=1e-9) and b.mechanics_calls==2
    assert p.certificate['true_final_QP'] and p.certificate['m_accept']<=1
    assert p.certificate['coupling_work']['working_mechanics_calls']==0
    assert p.certificate['coupling_work']['qp_calls']==1 and p.certificate['coupling_work']['newton_directions']==1
    assert old.fingerprint()==before and p.state.version==1
    if alpha<1:assert np.all(p.state.fatigue<1)
    assert all(x['m_accept']is None for x in rows if x.get('evaluation')=='joint_projected_trial')
    assert snap[0][0]['parent_id']==before and np.array_equal(snap[0][1]['u'][[0]],[0.])


def test_rejected_8_trials_stop_without_candidate_mechanics_or_history_update(monkeypatch):
    b,old=controller(monkeypatch);before=old.fingerprint();rows=[]
    real=jt.model_residual
    monkeypatch.setattr(jt,'model_residual',lambda m,*a:(m['Ru'],m['F']*2))
    with pytest.raises(StepFailure,match='finite trial budget'):run(b,old,rows)
    assert len([x for x in rows if x['event']=='joint_trial_rejected_without_fresh'])==8
    assert b.mechanics_calls==1 and old.fingerprint()==before


def test_final_pivot_failure_is_stop_not_more_work(monkeypatch):
    b,old=controller(monkeypatch);before=old.fingerprint()
    monkeypatch.setattr(b.mechanics_workspace,'certify_factor',lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('artificial bad pivot')))
    with pytest.raises(StepFailure,match='bad pivot'):run(b,old)
    assert b.mechanics_calls==2 and old.fingerprint()==before


def test_nested_pivot_diagnostics_do_not_steal_parent_solver_accounting(monkeypatch):
    b,old=controller(monkeypatch);real=b.mechanics;rows=[]
    def observed(*a,**kw):
        if b.mechanics_diagnostics:b.mechanics_diagnostics(dict(kind='artificial_pivot'))
        return real(*a,**kw)
    monkeypatch.setattr(b,'mechanics',observed)
    p=run(b,old,rows)
    parents=[x for x in p.work if x['kind']in ('common_mechanics_predictor','mechanics_re_equilibration')]
    assert len(parents)==2 and all('solver'in x for x in parents)
    assert all('solver'not in x for x in p.work if x['kind']=='iteration_evidence')


def test_failed_final_physical_audit_is_not_accepted_or_retried(monkeypatch):
    b,old=controller(monkeypatch);before=old.fingerprint();real=b.mechanics
    def badfinal(*a,**kw):
        u,info=real(*a,**kw)
        if b.mechanics_calls==2:u[1:]+=.1
        return u,info
    monkeypatch.setattr(b,'mechanics',badfinal)
    with pytest.raises(StepFailure,match='physical qualification'):run(b,old)
    assert b.mechanics_calls==2 and old.fingerprint()==before


def test_fresh_slot_reserved_for_final_and_no_factor_bypass(monkeypatch):
    b,old=controller(monkeypatch);before=old.fingerprint()
    with pytest.raises(StepFailure,match='final slot reserved'):run(b,old,max_outer=2)
    assert b.mechanics_calls==1 and old.fingerprint()==before


def test_actual_pivot_scalar_and_key_persist_before_rejection():
    b,old=native_old();rows=[];b.mechanics_workspace.qualification_diagnostic=rows.append
    factor=SimpleNamespace(U=sparse.diags([1.,1e-16],format='csc'))
    with pytest.raises(RuntimeError,match='near-singular'):b.mechanics_workspace.qualify(factor,b'abc','artificial')
    assert rows[-1]['pivot_ratio']==1e-16 and rows[-1]['current_matrix_key']==b'abc'.hex() and not rows[-1]['passed']


def test_near_zero_support_residual_evaluation_does_not_require_inverse(monkeypatch):
    b,old=native_old();u=.01*b.kin.points.ravel();d=np.ones(4)
    monkeypatch.setattr(b,'mechanics',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('no inverse allowed for trial')))
    # Artificial full-d1 element on the original eta0 tensile branch. The
    # original residual exists even though final pivot qualification may fail.
    psi,q=b.trial(old,u,d);qp=b.damage_problem(psi,q.fatigue,old)
    audit=b.force_audit(u,d,np.array([0,1]),u[[0,1]],settings(),include_vector=True)
    F,I=jt.natural_residual(d,qp.hessian@d+qp.linear,old.damage,1.)
    assert np.isfinite(audit['free_residual']).all() and np.isfinite(F).all()
    assert np.linalg.norm(audit['free_residual'])<1e-30


def test_radius_collapse_and_nonfinite_are_stops(monkeypatch):
    b,old=controller(monkeypatch);before=old.fingerprint()
    real=CouplingSettings(mode='joint_projected_trust')
    monkeypatch.setattr(jt,'trust_decision',lambda *a:(False,1e-9,dict(predicted_reduction=1.,actual_reduction=-1.,rho=-1.)))
    with pytest.raises(StepFailure,match='radius collapsed'):run(b,old)
    assert old.fingerprint()==before and b.mechanics_calls==1
    monkeypatch.setattr(jt,'model_residual',lambda *a:(np.array([np.nan]*7),np.zeros(4)))
    with pytest.raises(StepFailure,match='nonfinite joint work'):run(b,old)


def test_eight_block_direction_limit_on_joint_route(monkeypatch):
    b,old=controller(monkeypatch);before=old.fingerprint();original=jt.block_direction;calls=[]
    def partial(*a,**kw):
        dd,info,model=original(*a,**kw);model['du']*=.1;calls.append(1)
        return dd*.1,info,model
    monkeypatch.setattr(jt,'block_direction',partial)
    with pytest.raises(StepFailure,match='direction budget'):run(b,old)
    assert len(calls)==8 and b.mechanics_calls==1 and old.fingerprint()==before


@pytest.mark.parametrize('alpha',[10.,.005])
def test_native_small_nonzero_Ru_block_retains_joint_model(alpha):
    from hybrid_coupled_block import block_direction
    b,old=native_old(alpha=alpha);d=np.array([.15,.2,.3,.12]);u=np.array([0.,0.,.03,.01,.04,.02,.01,.03])
    dofs=np.array([0,1,2,3,5,7]);psi,q=b.trial(old,u,d);qp=b.damage_problem(psi,q.fatigue,old)
    dd,info,m=block_direction(b,old,dict(u=u,d=d,qp=qp,q=q),dofs,settings(),CouplingSettings(mode='joint_projected_trust'),lambda k,f:f(),lambda:1.,lambda e:None,return_model=True)
    ru,f=jt.model_residual(m,m['du'],dd,settings().damage_gradient_scale)
    assert info['passed'] and np.linalg.norm(ru)<1e-8 and np.linalg.norm(f)<4e-6
    assert np.linalg.norm(m['Ru'])>0
