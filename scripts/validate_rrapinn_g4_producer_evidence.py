#!/usr/bin/env python3
"""Fail-closed validator for future G4 producer and external-runtime artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import torch


COMMON_START = 301
COMMON_END = 409
MAX_RUNTIME_RATIO = 3.0
FROZEN_RESTART_MANIFEST_SHA256 = "df581bb790e91660a5a4be735fc0f3e11c699f329b0f4ce05af36b31fa2c03e9"
RESIDUAL_KEYS = {
    "residual_u", "residual_v", "intensive", "dual_area",
    "interior_free_mask", "coordinates", "connectivity", "damage",
    "raw_step", "physical_cycle", "substep_index", "displacement", "scale",
}
SUMMARY_KEYS = {
    "mean", "p95", "p99", "cvar95", "cvar99",
    "worst_1pct_area_residual_mass_fraction",
    "worst_1pct_selected_area_fraction",
}
ARCHIVE_HISTORIES = {
    "E_el_vs_cycle.npy", "alpha_bar_vs_cycle.npy", "x_tip_alpha_vs_cycle.npy",
    "x_tip_vs_cycle.npy", "Kt_vs_cycle.npy", "time_vs_cycle.npy",
    "energy_gradient_terms_vs_cycle.npy",
}
BOUNDARY_TRACE_KEYS = {
    "schema", "raw_step", "physical_cycle", "substep_index",
    "substep_displacement", "qualifying_nodes", "boundary_nodes",
    "boundary_max_damage", "x_min_exclusive",
    "damage_threshold_exclusive", "minimum_nodes", "triggered",
    "criterion", "trigger_source",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact(record, base: Path, label: str) -> Path:
    if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
        raise ValueError(f"{label} must be a path/SHA256 artifact record")
    path = Path(record["path"])
    if not path.is_absolute():
        path = (base / path).resolve()
    if not path.is_file() or sha256(path) != record["sha256"]:
        raise ValueError(f"{label} is missing or its SHA256 does not match")
    return path


def _residual_export(record, base: Path, expected_step: int) -> None:
    if not isinstance(record, dict) or set(record) != {"receipt", "fields"}:
        raise ValueError("residual export must bind receipt and fields artifacts")
    receipt_path = _artifact(record["receipt"], base, "residual receipt")
    fields_path = _artifact(record["fields"], base, "residual fields")
    if receipt_path.parent != fields_path.parent:
        raise ValueError("residual receipt and fields must share one step directory")
    if {path.name for path in receipt_path.parent.iterdir()} != {"receipt.json", "fields.npz"}:
        raise ValueError("residual step directory must contain exactly receipt.json and fields.npz")
    receipt = _load_json(receipt_path)
    if (
        receipt.get("schema") != "rrapinn-true-mechanical-residual-v1"
        or receipt.get("state_timing") != "optimizer_post_pre_history_refresh"
        or int(receipt.get("raw_step", -1)) != expected_step
        or receipt.get("npz") != fields_path.name
        or receipt.get("npz_sha256") != sha256(fields_path)
        or set(receipt.get("summary", {})) != SUMMARY_KEYS
        or not all(math.isfinite(float(value)) for value in receipt["summary"].values())
    ):
        raise ValueError(f"invalid true residual receipt at step {expected_step}")
    with np.load(fields_path, allow_pickle=False) as fields:
        if set(fields.files) != RESIDUAL_KEYS or int(fields["raw_step"]) != expected_step:
            raise ValueError(f"residual field schema/step mismatch at step {expected_step}")
        for key in RESIDUAL_KEYS - {"connectivity", "interior_free_mask"}:
            if not np.all(np.isfinite(fields[key])):
                raise ValueError(f"non-finite residual field {key} at step {expected_step}")
        n_nodes = int(fields["coordinates"].shape[0])
        if (
            fields["coordinates"].shape != (n_nodes, 2)
            or any(fields[key].shape != (n_nodes,) for key in (
                "residual_u", "residual_v", "intensive", "dual_area",
                "interior_free_mask", "damage",
            ))
            or fields["connectivity"].ndim != 2
            or fields["connectivity"].shape[1] != 3
            or np.any(fields["connectivity"] < 0)
            or np.any(fields["connectivity"] >= n_nodes)
            or np.any(fields["dual_area"] <= 0)
            or fields["interior_free_mask"].dtype != np.dtype(bool)
            or not np.any(fields["interior_free_mask"])
            or int(fields["physical_cycle"]) != (76 if expected_step == 379 else 82)
            or int(fields["substep_index"]) != 3
            or not np.isclose(float(fields["displacement"]), 0.12)
            or float(fields["scale"]) <= 0.0
        ):
            raise ValueError(f"residual field geometry/state mismatch at step {expected_step}")


def _derive_archive_endpoint(arm, base: Path) -> int:
    endpoint_model = _artifact(arm.get("archive_model"), base, "archive endpoint model")
    endpoint_checkpoint = _artifact(
        arm.get("archive_checkpoint"), base, "archive endpoint checkpoint"
    )
    model_match = re.fullmatch(r"trained_1NN_(\d+)\.pt", endpoint_model.name)
    checkpoint_match = re.fullmatch(r"checkpoint_step_(\d+)\.pt", endpoint_checkpoint.name)
    if not model_match or not checkpoint_match:
        raise ValueError("archive endpoint model/checkpoint names are invalid")
    model_step = int(model_match.group(1))
    checkpoint_step = int(checkpoint_match.group(1))
    model_state = torch.load(endpoint_model, map_location="cpu", weights_only=True)
    checkpoint_state = torch.load(
        endpoint_checkpoint, map_location="cpu", weights_only=False
    )
    if not isinstance(model_state, dict) or not all(
        torch.is_tensor(value) and bool(torch.all(torch.isfinite(value)))
        for value in model_state.values()
    ):
        raise ValueError("archive endpoint model does not decode to finite tensors")
    required_checkpoint = {"hist_alpha", "hist_fat", "psi_plus_prev", "psi_history_elem"}
    if not isinstance(checkpoint_state, dict) or not required_checkpoint.issubset(checkpoint_state):
        raise ValueError("archive endpoint checkpoint is missing fatigue state")
    if not all(
        torch.is_tensor(checkpoint_state[key])
        and bool(torch.all(torch.isfinite(checkpoint_state[key])))
        for key in required_checkpoint
    ):
        raise ValueError("archive endpoint checkpoint contains non-finite fatigue state")
    records = arm.get("archive_histories", {})
    if set(records) != ARCHIVE_HISTORIES:
        raise ValueError("archive endpoint histories are incomplete")
    derived_steps = set()
    for name, record in records.items():
        path = _artifact(record, base, f"archive history {name}")
        array = np.load(path, allow_pickle=False)
        if array.ndim < 1 or array.shape[0] == 0:
            raise ValueError(f"archive history has invalid shape: {name}")
        if np.any(np.isinf(array)) or (name != "Kt_vs_cycle.npy" and np.any(np.isnan(array))):
            raise ValueError(f"archive history violates finite policy: {name}")
        derived_steps.add(int(array.shape[0]) - 1)
    if derived_steps != {model_step} or checkpoint_step != model_step:
        raise ValueError("archive endpoint disagrees across model/checkpoint/histories")
    return model_step


def _event_artifacts(arm, base: Path, archive_endpoint: int) -> None:
    first_record = arm.get("first_detect_receipt")
    censor_record = arm.get("right_censor_receipt")
    if bool(first_record) == bool(censor_record):
        raise ValueError("producer evidence must contain exactly one first-detect or censor receipt")
    trace_path = _artifact(arm.get("boundary_trace"), base, "boundary trace")
    trace_rows = [json.loads(line) for line in trace_path.read_text().splitlines() if line.strip()]
    if not trace_rows or any(
        set(row) != BOUNDARY_TRACE_KEYS
        or row.get("schema") != "boundary-first-detect-v1"
        or row.get("trigger_source") != "boundary_only"
        for row in trace_rows
    ):
        raise ValueError("boundary trace is empty or has an invalid schema")
    trace_steps = [int(row.get("raw_step", -1)) for row in trace_rows]
    if trace_steps != list(range(COMMON_START, archive_endpoint + 1)):
        raise ValueError("boundary trace is not complete through the archive endpoint")
    displacements = [0.03, 0.06, 0.09, 0.12, 0.0]
    for row in trace_rows:
        adjusted = int(row["raw_step"]) - 1
        substep = adjusted % 5
        if (
            int(row.get("physical_cycle", -1)) != adjusted // 5 + 1
            or int(row.get("substep_index", -1)) != substep
            or not np.isclose(float(row.get("substep_displacement", float("nan"))), displacements[substep])
        ):
            raise ValueError("boundary trace contains an invalid Hard5 state mapping")
    if first_record:
        receipt = _load_json(_artifact(first_record, base, "first-detect receipt"))
        if receipt.get("trigger_source") != "boundary_only":
            raise ValueError("headline first-detect receipt is not boundary-only")
        matches = [row for row in trace_rows if int(row["raw_step"]) == int(receipt["raw_step"])]
        first_trigger = next(
            (int(row["raw_step"]) for row in trace_rows if row.get("triggered") is True),
            None,
        )
        if (
            not matches or matches[0].get("triggered") is not True
            or first_trigger != int(receipt["raw_step"])
            or archive_endpoint < max(COMMON_END, int(receipt["raw_step"]))
        ):
            raise ValueError("first-detect receipt is not backed by the boundary trace")
        expected_receipt = dict(next(row for row in trace_rows if int(row["raw_step"]) == first_trigger))
        expected_receipt.pop("triggered", None)
        if receipt != expected_receipt:
            raise ValueError("first-detect receipt fields do not exactly match the first trigger row")
    else:
        receipt = _load_json(_artifact(censor_record, base, "right-censor receipt"))
        if (
            receipt.get("schema") != "rrapinn-g4-right-censor-v1"
            or receipt.get("boundary_triggered") is not False
            or int(receipt.get("physical_cycle", -1)) != 92
            or int(receipt.get("last_raw_step", -1)) != 460
            or archive_endpoint != 460
            or any(row.get("triggered") is True for row in trace_rows)
        ):
            raise ValueError("right-censor receipt does not prove no event through c92")


def validate_producer_evidence(control_path, candidate_path, output_path=None):
    manifest_paths = [Path(control_path).resolve(), Path(candidate_path).resolve()]
    arms = [_load_json(path) for path in manifest_paths]
    if any(arm.get("schema") != "rrapinn-g4-producer-evidence-v2" for arm in arms):
        raise ValueError("producer evidence schema mismatch")
    opaque_ids = [arm.get("opaque_arm_id") for arm in arms]
    if len(set(opaque_ids)) != 2 or any(value in ("A", "B", "control", "candidate") for value in opaque_ids):
        raise ValueError("producer arm IDs must be two distinct opaque values")
    if {arm.get("risk_intervention") for arm in arms} != {"absent", "ME85_frozen"}:
        raise ValueError("producer pair does not contain the frozen absent/ME85 interventions")

    runtime_by_mode = {}
    common_hashes = set()
    for arm, manifest_path in zip(arms, manifest_paths):
        base = manifest_path.parent
        if arm.get("development_case") != "U0.12" or arm.get("held_out_amplitudes_accessed") is not False:
            raise ValueError("producer evidence is not isolated to U0.12")
        restart = _artifact(arm.get("restart_manifest"), base, "restart manifest")
        if sha256(restart) != FROZEN_RESTART_MANIFEST_SHA256:
            raise ValueError("producer did not use the frozen restart manifest")
        common = _artifact(arm.get("common_config"), base, "common config")
        common_payload = _load_json(common)
        if common_payload != {
            "schema": "rrapinn-g4-common-config-v1",
            "development_case": "U0.12",
            "restart_manifest_sha256": FROZEN_RESTART_MANIFEST_SHA256,
            "raw_step_start": 301,
            "raw_step_end_for_common_metrics": 409,
            "true_residual_export_steps": [379, 409],
            "boundary_first_detect_receipt": True,
            "hard_stop_physical_cycle": 92,
            "minimum_archive_raw_step": 409,
            "held_out_amplitudes_accessed": False,
        }:
            raise ValueError("common config schema mismatch")
        common_hashes.add(sha256(common))
        exports = arm.get("true_residual_exports", {})
        if set(exports) != {"379", "409"}:
            raise ValueError("true residual exports must exist at exactly steps 379 and 409")
        for step in (379, 409):
            _residual_export(exports[str(step)], base, step)
        endpoint = _derive_archive_endpoint(arm, base)
        _event_artifacts(arm, base, endpoint)
        if arm["risk_intervention"] == "absent":
            replay = _load_json(_artifact(arm.get("a_replay_receipt"), base, "A replay receipt"))
            reference_dir = (base / arm.get("a_replay_reference_best_models", "")).resolve()
            candidate_dir = (base / arm.get("a_replay_candidate_best_models", "")).resolve()
            if not reference_dir.is_dir() or not candidate_dir.is_dir():
                raise ValueError("A replay input directories are missing")
            try:
                from scripts.validate_rrapinn_g4_a_replay import validate_replay
            except ModuleNotFoundError:
                from validate_rrapinn_g4_a_replay import validate_replay
            recomputed_replay = validate_replay(reference_dir, candidate_dir)
            if replay != recomputed_replay:
                raise ValueError("control replay sentinel did not pass")
        runtime = _load_json(_artifact(arm.get("runtime_receipt"), base, "runtime receipt"))
        if (
            runtime.get("schema") != "rrapinn-g4-external-runtime-v1"
            or runtime.get("observer") != "external_launcher"
            or [runtime.get("common_raw_step_start"), runtime.get("common_raw_step_end")] != [COMMON_START, COMMON_END]
        ):
            raise ValueError("runtime receipt provenance or interval mismatch")
        wall = float(runtime.get("wall_time_per_step_seconds", float("nan")))
        memory = float(runtime.get("peak_memory_bytes", float("nan")))
        expected_runtime_keys = {str(step) for step in range(COMMON_START, COMMON_END + 1)}
        wall_by_step = runtime.get("wall_time_seconds_by_raw_step", {})
        memory_by_step = runtime.get("peak_memory_bytes_by_raw_step", {})
        if set(wall_by_step) != expected_runtime_keys or set(memory_by_step) != expected_runtime_keys:
            raise ValueError("runtime receipt lacks complete per-step external samples")
        wall_values = [float(wall_by_step[str(step)]) for step in range(COMMON_START, COMMON_END + 1)]
        memory_values = [float(memory_by_step[str(step)]) for step in range(COMMON_START, COMMON_END + 1)]
        if not all(math.isfinite(value) and value > 0 for value in wall_values + memory_values):
            raise ValueError("runtime receipt contains invalid wall-time or memory")
        if not np.isclose(wall, np.mean(wall_values)) or not np.isclose(memory, np.max(memory_values)):
            raise ValueError("runtime aggregate does not match its per-step samples")
        runtime_by_mode[arm["risk_intervention"]] = (wall, memory)
    if len(common_hashes) != 1:
        raise ValueError("normalized common config artifacts differ between arms")
    ratio_wall = runtime_by_mode["ME85_frozen"][0] / runtime_by_mode["absent"][0]
    ratio_memory = runtime_by_mode["ME85_frozen"][1] / runtime_by_mode["absent"][1]
    if ratio_wall > MAX_RUNTIME_RATIO or ratio_memory > MAX_RUNTIME_RATIO:
        raise ValueError("candidate exceeds the frozen 3x runtime or memory gate")
    payload = {
        "schema": "rrapinn-g4-producer-validation-v2",
        "status": "PASS_PRODUCER_EVIDENCE_CONTRACT",
        "opaque_arm_ids": opaque_ids,
        "wall_time_ratio": ratio_wall,
        "peak_memory_ratio": ratio_memory,
        "claim_boundary": "Evidence-contract pass only; scientific metrics remain sealed and separate.",
    }
    if output_path is not None:
        with Path(output_path).open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm-1", type=Path, required=True)
    ap.add_argument("--arm-2", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    print(json.dumps(validate_producer_evidence(args.arm_1, args.arm_2, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
