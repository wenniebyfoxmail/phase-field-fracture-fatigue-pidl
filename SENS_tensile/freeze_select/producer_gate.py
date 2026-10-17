from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd

from .schema import validate_frozen_snapshots


PRODUCER_REQUIRED_COLUMNS = (
    "actual_fatigue_increment",
    "nominal_fixed_physics_increment",
    "load_spectrum_id",
    "temperature_level",
    "moisture_level",
    "geometry_id",
    "precrack_id",
    "increment_state_timing",
)

MANIFEST_REQUIRED_KEYS = (
    "snapshot_sha256",
    "known_residual_sign",
    "code_commit",
    "dirty_status",
    "producer_machine",
    "runtime",
    "source_hashes",
    "temperature_parameter_mapping",
    "moisture_parameter_mapping",
    "load_spectrum_semantics",
    "right_censored_trajectories",
    "splits",
    "factorial_design",
)


@dataclass(frozen=True)
class ProducerGateReport:
    passed: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    metrics: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_snapshot(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError("snapshot must be CSV or Parquet")


def _mapping_is_physical(mapping: object, levels: set[str]) -> bool:
    if not isinstance(mapping, dict) or set(map(str, mapping)) != levels:
        return False
    encoded = [json.dumps(mapping[key], sort_keys=True) for key in mapping]
    return len(set(encoded)) == len(levels)


def validate_producer_frame(
    frame: pd.DataFrame,
    manifest: dict[str, object],
    *,
    actual_snapshot_sha256: str | None = None,
) -> ProducerGateReport:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        validate_frozen_snapshots(frame, claim_class="tooling-only")
    except Exception as exc:
        errors.append(f"base_schema: {exc}")
    missing_columns = [name for name in PRODUCER_REQUIRED_COLUMNS if name not in frame]
    if missing_columns:
        errors.append(f"missing_producer_columns: {missing_columns}")
    missing_manifest = [name for name in MANIFEST_REQUIRED_KEYS if name not in manifest]
    if missing_manifest:
        errors.append(f"missing_manifest_keys: {missing_manifest}")
    if errors:
        return ProducerGateReport(False, tuple(errors), tuple(warnings), {})

    trajectory_ids = set(frame["trajectory_id"].astype(str))
    physics_families = set(frame["physics_family"].astype(str))
    load_levels = set(frame["load_spectrum_id"].astype(str))
    temperature_levels = set(frame["temperature_level"].astype(str))
    moisture_levels = set(frame["moisture_level"].astype(str))
    combinations = set(
        zip(
            frame["load_spectrum_id"].astype(str),
            frame["temperature_level"].astype(str),
            frame["moisture_level"].astype(str),
        )
    )
    factorial_design = manifest["factorial_design"]
    if not isinstance(factorial_design, dict) or not {
        "load_spectrum_ids", "temperature_levels", "moisture_levels"
    } <= set(factorial_design):
        errors.append(
            "factorial_design: load_spectrum_ids, temperature_levels, and moisture_levels are required"
        )
        expected_load_levels = load_levels
        expected_temperature_levels = temperature_levels
        expected_moisture_levels = moisture_levels
    else:
        expected_load_levels = set(map(str, factorial_design["load_spectrum_ids"]))
        expected_temperature_levels = set(map(str, factorial_design["temperature_levels"]))
        expected_moisture_levels = set(map(str, factorial_design["moisture_levels"]))
    expected_combinations = {
        (load, temperature, moisture)
        for load in expected_load_levels
        for temperature in expected_temperature_levels
        for moisture in expected_moisture_levels
    }
    expected_trajectory_count = len(expected_combinations)
    if len(trajectory_ids) < expected_trajectory_count:
        errors.append(
            "trajectory_count: expected at least "
            f"{expected_trajectory_count}, got {len(trajectory_ids)}"
        )
    if len(physics_families) != 1:
        errors.append(f"physics_family_count: expected 1, got {len(physics_families)}")
    if load_levels != expected_load_levels:
        errors.append("factor_levels: exported load levels do not match factorial_design")
    if temperature_levels != expected_temperature_levels:
        errors.append("factor_levels: exported temperature levels do not match factorial_design")
    if moisture_levels != expected_moisture_levels:
        errors.append("factor_levels: exported moisture levels do not match factorial_design")
    missing_combinations = expected_combinations - combinations
    extra_combinations = combinations - expected_combinations
    if missing_combinations or extra_combinations:
        errors.append(
            "factorial_coverage: expected declared Cartesian product; "
            f"missing={sorted(missing_combinations)}, extra={sorted(extra_combinations)}"
        )
    for column in ("load_spectrum_id", "temperature_level", "moisture_level"):
        varying = frame.groupby("trajectory_id")[column].nunique()
        if int(varying.max()) != 1:
            errors.append(f"trajectory_factor_not_constant: {column}")
    if frame["geometry_id"].astype(str).nunique() != 1:
        errors.append("geometry_id: producer selector gate requires one fixed geometry")
    if frame["precrack_id"].astype(str).nunique() != 1:
        errors.append("precrack_id: producer selector gate requires one fixed precrack")
    if frame["increment_state_timing"].astype(str).nunique() != 1:
        errors.append("increment_state_timing: must be one explicit timing convention")

    sign = str(manifest["known_residual_sign"])
    actual = frame["actual_fatigue_increment"].to_numpy(float)
    nominal = frame["nominal_fixed_physics_increment"].to_numpy(float)
    residual = frame["known_residual"].to_numpy(float)
    if sign == "actual_minus_nominal":
        expected = actual - nominal
    elif sign == "nominal_minus_actual":
        expected = nominal - actual
    else:
        expected = np.full_like(residual, np.nan)
        errors.append("known_residual_sign: use actual_minus_nominal or nominal_minus_actual")
    residual_max_error = float(np.nanmax(np.abs(residual - expected)))
    residual_scale = max(float(np.nanmax(np.abs(expected))), 1.0)
    if not np.isfinite(residual_max_error) or residual_max_error > 1e-8 + 1e-6 * residual_scale:
        errors.append(f"known_residual_identity: max error {residual_max_error:.6g}")

    if not _mapping_is_physical(
        manifest["temperature_parameter_mapping"], temperature_levels
    ):
        errors.append("temperature_parameter_mapping: levels missing or parameter mappings identical")
    if not _mapping_is_physical(
        manifest["moisture_parameter_mapping"], moisture_levels
    ):
        errors.append("moisture_parameter_mapping: levels missing or parameter mappings identical")
    load_semantics = manifest["load_spectrum_semantics"]
    if not isinstance(load_semantics, dict) or set(map(str, load_semantics)) != load_levels:
        errors.append("load_spectrum_semantics: must describe every declared load spectrum")
    elif not all(
        isinstance(value, dict) and value.get("is_physical") is True
        for value in load_semantics.values()
    ):
        errors.append("load_spectrum_semantics: every spectrum must declare is_physical=true")

    right_censored = set(map(str, manifest["right_censored_trajectories"]))
    if not right_censored:
        errors.append("right_censored_trajectories: at least one is required")
    elif not right_censored <= trajectory_ids:
        errors.append("right_censored_trajectories: contains unknown trajectory ids")

    splits = manifest["splits"]
    if not isinstance(splits, dict) or not {"train", "validation", "holdout"} <= set(splits):
        errors.append("splits: train, validation, and holdout ids are required")
    else:
        split_sets = {name: set(map(str, splits[name])) for name in ("train", "validation", "holdout")}
        if any(not values for values in split_sets.values()):
            errors.append("splits: every split must be nonempty")
        if (
            split_sets["train"] & split_sets["validation"]
            or split_sets["train"] & split_sets["holdout"]
            or split_sets["validation"] & split_sets["holdout"]
        ):
            errors.append("splits: trajectory ids overlap")
        if set().union(*split_sets.values()) != trajectory_ids:
            errors.append("splits: union must equal exported trajectory ids")

    declared_hash = str(manifest["snapshot_sha256"])
    if actual_snapshot_sha256 is not None and declared_hash != actual_snapshot_sha256:
        errors.append("snapshot_sha256: manifest does not match snapshot bytes")
    source_hashes = manifest["source_hashes"]
    if not isinstance(source_hashes, dict) or not source_hashes:
        errors.append("source_hashes: nonempty mapping required")
    if str(manifest["dirty_status"]).lower() not in {"clean", "dirty"}:
        errors.append("dirty_status: must be clean or dirty")

    metrics = {
        "trajectory_count": len(trajectory_ids),
        "physics_family_count": len(physics_families),
        "load_level_count": len(load_levels),
        "temperature_level_count": len(temperature_levels),
        "moisture_level_count": len(moisture_levels),
        "factorial_combination_count": len(combinations),
        "expected_factorial_combination_count": expected_trajectory_count,
        "snapshot_count": int(frame["snapshot_id"].astype(str).nunique()),
        "row_count": int(len(frame)),
        "known_residual_max_identity_error": residual_max_error,
    }
    return ProducerGateReport(not errors, tuple(errors), tuple(warnings), metrics)


def run_producer_gate(snapshot: Path, manifest_path: Path, output_dir: Path) -> ProducerGateReport:
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = read_snapshot(snapshot)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    report = validate_producer_frame(
        frame, manifest, actual_snapshot_sha256=sha256_file(snapshot)
    )
    (output_dir / "producer_gate_report.json").write_text(
        json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "decision.md").write_text(
        "# Freeze-Then-Select producer gate\n\n"
        f"- Decision: **{'PASS' if report.passed else 'FAIL'}**\n"
        f"- Errors: `{len(report.errors)}`\n"
        "- Boundary: a pass qualifies an input package; it does not validate mechanism selection or prediction.\n",
        encoding="utf-8",
    )
    return report
