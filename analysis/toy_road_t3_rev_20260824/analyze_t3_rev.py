"""Read-only T3/T3-rev reductions; this module never authorizes or starts work."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import sys
import tempfile
import types
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from analysis.toy_road_t3_mechanism_20260819.mechanism import (
    element_geometry, load_mesh, load_peak_fields, process_zone, reduce_field,
)
from analysis.toy_road_t3_mechanism_20260819.run_analysis import (
    FIELDS, _crack_metrics, _field_arrays, _node_graph,
)


CASE_ID = "T3_loading_history"
REV_CASE_ID = "T3_rev_loading_order"
FIXED_CYCLES = (20, 30, 31, 40, 60, 61)
BLOCK_TRANSITIONS = ((30, 31), (60, 61))
ENERGY_COMPONENT_FIELDS = ("raw_driver", "raw_cyclemax_driver", "active_driver")
REDUCTION_METRICS = (
    "min", "max", "area_weighted_mean", "area_weighted_integral",
    "p50", "p95", "p99", "support_area_abs_1e15",
    "support_area_rel_1pct", "weighted_centroid_x", "weighted_centroid_y",
    "weighted_rms_width_x", "weighted_rms_width_y",
)
PROCESS_METRICS = (
    "threshold", "support_area", "centroid_x", "centroid_y",
    "rms_width_x", "rms_width_y", "crack_tip_x",
    "damaged_component_size", "right_boundary_connected_size",
    "event_hit_reconstructed",
)
EXACT_TOLERANCES = {"max_abs": 1e-12, "relative_l2": 1e-12}
QUALIFIED_T3_PROTOCOL_SHA256 = "db51a9cb54810711c2bdfe7ee35a705179e2852c7b069995d69693579c1e84a9"
QUALIFIED_T3_MANIFEST_SHA256 = "455b149b14276598ad87e4bcea6b6a2916de6e59d3812f791d66e61b1344bb01"
QUALIFIED_T3_ADJUDICATION_SHA256 = "9c0a0783bd6c59d825300538336258350df63c294f38f7febf29dae905c00300"


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{label} must be a finite number")
    return float(value)


def _tolerances(value: Mapping[str, float]) -> tuple[float, float]:
    if set(value) != {"max_abs", "relative_l2"}:
        raise ValueError("order-effect tolerances must contain exactly max_abs and relative_l2")
    maximum = _finite_number(value["max_abs"], "max_abs tolerance")
    relative = _finite_number(value["relative_l2"], "relative_l2 tolerance")
    if maximum != EXACT_TOLERANCES["max_abs"] or relative != EXACT_TOLERANCES["relative_l2"]:
        raise ValueError("order-effect tolerances must be the unchanged exact 1e-12 contract")
    return maximum, relative


def classify_order_effect(rows: Sequence[Mapping[str, float]], tolerances: Mapping[str, float]) -> str:
    """Classify predeclared field and event comparisons with inclusive tolerances."""
    max_tol, relative_tol = _tolerances(tolerances)
    by_cycle: dict[int, tuple[float, float]] = {}
    own_event_signals: list[bool] = []
    event_timing_differs = False
    for row in rows:
        if row.get("availability", "AVAILABLE") == "UNAVAILABLE":
            return "UNAVAILABLE"
        cycle_value = row.get("cycle")
        if isinstance(cycle_value, bool) or not isinstance(cycle_value, (int, float)) or int(cycle_value) != cycle_value:
            raise ValueError("order-effect cycle must be an exact integer")
        cycle = int(cycle_value)
        comparison = row.get("comparison", "same_cycle")
        if comparison != "same_cycle":
            maximum = _finite_number(row.get("max_abs"), "max_abs")
            relative = _finite_number(row.get("relative_l2"), "relative_l2")
            own_event_signals.append(maximum > max_tol or relative > relative_tol)
            left_cycle = row.get("left_cycle")
            right_cycle = row.get("right_cycle")
            if left_cycle is not None or right_cycle is not None:
                for value, label in ((left_cycle, "left event cycle"),
                                     (right_cycle, "right event cycle")):
                    if isinstance(value, bool) or not isinstance(value, (int, float)) \
                            or int(value) != value:
                        raise ValueError(f"{label} must be an exact integer")
                event_timing_differs = event_timing_differs or int(left_cycle) != int(right_cycle)
            continue
        if cycle < 1 or cycle in by_cycle:
            raise ValueError("order-effect rows must be unique positive cycles")
        by_cycle[cycle] = (_finite_number(row.get("max_abs"), "max_abs"),
                           _finite_number(row.get("relative_l2"), "relative_l2"))
    post_cycles = sorted(cycle for cycle in by_cycle if cycle >= 60)
    if not post_cycles or post_cycles[0] != 60:
        return "UNAVAILABLE"
    if post_cycles != list(range(60, post_cycles[-1] + 1)) or len(post_cycles) < 2:
        return "UNAVAILABLE"
    significant = {
        cycle: maximum > max_tol or relative > relative_tol
        for cycle, (maximum, relative) in by_cycle.items()
    }
    if event_timing_differs or any(own_event_signals):
        return "PERSISTENT_LOADING_ORDER_DEPENDENCE_OBSERVED"
    if not any(significant.values()):
        return "ORDER_EFFECT_NOT_RESOLVED_WITHIN_TOLERANCE"
    if not significant[post_cycles[-1]]:
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


def _load_observation(root: Path, cycle: int, mesh: Any) -> dict[str, object] | None:
    """Load one authenticated peak shard without retaining unused GP matrices."""
    path = root / "substeps" / f"cycle_{cycle:04d}.mat"
    if not path.is_file():
        return None
    peak = load_peak_fields(path, cycle)
    return {
        "cycle": cycle,
        "d_node": peak.d_node.copy(),
        "arrays": _field_arrays(peak, mesh),
    }


def _comparison_row(
        comparison: str, field: str, left_cycle: int, right_cycle: int,
        left: np.ndarray, right: np.ndarray, geometry: Any) -> dict[str, object]:
    """Emit the complete published reduction on both sides and its scalar differences."""
    left_reduction = reduce_field(left, geometry.areas, geometry.centroids)
    right_reduction = reduce_field(right, geometry.areas, geometry.centroids)
    delta = right - left
    reference_norm = float(np.linalg.norm(left.reshape(-1, order="F")))
    row: dict[str, object] = {
        "comparison": comparison, "field": field, "availability": "AVAILABLE",
        "left_cycle": left_cycle, "right_cycle": right_cycle,
        "max_abs": float(np.max(np.abs(delta), initial=0.0)),
        "relative_l2": float(np.linalg.norm(delta.reshape(-1, order="F")) / max(reference_norm, 1e-30)),
    }
    for metric, value in left_reduction.items():
        row[f"left_{metric}"] = value
        row[f"right_{metric}"] = right_reduction[metric]
        row[f"right_minus_left_{metric}"] = right_reduction[metric] - value
    return row


def _unavailable_field_rows(
        comparison: str, left_cycle: object, right_cycle: object, *,
        availability: str = "UNAVAILABLE", **metadata: object,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for field in FIELDS:
        row: dict[str, object] = {
            "comparison": comparison, "field": field,
            "left_cycle": left_cycle, "right_cycle": right_cycle,
            "availability": availability, "max_abs": None,
            "relative_l2": None, **metadata,
        }
        for metric in REDUCTION_METRICS:
            row[f"left_{metric}"] = None
            row[f"right_{metric}"] = None
            row[f"right_minus_left_{metric}"] = None
        rows.append(row)
    return rows


def _unavailable_process_row(
        comparison: str, left_cycle: object, right_cycle: object, *,
        availability: str = "UNAVAILABLE", **metadata: object,
) -> dict[str, object]:
    """Keep process-zone CSV columns stable when a boundary is unavailable."""
    row: dict[str, object] = {
        "comparison": comparison, "left_cycle": left_cycle,
        "right_cycle": right_cycle, "availability": availability,
        "history_baseline_cycle": 30,
        "history_signal_definition": "(right-left)_comparison-(right-left)_c30",
        **metadata,
    }
    for metric in PROCESS_METRICS:
        row[f"left_{metric}"] = None
        row[f"right_{metric}"] = None
        if metric != "event_hit_reconstructed":
            row[f"right_minus_left_{metric}"] = None
    for metric in (
            "process_zone_intersection_area", "process_zone_union_area",
            "process_zone_jaccard", "history_difference_threshold",
            "spatial_overlap_area", "spatial_overlap_fraction_of_right_zone",
            "spatial_overlap_present"):
        row[metric] = None
    return row


def _process_state(
        observation: Mapping[str, object], previous: Mapping[str, object],
        mesh: Any, geometry: Any, graph: list[set[int]], seed_nodes: set[int],
) -> tuple[dict[str, object], np.ndarray]:
    arrays = observation["arrays"]
    previous_arrays = previous["arrays"]
    if not isinstance(arrays, dict) or not isinstance(previous_arrays, dict):
        raise ValueError("authenticated process-zone observation is malformed")
    delta = np.asarray(arrays["damage"]) - np.asarray(previous_arrays["damage"])
    zone = process_zone(delta, geometry)
    positive_delta = np.maximum(delta, 0.0)
    support = positive_delta >= zone["threshold"]
    crack = _crack_metrics(
        np.asarray(observation["d_node"]), mesh, graph, seed_nodes)
    return {**zone, **crack}, support


def _process_comparison_row(
        comparison: str, left_cycle: int, right_cycle: int,
        left: Mapping[str, object], left_previous: Mapping[str, object],
        right: Mapping[str, object], right_previous: Mapping[str, object],
        left_baseline: Mapping[str, object], right_baseline: Mapping[str, object],
        mesh: Any, geometry: Any, graph: list[set[int]],
        left_seed_nodes: set[int], right_seed_nodes: set[int],
        **metadata: object,
) -> dict[str, object]:
    """Apply the published crack/process-zone and history-zone overlap definitions."""
    left_state, left_support = _process_state(
        left, left_previous, mesh, geometry, graph, left_seed_nodes)
    right_state, right_support = _process_state(
        right, right_previous, mesh, geometry, graph, right_seed_nodes)
    row: dict[str, object] = {
        "comparison": comparison, "availability": "AVAILABLE",
        "left_cycle": left_cycle, "right_cycle": right_cycle, **metadata,
    }
    for metric in PROCESS_METRICS:
        left_value, right_value = left_state[metric], right_state[metric]
        row[f"left_{metric}"] = left_value
        row[f"right_{metric}"] = right_value
        if type(left_value) is not bool and type(right_value) is not bool:
            row[f"right_minus_left_{metric}"] = right_value - left_value
    intersection = left_support & right_support
    union = left_support | right_support
    intersection_area = float(geometry.areas[intersection].sum())
    union_area = float(geometry.areas[union].sum())
    row.update({
        "process_zone_intersection_area": intersection_area,
        "process_zone_union_area": union_area,
        "process_zone_jaccard": intersection_area / union_area if union_area else 1.0,
    })
    left_arrays, right_arrays = left["arrays"], right["arrays"]
    left_baseline_arrays = left_baseline["arrays"]
    right_baseline_arrays = right_baseline["arrays"]
    if any(not isinstance(arrays, dict) for arrays in (
            left_arrays, right_arrays, left_baseline_arrays,
            right_baseline_arrays)):
        raise ValueError("authenticated history observation is malformed")
    history_signal = (
        np.asarray(right_arrays["history"]) - np.asarray(left_arrays["history"])
        - np.asarray(right_baseline_arrays["history"])
        + np.asarray(left_baseline_arrays["history"])
    )
    history_difference = np.abs(history_signal)
    difference_floor = max(
        1e-14, 0.01 * float(np.max(history_difference, initial=0.0)))
    history_support = history_difference >= difference_floor
    overlap = history_support & right_support
    overlap_area = float(geometry.areas[overlap].sum())
    right_zone_area = float(geometry.areas[right_support].sum())
    row.update({
        "history_baseline_cycle": 30,
        "history_signal_definition": "(right-left)_comparison-(right-left)_c30",
        "history_difference_threshold": difference_floor,
        "spatial_overlap_area": overlap_area,
        "spatial_overlap_fraction_of_right_zone": (
            overlap_area / right_zone_area if right_zone_area else 0.0),
        "spatial_overlap_present": bool(np.any(overlap)),
    })
    return row


def _coverage_status(rows: Sequence[Mapping[str, object]], *,
                     allow_right_censored: bool = False) -> str:
    availability = {row.get("availability") for row in rows}
    if "UNAVAILABLE" in availability or not rows:
        return "UNAVAILABLE"
    if availability == {"NOT_APPLICABLE_RIGHT_CENSORED"}:
        return "NOT_APPLICABLE_RIGHT_CENSORED" if allow_right_censored else "UNAVAILABLE"
    if not availability.issubset({"AVAILABLE", "NOT_APPLICABLE_RIGHT_CENSORED"}):
        return "UNAVAILABLE"
    return "AVAILABLE"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_exact_protocol(protocol_path: Path, expected_sha256: str, module_name: str) -> Any:
    if not protocol_path.is_file():
        raise ValueError(f"qualified protocol byte identity differs: {protocol_path}")
    payload = protocol_path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ValueError(f"qualified protocol byte identity differs: {protocol_path}")
    protocol = types.ModuleType(module_name)
    protocol.__file__ = str(protocol_path)
    exec(compile(payload, str(protocol_path), "exec"), protocol.__dict__)
    if _sha256(protocol_path) != expected_sha256:
        raise ValueError("qualified protocol changed while verified bytes were executed")
    return protocol


def _authenticate_package(protocol: Any, package_root: Path, case_id: str) -> dict[str, object]:
    try:
        receipt = protocol.authenticate_terminal_package(package_root, case_id)
        protocol.recheck_authenticated_package(receipt)
        return receipt
    except Exception as error:
        raise ValueError(f"{case_id} terminal package is not authenticated: {error}") from error


def _require_published_t3_chain(
        repo_root: Path, package_root: Path,
        authentication: Mapping[str, object]) -> None:
    """Bind the live authenticated package to the published T3 adjudication chain."""
    evidence_root = repo_root / "analysis" / "toy_road_t3_mechanism_20260819" / "evidence"
    adjudication_path = evidence_root / "T3_SIBLING_TERMINAL_ADJUDICATION.json"
    terminal_manifest_path = evidence_root / "TERMINAL_MANIFEST.json"
    if _sha256(adjudication_path) != QUALIFIED_T3_ADJUDICATION_SHA256 \
            or _sha256(terminal_manifest_path) != QUALIFIED_T3_MANIFEST_SHA256:
        raise ValueError("published T3 adjudication or terminal manifest bytes differ")
    adjudication = _strict_json(adjudication_path)
    published_manifest = _strict_json(terminal_manifest_path)
    seal_builder_path = Path(__file__).with_name("build_t3_rev_seal.py")
    spec = importlib.util.spec_from_file_location("t3_rev_analysis_t3_chain", seal_builder_path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load published T3 adjudication validator")
    seal_builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seal_builder)
    try:
        execution = seal_builder._require_t3_adjudication(adjudication, published_manifest)
    except Exception as error:
        raise ValueError(f"published T3 adjudication is invalid: {error}") from error
    evidence = adjudication.get("evidence_sha256")
    terminal_result = adjudication.get("terminal_result")
    files = authentication.get("files")
    if not isinstance(evidence, dict) or not isinstance(terminal_result, dict) \
            or not isinstance(files, list):
        raise ValueError("published T3 adjudication chain is incomplete")
    authenticated_hashes = {
        item.get("path"): item.get("sha256") for item in files if isinstance(item, dict)
    }
    expected_bindings = {
        "TERMINAL_MANIFEST.json": evidence.get("terminal_manifest"),
        "EXECUTION_INPUT_LOCK.json": evidence.get("execution_input_lock"),
        "INPUT_SNAPSHOT.json": evidence.get("input_snapshot"),
        "qualification/C5_NUMERICAL_GATE_RECEIPT.json": evidence.get("c5_receipt"),
    }
    if any(authenticated_hashes.get(path) != digest for path, digest in expected_bindings.items()) \
            or authentication.get("manifest_sha256") != QUALIFIED_T3_MANIFEST_SHA256 \
            or authentication.get("package_snapshot_sha256") != evidence.get("package_snapshot"):
        raise ValueError("live T3 package does not match the published adjudication hashes")
    if authentication.get("execution_input_lock_sha256") != evidence.get("execution_input_lock") \
            or authentication.get("runtime_lock_sha256") != execution.get("runtime_lock_sha256") \
            or authentication.get("family_contract_sha256") != execution.get("family_contract_sha256") \
            or authentication.get("case_physics_contract_sha256") != execution.get("case_physics_contract_sha256"):
        raise ValueError("live T3 execution identity differs from the published adjudication")
    live_terminal = _strict_json(package_root / "TERMINAL_RESULT.json")
    expected_terminal = {
        "terminal_reason": terminal_result.get("terminal_reason"),
        "terminal_cycle": terminal_result.get("terminal_cycle"),
        "first_hit_cycle": terminal_result.get("first_hit_cycle"),
        "confirmed_cycle": terminal_result.get("confirmed_cycle"),
    }
    if any(live_terminal.get(field) != value for field, value in expected_terminal.items()):
        raise ValueError("live T3 terminal event differs from the published adjudication")


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _qualified_rev_protocol(
        t3_rev_root: Path, seal_path: Path, *, launch_authority: Any | None = None,
        repository_root: Path | None = None) -> tuple[Any, dict[str, object]]:
    """Derive the only admissible T3-rev protocol from its sealed launch chain."""
    run_root = t3_rev_root.parent
    launch_path = run_root / "receipts" / "T3_REV_LAUNCH_RECEIPT.json"
    launch_receipt = _strict_json(launch_path)
    seal = _strict_json(seal_path)
    seal_bytes = seal_path.read_bytes()
    seal_sha256 = hashlib.sha256(seal_bytes).hexdigest()
    if seal_bytes != _canonical_json_bytes(seal) + b"\n":
        raise ValueError("T3-rev seal bytes are not canonical")
    launcher = launch_authority
    if launcher is None:
        launcher_path = Path(__file__).with_name("launch_t3_rev.py")
        launcher_spec = importlib.util.spec_from_file_location(
            "t3_rev_analysis_launch_authority", launcher_path)
        if launcher_spec is None or launcher_spec.loader is None:
            raise ValueError("cannot load fixed T3-rev launch authority")
        launcher = importlib.util.module_from_spec(launcher_spec)
        launcher_spec.loader.exec_module(launcher)
    try:
        launcher.require_bridge_authorization_receipt(launch_receipt)
        launcher._require_seal(seal_path, str(launch_receipt["launcher_repository_commit"]))
    except Exception as error:
        raise ValueError(f"T3-rev seal/launch qualification failed: {error}") from error
    extension_identity = seal.get("extension_identity")
    if not isinstance(extension_identity, dict) \
            or seal.get("case_id") != REV_CASE_ID \
            or launch_receipt.get("case_id") != REV_CASE_ID \
            or launch_receipt.get("run_root") != str(run_root.resolve()) \
            or launch_receipt.get("seal_sha256") != seal_sha256:
        raise ValueError("T3-rev seal and launch identity differ")
    extension_root_value = launch_receipt.get("extension_root")
    overlay_root_value = launch_receipt.get("runtime_overlay_root")
    if not isinstance(extension_root_value, str) or not isinstance(overlay_root_value, str):
        raise ValueError("T3-rev launch omits sealed protocol roots")
    extension_root = Path(extension_root_value)
    overlay_root = Path(overlay_root_value)
    if not extension_root.is_absolute() or not overlay_root.is_absolute():
        raise ValueError("T3-rev protocol roots must be absolute")
    repo_root = Path(__file__).resolve().parents[2] \
        if repository_root is None else Path(repository_root)
    try:
        _, verified_manifest, _ = launcher._require_extension(repo_root, extension_root, seal)
    except Exception as error:
        raise ValueError(f"T3-rev extension is not the sealed verified source: {error}") from error
    manifest_path = extension_root / "EXTENSION_SOURCE_MANIFEST.json"
    manifest_sha256 = _sha256(manifest_path)
    if extension_identity.get("extension_source_manifest_sha256") != manifest_sha256 \
            or launch_receipt.get("extension_source_manifest_sha256") != manifest_sha256:
        raise ValueError("T3-rev extension manifest is not hash-bound to seal and launch")
    manifest = _strict_json(manifest_path)
    if manifest != verified_manifest:
        raise ValueError("T3-rev extension verification and manifest bytes disagree")
    shadow_files = manifest.get("shadow_files")
    if not isinstance(shadow_files, list):
        raise ValueError("T3-rev extension shadow manifest is malformed")
    shadow_hashes = {
        item.get("path"): item.get("sha256") for item in shadow_files if isinstance(item, dict)
    }
    protocol_sha256 = shadow_hashes.get("toy_road_protocol.py")
    if not isinstance(protocol_sha256, str) \
            or launch_receipt.get("extension_shadow_sha256") != shadow_hashes:
        raise ValueError("T3-rev protocol shadows are not the launched sealed bytes")
    extension_protocol = extension_root / "toy_road_protocol.py"
    overlay_protocol = overlay_root / "toy_road_protocol.py"
    if _sha256(overlay_protocol) != protocol_sha256:
        raise ValueError("T3-rev runtime overlay protocol differs from the sealed extension")
    runtime_identity = seal.get("runtime_identity")
    if not isinstance(runtime_identity, dict):
        raise ValueError("T3-rev seal omits runtime identity")
    try:
        launcher.require_materialized_runtime_overlay(
            overlay_root, shadow_hashes, runtime_identity.get("four_binary_sha256"))
    except Exception as error:
        raise ValueError(f"T3-rev launched runtime overlay differs: {error}") from error
    marker = _strict_json(launcher.seal_consumption_marker(seal_sha256))
    expected_marker = {
        "schema_version": "toy_road_t3_rev_seal_consumption_v1",
        "case_id": REV_CASE_ID,
        "composite_producer": "sealed_T3_base_plus_T3_rev_case_definition_extension",
        "authorization_capability": "exactly_one_T3_rev_loading_order_execution",
        "seal_sha256": seal_sha256,
        "run_root": str(run_root.resolve()),
        "resume_allowed": False,
        "new_authorization_required": True,
    }
    if marker != expected_marker:
        raise ValueError("T3-rev global seal claim does not bind this analysis run")
    protocol = _load_exact_protocol(
        extension_protocol, protocol_sha256, "t3_rev_hash_qualified_analysis_protocol")
    return protocol, {
        "seal_sha256": seal_sha256,
        "launch_receipt_sha256": _sha256(launch_path),
        "extension_source_manifest_sha256": manifest_sha256,
        "protocol_sha256": protocol_sha256,
    }


def _snapshot_authenticated_inputs(
        protocol: Any, authentication: Mapping[str, object], package_root: Path,
        snapshot_root: Path, paths: Sequence[str]) -> None:
    """Copy only receipt-authenticated bytes, then recheck the complete package."""
    entries = authentication.get("files")
    if not isinstance(entries, list):
        raise ValueError("authentication receipt omits its file inventory")
    digests = {
        item.get("path"): item.get("sha256") for item in entries if isinstance(item, dict)
    }
    for relative in paths:
        source = package_root / relative
        expected = digests.get(relative)
        if not isinstance(expected, str) or not source.is_file():
            raise ValueError(f"authenticated analysis input is unavailable: {relative}")
        payload = source.read_bytes()
        if hashlib.sha256(payload).hexdigest() != expected:
            raise ValueError(f"authenticated analysis input changed: {relative}")
        target = snapshot_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    protocol.recheck_authenticated_package(authentication)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    preferred = [
        "comparison", "cycle", "availability", "field", "left_cycle", "right_cycle",
        "max_abs", "relative_l2",
    ]
    keys = {key for row in rows for key in row}
    columns = [key for key in preferred if key in keys]
    columns.extend(sorted(keys - set(columns)))
    if not columns:
        columns = ["comparison", "cycle", "availability"]
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _analyze_t3_rev(
        t3_root: Path, t3_rev_root: Path, destination: Path,
        tolerances: Mapping[str, float] | None = None,
        *, seal_path: Path,
        required_t3_manifest_sha256: str = QUALIFIED_T3_MANIFEST_SHA256,
        launch_authority: Any | None = None,
        repository_root: Path | None = None) -> dict[str, object]:
    """Reduce only declared comparison cycles, retaining unavailable evidence explicitly."""
    t3_root = Path(t3_root).resolve()
    t3_rev_root = Path(t3_rev_root).resolve()
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(f"analysis destination already exists: {destination}")
    if tolerances is None:
        tolerances = {"max_abs": 1e-12, "relative_l2": 1e-12}
    max_tol, relative_tol = _tolerances(tolerances)
    repo_root = Path(__file__).resolve().parents[2]
    t3_protocol_path = repo_root / "producer_handoffs" / "toy_road_p0_repeatability_20260803" / "toy_road_protocol.py"
    t3_protocol = _load_exact_protocol(
        t3_protocol_path, QUALIFIED_T3_PROTOCOL_SHA256, "t3_hash_qualified_analysis_protocol")
    t3_authentication = _authenticate_package(t3_protocol, t3_root, CASE_ID)
    manifest_path = t3_root / "TERMINAL_MANIFEST.json"
    if _sha256(manifest_path) != required_t3_manifest_sha256:
        raise ValueError("T3 package is not the published qualified source identity")
    if launch_authority is None:
        _require_published_t3_chain(repo_root, t3_root, t3_authentication)
    rev_protocol, rev_protocol_identity = _qualified_rev_protocol(
        t3_rev_root, Path(seal_path), launch_authority=launch_authority,
        repository_root=repository_root,
    )
    terminal_module_path = Path(__file__).with_name("validate_t3_rev_terminal.py")
    terminal_spec = importlib.util.spec_from_file_location("t3_rev_analysis_terminal", terminal_module_path)
    if terminal_spec is None or terminal_spec.loader is None:
        raise ValueError("cannot load T3-rev terminal authenticator")
    terminal_module = importlib.util.module_from_spec(terminal_spec)
    terminal_spec.loader.exec_module(terminal_module)
    lock_path = t3_rev_root.parent / "receipts" / "T3_REV_EXECUTION_INPUT_LOCK.json"
    launch_receipt = _strict_json(t3_rev_root.parent / "receipts" / "T3_REV_LAUNCH_RECEIPT.json")
    chain_repo_root = Path(repository_root).resolve() if repository_root is not None else repo_root
    try:
        rev_adjudication = terminal_module._validate_terminal(
            t3_rev_root,
            sealed_base_root=chain_repo_root / "producer_handoffs" /
            "toy_road_p0_repeatability_20260803",
            extension_root=Path(str(launch_receipt["extension_root"])),
            seal_path=Path(seal_path),
            run_root=t3_rev_root.parent,
            launch=launch_authority,
            _emit_adjudication=False,
        )
    except Exception as error:
        raise ValueError(f"T3-rev authoritative terminal chain failed: {error}") from error
    rev_authentication = rev_adjudication.get("terminal_authentication")
    if not isinstance(rev_authentication, dict):
        raise ValueError("T3-rev authoritative terminal chain has no completed authentication")
    lock = _strict_json(lock_path)
    measurement_path = t3_rev_root.parent / "receipts" / "T3_REV_RUNTIME_MEASUREMENT.json"
    measurement = _strict_json(measurement_path)
    try:
        rev_protocol.validate_execution_input_lock(lock, REV_CASE_ID)
        rev_protocol.validate_runtime_measurement(lock, measurement)
    except Exception as error:
        raise ValueError(f"T3-rev lock/runtime measurement is not authoritative PASS: {error}") from error
    if lock_path.read_bytes() != rev_protocol.canonical_json_bytes(lock):
        raise ValueError("T3-rev launch lock bytes are not canonical")
    if rev_authentication.get("execution_input_lock_sha256") != _sha256(lock_path) \
            or launch_receipt.get("execution_input_lock_sha256") != _sha256(lock_path) \
            or any(lock.get(field) != launch_receipt.get(field) for field in (
                "source_commit", "runtime_lock_sha256", "family_contract_sha256",
                "case_physics_contract_sha256")) \
            or rev_authentication.get("package_root") != str(t3_rev_root.resolve()):
        raise ValueError("T3-rev terminal authentication is not bound to its launch lock/root")
    with tempfile.TemporaryDirectory(prefix="t3-rev-analysis-snapshot-") as temporary:
        snapshot_parent = Path(temporary)
        initial = ("TERMINAL_RESULT.json", "EVENT_METADATA.json", "mesh_geometry.mat")
        _snapshot_authenticated_inputs(
            t3_protocol, t3_authentication, t3_root, snapshot_parent / "t3", initial)
        _snapshot_authenticated_inputs(
            rev_protocol, rev_authentication, t3_rev_root, snapshot_parent / "rev", initial)
        snapshot_t3, snapshot_rev = snapshot_parent / "t3", snapshot_parent / "rev"
        t3_terminal_result = _strict_json(snapshot_t3 / "TERMINAL_RESULT.json")
        rev_terminal_result = _strict_json(snapshot_rev / "TERMINAL_RESULT.json")
        t3_terminal, rev_terminal = _terminal_cycle(snapshot_t3), _terminal_cycle(snapshot_rev)
        common_terminal = min(t3_terminal, rev_terminal) if t3_terminal and rev_terminal else None
        declared = tuple(sorted(set(FIXED_CYCLES) | (
            set(range(60, common_terminal + 1)) if common_terminal is not None else set()
        )))
        t3_event = _strict_json(snapshot_t3 / "EVENT_METADATA.json")
        rev_event = _strict_json(snapshot_rev / "EVENT_METADATA.json")
        t3_event_cycles = {
            value for value in (t3_event.get("first_hit_cycle"), t3_event.get("confirmed_cycle"))
            if type(value) is int
        }
        rev_event_cycles = {
            value for value in (rev_event.get("first_hit_cycle"), rev_event.get("confirmed_cycle"))
            if type(value) is int
        }

        def observation_cycles(event_cycles: set[int]) -> set[int]:
            requested = set(declared) | event_cycles | {1}
            requested.update(cycle - 1 for cycle in tuple(requested) if cycle > 1)
            return requested

        t3_cycles = observation_cycles(t3_event_cycles)
        rev_cycles = observation_cycles(rev_event_cycles)
        t3_authenticated_paths = {
            item.get("path") for item in t3_authentication.get("files", [])
            if isinstance(item, dict)
        }
        rev_authenticated_paths = {
            item.get("path") for item in rev_authentication.get("files", [])
            if isinstance(item, dict)
        }
        t3_shard_paths = tuple(
            path for cycle in sorted(t3_cycles)
            if (path := f"substeps/cycle_{cycle:04d}.mat") in t3_authenticated_paths
        )
        rev_shard_paths = tuple(
            path for cycle in sorted(rev_cycles)
            if (path := f"substeps/cycle_{cycle:04d}.mat") in rev_authenticated_paths
        )
        _snapshot_authenticated_inputs(
            t3_protocol, t3_authentication, t3_root, snapshot_t3, t3_shard_paths)
        _snapshot_authenticated_inputs(
            rev_protocol, rev_authentication, t3_rev_root, snapshot_rev, rev_shard_paths)
        mesh_paths = (snapshot_t3 / "mesh_geometry.mat", snapshot_rev / "mesh_geometry.mat")
        t3_mesh, rev_mesh = load_mesh(mesh_paths[0]), load_mesh(mesh_paths[1])
        if t3_mesh.identities != rev_mesh.identities or not np.array_equal(t3_mesh.node_coords, rev_mesh.node_coords) \
                or not np.array_equal(t3_mesh.connectivity, rev_mesh.connectivity):
            raise ValueError("T3/T3-rev mesh identity is not exact")
        geometry = element_geometry(t3_mesh)
        graph = _node_graph(t3_mesh)
        t3_observations = {
            cycle: observation for cycle in sorted(t3_cycles)
            if (observation := _load_observation(snapshot_t3, cycle, t3_mesh)) is not None
        }
        rev_observations = {
            cycle: observation for cycle in sorted(rev_cycles)
            if (observation := _load_observation(snapshot_rev, cycle, rev_mesh)) is not None
        }
        if 1 not in t3_observations or 1 not in rev_observations:
            raise ValueError("authenticated c1 shard is required for crack-component seeding")
        t3_seed_nodes = set(int(index) for index in np.flatnonzero(
            np.asarray(t3_observations[1]["d_node"]) >= 0.95))
        rev_seed_nodes = set(int(index) for index in np.flatnonzero(
            np.asarray(rev_observations[1]["d_node"]) >= 0.95))
        t3_baseline = t3_observations.get(30)
        rev_baseline = rev_observations.get(30)
        same_rows: list[dict[str, object]] = []
        process_rows: list[dict[str, object]] = []
        aggregate: list[dict[str, object]] = []
        for cycle in declared:
            left = t3_observations.get(cycle)
            right = rev_observations.get(cycle)
            if left is None or right is None:
                unavailable = _unavailable_field_rows(
                    "same_cycle", cycle, cycle, cycle=cycle)
                same_rows.extend(unavailable)
                aggregate.append({"comparison": "same_cycle", "cycle": cycle, "availability": "UNAVAILABLE"})
            else:
                left_arrays, right_arrays = left["arrays"], right["arrays"]
                if not isinstance(left_arrays, dict) or not isinstance(right_arrays, dict):
                    raise ValueError("authenticated same-cycle observation is malformed")
                maxima: list[float] = []
                relatives: list[float] = []
                for field in FIELDS:
                    row = _comparison_row(
                        "same_cycle", field, cycle, cycle,
                        left_arrays[field], right_arrays[field], geometry)
                    row["cycle"] = cycle
                    maxima.append(float(row["max_abs"]))
                    relatives.append(float(row["relative_l2"]))
                    same_rows.append(row)
                aggregate.append({
                    "comparison": "same_cycle", "cycle": cycle,
                    "availability": "AVAILABLE", "max_abs": max(maxima),
                    "relative_l2": max(relatives),
                })
            left_previous = t3_observations.get(cycle - 1)
            right_previous = rev_observations.get(cycle - 1)
            if any(observation is None for observation in (
                    left, right, left_previous, right_previous,
                    t3_baseline, rev_baseline)):
                process_rows.append(_unavailable_process_row(
                    "same_cycle", cycle, cycle, cycle=cycle))
            else:
                process_rows.append(_process_comparison_row(
                    "same_cycle", cycle, cycle,
                    left, left_previous, right, right_previous,
                    t3_baseline, rev_baseline,
                    t3_mesh, geometry, graph, t3_seed_nodes, rev_seed_nodes,
                    cycle=cycle,
                ))
        event_rows: list[dict[str, object]] = []
        for label, event_field in (("first_hit", "first_hit_cycle"), ("confirmed", "confirmed_cycle")):
            left_cycle, right_cycle = t3_event.get(event_field), rev_event.get(event_field)
            comparison = f"own_event_{label}"
            if type(left_cycle) is not int or type(right_cycle) is not int:
                censored = t3_terminal_result.get("terminal_reason") == "right_censored" \
                    or rev_terminal_result.get("terminal_reason") == "right_censored"
                availability = "NOT_APPLICABLE_RIGHT_CENSORED" if censored else "UNAVAILABLE"
                event_rows.extend(_unavailable_field_rows(
                    comparison, left_cycle, right_cycle, availability=availability))
                process_rows.append(_unavailable_process_row(
                    comparison, left_cycle, right_cycle,
                    availability=availability))
                if not censored:
                    aggregate.append({
                        "comparison": comparison, "cycle": None,
                        "left_cycle": left_cycle, "right_cycle": right_cycle,
                        "availability": "UNAVAILABLE",
                    })
                continue
            left = t3_observations.get(left_cycle)
            right = rev_observations.get(right_cycle)
            if left is None or right is None:
                event_rows.extend(_unavailable_field_rows(
                    comparison, left_cycle, right_cycle))
                aggregate.append({
                    "comparison": comparison, "cycle": max(left_cycle, right_cycle),
                    "left_cycle": left_cycle, "right_cycle": right_cycle,
                    "availability": "UNAVAILABLE",
                })
                process_rows.append(_unavailable_process_row(
                    comparison, left_cycle, right_cycle))
                continue
            left_arrays, right_arrays = left["arrays"], right["arrays"]
            if not isinstance(left_arrays, dict) or not isinstance(right_arrays, dict):
                raise ValueError("authenticated own-event observation is malformed")
            maxima: list[float] = []
            relatives: list[float] = []
            for field_name in FIELDS:
                row = _comparison_row(
                    comparison, field_name, left_cycle, right_cycle,
                    left_arrays[field_name], right_arrays[field_name], geometry)
                event_rows.append(row)
                maxima.append(float(row["max_abs"]))
                relatives.append(float(row["relative_l2"]))
            aggregate.append({
                "comparison": comparison, "cycle": max(left_cycle, right_cycle),
                "left_cycle": left_cycle, "right_cycle": right_cycle,
                "availability": "AVAILABLE", "max_abs": max(maxima),
                "relative_l2": max(relatives),
            })
            left_previous = t3_observations.get(left_cycle - 1)
            right_previous = rev_observations.get(right_cycle - 1)
            if any(observation is None for observation in (
                    left_previous, right_previous, t3_baseline, rev_baseline)):
                process_rows.append(_unavailable_process_row(
                    comparison, left_cycle, right_cycle))
            else:
                process_rows.append(_process_comparison_row(
                    comparison, left_cycle, right_cycle,
                    left, left_previous, right, right_previous,
                    t3_baseline, rev_baseline,
                    t3_mesh, geometry, graph, t3_seed_nodes, rev_seed_nodes,
                ))

        transition_rows: list[dict[str, object]] = []
        cases = (
            (CASE_ID, t3_observations),
            (REV_CASE_ID, rev_observations),
        )
        for start, end in BLOCK_TRANSITIONS:
            for case_id, observations in cases:
                start_observation = observations.get(start)
                end_observation = observations.get(end)
                if start_observation is None or end_observation is None:
                    transition_rows.extend(_unavailable_field_rows(
                        "within_case_transition", start, end,
                        case_id=case_id, start_cycle=start, end_cycle=end))
                    continue
                start_arrays = start_observation["arrays"]
                end_arrays = end_observation["arrays"]
                if not isinstance(start_arrays, dict) or not isinstance(end_arrays, dict):
                    raise ValueError("authenticated transition observation is malformed")
                for field in FIELDS:
                    row = _comparison_row(
                        "within_case_transition", field, start, end,
                        start_arrays[field], end_arrays[field], geometry)
                    row.update({
                        "case_id": case_id, "start_cycle": start, "end_cycle": end,
                    })
                    transition_rows.append(row)
            endpoints = (
                t3_observations.get(start), t3_observations.get(end),
                rev_observations.get(start), rev_observations.get(end),
            )
            if any(observation is None for observation in endpoints):
                transition_rows.extend(_unavailable_field_rows(
                    "cross_case_difference_of_transitions", end, end,
                    left_case_id=CASE_ID, right_case_id=REV_CASE_ID,
                    start_cycle=start, end_cycle=end))
            else:
                t3_start, t3_end, rev_start, rev_end = endpoints
                transition_arrays = [
                    observation["arrays"] for observation in endpoints
                    if observation is not None
                ]
                if any(not isinstance(arrays, dict) for arrays in transition_arrays):
                    raise ValueError("authenticated cross-transition observation is malformed")
                t3_start_arrays, t3_end_arrays, rev_start_arrays, rev_end_arrays = transition_arrays
                for field in FIELDS:
                    t3_delta = t3_end_arrays[field] - t3_start_arrays[field]
                    rev_delta = rev_end_arrays[field] - rev_start_arrays[field]
                    row = _comparison_row(
                        "cross_case_difference_of_transitions", field, end, end,
                        t3_delta, rev_delta, geometry)
                    row.update({
                        "left_case_id": CASE_ID, "right_case_id": REV_CASE_ID,
                        "start_cycle": start, "end_cycle": end,
                    })
                    transition_rows.append(row)

        energy_rows = [{
            **row,
            "energy_component_role": "AUTHENTICATED_SHARD_ENERGY_DENSITY_OBSERVABLE",
        } for row in (*same_rows, *event_rows, *transition_rows)
            if row.get("field") in ENERGY_COMPONENT_FIELDS]
        unavailable_tot_en = "UNAVAILABLE_NOT_CAPTURED_IN_AUTHENTICATED_SHARDS"
        tot_en_role = "AUXILIARY_ONLY_EXCLUDED_FROM_CLASSIFICATION"
        tot_en_rows: list[dict[str, object]] = []
        for case_id, terminal_cycle in ((CASE_ID, t3_terminal), (REV_CASE_ID, rev_terminal)):
            if terminal_cycle is None:
                continue
            for cycle in range(1, terminal_cycle + 1):
                tot_en_rows.append({
                    "comparison": "within_case_trajectory", "case_id": case_id,
                    "cycle": cycle, "field": "tot_en",
                    "availability": unavailable_tot_en,
                    "role": tot_en_role,
                })
            for start, end in BLOCK_TRANSITIONS:
                tot_en_rows.append({
                    "comparison": "within_case_transition", "case_id": case_id,
                    "field": "tot_en", "start_cycle": start, "end_cycle": end,
                    "availability": unavailable_tot_en, "role": tot_en_role,
                })
        for start, end in BLOCK_TRANSITIONS:
            tot_en_rows.append({
                "comparison": "cross_case_difference_of_transitions",
                "left_case_id": CASE_ID, "right_case_id": REV_CASE_ID,
                "field": "tot_en", "start_cycle": start, "end_cycle": end,
                "availability": unavailable_tot_en, "role": tot_en_role,
            })

        required_coverage = {
            "same_cycle_fields": _coverage_status(same_rows),
            "block_transitions": _coverage_status(transition_rows),
            "process_zone_crack_overlap": _coverage_status(process_rows),
            "energy_components": _coverage_status(energy_rows),
            "own_event_boundaries": _coverage_status(
                event_rows, allow_right_censored=True),
        }
        required_complete = all(status in {
            "AVAILABLE", "NOT_APPLICABLE_RIGHT_CENSORED",
        } for status in required_coverage.values())
    if not required_complete:
        classification = "UNAVAILABLE"
    elif (t3_terminal_result.get("terminal_reason") == "right_censored") != \
            (rev_terminal_result.get("terminal_reason") == "right_censored"):
        classification = "PERSISTENT_LOADING_ORDER_DEPENDENCE_OBSERVED"
    else:
        classification = classify_order_effect(aggregate, tolerances)
    destination.mkdir(parents=True, exist_ok=False)
    _write_csv(destination / "same_cycle_differences.csv", same_rows)
    _write_csv(destination / "own_event_differences.csv", event_rows)
    _write_csv(destination / "block_transition_differences.csv", transition_rows)
    _write_csv(destination / "process_zone_crack_overlap.csv", process_rows)
    _write_csv(destination / "energy_component_differences.csv", energy_rows)
    _write_csv(destination / "auxiliary_tot_en.csv", tot_en_rows)
    figure, axis = plt.subplots(figsize=(8, 4))
    available = [row for row in aggregate if row.get("comparison") == "same_cycle"
                 and row.get("availability") == "AVAILABLE" and int(row["cycle"]) >= 60]
    if available:
        axis.plot([row["cycle"] for row in available], [row["max_abs"] for row in available], marker="o")
    axis.set(xlabel="cycle", ylabel="maximum absolute field difference", title="T3/T3-rev same-cycle reductions")
    figure.tight_layout()
    figure.savefig(destination / "same_cycle_order_effect.png", dpi=150)
    plt.close(figure)
    summary = {
        "schema_version": "toy_road_t3_t3rev_mechanism_summary_v1",
        "status": "PASS_OFFLINE_ANALYSIS" if required_complete
        else "INCOMPLETE_OFFLINE_ANALYSIS",
        "order_effect_classification": classification,
        "nominal_dose_match": "same prescribed amplitude histogram and cycle count through c60",
        "predeclared_cycle_set": list(declared),
        "comparison_tolerances": {"max_abs": max_tol, "relative_l2": relative_tol},
        "t3_terminal_authentication": t3_authentication,
        "t3_rev_terminal_authentication": rev_authentication,
        "t3_protocol_sha256": QUALIFIED_T3_PROTOCOL_SHA256,
        "t3_terminal_manifest_sha256": required_t3_manifest_sha256,
        "t3_rev_protocol_identity": rev_protocol_identity,
        "t3_rev_runtime_measurement_sha256": _sha256(measurement_path),
        "required_observable_coverage": required_coverage,
        "required_observables_complete": required_complete,
        "energy_component_definitions": {
            "raw_driver": "peak-substep GP-mean psi_raw_gp",
            "raw_cyclemax_driver": "cycle GP-mean psi_raw_cyclemax_gp",
            "active_driver": "peak-substep GP-mean psi_active_gp",
        },
        "auxiliary_observable_coverage": {
            "tot_en": "UNAVAILABLE_NOT_CAPTURED_IN_AUTHENTICATED_SHARDS",
        },
        "tot_en_role": "auxiliary monitor only; excluded from classification and required PASS coverage",
        "mechanism_claim_boundary": "Order sensitivity under the qualified kernel and declared extension is not unique proof of physical mechanism.",
        "authorization_capability": None,
        "follow_on_authorized": False,
    }
    (destination / "mechanism_summary.json").write_text(json.dumps(summary, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    return summary


def analyze_t3_rev(
        t3_root: Path, t3_rev_root: Path, destination: Path,
        tolerances: Mapping[str, float] | None = None, *, seal_path: Path) -> dict[str, object]:
    """Public analysis accepts no caller-selected protocol or qualification identity."""
    return _analyze_t3_rev(
        t3_root, t3_rev_root, destination, tolerances,
        seal_path=seal_path,
        required_t3_manifest_sha256=QUALIFIED_T3_MANIFEST_SHA256,
    )
