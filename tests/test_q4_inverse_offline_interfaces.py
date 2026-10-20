"""New offline interfaces on supplied arrays only; no primal/timeline solve."""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest
from scipy import sparse
from scipy.sparse.linalg import LinearOperator

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"source"))
from hybrid_history import AcceptedState, fatigue_factor
from hybrid_kinematics import build_portable_native_q4_kinematics
from q4_inverse_derivatives import ImplicitStep, Material, NonregularBranch, Q4Residual, Variation, Margins
from q4_inverse_sparse import (SparseLimits, SparsePreparationFailure, SparseSensitivityProvider,
                               assemble_consistent_sparse, _comparison_inverse_inf)
from q4_inverse_contracts import (InitialBinding, ReactionBinding, backend_physics_id,
    matlab_block_dofs_to_interleaved, matlab_block_displacement_to_interleaved,
    hdf_native_history_to_logical)
from q4_inverse_trajectory import DirectionalTransitionProblem, SensitivityTape
from test_q4_inverse_derivatives import fixture


def limits(**kw):
    values = dict(max_unknowns=40, max_elements=8, max_matrix_nnz=2000,
        max_factor_nnz=2000, max_product_work=100000, chunk_elements=1, wall_seconds=5.)
    values.update(kw)
    return SparseLimits(**values)


def patch(weak=False):
    points = np.array([[x, y] for y in (0., .5, 1.) for x in (0., .5, 1.)])
    cells = np.array([[0, 1, 4, 3], [1, 2, 5, 4], [3, 4, 7, 6], [4, 5, 8, 7]])
    kin = build_portable_native_q4_kinematics(points, cells)
    m = Material(gc=.08, alpha_t=.2); u = (.3*points).ravel()
    a = np.full((4, 4), 2.); f = fatigue_factor(a, m.alpha_t, m.power)
    from damage_conditioned_equilibrium import tensile_energy
    psi = tensile_energy(kin, u, youngs_modulus=m.youngs_modulus,
                         poisson_ratio=m.poisson_ratio)[0]
    dg = 1-m.gc*f[0, 0]/((8/3)*m.length_scale*2*psi[0, 0])
    old = AcceptedState(np.zeros(18), np.full(9, dg if weak else .1), a,
         np.full((4, 4), 10.), f, np.zeros((4, 4)), 0, 0, "patch",
         backend_physics_id(m), "given-start")
    r = Q4Residual(kin, m, old); d = np.full(9, dg)
    bc = np.arange(18) if weak else np.array([i for i in range(18) if i not in (8, 9)])
    return r, u, d, bc


@pytest.mark.parametrize("accumulating", [False, True])
@pytest.mark.parametrize("compression", [False, True])
def test_sparse_local_blocks_equal_independent_matrix_free_jvp(accumulating, compression):
    kin, m, old, u, d = fixture(compression, accumulating)
    r = Q4Residual(kin, m, old)
    free = np.arange(2, 8); interior = np.arange(4)
    def mv(x):
        v = r.zero_variation(); v.displacement[free] = x[:6]; v.damage[:] = x[6:]
        out = r.directional(u, d, v.displacement, v.damage)
        return np.r_[out.force[free], out.damage_residual]
    # Deliberately nonstationary GIVEN fields for assembly equality only.
    step = SimpleNamespace(r=r, u=u, d=d, free_u=free, interior=interior,
                           size=10, margins=Margins(), operator=LinearOperator((10, 10), matvec=mv))
    matrix = assemble_consistent_sparse(step, limits())
    dense = np.column_stack([mv(x) for x in np.eye(10)])
    np.testing.assert_allclose(matrix.toarray(), dense, rtol=2.e-14, atol=3.e-15)


def test_sparse_provider_scaling_bound_and_solution_on_analytic_patch():
    r, u, d, bc = patch()
    step = ImplicitStep(r, u, d, bc, force_tolerance=1.e-12, damage_tolerance=1.e-12)
    rows = np.linspace(.8, 1.5, step.size); cols = np.linspace(1.1, .9, step.size)
    provider = SparseSensitivityProvider(step, row_scale=rows, column_scale=cols, limits=limits())
    scaled = provider.matrix.toarray()*cols[None, :]/rows[:, None]
    actual = np.linalg.svd(scaled, compute_uv=False)
    assert 0 < provider.evidence.sigma_min <= actual[-1]*(1+1.e-12)
    assert provider.evidence.sigma_max >= actual[0]*(1-1.e-12)
    v, _ = step.propagate(r.zero_variation(), parameters=(.1, .01, .03),
        solve=provider, regularity=provider.evidence, linear_tolerance=1.e-11)
    np.testing.assert_allclose(v.displacement, 0, atol=2.e-15)
    assert provider.record['native_size_execution_verified'] is False
    with pytest.raises(ValueError, match="different exact operator"):
        provider(LinearOperator(step.operator.shape, matvec=lambda x:x), np.ones(step.size))


def test_comparison_triangular_bounds_exceed_exact_inverse_norms():
    from time import monotonic
    lower = sparse.csc_matrix([[1.,0,0],[-.3,1,0],[.4,-.2,1]])
    upper = sparse.csc_matrix([[2.,-.4,.1],[0,1.5,.5],[0,0,.7]])
    for a, lo in [(lower, True), (upper, False), (lower.T, False), (upper.T, True)]:
        bound = _comparison_inverse_inf(a, lo, monotonic(), limits())
        actual = np.linalg.norm(np.linalg.inv(a.toarray()), ord=np.inf)
        assert bound >= actual*(1-1.e-15)


def test_sparse_limits_fail_before_factorization(monkeypatch):
    r, u, d, bc = patch()
    step = ImplicitStep(r, u, d, bc, force_tolerance=1.e-12, damage_tolerance=1.e-12)
    def forbidden(*a, **k):
        raise AssertionError('must fail budget before any factorization')
    monkeypatch.setattr('q4_inverse_sparse.splu', forbidden)
    with pytest.raises(SparsePreparationFailure, match="dimension budget"):
        SparseSensitivityProvider(step, row_scale=np.ones(11), column_scale=np.ones(11),
                                  limits=limits(max_unknowns=1))


@pytest.mark.parametrize("kw,stage", [({'max_factor_nnz':1}, 'factorization'),
                                      ({'max_product_work':1}, 'factor_residual')])
def test_sparse_fill_product_caps_fail_closed(kw, stage):
    r, u, d, bc = patch()
    step = ImplicitStep(r, u, d, bc, force_tolerance=1.e-12, damage_tolerance=1.e-12)
    with pytest.raises(SparsePreparationFailure) as failure:
        SparseSensitivityProvider(step, row_scale=np.ones(11), column_scale=np.ones(11), limits=limits(**kw))
    assert failure.value.stage == stage


def test_sparse_null_mode_cannot_advance_implicit_tangent():
    kin, m, old, u, _ = fixture(accumulating=False)
    old = replace(old, damage=np.ones(4)); r = Q4Residual(kin, m, old)
    step = ImplicitStep(r, u, np.ones(4), np.array([], dtype=int),
                        force_tolerance=1.e-12, damage_tolerance=1.e-12)
    try:
        provider = SparseSensitivityProvider(step, row_scale=np.ones(8), column_scale=np.ones(8), limits=limits())
    except SparsePreparationFailure:
        return
    with pytest.raises(NonregularBranch):
        step.propagate(r.zero_variation(), solve=provider, regularity=provider.evidence,
                       linear_tolerance=1.e-12)


def test_stable_sensitivity_tape_atomic_and_once_only():
    r, u, d, bc = patch()
    step = ImplicitStep(r, u, d, bc, force_tolerance=1.e-12, damage_tolerance=1.e-12)
    p = r.evaluate(u, d)
    new = replace(r.old, displacement=u, damage=d, accumulated=p.accumulated,
                  driver=p.driver, fatigue=p.fatigue, version=1, load_index=1, load_id='next')
    tape = SensitivityTape(r.old, r.zero_variation(), initial_binding_id='unit-conditioned-state',
                          initialization_policy='fixed_recovered_profile')
    provider = SparseSensitivityProvider(step, row_scale=np.ones(11), column_scale=np.ones(11), limits=limits())
    before = (tape.state.fingerprint(), tape.variation, tape.receipts)
    def failed(*a):
        raise RuntimeError('unit callback failure, no retry')
    with pytest.raises(RuntimeError):
        tape.advance_given(step, new, expected_load_id='next', transition_tolerance=1.e-12,
            parameters=(.1,0,0), solve=failed, regularity=provider.evidence, linear_tolerance=1.e-12)
    assert (tape.state.fingerprint(), tape.variation, tape.receipts) == before
    receipt = tape.advance_given(step, new, expected_load_id='next', transition_tolerance=1.e-12,
            parameters=(.1,0,0), solve=provider, regularity=provider.evidence, linear_tolerance=1.e-12)
    assert receipt['derivative_commits'] == 1 and receipt['primal_commits'] == 0
    with pytest.raises(ValueError, match='stale'):
        tape.advance_given(step, new, expected_load_id='next', transition_tolerance=1.e-12,
            solve=provider, regularity=provider.evidence, linear_tolerance=1.e-12)
    assert len(tape.receipts) == 1


@pytest.mark.parametrize('gc_direction', [-.01, .01])
def test_weak_lower_switch_direction_and_history_equations(gc_direction):
    r, u, d, bc = patch(weak=True)
    with pytest.raises(NonregularBranch, match='weakly active'):
        ImplicitStep(r, u, d, bc, force_tolerance=1.e-12, damage_tolerance=1.e-12)
    problem = DirectionalTransitionProblem(r, u, d, bc,
        force_tolerance=1.e-12, damage_tolerance=1.e-12, force_scale=1., damage_scale=1., history_scale=1.)
    z = r.zero_variation()
    dd = np.maximum(-(1-d)*gc_direction/r.material.gc, 0)
    fields = r.directional(u, d, z.displacement, dd, parameters=(0,gc_direction,0), strict=False)
    candidate = Variation(z.displacement, dd, fields.accumulated, fields.driver)
    check, _ = problem.check(candidate, z, parameters=(0,gc_direction,0), tolerance=1.e-12)
    assert check.satisfies_directional_equations and not check.derivative_unique
    bad = replace(candidate, damage=np.full(9, -.1))
    check, _ = problem.check(bad, z, parameters=(0,gc_direction,0), tolerance=1.e-12)
    assert not check.satisfies_directional_equations and check.weak_primal_violation > 0
    assert problem.stop_record()['history_commits'] == 0
    tape = SensitivityTape(r.old, z, initial_binding_id='unit', initialization_policy='fixed_recovered_profile')
    with pytest.raises(TypeError, match='switches stop'):
        tape.advance_given(problem, r.old, expected_load_id='next', transition_tolerance=1.e-12)


def test_matlab_axis_dof_and_history_conversions_are_explicit():
    np.testing.assert_array_equal(matlab_block_dofs_to_interleaved([1,3,4,6],3), [0,4,1,5])
    np.testing.assert_array_equal(matlab_block_displacement_to_interleaved([10,20,30,1,2,3],3), [10,1,20,2,30,3])
    source = np.arange(4*4*3).reshape(4,4,3)
    logical = hdf_native_history_to_logical(source,3)
    assert logical.shape == (3,4,4) and logical[2,1,3] == source[3,1,2]
    with pytest.raises(ValueError):
        matlab_block_dofs_to_interleaved([0,2],3)


def test_initial_binding_and_legacy_reaction_cannot_be_mislabelled_fresh():
    kin,m,old,_,_ = fixture()
    zero = np.zeros((1,4))
    initial = replace(old, physics_id=backend_physics_id(m), load_id='recovery',
                      accumulated=zero, driver=zero, fatigue=np.ones((1,4)))
    binding = InitialBinding('source-exact',initial.mesh_id,initial.physics_id,'recovery','fixed_recovered_profile')
    assert binding.validate(initial,m)['recovery_counted_as_physical_step'] is False
    with pytest.raises(ValueError, match='never silently zero'):
        replace(binding,policy='differentiate_recovery').validate(initial,m)
    with pytest.raises(ValueError, match='material identity'):
        binding.validate(initial,replace(m,gc=.09))
    bc = matlab_block_dofs_to_interleaved([4,5],4)
    reaction = ReactionBinding('legacy_Q4','bottomY','mirror-and-source-order',
        'post_history_commit','cached_final_staggered_K_before_commit','normalized_length','normalized_force',
        bc,-np.ones(2))
    force = np.arange(8.)
    with pytest.raises(ValueError,match='not a fresh'):
        reaction.project(force,current_family='legacy_Q4',current_boundary_id='bottomY',current_state_phase='post_history_commit')
    fresh = replace(reaction,force_phase='fresh_at_exact_given_ud')
    assert fresh.project(force,current_family='legacy_Q4',current_boundary_id='bottomY',current_state_phase='post_history_commit') == -force[bc].sum()
    with pytest.raises(ValueError,match='solve/commit'):
        fresh.project(force,current_family='new_nodalK',current_boundary_id='bottomY',current_state_phase='precommit')
