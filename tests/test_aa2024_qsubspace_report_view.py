"""Prepared, not run: artificial scalar/rectangle tests; no canvas or saved report."""

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import aa2024_qsubspace_report_view as v


def fixture():
    rows = [dict(case='C0', Q_identity_ratio=None, Q_identity_pass=None,
                 Q_identity_role='not_applicable', Q_identity_outcome='no_y_p_r_in_C0')]
    for name in ('C1', 'C2', 'C3'):
        clean = name == 'C1'
        rows.append(dict(case=name, Q_identity_ratio=0.0 if clean else 2.0,
                         Q_identity_pass=clean,
                         Q_identity_role='clean_baseline' if clean else 'predeclared_negative_control',
                         Q_identity_outcome='passed' if clean else
                         'expected_not_passed_at_original_tolerance'))
    return dict(domain='synthetic', protocol_revision='E019-D01_v1.1', cases=rows,
                tolerances=dict(rtol=1e-12, matrix=1e-12, vector=1e-15, square=1e-18))


def boxes():
    texts = dict(title=[40, 90, 60, 96], subtitle=[30, 80, 70, 86],
                 value_C1=[20, 20, 25, 25], value_C2=[45, 40, 50, 45],
                 value_C3=[70, 40, 75, 45])
    markers = {'marker_C1': [19, 8, 21, 12], 'marker_C2': [44, 49, 46, 51],
               'marker_C3': [69, 49, 71, 51]}
    return texts, markers, [0, 0, 100, 100], [10, 10, 90, 70]


class ViewUnitTests(unittest.TestCase):
    def test_no_plot_stack_or_producer_on_import(self):
        for name in ('matplotlib', 'numpy', 'scipy', 'aa2024_qsubspace_diagnostic',
                     'aa2024_kinematic_capacity'):
            self.assertNotIn(name, sys.modules)

    def test_only_scalar_copy_and_evidence_never_accessed(self):
        class Poison(dict):
            def __getitem__(self, key):
                if key == 'evidence':
                    raise AssertionError('forbidden evidence access')
                return super().__getitem__(key)
        source = Poison(fixture())
        original = copy.deepcopy(source)
        selected = v.select_values(source)
        self.assertEqual(source, original)
        self.assertEqual(selected, source)
        self.assertIsNot(selected['cases'][1], source['cases'][1])

    def test_identity_order_and_tolerances_fail_closed(self):
        for field, value in (('domain', 'real'), ('protocol_revision', 'changed'),
                             ('tolerances', {}), ('cases', list(reversed(fixture()['cases'])))):
            with self.subTest(field=field), self.assertRaises((ValueError, KeyError)):
                source = fixture()
                source[field] = value
                v.select_values(source)

    def test_reject_nonfinite_bool_negative_and_out_of_range(self):
        for value in (float('nan'), float('inf'), True, -1, 1e9, '2', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                source = fixture()
                source['cases'][2]['Q_identity_ratio'] = value
                v.select_values(source)

    def test_zero_c0_and_negative_status_are_not_reclassified(self):
        for index, key, value in ((0, 'Q_identity_ratio', 0), (1, 'Q_identity_ratio', .1),
                                  (2, 'Q_identity_pass', True),
                                  (3, 'Q_identity_outcome', 'passed'),
                                  (2, 'Q_identity_role', 'clean_baseline')):
            with self.subTest(index=index, key=key), self.assertRaises(ValueError):
                source = fixture()
                source['cases'][index][key] = value
                v.select_values(source)

    def test_nonstandard_json_constants_rejected(self):
        for token in ('NaN', 'Infinity', '-Infinity'):
            with self.subTest(token=token), self.assertRaises(ValueError):
                json.loads('{"unused":' + token + '}', parse_constant=v.reject_constant)

    def test_layout_allows_zero_marker_across_axis_not_canvas(self):
        texts, markers, canvas, axes = boxes()
        self.assertTrue(v.check_boxes(texts, markers, canvas, axes)['passed'])

    def test_marker_and_text_canvas_margins(self):
        for which in ('text', 'marker'):
            with self.subTest(which=which), self.assertRaises(ValueError):
                texts, markers, canvas, axes = boxes()
                if which == 'text':
                    texts['title'] = [1, 90, 60, 96]
                else:
                    markers['marker_C1'] = [19, 1, 21, 12]
                v.check_boxes(texts, markers, canvas, axes)

    def test_overlap_axis_escape_and_nonfinite_stop(self):
        for bad in ([40, 90, 60, 96], [0, 20, 25, 25], [20, 20, float('nan'), 25]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                texts, markers, canvas, axes = boxes()
                texts['value_C1'] = bad
                v.check_boxes(texts, markers, canvas, axes)

    def test_artificial_file_hash_and_exclusive_writes(self):
        root = Path(os.environ['E019_VIEW_TEST_ROOT'])
        with tempfile.TemporaryDirectory(prefix='artificial-', dir=root) as folder:
            path = Path(folder) / 'toy.json'
            v.write_new_json(path, fixture())
            data = path.read_bytes()
            self.assertEqual(v.checked_bytes(path, v.digest(data)), data)
            with self.assertRaises(ValueError):
                v.checked_bytes(path, '0' * 64)
            with self.assertRaises(FileExistsError):
                v.write_new_json(path, {})
            link = Path(folder) / 'link.json'
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                v.checked_bytes(link, v.digest(data))

    def test_sidecar_copies_not_calculates(self):
        text = v.sidecar(v.select_values(fixture()))
        for phrase in ('How to read', 'Data provenance', 'Limitations', '2.0',
                       'C0 is not applicable', 'actual E019 root cause'):
            self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main(failfast=True, verbosity=2)
