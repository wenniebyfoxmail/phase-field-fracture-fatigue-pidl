#!/usr/bin/env python3
"""Export the exact-native-Q4 eta0 paired control for S04-E013.

The exporter is read-only: it reconstructs registered accepted PIDL states from
their network and checkpoint pairs.  It exports nodal displacement/damage,
native-Q4 Gauss-point mechanics and fatigue channels, and each state's own
step-1 prior.  It never substitutes FEM states or enters a training loop.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "source"))

_saved_argv = sys.argv
sys.argv = ["export_s04_e013_paired_eta0", "8", "400", "1", "TrainableReLU", "1.0"]
import config  # noqa: E402
from compute_energy import (  # noqa: E402
    compute_energy_per_elem,
    get_psi_plus_per_elem,
    gradients,
    strain_energy_with_split,
)
from export_pidl_element_diagnostics import (  # noqa: E402
    build_field_computation,
    parse_settings,
    safe_torch_load,
)
from fatigue_history import compute_fatigue_degrad  # noqa: E402
from q4_quadrature import q4_interpolate, q4_shape_data  # noqa: E402
sys.argv = _saved_argv


SCHEDULE = (0.02999988, 0.05999988, 0.08999988, 0.11999988, 0.0)
REQUIRED_CYCLES = (20, 60, 82, 83)
REQUIRED_SUBSTEPS = (2, 4, 5)
OWN_EVENT_STEP = 424
EXPECTED_SIGNATURE = "e16c9b230c07cc747f5544de1b2bc4afa42be0f6ff645f67b81671307c7eea0e"
EXPECTED_ARCHIVE_NAME = (
    "probeDriver_hl8_n400_seed1_AT1_numerical_carrara_asy_aT0.5_Ncyc120_"
    "Nstep601_U0.12_nativeq4_production_aaf13fd_current_active_native_q4_"
    "gp4_femIrrGP4_hardAlphaRecoverU0_u0.0299999-0.0599999-0.0899999-0.12-0"
)
EXPECTED_SETTINGS_SHA256 = "f2fb08784390d3e949205c48a9a4975ba01723c4f59dc597641b8d01f2d0fcad"
EXPECTED_MESH_SHA256 = "0e6db55abde5880200e2ce01bfe1a7fbb0d4a827362c15afbadbece111fdcb75"
EXPECTED_SOURCE_SHA256 = "e996c3389843596ee7459eb13d878e6030aa4c1630bff48d25b8c19c635f96c2"
EXPECTED_LOG_SHA256 = "ea7964e0b20b88a19cce38a1c9df170ad23dbee8453e77e03ddaef92392ffbf1"
EXPECTED_SOURCE_MEMBERS = {
    "source/model_train.py": "88661c8eef7c737c533d40c28b6ea80db6ece4b277b84880626cdbeb4dedd01d",
    "SENS_tensile/run_fem_mesh_probe_driver_umax.py": "337f6114bfdb092676bc40de47841d8d2a4f9d53c1cd1d4f86899057a1ab6d3f",
    "SENS_tensile/field_computation.py": "73ac9cd57db9c3b6f1d610437141373fd7a77f3acb14d040ebb39ad99e3f3c8c",
    "SENS_tensile/config.py": "2e36c71b49bf0b0af17aea4ffde22c01c9c67c95726adae0300acab0e016d4f4",
}


@dataclass(frozen=True)
class RegisteredState:
    label: str
    comparison_class: str
    cycle: int
    substep: int
    step: int
    load: float


def mapped_step(cycle: int, substep: int) -> int:
    if cycle < 1 or substep not in range(1, 6):
        raise ValueError((cycle, substep))
    return 1 + 5 * (cycle - 1) + (substep - 1)


def registered_states() -> list[RegisteredState]:
    states = [
        RegisteredState(
            f"c{cycle:02d}s{substep}", "same_cycle", cycle, substep,
            mapped_step(cycle, substep), SCHEDULE[substep - 1],
        )
        for cycle in REQUIRED_CYCLES for substep in REQUIRED_SUBSTEPS
    ]
    states.append(RegisteredState("c85s4_own_event", "own_event_first_detect", 85, 4, OWN_EVENT_STEP, SCHEDULE[3]))
    return states


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_archive_identity(
    archive: Path, mesh: Path, source_snapshot: Path, producer_log: Path,
) -> dict[str, object]:
    """Bind old files to the locked producer, save order, schedule and event record."""
    if archive.name != EXPECTED_ARCHIVE_NAME:
        raise AssertionError(f"wrong control archive: {archive.name}")
    settings_path = archive / "model_settings.txt"
    locks = {
        settings_path: EXPECTED_SETTINGS_SHA256,
        mesh: EXPECTED_MESH_SHA256,
        source_snapshot: EXPECTED_SOURCE_SHA256,
        producer_log: EXPECTED_LOG_SHA256,
    }
    for path, expected in locks.items():
        actual = digest(path)
        if actual != expected:
            raise AssertionError(f"identity hash mismatch {path}: {actual} != {expected}")

    settings = parse_settings(settings_path)
    expected_settings = {
        "runner": "run_fem_mesh_probe_driver_umax.py",
        "runner_sha256": EXPECTED_SOURCE_MEMBERS["SENS_tensile/run_fem_mesh_probe_driver_umax.py"],
        "n_training_steps": "601",
        "mesh_tag": "nativeq4_production_aaf13fd",
        "representation": "coordinate_MLP",
        "supervision": "physics_only_no_FEM_field_targets",
        "residual_stiffness": "0.0",
        "history_driver_mode": "current_active",
        "history_storage": "q4_gp4",
        "damage_history_storage": "previous_accepted_nodal",
        "spatial_discretization": "native_Q4_2x2_GP",
        "recovery_step_offset": "1",
        "explicit_cycle_step_mode": "absolute_displacement",
        "explicit_cycle_substeps": "5",
        "explicit_cycle_displacements": "[0.02999988, 0.05999988, 0.08999988, 0.11999988, 0.0]",
        "state_mapping": "step0=U0_hard_alpha_recovery; cN_peak=1+5*(N-1)+3; cN_unloaded=1+5*(N-1)+4",
    }
    for key, expected in expected_settings.items():
        if settings.get(key) != expected:
            raise AssertionError(f"locked setting {key}: {settings.get(key)!r} != {expected!r}")

    member_hashes: dict[str, str] = {}
    with tarfile.open(source_snapshot, "r:gz") as bundle:
        for name, expected in EXPECTED_SOURCE_MEMBERS.items():
            extracted = bundle.extractfile(name)
            if extracted is None:
                raise AssertionError(f"source snapshot missing {name}")
            actual = hashlib.sha256(extracted.read()).hexdigest()
            if actual != expected:
                raise AssertionError(f"source member mismatch {name}: {actual}")
            member_hashes[name] = actual

    log_text = producer_log.read_text(encoding="utf-8", errors="strict")
    onset = re.findall(r"\[Fracture\?\] cycle (\d+):", log_text)
    resets = re.findall(r"\[Fracture reset\] cycle (\d+):", log_text)
    confirmed = re.findall(
        r"\[Fracture confirmed\] Stopping at cycle (\d+)\. First detected at cycle (\d+)\.",
        log_text,
    )
    if onset != ["424"] or resets or confirmed != [("427", "424")]:
        raise AssertionError(
            f"event log identity mismatch: onset={onset}, resets={resets}, confirmed={confirmed}"
        )
    return {
        "archive_name": archive.name,
        "settings_sha256": EXPECTED_SETTINGS_SHA256,
        "mesh_sha256": EXPECTED_MESH_SHA256,
        "source_snapshot_sha256": EXPECTED_SOURCE_SHA256,
        "producer_log_sha256": EXPECTED_LOG_SHA256,
        "source_member_sha256": member_hashes,
        "accepted_state_save_order": (
            "fit -> recompute current model damage -> commit hist_alpha -> "
            "save trained_1NN_<step>.pt -> save checkpoint_step_<step>.pt"
        ),
        "event_first_occurrence_step": 424,
        "event_confirmation_completion_step": 427,
        "event_confirmation_semantics": "three subsequent consecutive accepted steps; onset excluded",
    }


def validate_checkpoint(checkpoint: dict, *, step: int) -> None:
    expected = {
        "mesh_state_signature": EXPECTED_SIGNATURE,
        "mesh_connectivity_arity": 4,
        "history_storage": "q4_gp4",
        "damage_history_storage": "previous_accepted_nodal",
        "history_driver_mode": "current_active",
    }
    for key, value in expected.items():
        if checkpoint.get(key) != value:
            raise AssertionError(f"step {step} checkpoint {key}: {checkpoint.get(key)!r} != {value!r}")
    if tuple(checkpoint["hist_fat"].shape) != (86408, 4):
        raise AssertionError(f"step {step} hist_fat shape")
    if tuple(checkpoint["psi_plus_prev"].shape) != (86408, 4):
        raise AssertionError(f"step {step} psi_plus_prev shape")


def validate_model_checkpoint_damage(
    damage_model: torch.Tensor, damage: torch.Tensor, *, step: int,
) -> float:
    mismatch = float(torch.max(torch.abs(damage_model - damage)).cpu())
    if mismatch > 5e-6:
        raise AssertionError(f"step {step} model/checkpoint damage mismatch {mismatch}")
    return mismatch


def validate_event_evidence(archive: Path, nodes: torch.Tensor, device: torch.device) -> dict[str, object]:
    """Recheck the locked first occurrence and three subsequent confirmations."""
    best = archive / "best_models"
    right = nodes[:, 0] > 0.48
    evidence: list[dict[str, object]] = []
    for step in range(423, 428):
        path = best / f"checkpoint_step_{step}.pt"
        if not path.is_file():
            raise FileNotFoundError(path)
        checkpoint = safe_torch_load(path, device)
        validate_checkpoint(checkpoint, step=step)
        count = int((checkpoint["hist_alpha"].to(device)[right] > 0.95).sum().cpu())
        expected_detected = step >= 424
        expected_remaining = 0 if step == 423 else 427 - step
        if bool(checkpoint.get("_frac_detected")) != expected_detected:
            raise AssertionError(f"step {step} event detected metadata mismatch")
        if checkpoint.get("_frac_cycle") != (424 if expected_detected else None):
            raise AssertionError(f"step {step} event onset metadata mismatch")
        if checkpoint.get("_frac_confirm_remaining") != expected_remaining:
            raise AssertionError(f"step {step} confirmation metadata mismatch")
        if (step == 423 and count >= 3) or (step >= 424 and count < 3):
            raise AssertionError(f"step {step} frozen detector count mismatch: {count}")
        evidence.append({
            "step": step,
            "right_region_nodes_above_0p95": count,
            "detected": expected_detected,
            "confirmation_remaining": expected_remaining,
            "checkpoint_sha256": digest(path),
        })
    return {
        "region": "node x > 0.48",
        "strict_damage_threshold": 0.95,
        "minimum_nodes": 3,
        "first_occurrence_step": 424,
        "confirmation_completion_step": 427,
        "confirmation_steps": [425, 426, 427],
        "evidence": evidence,
    }


def export_state(
    archive: Path, mesh: Path, state: RegisteredState, out_dir: Path,
    device: torch.device,
) -> dict[str, object]:
    best = archive / "best_models"
    model_path = best / f"trained_1NN_{state.step}.pt"
    checkpoint_path = best / f"checkpoint_step_{state.step}.pt"
    prior_path = best / f"checkpoint_step_{state.step - 1}.pt"
    for path in (model_path, checkpoint_path, prior_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    field, model, material, nodes, conn, area = build_field_computation(
        archive, device, umax=state.load, mesh_file=mesh,
    )
    if conn.shape != (86408, 4) or nodes.shape != (86756, 2):
        raise AssertionError(f"native-Q4 geometry mismatch: {tuple(nodes.shape)}, {tuple(conn.shape)}")
    field.lmbda = torch.tensor([state.load], device=device)
    field.net.load_state_dict(safe_torch_load(model_path, device))
    field.net.eval()
    checkpoint = safe_torch_load(checkpoint_path, device)
    prior = safe_torch_load(prior_path, device)
    validate_checkpoint(checkpoint, step=state.step)
    validate_checkpoint(prior, step=state.step - 1)

    with torch.no_grad():
        u, v, damage_model = field.fieldCalculation(nodes)
        damage = checkpoint["hist_alpha"].to(device)
        prior_damage = prior["hist_alpha"].to(device)
        model_damage_max_abs = validate_model_checkpoint_damage(
            damage_model, damage, step=state.step,
        )
        committed_history = checkpoint["hist_fat"].to(device)
        prior_history = prior["hist_fat"].to(device)
        accepted_driver = checkpoint["psi_plus_prev"].to(device)
        prior_driver = prior["psi_plus_prev"].to(device)
        fatigue = compute_fatigue_degrad(committed_history, config.fatigue_dict)
        shape, _, det_j = q4_shape_data(nodes, conn)
        damage_gp = q4_interpolate(damage, conn, shape)
        active = get_psi_plus_per_elem(
            nodes, u, v, damage, material, model, area, conn,
            history_driver_reduction_dict={"enable": True, "mode": "native_q4_gp4"},
        )
        eps_xx, eps_yy, eps_xy, grad_dx, grad_dy = gradients(nodes, u, v, damage, area, conn)
        _, raw = strain_energy_with_split(eps_xx, eps_yy, eps_xy, damage_gp, material, model)
        energy_el, energy_d, energy_hist = compute_energy_per_elem(
            nodes, u, v, damage, prior_damage, material, model, area, conn,
            f_fatigue=fatigue,
            irreversibility_penalty_cfg={"enable": True, "mode": "fem_gp_q4"},
        )
        g_damage, _ = model.Edegrade(damage_gp)

    arrays = {
        "node_xy": nodes.cpu().numpy(),
        "conn": conn.cpu().numpy(),
        "u_node": torch.stack((u, v), dim=1).cpu().numpy(),
        "d_node": damage.cpu().numpy(),
        "d_node_model": damage_model.cpu().numpy(),
        "prior_d_node": prior_damage.cpu().numpy(),
        "gp_det_j": det_j.cpu().numpy(),
        "history_committed_gp": committed_history.cpu().numpy(),
        "history_prior_gp": prior_history.cpu().numpy(),
        "fatigue_degradation_gp": fatigue.cpu().numpy(),
        "driver_active_gp": active.cpu().numpy(),
        "driver_raw_gp": raw.cpu().numpy(),
        "driver_accepted_gp": accepted_driver.cpu().numpy(),
        "driver_prior_gp": prior_driver.cpu().numpy(),
        "damage_gp": damage_gp.cpu().numpy(),
        "g_damage_gp": g_damage.cpu().numpy(),
        "strain_xx_gp": eps_xx.cpu().numpy(),
        "strain_yy_gp": eps_yy.cpu().numpy(),
        "strain_xy_tensor_gp": eps_xy.cpu().numpy(),
        "grad_damage_x_gp": grad_dx.cpu().numpy(),
        "grad_damage_y_gp": grad_dy.cpu().numpy(),
        "energy_elastic_elem": energy_el.cpu().numpy(),
        "energy_damage_elem": energy_d.cpu().numpy(),
        "energy_irreversibility_elem": energy_hist.cpu().numpy(),
        "cycle": np.array([state.cycle], dtype=np.int32),
        "substep": np.array([state.substep], dtype=np.int32),
        "pidl_step": np.array([state.step], dtype=np.int32),
        "load": np.array([state.load], dtype=np.float64),
        "comparison_class": np.array([state.comparison_class]),
        "export_timing": np.array(["post_fit_post_history_commit_accepted_state"]),
        "prior_timing": np.array(["own_checkpoint_step_minus_1_post_history_commit"]),
    }
    if not all(np.isfinite(value).all() for value in arrays.values() if value.dtype.kind in "fciu"):
        raise ValueError(f"nonfinite export {state.label}")
    out_path = out_dir / f"{state.label}_step{state.step:04d}.npz"
    np.savez_compressed(out_path, **arrays)
    return {
        "state": state.label,
        "comparison_class": state.comparison_class,
        "cycle": state.cycle,
        "substep": state.substep,
        "pidl_step": state.step,
        "prior_step": state.step - 1,
        "load": state.load,
        "output": out_path.name,
        "output_sha256": digest(out_path),
        "model_sha256": digest(model_path),
        "checkpoint_sha256": digest(checkpoint_path),
        "prior_checkpoint_sha256": digest(prior_path),
        "model_checkpoint_damage_max_abs": model_damage_max_abs,
        "n_nodes": int(nodes.shape[0]),
        "n_elements": int(conn.shape[0]),
        "history_commits": 0,
        "training": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--source-snapshot", type=Path, required=True)
    parser.add_argument("--producer-log", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    if not args.archive.is_dir() or not all(
        path.is_file() for path in (args.mesh, args.source_snapshot, args.producer_log)
    ):
        raise FileNotFoundError((args.archive, args.mesh, args.source_snapshot, args.producer_log))
    identity = validate_archive_identity(
        args.archive, args.mesh, args.source_snapshot, args.producer_log,
    )
    args.out.mkdir(parents=True)
    rows = [export_state(args.archive, args.mesh, state, args.out, torch.device(args.device))
            for state in registered_states()]
    with (args.out / "manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    # All states use the same locked mesh; bind the event row to archived
    # accepted-state tensors and detector metadata rather than a lookup label.
    _, _, _, event_nodes, _, _ = build_field_computation(
        args.archive, torch.device(args.device), umax=SCHEDULE[3], mesh_file=args.mesh,
    )
    event_evidence = validate_event_evidence(
        args.archive, event_nodes, torch.device(args.device),
    )
    manifest = {
        "schema": "s04-e013-exact-native-q4-eta0-paired-export-v1",
        "archive": str(args.archive),
        "mesh": str(args.mesh),
        "identity": identity,
        "mapping": "step=1+5*(cycle-1)+(substep-1); step0 is hard-alpha U0 recovery",
        "schedule": list(SCHEDULE),
        "event_detector": {
            "field": "accepted nodal damage in production right-boundary region x>0.48",
            "threshold": 0.95,
            "minimum_nodes_strictly_above_threshold": 3,
            "timing": "post_fit accepted state",
            "first_occurrence": True,
            "confirmation_cycles": 3,
            "control_first_event_step": OWN_EVENT_STEP,
            "control_first_event_state": "c85s4",
            "confirmation_completion_step": 427,
            "confirmation_steps": [425, 426, 427],
        },
        "event_evidence": event_evidence,
        "rows": rows,
        "training": False,
        "history_commits": 0,
    }
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
