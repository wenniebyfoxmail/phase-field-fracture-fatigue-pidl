"""ARTIFICIAL ALGEBRA ONLY: no file, network, research-array or FEM loading."""
import numpy as np
import pytest
from profiled_hidden_kernel import (Profiled,strict_spd_solver,conjugate_gradient,
    common_descent,limit_step,tangent_bounds,bounded_tangent_witness,finite_trial_decision)


def moving_profile(theta=.4):
    b=np.array([[1.],[theta]]);k=np.diag([2.,1.]);lift=np.array([0.,1.]);a=-theta/(2+theta**2)
    q=lift+b[:,0]*a;r=k@q;j=np.array([[0.],[a]]);c=np.array([[r[1]]]);h=b.T@k@b
    p=Profiled(1,2,1,lambda v:j@v,lambda w:j.T@w,lambda z:b@z,lambda w:b.T@w,
        lambda w:k@w,lambda w:k.T@w,lambda v:c@v,lambda z:c.T@z,strict_spd_solver(h))
    return p,q,r,j,b,k,c


def actual_profile(theta):
    a=-theta/(2+theta**2);return np.array([a,1+theta*a])


def test_moving_feature_term_is_required_and_profile_FD():
    p,q,r,j,b,k,c=moving_profile();eps=1e-6
    fd=(actual_profile(.4+eps)-actual_profile(.4-eps))/(2*eps)
    assert np.linalg.norm(p.q(np.ones(1))-fd)<1e-9
    assert np.linalg.norm(p.z(np.ones(1))-fd)>.1
    assert np.linalg.norm(c)>0


def test_u_and_q_adjoint_and_envelope():
    p,q,r,*_=moving_profile();v=np.array([.7]);z=np.array([-.3]);w=np.array([.9,-.2])
    assert abs(p.u(v)@z-v@p.ut(z))<1e-14
    assert abs(p.q(v)@w-v@p.qt(w))<1e-14
    assert abs(p.z(v)@w-v@p.zt(w))<1e-14
    assert np.linalg.norm(p.bt(r))<1e-14
    assert np.linalg.norm(p.qt(r)-p.jt(r))<1e-14


def test_metric_matches_physical_gram_and_not_exact_profile_Q():
    p,q,r,j,b,k,c=moving_profile();z=p.z(np.ones(1));expected=z@k@z+.03
    assert np.allclose(p.metric(np.ones(1),.03),[expected])
    assert abs(expected-(p.q(np.ones(1))@k@p.q(np.ones(1))+.03))>.01
    with pytest.raises(ValueError):p.metric(np.ones(1),0)


def test_profile_residual_and_energy_gradients_FD():
    p,q,r,j,b,k,c=moving_profile();ge,gr=p.gradients(r);h=1e-6
    plus,minus=actual_profile(.4+h),actual_profile(.4-h)
    assert abs(ge[0]-(plus@k@plus-minus@k@minus)/(4*h))<1e-9
    assert abs(gr[0]-(np.linalg.norm(k@plus)**2-np.linalg.norm(k@minus)**2)/(4*h))<1e-9


def test_cg_and_common_descent_without_weight_scan():
    m=np.array([[2.,.2],[.2,3.]]);ge=np.array([1.,0.]);gr=np.array([-.4,1.])
    solve=lambda rhs:conjugate_gradient(lambda v:m@v,rhs,relative_tolerance=1e-12)
    p,info=common_descent(ge,gr,solve)
    assert info['status']=='common_descent' and ge@p<0 and gr@p<0
    x,rec=solve(gr);assert rec['status']=='converged' and np.linalg.norm(m@x-gr)<1e-12


def test_opposing_zero_and_unresolved_gradients_are_not_success():
    exact=lambda g:(g,dict(status='exact'))
    assert common_descent(np.array([1.,0.]),np.array([-1.,0.]),exact)[0] is None
    assert common_descent(np.zeros(2),np.ones(2),exact)[1]['status']=='zero_gradient_no_claim'
    bad=lambda g:(g,dict(status='budget_unresolved'))
    assert common_descent(np.ones(2),np.ones(2),bad)[1]['status']=='metric_solve_unresolved'


def test_head_degeneracy_stops_without_ridge():
    with pytest.raises(np.linalg.LinAlgError):strict_spd_solver(np.array([[1.,1.],[1.,1.+1e-16]]))
    with pytest.raises(ValueError):strict_spd_solver(np.array([[1.,.1],[0.,1.]]))


def test_physical_TR_uses_Q_not_Z_and_parameter_ball():
    p,*_=moving_profile();v=np.array([2.]);out,info=limit_step(v,p,np.ones(2),.01,.1)
    assert np.linalg.norm(p.q(out))<=.01 and np.linalg.norm(out)<=.1
    assert abs(info['predicted_physical_norm']-np.linalg.norm(p.q(out)))<1e-14
    with pytest.raises(ValueError):limit_step(v,p,np.ones(2),float('nan'),.1)


def test_bounded_fit_reports_upper_lower_not_NN_capacity():
    a=np.array([[1.,0.],[0.,0.]]);b=np.array([0.,2.]);p=np.zeros(2)
    bounds=tangent_bounds(lambda v:a@v,lambda w:a.T@w,b,p,.5)
    assert abs(bounds['primal_upper']-2)<1e-14 and abs(bounds['dual_lower']-2)<1e-14
    x,res=bounded_tangent_witness(lambda v:a@v,lambda w:a.T@w,b,2,.5)
    assert res['status']=='bounded_numeric_gap' and res['raw_gap']==0
    assert 'Local linear' in bounds['scope']


def test_finite_ball_changes_ceiling_and_witness_can_be_exact():
    eye=lambda v:v
    x,res=bounded_tangent_witness(eye,eye,np.array([2.,0.]),2,.5)
    assert np.linalg.norm(x)<=.5 and abs(res['primal_upper']-1.125)<1e-12
    x,res=bounded_tangent_witness(eye,eye,np.array([.2,0.]),2,.5)
    assert res['primal_upper']<1e-25
    with pytest.raises(ValueError):tangent_bounds(eye,eye,np.ones(2),np.array([.6,0]),.5)


def test_linear_witness_or_energy_gain_alone_is_not_finite_NN_success():
    old=dict(E=1.,Ru=1.);new=dict(E=.9,Ru=.8,head_gradient_inf=9e-11,realization_maxabs=1e-12,finite=True,fixed_state=True,actual_nn=True)
    assert finite_trial_decision(old,new)=='accepted'
    assert finite_trial_decision(old,{**new,'actual_nn':False})=='rejected_contract'
    assert finite_trial_decision(old,{**new,'Ru':1.01})=='rejected_physical_joint_step'
    assert finite_trial_decision(old,{**new,'head_gradient_inf':1.1e-10})=='rejected_head_or_realization'
    assert finite_trial_decision(old,{**new,'E':float('nan')})=='rejected_contract'


def test_finite_shape_and_negative_curvature_fail_closed():
    p,*_=moving_profile()
    with pytest.raises(ValueError):p.q(np.array([np.nan]))
    with pytest.raises(ValueError):p.q(np.ones(2))
    with pytest.raises(ValueError):conjugate_gradient(lambda v:-v,np.ones(2))


def test_candidate_energy_nonincrease_is_not_strict_scientific_gain():
    old=dict(E=1.,Ru=1.)
    new=dict(E=1.,Ru=.8,head_gradient_inf=0.,realization_maxabs=0.,finite=True,fixed_state=True,actual_nn=True)
    assert finite_trial_decision(old,new)=='accepted'
    assert finite_trial_decision(old,{**new,'E':np.nextafter(1.,2.)})=='accepted'
    assert finite_trial_decision(old,{**new,'E':1.+1e-12})=='rejected_physical_joint_step'
    # Accepted equality/tiny roundoff is not the separately retained >1e-10 gain.
    assert old['E']-new['E']<=1e-10


def test_derived_overflow_and_nonfinite_budget_fail_closed():
    p,*_=moving_profile()
    with pytest.raises(ValueError):limit_step(np.array([1e200]),p,np.ones(2),.01,.1)
    with pytest.raises(ValueError):conjugate_gradient(lambda v:v,np.ones(2),relative_tolerance=np.inf)
    with pytest.raises(ValueError):conjugate_gradient(lambda v:v,np.ones(2),max_steps=1.5)
    with pytest.raises(ValueError):bounded_tangent_witness(lambda v:v,lambda v:v,np.ones(2),2,.5,relative_gap=np.inf)
    with pytest.raises(ValueError):tangent_bounds(lambda v:v,lambda v:v,np.full(2,1e200),np.zeros(2),.5)


def test_multidimensional_moving_chart_dense_and_finite_difference():
    rng=np.random.default_rng(17);n,m,k=3,5,2
    raw=rng.normal(size=(m,m));stiff=raw.T@raw+np.eye(m)
    base=rng.normal(size=(m,k));derivatives=rng.normal(size=(n,m,k));lift=rng.normal(size=m)
    def endpoint(theta):
        basis=base+np.einsum('j,jfi->fi',theta,derivatives)
        head=np.linalg.solve(basis.T@stiff@basis,-basis.T@stiff@lift)
        return lift+basis@head,basis,head
    theta=np.array([.1,-.2,.3]);q,b,head=endpoint(theta);r=stiff@q
    j=np.stack([d@head for d in derivatives],axis=1)
    c=np.stack([d.T@r for d in derivatives],axis=1);h=b.T@stiff@b
    profile=Profiled(n,m,k,lambda v:j@v,lambda w:j.T@w,lambda v:b@v,lambda w:b.T@w,
        lambda w:stiff@w,lambda w:stiff.T@w,lambda v:c@v,lambda w:c.T@w,strict_spd_solver(h))
    u=b.T@stiff@j+c;Q=j-b@np.linalg.solve(h,u);Z=j-b@np.linalg.solve(h,b.T@stiff@j)
    v=rng.normal(size=n);w=rng.normal(size=m);z=rng.normal(size=k)
    assert np.linalg.norm(c)>1e-3 and np.linalg.norm(Q-Z)>1e-3
    assert np.allclose(profile.u(v),u@v) and np.allclose(profile.ut(z),u.T@z)
    assert np.allclose(profile.q(v),Q@v) and np.allclose(profile.qt(w),Q.T@w)
    assert np.allclose(profile.z(v),Z@v) and np.allclose(profile.zt(w),Z.T@w)
    assert abs(profile.q(v)@w-v@profile.qt(w))<1e-12
    eps=1e-6;fd=(endpoint(theta+eps*v)[0]-endpoint(theta-eps*v)[0])/(2*eps)
    assert np.linalg.norm(fd-Q@v)<1e-8
    mat=np.stack([profile.metric(e,.03) for e in np.eye(n)],axis=1)
    assert np.allclose(mat,Z.T@stiff@Z+.03*np.eye(n))
    assert np.allclose(mat,mat.T) and np.linalg.eigvalsh(mat).min()>0
