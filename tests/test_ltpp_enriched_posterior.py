from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from ltpp_run_enriched_posterior import (  # noqa: E402
    aggregate,
    contrast,
    empirical_crps,
    standardize_fold,
)


class EnrichedPosteriorTest(unittest.TestCase):
    def test_empirical_crps_for_degenerate_forecast_is_absolute_error(self) -> None:
        self.assertAlmostEqual(empirical_crps(np.zeros(50), 3.0), 3.0)

    def test_fold_standardization_uses_training_only_and_zeroes_constant(self) -> None:
        rows = {
            "a": {"G1_source_crack_length_m": "0", "G3_forecast_horizon_years": "2"},
            "b": {"G1_source_crack_length_m": "3", "G3_forecast_horizon_years": "2"},
            "c": {"G1_source_crack_length_m": "8", "G3_forecast_horizon_years": "9"},
        }
        train, evaluation, zero = standardize_fold(
            rows,
            ["a", "b"],
            ["c"],
            ("G1_source_crack_length_m", "G3_forecast_horizon_years"),
        )
        self.assertEqual(zero, ["G3_forecast_horizon_years"])
        self.assertTrue(np.allclose(train[:, 1], 0.0))
        self.assertEqual(evaluation[0, 1], 0.0)
        self.assertGreater(evaluation[0, 0], 1.0)

    @staticmethod
    def metric_row(
        model: str, section: str, index: int, error: float, covered: int = 1
    ) -> dict:
        return {
            "model": model,
            "design": "LOSO",
            "transition_id": f"{section}-{index}",
            "section": section,
            "absolute_error_m": error,
            "squared_error_m2": error * error,
            "crps_m": error,
            "covered_90": covered,
        }

    def test_contrast_uses_all_four_frozen_gates(self) -> None:
        sections = [f"s{index}" for index in range(6)]
        reference = []
        challenger = []
        for section_index, section in enumerate(sections):
            for row_index in range(5):
                unique_index = 5 * section_index + row_index
                reference.append(
                    self.metric_row("M0", section, unique_index, 10.0)
                )
                challenger.append(
                    self.metric_row(
                        "M1", section, unique_index, 8.0, int(unique_index < 27)
                    )
                )
        rows = {"M0": reference, "M1": challenger}
        result = contrast("M1", "M0", rows)
        self.assertTrue(result["gates"]["mae_reduction_at_least_10pct"])
        self.assertTrue(result["gates"]["section_improvement_at_least_4_of_6"])
        self.assertTrue(result["gates"]["coverage_exactly_26_to_28"])
        self.assertTrue(result["gates"]["crps_worsening_no_more_than_5pct"])
        self.assertTrue(result["passed"])
        self.assertEqual(aggregate(challenger)["count"], 30)


if __name__ == "__main__":
    unittest.main()
