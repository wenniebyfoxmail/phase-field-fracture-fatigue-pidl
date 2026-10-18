#!/usr/bin/env python3
"""F01 manual in-memory tests only; running this file needs separate approval."""
import time
START = time.monotonic()

import argparse
import ast
from contextlib import ExitStack
import importlib.abc
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import warnings
import xml.etree.ElementTree as ET

from aa2024_runtime_guard import install_cli
GUARD = install_cli() if __name__ == '__main__' else None


class EarlyFence(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('matplotlib', 'scipy', 'aa2024_q_recheck', 'aa2024_q_verify'):
            raise RuntimeError('forbidden test dependency: '+fullname)
        return None


if __name__ == '__main__':
    warnings.simplefilter('error')
    sys.meta_path.insert(0, EarlyFence())

import numpy as np
import aa2024_saved_svg as candidate

NS = {'s': 'http://www.w3.org/2000/svg'}


def fixture():
    arrays = dict(source_xy=np.array([[-2., -1.], [0., 0.], [2., 1.]]), scale=np.ones(6))
    for i, key in enumerate(('r', 'old_r', 'proxy_r', 'intact_r'), 1):
        arrays[key] = np.array([-3., -2., -1., 1., 2., 3.])*i*.001
    report = dict(schema='E019-D03-U01-v1', rows=[dict(arm=arm, J_Q_mm2=1e-6,
                  gap2_mm2=(i+1)*1e-6, J_k_mm2=(i+3)*1e-6) for i, arm in enumerate(candidate.ARMS)])
    return arrays, report


def prepared():
    arrays, report = fixture()
    return candidate.prepare(arrays, report, points=3)


def clock():
    return candidate.Budget(start=START)


class Units(unittest.TestCase):
    def tearDown(self):
        clock().check()
        if GUARD is not None:
            GUARD.check()

    def test_prepare_display_only(self):
        arrays, report = fixture()
        arrays['scale'][:] = 2
        data = candidate.prepare(arrays, report, points=3)
        self.assertTrue(np.array_equal(data['maps'][0], arrays['r'].reshape(3, 2)/2))

    def test_default_shape_is_648_not_test_fixture(self):
        with self.assertRaisesRegex(candidate.Stop, 'array contract'):
            candidate.prepare(*fixture())

    def test_exact_keys(self):
        arrays, report = fixture(); arrays['unrequested'] = np.zeros(1)
        with self.assertRaisesRegex(candidate.Stop, 'selected array keys'):
            candidate.prepare(arrays, report, points=3)

    def test_wrong_shape(self):
        arrays, report = fixture(); arrays['r'] = np.zeros(5)
        with self.assertRaisesRegex(candidate.Stop, 'array contract'):
            candidate.prepare(arrays, report, points=3)

    def test_wrong_dtype(self):
        arrays, report = fixture(); arrays['r'] = arrays['r'].astype('float32')
        with self.assertRaisesRegex(candidate.Stop, 'array contract'):
            candidate.prepare(arrays, report, points=3)

    def test_nonfinite_array(self):
        arrays, report = fixture(); arrays['r'][1] = np.nan
        with self.assertRaisesRegex(candidate.Stop, 'array contract'):
            candidate.prepare(arrays, report, points=3)

    def test_zero_scale(self):
        arrays, report = fixture(); arrays['scale'][0] = 0
        with self.assertRaisesRegex(candidate.Stop, 'positive scale'):
            candidate.prepare(arrays, report, points=3)

    def test_negative_scale(self):
        arrays, report = fixture(); arrays['scale'][0] = -1
        with self.assertRaisesRegex(candidate.Stop, 'positive scale'):
            candidate.prepare(arrays, report, points=3)

    def test_degenerate_coordinates(self):
        arrays, report = fixture(); arrays['source_xy'][:, 1] = 0
        with self.assertRaisesRegex(candidate.Stop, 'coordinate extent'):
            candidate.prepare(arrays, report, points=3)

    def test_saved_schema(self):
        arrays, report = fixture(); report['schema'] = 'old'
        with self.assertRaisesRegex(candidate.Stop, 'schema'):
            candidate.prepare(arrays, report, points=3)

    def test_saved_row_count(self):
        arrays, report = fixture(); report['rows'].pop()
        with self.assertRaisesRegex(candidate.Stop, 'three saved rows'):
            candidate.prepare(arrays, report, points=3)

    def test_saved_row_order(self):
        arrays, report = fixture(); report['rows'].reverse()
        with self.assertRaisesRegex(candidate.Stop, 'row order'):
            candidate.prepare(arrays, report, points=3)

    def test_saved_negative_scalar(self):
        arrays, report = fixture(); report['rows'][0]['gap2_mm2'] = -1
        with self.assertRaisesRegex(candidate.Stop, 'saved scalar'):
            candidate.prepare(arrays, report, points=3)

    def test_saved_nonfinite_scalar(self):
        arrays, report = fixture(); report['rows'][0]['J_k_mm2'] = float('inf')
        with self.assertRaisesRegex(candidate.Stop, 'saved scalar'):
            candidate.prepare(arrays, report, points=3)

    def test_saved_bool_not_number(self):
        arrays, report = fixture(); report['rows'][0]['J_k_mm2'] = True
        with self.assertRaisesRegex(candidate.Stop, 'saved scalar'):
            candidate.prepare(arrays, report, points=3)

    def test_saved_common_floor(self):
        arrays, report = fixture(); report['rows'][0]['J_Q_mm2'] = 2e-6
        with self.assertRaisesRegex(candidate.Stop, 'one saved J_Q'):
            candidate.prepare(arrays, report, points=3)

    def test_display_stack_overflow(self):
        arrays, report = fixture(); report['rows'][0].update(J_Q_mm2=1.7e308, gap2_mm2=1.7e308)
        with self.assertRaisesRegex(candidate.Stop, 'stack overflow'):
            candidate.prepare(arrays, report, points=3)

    def test_display_division_underflow_still_stops(self):
        arrays, report = fixture(); arrays['r'][:] = 1e-300; arrays['scale'][:] = 1e300
        with self.assertRaises(FloatingPointError):
            candidate.prepare(arrays, report, points=3)

    def test_inputs_unchanged(self):
        arrays, report = fixture(); copies = {key: value.copy() for key, value in arrays.items()}
        original = json.dumps(report)
        candidate.prepare(arrays, report, points=3)
        self.assertTrue(all(np.array_equal(value, copies[key]) for key, value in arrays.items()))
        self.assertEqual(json.dumps(report), original)

    def test_colour_zero(self):
        self.assertEqual(candidate.color(0, 1), '#f7f7f7')

    def test_colour_endpoints(self):
        self.assertEqual(candidate.color(-1, 1), '#053061')
        self.assertEqual(candidate.color(1, 1), '#67001f')

    def test_colour_outside(self):
        with self.assertRaisesRegex(candidate.Stop, 'colour input'):
            candidate.color(2, 1)

    def test_svg_all_points_and_panels(self):
        root = ET.fromstring(candidate.residual_svg(prepared(), {}, clock()))
        dots = root.findall('s:circle', NS)
        self.assertEqual(len(dots), 24)
        self.assertEqual({dot.attrib['data-panel'] for dot in dots}, {f'{r}:{c}' for r in range(2) for c in range(4)})
        self.assertEqual({dot.attrib['data-point'] for dot in dots}, {'0', '1', '2'})

    def test_svg_shared_colour_not_per_panel(self):
        data = prepared(); root = ET.fromstring(candidate.residual_svg(data, {}, clock()))
        for dot in root.findall('s:circle', NS):
            self.assertEqual(dot.attrib['fill'], candidate.color(float(dot.attrib['data-mm']), data['bound']))

    def test_svg_equal_aspect_positive_y(self):
        root = ET.fromstring(candidate.residual_svg(prepared(), {}, clock()))
        dots = [v for v in root.findall('s:circle', NS) if v.attrib['data-panel'] == '0:0']
        dx = float(dots[2].attrib['cx'])-float(dots[0].attrib['cx'])
        dy = float(dots[0].attrib['cy'])-float(dots[2].attrib['cy'])
        self.assertEqual(dx/4, dy/2)

    def test_svg_zero_map_floor_only(self):
        arrays, report = fixture()
        for key in ('r', 'old_r', 'proxy_r', 'intact_r'):
            arrays[key][:] = 0
        data = candidate.prepare(arrays, report, points=3)
        self.assertTrue(data['zero_range']); self.assertEqual(data['bound'], 1e-15)
        root = ET.fromstring(candidate.residual_svg(data, {}, clock()))
        self.assertTrue(all(dot.attrib['fill'] == '#f7f7f7' for dot in root.findall('s:circle', NS)))

    def test_ledger_uses_saved_not_recomputed_values(self):
        data = prepared(); data['rows'][0]['J_k_mm2'] = 99e-6
        root = ET.fromstring(candidate.ledger_svg(data, {}, clock()))
        dot = root.find("s:circle[@data-arm='old']", NS)
        self.assertEqual(float(dot.attrib['data-value']), 99e-6)
        self.assertEqual(len(root.findall('s:circle', NS)), 3)

    def test_zero_ledger_range_only(self):
        data = prepared()
        for row in data['rows']:
            for key in ('J_Q_mm2', 'gap2_mm2', 'J_k_mm2'):
                row[key] = 0.
        root = ET.fromstring(candidate.ledger_svg(data, {}, clock()))
        self.assertIn('axis range only', ''.join(root.itertext()))

    def test_xml_escapes_external_text(self):
        root = candidate.canvas(20, 20, '<script>&"', {'path': '<&'})
        parsed = ET.fromstring(ET.tostring(root, encoding='unicode'))
        self.assertEqual(parsed.find('s:title', NS).text, '<script>&"')
        self.assertFalse(parsed.findall('.//s:script', NS))

    def test_sidecar_scope(self):
        for stem in ('residuals', 'square_ledger'):
            value = candidate.sidecar(stem, {'source_status': 'incomplete_unaccepted_synthetic'}, prepared())
            for token in ('How to read', 'Data provenance', 'Key numerical takeaway', 'Limitations',
                          'viewer fonts', 'B003 remains incomplete', 'not independently recomputed'):
                self.assertIn(token, value)

    def test_json_duplicate_rejected(self):
        with self.assertRaisesRegex(candidate.Stop, 'duplicate JSON'):
            candidate.strict_json('{"a": 1, "a": 2}')

    def test_json_nan_rejected(self):
        with self.assertRaisesRegex(candidate.Stop, 'nonfinite JSON'):
            candidate.strict_json('{"a": NaN}')

    def test_exact_budget_stop(self):
        candidate.Budget(start=0, clock=lambda: 59.999).check()
        with self.assertRaises(TimeoutError):
            candidate.Budget(start=0, clock=lambda: 60.).check()

    def test_fake_npz_only_selected_members(self):
        seen = []; arrays, _ = fixture()
        class Fake:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def __getitem__(self, key): seen.append(key); return arrays[key]
            @property
            def files(self): raise AssertionError('must not enumerate')
        def loader(path, allow_pickle):
            self.assertEqual(path, 'memory-only-fake.npz'); self.assertFalse(allow_pickle)
            return Fake()
        result = candidate.load_members('memory-only-fake.npz', loader=loader)
        self.assertEqual(tuple(seen), candidate.KEYS); self.assertEqual(set(result), set(candidate.KEYS))

    def test_factor_entry_is_forbidden_not_actual_factor(self):
        with self.assertRaisesRegex(candidate.Stop, 'factorisation/solve forbidden'):
            np.linalg.svd(np.zeros((2, 2)))

    def test_import_fence(self):
        fence = candidate.ImportFence()
        for name in ('matplotlib', 'matplotlib.pyplot', 'scipy.linalg', 'aa2024_q_recheck', 'aa2024_q_verify'):
            with self.assertRaises(candidate.Stop):
                fence.find_spec(name)
        self.assertIsNone(fence.find_spec('decimal'))

    def test_authority_wrong_input_before_io(self):
        with patch.object(Path, 'open', side_effect=AssertionError('no file IO')):
            with self.assertRaisesRegex(candidate.Stop, 'exact unaccepted synthetic'):
                candidate.input_fingerprints(Path('/not-authorized'), clock())

    def test_authority_explicit_and_exact(self):
        candidate.permissions(candidate.INPUT, candidate.OUTPUT, True)
        for source, output, allowed in ((candidate.INPUT, candidate.OUTPUT, False),
                                        (candidate.INPUT, candidate.INPUT, True),
                                        (Path('/other'), candidate.OUTPUT, True)):
            with self.assertRaises(candidate.Stop):
                candidate.permissions(source, output, allowed)

    def test_path_relative_and_symlink_rejected(self):
        with self.assertRaisesRegex(candidate.Stop, 'absolute'):
            candidate.safe_path(Path('relative'))
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaisesRegex(candidate.Stop, 'symlink'):
                candidate.safe_path(Path('/artificial'))

    def test_source_has_no_forbidden_imports_or_factor_calls(self):
        tree = ast.parse(Path(candidate.__file__).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertFalse(any(v.name.split('.')[0] in candidate.BLOCKED_IMPORTS for v in node.names))
            elif isinstance(node, ast.ImportFrom):
                self.assertNotIn((node.module or '').split('.')[0], candidate.BLOCKED_IMPORTS)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Attribute) and node.func.value.attr == 'linalg':
                    self.fail('renderer must not call linalg')


def main():
    budget = candidate.Budget(start=START); budget.check()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    candidate.require(all(os.environ.get(k) == '1' for k in candidate.THREADS) and
                      os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'single CPU environment')
    repo = Path(__file__).resolve().parents[1]
    initial = candidate.identity(repo, args.source_commit, budget)
    with candidate.numerical_fence(), patch.object(np, 'load', side_effect=AssertionError('no actual archive reads')):
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(Units)
        result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    budget.check()
    if not result.wasSuccessful():
        sys.exit(1)
    candidate.require(result.testsRun == 40 and not result.skipped, 'exact forty tests without skips')
    candidate.require(candidate.identity(repo, args.source_commit, budget) == initial, 'runtime source identity changed')
    GUARD.check('artificial_success_stdout')
    print(json.dumps(dict(status='F01_artificial_units_only_not_B003_display_or_acceptance', tests=result.testsRun,
                          actual_svd=0, actual_qr=0, runtime_head=initial[0], source_commit=args.source_commit,
                          source_sha256=initial[1], elapsed_before_print=time.monotonic()-START)))
    budget.check(); GUARD.check('artificial_success_stdout_done')


if __name__ == '__main__':
    main()
