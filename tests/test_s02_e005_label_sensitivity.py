"""Deterministic synthetic checks; no real frozen predictions or fitted models."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sensitivity', ROOT / 'scripts/s02_e005_label_sensitivity.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def row(origin, target, y, q0, q1):
    return {'record': 'F', 'origin_cycle': origin, 'target_cycle': target,
            'current_x_mm': 1, 'target_dx_mm': y, 'B0_dx_mm': 0,
            'B1_dx_mm': 0, 'M0_dx_mm': q0, 'M1_dx_mm': q1}


class TestSensitivity(unittest.TestCase):
    def test_closed_form_extrema(self):
        # |1-z|-|0-z| is 1 below zero, 1-2z in [0,1], -1 above one.
        pair = s.edge_extrema(1, 0, .5, .1)
        self.assertAlmostEqual(pair[0], -.4)
        self.assertAlmostEqual(pair[1], .4)
        self.assertEqual(s.edge_extrema(1, 0, .5, 1), (-1, 1))
        self.assertEqual(s.edge_extrema(0, 1, .5, 1), (-1, 1))
        self.assertEqual(s.edge_extrema(.3, .3, 0, 1), (0, 0))

    def test_four_epsilon_can_be_sharp_on_one_edge(self):
        r = [row(0, 1000, .4, 0, 1)]
        before = s.scores(r, {0: 0, 1000: 0})['D_mm']
        after = s.scores(r, {0: -.1, 1000: .1})['D_mm']
        self.assertAlmostEqual(before - after, .4)
        self.assertAlmostEqual(s.bounds(r, .1)['lower_mm'], after)

    def test_shared_endpoint_and_constant_bias(self):
        r = [row(0, 1000, .2, 0, 1), row(1000, 2000, .8, 0, 1)]
        e = s.node_errors(s.nodes(r), .1, 'alternating_positive')
        self.assertEqual(e, {0: .1, 1000: -.1, 2000: .1})
        # Shared centre makes neighbouring label changes opposite.
        self.assertAlmostEqual(e[1000] - e[0], -.2)
        self.assertAlmostEqual(e[2000] - e[1000], .2)
        for scenario in ['constant_positive', 'constant_negative']:
            self.assertEqual(s.scores(r, s.node_errors(s.nodes(r), .1, scenario)),
                             s.scores(r, {0: 0, 1000: 0, 2000: 0}))

    def test_outer_envelope_is_not_an_attainable_path(self):
        r = [row(0, 1000, .5, 0, 1), row(1000, 2000, .5, 0, 1)]
        b = s.bounds(r, .1)
        # Each independent edge wants +.2, but total endpoint change <=.2.
        # Thus the true minimum for this example is -.2, outer lower is -.4.
        self.assertAlmostEqual(b['lower_row_mm'], -.4)
        values = [s.scores(r, {0: a, 1000: c, 2000: d})['D_mm']
                  for a in [-.1, 0, .1] for c in [-.1, 0, .1] for d in [-.1, 0, .1]]
        self.assertAlmostEqual(min(values), -.2)
        self.assertGreater(min(values), b['lower_mm'])

    def test_equal_record_not_equal_window_weight(self):
        groups = {'F': [row(0, 1000, 0, 0, 1)],
                  'FF': [row(0, 1000, 0, 0, 3), row(1000, 2000, 0, 0, 3)]}
        cfg = {'epsilon_mm': [0, .1], 'scenario_ids': s.SCENARIOS, 'zero_tolerance_mm': 1e-10}
        bs, ss = s.analyse(groups, cfg)
        b = next(r for r in bs if r['record'] == 'equal_record')
        self.assertEqual(b['D0_mm'], 2)  # pooled-window value would be 7/3
        self.assertEqual(len(bs), 6)
        self.assertEqual(len(ss), 54)

    def test_frozen_secant_is_not_recomputed(self):
        r = [row(0, 1000, .2, .1, .3)]
        r[0]['B1_dx_mm'] = .4
        z = s.scores(r, {0: -.1, 1000: .1})
        self.assertAlmostEqual(z['B1'], 0)
        self.assertEqual(r[0]['B1_dx_mm'], .4)

    def test_input_checks_with_synthetic_archive(self):
        cfg = json.loads((ROOT / 'docs/research/S02/S02-E005/label_sensitivity_config_v1.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prepared, summary, all_rows = {}, {}, []
            for record, n in cfg['expected_evaluation_rows'].items():
                rs, es = [], []
                for i in range(n):
                    r = row(i * 1000, (i + 1) * 1000, .02, .03, .05)
                    r.update(record=record, current_x_mm=1 + i * .02, B1_dx_mm=.02)
                    rs.append(r)
                    es.append({'origin': r['origin_cycle'], 'target_cycle': r['target_cycle'],
                               'current_x': r['current_x_mm'], 'target_dx': .02, 'secant_dx': .02})
                cut = {'F': 265, 'FF': 74}[record]
                prepared[record] = {'fit_count': cut, 'evaluation_count': n,
                                    'rows': [{}] * cut + es}
                summary[record] = {'mae_dx_mm': {'B0': .02, 'B1': 0, 'M0': .01, 'M1': .03},
                                   'M1_minus_M0_mm': .02}
                all_rows.extend(rs)
            summary['equal_record_mean_M1_minus_M0_mm'] = .02
            (root / 'prepared.json').write_text(json.dumps(prepared))
            (root / 'summary.json').write_text(json.dumps(summary))
            def write_rows():
                with (root / 'predictions.csv').open('w') as h:
                    w = csv.DictWriter(h, fieldnames=s.COLUMNS)
                    w.writeheader(); w.writerows(all_rows)
            write_rows()
            (root / 'source.csv').write_text('synthetic source')
            lock = {'source.csv': hashlib.md5(b'synthetic source').hexdigest()}
            self.assertEqual(len(s.validate_inputs(root, cfg, root, lock)['F']), 114)
            all_rows[1]['origin_cycle'] = all_rows[0]['origin_cycle']
            write_rows()
            with self.assertRaisesRegex(ValueError, 'non1000|duplicate'):
                s.validate_inputs(root, cfg, root, lock)
            all_rows[1]['origin_cycle'] = 1000
            all_rows[0]['M1_dx_mm'] = .06
            write_rows()
            with self.assertRaisesRegex(ValueError, 'baseline'):
                s.validate_inputs(root, cfg, root, lock)


if __name__ == '__main__':
    unittest.main()
