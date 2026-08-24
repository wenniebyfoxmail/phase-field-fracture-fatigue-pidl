"""Fail-closed blind/seal/unblind contract for the RRaPINN G4 pilot.

This module only defines an offline evidence contract.  It does not calculate
G4 metrics and does not imply that producer or FEM evidence exists.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import tempfile
import math
from pathlib import Path
from typing import Iterable, Mapping, Sequence


SCHEMA = "rrapinn-g4-blind-seal/v1"
ARM_MAP_SCHEMA = ("opaque_arm", "treatment")
BLIND_METRICS_COLUMNS = (
    "opaque_arm",
    "endpoint",
    "cycle",
    "raw_step",
    "metric",
    "value",
    "unit",
    "status",
)
UNBLINDED_COLUMNS = ("opaque_arm", "treatment", *BLIND_METRICS_COLUMNS[1:])
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_OPAQUE_ARM_RE = re.compile(r"^arm_[0-9a-f]{8,64}$")
RESIDUAL_METRICS = (
    "mean", "p95", "p99", "cvar95", "cvar99", "worst_1pct_area_mass",
)
REQUIRED_METRIC_KEYS = frozenset(
    [("residual", str(cycle), metric) for cycle in (76, 82) for metric in RESIDUAL_METRICS]
    + [("field", "76", metric) for metric in ("active_log_mean", "active_log_cvar99")]
    + [("field", "82", metric) for metric in (
        "active_log_mean", "active_log_cvar99", "raw_log_cvar99",
        "absolute_support_iou", "absolute_support_area_ratio",
        "own_top1_support_iou", "active_correlation", "damage_mae",
        "history_log_mae", "fatigue_factor_mae",
        "damage_iou_025", "damage_iou_050", "damage_iou_075",
        "damage_components_025", "damage_crack_tip_x_025",
        "damage_centroid_x_025", "damage_centroid_y_025",
        "damage_forward_extent_025", "damage_width_025",
        "damage_one_sided_support_025", "mirror_asymmetry",
    )]
    + [("event", "headline", "first_detect_cycle")]
)
ALLOWED_STATUSES = {"measured", "pre_first_detect", "post_first_detect", "right_censored"}


class ContractError(ValueError):
    """Raised when an input fails the frozen G4 blind contract."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_regular_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise ContractError(f"{label} must be an existing regular file: {path}")


def _read_csv(path: Path, expected_columns: Sequence[str]) -> list[dict[str, str]]:
    _require_regular_file(path, "CSV")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(expected_columns):
            raise ContractError(
                f"CSV columns/order mismatch: expected {list(expected_columns)!r}, "
                f"got {reader.fieldnames!r}"
            )
        rows = list(reader)
    if not rows:
        raise ContractError("CSV must contain at least one data row")
    if any(None in row for row in rows):
        raise ContractError("CSV contains fields beyond the frozen column set")
    return rows


def _blind_arms(rows: Iterable[Mapping[str, str]]) -> tuple[str, str]:
    arms = sorted({row["opaque_arm"] for row in rows})
    if len(arms) != 2:
        raise ContractError(f"blind metrics must contain exactly two opaque arms; got {arms!r}")
    if any(not _OPAQUE_ARM_RE.fullmatch(arm) for arm in arms):
        raise ContractError(
            "opaque arms must match 'arm_' followed by 8-64 lowercase hex characters"
        )
    return arms[0], arms[1]


def _validate_metric_rows(rows: list[dict[str, str]], arms: tuple[str, str]) -> None:
    for arm in arms:
        arm_rows = [row for row in rows if row["opaque_arm"] == arm]
        keys = [(row["endpoint"], row["cycle"], row["metric"]) for row in arm_rows]
        if len(keys) != len(set(keys)) or set(keys) != REQUIRED_METRIC_KEYS:
            raise ContractError(f"blind metric endpoint/cycle/metric grid is incomplete for {arm}")
        event_rows = [row for row in arm_rows if row["endpoint"] == "event"]
        if len(event_rows) != 1:
            raise ContractError("each arm requires exactly one headline event row")
        event_raw_step = int(event_rows[0]["raw_step"])
        expected_c82_status = (
            "post_first_detect" if event_raw_step <= 409 else "pre_first_detect"
        )
        for row in arm_rows:
            try:
                value = float(row["value"])
                raw_step = int(row["raw_step"])
            except ValueError as exc:
                raise ContractError("blind metric value/raw_step must be numeric") from exc
            if not math.isfinite(value) or raw_step < 0 or not row["unit"]:
                raise ContractError("blind metric values must be finite with valid units/raw steps")
            if row["status"] not in ALLOWED_STATUSES:
                raise ContractError("blind metric status is outside the frozen vocabulary")
            expected_unit = {
                "residual": "scaled_residual",
                "field": "dimensionless",
                "event": "cycle",
            }[row["endpoint"]]
            if row["unit"] != expected_unit:
                raise ContractError("blind metric unit does not match the frozen endpoint unit")
            if row["cycle"] in {"76", "82"}:
                expected_step = 379 if row["cycle"] == "76" else 409
                if raw_step != expected_step:
                    raise ContractError("blind metric raw step does not match the frozen state")
            elif not (301 <= raw_step <= 460):
                raise ContractError("headline event raw step lies outside the G4 interval")
            if row["cycle"] == "76" and row["status"] != "pre_first_detect":
                raise ContractError("c76 metrics must be labelled pre_first_detect")
            if row["cycle"] == "82" and row["status"] != expected_c82_status:
                raise ContractError("c82 metrics do not match the arm first-detect receipt state")


def _canonical_json_bytes(payload: Mapping[str, object]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def _exclusive_install(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise FileExistsError(f"refusing concurrent overwrite: {path}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def build_seal(
    *,
    metrics_csv: Path,
    analysis_code: Path,
    fem_artifact: Path,
    projector_artifact: Path,
) -> dict[str, object]:
    rows = _read_csv(metrics_csv, BLIND_METRICS_COLUMNS)
    arms = _blind_arms(rows)
    _validate_metric_rows(rows, arms)
    artifacts = {
        "analysis_code": analysis_code,
        "fem_artifact": fem_artifact,
        "projector_artifact": projector_artifact,
    }
    for label, path in artifacts.items():
        _require_regular_file(path, label)
    return {
        "schema": SCHEMA,
        "blind_metrics_columns": list(BLIND_METRICS_COLUMNS),
        "blind_metrics_row_count": len(rows),
        "opaque_arms": list(arms),
        "sha256": {
            "blind_metrics_csv": sha256_file(metrics_csv),
            **{label: sha256_file(path) for label, path in artifacts.items()},
        },
    }


def seal_metrics(
    *,
    metrics_csv: Path,
    analysis_code: Path,
    fem_artifact: Path,
    projector_artifact: Path,
    output_seal: Path,
) -> str:
    payload = build_seal(
        metrics_csv=metrics_csv,
        analysis_code=analysis_code,
        fem_artifact=fem_artifact,
        projector_artifact=projector_artifact,
    )
    encoded = _canonical_json_bytes(payload)
    _exclusive_install(output_seal, encoded)
    return hashlib.sha256(encoded).hexdigest()


def verify_seal(
    *,
    seal_path: Path,
    expected_seal_sha256: str,
    metrics_csv: Path,
    analysis_code: Path,
    fem_artifact: Path,
    projector_artifact: Path,
) -> dict[str, object]:
    if not _SHA256_RE.fullmatch(expected_seal_sha256):
        raise ContractError("expected seal SHA256 must be 64 lowercase hex characters")
    _require_regular_file(seal_path, "seal")
    if sha256_file(seal_path) != expected_seal_sha256:
        raise ContractError("seal SHA256 does not match the independently supplied value")
    try:
        sealed = json.loads(seal_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContractError("seal is not valid UTF-8 JSON") from exc
    if not isinstance(sealed, dict) or sealed.get("schema") != SCHEMA:
        raise ContractError(f"seal schema must equal {SCHEMA!r}")
    current = build_seal(
        metrics_csv=metrics_csv,
        analysis_code=analysis_code,
        fem_artifact=fem_artifact,
        projector_artifact=projector_artifact,
    )
    if sealed != current:
        raise ContractError("seal content does not match current metrics/code/FEM/projector inputs")
    return sealed


def read_arm_map(path: Path) -> dict[str, str]:
    rows = _read_csv(path, ARM_MAP_SCHEMA)
    if len(rows) != 2:
        raise ContractError("arm map must contain exactly two rows")
    mapping: dict[str, str] = {}
    for row in rows:
        arm, treatment = row["opaque_arm"], row["treatment"]
        if arm in mapping:
            raise ContractError(f"duplicate opaque arm in arm map: {arm}")
        mapping[arm] = treatment
    if set(mapping.values()) != {"A", "B"}:
        raise ContractError("arm map treatments must be exactly A and B, once each")
    if any(not _OPAQUE_ARM_RE.fullmatch(arm) for arm in mapping):
        raise ContractError("arm map contains a non-opaque arm identifier")
    return mapping


def unblind_metrics(
    *,
    seal_path: Path,
    expected_seal_sha256: str,
    metrics_csv: Path,
    analysis_code: Path,
    fem_artifact: Path,
    projector_artifact: Path,
    arm_map_csv: Path,
    output_csv: Path,
) -> None:
    sealed = verify_seal(
        seal_path=seal_path,
        expected_seal_sha256=expected_seal_sha256,
        metrics_csv=metrics_csv,
        analysis_code=analysis_code,
        fem_artifact=fem_artifact,
        projector_artifact=projector_artifact,
    )
    mapping = read_arm_map(arm_map_csv)
    sealed_arms = set(sealed["opaque_arms"])
    if set(mapping) != sealed_arms:
        raise ContractError("arm map opaque-arm set does not exactly match the sealed arms")
    rows = _read_csv(metrics_csv, BLIND_METRICS_COLUMNS)

    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=UNBLINDED_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "opaque_arm": row["opaque_arm"],
                "treatment": mapping[row["opaque_arm"]],
                **{column: row[column] for column in BLIND_METRICS_COLUMNS[1:]},
            }
        )
    _exclusive_install(output_csv, buffer.getvalue().encode("utf-8"))
