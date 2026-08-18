"""Boundary-only first-detect observations and immutable receipts."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


SCHEMA = "boundary-first-detect-v1"


def map_raw_step(raw_step, *, displacements, step_offset=1):
    displacements = [float(value) for value in displacements]
    if not displacements or int(raw_step) < int(step_offset):
        raise ValueError("raw step is outside the explicit physical-cycle schedule")
    adjusted = int(raw_step) - int(step_offset)
    substep = adjusted % len(displacements)
    return {
        "physical_cycle": adjusted // len(displacements) + 1,
        "substep_index": substep,
        "substep_displacement": displacements[substep],
    }


def observe_boundary(
    raw_step, damage, coordinates, *, displacements, step_offset=1,
    x_min=0.48, threshold=0.95, minimum_nodes=3,
):
    damage = np.asarray(damage, dtype=np.float64).reshape(-1)
    coordinates = np.asarray(coordinates, dtype=np.float64)
    if coordinates.ndim != 2 or coordinates.shape != (damage.size, 2):
        raise ValueError("coordinates and damage must be node-aligned")
    if not np.all(np.isfinite(damage)) or not np.all(np.isfinite(coordinates)):
        raise ValueError("boundary observation inputs must be finite")
    if int(minimum_nodes) <= 0:
        raise ValueError("minimum_nodes must be positive")
    boundary = coordinates[:, 0] > float(x_min)
    if not np.any(boundary):
        raise ValueError("right-boundary observation population is empty")
    boundary_damage = damage[boundary]
    qualifying = int(np.sum(boundary_damage > float(threshold)))
    mapped = map_raw_step(
        raw_step, displacements=displacements, step_offset=step_offset
    )
    return {
        "schema": SCHEMA,
        "raw_step": int(raw_step),
        **mapped,
        "qualifying_nodes": qualifying,
        "boundary_nodes": int(boundary.sum()),
        "boundary_max_damage": float(boundary_damage.max()),
        "x_min_exclusive": float(x_min),
        "damage_threshold_exclusive": float(threshold),
        "minimum_nodes": int(minimum_nodes),
        "triggered": qualifying >= int(minimum_nodes),
        "criterion": "right_boundary_nodes_gt_damage_threshold",
        "trigger_source": "boundary_only",
    }


def record_boundary_observation(trace_path, receipt_path, observation):
    """Append every observation and create the first receipt exactly once."""
    trace_path = Path(trace_path)
    receipt_path = Path(receipt_path)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(observation, sort_keys=True) + "\n")
    if not observation.get("triggered", False):
        return None
    receipt = dict(observation)
    receipt.pop("triggered", None)
    if receipt_path.exists():
        existing = json.loads(receipt_path.read_text(encoding="utf-8"))
        if existing.get("schema") != SCHEMA:
            raise RuntimeError("existing first-detect receipt has an invalid schema")
        if int(existing["raw_step"]) > int(receipt["raw_step"]):
            raise RuntimeError("existing first-detect receipt is later than current trigger")
        return existing
    with receipt_path.open("x", encoding="utf-8") as handle:
        json.dump(receipt, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return receipt


def write_right_censor_receipt(path, *, physical_cycle, last_raw_step):
    """Create an immutable boundary-only right-censor receipt at the hard outer limit."""
    path = Path(path)
    payload = {
        "schema": "rrapinn-g4-right-censor-v1",
        "physical_cycle": int(physical_cycle),
        "last_raw_step": int(last_raw_step),
        "boundary_triggered": False,
        "trigger_source": "boundary_only",
    }
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return payload


def g4_archive_stop_decision(
    *, raw_step, hard_stop_raw_step, minimum_archive_raw_step,
    boundary_receipt_enabled, boundary_receipt_exists, fracture_confirmed,
):
    """Pure stop-state machine separating headline boundary evidence from fallback."""
    if hard_stop_raw_step is not None and int(raw_step) == int(hard_stop_raw_step):
        return "hard_stop_with_boundary" if boundary_receipt_exists else "right_censor"
    if (
        fracture_confirmed
        and int(raw_step) >= int(minimum_archive_raw_step)
        and (not boundary_receipt_enabled or boundary_receipt_exists)
    ):
        return "fracture_confirmed"
    return "continue"
