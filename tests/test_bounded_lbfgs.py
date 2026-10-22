import importlib.util
from pathlib import Path
import time
import unittest
import torch

spec = importlib.util.spec_from_file_location('bounded_lbfgs', Path(__file__).resolve().parents[1] / 'source/bounded_lbfgs.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class BoundedInnerTests(unittest.TestCase):
    def test_quadratic_and_all_calls_counted(self):
        seen = []
        def evaluate(x):
            seen.append(x.clone())
            return float((x - 2).square().sum()), 2 * (x - 2)
        x, info = mod.minimize(evaluate, torch.zeros(3, dtype=torch.float64),
            max_calls=30, deadline=time.monotonic()+3, gradient_tolerance=1e-8)
        self.assertTrue(torch.allclose(x, torch.full_like(x, 2)))
        self.assertEqual(info['calls'], len(seen))

    def test_domain_trial_rolls_back_at_cap(self):
        seen = []
        def evaluate(x):
            seen.append(x.clone())
            if float(x[0]) <= 0:
                return None, None
            return float(x.square().sum()), 2*x
        x0 = torch.tensor([.25], dtype=torch.float64)
        x, info = mod.minimize(evaluate, x0, max_calls=2,
            deadline=time.monotonic()+3, gradient_tolerance=1e-10)
        self.assertTrue(torch.equal(x, x0))
        self.assertEqual(info['calls'], 2)
        self.assertEqual(info['invalid_trials'], 1)

    def test_initial_domain_rejected(self):
        with self.assertRaises(ValueError):
            mod.minimize(lambda x: (None,None), torch.ones(1), max_calls=3,
                deadline=time.monotonic()+3, gradient_tolerance=1e-8)

    def test_expired_budget_returns_accepted_initial(self):
        x, info = mod.minimize(lambda x: (float(x.square().sum()), 2*x), torch.ones(1),
            max_calls=20, deadline=time.monotonic()-1, gradient_tolerance=1e-8)
        self.assertEqual(info['calls'], 1)
        self.assertEqual(info['reason'], 'wall_cap')
        self.assertEqual(float(x[0]), 1.)


if __name__ == '__main__':
    unittest.main()
