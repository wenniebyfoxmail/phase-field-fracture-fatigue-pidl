"""Small artificial algebra/control cases only; no project fields or producer."""
from dataclasses import replace
import numpy as np
import pytest
from scipy import sparse
from hybrid_coupled_block import solve_original_block,true_row_audit,block_direction
from hybrid_reduced_tangent import coupled_blocks,natural_residual
from hybrid_guarded_coupling import backtrack_candidate
from hybrid_coupled_acceleration import CouplingSettings
from hybrid_incremental import solve_step,StepFailure
from test_hybrid_incremental import settings
from test_hybrid_guarded_coupling import native_old,controller


def test_full_step_is_exact_target_despite_nonreversible_subtract_add():
    x=np.array([1e-8,.7,.9]);g=np.array([1e-20,.2,.3]);lo=np.zeros(3);crack=np.zeros(3,bool)
    assert not np.array_equal(x+(g-x),g)
    out=backtrack_candidate(x,g,1.,lo,crack)
    assert out is not g and np.array_equal(out,g)
    assert np.allclose(backtrack_candidate(x,g,.5,lo,crack),x+.5*(g-x))
    assert np.array_equal(backtrack_candidate(x,np.array([-2.,2.,1.]),1.,lo,crack),[0.,1.,1.])


@pytest.mark.parametrize('zero_mechanics',[False,True])
@pytest.mark.parametrize('with_active',[False,True])
def test_sparse_block_matches_dense_full_original_rows_nonzero_Ru_and_active(zero_mechanics,with_active):
    rng=np.random.default_rng(19);T=rng.normal(size=(5,5));K=T.T@T+np.eye(5)
    A=sparse.csc_matrix(K[:2,:2]);B=sparse.csc_matrix(K[:2,2:]);C=sparse.csc_matrix(K[2:,:2]);D=sparse.csc_matrix(K[2:,2:])
    Ru=np.array([0.,0.])if zero_mechanics else np.array([.01,-.02]);F=np.array([.03,.04,-.01]);I=np.array([True,not with_active,True])
    events=[];vectors=[];delta,info=solve_original_block(A,B,C,D,Ru,F,F,I,1.,settings(),.001,
        lambda k,f:f(),lambda:1.,events.append,lambda i,v:vectors.append(v))
    v=vectors[0];du=v['delta_u_free']
    assert np.linalg.norm(A@du+B@delta+Ru)<1e-14
    assert np.linalg.norm((C@du+D@delta+F)[I])<1e-14
    assert np.array_equal(delta[~I],-F[~I]) and info['passed']
    J=D.toarray()-C.toarray()@np.linalg.solve(A.toarray(),B.toarray())
    expected=np.zeros(3);expected[~I]=-F[~I]
    expected[I]=np.linalg.solve(J[np.ix_(I,I)],-F[I]+(C@np.linalg.solve(A.toarray(),Ru))[I]-(J@expected)[I])
    assert np.allclose(delta,expected,rtol=1e-12,atol=1e-14)


def test_zero_rhs_coupled_cancellation_roundoff_is_not_an_arbitrary_atol():
    rng=np.random.default_rng(19);T=rng.normal(size=(3,3));K=T.T@T+np.eye(3)
    A=sparse.csc_matrix(K[:2,:2]);B=sparse.csc_matrix(K[:2,2:]);C=sparse.csc_matrix(K[2:,:2]);D=sparse.csc_matrix(K[2:,2:])
    _,info=solve_original_block(A,B,C,D,np.zeros(2),np.array([-1.]),np.array([-1.]),np.ones(1,bool),1.,settings(),.001,lambda k,f:f(),lambda:1.,lambda e:None)
    assert info['mechanics_rhs_l2']==0 and info['mechanics_effective_relative_target']==info['mechanics_roundoff_l2_bound']
    assert info['passed'] and info['mechanics_roundoff_l2_bound']<1e-12
    zero=sparse.csc_matrix((1,1));info,_,_=true_row_audit(zero,zero,zero,zero,np.zeros(1),np.zeros(1),np.zeros(1),np.zeros(1),settings(),.001)
    assert info['mechanics_roundoff_l2_bound']==0 and info['damage_roundoff_l2_bound']==0


def test_large_mechanics_RHS_cannot_hide_bad_damage_row_and_abs_gate_still_binds():
    eye=sparse.eye(1,format='csc');zero=sparse.csc_matrix((1,1))
    info,_,_=true_row_audit(eye,zero,zero,eye,np.array([1e9]),np.array([1.]),np.array([1e9]),np.array([1e-6]),settings(),.001)
    assert not info['passed'] and info['damage_true_l2']>info['damage_effective_relative_target']
    info,_,_=true_row_audit(eye,zero,zero,eye,np.array([1e9+1e-4]),np.array([1e-6]),np.array([1e9]),np.array([1e-6]),settings(),.001)
    assert info['mechanics_true_l2']<info['mechanics_effective_relative_target'] and not info['passed']


@pytest.mark.parametrize('fatigue',[False,True])
def test_native_small_nonzero_Ru_original_residual_block_direction(fatigue):
    b,old=native_old(alpha=.005 if fatigue else 10.);d=np.array([.15,.2,.3,.12]);u=np.array([0.,0.,.03,.01,.04,.02,.01,.03])
    dofs=np.array([0,1,2,3,5,7]);psi,q=b.trial(old,u,d);qp=b.damage_problem(psi,q.fatigue,old)
    point=dict(d=d,u=u,qp=qp,q=q);before=old.fingerprint();events=[]
    delta,info=block_direction(b,old,point,dofs,settings(),CouplingSettings(mode='guarded_block_newton'),lambda k,f:f(),lambda:1.,events.append)
    assert info['passed'] and info['mechanics_rhs_l2']>0 and np.isfinite(delta).all()
    assert old.fingerprint()==before


def test_warning_in_factorization_is_recorded_then_stops(monkeypatch):
    import hybrid_coupled_block as m, warnings
    real=m.splu
    def warn(*a,**k):warnings.warn('artificial numerical warning',RuntimeWarning);return real(*a,**k)
    monkeypatch.setattr(m,'splu',warn);e=sparse.eye(1,format='csc');z=sparse.csc_matrix((1,1));events=[]
    with pytest.raises(RuntimeError,match='factorization warning'):
        solve_original_block(e,z,z,e,np.ones(1),np.ones(1),np.ones(1),np.ones(1,bool),1.,settings(),.001,lambda k,f:f(),lambda:1.,events.append)
    assert events[-1]['event']=='block_numerical_warning'


def test_AA_history_uses_full_map_operation_not_array_roundtrip(monkeypatch):
    import hybrid_guarded_coupling as g
    b,old=controller(monkeypatch);events=[]
    p=solve_step(b,old,np.array([0]),np.array([0.]),next_load_id='unit',settings=settings(),
        coupling=CouplingSettings(mode='guarded_block_newton',schur_trigger_ratio=.99),iteration_observer=events.append)
    history=[x for x in events if x['event']=='anderson_history'];assert history[0]['history_length']==1
    assert history[1]['history_length']==2 and history[1]['operation']=='add_full_original_QP_map'
    assert p.certificate['true_final_QP'] and p.certificate['m_accept']<=1


def test_8_direction_cap_is_checked_before_ninth_and_old_history_is_unchanged(monkeypatch):
    import hybrid_guarded_coupling as g
    b,old=controller(monkeypatch);before=old.fingerprint();calls=[];rows=[]
    def no_update(b,o,p,*a):calls.append(1);return np.zeros(4),{}
    monkeypatch.setattr(g,'block_direction',no_update)
    # Slow original map; block direction unchanged: zero fresh candidate cannot bypass cap.
    with pytest.raises(StepFailure,match='direction budget'):
        solve_step(b,old,np.array([0]),np.array([0.]),next_load_id='unit',settings=settings(damage_tolerance=1e-14),
            coupling=CouplingSettings(mode='guarded_block_newton',schur_trigger_ratio=.1),iteration_observer=rows.append)
    assert len(calls)==8 and old.fingerprint()==before
    assert rows[-1]['event']=='block_direction_budget'


def test_no_QP_block_point_is_NA_and_real_final_QP_remains_required(monkeypatch):
    import hybrid_guarded_coupling as g
    b,old=controller(monkeypatch);rows=[]
    monkeypatch.setattr(g,'block_direction',lambda b,o,p,*a:(.4-p['d'],{}))
    p=solve_step(b,old,np.array([0]),np.array([0.]),next_load_id='unit',settings=settings(),
        coupling=CouplingSettings(mode='guarded_block_newton',schur_trigger_ratio=.1),iteration_observer=rows.append)
    work=next(x for x in rows if x.get('evaluation')=='coupled_block_Newton')
    assert work['m_accept']is None and not work['full_original_QP_map']
    assert p.certificate['true_final_QP'] and p.certificate['coupling_work']['qp_calls']==2


def test_inactive_row_uses_original_gradient_not_roundtrip_natural_residual():
    A=sparse.eye(1,format='csc');B=sparse.csc_matrix([[.2]]);C=B.T.tocsc();D=sparse.csc_matrix([[2.]])
    d=np.array([.7]);Rd=np.array([1e-12]);scale=3.;F,I=natural_residual(d,Rd,np.zeros(1),scale)
    assert not np.array_equal(scale*F,Rd)
    vectors=[];_,info=solve_original_block(A,B,C,D,np.array([1e-11]),Rd,F,I,scale,settings(),.001,lambda k,f:f(),lambda:1.,lambda e:None,lambda i,v:vectors.append(v))
    assert np.array_equal(vectors[0]['rhs_damage_inactive'],-Rd) and info['passed']
