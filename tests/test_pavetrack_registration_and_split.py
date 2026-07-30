from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "SENS_tensile" / "audit_pavetrack_registration_and_split.py"
SPEC = importlib.util.spec_from_file_location("pavetrack_registration", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_reconciliation_explains_duplicate_and_filename_counts() -> None:
    workbook = [
        ("1", "same.jpg", "A"),
        ("1", "same.jpg", "A"),
        ("1", "same.jpg", "B"),
        ("2", "same.jpg", "A"),
    ]
    manifest = [
        {"reid": "1", "img_name": "same.jpg", "category": "A"},
        {"reid": "1", "img_name": "same.jpg", "category": "B"},
        {"reid": "2", "img_name": "same.jpg", "category": "A"},
    ]
    result = MODULE.reconcile_counts(workbook, manifest)
    assert result["counts_reconciled"]
    assert result["workbook_exact_duplicate_annotation_rows"] == 1
    assert result["unique_location_image_pairs"] == 2
    assert result["unique_filename_only"] == 1
    assert result["cross_location_filename_collisions"] == 1


def test_location_split_is_location_isolated_and_deterministic() -> None:
    rows = [
        {"reid": str(index), "category": category, "img_name": f"{index}.jpg"}
        for index in range(40)
        for category in ("Alligator Crack", "Transverse Crack")
    ]
    locations_a, summary_a = MODULE.build_location_split(rows)
    locations_b, summary_b = MODULE.build_location_split(list(reversed(rows)))
    assert locations_a == locations_b
    assert summary_a == summary_b
    assert len({row["reid"] for row in locations_a}) == 40
    assert sum(row["locations"] for row in summary_a) == 40


def test_registration_gate_rejects_degenerate_homography_metrics() -> None:
    gate = MODULE.REGISTRATION_GATE
    assert gate["min_inliers"] >= 4
    assert gate["min_projected_area_ratio"] > 0
    assert gate["max_projected_area_ratio"] < 10
