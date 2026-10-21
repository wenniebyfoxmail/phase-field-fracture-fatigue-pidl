"""R008 given-array and saved-array control delta; no native FEM assembly."""
from fractions import Fraction as Q
from pathlib import Path
import numpy as np
import pytest
import hybrid_representable_box as rb
import hybrid_box_residual_subproblem as sub
from test_hybrid_box_residual_subproblem import fixture


def plain(n=1):
    return np.zeros(n),np.ones(n),np.full(n,-1.),np.ones(n)


def test_directed_representable_interval_is_inner_and_preserves_zero():
    rng=np.random.default_rng(83);base=rng.uniform(-1e3,1e3,30);D=rng.uniform(.01,1e3,30);lo=np.full(30,-1e6);hi=-lo;radius=.1
    il,iu,ol,ou=rb.state_intervals(base,D,radius,lo,hi)
    assert np.all(il<=base)and np.all(iu>=base)
    for i in range(30):
        b=Q(float(base[i]));delta=Q(radius)/Q(float(D[i]))
        assert Q(float(il[i]))>=b-delta and Q(float(iu[i]))<=b+delta
        assert Q(float(ol[i]))<=b-delta and Q(float(ou[i]))>=b+delta
    z,D,lo,hi=plain();z[:]=1e16;lo[:]=-1e17;hi[:]=1e17
    il,iu,_,_=rb.state_intervals(z,D,.1,lo,hi);assert il[0]==iu[0]==z[0]


def test_exact_equality_and_true_nextafter_outside_are_distinct():
    base,D,lo,hi=plain();x=np.array([.1]);p,t,u,info=rb.certify_state(x,base,D,.1,lo,hi)
    assert info['exact_comparisons']==1 and info['exact_records'][0]['margin_numerator']=='0'and u[0]<=.1
    assert info['raw_max_upper']>.1
    with pytest.raises(rb.CandidateUncertified,match='exactly outside')as exc:
        rb.certify_state(np.nextafter(x,np.inf),base,D,.1,lo,hi)
    assert exc.value.diagnostics['exact_records'][0]['inside']is False


def test_64_exact_comparisons_and_65th_candidate_stop():
    base,D,lo,hi=plain(65)
    with pytest.raises(rb.CandidateUncertified,match='component qualification budget')as exc:
        rb.certify_state(np.full(65,.1),base,D,.1,lo,hi)
    assert exc.value.diagnostics['exact_comparisons']==64
    p,t,u,info=rb.certify_state(np.full(64,.1),base[:64],D[:64],.1,lo[:64],hi[:64])
    assert info['exact_comparisons']==64 and np.max(u)<=.1


def test_exact_CPU_budget_is_candidate_wide_and_explicit(monkeypatch):
    base,D,lo,hi=plain();times=iter([0.,.2,.2]);monkeypatch.setattr(rb,'process_time',lambda:next(times))
    with pytest.raises(rb.CandidateUncertified,match='CPU qualification budget')as exc:
        rb.certify_state(np.array([.1]),base,D,.1,lo,hi)
    assert exc.value.diagnostics['exact_comparisons']==0


@pytest.mark.parametrize('bad',[np.nan,np.inf,1e-320])
def test_nonfinite_subnormal_or_bad_identity_is_never_optional(bad):
    base,D,lo,hi=plain();x=np.array([bad])
    with pytest.raises(RuntimeError)as exc:rb.certify_state(x,base,D,.1,lo,hi)
    assert not isinstance(exc.value,rb.CandidateUncertified)


def test_hard_box_and_subtraction_cancellation():
    base,D,lo,hi=plain()
    with pytest.raises(rb.CandidateUncertified,match='original box'):rb.certify_state(np.array([2.]),base,D,10.,lo,hi)
    b=dict(u=np.zeros(2),d=np.array([.4,1.]));D=np.ones(3)
    c=rb.representable_candidate(np.array([.1,-2.,-2.]),b,D,np.array([1]),np.array([0]),np.array([0.]),np.array([.2,1.]),np.array([False,True]),10.)
    assert np.array_equal(c['d'],[.2,1.])and c['u'][0]==0
    from hybrid_box_residual_subproblem import exact_difference
    x=np.array([.1]);z=np.array([1e-30]);h,t=exact_difference(x,z)
    assert Q(float(h[0]))+Q(float(t[0]))==Q(float(x[0]))-Q(float(z[0]))


def failure():return rb.CandidateUncertified('finite qualification absent',dict(exact_comparisons=0,exact_CPU_seconds=0.))


def test_main_stage_failure_stops_even_with_prior_valid_Cauchy(monkeypatch):
    m,base,free,dofs,values,lower,crack,r=fixture();real=sub.feasible_candidate;calls=[]
    def candidate(*a,**kw):
        calls.append(1)
        if len(calls)==2:raise failure()
        return real(*a,**kw)
    monkeypatch.setattr(sub,'feasible_candidate',candidate)
    with pytest.raises(rb.CandidateUncertified):sub.solve_box_model(m,base,free,dofs,values,lower,crack,r,np.zeros(2))
    assert len(calls)==2


def test_optional_finite_failure_keeps_certified_main_and_stage_order(monkeypatch):
    m,base,free,dofs,values,lower,crack,r=fixture();real=sub.feasible_candidate;calls=[];stages=[]
    def candidate(*a,**kw):
        calls.append(1)
        if len(calls)==4:raise failure()
        return real(*a,**kw)
    def observe(name,p,best,meta):
        stages.append(name)
        if name=='Cauchy_certified':assert meta['cauchy_model_lower_bound']>=meta['cauchy_required_bound']>0
    monkeypatch.setattr(sub,'feasible_candidate',candidate)
    p=sub.solve_box_model(m,base,free,dofs,values,lower,crack,r,np.zeros(2),stage_observer=observe)
    assert p['optional_Newton_status']=='finite_feasibility_qualification_not_obtained'and p['pred_lower']>=p['cauchy_pred_lower']
    assert stages.index('Cauchy_certified')<stages.index('PG1_complete')<stages.index('PG2_complete')<stages.index('optional_Newton_scaling_start')


@pytest.mark.parametrize('fault',[RuntimeError('nonfinite candidate'),RuntimeError('underflow'),OSError('IO failed')])
def test_optional_true_errors_are_not_swallowed(monkeypatch,fault):
    m,base,free,dofs,values,lower,crack,r=fixture();real=sub.feasible_candidate;calls=[]
    def candidate(*a,**kw):
        calls.append(1)
        if len(calls)==4:raise fault
        return real(*a,**kw)
    monkeypatch.setattr(sub,'feasible_candidate',candidate)
    with pytest.raises(type(fault),match=str(fault)):sub.solve_box_model(m,base,free,dofs,values,lower,crack,r,np.zeros(2))


def test_Cauchy_persistence_error_prevents_optional_work():
    m,base,free,dofs,values,lower,crack,r=fixture();stages=[]
    def save(name,*args):
        stages.append(name)
        if name=='Cauchy_certified':raise OSError('evidence IO failed')
    with pytest.raises(OSError,match='evidence IO'):sub.solve_box_model(m,base,free,dofs,values,lower,crack,r,np.zeros(2),stage_observer=save)
    assert 'optional_Newton_scaling_start'not in stages


def test_saved_R007_overlap_is_certified_without_new_FEM():
    root=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v10_20261021/recovered_verified/archive/train_A');folder=root/'unaccepted_work_points'
    with np.load(folder/'last_box_model.npz',allow_pickle=False)as z:D=z['D'];u=z['base_u'];d=z['base_d']
    with np.load(folder/'last_block_direction.npz',allow_pickle=False)as z:free=z['free_dofs'];pn=np.r_[z['delta_u_free'],z['delta_damage']]
    # Only decode saved lower, no scientific backend/assembly/factorisation.
    with np.load(root/'states/state0000.npz',allow_pickle=False)as z:
        key=next(k for k in z.files if k=='damage');lower=z[key]
    nu=len(free);base=dict(u=u,d=d);lo,hi=sub.box_bounds(base,D,nu,lower,.1);y=np.clip(D*pn,lo,hi);x0=np.r_[u[free],d];x=x0+y/D
    x=np.clip(x,np.r_[np.full(nu,-np.inf),lower],np.r_[np.full(nu,np.inf),np.ones(len(d))])
    for _ in range(2):
        h,t=sub.exact_difference(x,x0);upper=sub.scaled_abs_upper(D,h,t);bad=upper>.1;x[bad]=np.nextafter(x[bad],x0[bad])
    h,t=sub.exact_difference(x,x0);upper=sub.scaled_abs_upper(D,h,t);assert np.count_nonzero(upper>.1)==1
    _,_,certified,info=rb.certify_state(x,x0,D,.1,np.r_[np.full(nu,-np.inf),lower],np.r_[np.full(nu,np.inf),np.ones(len(d))])
    assert max(certified)<=.1 and info['exact_comparisons']<=64
    assert abs(Q(float(D[204978]))*(Q(float(x[204978]))-Q(float(x0[204978]))))<=Q(.1)


def test_exact_accounting_survives_radius_retry_with_same_outer_budget(monkeypatch):
    m,base,free,dofs,values,lower,crack,r=fixture();real=sub.feasible_candidate
    def candidate(*a,**kw):
        p=real(*a,**kw);p['feasibility']['exact_comparisons']=1;p['feasibility']['exact_CPU_seconds']=.001
        return p
    monkeypatch.setattr(sub,'feasible_candidate',candidate)
    a=sub.solve_box_model(m,base,free,dofs,values,lower,crack,r,np.zeros(2))
    c=sub.solve_box_model(m,base,free,dofs,values,lower,crack,r/4,np.zeros(2))
    assert a['exact_comparisons_cumulative']==4 and c['exact_comparisons_cumulative']==8
    assert m.budget.exact_comparisons==8 and m.budget.updates==8
