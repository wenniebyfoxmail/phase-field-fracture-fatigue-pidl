from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from ltpp_run_enriched_oracle import realized_traffic  # noqa: E402


class EnrichedOracleTest(unittest.TestCase):
    def test_realized_traffic_prorates_esal_and_day_weights_aadtt(self) -> None:
        rows = [
            {
                "CONSTRUCTION_NO": "1",
                "YEAR": "2000",
                "ANNUAL_ESAL_TREND": "3660",
                "AADTT_ALL_TRUCKS_TREND": "100",
            },
            {
                "CONSTRUCTION_NO": "1",
                "YEAR": "2001",
                "ANNUAL_ESAL_TREND": "3650",
                "AADTT_ALL_TRUCKS_TREND": "200",
            },
        ]
        result = realized_traffic(
            date(2000, 7, 1), date(2001, 7, 1), construction=1, rows=rows
        )
        self.assertAlmostEqual(result["coverage_fraction"], 1.0)
        self.assertAlmostEqual(result["realized_esal"], 3650.0)
        self.assertAlmostEqual(
            result["realized_mean_aadtt"], (184 * 100 + 181 * 200) / 365
        )

    def test_realized_traffic_fails_closed_on_missing_year(self) -> None:
        rows = [
            {
                "CONSTRUCTION_NO": "1",
                "YEAR": "2000",
                "ANNUAL_ESAL_TREND": "3660",
                "AADTT_ALL_TRUCKS_TREND": "100",
            }
        ]
        with self.assertRaisesRegex(ValueError, "coverage incomplete"):
            realized_traffic(
                date(2000, 7, 1), date(2001, 7, 1), construction=1, rows=rows
            )


if __name__ == "__main__":
    unittest.main()
