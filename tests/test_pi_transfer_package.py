import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs" / "pi_transfer_controls_20260729"


def _csv_rows(name: str):
    with (PACKAGE / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_control_summary_and_claim_boundary():
    summary = json.loads((PACKAGE / "control_summary.json").read_text())
    assert summary["f1a_scaling_io_pass"] is True
    assert summary["f1a_field_roundtrip_max_abs"] <= 1e-12
    assert summary["f1b_solver_invariance_pass"] is False
    assert summary["f1b_status"].startswith("blocked")
    assert summary["f2_scalar_pi_pass"] is True
    assert summary["f2_boundary_condition_status"] == "mismatched"
    assert summary["road_validation"] is False
    assert summary["cycle_to_traffic_mapping"] is False


def test_pi_and_unobservable_field_gates():
    pi_rows = _csv_rows("pi_transfer_audit.csv")
    assert all(row["status"] == "matched" for row in pi_rows if row["control"] == "F1_exact_pi")
    f2 = [row for row in pi_rows if row["control"] == "F2_bc_negative"]
    assert all(
        row["status"] == "matched"
        for row in f2
        if row["category"] in {"buckingham_pi", "geometry_load_ratio"}
    )
    assert next(row for row in f2 if row["group"] == "boundary_condition")["status"] == "mismatched"

    fields = _csv_rows("fem_centred_field_metrics.csv")
    missing = {
        row["field"]: row["status"]
        for row in fields
        if row["control"] == "F2_bc_negative" and row["field"] in {"raw", "active"}
    }
    assert missing == {"raw": "unobservable", "active": "unobservable"}


def test_manifest_hashes_and_protected_scope():
    manifest = json.loads((PACKAGE / "RUN_MANIFEST.json").read_text())
    assert manifest["fresh_fem_solve"] is False
    assert manifest["protected_scope"] == {
        "forecast_files_modified": False,
        "inverse_files_modified": False,
    }
    for line in (PACKAGE / "HASHES.sha256").read_text().splitlines():
        expected, name = line.split("  ", 1)
        actual = hashlib.sha256((PACKAGE / name).read_bytes()).hexdigest()
        assert actual == expected
