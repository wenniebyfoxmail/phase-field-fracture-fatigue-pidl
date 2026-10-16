"""Prepared, NOT RUN: E019-D01 fixed synthetic unit tests; no array-file input."""
from contextlib import ExitStack
from decimal import Decimal, localcontext
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import aa2024_qsubspace_diagnostic as d


@pytest.fixture(autouse=True)
def zero_decompositions_and_reads():
    with ExitStack() as stack:
        d.guards(stack)
        yield
        assert np.load.call_count == 0
        assert np.linalg.svd.call_count == 0
        assert d.original.linalg.svd.call_count == 0


def test_hadamard_exact_dyadic_orthogonality():
    o = d.hadamard16()
    assert o.shape == (16, 16) and set(o.ravel()) == {-.25, .25}
    assert np.array_equal(d.scalar_product(o.T, o), np.eye(16))


def test_decimal_conversion_preserves_binary_float_not_display_string():
    assert d.dec([[.1]])[0][0] == Decimal.from_float(.1)
    assert d.dec([[.1]])[0][0] != Decimal('.1')


def test_decimal_product_and_shapes():
    with localcontext() as ctx:
        ctx.prec = 80
        a, b = d.dec([[1., 2.], [3., 4.]]), d.dec([[5.], [6.]])
        assert d.dm(a, b) == [[Decimal(17)], [Decimal(39)]]
        assert d.transpose(a) == [[Decimal(1), Decimal(3)], [Decimal(2), Decimal(4)]]
        with pytest.raises(ValueError, match='shape'):
            d.dm(a, [[Decimal(1)]])


@pytest.mark.parametrize('kind,delta', [('matrix', 2e-12), ('vector', 2e-15), ('square', 2e-18)])
def test_original_tolerances_are_not_widened(kind, delta):
    with pytest.raises(ValueError, match='identity'):
        d.check([[delta]], [[0.]], 'intentional tolerance rejection', kind)
    d.check([[delta/4]], [[0.]], 'below original absolute tolerance', kind)


def test_decimal_original_vector_tolerance():
    with pytest.raises(ValueError, match='decimal identity'):
        d.dcheck(d.dec([[2e-15]]), d.dec([[0.]]), 'intentional rejection', 'vector')


@pytest.mark.parametrize('bad', [np.array([np.nan]), np.array([np.inf]), np.zeros((1, 1, 1))])
def test_nonfinite_or_nonmatrix_input_is_rejected(bad):
    with pytest.raises(ValueError, match='finite matrix'):
        d.array2(bad)


def test_only_fixed_analytic_case_ids():
    with pytest.raises(ValueError, match='fixed case'):
        d.analytic_case('real_or_extra_case')


def test_fixed_constants_and_no_numeric_rank_estimation():
    H, A, L, V, s, y, constants = d.analytic_case('C1')
    assert H.shape == (16, 3) and A.shape == (16, 16) and L.shape == V.shape == (16, 5)
    assert y.shape == (16, 1)
    assert np.array_equal(s, [1., 2.**-4, 2.**-12, 2.**-24, 2.**-32])
    assert np.all(s > 10*constants['tau']) and constants['known_retained_modes'] == 5
    assert np.linalg.matrix_rank.call_count == 0


def test_clean_baseline_factor_and_projection_ledgers():
    with localcontext() as ctx:
        ctx.prec = 80
        H, A, L, V, s, y, _ = d.analytic_case('C1')
        factor = d.factor_layer(H, A, L, V, s)
        projection, data = d.projection_layer('C1', H, L, y)
        assert factor['factor_reconstruction_pass']
        assert projection['Q_identity_pass'] and projection['Q_identity_ratio'] <= 1
        o = d.hadamard16()
        expected_p = (2.**-8*(o[:, 3]+o[:, 7]))[:, None]
        d.check(data['p'], expected_p, 'analytic clean p', 'vector')
        d.check(data['r'], (-2.**-12*o[:, 13])[:, None], 'analytic clean r', 'vector')


@pytest.mark.parametrize('name', ['C2', 'C3'])
def test_declared_negative_control_keeps_original_failed_identity(name):
    with localcontext() as ctx:
        ctx.prec = 80
        H, A, L, V, s, y, _ = d.analytic_case(name)
        factor = d.factor_layer(H, A, L, V, s)
        projection, _ = d.projection_layer(name, H, L, y)
        assert factor['factor_reconstruction_pass']
        assert not projection['Q_identity_pass'] and projection['Q_identity_ratio'] > 1
        assert projection['Q_identity_outcome'] == 'expected_not_passed_at_original_tolerance'
        assert float(factor['factor_HtL_max']) > d.ATOL['matrix']
        assert float(projection['p_existing_subspace_max_mm']) > float(projection['p_new_evaluation_max_mm'])


def test_input_and_factor_controls_share_p_not_input_matrix():
    with localcontext() as ctx:
        ctx.prec = 80
        outputs, inputs = [], []
        for name in ('C2', 'C3'):
            H, A, L, V, s, y, _ = d.analytic_case(name)
            inputs.append(A)
            outputs.append(d.projection_layer(name, H, L, y)[1])
        assert not np.array_equal(inputs[0], inputs[1])
        assert outputs[0]['p'] == outputs[1]['p'] and outputs[0]['r'] == outputs[1]['r']


def test_C0_synthetic_A_ledger_and_original_sampling_only():
    with localcontext() as ctx:
        ctx.prec = 80
        xy = np.array([[-13.05, -4.95], [-8.55, -2.25], [-4.05, 2.25], [-.45, 4.95],
                       [.45, -4.95], [4.05, -2.25], [8.55, 2.25], [13.05, 4.95]])
        S, _, _ = d.original.sampling(xy)
        bd = d.original.prior.rectangular_mesh()[2]
        free = np.flatnonzero(~np.repeat(bd, 2))
        scale, H = d.original.rigid_basis(xy, np.arange(1., 9.))
        C = scale[:, None]*S[:, free].toarray()
        assert C.shape == (16, 1482)
        row = d.a_layer(H, C, d.original.quotient(H, C))
        assert Decimal(row['A_ledger_error_max']) <= Decimal.from_float(d.ATOL['matrix'])


def test_unexpected_clean_Q_failure_is_not_accepted_as_negative_control():
    H, _, L, _, _, y, _ = d.analytic_case('C2')
    with localcontext() as ctx:
        ctx.prec = 80
        with pytest.raises(ValueError, match='unexpected frozen Q'):
            d.projection_layer('C1', H, L, y)


def test_runtime_prohibitions_are_armed_without_calling_decompositions():
    assert np.linalg.svd.side_effect is d.forbidden
    assert d.original.linalg.svd.side_effect is d.forbidden
    assert d.original.project.side_effect is d.forbidden
    assert np.load.side_effect is d.forbidden
    # Do not attempt SVD even to test its guard.


def test_fresh_canonical_output_guard_writes_nothing(tmp_path):
    out = tmp_path/'not_the_approved_output'
    with pytest.raises(ValueError, match='fresh canonical'):
        d.run(out, '0'*40)
    assert not out.exists()


def test_budget_failure_has_no_retry():
    with pytest.raises(TimeoutError, match='soft60s'):
        d.within(0., lambda: 60.)


def test_scalar_vs_decimal_contraction_reference():
    with localcontext() as ctx:
        ctx.prec = 80
        a = np.array([[.1, .3, -.2], [1., -.7, .9]])
        b = np.array([[.002], [-.004], [.003]])
        d.crosscheck(a, b, 'synthetic scalar reference', 'vector')
