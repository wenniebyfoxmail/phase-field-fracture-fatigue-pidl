import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_inventory_registration_controls_v2.py"
SPEC = importlib.util.spec_from_file_location("ltpp_inventory_registration_controls_v2", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def row():
    return {
        "survey_date": "20000101",
        "qualification_mode": "dense_internal_grid",
        "source_sha256": "source",
        "source_height": 500,
        "source_width": 1524,
        "x0": 0,
        "x1": 1000,
        "y0": 0,
        "y1": 500,
        "detected_vertical_positions": [100 * i for i in range(11)],
        "detected_horizontal_positions": [100 * i for i in range(6)],
    }


def test_inventory_marks_historical_candidates_non_independent():
    result = MODULE.inventory_row(row())
    assert result["candidate_lines_missing"] == 0
    assert result["candidate_lines_ambiguous"] == 0
    assert result["independent_final_controls_available"] is False
    assert all(
        line["historical_v1_status"] == "non_independent_of_v1"
        for line in result["line_candidates"]
    )


def test_inventory_counts_missing_and_ambiguous_candidates():
    value = row()
    value["detected_vertical_positions"].remove(200)
    value["detected_vertical_positions"].extend([395, 405])
    result = MODULE.inventory_row(value)
    assert result["candidate_lines_missing"] == 1
    assert result["candidate_lines_ambiguous"] == 1
