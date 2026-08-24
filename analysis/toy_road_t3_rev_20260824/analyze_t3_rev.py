"""Read-only T3/T3-rev reductions; this module never authorizes or starts work."""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analysis.toy_road_t3_mechanism_20260819.mechanism import (
    element_geometry, load_mesh, load_peak_fields, reduce_field,
)
from analysis.toy_road_t3_mechanism_20260819.run_analysis import FIELDS, _field_arrays


CASE_ID = "T3_loading_history"
REV_CASE_ID = "T3_rev_loading_order"
FIXED_CYCLES = (20, 30, 31, 40, 60, 61)


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def _tolerances(value: Mapping[str, float]) -> tuple[float, float]:
    if set(value) != {"max_abs", "relative_l2"}:
        raise ValueError("order-effect tolerances must contain exactly max_abs and relative_l2")
    maximum = _finite_number(value["max_abs"], "max_abs tolerance")
    relative = _finite_number(value["relative_l2"], "relative_l2 tolerance")
    if maximum < 0 or relative < 0:
        raise ValueError("order-effect tolerances must be nonnegative")
    return maximum, relative


def classify_order_effect(rows: Sequence[Mapping[str, float]], tolerances: Mapping[str, float]) -> str:
    """Classify only complete consecutive c60+ evidence, with inclusive tolerances."""
    max_tol, relative_tol = _tolerances(tolerances)
    by_cycle: dict[int, tuple[float, float]] = {}
    for row in rows:
        cycle_value = row.get("cycle")
        if isinstance(cycle_value, bool) or not isinstance(cycle_value, (int, float)) or int(cycle_value) != cycle_value:
            raise ValueError("order-effect cycle must be an exact integer")
        cycle = int(cycle_value)
        if cycle < 60 or cycle in by_cycle:
            raise ValueError("order-effect rows must be unique c60-or-later cycles")
        by_cycle[cycle] = (_finite_number(row.get("max_abs"), "max_abs"),
                           _finite_number(row.get("relative_l2"), "relative_l2"))
    if not by_cycle or 60 not in by_cycle:
        return "UNAVAILABLE"
    cycles = sorted(by_cycle)
    if cycles != list(range(60, cycles[-1] + 1)) or len(cycles) < 2:
        return "UNAVAILABLE"
    significant = {
        cycle: maximum > max_tol or relative > relative_tol
        for cycle, (maximum, relative) in by_cycle.items()
    }
    if not any(significant.values()):
        return "ORDER_EFFECT_NOT_RESOLVED_WITHIN_TOLERANCE"
    if significant[60] and not any(significant[cycle] for cycle in cycles[1:]):
        return "TRANSIENT_ORDER_EFFECT_TERMINAL_TRAJECTORY_INSENSITIVE"
    return "PERSISTENT_LOADING_ORDER_DEPENDENCE_OBSERVED"


def _strict_json(path: Path) -> dict[str, object]:
    def reject_duplicate(pairs: list[tuple[str, object]]) -> dict[str, object]:
        output: dict[str, object] = {}
        for key, value in pairs:
            if key in output:
                raise ValueError(f"duplicate JSON key: {key}")
            output[key] = value
        return output
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate,
                       parse_constant=lambda token: (_ for _ in ()).throw(ValueError(f"non-finite JSON: {token}")))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _terminal_cycle(root: Path) -> int | None:
    path = root / "TERMINAL_RESULT.json"
    if not path.is_file():
        return None
    terminal = _strict_json(path)
    cycle = terminal.get("terminal_cycle")
    if isinstance(cycle, bool) or not isinstance(cycle, int) or cycle < 1:
        raise ValueError(f"terminal cycle is invalid: {root}")
    return cycle


def _load_cycle(root: Path, cycle: int, mesh: Any) -> dict[str, np.ndarray] | None:
    path = root / "substeps" / f"cycle_{cycle:04d}.mat"
    if not path.is_file():
        return None
    return _field_arrays(load_peak_fields(path, cycle), mesh)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    columns = list(rows[0]) if rows else ["comparison", "cycle", "availability"]
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def analyze_t3_rev(
        t3_root: Path, t3_rev_root: Path, destination: Path,
        tolerances: Mapping[str, float] | None = None) -> dict[str, object]:
    """Reduce only declared comparison cycles, retaining unavailable evidence explicitly."""
    t3_root, t3_rev_root, destination = Path(t3_root), Path(t3_rev_root), Path(destination)
    if destination.exists():
        raise FileExistsError(f"analysis destination already exists: {destination}")
    if tolerances is None:
        tolerances = {"max_abs": 1e-12, "relative_l2": 1e-12}
    max_tol, relative_tol = _tolerances(tolerances)
    t3_terminal, rev_terminal = _terminal_cycle(t3_root), _terminal_cycle(t3_rev_root)
    common_terminal = min(t3_terminal, rev_terminal) if t3_terminal and rev_terminal else None
    declared = tuple(sorted(set(FIXED_CYCLES) | (
        set(range(60, common_terminal + 1)) if common_terminal is not None else set()
    )))
    mesh_paths = (t3_root / "mesh_geometry.mat", t3_rev_root / "mesh_geometry.mat")
    mesh_available = all(path.is_file() for path in mesh_paths)
    t3_mesh = rev_mesh = geometry = None
    if mesh_available:
        t3_mesh, rev_mesh = load_mesh(mesh_paths[0]), load_mesh(mesh_paths[1])
        if t3_mesh.identities != rev_mesh.identities or not np.array_equal(t3_mesh.node_coords, rev_mesh.node_coords) \
                or not np.array_equal(t3_mesh.connectivity, rev_mesh.connectivity):
            raise ValueError("T3/T3-rev mesh identity is not exact")
        geometry = element_geometry(t3_mesh)
    same_rows: list[dict[str, object]] = []
    aggregate: list[dict[str, float]] = []
    for cycle in declared:
        if t3_mesh is None or geometry is None:
            same_rows.append({"comparison": "same_cycle", "cycle": cycle, "availability": "UNAVAILABLE"})
            continue
        left, right = _load_cycle(t3_root, cycle, t3_mesh), _load_cycle(t3_rev_root, cycle, t3_mesh)
        if left is None or right is None:
            same_rows.append({"comparison": "same_cycle", "cycle": cycle, "availability": "UNAVAILABLE"})
            continue
        maxima: list[float] = []
        relatives: list[float] = []
        for field in FIELDS:
            delta = right[field] - left[field]
            maximum = float(np.max(np.abs(delta), initial=0.0))
            reference_norm = float(np.linalg.norm(left[field].reshape(-1, order="F")))
            relative = float(np.linalg.norm(delta.reshape(-1, order="F")) / max(reference_norm, 1e-30))
            maxima.append(maximum)
            relatives.append(relative)
            same_rows.append({"comparison": "same_cycle", "cycle": cycle, "field": field,
                              "availability": "AVAILABLE", "max_abs": maximum, "relative_l2": relative,
                              **reduce_field(left[field], geometry.areas, geometry.centroids),
                              "right_area_weighted_mean": reduce_field(right[field], geometry.areas, geometry.centroids)["area_weighted_mean"]})
        aggregate.append({"cycle": float(cycle), "max_abs": max(maxima), "relative_l2": max(relatives)})
    common_post = [row for row in aggregate if row["cycle"] >= 60]
    expected_post = list(range(60, common_terminal + 1)) if common_terminal is not None else []
    classification = "UNAVAILABLE" if not expected_post or [int(row["cycle"]) for row in common_post] != expected_post else classify_order_effect(common_post, tolerances)
    event_rows: list[dict[str, object]] = []
    t3_event_path, rev_event_path = t3_root / "EVENT_METADATA.json", t3_rev_root / "EVENT_METADATA.json"
    t3_event = _strict_json(t3_event_path) if t3_event_path.is_file() else {}
    rev_event = _strict_json(rev_event_path) if rev_event_path.is_file() else {}
    for label, field in (("first_hit", "first_hit_cycle"), ("confirmed", "confirmed_cycle")):
        left_cycle, right_cycle = t3_event.get(field), rev_event.get(field)
        if type(left_cycle) is not int or type(right_cycle) is not int:
            event_rows.append({"comparison": label, "availability": "UNAVAILABLE"})
        else:
            event_rows.append({"comparison": label, "availability": "AVAILABLE", "t3_cycle": left_cycle, "t3_rev_cycle": right_cycle})
    destination.mkdir(parents=True, exist_ok=False)
    _write_csv(destination / "same_cycle_differences.csv", same_rows)
    _write_csv(destination / "own_event_differences.csv", event_rows)
    figure, axis = plt.subplots(figsize=(8, 4))
    available = [row for row in aggregate if row["cycle"] >= 60]
    if available:
        axis.plot([row["cycle"] for row in available], [row["max_abs"] for row in available], marker="o")
    axis.set(xlabel="cycle", ylabel="maximum absolute field difference", title="T3/T3-rev same-cycle reductions")
    figure.tight_layout()
    figure.savefig(destination / "same_cycle_order_effect.png", dpi=150)
    plt.close(figure)
    summary = {
        "schema_version": "toy_road_t3_t3rev_mechanism_summary_v1",
        "status": "PASS_OFFLINE_ANALYSIS",
        "order_effect_classification": classification,
        "nominal_dose_match": "same prescribed amplitude histogram and cycle count through c60",
        "predeclared_cycle_set": list(declared),
        "comparison_tolerances": {"max_abs": max_tol, "relative_l2": relative_tol},
        "mechanism_claim_boundary": "Order sensitivity under the qualified kernel and declared extension is not unique proof of physical mechanism.",
        "authorization_capability": None,
        "follow_on_authorized": False,
    }
    (destination / "mechanism_summary.json").write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    return summary
