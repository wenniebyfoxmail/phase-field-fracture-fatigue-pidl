import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ltpp_inventory_registration_layout_pages_v1.py"
SPEC = importlib.util.spec_from_file_location("ltpp_layout_inventory", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def row(vertical, horizontal, status="DENSE_PRINTED_GRID"):
    return {"vertical_grid_matches": vertical, "horizontal_grid_matches": horizontal, "status": status}


def test_summary_identifies_date_without_any_vertical_grid_support():
    summary = MODULE.date_summary("x", [row(2, 6, "PARTIAL_PRINTED_GRID") for _ in range(10)])
    assert summary["conclusion"] == "NO_DATE_LEVEL_VERTICAL_GRID_SUPPORT"


def test_summary_identifies_consistent_layout_candidate():
    summary = MODULE.date_summary("x", [row(11, 6) for _ in range(10)])
    assert summary["conclusion"] == "CONSISTENT_PRINTED_LAYOUT_CANDIDATE"


def test_summary_identifies_partial_layout_candidate():
    pages = [row(11, 6)] * 4 + [row(5, 6, "PARTIAL_PRINTED_GRID")] * 6
    summary = MODULE.date_summary("x", pages)
    assert summary["conclusion"] == "PARTIAL_DATE_LAYOUT_CANDIDATE"
