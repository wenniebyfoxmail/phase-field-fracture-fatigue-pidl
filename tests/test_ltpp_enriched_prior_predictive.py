from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from ltpp_run_enriched_prior_predictive import (  # noqa: E402
    inverse_growth,
    run_fold,
    standardized_eval,
)


class EnrichedPriorPredictiveTest(unittest.TestCase):
    def test_standardization_uses_training_rows_and_records_zero_variance(self) -> None:
        rows = {
            "a": {"section": "s1", "G1_source_crack_length_m": "0", "G3_forecast_horizon_years": "2"},
            "b": {"section": "s2", "G1_source_crack_length_m": "3", "G3_forecast_horizon_years": "2"},
            "c": {"section": "s3", "G1_source_crack_length_m": "8", "G3_forecast_horizon_years": "9"},
        }
        values, zero = standardized_eval(
            rows,
            ["a", "b"],
            ["c"],
            ("G1_source_crack_length_m", "G3_forecast_horizon_years"),
        )
        self.assertEqual(zero, ["G3_forecast_horizon_years"])
        self.assertEqual(values["c"][1], 0.0)
        self.assertGreater(values["c"][0], 1.0)

    def test_inverse_growth_is_nonnegative_and_overflow_safe(self) -> None:
        self.assertEqual(inverse_growth(-2.0), 0.0)
        self.assertEqual(inverse_growth(0.0), 0.0)
        self.assertGreater(inverse_growth(1.0), 0.0)
        self.assertEqual(inverse_growth(1000.0), float("inf"))

    def test_prior_fold_is_deterministic_and_shares_row_count_contract(self) -> None:
        features = ("G3_forecast_horizon_years",)
        rows = {
            "a": {"section": "s1", "G3_forecast_horizon_years": "1"},
            "b": {"section": "s2", "G3_forecast_horizon_years": "2"},
            "c": {"section": "s3", "G3_forecast_horizon_years": "3"},
        }
        first = run_fold(rows, ["a", "b"], ["c"], features, 123)
        second = run_fold(rows, ["a", "b"], ["c"], features, 123)
        self.assertEqual(first, second)
        self.assertEqual(first["row_level_prediction_count"], 500)


if __name__ == "__main__":
    unittest.main()
