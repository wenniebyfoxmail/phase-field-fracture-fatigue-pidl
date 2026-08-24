import csv
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))

from rrapinn_g4_blind_contract import (  # noqa: E402
    BLIND_METRICS_COLUMNS,
    ContractError,
    REQUIRED_METRIC_KEYS,
    seal_metrics,
    unblind_metrics,
)


ARMS = ("arm_0123abcd", "arm_fedcba98")


def _write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _fixture(tmp_path: Path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    metrics = tmp_path / "blind.csv"
    rows = []
    for arm, value in zip(ARMS, ("1.0", "0.8")):
        for endpoint, cycle, metric in sorted(REQUIRED_METRIC_KEYS):
            rows.append({
                "opaque_arm": arm,
                "endpoint": endpoint,
                "cycle": cycle,
                "raw_step": "379" if cycle == "76" else (
                    "409" if cycle == "82" else "444"
                ),
                "metric": metric,
                "value": value,
                "unit": (
                    "cycle" if endpoint == "event" else (
                        "scaled_residual" if endpoint == "residual" else "dimensionless"
                    )
                ),
                "status": (
                    "pre_first_detect" if cycle in {"76", "82"} else "measured"
                ),
            })
    _write_csv(metrics, BLIND_METRICS_COLUMNS, rows)
    artifacts = {}
    for name in ("prelaunch_lock", "fem_artifact", "projector_artifact"):
        path = tmp_path / f"{name}.bin"
        path.write_bytes(name.encode("ascii"))
        artifacts[name] = path
    arm_manifests = []
    for arm in ARMS:
        root = tmp_path / arm
        root.mkdir()
        states = {}
        for cycle, step in ((76, 379), (82, 409)):
            records = {}
            for field in ("residual_fields", "element_fields"):
                path = root / f"{field}_{cycle}.npz"
                path.write_bytes(f"{arm}:{field}:{cycle}".encode())
                records[field] = {
                    "path": path.name,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            states[str(cycle)] = {"cycle": cycle, "raw_step": step, **records}
        receipt = root / "event.json"
        receipt.write_text("{}\n", encoding="utf-8")
        manifest = root / "analysis.json"
        manifest.write_text(json.dumps({
            "schema": "rrapinn-g4-blind-analysis-input-v1",
            "opaque_arm": arm, "development_case": "U0.12", "states": states,
            "event": {
                "kind": "first_detect",
                "receipt": {
                    "path": receipt.name,
                    "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
                },
            },
        }), encoding="utf-8")
        arm_manifests.append(manifest)
    artifacts["arm_manifests"] = arm_manifests
    seal = tmp_path / "seal.json"
    seal_hash = seal_metrics(metrics_csv=metrics, output_seal=seal, **artifacts)
    arm_map = tmp_path / "arm_map.csv"
    _write_csv(
        arm_map,
        ("opaque_arm", "treatment"),
        [
            {"opaque_arm": ARMS[0], "treatment": "B"},
            {"opaque_arm": ARMS[1], "treatment": "A"},
        ],
    )
    return metrics, artifacts, seal, seal_hash, arm_map


def test_seal_then_verify_before_unblind(tmp_path):
    metrics, artifacts, seal, seal_hash, arm_map = _fixture(tmp_path)
    output = tmp_path / "unblinded.csv"
    unblind_metrics(
        seal_path=seal,
        expected_seal_sha256=seal_hash,
        metrics_csv=metrics,
        arm_map_csv=arm_map,
        output_csv=output,
        **artifacts,
    )
    with output.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert {row["treatment"] for row in rows} == {"A", "B"}
    assert all(
        row["treatment"] == ("B" if row["opaque_arm"] == ARMS[0] else "A")
        for row in rows
    )


def test_fixed_metrics_column_order_is_enforced(tmp_path):
    metrics, artifacts, _, _, _ = _fixture(tmp_path)
    text = metrics.read_text(encoding="utf-8")
    metrics.write_text(text.replace("opaque_arm,endpoint", "endpoint,opaque_arm"), encoding="utf-8")
    with pytest.raises(ContractError, match="columns/order"):
        seal_metrics(metrics_csv=metrics, output_seal=tmp_path / "bad.json", **artifacts)


def test_incomplete_or_nonfinite_metric_grid_is_rejected(tmp_path):
    metrics, artifacts, _, _, _ = _fixture(tmp_path)
    lines = metrics.read_text(encoding="utf-8").splitlines()
    metrics.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    with pytest.raises(ContractError, match="grid is incomplete"):
        seal_metrics(metrics_csv=metrics, output_seal=tmp_path / "bad-grid.json", **artifacts)

    metrics, artifacts, _, _, _ = _fixture(tmp_path / "second")
    text = metrics.read_text(encoding="utf-8").replace(",1.0,", ",nan,", 1)
    metrics.write_text(text, encoding="utf-8")
    with pytest.raises(ContractError, match="finite"):
        seal_metrics(metrics_csv=metrics, output_seal=tmp_path / "bad-finite.json", **artifacts)


def test_wrong_raw_step_unit_or_mixed_c82_state_is_rejected(tmp_path):
    for index, replacement, match in (
        (1, lambda row: row.update(raw_step="0"), "raw step"),
        (2, lambda row: row.update(unit="wrong"), "unit"),
        (3, lambda row: row.update(status="post_first_detect"), "first-detect"),
    ):
        case = tmp_path / f"case-{index}"
        metrics, artifacts, _, _, _ = _fixture(case)
        with metrics.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        target = next(row for row in rows if row["cycle"] == ("76" if index < 3 else "82"))
        replacement(target)
        _write_csv(metrics, BLIND_METRICS_COLUMNS, rows)
        with pytest.raises(ContractError, match=match):
            seal_metrics(metrics_csv=metrics, output_seal=case / "bad.json", **artifacts)


@pytest.mark.parametrize(
    "rows",
    [
        [{"opaque_arm": ARMS[0], "treatment": "A"}],
        [
            {"opaque_arm": ARMS[0], "treatment": "A"},
            {"opaque_arm": ARMS[1], "treatment": "A"},
        ],
        [
            {"opaque_arm": ARMS[0], "treatment": "A"},
            {"opaque_arm": "arm_aaaaaaaa", "treatment": "B"},
        ],
    ],
)
def test_unblind_rejects_non_bijective_or_mismatched_arm_map(tmp_path, rows):
    metrics, artifacts, seal, seal_hash, arm_map = _fixture(tmp_path)
    _write_csv(arm_map, ("opaque_arm", "treatment"), rows)
    with pytest.raises(ContractError):
        unblind_metrics(
            seal_path=seal,
            expected_seal_sha256=seal_hash,
            metrics_csv=metrics,
            arm_map_csv=arm_map,
            output_csv=tmp_path / "out.csv",
            **artifacts,
        )


def test_unblind_rejects_tampered_metrics_before_reading_map(tmp_path):
    metrics, artifacts, seal, seal_hash, arm_map = _fixture(tmp_path)
    metrics.write_text(metrics.read_text().replace("1.0", "9.0"), encoding="utf-8")
    arm_map.unlink()
    with pytest.raises(ContractError, match="seal content"):
        unblind_metrics(
            seal_path=seal,
            expected_seal_sha256=seal_hash,
            metrics_csv=metrics,
            arm_map_csv=arm_map,
            output_csv=tmp_path / "out.csv",
            **artifacts,
        )


def test_seal_binds_every_manifest_referenced_input(tmp_path):
    metrics, artifacts, seal, seal_hash, arm_map = _fixture(tmp_path)
    manifest = artifacts["arm_manifests"][0]
    payload = json.loads(manifest.read_text())
    residual = manifest.parent / payload["states"]["76"]["residual_fields"]["path"]
    residual.write_bytes(b"tampered")
    with pytest.raises(ContractError, match="analysis input artifact hash"):
        unblind_metrics(
            seal_path=seal, expected_seal_sha256=seal_hash,
            metrics_csv=metrics, arm_map_csv=arm_map,
            output_csv=tmp_path / "out.csv", **artifacts,
        )


def test_seal_rejects_metrics_manifest_arm_mismatch(tmp_path):
    metrics, artifacts, _, _, _ = _fixture(tmp_path)
    manifest = artifacts["arm_manifests"][0]
    payload = json.loads(manifest.read_text())
    payload["opaque_arm"] = "arm_aaaaaaaa"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ContractError, match="opaque-arm sets do not match"):
        seal_metrics(
            metrics_csv=metrics, output_seal=tmp_path / "mismatch.json", **artifacts,
        )


def test_unblind_rejects_wrong_external_seal_hash(tmp_path):
    metrics, artifacts, seal, _, arm_map = _fixture(tmp_path)
    wrong = hashlib.sha256(b"different seal").hexdigest()
    with pytest.raises(ContractError, match="independently supplied"):
        unblind_metrics(
            seal_path=seal,
            expected_seal_sha256=wrong,
            metrics_csv=metrics,
            arm_map_csv=arm_map,
            output_csv=tmp_path / "out.csv",
            **artifacts,
        )


def test_outputs_are_exclusive_create(tmp_path):
    metrics, artifacts, seal, seal_hash, arm_map = _fixture(tmp_path)
    with pytest.raises(FileExistsError):
        seal_metrics(metrics_csv=metrics, output_seal=seal, **artifacts)
    output = tmp_path / "out.csv"
    output.write_text("owned\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        unblind_metrics(
            seal_path=seal,
            expected_seal_sha256=seal_hash,
            metrics_csv=metrics,
            arm_map_csv=arm_map,
            output_csv=output,
            **artifacts,
        )
