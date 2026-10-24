#!/usr/bin/env python3
"""Read-only S04-E040 versus S04-E037-R001 trajectory comparison.

The two arms optimise different scalar objectives.  This tool never compares
them as if they had the same loss: it reports the common physical-energy
components and writes both objective definitions explicitly.  It pairs only a
continuous prefix of *accepted* candidate states, keyed by
``(step, cycle, substep, load)``.  A capped, rejected, missing, or phase-mismatched
candidate record is retained separately in ``terminal_trial.json`` and is never
used as a trajectory point.

Inputs are read only.  All generated files live below ``--output``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable

import numpy as np


LOAD_ABS_TOLERANCE = 1.0e-7
MESH_KEYS = ("xy", "triangles", "area")
NODE_FIELD_KEYS = ("d", "history_d")
ELEMENT_FIELD_KEYS = ("strain_xx", "strain_yy", "strain_xy", "raw_psi", "trial_A")
TRI3_GAUSS_BARYCENTRIC = np.asarray(
    ((2.0 / 3.0, 1.0 / 6.0, 1.0 / 6.0),
     (1.0 / 6.0, 2.0 / 3.0, 1.0 / 6.0),
     (1.0 / 6.0, 1.0 / 6.0, 2.0 / 3.0)),
    dtype=np.float64,
)


class InputContractError(RuntimeError):
    """The archived inputs cannot support the declared comparison."""


def _json_safe(value: Any) -> Any:
    """Convert numpy values recursively and reject non-finite JSON numbers."""
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def dump_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(_json_safe(value), indent=2, sort_keys=True, allow_nan=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], default_keys: Iterable[str] = ()) -> None:
    """Write a stable union of row keys, including an empty-schema CSV if needed."""
    keys = list(dict.fromkeys((*default_keys, *(key for row in rows for key in row))))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows([_json_safe(row) for row in rows])


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise InputContractError(f"Missing required input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputContractError(f"Invalid JSON in {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _existing_unique(paths: Iterable[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        path = path.resolve()
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def resolve_arm_dir(provided: Path, arm_name: str) -> Path:
    """Accept either an arm directory or its enclosing output/raw directory."""
    provided = provided.resolve()
    candidates = _existing_unique((provided, provided / arm_name))
    for candidate in candidates:
        if (candidate / "steps.json").is_file():
            return candidate
    rendered = ", ".join(str(item) for item in candidates)
    raise InputContractError(
        f"Could not find {arm_name!r} steps.json under supplied path; checked {rendered}"
    )


def resolve_mesh_path(provided: Path, arm_dir: Path) -> Path:
    """Find a shared mesh next to either a result root or its arm subdirectory."""
    candidates = _existing_unique(
        (
            provided / "mesh.npz",
            arm_dir / "mesh.npz",
            arm_dir.parent / "mesh.npz",
            provided.parent / "mesh.npz",
        )
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    rendered = ", ".join(str(item) for item in candidates)
    raise InputContractError(f"Could not locate mesh.npz; checked {rendered}")


def load_mesh(path: Path) -> dict[str, np.ndarray]:
    try:
        with np.load(path, allow_pickle=False) as archive:
            missing = [key for key in MESH_KEYS if key not in archive.files]
            if missing:
                raise InputContractError(f"{path} lacks required mesh keys: {missing}")
            mesh = {key: np.asarray(archive[key]) for key in (*MESH_KEYS, "node_weights") if key in archive.files}
    except OSError as exc:
        raise InputContractError(f"Cannot read mesh {path}: {exc}") from exc

    xy, triangles, area = mesh["xy"], mesh["triangles"], mesh["area"]
    if xy.ndim != 2 or xy.shape[1] != 2:
        raise InputContractError(f"{path}: xy must have shape (n_nodes, 2), got {xy.shape}")
    if triangles.ndim != 2 or triangles.shape[1] != 3:
        raise InputContractError(f"{path}: triangles must have shape (n_elements, 3), got {triangles.shape}")
    if area.shape != (len(triangles),):
        raise InputContractError(f"{path}: area shape {area.shape} does not match {len(triangles)} elements")
    if not np.issubdtype(triangles.dtype, np.integer):
        raise InputContractError(f"{path}: triangles must be integer indices, got {triangles.dtype}")
    if not np.isfinite(xy).all() or not np.isfinite(area).all():
        raise InputContractError(f"{path}: xy or area contains non-finite values")
    if np.any(area <= 0.0):
        raise InputContractError(f"{path}: element areas must be strictly positive")
    if triangles.size and (triangles.min() < 0 or triangles.max() >= len(xy)):
        raise InputContractError(f"{path}: triangles contain out-of-range node indices")
    if "node_weights" in mesh:
        weights = mesh["node_weights"]
        if weights.shape != (len(xy),):
            raise InputContractError(f"{path}: node_weights shape {weights.shape} does not match {len(xy)} nodes")
        if not np.isfinite(weights).all() or np.any(weights < 0.0) or float(weights.sum()) <= 0.0:
            raise InputContractError(f"{path}: node_weights must be finite, non-negative, and sum positive")
    return mesh


def strict_mesh_check(reference: dict[str, np.ndarray], candidate: dict[str, np.ndarray]) -> dict[str, Any]:
    """Reject any geometry/order mismatch before field values are paired."""
    report: dict[str, Any] = {}
    for key in MESH_KEYS:
        ref, new = reference[key], candidate[key]
        identical = np.array_equal(ref, new)
        report[f"{key}_bitwise_equal"] = bool(identical)
        if not identical:
            detail = f"shape {ref.shape} versus {new.shape}"
            if ref.shape == new.shape and np.issubdtype(ref.dtype, np.number) and np.issubdtype(new.dtype, np.number):
                detail += f", maximum absolute difference {float(np.max(np.abs(ref.astype(np.float64) - new.astype(np.float64)))):.17g}"
            raise InputContractError(f"Strict mesh mismatch for {key}: {detail}")
    if "node_weights" in reference and "node_weights" in candidate:
        report["node_weights_bitwise_equal"] = bool(
            np.array_equal(reference["node_weights"], candidate["node_weights"])
        )
    else:
        report["node_weights_bitwise_equal"] = None
    return report


def require_records(path: Path) -> list[dict[str, Any]]:
    raw = read_json(path / "steps.json")
    if not isinstance(raw, list) or not all(isinstance(item, dict) for item in raw):
        raise InputContractError(f"{path / 'steps.json'} must contain a JSON list of records")
    return list(raw)


def _required_float(record: dict[str, Any], key: str, context: str) -> float:
    if key not in record:
        raise InputContractError(f"{context}: missing {key!r}")
    try:
        value = float(record[key])
    except (TypeError, ValueError) as exc:
        raise InputContractError(f"{context}: {key!r} is not numeric") from exc
    if not math.isfinite(value):
        raise InputContractError(f"{context}: {key!r} is not finite")
    return value


def phase(record: dict[str, Any], context: str) -> tuple[int, int, int, float]:
    values: list[int] = []
    for key in ("step", "cycle", "substep"):
        if key not in record:
            raise InputContractError(f"{context}: missing {key!r}")
        try:
            value = int(record[key])
        except (TypeError, ValueError) as exc:
            raise InputContractError(f"{context}: {key!r} is not an integer") from exc
        if value < 1:
            raise InputContractError(f"{context}: {key!r} must be positive")
        values.append(value)
    return values[0], values[1], values[2], _required_float(record, "load", context)


def accepted(record: dict[str, Any], context: str) -> bool:
    if "accepted" not in record or not isinstance(record["accepted"], bool):
        raise InputContractError(f"{context}: accepted must be a JSON boolean")
    return record["accepted"]


def ordered_records(records: list[dict[str, Any]], label: str) -> list[dict[str, Any]]:
    seen_steps: set[int] = set()
    checked: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        context = f"{label} record #{index}"
        step, _, _, _ = phase(record, context)
        accepted(record, context)
        if step in seen_steps:
            raise InputContractError(f"{label}: duplicate step number {step}")
        seen_steps.add(step)
        checked.append(record)
    return sorted(checked, key=lambda record: phase(record, label)[0])


def phase_dict(record: dict[str, Any], context: str) -> dict[str, Any]:
    step, cycle, substep, load = phase(record, context)
    return {"step": step, "cycle": cycle, "substep": substep, "load": load}


def same_phase(reference: dict[str, Any], candidate: dict[str, Any], load_tolerance: float) -> bool:
    ref = phase(reference, "reference record")
    new = phase(candidate, "candidate record")
    return ref[:3] == new[:3] and abs(ref[3] - new[3]) <= load_tolerance


def step_dir(arm_dir: Path, record: dict[str, Any], label: str) -> Path:
    step, _, _, _ = phase(record, label)
    return arm_dir / f"step_{step:03d}"


def receipt_for(arm_dir: Path, record: dict[str, Any], label: str, load_tolerance: float) -> dict[str, Any]:
    """Use the per-step receipt when present and reject a conflicting one."""
    receipt_path = step_dir(arm_dir, record, label) / "receipt.json"
    if not receipt_path.exists():
        return record
    receipt = read_json(receipt_path)
    if not isinstance(receipt, dict):
        raise InputContractError(f"{receipt_path} must contain one JSON object")
    if not same_phase(record, receipt, load_tolerance):
        raise InputContractError(f"{receipt_path} phase does not match steps.json")
    if accepted(record, label) != accepted(receipt, str(receipt_path)):
        raise InputContractError(f"{receipt_path} accepted flag does not match steps.json")
    return receipt


def load_fields(
    arm_dir: Path,
    record: dict[str, Any],
    mesh: dict[str, np.ndarray],
    label: str,
) -> dict[str, np.ndarray]:
    path = step_dir(arm_dir, record, label) / "fields.npz"
    try:
        with np.load(path, allow_pickle=False) as archive:
            required = NODE_FIELD_KEYS + ELEMENT_FIELD_KEYS
            missing = [key for key in required if key not in archive.files]
            if missing:
                raise InputContractError(f"{path}: missing required field keys {missing}")
            optional = {"q_raw", "q_ref"}
            fields = {
                key: np.asarray(archive[key], dtype=np.float64)
                for key in set(required).union(optional).intersection(archive.files)
            }
    except FileNotFoundError as exc:
        raise InputContractError(f"Missing paired final field file: {path}") from exc
    except OSError as exc:
        raise InputContractError(f"Cannot read field file {path}: {exc}") from exc

    n_nodes, n_elements = len(mesh["xy"]), len(mesh["triangles"])
    for key in NODE_FIELD_KEYS:
        if fields[key].shape != (n_nodes,):
            raise InputContractError(f"{path}: {key} shape {fields[key].shape} does not match {n_nodes} nodes")
    for key in ELEMENT_FIELD_KEYS:
        if fields[key].shape != (n_elements,):
            raise InputContractError(f"{path}: {key} shape {fields[key].shape} does not match {n_elements} elements")
    for key in (*NODE_FIELD_KEYS, *ELEMENT_FIELD_KEYS):
        if not np.isfinite(fields[key]).all():
            raise InputContractError(f"{path}: {key} has non-finite values")
    return fields


def optional_metric(metrics: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        if key in metrics and metrics[key] is not None:
            try:
                value = float(metrics[key])
            except (TypeError, ValueError) as exc:
                raise InputContractError(f"Metric {key!r} is not numeric") from exc
            if not math.isfinite(value):
                raise InputContractError(f"Metric {key!r} is not finite")
            return value
    return None


def energy_values(receipt: dict[str, Any], label: str, includes_irr: bool) -> dict[str, Any]:
    metrics = receipt.get("metrics")
    if not isinstance(metrics, dict):
        raise InputContractError(f"{label}: receipt has no metrics object")
    e_el = optional_metric(metrics, "E_el")
    e_d = optional_metric(metrics, "E_d")
    e_irr = optional_metric(metrics, "shadow_E_irr", "E_irr")
    l2 = optional_metric(metrics, "weighted_L2")
    if e_el is None or e_d is None or e_irr is None or l2 is None:
        raise InputContractError(
            f"{label}: metrics must contain E_el, E_d, shadow_E_irr (or E_irr), and weighted_L2"
        )
    e_noirr = e_el + e_d
    objective_input = e_noirr + e_irr if includes_irr else e_noirr
    if objective_input <= 0.0:
        raise InputContractError(f"{label}: objective log input must be positive, got {objective_input:.17g}")
    reported_noirr = optional_metric(metrics, "E_noirr")
    return {
        "E_el": e_el,
        "E_d": e_d,
        "shadow_E_irr": e_irr,
        "weighted_L2": l2,
        "E_noirr": e_noirr,
        "reported_E_noirr": reported_noirr,
        "reported_minus_recomputed_E_noirr": None if reported_noirr is None else reported_noirr - e_noirr,
        "E_irr_objective_included": includes_irr,
        "objective_log_input": objective_input,
        "objective_value": math.log10(objective_input) + l2,
    }


def weighted_field_metric(
    reference: np.ndarray,
    candidate: np.ndarray,
    weights: np.ndarray,
) -> dict[str, Any]:
    if reference.shape != candidate.shape or reference.shape != weights.shape:
        raise InputContractError(
            f"Field/support shape mismatch: ref={reference.shape}, candidate={candidate.shape}, weights={weights.shape}"
        )
    if not np.isfinite(reference).all() or not np.isfinite(candidate).all():
        raise InputContractError("Cannot compare non-finite final fields")
    weights = np.asarray(weights, dtype=np.float64)
    if not np.isfinite(weights).all() or np.any(weights < 0.0):
        raise InputContractError("Comparison weights must be finite and non-negative")
    weight_sum = float(weights.sum())
    if weight_sum <= 0.0:
        raise InputContractError("Comparison weights must sum positive")
    delta = candidate - reference
    ref_l2_sq = float(np.sum(weights * reference**2))
    candidate_l2_sq = float(np.sum(weights * candidate**2))
    delta_l2_sq = float(np.sum(weights * delta**2))
    reference_mean = float(np.sum(weights * reference) / weight_sum)
    candidate_mean = float(np.sum(weights * candidate) / weight_sum)
    return {
        "support_weight_sum": weight_sum,
        "reference_weighted_mean": reference_mean,
        "candidate_weighted_mean": candidate_mean,
        "candidate_minus_reference_weighted_mean": candidate_mean - reference_mean,
        "reference_weighted_l2": math.sqrt(ref_l2_sq),
        "candidate_weighted_l2": math.sqrt(candidate_l2_sq),
        "difference_weighted_rms": math.sqrt(delta_l2_sq / weight_sum),
        "difference_maxabs": float(np.max(np.abs(delta))),
        "relative_l2": None if ref_l2_sq == 0.0 else math.sqrt(delta_l2_sq / ref_l2_sq),
        "relative_l2_defined": bool(ref_l2_sq != 0.0),
        "mean_ratio": None if reference_mean == 0.0 else candidate_mean / reference_mean,
        "mean_ratio_defined": bool(reference_mean != 0.0),
        "reference_min": float(reference.min()),
        "reference_max": float(reference.max()),
        "candidate_min": float(candidate.min()),
        "candidate_max": float(candidate.max()),
    }


def field_rows(
    reference_record: dict[str, Any],
    candidate_record: dict[str, Any],
    reference_fields: dict[str, np.ndarray],
    candidate_fields: dict[str, np.ndarray],
    reference_mesh: dict[str, np.ndarray],
) -> list[dict[str, Any]]:
    common = phase_dict(candidate_record, "candidate record")
    element_weights = np.asarray(reference_mesh["area"], dtype=np.float64)
    if "node_weights" not in reference_mesh:
        raise InputContractError("Reference mesh must supply node_weights for the nodal-damage comparison")
    node_weights = np.asarray(reference_mesh["node_weights"], dtype=np.float64)
    if node_weights.shape != reference_fields["d"].shape:
        raise InputContractError("Reference mesh must supply node_weights matching damage nodes")
    quantities = (
        ("damage_d", "node", reference_fields["d"], candidate_fields["d"], node_weights),
        (
            "strain_norm",
            "element",
            np.sqrt(reference_fields["strain_xx"]**2 + reference_fields["strain_yy"]**2 + 2.0 * reference_fields["strain_xy"]**2),
            np.sqrt(candidate_fields["strain_xx"]**2 + candidate_fields["strain_yy"]**2 + 2.0 * candidate_fields["strain_xy"]**2),
            element_weights,
        ),
        ("raw_psi_plus", "element", reference_fields["raw_psi"], candidate_fields["raw_psi"], element_weights),
        ("fatigue_A_trial", "element", reference_fields["trial_A"], candidate_fields["trial_A"], element_weights),
    )
    rows: list[dict[str, Any]] = []
    for quantity, support, reference, candidate, weights in quantities:
        rows.append(
            {
                **common,
                "quantity": quantity,
                "support": support,
                **weighted_field_metric(reference, candidate, weights),
            }
        )
    return rows


def constraint_row(
    arm: str,
    record: dict[str, Any],
    fields: dict[str, np.ndarray],
    mesh: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Report direct nodal and TRI3 Gauss-point bounds from saved final fields."""
    d, h = fields["d"], fields["history_d"]
    delta = d - h
    tri = mesh["triangles"]
    tri_d = d[tri]
    tri_delta = delta[tri]
    gp_d = tri_d @ TRI3_GAUSS_BARYCENTRIC.T
    gp_delta = tri_delta @ TRI3_GAUSS_BARYCENTRIC.T
    row: dict[str, Any] = {
        "arm": arm,
        **phase_dict(record, f"{arm} record"),
        "node_min_d_minus_history_d": float(delta.min()),
        "node_max_d_minus_history_d": float(delta.max()),
        "node_min_d": float(d.min()),
        "node_max_d": float(d.max()),
        "node_lower_violation_count_exact": int(np.count_nonzero(delta < 0.0)),
        "node_upper_violation_count_exact": int(np.count_nonzero(d > 1.0)),
        "tri3_gp_min_d_minus_history_d": float(gp_delta.min()),
        "tri3_gp_max_d_minus_history_d": float(gp_delta.max()),
        "tri3_gp_min_d": float(gp_d.min()),
        "tri3_gp_max_d": float(gp_d.max()),
        "tri3_gp_lower_violation_count_exact": int(np.count_nonzero(gp_delta < 0.0)),
        "tri3_gp_upper_violation_count_exact": int(np.count_nonzero(gp_d > 1.0)),
    }
    if "q_raw" in fields and "q_ref" in fields:
        raw, reference = fields["q_raw"], fields["q_ref"]
        if raw.shape != d.shape or reference.shape != d.shape:
            raise InputContractError("q_raw and q_ref must match nodal damage shape")
        if not np.isfinite(raw).all() or not np.isfinite(reference).all():
            raise InputContractError("q_raw or q_ref contains non-finite values")
        increment = raw - reference
        row.update(
            {
                "q_minus_q_ref_min": float(increment.min()),
                "q_minus_q_ref_max": float(increment.max()),
                "q_le_q_ref_node_fraction": float(np.mean(increment <= 0.0)),
                "q_gt_q_ref_node_fraction": float(np.mean(increment > 0.0)),
            }
        )
    return row


def terminal_field_summary(arm_dir: Path, record: dict[str, Any], mesh: dict[str, np.ndarray], label: str) -> dict[str, Any]:
    """Summarise a non-paired terminal field if it was written, without comparing it."""
    path = step_dir(arm_dir, record, label) / "fields.npz"
    summary: dict[str, Any] = {"fields_path": str(path), "fields_available": path.is_file()}
    if not path.is_file():
        return summary
    try:
        with np.load(path, allow_pickle=False) as archive:
            for key in ("d", "history_d", "raw_psi", "trial_A"):
                if key in archive.files:
                    values = np.asarray(archive[key], dtype=np.float64)
                    summary[f"{key}_finite"] = bool(np.isfinite(values).all())
                    if values.size and np.isfinite(values).all():
                        summary[f"{key}_min"] = float(values.min())
                        summary[f"{key}_max"] = float(values.max())
            if "d" in archive.files and "history_d" in archive.files:
                d = np.asarray(archive["d"], dtype=np.float64)
                h = np.asarray(archive["history_d"], dtype=np.float64)
                if d.shape == h.shape and np.isfinite(d).all() and np.isfinite(h).all():
                    summary["d_minus_history_d_min"] = float((d - h).min())
    except (OSError, ValueError) as exc:
        summary["fields_read_error"] = str(exc)
    return summary


def continuous_prefix(
    reference_records: list[dict[str, Any]],
    candidate_records: list[dict[str, Any]],
    load_tolerance: float,
) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], dict[str, Any]]:
    """Return only the beginning of the candidate trajectory that is comparable."""
    if any(not accepted(record, "reference record") for record in reference_records):
        raise InputContractError("Reference arm contains an unaccepted record; it is not a completed control trajectory")

    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for index, reference in enumerate(reference_records):
        expected = phase_dict(reference, "reference record")
        if index >= len(candidate_records):
            return pairs, {
                "kind": "missing_candidate_record",
                "expected_reference_phase": expected,
                "candidate_record_index": index,
            }
        candidate = candidate_records[index]
        observed = phase_dict(candidate, "candidate record")
        if not same_phase(reference, candidate, load_tolerance):
            return pairs, {
                "kind": "phase_mismatch",
                "expected_reference_phase": expected,
                "candidate_phase": observed,
                "candidate_record_index": index,
                "candidate_record": candidate,
            }
        if not accepted(candidate, "candidate record"):
            return pairs, {
                "kind": "unaccepted_record",
                "expected_reference_phase": expected,
                "candidate_phase": observed,
                "candidate_record_index": index,
                "candidate_record": candidate,
            }
        pairs.append((reference, candidate))

    if len(candidate_records) > len(reference_records):
        extra = candidate_records[len(reference_records)]
        return pairs, {
            "kind": "extra_candidate_record_after_reference",
            "candidate_record_index": len(reference_records),
            "candidate_phase": phase_dict(extra, "candidate record"),
            "candidate_record": extra,
        }
    return pairs, {"kind": "none", "message": "Candidate accepted the full reference horizon."}


def _receipt_metric_row(
    reference_receipt: dict[str, Any],
    candidate_receipt: dict[str, Any],
    candidate_record: dict[str, Any],
) -> dict[str, Any]:
    ref = energy_values(reference_receipt, "reference receipt", includes_irr=True)
    new = energy_values(candidate_receipt, "candidate receipt", includes_irr=False)
    return {
        **phase_dict(candidate_record, "candidate record"),
        **{f"reference_{key}": value for key, value in ref.items()},
        **{f"candidate_{key}": value for key, value in new.items()},
        "candidate_minus_reference_E_noirr": new["E_noirr"] - ref["E_noirr"],
        "candidate_to_reference_E_noirr_ratio": new["E_noirr"] / ref["E_noirr"] if ref["E_noirr"] != 0.0 else None,
        "objective_definition_note": (
            "reference=log10(E_el+E_d+shadow_E_irr)+weighted_L2; "
            "candidate=log10(E_el+E_d)+weighted_L2"
        ),
    }


def _timing_row(reference_receipt: dict[str, Any], candidate_receipt: dict[str, Any], candidate_record: dict[str, Any]) -> dict[str, Any]:
    ref_seconds = _required_float(reference_receipt, "step_elapsed_seconds", "reference receipt")
    new_seconds = _required_float(candidate_receipt, "step_elapsed_seconds", "candidate receipt")
    ref_updates = _required_float(reference_receipt, "updates", "reference receipt")
    new_updates = _required_float(candidate_receipt, "updates", "candidate receipt")
    return {
        **phase_dict(candidate_record, "candidate record"),
        "reference_updates": int(ref_updates) if ref_updates.is_integer() else ref_updates,
        "candidate_updates": int(new_updates) if new_updates.is_integer() else new_updates,
        "reference_step_elapsed_seconds": ref_seconds,
        "candidate_step_elapsed_seconds": new_seconds,
        "candidate_minus_reference_seconds": new_seconds - ref_seconds,
        "candidate_to_reference_seconds_ratio": new_seconds / ref_seconds if ref_seconds != 0.0 else None,
    }


def analyze(reference_input: Path, candidate_input: Path, output: Path, load_tolerance: float) -> dict[str, Any]:
    if not math.isfinite(load_tolerance) or load_tolerance < 0.0:
        raise InputContractError("load tolerance must be a finite non-negative number")

    reference_arm = resolve_arm_dir(reference_input, "original")
    candidate_arm = resolve_arm_dir(candidate_input, "feasible_damage")
    reference_mesh_path = resolve_mesh_path(reference_input, reference_arm)
    candidate_mesh_path = resolve_mesh_path(candidate_input, candidate_arm)
    reference_mesh = load_mesh(reference_mesh_path)
    candidate_mesh = load_mesh(candidate_mesh_path)
    mesh_report = strict_mesh_check(reference_mesh, candidate_mesh)

    reference_records = ordered_records(require_records(reference_arm), "reference")
    candidate_records = ordered_records(require_records(candidate_arm), "candidate")
    pairs, terminal = continuous_prefix(reference_records, candidate_records, load_tolerance)

    output.mkdir(parents=True, exist_ok=True)
    dump_json(
        output / "input_provenance.json",
        {
            "reference_input": str(reference_input.resolve()),
            "candidate_input": str(candidate_input.resolve()),
            "reference_arm": str(reference_arm),
            "candidate_arm": str(candidate_arm),
            "reference_mesh": str(reference_mesh_path),
            "candidate_mesh": str(candidate_mesh_path),
            "reference_mesh_sha256": sha256_file(reference_mesh_path),
            "candidate_mesh_sha256": sha256_file(candidate_mesh_path),
            "strict_mesh_check": mesh_report,
            "load_absolute_tolerance": load_tolerance,
            "reference_reexecuted": False,
        },
    )

    field_output: list[dict[str, Any]] = []
    energy_output: list[dict[str, Any]] = []
    timing_output: list[dict[str, Any]] = []
    constraint_output: list[dict[str, Any]] = []
    for reference_record, candidate_record in pairs:
        reference_receipt = receipt_for(reference_arm, reference_record, "reference", load_tolerance)
        candidate_receipt = receipt_for(candidate_arm, candidate_record, "candidate", load_tolerance)
        reference_fields = load_fields(reference_arm, reference_record, reference_mesh, "reference")
        candidate_fields = load_fields(candidate_arm, candidate_record, candidate_mesh, "candidate")
        field_output.extend(field_rows(reference_record, candidate_record, reference_fields, candidate_fields, reference_mesh))
        energy_output.append(_receipt_metric_row(reference_receipt, candidate_receipt, candidate_record))
        timing_output.append(_timing_row(reference_receipt, candidate_receipt, candidate_record))
        constraint_output.extend(
            (
                constraint_row("reference", reference_record, reference_fields, reference_mesh),
                constraint_row("candidate", candidate_record, candidate_fields, candidate_mesh),
            )
        )

    terminal_output = dict(terminal)
    terminal_record = terminal.get("candidate_record")
    if isinstance(terminal_record, dict):
        terminal_output["receipt"] = receipt_for(candidate_arm, terminal_record, "candidate", load_tolerance)
        terminal_output["field_summary"] = terminal_field_summary(candidate_arm, terminal_record, candidate_mesh, "candidate")
        terminal_output["not_used_in_field_or_timing_comparison"] = True
    terminal_index = terminal.get("candidate_record_index")
    if isinstance(terminal_index, int):
        tail = candidate_records[terminal_index + 1 :]
        terminal_output["candidate_records_after_terminal_count"] = len(tail)
        terminal_output["candidate_phases_after_terminal"] = [
            phase_dict(record, "candidate trailing record") for record in tail
        ]
    terminal_output["common_accepted_prefix_steps"] = len(pairs)
    dump_json(output / "terminal_trial.json", terminal_output)

    write_csv(
        output / "paired_fields.csv",
        field_output,
        default_keys=("step", "cycle", "substep", "load", "quantity", "support", "relative_l2"),
    )
    write_csv(
        output / "paired_energies.csv",
        energy_output,
        default_keys=("step", "cycle", "substep", "load", "reference_E_noirr", "candidate_E_noirr"),
    )
    write_csv(
        output / "timing.csv",
        timing_output,
        default_keys=("step", "cycle", "substep", "load", "reference_step_elapsed_seconds", "candidate_step_elapsed_seconds"),
    )
    write_csv(
        output / "constraint_state.csv",
        constraint_output,
        default_keys=("arm", "step", "cycle", "substep", "load", "node_min_d_minus_history_d"),
    )

    reference_seconds = sum(float(row["reference_step_elapsed_seconds"]) for row in timing_output)
    candidate_seconds = sum(float(row["candidate_step_elapsed_seconds"]) for row in timing_output)
    timing_summary = {
        "comparison_scope": "continuous common accepted prefix only",
        "common_accepted_prefix_steps": len(pairs),
        "reference_seconds_common_prefix": reference_seconds,
        "candidate_seconds_common_prefix": candidate_seconds,
        "candidate_minus_reference_seconds_common_prefix": candidate_seconds - reference_seconds,
        "candidate_to_reference_seconds_ratio_common_prefix": (
            candidate_seconds / reference_seconds if reference_seconds != 0.0 else None
        ),
        "speed_claim_supported": bool(terminal["kind"] == "none" and len(pairs) == len(reference_records)),
    }
    dump_json(output / "timing_summary.json", timing_summary)

    summary = {
        "analysis_status": "complete",
        "comparison_scope": "continuous common accepted prefix only",
        "reference_records": len(reference_records),
        "candidate_records": len(candidate_records),
        "common_accepted_prefix_steps": len(pairs),
        "reference_horizon_completed_by_candidate": bool(
            terminal["kind"] == "none" and len(pairs) == len(reference_records)
        ),
        "terminal_kind": terminal["kind"],
        "objective_distinction": {
            "reference_E_irr_objective_included": True,
            "candidate_E_irr_objective_included": False,
            "reference_formula": "log10(E_el + E_d + shadow_E_irr) + weighted_L2",
            "candidate_formula": "log10(E_el + E_d) + weighted_L2",
        },
        "outputs": {
            "input_provenance": "input_provenance.json",
            "paired_fields": "paired_fields.csv",
            "paired_energies": "paired_energies.csv",
            "timing": "timing.csv",
            "timing_summary": "timing_summary.json",
            "constraint_state": "constraint_state.csv",
            "terminal_trial": "terminal_trial.json",
        },
        "timing": timing_summary,
    }
    dump_json(output / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reference",
        required=True,
        type=Path,
        help="R001 original arm directory, or raw_producer directory containing original/ and mesh.npz",
    )
    parser.add_argument(
        "--candidate",
        required=True,
        type=Path,
        help="E040 output directory containing feasible_damage/ and mesh.npz, or feasible_damage/ directly",
    )
    parser.add_argument("--output", required=True, type=Path, help="New analysis output directory")
    parser.add_argument(
        "--load-abs-tolerance",
        type=float,
        default=LOAD_ABS_TOLERANCE,
        help=f"absolute load tolerance for phase pairing (default: {LOAD_ABS_TOLERANCE:g})",
    )
    args = parser.parse_args()
    try:
        summary = analyze(args.reference, args.candidate, args.output, args.load_abs_tolerance)
    except InputContractError as exc:
        parser.error(str(exc))
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
