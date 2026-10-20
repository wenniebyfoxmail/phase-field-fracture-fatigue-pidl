"""Artificial-only unit checks. Never load archived images or derived image arrays."""
from pathlib import Path
import sys
import json
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import md03_controlled_opening as m


class ControlledOpeningTests(unittest.TestCase):
    def setUp(self):
        self.a = np.random.default_rng(20261020).normal(120, 28, (180, 800)).astype(np.float32)
        self.v = np.ones_like(self.a)
        self.mask = np.zeros_like(self.a, bool)

    def gauge(self, target, x=400):
        return m.gauge(self.a, target, self.mask, self.v, self.v, x, 90)

    def test_linear_field_cancellation_independent_analytic(self):
        d = np.column_stack((2+.03*m.OFFSETS, -.4-.02*m.OFFSETS))
        j, error = m.jump_from_displacements(d)
        np.testing.assert_allclose(j, [0, 0], atol=1e-12)
        self.assertLess(error, 1e-12)

    def test_vector_jump_and_sign_independent_closed_form(self):
        d = np.column_stack((.1*m.OFFSETS, -.02*m.OFFSETS))
        d[:3] += [-.5, -.25]; d[3:] += [.5, .25]
        j, _ = m.jump_from_displacements(d)
        np.testing.assert_allclose(j, [1, .5], atol=1e-12)
        # Independent old equally spaced intercept coefficients.
        expected = (np.array([4, 1, -2])@d[3:] - np.array([-2, 1, 4])@d[:3])/3
        np.testing.assert_allclose(j, expected, atol=1e-12)

    def test_identity_bidirectional(self):
        r = self.gauge(self.a)
        self.assertTrue(r['numerically_usable'], r['reasons'])
        # Finite-patch autocorrelation is not exactly symmetric: parabola bias
        # is below .02 native px here, much smaller than the .5px QC bound.
        self.assertLess(abs(r['jump_normal_px']), .02)
        self.assertLess(max(p['roundtrip'] for p in r['matches']), .02)
        self.assertEqual(r['visibility'], 'unknown_not_annotated')
        self.assertIsNone(r['physical_width'])

    def test_integer_translation_with_affine_brightness(self):
        target = cv2.warpAffine(self.a, np.array([[1., 0, 2.], [0, 1., -1.]]), (800, 180))*1.05+8
        r = self.gauge(target)
        self.assertTrue(r['numerically_usable'], r['reasons'])
        self.assertLess(abs(r['jump_normal_px']), .02)
        for p in r['matches']:
            np.testing.assert_allclose(p['forward']['d'], [2, -1], atol=.02)
            self.assertLess(p['roundtrip'], .02)

    def test_fractional_translation_is_not_opening(self):
        target = cv2.warpAffine(self.a, np.array([[1., 0, .5], [0, 1., -.25]]), (800, 180))
        r = self.gauge(target)
        # Interpolation-induced quality failure stays unknown, never rescued.
        if r['numerically_usable']:
            self.assertLess(abs(r['jump_normal_px']), .15)
        else:
            self.assertIsNone(r['jump_normal_px'])
            self.assertTrue(r['reasons'])

    def test_step_opening_vs_equal_budget_internal_arms(self):
        target = self.a.copy()
        target[:, :399] = self.a[:, 1:400]
        target[:, 401:] = self.a[:, 400:-1]
        target[:, 399:401] = 0
        central = self.gauge(target)
        self.assertTrue(central['numerically_usable'], central['reasons'])
        self.assertAlmostEqual(central['jump_normal_px'], 2, delta=.03)
        for shift in (-120, 120):
            inside = self.gauge(target, 400+shift)
            self.assertTrue(inside['numerically_usable'], inside['reasons'])
            self.assertLess(abs(inside['jump_normal_px']), .03)
            self.assertEqual(len(inside['matches']), len(central['matches']))

    def test_central_dark_paint_does_not_imply_opening(self):
        target = self.a.copy(); target[:, 398:403] = 0
        r = self.gauge(target)
        self.assertTrue(r['numerically_usable'], r['reasons'])
        self.assertGreater(r['central_darkening_gray'], 50)
        self.assertLess(abs(r['jump_normal_px']), .01)

    def test_flat_texture_unknown_not_zero(self):
        a = np.ones_like(self.a)*100
        r = m.gauge(a, a, self.mask, self.v, self.v, 400, 90)
        self.assertFalse(r['numerically_usable'])
        self.assertIn('low_texture', r['reasons'])
        self.assertIsNone(r['jump_normal_px'])

    def test_occlusion_unknown_keeps_raw_diagnostics(self):
        target = self.a.copy(); target[60:120, 310:490] = 100
        r = self.gauge(target)
        self.assertFalse(r['numerically_usable'])
        self.assertIsNone(r['jump_normal_px'])
        self.assertIsNotNone(r['residual_abs_gray'])

    def test_unrelated_texture_unknown(self):
        target = np.random.default_rng(12).normal(120, 28, self.a.shape).astype(np.float32)
        r = self.gauge(target)
        self.assertFalse(r['numerically_usable'])
        self.assertIn('low_ncc', r['reasons'])

    def test_repeated_texture_ambiguity_unknown(self):
        a = np.tile([30, 200], (180, 400)).astype(np.float32)
        p = m.bidirectional(a, a, 400, 90, self.v, self.v)
        self.assertFalse(p['usable'])
        self.assertIn('ambiguous_peak', p['reasons'])

    def test_search_edge_unknown(self):
        target = cv2.warpAffine(self.a, np.array([[1., 0, 4.], [0, 1., 0.]]), (800, 180))
        r = self.gauge(target)
        self.assertFalse(r['numerically_usable'])
        self.assertIn('search_edge', r['reasons'])

    def test_validity_hole_and_image_boundary(self):
        valid = self.v.copy(); valid[70:110, 310:350] = 0
        p = m.bidirectional(self.a, self.a, 328, 90, valid, self.v)
        self.assertFalse(p['usable']); self.assertIn('support', p['reasons'])
        self.assertIsNone(m.crop(self.a, 5, 5, 15))

    def test_reverse_quality_failure_cannot_be_silently_used(self):
        f = dict(d=[1., 0.], ncc=1., usable=True, reasons=[])
        b = dict(d=None, usable=False, reasons=['low_texture'])
        with patch.object(m, 'forward', side_effect=[f, b]):
            r = m.bidirectional(self.a, self.a, 400, 90, self.v, self.v)
        self.assertFalse(r['usable'])
        self.assertIn('reverse_low_texture', r['reasons'])
        self.assertIsNone(r['roundtrip'])

    def test_roundtrip_checks_original_point_not_displacement_sign(self):
        f = dict(d=[1., .2], usable=True, reasons=[])
        b = dict(d=[-.8, -.2], usable=True, reasons=[])
        with patch.object(m, 'forward', side_effect=[f, b]) as call:
            r = m.bidirectional(self.a, self.a, 400, 90, self.v, self.v)
        self.assertAlmostEqual(r['roundtrip'], .2)
        self.assertEqual(call.call_args_list[1].args[2:4], (401., 90.2))

    def test_nonfinite_and_wrong_displacement_shape(self):
        a = self.a.copy(); a[90, 400] = np.nan
        p = m.forward(a, self.a, 400, 90, self.v, self.v)
        self.assertFalse(p['usable']); self.assertIn('nonfinite', p['reasons'])
        with self.assertRaises(ValueError):
            m.jump_from_displacements(np.zeros((5, 2)))

    def test_peak_tie_rule_and_separation(self):
        scores = np.full((9, 9), -1., np.float32)
        scores[4, 2] = scores[4, 6] = 1.
        p = m.peak(scores)
        self.assertEqual(p['d'], [-2., 0.])
        self.assertEqual(p['separation'], 0.)

    def test_numpy_ncc_independent_arithmetic(self):
        p = self.a[75:106, 385:416].astype(float)
        search = self.a[71:110, 381:420].astype(float)
        windows = np.lib.stride_tricks.sliding_window_view(search, (31, 31))
        p -= p.mean(); windows = windows-windows.mean(axis=(-2, -1), keepdims=True)
        scores = (windows*p).sum(axis=(-2, -1))/np.sqrt((windows*windows).sum(axis=(-2, -1))*(p*p).sum())
        cv = cv2.matchTemplate(search.astype(np.float32), self.a[75:106, 385:416], cv2.TM_CCOEFF_NORMED)
        np.testing.assert_allclose(scores, cv, atol=2e-5)

    def test_summary_common_support_no_selective_denominator(self):
        records = []
        for site in ('a', 'b'):
            for arm in m.ARMS:
                for pert in m.PERTURBATIONS:
                    usable = not (site == 'b' and arm == 'right_internal' and pert == (1, 0))
                    records.append(dict(site=site, arm=arm, perturbation=list(pert),
                                        numerically_usable=usable, reasons=[] if usable else ['support'],
                                        jump_normal_px=(2 if arm == 'central' else .1) if usable else None,
                                        jump_tangent_px=0 if usable else None))
        s = m.summarize(records)
        self.assertTrue(s['sites'][0]['all_arms_and_perturbations_usable'])
        self.assertAlmostEqual(s['sites'][0]['positive_central_minus_abs_internal_envelope_px'], 1.9)
        self.assertFalse(s['sites'][1]['all_arms_and_perturbations_usable'])
        self.assertIsNone(s['sites'][1]['positive_central_minus_abs_internal_envelope_px'])
        self.assertTrue(all(r['nominal'] == 2 and r['unknown_visibility'] == 2 for r in s['arms']))

    def test_warp_direction_and_support(self):
        w, v = m.warp(self.a, [[1., 0, 2.], [0, 1., -1.]])
        np.testing.assert_array_equal(w[:-1, 2:], self.a[1:, :-2])
        self.assertFalse(v[:, :2].any())

    def test_mac_admission_before_any_file_access(self):
        with patch.object(m.platform, 'system', return_value='Darwin'), patch.object(Path, 'read_text', side_effect=AssertionError('no input read')):
            with self.assertRaisesRegex(RuntimeError, 'Mac is preparation-only'):
                m.admit(Path('not_read'), Path('not_read'), Path('not_created'))

    def test_no_archived_array_access_in_unit_suite(self):
        with patch.object(np, 'load', side_effect=AssertionError('no real arrays')):
            self.assertTrue(self.gauge(self.a)['numerically_usable'])

    def contract_fixture(self):
        names = ['history_support.json', 'D3_20261019/R001/input_specification.json',
                 'R000_selection/selection_lock.json', 'R002_history/89/arrays.npz',
                 'R002_history/132/arrays.npz', 'R003_target/arrays.npz']
        files = dict.fromkeys(names, 'artificial')
        files.update({'source/'+n: h for n, h in m.SOURCE_HASHES.items()})
        return dict(candidate=m.PACKAGE, normal=[1, 0], tangent=[0, 1], xs=list(m.XS), ys=list(m.YS),
                    arms=m.ARMS, offsets=m.OFFSETS.tolist(), perturbations=[list(p) for p in m.PERTURBATIONS],
                    patch_size=31, search_radius=m.SEARCH, quality=m.QC, wall_seconds=m.WALL_SECONDS,
                    output_bytes=m.OUTPUT_BYTES, pairs=[[89, 132], [132, 175]], roi=[2260, 1600, 3240, 2160],
                    matrices=[[[1, 0, 0], [0, 1, 0]]]*2, files=files,
                    raw_source_sha256=m.SOURCE_HASHES, code_sha256=m.sha(m.__file__), protocol_sha256=m.sha(m.PROTOCOL))

    def test_contract_refuses_parameter_input_and_code_drift(self):
        c = self.contract_fixture(); m.validate_contract(c)
        for key, value in [('quality', {}), ('xs', [2750]), ('files', {}), ('code_sha256', 'changed'),
                           ('matrices', [[[1, 0, float('nan')], [0, 1, 0]]]*2)]:
            d = dict(c, **{key: value})
            with self.assertRaises(ValueError):
                m.validate_contract(d)

    def test_new_json_only_and_no_nan_serialization(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)/'artificial.json'
            m.write_json(p, dict(known=2, unknown=None))
            self.assertEqual(json.loads(p.read_text()), dict(known=2, unknown=None))
            with self.assertRaises(FileExistsError):
                m.write_json(p, dict(replaced=True))
            self.assertEqual(json.loads(p.read_text())['known'], 2)

    def test_stencils_stay_same_side_with_matched_resource(self):
        for x in m.XS:
            left = np.array(m.OFFSETS)+x+m.ARMS['left_internal']
            right = np.array(m.OFFSETS)+x+m.ARMS['right_internal']
            self.assertLess(max(left)+m.HALF, x)
            self.assertGreater(min(right)-m.HALF, x)
            self.assertTrue(np.all(left-m.HALF-m.SEARCH >= 2260))
            self.assertTrue(np.all(right+m.HALF+m.SEARCH < 3240))
        self.assertEqual(len(m.XS)*len(m.YS)*len(m.ARMS)*len(m.PERTURBATIONS)*2, 2520)


if __name__ == '__main__':
    unittest.main()
