#!/usr/bin/env python3
"""Fail-closed validator for future G4 producer and external-runtime artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
from rrapinn_producer_observer import (  # noqa: E402
    command_sha256,
    path_policy_sha256,
    scan_trace_forbidden,
    trace_has_cwd_change,
)


COMMON_START = 301
COMMON_END = 409
MAX_RUNTIME_RATIO = 3.0
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
ELEMENT_REQUIRED_KEYS = {
    "alpha_elem", "hist_fat_elem", "f_fatigue_elem", "psi_raw_elem",
    "psi_active_elem", "elem_x", "elem_y", "raw_step", "physical_cycle",
    "substep_index", "displacement", "state_label", "state_timing",
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


def _element_export(record, base: Path, expected_step: int) -> None:
    if not isinstance(record, dict) or set(record) != {"receipt", "fields"}:
        raise ValueError("element export must bind receipt and fields artifacts")
    receipt_path = _artifact(record["receipt"], base, "element admissibility receipt")
    fields_path = _artifact(record["fields"], base, "element fields")
    receipt = _load_json(receipt_path)
    expected_cycle = 76 if expected_step == 379 else 82
    if (
        receipt.get("schema") != "pidl-element-alpha-admissibility-v1"
        or receipt.get("status") != "PASS"
        or receipt.get("policy") != "strict"
        or receipt.get("finite") is not True
        or int(receipt.get("nonfinite_count", -1)) != 0
        or int(receipt.get("raw_step", -1)) != expected_step
        or int(receipt.get("physical_cycle", -1)) != expected_cycle
        or int(receipt.get("substep_index", -1)) != 3
        or not np.isclose(float(receipt.get("displacement", float("nan"))), 0.12)
        or receipt.get("state_label") != f"c{expected_cycle}_substep_3"
        or receipt.get("state_timing") != "post_history_refresh_cycle_end"
        or int(receipt.get("below_zero_count", -1)) != 0
        or int(receipt.get("above_one_count", -1)) != 0
        or receipt.get("npz") != fields_path.name
        or receipt.get("npz_sha256") != sha256(fields_path)
    ):
        raise ValueError(f"element alpha-admissibility receipt failed at step {expected_step}")
    with np.load(fields_path, allow_pickle=False) as fields:
        if not ELEMENT_REQUIRED_KEYS.issubset(fields.files):
            raise ValueError(f"element field schema mismatch at step {expected_step}")
        alpha = np.asarray(fields["alpha_elem"], dtype=np.float64).reshape(-1)
        aligned = {
            name: np.asarray(fields[name], dtype=np.float64).reshape(-1)
            for name in (
                "hist_fat_elem", "f_fatigue_elem", "psi_raw_elem",
                "psi_active_elem", "elem_x", "elem_y",
            )
        }
        if (
            alpha.size == 0 or not np.all(np.isfinite(alpha))
            or any(values.size != alpha.size for values in aligned.values())
            or any(not np.all(np.isfinite(values)) for values in aligned.values())
            or np.any(alpha < 0.0) or np.any(alpha > 1.0)
            or np.any(aligned["hist_fat_elem"] < 0.0)
            or np.any(aligned["f_fatigue_elem"] < 0.0)
            or np.any(aligned["f_fatigue_elem"] > 1.0)
            or np.any(aligned["psi_raw_elem"] < 0.0)
            or np.any(aligned["psi_active_elem"] < 0.0)
            or int(np.asarray(fields["raw_step"]).reshape(-1)[0]) != expected_step
            or int(np.asarray(fields["physical_cycle"]).reshape(-1)[0]) != expected_cycle
            or int(np.asarray(fields["substep_index"]).reshape(-1)[0]) != 3
            or not np.isclose(
                float(np.asarray(fields["displacement"]).reshape(-1)[0]), 0.12
            )
            or str(np.asarray(fields["state_label"]).reshape(-1)[0])
            != f"c{expected_cycle}_substep_3"
            or str(np.asarray(fields["state_timing"]).reshape(-1)[0])
            != "post_history_refresh_cycle_end"
        ):
            raise ValueError(f"element field state/range mismatch at step {expected_step}")


def _path_access_receipt(record, base: Path) -> tuple[dict, str]:
    receipt_path = _artifact(record, base, "host path-access receipt")
    receipt = _load_json(receipt_path)
    raw = receipt.get("raw_trace")
    if not isinstance(raw, dict) or set(raw) != {"path", "sha256"}:
        raise ValueError("path-access receipt must bind its raw strace ledger")
    trace_path = _artifact(raw, receipt_path.parent, "raw path-access trace")
    forbidden = receipt.get("forbidden_path_prefixes")
    if (
        receipt.get("schema") != "rrapinn-host-path-access-v1"
        or receipt.get("observer") != "strace_file_syscalls_follow_forks"
        or receipt.get("status") != "PASS"
        or receipt.get("follow_forks") is not True
        or receipt.get("fd_paths_decoded") is not True
        or int(receipt.get("producer_returncode", -1)) != 0
        or receipt.get("observer_error") is not None
        or receipt.get("matched_forbidden_paths") != []
        or not isinstance(forbidden, list) or len(forbidden) < 2
        or not all(isinstance(value, str) for value in forbidden)
        or not any("0.11" in value for value in forbidden)
        or not any("0.13" in value for value in forbidden)
        or receipt.get("cwd_change_syscalls_observed") is not False
        or receipt.get("path_policy_sha256")
        != path_policy_sha256([Path(value) for value in forbidden])
    ):
        raise ValueError("host path-access receipt schema/status mismatch")
    recomputed = scan_trace_forbidden(
        trace_path,
        cwd=Path(receipt.get("producer_cwd", "")),
        forbidden_prefixes=[Path(value) for value in forbidden],
    )
    if recomputed:
        raise ValueError("raw host ledger contains forbidden held-out access")
    if trace_has_cwd_change(trace_path):
        raise ValueError("raw host ledger contains unsupported cwd changes")
    command_hash = receipt.get("command_sha256")
    command = receipt.get("command")
    if (
        not isinstance(command, list)
        or not all(isinstance(value, str) for value in command)
        or command_sha256(command) != command_hash
        or not isinstance(command_hash, str)
        or not re.fullmatch(r"[0-9a-f]{64}", command_hash)
    ):
        raise ValueError("path-access receipt command hash is invalid")
    return receipt, command_hash


def _frozen_command_provenance(
    arm: dict, path_receipt: dict, runtime: dict, restart_sha: str,
) -> None:
    command = path_receipt["command"]
    if runtime.get("command") != command:
        raise ValueError("runtime/path receipts do not contain one exact command")
    try:
        restart_index = command.index("--resume-bundle") + 1
        restart_bundle = Path(command[restart_index])
    except (ValueError, IndexError) as exc:
        raise ValueError("producer command does not declare its restart bundle") from exc
    if not restart_bundle.is_absolute():
        raise ValueError("producer restart bundle path must be absolute")
    from scripts.run_rrapinn_g4_arm import frozen_command
    expected = frozen_command(
        repo=Path("/unused"),
        arm="A_absent" if arm["risk_intervention"] == "absent" else "B_on",
        restart_bundle=restart_bundle,
        producer_head=arm["producer_head"],
        restart_manifest_sha256=restart_sha,
    )
    if command != expected:
        raise ValueError("producer command differs from the lock-qualified frozen command")


def _launch_provenance(
    arm: dict, base: Path, restart_sha256: str, path_policy_hash: str,
) -> tuple[str, str]:
    lock_path = _artifact(arm.get("prelaunch_lock"), base, "prelaunch lock")
    authorization_path = _artifact(
        arm.get("authorization_receipt"), base, "authorization receipt"
    )
    lock = _load_json(lock_path)
    producer_head = arm.get("producer_head")
    producer = lock.get("producer_contract", {})
    locked_forbidden = producer.get("forbidden_path_prefixes")
    if (
        lock.get("schema") != "rrapinn-g4-prelaunch-lock-v4"
        or lock.get("status")
        != "READY_FOR_INDEPENDENT_GATE_TRAINING_UNAUTHORIZED"
        or lock.get("training_authorized") is not False
        or lock.get("development_case") != "U0.12"
        or lock.get("integration_commit") != producer_head
        or not isinstance(producer_head, str)
        or not re.fullmatch(r"[0-9a-f]{40}", producer_head)
        or producer.get("restart_manifest_sha256") != restart_sha256
        or producer.get("alpha_enforcement_scope")
        != "export_admissibility_only"
        or producer.get("model_decoder_changed") is not False
        or producer.get("smoke_scientific_outputs_decisional") is not False
        or not isinstance(locked_forbidden, dict)
        or set(locked_forbidden) != {"U0.11", "U0.13"}
        or not all(isinstance(value, str) for value in locked_forbidden.values())
        or not all(Path(value).is_absolute() for value in locked_forbidden.values())
        or path_policy_sha256(
            [Path(locked_forbidden[label]) for label in ("U0.11", "U0.13")]
        )
        != path_policy_hash
        or producer.get("path_policy_sha256") != path_policy_hash
        or producer.get("heldout_access_authorized") is not False
    ):
        raise ValueError("producer evidence is not bound to the qualified v4 lock")
    authorization = _load_json(authorization_path)
    if authorization != {
        "schema": "rrapinn-g4-user-authorization-v1",
        "authorized": True,
        "scope": "g4-u012-c60-two-arm-pilot",
        "development_case": "U0.12",
        "producer_head": producer_head,
        "prelaunch_lock_sha256": sha256(lock_path),
        "authorized_arms": ["A_absent", "B_on"],
        "heldout_access_authorized": False,
    }:
        raise ValueError("producer authorization is not bound to the v4 lock/head")
    return sha256(lock_path), producer_head


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
    if any(arm.get("schema") != "rrapinn-g4-producer-evidence-v4" for arm in arms):
        raise ValueError("producer evidence schema mismatch")
    opaque_ids = [arm.get("opaque_arm_id") for arm in arms]
    if len(set(opaque_ids)) != 2 or any(value in ("A", "B", "control", "candidate") for value in opaque_ids):
        raise ValueError("producer arm IDs must be two distinct opaque values")
    if {arm.get("risk_intervention") for arm in arms} != {"absent", "ME85_frozen"}:
        raise ValueError("producer pair does not contain the frozen absent/ME85 interventions")

    runtime_by_mode = {}
    common_hashes = set()
    lock_hashes = set()
    producer_heads = set()
    path_policy_hashes = set()
    for arm, manifest_path in zip(arms, manifest_paths):
        base = manifest_path.parent
        if arm.get("development_case") != "U0.12" or arm.get("held_out_amplitudes_accessed") is not False:
            raise ValueError("producer evidence is not isolated to U0.12")
        restart = _artifact(arm.get("restart_manifest"), base, "restart manifest")
        restart_sha = sha256(restart)
        common = _artifact(arm.get("common_config"), base, "common config")
        common_payload = _load_json(common)
        if common_payload != {
            "schema": "rrapinn-g4-common-config-v1",
            "development_case": "U0.12",
            "restart_manifest_sha256": restart_sha,
            "raw_step_start": 301,
            "raw_step_end_for_common_metrics": 409,
            "true_residual_export_steps": [379, 409],
            "element_field_export_steps": [379, 409],
            "strict_element_state_metadata": True,
            "strict_alpha_admissibility": True,
            "boundary_first_detect_receipt": True,
            "host_path_access_ledger_required": True,
            "external_step_runtime_and_peak_memory_required": True,
            "scientific_outputs_decisional": False,
            "candidate_promotion_authorized": False,
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
        element_exports = arm.get("element_field_exports", {})
        if set(element_exports) != {"379", "409"}:
            raise ValueError("element field exports must exist at exactly steps 379 and 409")
        for step in (379, 409):
            _element_export(element_exports[str(step)], base, step)
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
        path_receipt, path_command_hash = _path_access_receipt(
            arm.get("path_access_receipt"), base,
        )
        lock_hash, producer_head = _launch_provenance(
            arm, base, restart_sha, path_receipt["path_policy_sha256"]
        )
        lock_hashes.add(lock_hash)
        producer_heads.add(producer_head)
        path_policy_hashes.add(path_receipt["path_policy_sha256"])
        runtime = _load_json(_artifact(arm.get("runtime_receipt"), base, "runtime receipt"))
        _frozen_command_provenance(arm, path_receipt, runtime, restart_sha)
        if (
            runtime.get("schema") != "rrapinn-g4-external-runtime-v2"
            or runtime.get("observer") != "external_launcher_strace_nvidia_smi"
            or runtime.get("status") != "PASS"
            or runtime.get("command_sha256") != path_command_hash
            or runtime.get("path_policy_sha256")
            != path_receipt.get("path_policy_sha256")
            or int(runtime.get("producer_returncode", -1)) != 0
            or runtime.get("observer_error") is not None
            or runtime.get("missing_wall_steps") != []
            or runtime.get("missing_peak_memory_steps") != []
            or not np.isclose(float(runtime.get("sample_interval_seconds", float("nan"))), 0.25)
            or runtime.get("memory_metric")
            != "sampled_descendant_process_max_bytes"
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
    if len(lock_hashes) != 1 or len(producer_heads) != 1 or len(path_policy_hashes) != 1:
        raise ValueError("producer arms do not share one lock/head/path policy")
    ratio_wall = runtime_by_mode["ME85_frozen"][0] / runtime_by_mode["absent"][0]
    ratio_memory = runtime_by_mode["ME85_frozen"][1] / runtime_by_mode["absent"][1]
    if ratio_wall > MAX_RUNTIME_RATIO or ratio_memory > MAX_RUNTIME_RATIO:
        raise ValueError("candidate exceeds the frozen 3x runtime or memory gate")
    payload = {
        "schema": "rrapinn-g4-producer-validation-v3",
        "status": "PASS_PRODUCER_EVIDENCE_CONTRACT",
        "opaque_arm_ids": opaque_ids,
        "wall_time_ratio": ratio_wall,
        "peak_memory_ratio": ratio_memory,
        "scientific_outputs_decisional": False,
        "candidate_promotion_authorized": False,
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
