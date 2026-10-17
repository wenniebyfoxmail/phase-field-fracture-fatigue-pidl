#!/usr/bin/env python3
"""U01 tiny: artificial boundaries + original 24 stub regressions, one 60s package.

No reports/archives/real arrays, full-size synthetic generator, QR/SVD or solve.
Negative controls are named assertions, not exception permissions for candidates.
"""
import time
START = time.monotonic()

import argparse
from contextlib import ExitStack
from fractions import Fraction
import json
import logging
import os
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch
import warnings

warnings.simplefilter('error')


class StopLogging(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            raise RuntimeError('unexpected logging warning: '+record.getMessage())


logging.getLogger().addHandler(StopLogging(level=logging.WARNING))
import numpy as np
import aa2024_dyadic_reference as arithmetic
import aa2024_q_recheck as candidate
import aa2024_q_verify as independent
from test_aa2024_q_recheck import Units as OriginalUnits


def forbidden(*args, **kwargs):
    raise AssertionError('tiny forbids factorization, solve, full-size generation or array/report reads')


def number(code):
    return struct.unpack('>d', int(code).to_bytes(8, 'big'))[0]


def code(value):
    return int.from_bytes(struct.pack('>d', float(value)), 'big')


def remaining_budget():
    if time.monotonic()-START >= 60:
        raise TimeoutError('tiny whole-package soft60s incomplete; no retry')


class UnderflowUnits(unittest.TestCase):
    def tearDown(self):
        remaining_budget()

    def product(self, x, t, site='producer.retained_right'):
        a, s = np.array([[x]], dtype=np.float64), np.array([t], dtype=np.float64)
        original = [v.tobytes() for v in (a, s)]
        records = []
        result = arithmetic.column_reference(a, s, site, records)
        self.assertEqual(original, [v.tobytes() for v in (a, s)])
        independent.rounding_interval(x, t, float(result[0, 0]))
        for cert in records[0]['certificates']:
            independent.product_certificate(cert)
        self.assertFalse(result.flags.writeable)
        self.assertFalse(np.shares_memory(result, a))
        return float(result[0, 0]), records[0]

    def test_model_supported_probes(self):
        self.assertIn('RN-even', arithmetic.check_model())

    def test_model_wrong_rounding_rejected(self):
        with patch.object(arithmetic, '_round_mode', return_value=1):
            with self.assertRaisesRegex(arithmetic.ArithmeticContract, 'FE_TONEAREST'):
                arithmetic.model_state()

    def test_model_daz_behavior_rejected_stub(self):
        original = np.multiply
        with patch.object(np, 'multiply', return_value=np.array([0.])):
            with self.assertRaisesRegex(arithmetic.ArithmeticContract, 'subnormal input'):
                arithmetic.check_model()
        self.assertIs(np.multiply, original)

    def test_normal_matches_original_bits(self):
        for x, t in ((1.25, -3.), (-2., -.125), (float.fromhex('0x1p-400'), float.fromhex('0x1p-500'))):
            value, rec = self.product(x, t)
            self.assertEqual(code(value), code(np.multiply(np.float64(x), np.float64(t))))
            self.assertEqual(rec['ordinary_count'], 1)

    def test_subnormal_input_normal_output(self):
        value, rec = self.product(number(1), float.fromhex('0x1p52'))
        self.assertEqual(code(value), 1 << 52)
        self.assertEqual(rec['ordinary_count'], 1)

    def test_signed_zero_all_signs(self):
        for x in (0., -0.):
            for t in (2., -2., 0., -0.):
                value, rec = self.product(x, t)
                self.assertEqual(code(value) >> 63, (code(x) ^ code(t)) >> 63)
                self.assertEqual(rec['zero_operand_count'], 1)

    def test_exact_subnormal_not_flushed(self):
        for x in (number(1), -number(1), number(17)):
            value, rec = self.product(x, 1.)
            self.assertEqual(code(value), code(x))
            self.assertEqual(rec['subnormal_output_count'], 1)
            self.assertEqual(rec['certificates'][0]['magnitude_rounding'], 'exact')

    def test_half_quantum_tie_to_zero(self):
        for x in (number(1), -number(1)):
            value, rec = self.product(x, .5)
            self.assertEqual(code(value), (code(x) >> 63) << 63)
            self.assertEqual(rec['nonzero_product_rounded_zero_count'], 1)

    def test_three_half_quantum_tie_to_even(self):
        for x in (number(3), -number(3)):
            value, _ = self.product(x, .5)
            self.assertEqual(code(abs(value)), 2)

    def test_half_quantum_adjacent_below_above(self):
        for factor, expected in ((number(code(.5)-1), 0), (number(code(.5)+1), 1)):
            for sign in (1, -1):
                value, _ = self.product(number(1)*sign, factor)
                self.assertEqual(code(abs(value)), expected)

    def test_largest_subnormal_exact(self):
        value, _ = self.product(number((1 << 52)-1), 1.)
        self.assertEqual(code(value), (1 << 52)-1)

    def test_reachable_subnormal_to_normal_rounding(self):
        value, rec = self.product(number((1 << 52)-1), number(code(1.)+1))
        self.assertEqual(code(value), 1 << 52)
        self.assertEqual(rec['certificates'][0]['magnitude_rounding'], 'larger_magnitude')

    def test_min_normal_in_integer_branch(self):
        value, rec = self.product(number(1 << 52), 1.)
        self.assertEqual(code(value), 1 << 52)
        self.assertEqual(rec['integer_branch_count'], 1)

    def test_first_normal_binade_in_integer_branch(self):
        value, rec = self.product(number((1 << 52)+7), 1.)
        self.assertEqual(code(value), (1 << 52)+7)
        self.assertEqual(rec['integer_branch_count'], 1)

    def test_reachable_integer_branch_upper_pair(self):
        x = number(code(float.fromhex('0x1p-511'))-1)
        t = number(code(float.fromhex('0x1p-510'))-1)
        value, rec = self.product(x, t)
        self.assertEqual(rec['integer_branch_count'], 1)
        self.assertEqual(code(value), (1 << 53)-2)

    def test_pack_only_unreachable_upper_boundary(self):
        # This is NOT an end-to-end product case, as required by Pro.
        for negative in (False, True):
            self.assertEqual(code(arithmetic.pack_quantum(1 << 53, negative)),
                             (1 << 53) | ((1 << 63) if negative else 0))

    def test_pack_rejects_invalid_range(self):
        for n in (-1, (1 << 53)+1, 1.0):
            with self.assertRaises(arithmetic.ArithmeticContract):
                arithmetic.pack_quantum(n, False)

    def test_fixed_column_axis_and_sites(self):
        for site in arithmetic.SITES:
            x = np.array([[number(1), 2.], [number(3), -4.]])
            s = np.array([.5, 3.]); records = []
            out = arithmetic.column_reference(x, s, site, records)
            for index in np.ndindex(x.shape):
                independent.rounding_interval(float(x[index]), float(s[index[1]]), float(out[index]))
            self.assertEqual(records[0]['integer_branch_count'], 2)

    def test_wrong_site_rejected_before_multiply(self):
        with patch.object(np, 'multiply', side_effect=forbidden):
            with self.assertRaisesRegex(arithmetic.ArithmeticContract, 'site'):
                arithmetic.column_reference(np.ones((1, 1)), np.ones(1), 'arbitrary', [])

    def test_wrong_column_shape_rejected(self):
        for x, t in ((np.ones((2, 3)), np.ones(2)), (np.ones((2, 3)), np.ones((1, 3))),
                     (np.ones(3), np.ones(3))):
            with self.assertRaisesRegex(arithmetic.ArithmeticContract, 'shape'):
                arithmetic.column_reference(x, t, arithmetic.SITES[0], [])

    def test_wrong_dtype_rejected(self):
        with self.assertRaisesRegex(arithmetic.ArithmeticContract, 'float64'):
            arithmetic.column_reference(np.ones((1, 1), dtype=np.float32), np.ones(1), arithmetic.SITES[0], [])

    def test_nonfinite_checked_before_zero(self):
        for bad in (np.nan, np.inf, -np.inf):
            with self.assertRaisesRegex(arithmetic.ArithmeticContract, 'finite'):
                arithmetic.column_reference(np.zeros((1, 1)), np.array([bad]), arithmetic.SITES[0], [])

    def test_only_ordinary_operands_multiplied(self):
        multiply = np.multiply; seen = []
        def guarded(x, t):
            seen.append((x.copy(), t.copy()))
            self.assertTrue(np.all(np.abs(x) >= 1.))
            return multiply(x, t)
        x, t = np.array([[number(1), 2.]]), np.array([.5, 3.])
        with patch.object(np, 'multiply', side_effect=guarded):
            out = arithmetic.column_reference(x, t, arithmetic.SITES[0], [])
        self.assertEqual(len(seen), 1)
        self.assertEqual(out[0, 1], 6.)

    def test_original_underflow_expected_negative_control(self):
        # Explicit old-path negative control: not a candidate fallback result.
        with self.assertRaises(FloatingPointError):
            np.multiply(np.array([number(1)]), np.array([.5]))

    def test_unlisted_arithmetic_underflow_still_stops(self):
        with self.assertRaises(FloatingPointError):
            np.multiply(np.array([number(3)]), np.array([.5]))

    def test_ordinary_overflow_stops(self):
        with self.assertRaises(FloatingPointError):
            self.product(sys.float_info.max, 2.)

    def test_repeat_site_rejected(self):
        records = []
        arithmetic.column_reference(np.ones((1, 1)), np.ones(1), arithmetic.SITES[0], records)
        with self.assertRaisesRegex(arithmetic.ArithmeticContract, 'twice'):
            arithmetic.column_reference(np.ones((1, 1)), np.ones(1), arithmetic.SITES[0], records)

    def test_budget_exhaustion_before_product(self):
        class Ended:
            def check(self): raise TimeoutError('artificial budget ended')
        with self.assertRaises(TimeoutError):
            arithmetic.column_reference(np.ones((1, 1)), np.ones(1), arithmetic.SITES[0], [], Ended())

    def test_input_bit_mutation_rejected(self):
        x = np.ones((1, 1)); multiply = np.multiply
        def changed(a, b):
            x[0, 0] = 2.
            return multiply(a, b)
        with patch.object(np, 'multiply', side_effect=changed):
            with self.assertRaisesRegex(arithmetic.ArithmeticContract, 'input bits changed'):
                arithmetic.column_reference(x, np.ones(1), arithmetic.SITES[0], [])

    def test_fraction_oracle_rejects_wrong_rounding(self):
        with self.assertRaisesRegex(independent.Rejected, 'nearest-even'):
            independent.rounding_interval(number(1), .5, number(1))

    def test_fraction_oracle_rejects_wrong_zero_sign(self):
        with self.assertRaisesRegex(independent.Rejected, 'sign'):
            independent.rounding_interval(-number(1), .5, 0.)

    def test_fraction_certificate_tamper_rejected(self):
        _, rec = self.product(number(3), .5)
        cert = dict(rec['certificates'][0], remainder='0')
        with self.assertRaises(independent.Rejected):
            independent.product_certificate(cert)

    def test_direction_and_counts_are_not_underflow_events(self):
        x = np.array([[number(1), number(3), number(1 << 52), 0.]])
        recs = []
        arithmetic.column_reference(x, np.array([.5, .5, 1., -2.]), arithmetic.SITES[0], recs)
        r = recs[0]
        self.assertEqual((r['integer_branch_count'], r['subnormal_output_count'], r['nonzero_product_rounded_zero_count'], r['zero_operand_count']), (3, 1, 1, 1))
        self.assertEqual([c['magnitude_rounding'] for c in r['certificates']], ['smaller_magnitude', 'larger_magnitude', 'exact'])

    def test_threshold_dispatch_fraction_reference(self):
        boundary = float.fromhex('0x1p-900')
        refs = (0., number(1), -number(3), number(code(boundary)-1), boundary, -boundary, number(code(boundary)+1), 1.)
        for kind, atol in arithmetic.ATOL.items():
            for ref in refs:
                actual = arithmetic.comparison(np.array([ref]), np.array([ref]), kind)
                relative = float(Fraction.from_float(1e-12)*abs(Fraction.from_float(ref)))
                expected = float(Fraction.from_float(atol)+Fraction.from_float(relative))
                self.assertEqual(code(actual['max_absolute_delta']['limit']), code(expected))

    def test_inclusive_limit_and_adjacent_outside(self):
        for kind, atol in arithmetic.ATOL.items():
            self.assertTrue(arithmetic.comparison(np.array([atol]), np.array([0.]), kind)['all_pass'])
            self.assertFalse(arithmetic.comparison(np.array([number(code(atol)+1)]), np.array([0.]), kind)['all_pass'])

    def test_failure_witness_not_max_absolute_error(self):
        a, ref = np.array([1e10+1e-3, 2e-15]), np.array([1e10, 0.])
        summary = arithmetic.comparison(a, ref)
        self.assertEqual(summary['max_absolute_delta']['index'], [0])
        self.assertEqual(summary['first_failure']['index'], [1])
        with self.assertRaisesRegex(candidate.Stop, 'index.*1'):
            candidate.close(a, ref, 'all components')

    def test_direct_criterion_ratio_theorem_without_float_divide(self):
        for denominator in (number(1), number(1 << 52), 1e-18, 1e-15, 1e-12, 1., sys.float_info.max):
            adjacent = (code(denominator)-1, code(denominator))
            if denominator < sys.float_info.max:
                adjacent += (code(denominator)+1,)
            for raw in adjacent:
                d = number(raw); q = Fraction.from_float(d)/Fraction.from_float(denominator)
                # RN64(q)<=1 iff q is no greater than the upper midpoint of 1 (even).
                rounded_status = q <= Fraction(1)+Fraction(1, 1 << 53)
                self.assertEqual(d <= denominator, rounded_status)

    def test_comparison_unknown_kind_rejected(self):
        with self.assertRaisesRegex(arithmetic.ArithmeticContract, 'tolerance'):
            arithmetic.comparison(np.array([0.]), np.array([0.]), 'arbitrary')

    def test_comparison_shape_nonfinite_rejected(self):
        for a, ref in ((np.zeros(2), np.zeros(1)), (np.array([np.nan]), np.zeros(1)), (np.zeros(1), np.array([np.inf]))):
            with self.assertRaises(arithmetic.ArithmeticContract):
                arithmetic.comparison(a, ref)

    def test_comparison_overflow_stops(self):
        with self.assertRaises(FloatingPointError):
            arithmetic.comparison(np.array([sys.float_info.max]), np.array([-sys.float_info.max]))

    def test_no_ratio_and_json_safe_summary(self):
        summary = arithmetic.comparison(np.array([number(1)]), np.array([0.]))
        self.assertTrue(summary['all_pass'])
        self.assertNotIn('ratio', json.dumps(summary, allow_nan=False).lower())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    head = candidate.snapshot(repo, args.source_commit)
    hashes = candidate.code_hashes()
    candidate.require(all(os.environ.get(k) == '1' for k in candidate.THREADS) and
                      os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'single CPU environment')
    remaining_budget()
    warnings.simplefilter('error')
    original_load_real = candidate.load_real
    def guarded_real(opaque_authorized):
        if opaque_authorized:
            forbidden()
        # Original opaque-permission negative test: exits before any file read.
        return original_load_real(False)
    with ExitStack() as stack:
        for module, names in ((candidate.linalg, ('qr', 'svd', 'solve', 'lstsq', 'pinv', 'eig', 'eigh')),
                              (np.linalg, ('qr', 'svd', 'solve', 'lstsq', 'pinv', 'eig', 'eigh'))):
            for name in names:
                stack.enter_context(patch.object(module, name, side_effect=forbidden))
        stack.enter_context(patch.object(np, 'load', side_effect=forbidden))
        stack.enter_context(patch.object(candidate, 'load_real', side_effect=guarded_real))
        stack.enter_context(patch.object(candidate, 'artificial', side_effect=forbidden))
        stack.enter_context(np.errstate(all='raise'))
        arithmetic.check_model()
        suite = unittest.TestSuite((unittest.defaultTestLoader.loadTestsFromTestCase(UnderflowUnits),
                                   unittest.defaultTestLoader.loadTestsFromTestCase(OriginalUnits)))
        result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    remaining_budget()
    if not result.wasSuccessful():
        sys.exit(1)
    candidate.final_identity(repo, args.source_commit, head, hashes)
    remaining_budget()
    print(json.dumps(dict(status='tiny_artificial_units_completed_not_B002_or_real_acceptance',
                          tests=result.testsRun, actual_svd=0, actual_qr=0, source_commit=args.source_commit,
                          runtime_head=head, source_sha256=hashes, elapsed_before_print=time.monotonic()-START), allow_nan=False))
    remaining_budget()
