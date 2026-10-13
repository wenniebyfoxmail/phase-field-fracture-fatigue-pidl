import importlib.util
from pathlib import Path
import unittest

import numpy as np

spec = importlib.util.spec_from_file_location('runner', Path(__file__).parents[1]
                                           / 'scripts/s02_e005_fatacrack_history.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class CausalityTests(unittest.TestCase):
    def test_future_values_cannot_change_origin_features(self):
        targets = {n: np.array([n / 1000, 6.0]) for n in range(1000, 10001, 1000)}
        signals = {n: np.array([n / 100, n / 200]) for n in targets}
        a = m.build_rows(targets, signals)[0]
        targets[4000] = np.array([999., 100.])
        signals[4000] = np.array([10000., 10000.])
        b = m.build_rows(targets, signals)[0]
        self.assertEqual(a['features'], b['features'])
        self.assertNotEqual(a['target_dx'], b['target_dx'])

    def test_999_gap_is_not_repaired(self):
        targets = {n: np.array([1., 6.]) for n in [1001, 2001, 3001, 4000, 5000]}
        signals = {n: np.zeros(2) for n in targets}
        self.assertEqual(m.build_rows(targets, signals), [])

    def test_ridge_test_scaling_is_prefix_only(self):
        train = np.array([[1., 7.], [2., 7.], [3., 7.]])
        y = np.array([1., 2., 3.])
        a, state = m.ridge_predict(train, y, np.array([[4., 7.]]))
        b, other = m.ridge_predict(train, y, np.array([[4., 7.], [1e9, 9e9]]))
        self.assertAlmostEqual(a[0], b[0])
        self.assertEqual(state, other)
        self.assertEqual(state['active'], [True, False])


if __name__ == '__main__':
    unittest.main()
