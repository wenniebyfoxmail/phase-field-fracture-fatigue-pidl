import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from aa2024_rigid_observable import quotient_residual


class RigidObservableTests(unittest.TestCase):
    def setUp(self):
        x, y = np.meshgrid(np.linspace(-2, 2, 7), np.linspace(-1, 1, 5))
        self.xy = np.c_[x.ravel(), y.ravel()]
        self.w = np.linspace(1, 2, len(self.xy))

    def rigid(self, t, omega):
        return np.array(t) + omega * np.c_[-self.xy[:, 1], self.xy[:, 0]]

    def test_one_global_rigid_field_is_removed(self):
        out = quotient_residual(self.xy, self.rigid((.03, -.07), .002), self.w)
        np.testing.assert_allclose(out, 0, atol=1e-14)

    def test_independent_stage_gauges_leave_full_synthetic_q_profile_invariant(self):
        # Abstract candidate residual family, NOT a FEM solve or real q evidence.
        shape = np.c_[self.xy[:, 0] ** 2, self.xy[:, 0] * self.xy[:, 1]]
        r7 = self.rigid((.02, -.01), .004)
        r8 = self.rigid((-.05, .02), -.002)
        r9 = self.rigid((.01, .09), .003)
        alpha = 2.1
        gauge = (r9 - r7) - alpha * (r8 - r7)
        for q in np.linspace(0, .95, 21):
            residual = (.42 - q) * shape
            before = quotient_residual(self.xy, residual, self.w)
            after = quotient_residual(self.xy, residual + gauge, self.w)
            np.testing.assert_allclose(before, after, atol=1e-14)

    def test_nonrigid_opening_is_not_removed(self):
        opening = np.c_[np.zeros(len(self.xy)), np.sign(self.xy[:, 1])]
        out = quotient_residual(self.xy, opening, self.w)
        self.assertGreater(np.linalg.norm(out), 1)

    def test_rank_failure_and_missing_values_are_rejected(self):
        with self.assertRaises(ValueError):
            quotient_residual(np.zeros((3, 2)), np.zeros((3, 2)), np.ones(3))
        r = np.zeros_like(self.xy)
        r[0, 0] = np.nan
        with self.assertRaises(ValueError):
            quotient_residual(self.xy, r, self.w)

    def test_zero_weight_is_not_a_silent_mask(self):
        w = self.w.copy()
        w[0] = 0
        with self.assertRaises(ValueError):
            quotient_residual(self.xy, np.zeros_like(self.xy), w)


if __name__ == "__main__":
    unittest.main()
