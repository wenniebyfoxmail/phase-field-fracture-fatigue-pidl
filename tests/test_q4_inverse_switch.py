"""Given-state directional solves only; never primal FEM or trajectory replay."""
from dataclasses import replace
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy import sparse

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from q4_inverse_derivatives import Q4Residual, Variation
from q4_inverse_trajectory import DirectionalTransitionProblem, SensitivityTape
from q4_inverse_switch import DirectionalSolver, SwitchLimits, _assemble, _monotonicity_bounds
from q4_inverse_sparse import SparsePreparationFailure
from test_q4_inverse_offline_interfaces import patch, limits


def problem(r,u,d,bc):
    return DirectionalTransitionProblem(r,u,d,bc,force_tolerance=1.e-12,damage_tolerance=1.e-12,
        force_scale=1.,damage_scale=1.,history_scale=1.)


def solver(p,**kw):
    n=len(p.free_u)+np.count_nonzero(p.interior|p.weak_lower|p.weak_upper)
    args=dict(row_scale=np.ones(n),column_scale=np.ones(n),uniqueness_weights=np.ones(n),
        limits=SwitchLimits(limits(),12,12),minimum_monotonicity=1.e-12,minimum_reciprocal_bound=1.e-12)
    args.update(kw)
    return DirectionalSolver(p,**args)


@pytest.mark.parametrize('gc_direction',[-.01,.01])
def test_q4_weak_lower_solve_matches_release_or_stick(gc_direction):
    r,u,d,bc=patch(weak=True); p=problem(r,u,d,bc)
    result=solver(p).solve(r.zero_variation(),parameters=(0,gc_direction,0),
                          residual_tolerance=1.e-11,solution_tolerance=1.e-8)
    expected=np.maximum(-(1-d)*gc_direction/r.material.gc,0)
    np.testing.assert_allclose(result.variation.damage,expected,atol=2.e-13)
    assert result.record['derivative_unique']
    assert result.record['primal_steps']==0 and result.record['mu_lower']>0


def test_all_branch_hull_contains_selected_history_switch_jacobians():
    r,u,d,bc=patch(); old=replace(r.old,driver=r.evaluate(u,d).driver)
    r=Q4Residual(r.kin,r.material,old); p=problem(r,u,d,bc); s=solver(p)
    from time import monotonic
    lo,hi=_assemble(p,s.nodes,limits(),monotonic())
    oldv=r.zero_variation()
    for direction in (-1.,1.):
        x=np.linspace(-.2,.3,s.size)*direction
        v,out=s._variation(x,oldv,np.zeros(len(bc)),(0,.01,.02))
        J=_assemble(p,s.nodes,limits(),monotonic(),variation=v,old=oldv,parameters=(0,.01,.02))[0]
        assert np.min((J-lo).toarray())>=-2.e-15
        assert np.min((hi-J).toarray())>=-2.e-15
        # Analytic selected matrix must match directional-map finite difference
        # on the same branch, including RHS from material/old-history directions.
        z=np.linspace(.1,.2,s.size); h=1.e-7
        va,oa=s._variation(x+h*z,oldv,np.zeros(len(bc)),(0,.01,.02))
        vb,ob=s._variation(x-h*z,oldv,np.zeros(len(bc)),(0,.01,.02))
        got=np.r_[(oa.force-ob.force)[p.free_u],(oa.damage_residual-ob.damage_residual)[s.nodes]]/(2*h)
        np.testing.assert_allclose(J@z,got,rtol=2.e-7,atol=2.e-10)


def test_interval_bound_covers_every_corner_and_rejects_branch_only_uniqueness():
    lo=sparse.csc_matrix([[2.,-.2],[-.1,3.]])
    hi=sparse.csc_matrix([[2.2,.1],[.3,3.1]])
    mu,L=_monotonicity_bounds(lo,hi,np.array([1.,1.2]))
    assert mu>0
    from itertools import product
    for bits in product((0,1),repeat=4):
        a=np.where(np.array(bits).reshape(2,2),hi.toarray(),lo.toarray())
        assert np.linalg.eigvalsh((a+a.T)/2)[0]>=mu
        assert np.linalg.norm(a,2)<=L
    badlo=sparse.csc_matrix([[-1.]])
    assert _monotonicity_bounds(badlo,sparse.csc_matrix([[1.]]),np.ones(1))[0]<0


def test_uniqueness_inconclusive_stops_before_any_newton_factor(monkeypatch):
    r,u,d,bc=patch(weak=True); s=solver(problem(r,u,d,bc),minimum_monotonicity=1.e6,uniqueness_method='weighted_gershgorin')
    def forbidden(*args,**kw):
        raise AssertionError('uniqueness must fail before Newton')
    monkeypatch.setattr('q4_inverse_switch.splu',forbidden)
    with pytest.raises(SparsePreparationFailure,match='strong-monotonicity bound inconclusive'):
        s.solve(r.zero_variation(),parameters=(0,-.01,0),residual_tolerance=1.e-11,solution_tolerance=1.e-8)


def test_switch_bound_and_budget_failures_do_not_produce_a_solution():
    r,u,d,bc=patch(weak=True); p=problem(r,u,d,bc)
    with pytest.raises(SparsePreparationFailure,match='dimension budget'):
        solver(p,limits=SwitchLimits(limits(max_unknowns=1),12,12)).solve(r.zero_variation(),
            parameters=(0,-.01,0),residual_tolerance=1.e-11,solution_tolerance=1.e-8)
    with pytest.raises(SparsePreparationFailure,match='factor fill budget'):
        solver(p,limits=SwitchLimits(limits(max_factor_nnz=1),12,12)).solve(r.zero_variation(),
            parameters=(0,-.01,0),residual_tolerance=1.e-11,solution_tolerance=1.e-8)


def test_changed_problem_and_nonzero_nominal_kink_reject():
    r,u,d,bc=patch(weak=True); p=problem(r,u,d,bc); s=solver(p)
    p.damage_scale=2.
    with pytest.raises(ValueError,match='changed'):
        s.solve(r.zero_variation(),parameters=(0,-.01,0),residual_tolerance=1.e-11,solution_tolerance=1.e-8)
    p=problem(r,u,d,bc)
    # A nearby nonzero history gap is not an exact mathematical kink.
    old=replace(r.old,driver=r.evaluate(u,d).driver+1.e-14)
    rr=Q4Residual(r.kin,r.material,old)
    with pytest.raises(SparsePreparationFailure,match='nonzero nominal kink'):
        solver(problem(rr,u,d,bc)).solve(rr.zero_variation(),parameters=(0,-.01,0),
            residual_tolerance=1.e-11,solution_tolerance=1.e-8)


@pytest.mark.parametrize('sign',[-1.,1.])
def test_exact_unloaded_amor_switch_with_free_mechanics_and_boundary_lifting(sign):
    r,u,d,bc=patch()
    old=replace(r.old,driver=np.zeros((4,4)))
    r=Q4Residual(r.kin,r.material,old); u=np.zeros_like(u); d=old.damage.copy()
    p=problem(r,u,d,bc); s=solver(p)
    affine=(sign*.03*r.kin.points).ravel()
    result=s.solve(r.zero_variation(),parameters=(0,0,0),boundary_variation=affine[bc],
                   residual_tolerance=1.e-11,solution_tolerance=1.e-8)
    np.testing.assert_allclose(result.variation.displacement,affine,atol=1.e-13)
    np.testing.assert_array_equal(result.variation.damage,np.zeros_like(d))
    assert result.record['derivative_unique']


@pytest.mark.parametrize('dT',[-.01,.01])
def test_exact_fatigue_threshold_directional_solve(dT):
    from hybrid_history import fatigue_factor
    r,u,_,bc=patch()
    m=replace(r.material,gc=.001)
    a=np.full((4,4),m.alpha_t)
    old=replace(r.old,accumulated=a,fatigue=fatigue_factor(a,m.alpha_t,m.power))
    r=Q4Residual(r.kin,m,old)
    from damage_conditioned_equilibrium import tensile_energy
    psi=tensile_energy(r.kin,u,youngs_modulus=m.youngs_modulus,poisson_ratio=m.poisson_ratio)[0]
    d=np.full(9,1-m.gc/((8/3)*m.length_scale*2*psi[0,0]))
    # Fully supplied displacement eliminates unrelated mechanics coupling.
    p=problem(r,u,d,np.arange(len(u)))
    result=solver(p).solve(r.zero_variation(),parameters=(0,0,dT),
        residual_tolerance=1.e-11,solution_tolerance=1.e-8)
    df=min(m.power*dT/(2*m.alpha_t),0.)
    np.testing.assert_allclose(result.variation.damage,-(1-d)*df,atol=2.e-13)
    assert result.record['derivative_unique']


def test_all_prescribed_empty_directional_problem_is_unique_without_factor(monkeypatch):
    r,u,d,_=patch(); r=Q4Residual(r.kin,r.material,replace(r.old,driver=np.zeros((4,4))))
    p=problem(r,np.zeros_like(u),r.old.damage.copy(),np.arange(len(u)))
    def forbidden(*a,**kw):
        raise AssertionError('zero-dimensional problem must not factor')
    monkeypatch.setattr('q4_inverse_switch.splu',forbidden)
    result=solver(p).solve(r.zero_variation(),parameters=(.1,.01,0),
        residual_tolerance=1.e-11,solution_tolerance=1.e-8)
    assert result.record['unknowns']==0 and result.record['iterations']==0


def test_ldlt_interval_uniqueness_bound_and_indefinite_counterexample():
    from time import monotonic
    from q4_inverse_switch import _ldlt_monotonicity_bounds
    lo=sparse.csc_matrix([[2.,.8],[.8,2.]])
    hi=sparse.csc_matrix([[2.1,.9],[.9,2.1]])
    mu,L,record=_ldlt_monotonicity_bounds(lo,hi,limits(),monotonic())
    assert 0<mu<1.2 and L>=2.9
    assert record['uniqueness_factorizations']==1
    # G(x)=1-x, x>=0 admits x=0 and x=1. A selected min-map Jacobian
    # at x=0 is +1, but global VI uniqueness is false and must not certify.
    with pytest.raises(SparsePreparationFailure,match='positive-pivot'):
        _ldlt_monotonicity_bounds(sparse.csc_matrix([[-1.]]),sparse.csc_matrix([[-1.]]),limits(),monotonic())


@pytest.mark.parametrize('constant,root',[(-1.,0.),(1.,-.5)])
def test_upper_natural_map_sticking_and_release_equations(constant,root):
    from types import SimpleNamespace
    p=SimpleNamespace(free_u=np.array([],dtype=int),weak_lower=np.array([False]),weak_upper=np.array([True]))
    s=DirectionalSolver.__new__(DirectionalSolver); s.problem=p
    s.nodes=np.array([0]); s.cols=s.rows=np.ones(1); s.size=1
    def supplied(x,*args):
        return SimpleNamespace(damage=x.copy()),SimpleNamespace(force=np.zeros(0),damage_residual=2*x+constant)
    s._variation=supplied
    value,*_=s._natural(np.array([root]),SimpleNamespace(damage=np.zeros(1)),None,None,False,0.)
    np.testing.assert_array_equal(value,[0.])


def test_switch_tape_atomic_failure_commit_and_duplicate_rejection():
    r,u,d,bc=patch(weak=True); p=problem(r,u,d,bc); point=r.evaluate(u,d)
    new=replace(r.old,displacement=u,damage=d,accumulated=point.accumulated,
        driver=point.driver,fatigue=point.fatigue,version=1,load_index=1,load_id='given-switch')
    tape=SensitivityTape(r.old,r.zero_variation(),initial_binding_id='unit-conditioned-state',
                         initialization_policy='fixed_recovered_profile',parameter_direction=(0,-.01,0))
    before=(tape.state.fingerprint(),tape.variation,tape.receipts)
    with pytest.raises(SparsePreparationFailure):
        tape.advance_switch_given(solver(p,minimum_monotonicity=1.e6),new,
            expected_load_id='given-switch',transition_tolerance=1.e-12,
            residual_tolerance=1.e-11,solution_tolerance=1.e-8)
    assert (tape.state.fingerprint(),tape.variation,tape.receipts)==before
    receipt=tape.advance_switch_given(solver(p),new,expected_load_id='given-switch',
        transition_tolerance=1.e-12,residual_tolerance=1.e-11,solution_tolerance=1.e-8)
    assert receipt['directional']['derivative_unique'] and receipt['primal_commits']==0
    assert receipt['parameters']==(0,-.01,0) and len(tape.receipts)==1
    with pytest.raises(ValueError,match='stale'):
        tape.advance_switch_given(solver(p),new,expected_load_id='given-switch',
            transition_tolerance=1.e-12,residual_tolerance=1.e-11,solution_tolerance=1.e-8)


def test_switch_tape_never_calls_solver_for_mismatched_committed_history(monkeypatch):
    r,u,d,bc=patch(weak=True); s=solver(problem(r,u,d,bc)); point=r.evaluate(u,d)
    new=replace(r.old,displacement=u,damage=d,accumulated=point.accumulated+.01,
        driver=point.driver,fatigue=point.fatigue,version=1,load_index=1,load_id='given-switch')
    tape=SensitivityTape(r.old,r.zero_variation(),initial_binding_id='unit',
        initialization_policy='fixed_recovered_profile',parameter_direction=(0,-.01,0))
    def forbidden(*args,**kw):
        raise AssertionError('transition must reject before directional solve')
    monkeypatch.setattr(s,'solve',forbidden)
    with pytest.raises(ValueError,match='committed history differs'):
        tape.advance_switch_given(s,new,expected_load_id='given-switch',transition_tolerance=1.e-12,
            residual_tolerance=1.e-11,solution_tolerance=1.e-8)
    assert tape.receipts==()


@pytest.mark.parametrize('oldA',[0.,.3])
def test_switch_solution_transmits_old_history_and_moving_lower(oldA):
    r,u,d,bc=patch(weak=True); p=problem(r,u,d,bc)
    z=r.zero_variation()
    old=Variation(z.displacement,np.full(9,.02),np.full((4,4),oldA),np.full((4,4),.7))
    result=solver(p).solve(old,parameters=(0,0,0),
        residual_tolerance=1.e-11,solution_tolerance=1.e-8)
    expected=np.maximum((1-d)*r.material.power*oldA/(2.+r.material.alpha_t),.02)
    np.testing.assert_allclose(result.variation.damage,expected,atol=2.e-13)
    np.testing.assert_array_equal(result.variation.accumulated,old.accumulated)
    check,_=p.check(result.variation,old,parameters=(0,0,0),tolerance=1.e-11)
    assert check.satisfies_directional_equations


def test_solver_configuration_is_bound_and_nonunit_scaling_preserves_solution():
    r,u,d,bc=patch(weak=True); p=problem(r,u,d,bc); n=9
    s=solver(p,row_scale=np.linspace(.8,1.2,n),column_scale=np.linspace(1.1,.9,n))
    result=s.solve(r.zero_variation(),parameters=(0,-.01,0),
        residual_tolerance=1.e-11,solution_tolerance=1.e-8)
    np.testing.assert_allclose(result.variation.damage,(1-d)*.01/r.material.gc,atol=2.e-13)
    s.rows=np.ones(n)
    with pytest.raises(ValueError,match='configuration changed'):
        s.solve(r.zero_variation(),parameters=(0,-.01,0),residual_tolerance=1.e-11,solution_tolerance=1.e-8)
