#!/usr/bin/env python3
"""E021 three-state coordinate screen; strict numerical admission derived from E020."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_s04_e021_coordinate_screen import (  # noqa: E402
    ALLOCATIONS,
    BATCH_NODES,
    DAMAGE_THRESHOLD,
    EXPECTED,
    MONITOR_STEPS,
    PROTOCOL_REVISION,
    SAMPLE_SEED_OFFSET,
    SEEDS,
    STEPS,
    US,
    validate_reference,
)

from s04_e018_global_local import anchor_component_geometry
from s04_e019_frozen_residual import (
    ARMS,
    PARAMETER_COUNT,
    RESIDUAL_PARAMETER_COUNT,
    build_model,
    state_digest,
)
from run_s04_e021_coordinate_screen import (
    admit_backbone,
    BACKBONE_LOCKS,
    support_diagnostics,
    predict_in_chunks,
    final_metrics,
)

from s04_e021_screen import (
    CONTROL_LOCKS,
    admit_control,
    check_pair_identity,
    check_schedule_identity,
    PROTOCOL_REVISION,
    check_runtime_identity,
    MAP_LOCKS,
    admit_coordinate_map,
    build_candidate,
    validate_coordinate_buffers,
    native_replay,
)

ARMS = ("localized",)


def validate_schedule_and_pair(path):
    record = json.loads(path.read_text())
    checkpoint = torch.load(
        path.parent / "final_step_10000.pt", map_location="cpu", weights_only=True
    )
    receipt = json.loads((path.parent / "RUN_RECEIPT.json").read_text())
    lr_path = path.parent / "learning_rates.npy"
    if receipt.get("gpu") != record.get("gpu"):
        raise ValueError("receipt GPU/runtime mismatch")
    check_runtime_identity(
        record["state"],
        {
            **{
                k: record[k]
                for k in ("torch_version", "numpy_version", "cuda_version", "gpu")
            },
            **{
                k: receipt[k]
                for k in ("hostname", "cuda_visible_devices", "cublas_workspace_config")
            },
        },
    )
    rates = np.load(lr_path, allow_pickle=False)
    expected_path = path.parent / "expected_learning_rates.npy"
    expected = np.load(expected_path, allow_pickle=False)
    check_schedule_identity(record.get("lr_schedule"), expected)
    if not np.array_equal(rates, expected):
        raise ValueError("actual LR differs from before-update replay")
    mapping_path = path.parent / "coordinate_map.json"
    mapping = json.loads(mapping_path.read_text())
    locked = MAP_LOCKS[record["state"]]["mapping"]
    if json.dumps(mapping, sort_keys=True, allow_nan=False) != json.dumps(
        locked, sort_keys=True, allow_nan=False
    ):
        raise ValueError("saved coordinate mapping differs from locked rule")
    for asset in (record, checkpoint, receipt):
        if asset.get("paired_control_lock") != CONTROL_LOCKS[record["state"]]:
            raise ValueError("paired historical identity mismatch")
        check_schedule_identity(asset.get("lr_schedule"), rates)
        if asset.get("learning_rates_sha256") != sha256(lr_path):
            raise ValueError("actual LR file identity mismatch")
        if asset.get("expected_learning_rates_sha256") != sha256(expected_path):
            raise ValueError("expected native replay file identity mismatch")
        if asset.get("coordinate_map_sha256") != sha256(mapping_path):
            raise ValueError("coordinate map file identity mismatch")
        if json.dumps(
            asset.get("coordinate_mapping"), sort_keys=True, allow_nan=False
        ) != json.dumps(locked, sort_keys=True, allow_nan=False):
            raise ValueError("coordinate mapping envelope mismatch")
        if asset.get("pre_update_sha256") != sha256(path.parent / "PRE_UPDATE.json"):
            raise ValueError("pre-update file identity mismatch")


def validate_pre_update(path, expected_commit, reference_data):
    from datetime import datetime

    record = json.loads(path.read_text())
    receipt = json.loads((path.parent / "RUN_RECEIPT.json").read_text())
    pre = json.loads((path.parent / "PRE_UPDATE.json").read_text())
    if any(receipt.get(k) != record.get(k) for k in ("started_utc", "finished_utc")):
        raise ValueError("receipt/metrics timing mismatch")
    data = reference_data[record["state"]]
    expected = dict(
        protocol_revision=PROTOCOL_REVISION,
        state=record["state"],
        seed=7,
        alpha="0.7",
        arm="localized",
        run_id=receipt["run_id"],
        code_commit=expected_commit,
        reference_sha256=record["reference_sha256"],
        backbone_digest=data["base_digest"],
        initial_residual_digest=data["initial_residual_digest"],
        initial_model_digest=data["initial_coordinate_model_digest"],
        coordinate_mapping=data["coordinate_mapping"],
        coordinate_map_sha256=record["coordinate_map_sha256"],
        expected_learning_rates_sha256=record["expected_learning_rates_sha256"],
        lr_schedule=record["lr_schedule"],
        runtime=CONTROL_LOCKS[record["state"]]["runtime"],
    )
    for key, value in expected.items():
        if json.dumps(pre.get(key), sort_keys=True, allow_nan=False) != json.dumps(
            value, sort_keys=True, allow_nan=False
        ):
            raise ValueError(f"pre-update identity mismatch: {key}")
    if (
        type(pre.get("new_optimizer_steps")) is not int
        or pre["new_optimizer_steps"] != 0
    ):
        raise ValueError("pre-update must precede all candidate steps")
    if strict_bool(pre.get("dirty"), "pre-update dirty") is not False:
        raise ValueError("pre-update source dirty")
    timestamps = [
        datetime.fromisoformat(x.replace("Z", "+00:00"))
        for x in (pre["created_utc"], record["started_utc"], record["finished_utc"])
    ]
    if (
        any(t.tzinfo is None for t in timestamps)
        or not timestamps[0] <= timestamps[1] <= timestamps[2]
    ):
        raise ValueError("invalid pre-update/start/finish chronology")
    trace = json.loads((path.parent / "monitoring.json").read_text())
    for entry in trace:
        step = entry["step"]
        used = native_replay()[step - 1] if step else None
        next_lr = native_replay()[step] if step < 10000 else None
        if entry.get("lr_used") != used or entry.get("lr_next") != next_lr:
            raise ValueError("passive actual LR trace mismatch")


THRESHOLDS = {
    "essential_bc_max_abs_error": 1e-12,
    "displacement_mass_rms_over_abs_Us": 1e-3,
    "strain_relative_l2": 1e-2,
    "predicted_rho_u": 1e-3,
}
GATE_KEYS = {
    "essential_bc_max_abs_error": "gate_essential_bc",
    "displacement_mass_rms_over_abs_Us": "gate_displacement_fit",
    "strain_relative_l2": "gate_strain_fit",
    "predicted_rho_u": "gate_rho_u",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def strict_bool(value, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a JSON boolean")
    return value


def finite_number(value, label: str) -> float:
    if type(value) not in (int, float) or isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


def geometry_matches(actual, expected) -> bool:
    if isinstance(expected, dict):
        return (
            isinstance(actual, dict)
            and set(actual) == set(expected)
            and all(geometry_matches(actual[k], v) for k, v in expected.items())
        )
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(geometry_matches(a, b) for a, b in zip(actual, expected))
        )
    if type(expected) in (int, float):
        return (
            type(actual) in (int, float)
            and math.isfinite(float(actual))
            and math.isclose(actual, expected, rel_tol=0, abs_tol=1e-14)
        )
    return type(actual) is type(expected) and actual == expected


def validate_common_record(
    path: Path, expected_commit: str, reference_data: dict
) -> dict:
    record = json.loads(path.read_text(encoding="utf-8"))
    state, seed = record.get("state"), record.get("seed")
    arm = record.get("arm")
    if arm not in ARMS:
        raise ValueError("unexpected representation arm")
    alpha = record.get("alpha")
    if alpha not in ALLOCATIONS:
        raise ValueError("unexpected sampling alpha")
    n_damage, n_background = ALLOCATIONS[alpha]
    pair = (state, seed, alpha)
    if state not in EXPECTED or seed not in SEEDS:
        raise ValueError(f"unexpected state-seed pair {pair}")
    if record.get("protocol_revision") != PROTOCOL_REVISION:
        raise ValueError("protocol mismatch")
    if (
        record.get("status") != "COMPLETED"
        or strict_bool(record.get("training"), "training") is not True
    ):
        raise ValueError("run is not a completed training run")
    if record.get("reference_sha256") != EXPECTED[state]:
        raise ValueError("reference identity mismatch")
    if record.get("reference_sha256_after") != EXPECTED[state]:
        raise ValueError("reference before/after identity mismatch")
    if record.get("steps") != STEPS or record.get("batch_nodes") != BATCH_NODES:
        raise ValueError("training budget mismatch")
    final_lr = finite_number(record.get("final_scheduler_lr"), "final_scheduler_lr")
    if not math.isclose(final_lr, 1e-5, rel_tol=0.0, abs_tol=1e-15):
        raise ValueError("final scheduler learning rate mismatch")

    run_dir = path.parent
    checkpoint = run_dir / "final_step_10000.pt"
    prediction = run_dir / "prediction.npz"
    monitoring = run_dir / "monitoring.json"
    receipt_path = run_dir / "RUN_RECEIPT.json"
    for asset in (checkpoint, prediction, monitoring, receipt_path):
        if not asset.is_file():
            raise ValueError(f"missing required asset {asset.name}")
    if sha256(checkpoint) != record.get("checkpoint_sha256"):
        raise ValueError("checkpoint SHA mismatch")
    if sha256(prediction) != record.get("prediction_sha256"):
        raise ValueError("prediction SHA mismatch")
    if sha256(monitoring) != record.get("monitoring_sha256"):
        raise ValueError("monitoring SHA mismatch")
    checkpoint_data = torch.load(checkpoint, map_location="cpu", weights_only=True)
    expected_checkpoint = {
        "protocol_revision": PROTOCOL_REVISION,
        "state": state,
        "seed": seed,
        "alpha": alpha,
        "arm": arm,
        "step": STEPS,
    }
    if any(
        checkpoint_data.get(key) != value for key, value in expected_checkpoint.items()
    ):
        raise ValueError("checkpoint final-step identity mismatch")
    expected_sampler = {
        "damage_threshold": DAMAGE_THRESHOLD,
        "n_damage": n_damage,
        "n_background": n_background,
        "sample_seed": seed + SAMPLE_SEED_OFFSET,
        "order": "damage_then_background_no_shuffle",
    }
    if checkpoint_data.get("sampler") != expected_sampler:
        raise ValueError("checkpoint sampler identity mismatch")
    if not isinstance(checkpoint_data.get("model_state_dict"), dict):
        raise ValueError("checkpoint lacks model_state_dict")
    with np.load(prediction) as pred:
        if set(pred.files) != {"uv"} or pred["uv"].shape != (86_756, 2):
            raise ValueError("prediction schema mismatch")
        if not np.isfinite(pred["uv"]).all():
            raise ValueError("prediction contains nonfinite values")
        saved_uv = pred["uv"].copy()

    trace = json.loads(monitoring.read_text(encoding="utf-8"))
    if not isinstance(trace, list) or [entry.get("step") for entry in trace] != list(
        MONITOR_STEPS
    ):
        raise ValueError("monitoring steps mismatch")
    for entry in trace:
        for key in (
            "full_field_loss",
            "displacement_mass_rms_over_abs_Us",
            "active_contribution",
            "background_contribution",
        ):
            finite_number(entry.get(key), f"monitoring.{key}")
        if not math.isclose(
            entry["full_field_loss"],
            entry["active_contribution"] + entry["background_contribution"],
            rel_tol=1e-12,
            abs_tol=1e-15,
        ):
            raise ValueError("monitoring contribution mismatch")
        if not math.isclose(
            entry["displacement_mass_rms_over_abs_Us"] ** 2,
            entry["full_field_loss"],
            rel_tol=1e-12,
            abs_tol=1e-15,
        ):
            raise ValueError("monitoring RMS mismatch")

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if strict_bool(receipt.get("dirty"), "receipt dirty") is not False:
        raise ValueError("dirty producer source")
    required_receipt = {
        "status": "COMPLETED",
        "protocol_revision": PROTOCOL_REVISION,
        "state": state,
        "seed": seed,
        "alpha": alpha,
        "arm": arm,
        "producer_alias": "taobo",
        "code_commit": expected_commit,
        "dirty": False,
        "checkpoint_sha256": record["checkpoint_sha256"],
        "prediction_sha256": record["prediction_sha256"],
        "monitoring_sha256": record["monitoring_sha256"],
        "metrics_sha256": sha256(path),
        "reference_sha256": EXPECTED[state],
        "archive_status": "VERIFIED_COPY",
    }
    if any(receipt.get(key) != value for key, value in required_receipt.items()):
        raise ValueError("run receipt identity mismatch")
    for key in (
        "run_id",
        "hostname",
        "command",
        "gpu",
        "cuda_visible_devices",
        "output_root",
        "archive_root",
        "log_path",
        "started_utc",
        "finished_utc",
    ):
        if not isinstance(receipt.get(key), str) or not receipt[key].strip():
            raise ValueError(f"run receipt missing {key}")
    archive_hashes = receipt.get("archive_file_hashes")
    expected_archive_hashes = {
        checkpoint.name: record["checkpoint_sha256"],
        prediction.name: record["prediction_sha256"],
        monitoring.name: record["monitoring_sha256"],
        path.name: sha256(path),
        "learning_rates.npy": record["learning_rates_sha256"],
        "expected_learning_rates.npy": record["expected_learning_rates_sha256"],
        "coordinate_map.json": record["coordinate_map_sha256"],
        "PRE_UPDATE.json": record["pre_update_sha256"],
    }
    if archive_hashes != expected_archive_hashes:
        raise ValueError("archive hash manifest mismatch")
    run_id = receipt["run_id"]
    for key, prefix in {
        "output_root": "/mnt/data2/drtao/wennie/",
        "archive_root": "/mnt/data2/drtao/pidl_archives/",
        "log_path": "/mnt/data2/drtao/wennie/",
    }.items():
        if not receipt[key].startswith(prefix) or run_id not in receipt[key]:
            raise ValueError(f"run receipt has invalid {key}")

    for key, expected in {
        "n_damage": n_damage,
        "n_background": n_background,
        "damage_threshold": DAMAGE_THRESHOLD,
        "sample_seed": seed + SAMPLE_SEED_OFFSET,
        "sample_order": "damage_then_background_no_shuffle",
    }.items():
        if record.get(key) != expected:
            raise ValueError(f"sampler field mismatch: {key}")
    if (
        record.get("damage_node_count", 0) <= 0
        or record.get("background_node_count", 0) <= 0
    ):
        raise ValueError("invalid stratum node counts")
    p_damage = finite_number(record.get("p_damage"), "p_damage")
    p_background = finite_number(record.get("p_background"), "p_background")
    if not math.isclose(p_damage + p_background, 1.0, rel_tol=0.0, abs_tol=1e-14):
        raise ValueError("stratum masses do not sum to one")

    metrics = record.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError("metrics must be an object")
    recomputed = {}
    for metric, threshold in THRESHOLDS.items():
        value = finite_number(metrics.get(metric), metric)
        passed = value <= threshold
        stored_key = GATE_KEYS[metric]
        if strict_bool(metrics.get(stored_key), stored_key) != passed:
            raise ValueError(f"stored {stored_key} is inconsistent with {metric}")
        recomputed[stored_key] = passed
    for metric in ("strain_error_norm", "strain_reference_norm", "reference_rho_u"):
        value = finite_number(metrics.get(metric), metric)
        if metric == "strain_reference_norm" and value <= 0.0:
            raise ValueError("strain_reference_norm must be positive")
    if strict_bool(metrics.get("gate_finite"), "gate_finite") is not True:
        raise ValueError("gate_finite must pass for a completed valid run")
    joint = all(recomputed.values())
    if strict_bool(metrics.get("joint_pass"), "joint_pass") != joint:
        raise ValueError("stored joint_pass is inconsistent with recomputed gates")
    final_displacement = float(metrics["displacement_mass_rms_over_abs_Us"])
    if not math.isclose(
        trace[-1]["displacement_mass_rms_over_abs_Us"],
        final_displacement,
        rel_tol=0.0,
        abs_tol=1e-14,
    ):
        raise ValueError("final monitoring displacement does not match decision metric")
    for entry in trace:
        for label, p_key, contribution_key in (
            ("damage", "p_damage", "active_contribution"),
            ("background", "p_background", "background_contribution"),
        ):
            p_value = finite_number(entry.get(p_key), p_key)
            rms = finite_number(
                entry.get(label + "_conditional_rms_over_abs_Us"), label
            )
            if not 0 < p_value < 1 or rms < 0:
                raise ValueError("invalid regional metric")
            expected_p = p_damage if label == "damage" else p_background
            if not math.isclose(p_value, expected_p, rel_tol=0, abs_tol=1e-14):
                raise ValueError("regional probability mismatch")
            if not math.isclose(
                p_value * rms**2,
                entry[contribution_key],
                rel_tol=1e-12,
                abs_tol=1e-15,
            ):
                raise ValueError("regional RMS/contribution mismatch")
    data = reference_data[state]
    expected_geometry = anchor_component_geometry(
        data["xy"], data["damage"], data["conn"], data["mass"]
    )
    for stored_geometry in (record.get("geometry"), checkpoint_data.get("geometry")):
        if not isinstance(stored_geometry, dict) or set(stored_geometry) != set(
            expected_geometry
        ):
            raise ValueError("geometry manifest schema mismatch")
        if not geometry_matches(stored_geometry, expected_geometry):
            raise ValueError("anchor geometry identity mismatch")
    if (
        record.get("parameter_count") != PARAMETER_COUNT
        or checkpoint_data.get("parameter_count") != PARAMETER_COUNT
    ):
        raise ValueError("parameter count mismatch")
    probability = data["mass"] / np.sum(data["mass"])
    active = data["damage"] > DAMAGE_THRESHOLD
    squared = np.sum((saved_uv - data["equilibrated_uv"]) ** 2, axis=1) / abs(US) ** 2
    c_active = float(np.sum(probability[active] * squared[active]))
    c_background = float(np.sum(probability[~active] * squared[~active]))
    independently_computed = {
        "full_field_loss": c_active + c_background,
        "displacement_mass_rms_over_abs_Us": float(np.sqrt(c_active + c_background)),
        "active_contribution": c_active,
        "background_contribution": c_background,
        "damage_conditional_rms_over_abs_Us": float(
            np.sqrt(c_active / probability[active].sum())
        ),
        "background_conditional_rms_over_abs_Us": float(
            np.sqrt(c_background / probability[~active].sum())
        ),
        "p_damage": float(probability[active].sum()),
        "p_background": float(probability[~active].sum()),
    }
    if not math.isclose(
        independently_computed["displacement_mass_rms_over_abs_Us"],
        final_displacement,
        rel_tol=0,
        abs_tol=1e-14,
    ):
        raise ValueError("saved prediction displacement disagrees with reported metric")
    for key, value in independently_computed.items():
        if not math.isclose(value, trace[-1][key], rel_tol=0, abs_tol=1e-14):
            raise ValueError(f"saved prediction regional metric mismatch: {key}")
    if record["damage_node_count"] != int(active.sum()) or record[
        "background_node_count"
    ] != int((~active).sum()):
        raise ValueError("saved reference stratum count mismatch")
    return {
        "state": state,
        "seed": seed,
        "alpha": alpha,
        "arm": arm,
        "reference_sha256": record["reference_sha256"],
        "checkpoint_sha256": record["checkpoint_sha256"],
        **{metric: float(metrics[metric]) for metric in THRESHOLDS},
        "reference_rho_u": float(metrics["reference_rho_u"]),
        "joint_pass": joint,
        "final_damage_conditional_rms": trace[-1]["damage_conditional_rms_over_abs_Us"],
        "final_background_conditional_rms": trace[-1][
            "background_conditional_rms_over_abs_Us"
        ],
        "final_active_contribution": trace[-1]["active_contribution"],
        "final_background_contribution": trace[-1]["background_contribution"],
        "monitor_initial_displacement": float(
            trace[0]["displacement_mass_rms_over_abs_Us"]
        ),
        "monitor_final_displacement": float(
            trace[-1]["displacement_mass_rms_over_abs_Us"]
        ),
    }


def prepare_baseline(state, reference_path, backbone_path, control_path):
    data = validate_reference(state, reference_path)
    model, stored, lock = admit_backbone(state, backbone_path, data)
    uv = (
        predict_in_chunks(model, torch.tensor(data["xy"], dtype=torch.float64))
        .cpu()
        .numpy()
    )
    np.testing.assert_allclose(uv, stored, rtol=0, atol=1e-12)
    metrics = final_metrics(data, uv)
    np.testing.assert_allclose(
        metrics["displacement_mass_rms_over_abs_Us"],
        final_metrics(data, stored)["displacement_mass_rms_over_abs_Us"],
        rtol=0,
        atol=1e-14,
    )
    geometry = anchor_component_geometry(
        data["xy"], data["damage"], data["conn"], data["mass"]
    )
    initial = build_model(7, "localized", geometry, model)
    data.update(
        base_model=model,
        base_uv=uv,
        base_metrics=metrics,
        base_digest=state_digest(model),
        initial_residual_digest=state_digest(initial.residual),
    )
    data["paired_control"] = admit_control(state, control_path, data, model)
    data["coordinate_mapping"] = admit_coordinate_map(state, data, stored, geometry)
    candidate = build_candidate(
        7, "localized", geometry, copy.deepcopy(model), data["coordinate_mapping"]
    )
    data["initial_coordinate_model_digest"] = state_digest(candidate)
    with np.load(control_path / "prediction.npz") as saved_control:
        data["control_support"] = support_diagnostics(
            saved_control["uv"], uv, data, geometry
        )
    return data


def validate_record(path, expected_commit, reference_data):
    validate_schedule_and_pair(path)
    row = validate_common_record(path, expected_commit, reference_data)
    validate_pre_update(path, expected_commit, reference_data)
    record = json.loads(path.read_text())
    if record.get("damage_solves") != 0 or record.get("history_commits") != 0:
        raise ValueError("damage/history update in frozen-state experiment")
    state = row["state"]
    arm = row["arm"]
    data = reference_data[state]
    checkpoint = torch.load(
        path.parent / "final_step_10000.pt", map_location="cpu", weights_only=True
    )
    receipt = json.loads((path.parent / "RUN_RECEIPT.json").read_text())
    for asset in (record, checkpoint, receipt):
        if asset.get("backbone_lock") != BACKBONE_LOCKS[state]:
            raise ValueError("inherited backbone lock mismatch")
        if asset.get("backbone_digest") != data["base_digest"]:
            raise ValueError("frozen backbone tensor mismatch")
        if asset.get("initial_residual_digest") != data["initial_residual_digest"]:
            raise ValueError("residual initialization mismatch")
        digest = asset.get("sampler_index_sha256")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(c not in "0123456789abcdef" for c in digest)
        ):
            raise ValueError("invalid sampler digest")
        if digest != record["sampler_index_sha256"]:
            raise ValueError("sampler manifest mismatch")
    for asset in (record, checkpoint):
        if asset.get("residual_parameter_count") != RESIDUAL_PARAMETER_COUNT:
            raise ValueError("residual count mismatch")
    if strict_bool(record.get("backbone_frozen"), "backbone_frozen") is not True:
        raise ValueError("backbone not frozen")
    if (
        record.get("new_optimizer_steps") != 10000
        or record.get("inherited_optimizer_steps") != 10000
    ):
        raise ValueError("budget lineage")
    geometry = anchor_component_geometry(
        data["xy"], data["damage"], data["conn"], data["mass"]
    )
    model = build_candidate(
        7, arm, geometry, copy.deepcopy(data["base_model"]), data["coordinate_mapping"]
    )
    model.load_state_dict(checkpoint["model_state_dict"], strict=True)
    validate_coordinate_buffers(model, data["coordinate_mapping"])
    for name in ("lower", "upper", "center", "scale"):
        if not torch.equal(
            getattr(model, name), torch.tensor(geometry[name], dtype=torch.float64)
        ):
            raise ValueError("actual geometry buffer mismatch")
    if state_digest(model.backbone) != data["base_digest"]:
        raise ValueError("actual backbone tensor drift")
    if any(
        t.dtype != torch.float64 or not torch.isfinite(t).all()
        for t in checkpoint["model_state_dict"].values()
    ):
        raise ValueError("checkpoint dtype/finiteness")
    with np.load(path.parent / "prediction.npz") as pred:
        uv = pred["uv"].copy()
    reloaded = (
        predict_in_chunks(model, torch.tensor(data["xy"], dtype=torch.float64))
        .cpu()
        .numpy()
    )
    np.testing.assert_allclose(reloaded, uv, rtol=0, atol=1e-12)
    diagnostics = support_diagnostics(uv, data["base_uv"], data, geometry)
    if not geometry_matches(record.get("support_diagnostics"), diagnostics):
        raise ValueError("support diagnostics mismatch")
    if arm == "localized" and diagnostics["outside_support_max_abs_delta"] > 1e-12:
        raise ValueError("outside-window prediction drift")
    # Baseline metric/region sidecars cannot decide preservation without recomputation.
    for k, v in data["base_metrics"].items():
        stored = record["baseline_metrics"][k]
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if not math.isclose(stored, v, rel_tol=1e-12, abs_tol=1e-14):
                raise ValueError("baseline metric mismatch")
        elif stored != v:
            raise ValueError("baseline flag mismatch")
    w = data["mass"] / data["mass"].sum()
    a = data["damage"] > 0.1
    squared = (
        np.sum((data["base_uv"] - data["equilibrated_uv"]) ** 2, axis=1) / abs(US) ** 2
    )
    ca = float(np.sum(w[a] * squared[a]))
    cb = float(np.sum(w[~a] * squared[~a]))
    bf = float(np.sqrt(ca + cb))
    bd = float(np.sqrt(ca / w[a].sum()))
    bb = float(np.sqrt(cb / w[~a].sum()))
    trace = json.loads((path.parent / "monitoring.json").read_text())
    for key, value in (
        ("displacement_mass_rms_over_abs_Us", bf),
        ("damage_conditional_rms_over_abs_Us", bd),
        ("background_conditional_rms_over_abs_Us", bb),
    ):
        for stored in (trace[0], record["baseline_regions"]):
            if not math.isclose(stored[key], value, rel_tol=0, abs_tol=1e-14):
                raise ValueError("step0 baseline mismatch")
    row.update(
        base_full=bf,
        base_damage=bd,
        base_background=bb,
        outside_support_max_abs_delta=diagnostics["outside_support_max_abs_delta"],
        sampler_index_sha256=record["sampler_index_sha256"],
    )
    check_pair_identity(
        state,
        geometry,
        record["backbone_digest"],
        record["initial_residual_digest"],
        record["sampler_index_sha256"],
    )
    control = data["paired_control"]["regions"]
    row.update(
        control_full=control["full"],
        control_damage=control["damage"],
        control_background=control["background"],
        background_inside_support_conditional_rms=diagnostics[
            "background_inside_support_conditional_rms"
        ],
        background_outside_support_conditional_rms=diagnostics[
            "background_outside_support_conditional_rms"
        ],
        control_background_inside_support_conditional_rms=data["control_support"][
            "background_inside_support_conditional_rms"
        ],
        control_background_outside_support_conditional_rms=data["control_support"][
            "background_outside_support_conditional_rms"
        ],
    )
    return row


def summarize(rows, errors=(), missing=()):
    expected = set(EXPECTED)
    if len(rows) != len({r["state"] for r in rows}) or any(
        r["state"] not in expected for r in rows
    ):
        errors = [*errors, {"error": "duplicate or unexpected state"}]
    missing = sorted(set(missing) | (expected - {r["state"] for r in rows}))
    complete = not errors and not missing and len(rows) == 3
    primary = complete and all(
        r["displacement_mass_rms_over_abs_Us"] <= 0.001 for r in rows
    )
    return dict(
        protocol_revision=PROTOCOL_REVISION,
        expected_runs=3,
        valid_completed_runs=len(rows),
        missing=missing,
        integrity_errors=list(errors),
        verdict="INADMISSIBLE"
        if errors
        else "INCONCLUSIVE"
        if not complete
        else "COORDINATE_PRECONDITIONED_THREE_STATE_UV_SCREEN_PASS"
        if primary
        else "COORDINATE_PRECONDITIONED_THREE_STATE_UV_SCREEN_FAIL",
        clean_damage_progress_background_preserved=all(
            r["final_damage_conditional_rms"] < r["base_damage"] - 1e-14
            and r["final_background_conditional_rms"] <= r["base_background"] + 1e-14
            for r in rows
        )
        if complete
        else None,
        clean_damage_progress_background_preserved_vs_control=all(
            r["final_damage_conditional_rms"] < r["control_damage"] - 1e-14
            and r["final_background_conditional_rms"] <= r["control_background"] + 1e-14
            for r in rows
        )
        if complete
        else None,
        stage2_authorized=False,
        qualified_fem_teacher="NOT_QUALIFIED",
    )


def aggregate(input_root, expected_commit, reference_root, backbone_root, control_root):
    rows, errors, data = [], [], {}
    for state in EXPECTED:
        try:
            data[state] = prepare_baseline(
                state,
                reference_root / f"{state}.npz",
                backbone_root / state,
                control_root / CONTROL_LOCKS[state]["run_id"],
            )
        except Exception as exc:
            errors.append(dict(state=state, error=str(exc)))
    for path in sorted(input_root.glob("**/metrics.json")):
        try:
            rows.append(validate_record(path, expected_commit, data))
        except Exception as exc:
            errors.append(dict(path=str(path), error=str(exc)))
    rows.sort(key=lambda r: r["state"])
    summary = summarize(rows, errors)
    summary["code_commit"] = expected_commit
    return rows, summary


def main():
    parser = argparse.ArgumentParser()
    for name in (
        "input-root",
        "reference-root",
        "backbone-root",
        "control-root",
        "out",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--code-commit", required=True)
    args = parser.parse_args()
    if len(args.code_commit) != 40 or any(
        c not in "0123456789abcdef" for c in args.code_commit
    ):
        parser.error("--code-commit must be a lowercase40-character Git SHA")
    if args.out.exists():
        parser.error("--out must not already exist")
    rows, summary = aggregate(
        args.input_root,
        args.code_commit,
        args.reference_root,
        args.backbone_root,
        args.control_root,
    )
    args.out.mkdir(parents=True)
    with (args.out / "metrics.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["state"])
        writer.writeheader()
        writer.writerows(rows)
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    if summary["verdict"] == "INADMISSIBLE":
        raise SystemExit(2)
    if summary["verdict"] == "INCONCLUSIVE":
        raise SystemExit(3)


if __name__ == "__main__":
    main()
