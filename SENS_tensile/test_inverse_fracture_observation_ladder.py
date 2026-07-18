"""Fast, no-training checks for the c87 observation-ladder primitives."""
from __future__ import annotations

import unittest
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from inverse_fracture_observation_ladder import (
    RAW,
    Config,
    direct_analysis,
    laplacian_analysis,
    noisy_log_raw,
    select_mask,
)


class ObservationLadderTest(unittest.TestCase):
    def setUp(self) -> None:
        xx, yy = np.meshgrid(np.linspace(0.0, 1.0, 12), np.linspace(-0.2, 0.2, 6))
        self.coordinates = np.column_stack((xx.ravel(), yy.ravel()))
        count = len(self.coordinates)
        self.prior = np.zeros((count, 4), dtype=np.float64)
        self.prior[:, 0] = np.exp(-((self.coordinates[:, 0] - 0.65) / 0.15) ** 2)
        self.prior[:, RAW] = self.coordinates[:, 0]
        source = np.arange(count - 1)
        self.edges = np.vstack((source, source + 1))

    def test_masks_have_requested_density_and_are_deterministic(self) -> None:
        expected = round(len(self.coordinates) * 0.1)
        mask_a = select_mask(self.coordinates, self.prior, self.edges, 0.1, "adaptive", 42)
        mask_b = select_mask(self.coordinates, self.prior, self.edges, 0.1, "adaptive", 42)
        self.assertEqual(int(mask_a.sum()), expected)
        np.testing.assert_array_equal(mask_a, mask_b)

    def test_direct_analysis_only_changes_observed_raw_channel(self) -> None:
        mask = select_mask(self.coordinates, self.prior, self.edges, 0.1, "random", 2)
        observed = self.prior[:, RAW] + 1.0
        result = direct_analysis(self.prior, mask, observed)
        np.testing.assert_allclose(result[mask, RAW], observed[mask])
        np.testing.assert_allclose(result[~mask, RAW], self.prior[~mask, RAW])
        np.testing.assert_allclose(result[:, :RAW], self.prior[:, :RAW])

    def test_variational_analysis_preserves_observations_and_is_finite(self) -> None:
        mask = select_mask(self.coordinates, self.prior, self.edges, 0.1, "uniform", 3)
        observed = self.prior[:, RAW] + 0.25
        result = laplacian_analysis(self.prior, mask, observed, self.edges, iterations=4)
        np.testing.assert_allclose(result[mask, RAW], observed[mask])
        self.assertTrue(np.isfinite(result).all())

    def test_zero_noise_is_identity(self) -> None:
        value = self.prior[:, RAW]
        np.testing.assert_array_equal(noisy_log_raw(value, 0.0, np.random.default_rng(1)), value)
        self.assertEqual(Config("raw_full_field", 1.0, "uniform", 0.0, "direct").fraction, 1.0)


if __name__ == "__main__":
    unittest.main()
