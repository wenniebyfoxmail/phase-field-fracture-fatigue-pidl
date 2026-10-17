"""Prepared, NOT RUN. Artificial unit checks; no real QR or full diagnostic."""
from contextlib import ExitStack
from decimal import Decimal, localcontext
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import aa2024_qconsistent_repair as d
import numpy as np


class SyntheticUnits(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.decimal = self.stack.enter_context(localcontext())
        self.decimal.prec = 80
        self.sentinels = d.guards(self.stack)
        self.no_qr = self.stack.enter_context(patch.object(d.linalg, 'qr', side_effect=d.forbidden))

    def tearDown(self):
        self.assertTrue(all(s.call_count == 0 for s in self.sentinels))
        self.assertEqual(self.no_qr.call_count, 0)

    def candidate_with_prescribed_qr(self, f):
        scale = 1. if np.array_equal(f['Lr'], f['clean']) else f['constants']['c']
        prescribed_T = np.diag([1., 1., 1., 1., scale])
        before = {k: f[k].copy() for k in ('H', 'Lr', 'y')}
        with patch.object(d.linalg, 'qr', return_value=(f['clean'].copy(), prescribed_T)) as qr:
            result = d.repair(f['H'], f['Lr'], f['y'])
            self.assertEqual(qr.call_count, 1)
            self.assertEqual(qr.call_args.kwargs, dict(mode='economic', pivoting=False, check_finite=True))
            d.check(qr.call_args.args[0], d.quotient(f['H'], f['Lr']), 'QR receives QLr')
        for k in before:
            self.assertTrue(np.array_equal(before[k], f[k]))
        return result

    def test_hadamard_and_constants(self):
        o = d.hadamard16()
        self.assertEqual(set(o.ravel()), {-.25, .25})
        self.assertTrue(np.array_equal(d.multiply(o.T, o), np.eye(16)))
        f = d.fixture('C1')
        self.assertEqual(f['Lr'].shape, (16, 5))
        self.assertTrue(np.array_equal(f['s'], [1., 2.**-4, 2.**-12, 2.**-24, 2.**-32]))
        self.assertEqual(f['constants']['retained_modes'], 5)

    def test_fixed_case_ids_only(self):
        with self.assertRaisesRegex(d.Stop, 'fixed C1-C3'):
            d.fixture('C0_or_real')

    def test_input_mechanisms_remain_distinct(self):
        a, b = d.fixture('C2'), d.fixture('C3')
        for k in ('H', 'Lr', 'y', 's', 'V'):
            self.assertTrue(np.array_equal(a[k], b[k]))
        self.assertFalse(np.array_equal(a['A'], b['A']))
        self.assertEqual(a['constants']['t'], 2.**-20)

    def test_old_negative_controls_preserved(self):
        for name in d.CASES:
            with self.subTest(case=name):
                f = d.fixture(name)
                p = d.multiply(f['Lr'], d.multiply(f['Lr'].T, f['y']))
                q = d.q_check(f['H'], p-f['y'])
                self.assertIs(q['producer_pass'], name == 'C1')
                self.assertIs(q['Decimal80_pass'], name == 'C1')

    def test_candidate_dataflow_uses_one_q_and_prescribed_qr(self):
        f = d.fixture('C2')
        # The candidate signature has no clean/A/s/V parameter. The QR is a stub.
        c = self.candidate_with_prescribed_qr(f)
        d.check(c['p'], 2.**-8*(f['clean'][:, :1]+f['clean'][:, 4:5]), 'stub p', 'vector')
        d.check(c['r'], -2.**-12*f['g'], 'stub r', 'vector')

    def test_signed_qr_preserves_factorisation(self):
        f = d.fixture('C1')
        U, T = d.signed_qr(-f['clean'], -np.eye(5))
        self.assertTrue(np.array_equal(U, f['clean']))
        self.assertTrue(np.array_equal(T, np.eye(5)))
        d.check(d.multiply(U, T), f['clean'], 'sign reconstruction')

    def test_zero_diagonal_rejected_before_sign(self):
        with self.assertRaisesRegex(d.Stop, 'zero QR diagonal'):
            d.signed_qr(d.fixture('C1')['clean'], np.zeros((5, 5)))

    def test_five_modes_required_no_truncation(self):
        f = d.fixture('C1')
        with self.assertRaisesRegex(d.Stop, 'five modes'):
            d.signed_qr(f['clean'][:, :4], np.eye(4))
        with self.assertRaisesRegex(d.Stop, 'fixed dimensions'):
            d.repair(f['H'], f['Lr'][:, :4], f['y'])

    def test_eta_is_row_sum_not_max_element(self):
        T = np.eye(5)
        T[0, 1:3] = .3
        with self.assertRaisesRegex(d.Stop, 'eta exceeds'):
            d.rank_guard(T)

    def test_eta_hard_boundary_without_tolerance(self):
        T = np.eye(5)
        T[0, 0] = .5
        self.assertEqual(d.rank_guard(T), .5)
        T[0, 0] -= 2.**-40
        with self.assertRaisesRegex(d.Stop, 'eta exceeds'):
            d.rank_guard(T)

    def test_nonfinite_and_shapes_reject(self):
        for value in (np.array([[np.nan]]), np.array([[np.inf]]), np.ones(3)):
            with self.subTest(value=str(value)):
                with self.assertRaisesRegex(d.Stop, 'finite two-dimensional'):
                    d.matrix(value)

    def test_original_tolerances_not_widened(self):
        for kind, delta in (('matrix', 2e-12), ('vector', 2e-15), ('square', 2e-18)):
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(d.Stop, 'STOP_IDENTITY'):
                    d.check([[delta]], [[0.]], 'over tolerance', kind)
                d.check([[delta/4]], [[0.]], 'under tolerance', kind)

    def test_all_five_probes_and_pythagoras_with_stub(self):
        for name in d.CASES:
            with self.subTest(case=name):
                f = d.fixture(name)
                row = d.audit_case(name, f, self.candidate_with_prescribed_qr(f))
                self.assertEqual([p['mode'] for p in row['probes']], [1, 2, 3, 4, 5])
                self.assertLessEqual(row['checks']['primary_p'], 1)
                self.assertEqual(row['evidence']['A'], f['A'].tolist())
                self.assertEqual(row['evidence']['constants']['c'], f['constants']['c'])

    def test_unexcited_wrong_direction_not_hidden_by_single_y(self):
        f = d.fixture('C1')
        c = self.candidate_with_prescribed_qr(f)
        # Replace unexcited second direction by an unused Q-space Hadamard mode.
        c['U'][:, 1] = d.hadamard16()[:, 14]
        d.check(c['p'], 2.**-8*(f['clean'][:, :1]+f['clean'][:, 4:5]), 'p still correct', 'vector')
        for j in (0, 4):
            d.image_probe(c['U'], 2.**-8*f['clean'][:, j:j+1], 'excited probe')
        with self.assertRaisesRegex(d.Stop, 'probe image 2'):
            d.image_probe(c['U'], 2.**-8*f['clean'][:, 1:2], 'probe image 2')

    def test_non_q_target_rejected_without_qr_or_replacement(self):
        f = d.fixture('C1')
        y = f['y']+2.**-8*f['H'][:, :1]
        saved = y.copy()
        with self.assertRaisesRegex(d.Stop, 'STOP_Q_CONSISTENCY'):
            d.repair(f['H'], f['Lr'], y)
        self.assertTrue(np.array_equal(y, saved))

    def test_reference_float_conversion_not_rounded_text(self):
        self.assertEqual(d.decimals([[.1]])[0][0], Decimal.from_float(.1))
        self.assertNotEqual(d.decimals([[.1]])[0][0], Decimal('.1'))
        value = d.multiply([[.1, .3]], [[.2], [-.7]])
        d.reference_product([[.1, .3]], [[.2], [-.7]], value, 'artificial product')

    def test_forbidden_apis_armed_without_invoking_them(self):
        self.assertIs(np.linalg.svd.side_effect, d.forbidden)
        self.assertIs(d.linalg.svd.side_effect, d.forbidden)
        self.assertIs(np.load.side_effect, d.forbidden)
        self.assertIs(np.linalg.qr.side_effect, d.forbidden)


if __name__ == '__main__':
    unittest.main(verbosity=2, failfast=True)
