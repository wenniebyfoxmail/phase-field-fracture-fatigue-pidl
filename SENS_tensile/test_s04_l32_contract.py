"""Generated/static contract checks only: no solve, project run, or archive access."""
import ast
import csv
import io as textio
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import s04_l32 as worker
import s04_l32_inputs as contract
import s04_l32_guard as guard


class ContractChecks(unittest.TestCase):
    def test_late_weights(self):
        for n, count in ((99, 59), (82, 42), (55, 15)):
            w = worker.late_weights(n)
            self.assertEqual(np.count_nonzero(w), count)
            self.assertTrue(np.all(w[:40] == 0))
            self.assertTrue(np.all(w[40:] == 1/count))
            self.assertAlmostEqual(float(w.sum()), 1)
        for n in (0, 40, 40.0, True):
            with self.assertRaises(ValueError): worker.late_weights(n)

    def test_static_one_solve_no_baseline_prediction_or_scale_refit(self):
        tree = ast.parse(Path(worker.__file__).read_text())
        calls = [ast.unparse(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)]
        self.assertEqual(calls.count('np.linalg.solve'), 1)
        self.assertFalse(set(calls) & {'inherited.fit', 'inherited.evaluate', 'raw.fit', 'raw.scales', 'merge_moments'})
        fit = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'fit_one')
        self.assertNotIn('B32', ast.unparse(fit))

    def test_git_manifest_only(self):
        m = contract.manifest()
        self.assertEqual(len(m['scientific_files']), 9)
        self.assertEqual(len(m['frozen_files']), 5)
        grant = contract.grant_for('a'*40, dict(approval_ref='UNAPPROVED_TEST', review_ref='STATIC_TEST', reviewed_commit='a'*40), m)
        self.assertFalse(grant['baseline_refit']); self.assertFalse(grant['baseline_reevaluation'])
        self.assertFalse(grant['confirmation']); self.assertEqual(grant['expected_fit_count'], 1)

    def test_launch_closed_without_permission(self):
        with patch.object(guard.io, 'manifest', side_effect=AssertionError('must not read')), \
             patch.object(guard.subprocess, 'Popen', side_effect=AssertionError('must not launch')):
            with self.assertRaises(ValueError): guard.execute(contract.OUT, 'a'*40, {}, False)

    def test_child_closed_without_handoff(self):
        with patch.dict('os.environ', {}, clear=True), \
             patch.object(contract, 'manifest', side_effect=AssertionError('must not read')):
            with self.assertRaises(ValueError): contract.child_authorization(contract.OUT)

    def test_saved_eval_closed_before_fit(self):
        m = dict(frozen_files=[dict(name='percycle.csv', role='evaluation_after_fit')])
        with patch.object(contract, 'bounded_read', side_effect=AssertionError('must not read')):
            for fits, released in ((0, False), (1, False), (2, True)):
                a = dict(verified_frozen=[], fits_completed=fits, training_released=released)
                with self.assertRaises(ValueError): contract.read_frozen(m, 'percycle.csv', a)

    def test_fd_open_error_and_close_on_fd_identity_error(self):
        path = MagicMock(); path.resolve.return_value = path
        path.lstat.return_value = type('Stat', (), dict(st_mode=0o100444, st_nlink=1, st_size=1,
            st_dev=1, st_ino=1, st_mtime_ns=1))()
        with patch.object(contract.os, 'open', side_effect=OSError('mock open error')):
            with self.assertRaises(OSError): contract.bounded_read(path, 1, lambda b: b, readonly=True)
        stream = MagicMock()
        with patch.object(contract.os, 'open', return_value=73), \
             patch.object(contract.os, 'fdopen', return_value=stream), \
             patch.object(contract.os, 'fstat', side_effect=OSError('mock fd error')), \
             patch.object(contract.os, 'close') as close:
            with self.assertRaises(OSError): contract.bounded_read(path, 1, lambda b: b, readonly=True)
            close.assert_called_once_with(73)

    def test_generated_csv_bounds_and_completeness(self):
        fields = ['cycle', 'stratum', 'cycle_weight', 'V0_physical_mse', 'B32_physical_mse',
                  'B32_raw_min', 'B32_raw_negative_area', 'B32_damage_history_identical']
        def data(bad=None):
            f = textio.StringIO(); w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
            for c, weight in enumerate(worker.cycle_weights(121), 1):
                row = dict(zip(fields, [c, min((c-1)//20, 2), weight, 1, 1, 0, 0, 'True']))
                if c == 1 and bad: row.update(bad)
                w.writerow(row)
            return f.getvalue().encode()
        self.assertEqual(len(worker.saved_rows(data())), 121)
        for bad in ({'cycle': 0}, {'stratum': 2}, {'B32_physical_mse': 'NaN'},
                    {'B32_raw_min': -1}, {'B32_damage_history_identical': 'False'}):
            with self.assertRaises(ValueError): worker.saved_rows(data(bad))


if __name__ == '__main__': unittest.main()
