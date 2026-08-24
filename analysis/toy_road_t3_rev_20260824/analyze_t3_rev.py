"""Read-only T3/T3-rev reductions; this module never authorizes or starts work."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import sys
import tempfile
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
EXACT_TOLERANCES = {"max_abs": 1e-12, "relative_l2": 1e-12}
QUALIFIED_T3_PROTOCOL_SHA256 = "db51a9cb54810711c2bdfe7ee35a705179e2852c7b069995d69693579c1e84a9"
QUALIFIED_T3_MANIFEST_SHA256 = "455b149b14276598ad87e4bcea6b6a2916de6e59d3812f791d66e61b1344bb01"


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_exact_protocol(protocol_path: Path, expected_sha256: str, module_name: str) -> Any:
    if not protocol_path.is_file() or _sha256(protocol_path) != expected_sha256:
        raise ValueError(f"qualified protocol byte identity differs: {protocol_path}")
    spec = importlib.util.spec_from_file_location(module_name, protocol_path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load hash-qualified protocol")
    protocol = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(protocol)
    if _sha256(protocol_path) != expected_sha256:
        raise ValueError("qualified protocol changed while it was imported")
    return protocol


def _authenticate_package(protocol: Any, package_root: Path, case_id: str) -> dict[str, object]:
    try:
        receipt = protocol.authenticate_terminal_package(package_root, case_id)
        protocol.recheck_authenticated_package(receipt)
        return receipt
    except Exception as error:
        raise ValueError(f"{case_id} terminal package is not authenticated: {error}") from error


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
    rev_authentication = terminal_module.authenticate_completed_package(rev_protocol, t3_rev_root)
    lock_path = t3_rev_root.parent / "receipts" / "T3_REV_EXECUTION_INPUT_LOCK.json"
    launch_receipt = _strict_json(t3_rev_root.parent / "receipts" / "T3_REV_LAUNCH_RECEIPT.json")
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
        t3_terminal, rev_terminal = _terminal_cycle(snapshot_t3), _terminal_cycle(snapshot_rev)
        common_terminal = min(t3_terminal, rev_terminal) if t3_terminal and rev_terminal else None
        declared = tuple(sorted(set(FIXED_CYCLES) | (
            set(range(60, common_terminal + 1)) if common_terminal is not None else set()
        )))
        t3_event = _strict_json(snapshot_t3 / "EVENT_METADATA.json")
        rev_event = _strict_json(snapshot_rev / "EVENT_METADATA.json")
        event_cycles = {
            value for event in (t3_event, rev_event)
            for value in (event.get("first_hit_cycle"), event.get("confirmed_cycle"))
            if type(value) is int
        }
        required_cycles = sorted(set(declared) | event_cycles)
        shard_paths = tuple(f"substeps/cycle_{cycle:04d}.mat" for cycle in required_cycles)
        _snapshot_authenticated_inputs(
            t3_protocol, t3_authentication, t3_root, snapshot_t3, shard_paths)
        _snapshot_authenticated_inputs(
            rev_protocol, rev_authentication, t3_rev_root, snapshot_rev, shard_paths)
        mesh_paths = (snapshot_t3 / "mesh_geometry.mat", snapshot_rev / "mesh_geometry.mat")
        t3_mesh, rev_mesh = load_mesh(mesh_paths[0]), load_mesh(mesh_paths[1])
        if t3_mesh.identities != rev_mesh.identities or not np.array_equal(t3_mesh.node_coords, rev_mesh.node_coords) \
                or not np.array_equal(t3_mesh.connectivity, rev_mesh.connectivity):
            raise ValueError("T3/T3-rev mesh identity is not exact")
        geometry = element_geometry(t3_mesh)
        same_rows: list[dict[str, object]] = []
        aggregate: list[dict[str, object]] = []
        for cycle in declared:
            left = _load_cycle(snapshot_t3, cycle, t3_mesh)
            right = _load_cycle(snapshot_rev, cycle, t3_mesh)
            if left is None or right is None:
                same_rows.append({"comparison": "same_cycle", "cycle": cycle, "availability": "UNAVAILABLE"})
                aggregate.append({"comparison": "same_cycle", "cycle": cycle, "availability": "UNAVAILABLE"})
                continue
            maxima: list[float] = []
            relatives: list[float] = []
            for field in FIELDS:
                row = _comparison_row("same_cycle", field, cycle, cycle, left[field], right[field], geometry)
                row["cycle"] = cycle
                maxima.append(float(row["max_abs"]))
                relatives.append(float(row["relative_l2"]))
                same_rows.append(row)
            aggregate.append({"comparison": "same_cycle", "cycle": cycle,
                              "availability": "AVAILABLE", "max_abs": max(maxima),
                              "relative_l2": max(relatives)})
        event_rows: list[dict[str, object]] = []
        for label, event_field in (("first_hit", "first_hit_cycle"), ("confirmed", "confirmed_cycle")):
            left_cycle, right_cycle = t3_event.get(event_field), rev_event.get(event_field)
            comparison = f"own_event_{label}"
            if type(left_cycle) is not int or type(right_cycle) is not int:
                for field_name in FIELDS:
                    event_rows.append({
                        "comparison": comparison, "field": field_name,
                        "left_cycle": left_cycle, "right_cycle": right_cycle,
                        "availability": "UNAVAILABLE",
                    })
                aggregate.append({"comparison": comparison, "cycle": None,
                                  "left_cycle": left_cycle, "right_cycle": right_cycle,
                                  "availability": "UNAVAILABLE"})
                continue
            left = _load_cycle(snapshot_t3, left_cycle, t3_mesh)
            right = _load_cycle(snapshot_rev, right_cycle, t3_mesh)
            if left is None or right is None:
                for field_name in FIELDS:
                    event_rows.append({
                        "comparison": comparison, "field": field_name,
                        "left_cycle": left_cycle, "right_cycle": right_cycle,
                        "availability": "UNAVAILABLE",
                    })
                aggregate.append({"comparison": comparison, "cycle": max(left_cycle, right_cycle),
                                  "left_cycle": left_cycle, "right_cycle": right_cycle,
                                  "availability": "UNAVAILABLE"})
                continue
            maxima: list[float] = []
            relatives: list[float] = []
            for field_name in FIELDS:
                row = _comparison_row(comparison, field_name, left_cycle, right_cycle,
                                      left[field_name], right[field_name], geometry)
                event_rows.append(row)
                maxima.append(float(row["max_abs"]))
                relatives.append(float(row["relative_l2"]))
            aggregate.append({"comparison": comparison, "cycle": max(left_cycle, right_cycle),
                              "left_cycle": left_cycle, "right_cycle": right_cycle,
                              "availability": "AVAILABLE", "max_abs": max(maxima),
                              "relative_l2": max(relatives)})
    common_post = [row for row in aggregate if row.get("comparison") == "same_cycle"
                   and row.get("availability") == "AVAILABLE" and int(row["cycle"]) >= 60]
    expected_post = list(range(60, common_terminal + 1)) if common_terminal is not None else []
    classification = "UNAVAILABLE" if not expected_post or [int(row["cycle"]) for row in common_post] != expected_post else classify_order_effect(aggregate, tolerances)
    destination.mkdir(parents=True, exist_ok=False)
    _write_csv(destination / "same_cycle_differences.csv", same_rows)
    _write_csv(destination / "own_event_differences.csv", event_rows)
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
        "status": "PASS_OFFLINE_ANALYSIS",
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
