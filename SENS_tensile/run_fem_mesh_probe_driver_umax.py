#!/usr/bin/env python3
"""Run strict FEM-mesh PIDL with opt-in fatigue-driver reduction.

By default this discriminator keeps the variational energy/objective unchanged:
only the post-fit fatigue-history driver changes from

    g(mean(alpha_nodes)) * psi_raw_elem

to either the archived probe rule or the FEM-like tri3 quadrature rule,

    mean_q[g(alpha_q)] * psi_raw_elem

where alpha_q is evaluated at three triangle points.  With
``--fem-irr-penalty`` the irreversibility penalty also moves from
``ReLU(-mean(delta_alpha_nodes))^2`` to local quadrature
``mean_q(ReLU(-delta_alpha_q)^2)``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np


def _resolve_mesh_file(here: Path, filename: str) -> str:
    path = Path(filename).expanduser()
    if path.is_absolute():
        return str(path)
    local = here / path
    if local.exists():
        return str(local)
    for parent in here.parents:
        candidate = parent / "SENS_tensile" / path
        if candidate.exists():
            return str(candidate)
    return filename


def _mesh_tag(mesh_file: str, explicit: str) -> str:
    if explicit:
        return explicit.strip().replace(" ", "_")
    stem = Path(mesh_file).stem
    return stem.removeprefix("meshed_geom_").replace(" ", "_")


def _parse_float_csv(raw: str) -> list[float]:
    vals = [float(x) for x in raw.split(",") if x.strip()]
    if len(vals) < 2:
        raise argparse.ArgumentTypeError("need at least two comma-separated values")
    return vals


def _parse_cycles(raw: str) -> list[int]:
    return [int(x) for x in raw.split(",") if x.strip()]


def _validate_res_stiffness(value: str | float) -> float:
    eta = float(value)
    if not np.isfinite(eta) or eta < 0.0:
        raise argparse.ArgumentTypeError(
            f"--res-stiffness must be finite and non-negative, got {value!r}"
        )
    return eta


def _format_eta_tag(eta: float) -> str:
    value = f"{float(eta):.3g}"
    return (
        f"eta{value}"
        .replace(".", "p")
        .replace("+", "")
        .replace("-", "m")
    )


def _git_value(here: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=here.parent,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _peak_substep_index(values: np.ndarray) -> int:
    return int(np.argmax(np.asarray(values, dtype=float)))


def _diag_steps(
    physical_cycles: list[int],
    n_substeps: int,
    *,
    peak_substep: int,
    unload_substep: int,
    step_offset: int = 0,
    full_physical_cycles: list[int] | None = None,
) -> list[int]:
    steps = {0}
    full_cycles = {int(c) for c in (full_physical_cycles or []) if int(c) >= 1}
    for cyc in physical_cycles:
        if cyc < 1:
            continue
        base = int(step_offset) + (cyc - 1) * n_substeps
        if cyc in full_cycles:
            steps.update(base + i for i in range(n_substeps))
        else:
            steps.add(base + int(peak_substep))
            steps.add(base + int(unload_substep))
    return sorted(steps)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("umax", type=float)
    parser.add_argument("--n-cycles-physical", "--n-cycles", dest="n_cycles_physical",
                        type=int, default=120)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    parser.add_argument("--coarse-mesh-file", default=None)
    parser.add_argument("--tag", default="probeDriver_softHist0_stateTiming")
    parser.add_argument("--hidden-layers", type=int, default=8)
    parser.add_argument("--neurons", type=int, default=400)
    parser.add_argument("--init-coeff", default="1.0")
    parser.add_argument("--epochs-rprop", type=int, default=None,
                        help="Override config.optimizer_dict['n_epochs_RPROP'] for smoke runs.")
    parser.add_argument("--epochs-lbfgs", type=int, default=None,
                        help="Override config.optimizer_dict['n_epochs_LBFGS'] for smoke runs.")
    parser.add_argument("--optim-rel-tol", type=float, default=None,
                        help="Override main/pretrain early-stopping relative tolerance.")
    parser.add_argument("--substeps", type=_parse_float_csv,
                        default=_parse_float_csv("0.25,0.5,0.75,1,0"),
                        help=("Legacy per-cycle displacement factors multiplied "
                              "by positional umax. Prefer --displacement-steps "
                              "for FEM/PIDL alignment protocols."))
    parser.add_argument("--displacement-steps", type=_parse_float_csv, default=None,
                        help=("Absolute per-cycle displacement values. When set, "
                              "these values are used directly and --substeps is "
                              "ignored except for backwards compatibility."))
    parser.add_argument("--history-driver-reduction-mode",
                        choices=("probe_g_mean", "fem_gp_tri3_g_mean"),
                        default="probe_g_mean")
    parser.add_argument("--res-stiffness", type=_validate_res_stiffness, default=0.0,
                        help=("Residual stiffness eta in "
                              "Edegrade(alpha)=(1-alpha)^2+eta. "
                              "Default 0.0 preserves the formal baseline."))
    parser.add_argument("--fem-irr-penalty", action="store_true",
                        help="Use FEM-like tri3 quadrature for the irreversibility penalty.")
    parser.add_argument("--hard-alpha-recovery-step", action="store_true",
                        help=("Preset the current NN alpha field to a uniform hard "
                              "value, run step 0 at U=0 for recovery, then continue "
                              "the explicit cyclic schedule with histories preserved."))
    parser.add_argument("--hard-alpha-target", type=float, default=1.0,
                        help="Uniform current alpha target for --hard-alpha-recovery-step.")
    parser.add_argument("--diag-physical-cycles", default="1,2,3,20,40,60,69")
    parser.add_argument("--diag-full-physical-cycles", default="",
                        help=("Physical cycles for which all substeps should be "
                              "saved in element diagnostics. Other listed cycles "
                              "save only peak and final unloaded states."))
    parser.add_argument("--fracture-confirm-cycles", type=int, default=3)
    parser.add_argument("--plot-every", type=int, default=20)
    parser.add_argument("--compile", action="store_true")
    parser.add_argument("--graph-pidl", action="store_true",
                        help="Replace the coordinate MLP by a physics-trained mesh GNN.")
    parser.add_argument(
        "--graph-mode",
        choices=("full", "hybrid", "channel_separated", "damage_latent"),
        default="full",
    )
    parser.add_argument("--graph-layers", type=int, default=None)
    parser.add_argument("--graph-neurons", type=int, default=None)
    parser.add_argument("--graph-scale", type=float, default=1.0)
    parser.add_argument("--graph-uv-scale", type=float, default=0.05)
    parser.add_argument("--graph-alpha-scale", type=float, default=0.01)
    parser.add_argument("--graph-latent-scale", type=float, default=0.05)
    parser.add_argument("--graph-mask-x-min", type=float, default=-0.12)
    parser.add_argument("--graph-mask-x-max", type=float, default=0.50)
    parser.add_argument("--graph-mask-half-width", type=float, default=0.06)
    parser.add_argument("--graph-mask-transition", type=float, default=0.01)
    parser.add_argument("--graph-bounded", action="store_true",
                        help="Bound raw-output graph corrections with tanh.")
    parser.add_argument(
        "--graph-correction-channels",
        choices=("all", "alpha", "uv"),
        default="all",
        help=("Hybrid-only raw-output channel ablation: all=(u,v,alpha_raw), "
              "alpha=(alpha_raw only), uv=(u,v only)."),
    )
    parser.add_argument("--force-cpu", action="store_true")
    parser.add_argument(
        "--mechanical-risk-mode",
        choices=("absent", "off", "on"),
        default="absent",
        help=("G3 tri-state intervention: absent removes the config key, off "
              "installs an explicitly disabled key, and on enables the frozen risk term."),
    )
    parser.add_argument("--mechanical-risk-lambda", type=float, default=None)
    parser.add_argument("--mechanical-risk-alpha", type=float, default=0.85)
    parser.add_argument("--mechanical-risk-e-ref", type=float, default=1.0)
    parser.add_argument("--mechanical-risk-l-ref", type=float, default=1.0)
    parser.add_argument("--mechanical-residual-export-steps", default="",
                        help="Comma-separated raw steps for true optimizer-post residual exports.")
    parser.add_argument("--boundary-first-detect-receipt", action="store_true",
                        help="Emit boundary-only per-step trace and immutable first-detect receipt.")
    parser.add_argument("--hard-stop-physical-cycle", type=int, default=None,
                        help="Stop after the unloaded state of this physical cycle.")
    parser.add_argument("--init-checkpoint", default=None,
                        help="Shared pretraining state_dict copied into each G3 arm.")
    parser.add_argument("--init-checkpoint-sha256", default=None,
                        help="Required expected SHA-256 when --init-checkpoint is used.")
    parser.add_argument("--resume-bundle", default=None,
                        help="Frozen c60 restart-bundle directory for G4 preparation.")
    parser.add_argument("--resume-bundle-manifest-sha256", default=None,
                        help="Required manifest SHA-256 when --resume-bundle is used.")
    parser.add_argument("--preflight-only", action="store_true",
                        help="Validate arguments and print canonical JSON; create no run directory.")
    parser.add_argument("--require-clean-git", action="store_true")
    parser.add_argument("--fresh-output-required", action="store_true")
    parser.add_argument("--required-head-commit", default=None)
    return parser


def _mechanical_risk_config(args: argparse.Namespace) -> dict | None:
    mode = args.mechanical_risk_mode
    coefficient = args.mechanical_risk_lambda
    if not 0.0 < float(args.mechanical_risk_alpha) < 1.0:
        raise ValueError("--mechanical-risk-alpha must lie strictly between zero and one")
    if not np.isfinite(args.mechanical_risk_e_ref) or args.mechanical_risk_e_ref <= 0.0:
        raise ValueError("--mechanical-risk-e-ref must be finite and positive")
    if not np.isfinite(args.mechanical_risk_l_ref) or args.mechanical_risk_l_ref <= 0.0:
        raise ValueError("--mechanical-risk-l-ref must be finite and positive")
    if mode == "on":
        if coefficient is None or not np.isfinite(coefficient) or coefficient <= 0.0:
            raise ValueError("risk-on requires a finite positive --mechanical-risk-lambda")
        return {
            "enable": True,
            "lambda": float(coefficient),
            "alpha": float(args.mechanical_risk_alpha),
            "Umax": float(args.umax),
            "E_ref": float(args.mechanical_risk_e_ref),
            "L_ref": float(args.mechanical_risk_l_ref),
        }
    if coefficient is not None:
        raise ValueError("--mechanical-risk-lambda is only valid in risk-on mode")
    if mode == "off":
        return {"enable": False}
    return None


def _validate_checkpoint_args(args: argparse.Namespace) -> dict | None:
    if bool(args.init_checkpoint) != bool(args.init_checkpoint_sha256):
        raise ValueError("--init-checkpoint and --init-checkpoint-sha256 are required together")
    if not args.init_checkpoint:
        return None
    path = Path(args.init_checkpoint).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"initial checkpoint does not exist: {path}")
    expected = args.init_checkpoint_sha256.lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise ValueError("--init-checkpoint-sha256 must be 64 lowercase hex characters")
    actual = _file_sha256(path)
    if actual != expected:
        raise ValueError(f"initial checkpoint SHA-256 mismatch: expected {expected}, got {actual}")
    return {"path": str(path), "sha256": actual}


def _validate_restart_args(args: argparse.Namespace) -> dict | None:
    if bool(args.resume_bundle) != bool(args.resume_bundle_manifest_sha256):
        raise ValueError(
            "--resume-bundle and --resume-bundle-manifest-sha256 are required together"
        )
    if args.resume_bundle and args.init_checkpoint:
        raise ValueError("--resume-bundle and --init-checkpoint are mutually exclusive")
    if not args.resume_bundle:
        return None
    frozen_displacements = [0.03, 0.06, 0.09, 0.12, 0.0]
    if (
        not np.isclose(float(args.umax), 0.12)
        or args.displacement_steps is None
        or not np.array_equal(np.asarray(args.displacement_steps), frozen_displacements)
        or not args.hard_alpha_recovery_step
        or args.history_driver_reduction_mode != "fem_gp_tri3_g_mean"
        or not args.fem_irr_penalty
        or args.hard_stop_physical_cycle != 92
        or _parse_cycles(args.mechanical_residual_export_steps) != [379, 409]
        or not args.boundary_first_detect_receipt
        or int(args.n_cycles_physical) < 92
        or args.epochs_rprop != 10000
        or args.epochs_lbfgs != 0
        or args.optim_rel_tol != 5e-7
        or args.mechanical_risk_mode not in {"absent", "on"}
        or int(args.seed) != 1
        or int(args.hidden_layers) != 8
        or int(args.neurons) != 400
        or float(args.res_stiffness) != 0.0
        or args.graph_pidl
        or args.compile
        or args.force_cpu
        or not args.fresh_output_required
        or not args.require_clean_git
        or not args.required_head_commit
    ):
        raise ValueError("G4 resume arguments do not match the frozen U0.12 protocol")
    if args.mechanical_risk_mode == "on" and (
        args.mechanical_risk_lambda != 0.000549728557462236
        or args.mechanical_risk_alpha != 0.85
        or args.mechanical_risk_e_ref != 1.0
        or args.mechanical_risk_l_ref != 1.0
    ):
        raise ValueError("G4 risk-on intervention does not match the frozen ME85 contract")
    mesh = Path(args.mesh_file).expanduser()
    if not mesh.is_absolute():
        mesh = Path(__file__).resolve().parent / mesh
    from rrapinn_g4_restart import SOURCE_MESH_SHA256
    if not mesh.is_file() or _file_sha256(mesh) != SOURCE_MESH_SHA256:
        raise ValueError("G4 resume mesh does not match the frozen U0.12 mesh")
    expected = args.resume_bundle_manifest_sha256.lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise ValueError("--resume-bundle-manifest-sha256 must be 64 lowercase hex characters")
    from rrapinn_g4_restart import validate_bundle

    payload = validate_bundle(Path(args.resume_bundle).expanduser(), expected)
    return {
        "path": payload["bundle_root"],
        "manifest_sha256": payload["manifest_sha256"],
        "start_state": payload["start_state"],
    }


def _preflight_record(args: argparse.Namespace) -> dict:
    risk = _mechanical_risk_config(args)
    checkpoint = _validate_checkpoint_args(args)
    restart = _validate_restart_args(args)
    return {
        "schema": "rrapinn-runner-preflight-v2",
        "training_launched": False,
        "umax": float(args.umax),
        "seed": int(args.seed),
        "hidden_layers": int(args.hidden_layers),
        "neurons": int(args.neurons),
        "n_cycles_physical": int(args.n_cycles_physical),
        "epochs_rprop": args.epochs_rprop,
        "epochs_lbfgs": args.epochs_lbfgs,
        "mechanical_risk_mode": args.mechanical_risk_mode,
        "mechanical_residual_risk": risk,
        "init_checkpoint": checkpoint,
        "resume_bundle": restart,
        "mechanical_residual_export_steps": _parse_cycles(
            args.mechanical_residual_export_steps
        ),
        "boundary_first_detect_receipt": bool(args.boundary_first_detect_receipt),
        "hard_stop_physical_cycle": args.hard_stop_physical_cycle,
        "require_clean_git": bool(args.require_clean_git),
        "fresh_output_required": bool(args.fresh_output_required),
        "required_head_commit": args.required_head_commit,
    }


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        risk_config = _mechanical_risk_config(args)
        init_checkpoint = _validate_checkpoint_args(args)
        restart_bundle = _validate_restart_args(args)
    except ValueError as exc:
        parser.error(str(exc))

    if args.preflight_only:
        print(json.dumps(_preflight_record(args), indent=2, sort_keys=True))
        return

    if min(args.graph_scale, args.graph_uv_scale, args.graph_alpha_scale,
           args.graph_latent_scale) < 0.0:
        parser.error("graph correction scales must be non-negative")
    if args.graph_mask_transition <= 0.0:
        parser.error("--graph-mask-transition must be positive")
    if args.graph_correction_channels != "all" and not (
        args.graph_pidl and args.graph_mode == "hybrid"
    ):
        parser.error("non-all --graph-correction-channels requires --graph-pidl --graph-mode hybrid")
    if args.graph_pidl and args.graph_mode in ("hybrid", "channel_separated") and not args.graph_bounded:
        parser.error("raw-output graph corrections require --graph-bounded")

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = [
        "main.py",
        str(args.hidden_layers),
        str(args.neurons),
        str(args.seed),
        "TrainableReLU",
        str(args.init_coeff),
    ]

    here = Path(__file__).resolve().parent
    if args.require_clean_git:
        status = _git_value(here, "status", "--porcelain")
        if status:
            raise RuntimeError("--require-clean-git failed: tracked or untracked changes present")
    if args.required_head_commit:
        actual_head = _git_value(here, "rev-parse", "HEAD")
        if actual_head != args.required_head_commit:
            raise RuntimeError(
                f"producer HEAD mismatch: expected {args.required_head_commit}, got {actual_head}"
            )
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config  # noqa: WPS433

    fem_mesh = _resolve_mesh_file(here, args.mesh_file)
    coarse_mesh = _resolve_mesh_file(here, args.coarse_mesh_file or config.coarse_mesh_file)

    # Strict benchmark controls: isolate only the history-driver reduction.
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False
    config.fatigue_dict["void_notch_mask"]["enable"] = False
    config.local_patch_dict["enable"] = False
    if hasattr(config, "adaptive_sampling_dict"):
        config.adaptive_sampling_dict["enable"] = False
    if hasattr(config, "sidecar_S1_dict"):
        config.sidecar_S1_dict["enable"] = False
    if hasattr(config, "sidecar_S2_dict"):
        config.sidecar_S2_dict["enable"] = False
    if hasattr(config, "tip_local_net_dict"):
        config.tip_local_net_dict["enable"] = False
    config.symmetry_prior = False

    if args.displacement_steps is not None:
        cycle_disp_values = np.asarray(args.displacement_steps, dtype=float)
        if np.any(cycle_disp_values < -1.0e-12):
            raise ValueError("--displacement-steps must be non-negative")
        if not np.isclose(
            float(np.max(cycle_disp_values)),
            float(args.umax),
            rtol=1.0e-6,
            atol=1.0e-12,
        ):
            raise ValueError(
                "positional umax must equal max(--displacement-steps) for "
                "unambiguous displacement-history provenance"
            )
        step_source = "absolute_displacement"
    else:
        factors = np.asarray(args.substeps, dtype=float)
        cycle_disp_values = factors * float(args.umax)
        step_source = "umax_scaled_factors_legacy"
    if len(cycle_disp_values) < 2:
        raise ValueError("need at least two displacement values per cycle")
    if float(args.umax) <= 0.0:
        raise ValueError("umax must be positive")
    derived_factors = cycle_disp_values / float(args.umax)
    cyclic_disp_steps = np.tile(cycle_disp_values, int(args.n_cycles_physical))
    if args.hard_alpha_recovery_step:
        disp_steps = np.concatenate(([0.0], cyclic_disp_steps))
    else:
        disp_steps = cyclic_disp_steps
    total_steps = int(len(disp_steps))
    recovery_step_offset = 1 if args.hard_alpha_recovery_step else 0
    peak_substep = _peak_substep_index(cycle_disp_values)
    unload_substep = int(len(cycle_disp_values) - 1)
    diag_physical_cycles = _parse_cycles(args.diag_physical_cycles)
    diag_full_physical_cycles = _parse_cycles(args.diag_full_physical_cycles)
    diag_steps = _diag_steps(
        diag_physical_cycles,
        len(cycle_disp_values),
        peak_substep=peak_substep,
        unload_substep=unload_substep,
        step_offset=recovery_step_offset,
        full_physical_cycles=diag_full_physical_cycles,
    )

    config.coarse_mesh_file = coarse_mesh
    config.fine_mesh_file = fem_mesh
    config.PFF_model_dict["residual_stiffness"] = float(args.res_stiffness)
    config.network_dict["compile"] = bool(args.compile)
    config.graph_dict = {
        "enable": bool(args.graph_pidl),
        "type": "mean_message_passing",
        "mode": args.graph_mode,
        "layers": args.graph_layers if args.graph_layers is not None else args.hidden_layers,
        "neurons": args.graph_neurons if args.graph_neurons is not None else args.neurons,
        "scale": float(args.graph_scale),
        "uv_scale": float(args.graph_uv_scale),
        "alpha_scale": float(args.graph_alpha_scale),
        "latent_scale": float(args.graph_latent_scale),
        "mask_x_min": float(args.graph_mask_x_min),
        "mask_x_max": float(args.graph_mask_x_max),
        "mask_half_width": float(args.graph_mask_half_width),
        "mask_transition": float(args.graph_mask_transition),
        "bounded": bool(args.graph_bounded),
        "correction_channels": args.graph_correction_channels,
    }
    if args.graph_pidl and config.numr_dict["gradient_type"] != "numerical":
        raise ValueError("--graph-pidl requires numerical mesh gradients")
    if args.epochs_rprop is not None:
        config.optimizer_dict["n_epochs_RPROP"] = int(args.epochs_rprop)
    if args.epochs_lbfgs is not None:
        config.optimizer_dict["n_epochs_LBFGS"] = int(args.epochs_lbfgs)
    if args.optim_rel_tol is not None:
        config.optimizer_dict["optim_rel_tol"] = float(args.optim_rel_tol)
        config.optimizer_dict["optim_rel_tol_pretrain"] = float(args.optim_rel_tol)
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles_physical)
    config.fatigue_dict["loading_type"] = "cyclic"
    config.fatigue_dict["explicit_cycle_substeps"] = int(len(cycle_disp_values))
    config.fatigue_dict["explicit_cycle_step_mode"] = step_source
    config.fatigue_dict["explicit_cycle_displacements"] = [
        float(x) for x in cycle_disp_values
    ]
    # Some legacy oracle helpers accept factors.  Keep them as a derived
    # internal quantity while preserving displacement values as the source.
    config.fatigue_dict["explicit_cycle_factors"] = [
        float(x) for x in derived_factors
    ]
    config.fatigue_dict["history_driver_mode"] = "current_active"
    config.fatigue_dict["history_driver_reduction"] = {
        "enable": True,
        "mode": args.history_driver_reduction_mode,
    }
    if risk_config is None:
        config.fatigue_dict.pop("mechanical_residual_risk", None)
    else:
        config.fatigue_dict["mechanical_residual_risk"] = risk_config
    config.fatigue_dict["initial_alpha_protocol"] = {
        "enable": bool(args.hard_alpha_recovery_step),
        "mode": "uniform_current_alpha",
        "target_alpha": float(args.hard_alpha_target),
        "preserve_histories": True,
        "requires_first_displacement_zero": True,
    }
    config.numr_dict["irreversibility_penalty"] = {
        "enable": bool(args.fem_irr_penalty),
        "mode": "fem_gp_tri3",
    }
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    config.fatigue_dict["element_diagnostics"] = {
        "enable": True,
        "cycles": diag_steps,
        "every_n_cycles": None,
        "dense_sampling": True,
        "on_fracture": True,
        "dir": "element_diagnostics_probe_driver",
    }
    config.fatigue_dict["gradient_diagnostics"] = {
        "enable": True,
        "cycles": diag_steps,
        "every_n_cycles": 1,
        "dense_sampling": True,
        "on_fracture": True,
    }
    _residual_export_steps = _parse_cycles(args.mechanical_residual_export_steps)
    config.fatigue_dict["mechanical_residual_diagnostics"] = {
        "enable": bool(_residual_export_steps),
        "steps": _residual_export_steps,
        "dir": "mechanical_residual_diagnostics",
        "Umax": float(args.umax),
        "E_ref": float(args.mechanical_risk_e_ref),
        "L_ref": float(args.mechanical_risk_l_ref),
        "explicit_cycle_displacements": [float(x) for x in cycle_disp_values],
        "step_offset": recovery_step_offset,
    }
    config.fatigue_dict["boundary_first_detect_receipt"] = {
        "enable": bool(args.boundary_first_detect_receipt),
        "dir": "boundary_first_detect",
        "explicit_cycle_displacements": [float(x) for x in cycle_disp_values],
        "step_offset": recovery_step_offset,
        "x_min": 0.48,
        "damage_threshold": 0.95,
        "minimum_nodes": 3,
        "hard_stop_physical_cycle": args.hard_stop_physical_cycle,
        "minimum_archive_raw_step": 409 if args.resume_bundle else None,
    }
    config.disp_cyclic = disp_steps

    fat = config.fatigue_dict
    mesh_tag = _mesh_tag(fem_mesh, args.tag)
    if step_source == "absolute_displacement":
        step_tag = "u" + "-".join(f"{x:g}" for x in cycle_disp_values)
    else:
        step_tag = "s" + "-".join(f"{x:g}" for x in derived_factors)
    graph_variant_tag = ""
    if args.graph_pidl and args.graph_mode == "hybrid":
        graph_variant_tag = f"_{args.graph_correction_channels}_s{args.graph_scale:g}"
    elif args.graph_pidl and args.graph_mode == "channel_separated":
        graph_variant_tag = f"_suv{args.graph_uv_scale:g}_sa{args.graph_alpha_scale:g}"
    elif args.graph_pidl and args.graph_mode == "damage_latent":
        graph_variant_tag = f"_slat{args.graph_latent_scale:g}"
    dir_name = (
        f"probeDriver_hl{config.network_dict['hidden_layers']}"
        f"_n{config.network_dict['neurons']}"
        f"_seed{config.network_dict['seed']}"
        f"_{config.PFF_model_dict['PFF_model']}"
        f"_{config.numr_dict['gradient_type']}"
        f"_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}"
        f"_Ncyc{fat['n_cycles']}_Nstep{total_steps}"
        f"_U{fat['disp_max']}"
        f"_{mesh_tag}"
        f"{'_graphPIDL_' + args.graph_mode if args.graph_pidl else ''}"
        f"{graph_variant_tag}"
        f"_current_active_{args.history_driver_reduction_mode}"
        f"{'_' + _format_eta_tag(args.res_stiffness) if args.res_stiffness > 0.0 else ''}"
        f"{'_femIrrGP3' if args.fem_irr_penalty else ''}"
        f"{'_hardAlphaRecoverU0' if args.hard_alpha_recovery_step else ''}"
        f"_mechRisk-{args.mechanical_risk_mode}"
        f"_{step_tag}"
        f"{'_compile' if args.compile else ''}"
    )
    config.model_path = config.resolve_archive_dir(here, dir_name)
    config.trainedModel_path = config.model_path / Path("best_models/")
    config.intermediateModel_path = config.model_path / Path("intermediate_models/")
    if args.fresh_output_required and any(config.model_path.iterdir()):
        raise RuntimeError(f"fresh G3 output required but archive is non-empty: {config.model_path}")
    config.model_path.mkdir(parents=True, exist_ok=True)
    config.intermediateModel_path.mkdir(parents=True, exist_ok=True)
    if restart_bundle is not None:
        from rrapinn_g4_restart import stage_bundle

        stage_bundle(
            Path(restart_bundle["path"]),
            config.trainedModel_path,
            restart_bundle["manifest_sha256"],
        )
    else:
        config.trainedModel_path.mkdir(parents=True, exist_ok=True)
    if init_checkpoint is not None:
        init_destination = config.trainedModel_path / "trained_1NN_initTraining.pt"
        if init_destination.exists():
            existing_sha = _file_sha256(init_destination)
            if existing_sha != init_checkpoint["sha256"]:
                raise RuntimeError(
                    f"refusing to overwrite different initialization checkpoint: {init_destination}"
                )
        else:
            shutil.copy2(init_checkpoint["path"], init_destination)
    try:
        config.writer.close()
    except Exception:
        pass
    config.writer = config.SummaryWriter(config.model_path / Path("TBruns"))
    runner_path = Path(__file__).resolve()
    runner_git_commit = _git_value(here, "rev-parse", "HEAD")
    runner_git_branch = _git_value(here, "rev-parse", "--abbrev-ref", "HEAD")
    runner_sha256 = _file_sha256(runner_path)
    provenance_path = config.model_path / "RUN_PROVENANCE.json"
    provenance = {
        "schema": "rrapinn-g3-run-provenance-v1",
        "status": "prepared_not_completed",
        "runner_git_commit": runner_git_commit,
        "runner_git_branch": runner_git_branch,
        "runner_sha256": runner_sha256,
        "required_head_commit": args.required_head_commit,
        "git_clean_required": bool(args.require_clean_git),
        "mechanical_risk_mode": args.mechanical_risk_mode,
        "mechanical_residual_risk": risk_config,
        "init_checkpoint": init_checkpoint,
        "resume_bundle": restart_bundle,
        "mechanical_residual_export_steps": _residual_export_steps,
        "boundary_first_detect_receipt": bool(args.boundary_first_detect_receipt),
        "hard_stop_physical_cycle": args.hard_stop_physical_cycle,
        "training_authorized_by_packet": False,
        "note": "Presence of this file is not user authorization; launch authorization is external.",
    }
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")

    with open(config.model_path / "model_settings.txt", "w", encoding="utf-8") as handle:
        handle.write("runner: run_fem_mesh_probe_driver_umax.py\n")
        handle.write(f"runner_git_commit: {runner_git_commit}\n")
        handle.write(f"runner_git_branch: {runner_git_branch}\n")
        handle.write(f"runner_sha256: {runner_sha256}\n")
        handle.write(f"umax: {args.umax}\n")
        handle.write(f"n_cycles_physical: {args.n_cycles_physical}\n")
        handle.write(f"n_training_steps: {total_steps}\n")
        handle.write(f"seed: {args.seed}\n")
        handle.write(f"hidden_layers: {config.network_dict['hidden_layers']}\n")
        handle.write(f"neurons: {config.network_dict['neurons']}\n")
        handle.write(f"init_coeff: {args.init_coeff}\n")
        handle.write(f"n_epochs_RPROP: {config.optimizer_dict['n_epochs_RPROP']}\n")
        handle.write(f"n_epochs_LBFGS: {config.optimizer_dict['n_epochs_LBFGS']}\n")
        handle.write(f"optim_rel_tol: {config.optimizer_dict['optim_rel_tol']}\n")
        handle.write(f"resume_bundle: {restart_bundle}\n")
        handle.write(f"mechanical_residual_export_steps: {_residual_export_steps}\n")
        handle.write(
            f"boundary_first_detect_receipt: {bool(args.boundary_first_detect_receipt)}\n"
        )
        handle.write(f"hard_stop_physical_cycle: {args.hard_stop_physical_cycle}\n")
        handle.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        handle.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        handle.write(f"mesh_tag: {mesh_tag}\n")
        handle.write(f"torch_compile: {bool(args.compile)}\n")
        representation = (
            f"GraphPIDL_{args.graph_mode}" if args.graph_pidl else "coordinate_MLP"
        )
        handle.write(f"representation: {representation}\n")
        handle.write(f"graph_dict: {config.graph_dict}\n")
        if args.graph_pidl and args.graph_mode == "channel_separated":
            handle.write(
                "graph_scale_semantics: uv_scale and alpha_scale independently "
                "bound additive raw-output corrections; they do not bound physical "
                "displacement or constrained alpha\n"
            )
        elif args.graph_pidl and args.graph_mode == "damage_latent":
            handle.write(
                "graph_scale_semantics: latent_scale bounds the graph update before "
                "the alpha head; UV uses the unmodified MLP latent\n"
            )
        else:
            handle.write(
                "graph_scale_semantics: bounds additive raw-network-output correction; "
                "it is not a bound on physical displacement or constrained alpha\n"
            )
        handle.write("supervision: physics_only_no_FEM_field_targets\n")
        handle.write(f"residual_stiffness: {float(args.res_stiffness)}\n")
        handle.write(
            "PFF_model_dict.residual_stiffness: "
            f"{config.PFF_model_dict['residual_stiffness']}\n"
        )
        handle.write("Edegrade_formula: (1-alpha)^2 + residual_stiffness\n")
        handle.write("history_driver_mode: current_active\n")
        handle.write(f"history_driver_reduction: {fat['history_driver_reduction']}\n")
        handle.write(
            f"irreversibility_penalty: {config.numr_dict['irreversibility_penalty']}\n"
        )
        handle.write(f"initial_alpha_protocol: {fat['initial_alpha_protocol']}\n")
        handle.write(f"recovery_step_offset: {recovery_step_offset}\n")
        handle.write(f"peak_substep_index: {peak_substep}\n")
        handle.write(f"unload_substep_index: {unload_substep}\n")
        handle.write(f"explicit_cycle_step_mode: {step_source}\n")
        handle.write(f"explicit_cycle_substeps: {fat['explicit_cycle_substeps']}\n")
        handle.write(
            f"explicit_cycle_displacements: {fat['explicit_cycle_displacements']}\n"
        )
        handle.write(
            "derived_explicit_cycle_factors_for_internal_oracles: "
            f"{fat['explicit_cycle_factors']}\n"
        )
        handle.write(f"diag_physical_cycles: {diag_physical_cycles}\n")
        handle.write(f"diag_full_physical_cycles: {diag_full_physical_cycles}\n")
        handle.write(f"void_notch_mask_enable: {fat['void_notch_mask']['enable']}\n")
        handle.write("local_patch_enable: False\n")
        handle.write("adaptive_sampling_enable: False\n")
        handle.write("delta1_enable: False\n")
        handle.write("j_path_enable: False\n")
        handle.write(f"mechanical_risk_mode: {args.mechanical_risk_mode}\n")
        handle.write(f"mechanical_residual_risk: {fat.get('mechanical_residual_risk', '<absent>')}\n")
        handle.write(f"init_checkpoint: {init_checkpoint}\n")
        handle.write(f"element_diagnostics_steps: {diag_steps}\n")
        handle.write("element_diagnostics_fields: mechanics+energy+driver\n")
        handle.write(
            "diagnostic_raw_export_semantics: "
            "psi_raw_elem=psi_active/g_alpha legacy alias; "
            "psi_raw_from_g_alpha_elem=psi_active/g_alpha; "
            "psi_raw_from_g_solver_elem=psi_active/g_solver; "
            "g_solver_override_active records whether solver override was active\n"
        )
        handle.write("gradient_diagnostics: pre_history_refresh_every_step\n")
        handle.write(
            "gradient_diagnostics_columns: step,E_el,E_d,E_hist,"
            "grad_E_el,grad_E_d,grad_E_hist\n"
        )
        if args.hard_alpha_recovery_step:
            handle.write(
                "state_mapping: step0=U0_hard_alpha_recovery; "
                f"cN_peak={recovery_step_offset}+{len(cycle_disp_values)}*(N-1)+{peak_substep}; "
                f"cN_unloaded={recovery_step_offset}+{len(cycle_disp_values)}*(N-1)+{unload_substep}\n"
            )
            handle.write(
                "recovery_semantics: current NN alpha is set to hard target before "
                "step0; hist_alpha, hist_fat, f_fatigue, and psi_plus_prev remain "
                "state0 baseline until step0 post-commit\n"
            )
        handle.write(
            "purpose: strict FEM-mesh fatigue-driver reduction with optional "
            "FEM-like irreversibility penalty quadrature\n"
        )

    print("=" * 72)
    print("PIDL FEM-mesh probe-averaged fatigue-driver reduction")
    print(f"  U_max          = {args.umax} | physical cycles = {args.n_cycles_physical}")
    print(f"  training steps = {total_steps} | seed = {args.seed}")
    print(
        f"  network        = {config.network_dict['hidden_layers']}x"
        f"{config.network_dict['neurons']}"
    )
    representation = f"GraphPIDL {args.graph_mode}" if args.graph_pidl else "coordinate MLP"
    print(f"  representation = {representation}")
    print(
        f"  epochs         = RPROP {config.optimizer_dict['n_epochs_RPROP']} | "
        f"LBFGS {config.optimizer_dict['n_epochs_LBFGS']}"
    )
    print(f"  step mode      = {step_source}")
    print(f"  disp steps     = {list(cycle_disp_values)}")
    print(
        f"  peak/unload    = substep {peak_substep} U={cycle_disp_values[peak_substep]:g} | "
        f"substep {unload_substep} U={cycle_disp_values[unload_substep]:g}"
    )
    print(f"  FEM mesh       = {fem_mesh}")
    print(f"  coarse mesh    = {coarse_mesh}")
    print("  history driver = current_active")
    print(f"  reduction      = {args.history_driver_reduction_mode}")
    print(f"  residual eta   = {args.res_stiffness:.3e}")
    print(f"  irr penalty    = {'fem_gp_tri3' if args.fem_irr_penalty else 'legacy'}")
    if args.hard_alpha_recovery_step:
        print(f"  recovery step  = step0 U=0 after hard alpha target {args.hard_alpha_target:g}")
        print(
            "  mapping        = "
            f"cN_peak -> {recovery_step_offset}+{len(cycle_disp_values)}*(N-1)+{peak_substep}, "
            f"cN_unloaded -> {recovery_step_offset}+{len(cycle_disp_values)}*(N-1)+{unload_substep}"
        )
    print("  void mask      = disabled")
    print("  other sampling = local_patch/adaptive/delta1/J-path disabled")
    print(f"  mechanical risk= {args.mechanical_risk_mode} | {risk_config}")
    print(f"  elem diag      = {diag_steps}")
    print("  gradient diag  = pre-history-refresh every step")
    print(f"  compile        = {bool(args.compile)}")
    print(f"  device         = {config.device}")
    print(f"  archive        = {dir_name}")
    print(f"  full path      = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})
    checkpoint_rows = []
    for path in sorted(config.trainedModel_path.glob("checkpoint_step_*.pt")):
        checkpoint_rows.append({"name": path.name, "sha256": _file_sha256(path)})
    if args.fresh_output_required and not checkpoint_rows:
        raise RuntimeError("G3 smoke completed without writing a step checkpoint")
    metrics = {
        "schema": "rrapinn-g3-smoke-metrics-v1",
        "execution_returned": True,
        "mechanical_risk_mode": args.mechanical_risk_mode,
        "mechanical_residual_risk": risk_config,
        "checkpoint_count": len(checkpoint_rows),
        "checkpoints": checkpoint_rows,
        "claim_boundary": "Producer smoke completion only; no efficacy claim.",
    }
    (config.model_path / "g3_smoke_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )
    provenance["status"] = "execution_returned_pending_cross_arm_validation"
    provenance["checkpoint_count"] = len(checkpoint_rows)
    provenance_path.write_text(json.dumps(provenance, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
