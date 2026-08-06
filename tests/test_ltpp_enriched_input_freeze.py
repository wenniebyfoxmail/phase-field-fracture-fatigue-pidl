from __future__ import annotations

import sys
import unittest
from datetime import date
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from ltpp_build_enriched_input_freeze import (  # noqa: E402
    active_structure,
    active_traffic,
    trailing_climate,
)


class EnrichedInputFreezeTest(unittest.TestCase):
    def test_traffic_requires_exact_construction_year_pair(self) -> None:
        rows = [
            {
                "CONSTRUCTION_NO": "2",
                "YEAR": "1995",
                "ANNUAL_ESAL_TREND": "100",
                "AADTT_ALL_TRUCKS_TREND": "20",
                "ESAL_SOURCE": "1",
                "AADTT_SOURCE": "M",
            }
        ]
        with self.assertRaisesRegex(ValueError, "found 0"):
            active_traffic(rows, construction=3, year=1995)

    def test_structure_uses_top_layer_and_excludes_subgrade(self) -> None:
        rows = [
            {"CONSTRUCTION_NO": "1", "LAYER_NO": "1", "REPR_THICKNESS": "9", "RECORD_STATUS": "E"},
            {"CONSTRUCTION_NO": "1", "LAYER_NO": "2", "REPR_THICKNESS": "4", "RECORD_STATUS": "E"},
            {"CONSTRUCTION_NO": "1", "LAYER_NO": "3", "REPR_THICKNESS": "2", "RECORD_STATUS": "E"},
        ]
        result = active_structure(rows, construction=1, millimetres_per_stored_unit=25.4)
        self.assertAlmostEqual(result["top_mm"], 50.8)
        self.assertAlmostEqual(result["total_non_subgrade_mm"], 152.4)

    def test_trailing_climate_uses_exact_365_25_day_window(self) -> None:
        months = {
            (year, month): 10.0
            for year in (1999, 2000, 2001)
            for month in range(1, 13)
        }
        precipitation = {
            (year, month): float(__import__("calendar").monthrange(year, month)[1])
            for year in (1999, 2000, 2001)
            for month in range(1, 13)
        }
        result = trailing_climate(date(2001, 1, 1), months, precipitation)
        self.assertAlmostEqual(result["coverage_days"], 365.25)
        self.assertAlmostEqual(result["temperature_C"], 10.0)
        self.assertAlmostEqual(result["precipitation_mm"], 365.25)


if __name__ == "__main__":
    unittest.main()
