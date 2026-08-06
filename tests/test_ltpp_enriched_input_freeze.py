from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from ltpp_build_enriched_input_freeze import (  # noqa: E402
    V3_AMENDMENT_SHA256,
    active_structure,
    active_traffic,
    build_split_receipt,
    select_transition_set,
    trailing_climate,
)


class EnrichedInputFreezeTest(unittest.TestCase):
    @staticmethod
    def synthetic_transitions() -> list[dict]:
        section_counts = {
            "06-1253": 7,
            "06-2041": 7,
            "06-2647": 4,
            "06-8149": 5,
            "06-8150": 4,
            "06-8201": 4,
        }
        rows = []
        for section, count in section_counts.items():
            for index in range(1, count + 1):
                rows.append(
                    {
                        "transition_id": f"{section}-T{index:02d}",
                        "section": section,
                        "development_transition": index < count,
                        "future_time_test": index == count,
                    }
                )
        return rows

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

    def test_v3_selection_allows_only_exact_named_exclusion_and_hash(self) -> None:
        transitions = self.synthetic_transitions()
        with tempfile.TemporaryDirectory() as directory:
            amendment = Path(directory) / "amendment.md"
            amendment.write_text("wrong bytes", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                select_transition_set(transitions, ["06-2041-T01"], amendment)
        with self.assertRaisesRegex(ValueError, "Only the exact approved exclusion"):
            select_transition_set(transitions, ["06-2041-T02"], None)
        self.assertEqual(len(V3_AMENDMENT_SHA256), 64)

    def test_v3_split_receipt_is_fixed_30_row_loso_and_24_plus_6(self) -> None:
        transitions = [
            row
            for row in self.synthetic_transitions()
            if row["transition_id"] != "06-2041-T01"
        ]
        protocol = {
            "protocol": "v3_30_row_complete_input_sensitivity",
            "excluded_transition_ids": ["06-2041-T01"],
        }
        receipt = build_split_receipt(transitions, protocol)
        self.assertEqual(receipt["transition_count"], 30)
        self.assertEqual(receipt["future_time"]["train_count"], 24)
        self.assertEqual(receipt["future_time"]["test_count"], 6)
        self.assertEqual(
            {fold["held_out_section"]: fold["test_count"] for fold in receipt["loso"]},
            {
                "06-1253": 7,
                "06-2041": 6,
                "06-2647": 4,
                "06-8149": 5,
                "06-8150": 4,
                "06-8201": 4,
            },
        )
        self.assertEqual(receipt["outcome_fields_used"], [])


if __name__ == "__main__":
    unittest.main()
