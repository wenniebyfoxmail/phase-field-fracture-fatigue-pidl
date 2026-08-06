import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_audit_spatial_registration.py"
SPEC = importlib.util.spec_from_file_location("ltpp_audit_spatial_registration", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def perfect_row():
    return {
        "survey_date": "20000101", "qualification_mode": "synthetic",
        "x0": 100, "x1": 1100, "y0": 50, "y1": 550,
        "detected_vertical_positions": [100 + 100 * i for i in range(11)],
        "detected_horizontal_positions": [50 + 100 * i for i in range(6)],
    }


def test_exact_grid_qualifies_and_has_fifteen_dependent_intersections():
    result = MODULE.audit_row(perfect_row())
    assert result["status"] == "SPATIAL_REGISTRATION_QUALIFIED"
    assert len(result["axis_residuals"]) == 8
    assert result["intersection_median_m"] < 1e-12
    assert result["intersection_p95_m"] < 1e-12
    assert result["intersection_max_m"] < 1e-12


def test_tie_break_selects_lower_pixel_coordinate():
    row = perfect_row()
    row["detected_vertical_positions"] = [value for value in row["detected_vertical_positions"] if value != 200]
    row["detected_vertical_positions"].extend([195, 205])
    selected = MODULE.extract_axis_lines(row, "x")[1]
    assert selected["candidate_count"] == 2
    assert selected["selected_pixel"] == 195


def test_missing_fixed_line_fails_closed():
    row = perfect_row()
    row["detected_vertical_positions"].remove(200)
    result = MODULE.audit_row(row)
    assert result["status"] == "INSUFFICIENT_CONTROL_POINTS"
    assert result["missing_line_count"] == 1
    assert result["intersection_median_m"] is None


def test_heldout_shift_above_gate_does_not_qualify():
    row = perfect_row()
    row["detected_vertical_positions"].remove(200)
    row["detected_vertical_positions"].append(217)
    result = MODULE.audit_row(row)
    assert result["status"] == "SPATIAL_REGISTRATION_NOT_QUALIFIED"
    assert result["intersection_max_m"] > MODULE.MAX_GATE_M
