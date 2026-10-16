"""Reviewed Stage-0A P1 packet export and verification.

The exporter never discovers an archive.  Callers provide the exact sealed run,
A002 receipt, frozen config and a new output directory.  It repeats the complete
six-state qualification before writing the selected 16 transitions.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

import numpy as np

from s09_stage0a_capability import (
    S09_E008_CONTEXT,
    Stage0ACapabilityContext,
    _qualify_decode_and_freeze,
    decode_native_static,
    load_state_index,
)
from s09_stage0a_packet import decode_stage0a_transitions

SCHEMA = "s09-e008-p1-packet-v1"
REVIEWED_BASE_CONFIG_SHA256 = "0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b"
ARRAY_NAMES = (
    "cycles", "path", "d_pre", "d_peak", "history_pre", "history_peak",
    "u_peak", "xy", "conn", "shape", "reference_derivative",
    "gauss_weight", "thickness", "nodal_weight", "gp_weight",
)


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def _validate_config(config: dict[str, Any]) -> tuple[int, ...]:
    _require(config.get("schema_version") == "s09-e008-p1-run-package-v2",
             "unexpected P1 config schema")
    selected = tuple(config["data"]["selected_cycles"])
    _require(selected == (1, 2, 3, 4, 21, 29, 41, 46, 48, 58, 60, 69, 70, 71, 72, 73),
             "selected cycles differ from package review")
    _require(config["data"]["history_order"] == ["H", "alpha_bar", "q_prev", "f"],
             "history order differs from package review")
    _require(config["data"]["prescribed_path"] == [0.0, 0.031249875, 0.062499875, 0.093749875, 0.124999875, 0.0],
             "prescribed path differs from package review")
    _require(config["execution_authorized"] is False,
             "unresolved package config must remain non-executable")
    _require(config["data"]["detectable_growth_scale_D"] == 0.00016864539921617467,
             "detectable-growth scale D differs from A002")
    _require(config["data"]["near_stagnant_selection_limit"] == 8.432269960808734e-06,
             "near-stagnant selection limit differs from A002")
    return selected


def _validate_arrays(arrays: dict[str, np.ndarray], *, cycles: tuple[int, ...],
                     context: Stage0ACapabilityContext) -> None:
    expected = {
        "cycles": ((16,), np.dtype("int64")),
        "path": ((6,), np.dtype("float64")),
        "d_pre": ((16, context.expected_nodes), np.dtype("float64")),
        "d_peak": ((16, context.expected_nodes), np.dtype("float64")),
        "history_pre": ((16, context.expected_elements, context.expected_gp, 4), np.dtype("float64")),
        "history_peak": ((16, context.expected_elements, context.expected_gp, 4), np.dtype("float64")),
        "u_peak": ((16, context.expected_nodes, 2), np.dtype("float64")),
        "xy": ((context.expected_nodes, 2), np.dtype("float64")),
        "conn": ((context.expected_elements, 4), np.dtype("int64")),
        "shape": ((context.expected_gp, 4), np.dtype("float64")),
        "reference_derivative": ((context.expected_gp, 2, 4), np.dtype("float64")),
        "gauss_weight": ((context.expected_gp,), np.dtype("float64")),
        "thickness": ((1,), np.dtype("float64")),
        "nodal_weight": ((context.expected_nodes,), np.dtype("float64")),
        "gp_weight": ((context.expected_elements, context.expected_gp), np.dtype("float64")),
    }
    _require(set(arrays) == set(expected), "packet array membership mismatch")
    for name, (shape, dtype) in expected.items():
        value = arrays[name]
        _require(value.shape == shape and value.dtype == dtype, f"invalid {name} shape/dtype")
        if dtype.kind == "f":
            _require(np.isfinite(value).all(), f"nonfinite packet array: {name}")
    _require(tuple(arrays["cycles"].tolist()) == cycles, "packet cycle order mismatch")
    _require(np.all((arrays["d_pre"] >= 0) & (arrays["d_pre"] <= 1)), "invalid pre damage")
    _require(np.all((arrays["d_peak"] >= arrays["d_pre"]) & (arrays["d_peak"] <= 1)),
             "invalid peak damage")
    _require(np.all(arrays["history_peak"][..., 1] >= arrays["history_pre"][..., 1]),
             "invalid alpha irreversibility")
    _require(np.all(arrays["nodal_weight"] > 0) and np.all(arrays["gp_weight"] > 0),
             "nonpositive support weights")
    _require(np.all(arrays["conn"] >= 0) and np.all(arrays["conn"] < context.expected_nodes),
             "connectivity outside native node range")


def write_packet(*, output_dir: Path, arrays: dict[str, np.ndarray],
                 metadata: dict[str, Any], cycles: tuple[int, ...],
                 context: Stage0ACapabilityContext) -> dict[str, Any]:
    """Atomically write a fresh packet directory and return its identity."""
    output_dir = output_dir.resolve()
    _require(not output_dir.exists(), "packet output directory already exists")
    _validate_arrays(arrays, cycles=cycles, context=context)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent))
    try:
        records: dict[str, dict[str, Any]] = {}
        for name in ARRAY_NAMES:
            path = staging / f"{name}.npy"
            with path.open("wb") as stream:
                np.save(stream, np.ascontiguousarray(arrays[name]), allow_pickle=False)
            records[name] = {
                "file": path.name,
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "shape": list(arrays[name].shape),
                "dtype": arrays[name].dtype.str,
            }
        manifest = {
            "schema_version": SCHEMA,
            "metadata": metadata,
            "arrays": records,
        }
        manifest_bytes = canonical_json(manifest)
        (staging / "manifest.json").write_bytes(manifest_bytes)
        identity = {
            "schema_version": SCHEMA,
            "manifest_sha256": sha256_bytes(manifest_bytes),
            "manifest_bytes": len(manifest_bytes),
            "array_count": len(records),
        }
        (staging / "packet_identity.json").write_bytes(canonical_json(identity))
        os.replace(staging, output_dir)
        return identity
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def export_s09_e008_p1_packet(*, run_root: Path, capability_receipt_path: Path,
                              config_path: Path, output_dir: Path,
                              context: Stage0ACapabilityContext = S09_E008_CONTEXT) -> dict[str, Any]:
    """Repeat qualification and export the exact reviewed 16-cycle packet."""
    config = _load_json(config_path)
    _require(sha256_file(config_path) == REVIEWED_BASE_CONFIG_SHA256,
             "base config differs from reviewed identity")
    cycles = _validate_config(config)
    expected_receipt = config["source"]["capability_receipt_sha256"]
    _require(sha256_file(capability_receipt_path) == expected_receipt,
             "A002 capability receipt identity mismatch")
    receipt = _load_json(capability_receipt_path)
    _require(receipt.get("audit_id") == config["source"]["capability_run_id"],
             "A002 capability run identity mismatch")
    _require(receipt.get("target_commit") == config["source"]["capability_code_commit"],
             "A002 capability code identity mismatch")

    frozen, hash_receipt, decode_receipt = _qualify_decode_and_freeze(
        run_root=run_root, context=context)
    _require(tuple(frozen["selected_cycles"]) == cycles, "recomputed selection drift")
    _require(frozen["growth_cycles"] == config["data"]["growth_cycles"],
             "recomputed growth group drift")
    _require(frozen["near_stagnant_cycles"] == config["data"]["near_stagnant_cycles"],
             "recomputed near-stagnant group drift")
    _require(frozen["normalisers"] == {
        "damage_increment": config["normalisers"]["damage_increment"],
        "history_increment": config["normalisers"]["history_increment"],
        "displacement": config["normalisers"]["displacement"],
    }, "recomputed normaliser drift")
    _require(frozen["D"] == config["data"]["detectable_growth_scale_D"],
             "recomputed detectable-growth scale drift")
    _require(frozen["near_stagnant_limit"] == config["data"]["near_stagnant_selection_limit"],
             "recomputed near-stagnant limit drift")
    _require(frozen["source_static_sha256"] == config["source"]["static_sha256"],
             "static identity drift")
    rows = load_state_index(run_root / "state_index.csv", context)
    transitions, endpoint_receipt = decode_stage0a_transitions(
        states_dir=run_root / "states", rows=rows, cycles=cycles,
        expected_nodes=context.expected_nodes, expected_elements=context.expected_elements,
        expected_gp=context.expected_gp,
    )
    static, static_receipt = decode_native_static(
        run_root / "static" / context.static_filename, context)
    arrays = {
        "cycles": np.asarray(cycles, dtype=np.int64),
        "path": np.asarray(config["data"]["prescribed_path"], dtype=np.float64),
        "d_pre": np.stack([pre.d_node for pre, _ in transitions]),
        "d_peak": np.stack([peak.d_node for _, peak in transitions]),
        "history_pre": np.stack([pre.history_gp for pre, _ in transitions]),
        "history_peak": np.stack([peak.history_gp for _, peak in transitions]),
        "u_peak": np.stack([peak.u_node for _, peak in transitions]),
        "xy": np.asarray(static["xy"]),
        "conn": np.asarray(static["conn"]),
        "shape": np.asarray(static["shape"]),
        "reference_derivative": np.asarray(static["reference_derivative"]),
        "gauss_weight": np.asarray(static["gauss_weight"]),
        "thickness": np.asarray([static["thickness"]], dtype=np.float64),
        "nodal_weight": np.asarray(static["nodal_weight"]),
        "gp_weight": np.asarray(static["gp_weight"]),
    }
    metadata = {
        "experiment_id": config["experiment_id"],
        "planned_run_id": config["planned_run_id"],
        "role": "development_only",
        "source_context_sha256": context.digest,
        "source_static_sha256": context.static_sha256,
        "source_capability_receipt_sha256": expected_receipt,
        "source_hash_verdict": hash_receipt["verdict"],
        "source_decode_verdict": decode_receipt["verdict"],
        "source_p1_verdict": frozen["verdict"],
        "selected_cycles": list(cycles),
        "growth_cycles": config["data"]["growth_cycles"],
        "near_stagnant_cycles": config["data"]["near_stagnant_cycles"],
        "detectable_growth_scale_D": frozen["D"],
        "near_stagnant_selection_limit": frozen["near_stagnant_limit"],
        "history_order": config["data"]["history_order"],
        "normalisers": config["normalisers"],
        "material": {"young": 1.0, "poisson": 0.3, "residual_stiffness": 0.0},
        "thickness": static["thickness"],
        "static_receipt": static_receipt,
        "endpoint_receipt": endpoint_receipt,
        "config_sha256": sha256_file(config_path),
    }
    return write_packet(output_dir=output_dir, arrays=arrays, metadata=metadata,
                        cycles=cycles, context=context)


def load_verified_packet(packet_dir: Path, *,
                         context: Stage0ACapabilityContext = S09_E008_CONTEXT
                         ) -> tuple[dict[str, np.ndarray], dict[str, Any], dict[str, Any]]:
    """Load a packet only after canonical manifest and every array hash pass."""
    packet_dir = packet_dir.resolve(strict=True)
    manifest_path = packet_dir / "manifest.json"
    identity_path = packet_dir / "packet_identity.json"
    raw_identity = identity_path.read_bytes()
    identity = json.loads(raw_identity)
    _require(raw_identity == canonical_json(identity), "packet identity is not canonical JSON")
    raw_manifest = manifest_path.read_bytes()
    _require(identity.get("schema_version") == SCHEMA, "packet identity schema mismatch")
    _require(sha256_bytes(raw_manifest) == identity.get("manifest_sha256"),
             "packet manifest hash mismatch")
    manifest = json.loads(raw_manifest)
    _require(raw_manifest == canonical_json(manifest), "packet manifest is not canonical JSON")
    _require(manifest.get("schema_version") == SCHEMA, "packet manifest schema mismatch")
    records = manifest.get("arrays", {})
    _require(set(records) == set(ARRAY_NAMES), "packet array manifest mismatch")
    arrays: dict[str, np.ndarray] = {}
    for name in ARRAY_NAMES:
        record = records[name]
        path = packet_dir / record["file"]
        _require(path.parent == packet_dir and path.name == f"{name}.npy" and not path.is_symlink(),
                 f"invalid packet path: {name}")
        _require(path.stat().st_size == record["bytes"] and sha256_file(path) == record["sha256"],
                 f"packet array identity mismatch: {name}")
        value = np.load(path, allow_pickle=False)
        _require(list(value.shape) == record["shape"] and value.dtype.str == record["dtype"],
                 f"packet array schema mismatch: {name}")
        _require(value.dtype.kind in "fiu" and
                 (value.dtype.kind != "f" or np.isfinite(value).all()),
                 f"invalid packet array values: {name}")
        arrays[name] = value
    metadata = manifest["metadata"]
    _validate_arrays(arrays, cycles=tuple(metadata["selected_cycles"]), context=context)
    _require(identity.get("manifest_bytes") == len(raw_manifest), "packet manifest byte count mismatch")
    _require(identity.get("array_count") == len(ARRAY_NAMES), "packet array count mismatch")
    return arrays, metadata, identity
