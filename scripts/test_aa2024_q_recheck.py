#!/usr/bin/env python3
"""Command A: artificial unit tests only. Not run during package preparation."""
import argparse
import logging
import os
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
import warnings

warnings.simplefilter('error')


class StopLogging(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            raise RuntimeError('unexpected logging warning: '+record.getMessage())


logging.getLogger().addHandler(StopLogging(level=logging.WARNING))

START = time.monotonic()
import numpy as np
import aa2024_q_recheck as candidate
import aa2024_q_verify as independent


def forbidden(*args, **kwargs):
    raise AssertionError('actual decomposition, solver or array read forbidden in command A')


class Units(unittest.TestCase):
    def setUp(self):
        self.H = np.eye(12)[:, :3]
        self.L = np.eye(12)[:, 3:8]
        self.y = .004*self.L[:, 0]+.0002*np.eye(12)[:, 8]

    def tearDown(self):
        if time.monotonic()-START >= 60:
            raise TimeoutError('unit command soft60s incomplete')

    def repair(self, L=None, qr=None):
        def exact(a, **kwargs):
            self.assertEqual(kwargs, dict(mode='economic', pivoting=False, check_finite=True))
            return self.L.copy(), np.eye(5)
        return candidate.repair(self.H, self.L if L is None else L, self.y,
                                candidate.Factors(qr=exact if qr is None else qr, svd=forbidden))

    def test_clean_projection(self):
        result = self.repair()
        np.testing.assert_array_equal(result['p'], .004*self.L[:, 0])
        candidate.close(result['r'], -.0002*np.eye(12)[:, 8], 'known residual')

    def test_given_leak_removed_before_stub_qr(self):
        leaked = self.L.copy(); leaked[:, -1] += 2**-20*self.H[:, 0]
        def known_qr(a, **kwargs):
            np.testing.assert_array_equal(a, self.L)
            return self.L.copy(), np.eye(5)
        result = self.repair(leaked, known_qr)
        candidate.close(result['B'], self.L, 'B')

    def test_candidate_inputs_not_overwritten(self):
        H, L, y = self.H.copy(), self.L.copy(), self.y.copy()
        self.repair()
        for a, b in ((H, self.H), (L, self.L), (y, self.y)):
            np.testing.assert_array_equal(a, b)

    def test_qr_signs_coupled(self):
        def negative(a, **kwargs):
            return -self.L, -np.eye(5)
        result = self.repair(qr=negative)
        np.testing.assert_array_equal(result['U'], self.L)
        np.testing.assert_array_equal(result['T'], np.eye(5))

    def test_zero_qr_diag_stops(self):
        def bad(a, **kwargs):
            return self.L, np.zeros((5, 5))
        with self.assertRaisesRegex(candidate.Stop, 'diagonal'):
            self.repair(qr=bad)

    def test_nonfinite_qr_stops(self):
        def bad(a, **kwargs):
            return self.L*np.nan, np.eye(5)
        with self.assertRaisesRegex(candidate.Stop, 'finite'):
            self.repair(qr=bad)

    def test_eta_boundary_exact(self):
        def half(a, **kwargs):
            return self.L, .5*np.eye(5)
        result = self.repair(.5*self.L, half)
        self.assertEqual(float(result['eta']), .5)

    def test_eta_no_tolerance(self):
        def outside(a, **kwargs):
            return self.L, .4999999*np.eye(5)
        with self.assertRaisesRegex(candidate.Stop, 'eta hard'):
            self.repair(.4999999*self.L, outside)

    def test_eta_row_sum_not_max_element(self):
        def bad(a, **kwargs):
            T = np.eye(5); T[0, 1:3] = .3
            return self.L, T
        with self.assertRaisesRegex(candidate.Stop, 'eta hard'):
            self.repair(qr=bad)

    def test_no_second_qr(self):
        f = candidate.Factors(qr=lambda a, **kw: (self.L, np.eye(5)), svd=forbidden)
        f.qr(self.L); f.qr(self.L)
        with self.assertRaisesRegex(candidate.Stop, 'extra QR'):
            f.qr(self.L)

    def test_one_svd_fixed_driver_stub_only(self):
        seen = []
        def fake(a, **kwargs):
            seen.append(kwargs); return ('left', 's', 'right')
        f = candidate.Factors(qr=forbidden, svd=fake)
        self.assertEqual(f.svd(np.ones((2, 2))), ('left', 's', 'right'))
        self.assertEqual(seen, [dict(full_matrices=False, check_finite=True, lapack_driver='gesvd')])
        with self.assertRaisesRegex(candidate.Stop, 'extra SVD'):
            f.svd(np.ones((2, 2)))

    def test_vector_vs_matrix_units(self):
        with self.assertRaises(candidate.Stop):
            candidate.close(np.array([2e-15]), np.zeros(1), 'vector')
        candidate.close(np.array([2e-15]), np.zeros(1), 'matrix', 'matrix')

    def test_square_unit_threshold(self):
        candidate.close(1e-18, 0., 'inclusive', 'square')
        with self.assertRaises(candidate.Stop):
            candidate.close(1.01e-18, 0., 'over', 'square')

    def test_budget_exact_stop(self):
        times = iter((0., 59.99, 60.))
        budget = candidate.Budget(lambda: next(times))
        self.assertEqual(budget.check(), 59.99)
        with self.assertRaises(TimeoutError):
            budget.check()

    def test_cst_affine_and_component_order(self):
        xy = np.array([[.13, .27], [-.28, -.32], [1.19, .01]])
        S, _, _ = candidate.sampling(xy)
        mesh, _, _ = candidate.mesh_definition()
        values = np.c_[2+3*mesh[:, 0]-mesh[:, 1], -1+mesh[:, 0]+2*mesh[:, 1]]
        expected = np.c_[2+3*xy[:, 0]-xy[:, 1], -1+xy[:, 0]+2*xy[:, 1]]
        candidate.close(candidate.mm(S, values.ravel()).reshape(-1, 2), expected, 'affine', 'matrix')
        second, _, _ = independent.stencil(xy)
        np.testing.assert_array_equal(second, S)

    def test_roi_boundary_excluded(self):
        with self.assertRaisesRegex(candidate.Stop, 'ROI'):
            candidate.sampling(np.array([[16.2, 0.]]))

    def test_selective_npz_keys_no_other_decode(self):
        class Fake:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def __getitem__(self, key):
                if key not in ('ids', 'xy'): raise AssertionError('unexpected decoded key')
                return key
        with patch.object(candidate, 'safe_path') as safe, patch.object(np, 'load', return_value=Fake()) as load:
            self.assertEqual(candidate.selective('artificial-placeholder-not-opened', ('ids', 'xy')), {'ids': 'ids', 'xy': 'xy'})
            load.assert_called_once_with('artificial-placeholder-not-opened', allow_pickle=False)
            safe.assert_called_once_with('artificial-placeholder-not-opened', file=True)

    def test_opaque_permission_before_any_read(self):
        with patch.object(candidate, 'sha', side_effect=forbidden):
            with self.assertRaisesRegex(candidate.Stop, 'opaque'):
                candidate.load_real(False)

    def test_independent_reference_full_vector(self):
        result = self.repair()
        for method in ('fsum', 'decimal80'):
            with independent.localcontext() as ctx:
                ctx.prec = 80
                projected = independent.float_vector(independent.project(self.L, self.y, method, independent.Timer()))
                candidate.close(projected, result['p'], 'independent '+method)

    def test_reference_failure_not_ratio_scalar_equality(self):
        with self.assertRaisesRegex(independent.Rejected, 'REFERENCE_PATH_UNRESOLVED'):
            independent.equal(np.array([3e-15]), np.zeros(1), 'REFERENCE_PATH_UNRESOLVED')

    def test_logging_warning_stops(self):
        record = logging.LogRecord('artificial-unit', logging.WARNING, '', 0, 'artificial expected warning guard', (), None)
        with self.assertRaisesRegex(RuntimeError, 'unexpected logging warning'):
            StopLogging().emit(record)

    def test_python_warning_stops(self):
        with self.assertRaises(UserWarning):
            warnings.warn('artificial expected warning guard', UserWarning)

    def test_symlink_ancestor_rejected_without_IO(self):
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaisesRegex(candidate.Stop, 'symlink'):
                candidate.safe_path(Path('/artificial-not-created/leaf'))

    def test_runtime_code_change_rejected_stub(self):
        with patch.object(candidate, 'snapshot', return_value='changed'), patch.object(candidate, 'code_hashes', return_value={}):
            with self.assertRaisesRegex(candidate.Stop, 'HEAD changed'):
                candidate.final_identity(Path('/artificial'), 'baseline', 'initial', {})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    initial_head = candidate.snapshot(repo, args.source_commit)
    initial_hashes = candidate.code_hashes()
    candidate.require(all(os.environ.get(k) == '1' for k in candidate.THREADS) and os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'single CPU environment')
    warnings.simplefilter('error')
    with patch.object(candidate.linalg, 'qr', side_effect=forbidden), patch.object(candidate.linalg, 'svd', side_effect=forbidden), \
         patch.object(np.linalg, 'svd', side_effect=forbidden), patch.object(np.linalg, 'qr', side_effect=forbidden), \
         patch.object(np.linalg, 'solve', side_effect=forbidden), patch.object(np.linalg, 'lstsq', side_effect=forbidden), \
         patch.object(np.linalg, 'pinv', side_effect=forbidden), patch.object(np, 'load', side_effect=forbidden), np.errstate(all='raise'):
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Units)
        result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    if time.monotonic()-START >= 60:
        raise TimeoutError('unit command final soft60s incomplete')
    if not result.wasSuccessful():
        sys.exit(1)
    candidate.final_identity(repo, args.source_commit, initial_head, initial_hashes)
    if time.monotonic()-START >= 60:
        raise TimeoutError('unit command final identity soft60s incomplete')
    print('Command A: 24 artificial units; zero actual QR/SVD, no report/real-array reads; not production acceptance; source='+args.source_commit)
