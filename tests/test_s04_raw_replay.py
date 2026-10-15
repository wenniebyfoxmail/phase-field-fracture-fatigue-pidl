import csv
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / 'SENS_tensile'))

import s04_raw as production
import s04_raw_replay as replay
import s04_raw_replay_report as report
from s04_g5_features import FIELDS, FeaturePipeline


def generated_cases():
    cells = 13
    contained = np.array([True] * 12 + [False])
    centers = np.column_stack((np.linspace(-0.5, 0.5, cells),
                               np.sin(np.arange(cells)) * 0.07))
    areas = np.linspace(0.5, 1.7, cells)
    pipeline = FeaturePipeline(centers, areas, contained)
    cases = {}
    grid = np.linspace(0.0, 1.0, cells, dtype=np.float32)
    counts = {'u011': 121, 'u0115': 99, 'u012': 82, 'u013': 55}
    for key, count in counts.items():
        umax = {'u011': 0.11, 'u0115': 0.115, 'u012': 0.12, 'u013': 0.13}[key]
        pin = {name: np.empty((count, cells), dtype=np.float32) for name in FIELDS}
        fem = {name: np.empty((count, cells), dtype=np.float32)
               for name in ('damage', 'alpha_bar', 'psi_raw_direct')}
        for index in range(count):
            cycle = index + 1
            pin['damage'][index] = -0.0001 + 0.34 * grid + cycle * 0.0002
            pin['alpha_bar'][index] = 0.2 + grid + cycle * 0.008 + umax
            pin['fatigue_f'][index] = 0.82 - 0.2 * grid
            pin['psi_raw_direct'][index] = 0.5 + grid**2 + cycle * 0.004 + 2 * umax
            fem['damage'][index] = np.clip(pin['damage'][index] + 0.01, 0, 1)
            fem['alpha_bar'][index] = pin['alpha_bar'][index] + 0.03
            fem['psi_raw_direct'][index] = (pin['psi_raw_direct'][index] + 0.12
                                             + 0.05 * grid + cycle * 0.0003)
        cases[key] = dict(pin=pin, fem=fem, n=count, umax=umax)
    return cases, pipeline


def complete_parent(parent: Path, cases: dict, pipeline) -> None:
    parent.mkdir()
    info = production.pipeline_run(cases, pipeline, parent, sample_count=10)
    decision = json.loads((parent / 'decision.json').read_text())
    with (parent / 'folds.csv').open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['holdout', 'fallback', 'R', 'G'])
        writer.writeheader(); writer.writerows(decision['folds'])
    receipt = dict(status='COMPLETED', run_id=replay.PARENT_RUN,
                   code_commit=replay.PARENT_CODE, design_commit='45b8d32',
                   lock_sha256=replay.LOCK_SHA, mode='generated_fixture', **info)
    (parent / 'receipt.json').write_text(json.dumps(receipt, indent=2))
    (parent / 'V0_V1_holdouts.png').write_bytes(b'generated fixture only')
    (parent / 'u0115_C20_raw.png').write_bytes(b'generated fixture only')
    (parent / 'README_analysis.md').write_text('generated fixture only')


class FrozenReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.cases, cls.pipeline = generated_cases()
        cls.parent = cls.root / replay.PARENT_RUN
        complete_parent(cls.parent, cls.cases, cls.pipeline)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_complete_generated_replay_without_fit_or_selection(self):
        destination = self.root / 'replay_complete'
        result = replay.replay(self.cases, self.pipeline, self.parent, destination)
        self.assertEqual(result['status'], 'REPLAY_REPRODUCED')
        self.assertEqual(result['rows'], 357)
        self.assertFalse(result['fit_performed'])
        self.assertFalse(result['selection_performed'])
        self.assertFalse(result['confirmation_accessed'])
        report_result = report.generate(destination)
        self.assertTrue((destination / 'replay_decision.png').is_file())
        self.assertTrue((destination / 'replay_decision.md').is_file())
        sidecar = (destination / 'replay_decision.md').read_text().lower()
        for phrase in ('how to read', 'data provenance', 'limitation'):
            self.assertIn(phrase, sidecar)
        self.assertGreater(len(sidecar), 400)
        analysis = (destination / 'README_analysis.md').read_text().lower()
        for phrase in ('scientific question', 'evidence source', 'reading order',
                       'allowed conclusion', 'blocked conclusion', 'storyline impact'):
            self.assertIn(phrase, analysis)
        validation = subprocess.run(
            [sys.executable, str(ROOT / 'source/validate_figure_sidecars.py'),
             str(destination)], check=False, capture_output=True, text=True)
        self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)
        self.assertLessEqual(report_result['percycle_max_tolerance_fraction'], 1.0)
        with (destination / 'percycle_comparison.csv').open() as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 357)
        self.assertLess(max(float(row['V1_tolerance_fraction']) for row in rows), 1.0)

    def test_explicit_scalar_accumulation_matches_matrix_reference(self):
        rng = np.random.default_rng(822)
        x = rng.normal(size=(31, 32))
        coefficients = rng.normal(size=(3, 33, 1))
        model = dict(xm=rng.normal(size=32), xstd=rng.uniform(0.1, 2, size=32),
                     ym=np.array([0.7]), ystd=np.array([1.3]), scales=np.array([2.0, 4.0]),
                     coefficients=coefficients)
        actual = replay.scalar_prediction(x, model, 1)
        design = np.column_stack((np.ones(len(x)), (x - model['xm']) / model['xstd']))
        expected = model['scales'][1] * (
            (design @ coefficients[1, :, 0]) * model['ystd'][0] + model['ym'][0])
        np.testing.assert_allclose(actual, expected, rtol=2e-15, atol=2e-15)

    def test_saved_mse_corruption_fails_closed(self):
        corrupted = self.root / 'corrupted_parent'
        shutil.copytree(self.parent, corrupted)
        with (corrupted / 'percycle.csv').open() as handle:
            rows = list(csv.DictReader(handle))
        rows[0]['V1_physical_mse'] = str(float(rows[0]['V1_physical_mse']) + 1e-3)
        with (corrupted / 'percycle.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
        corrupted.rename(self.root / 'renamed_corrupted')
        renamed = self.root / 'renamed_corrupted'
        target = self.root / replay.PARENT_RUN
        original = self.parent
        original.rename(self.root / 'parent_saved')
        renamed.rename(target)
        try:
            with self.assertRaisesRegex(replay.ReplayError, 'replay mismatch'):
                replay.replay(self.cases, self.pipeline, target, self.root / 'must_not_exist')
            self.assertFalse((self.root / 'must_not_exist').exists())
        finally:
            target.rename(self.root / 'corrupted_done')
            (self.root / 'parent_saved').rename(original)

    def test_parent_hash_mismatch_fails_before_output(self):
        output = self.root / 'hash_mismatch_output'
        hashes = replay.file_hashes(self.parent)
        hashes['models.json'] = '0' * 64
        with self.assertRaisesRegex(replay.ReplayError, 'SHA-256 mismatch'):
            replay.replay(self.cases, self.pipeline, self.parent, output,
                          expected_hashes=hashes)
        self.assertFalse(output.exists())

    def test_missing_authorization_fails_before_output(self):
        output = self.root / 'not_created'
        with self.assertRaisesRegex(replay.ReplayError, 'authorization'):
            replay.authorization(None, output, self.parent)
        self.assertFalse(output.exists())

    def test_generated_authorization_binds_head_paths_and_parent_hashes(self):
        output = self.root / 'S04-E022-R001'
        commit = subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        record = dict(user_approved_real_replay=True,
                      independent_code_review='APPROVED',
                      experiment_id='S04-E022', run_id='S04-E022-R001',
                      code_commit=commit, parent_result_commit=replay.PARENT_RESULT,
                      parent_run_id=replay.PARENT_RUN, lock_sha256=replay.LOCK_SHA,
                      source_run=str(self.parent.resolve()), output=str(output.resolve()),
                      source_file_sha256=replay.file_hashes(self.parent))
        path = self.root / 'generated_authorization.json'
        path.write_text(json.dumps(record))
        self.assertEqual(replay.authorization(path, output, self.parent), record)
        self.assertFalse(output.exists())

    def test_replay_module_has_no_fit_or_production_evaluate_dependency(self):
        text = (ROOT / 'SENS_tensile/s04_raw_replay.py').read_text()
        self.assertNotIn('production.fit', text)
        self.assertNotIn('production.evaluate', text)
        self.assertNotIn('from s04_raw import', text)

    def test_nonnegative_projection_and_cancellation_are_finite(self):
        x = np.ones((7, 32), dtype=np.float64)
        beta = np.zeros((3, 33, 1), dtype=np.float64)
        beta[0, 0, 0] = -3.0
        beta[0, 1:, 0] = np.array([1e6, -1e6] * 16)
        model = dict(xm=np.zeros(32), xstd=np.ones(32), ym=np.zeros(1),
                     ystd=np.ones(1), scales=np.ones(2), coefficients=beta)
        residual = replay.scalar_prediction(x, model, 0)
        self.assertTrue(np.isfinite(residual).all())
        pin = np.column_stack((np.linspace(-0.2, 1.2, 7),
                               np.linspace(-0.1, 0.3, 7), np.ones(7)))
        v0, v1 = replay.map_outputs(pin, residual)
        self.assertTrue(np.all(v1[:, 2] >= 0))
        self.assertTrue(np.all(v1[:, 2] == 0))
        np.testing.assert_array_equal(v0[:, :2], v1[:, :2])
        self.assertTrue(np.all((v1[:, 0] >= 0) & (v1[:, 0] <= 1)))


if __name__ == '__main__':
    unittest.main()
