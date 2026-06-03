#!/usr/bin/env python3
"""Run strict FEM-mesh PIDL with early-cycle state-timing exports.

This is an alignment diagnostic, not a new architecture branch.  It exports
pre-fit, post-fit/pre-history-refresh, and post-history-refresh states for the
first PIDL cycles/steps so we can compare against FEM state timing directly.

Optional ``--substeps`` turns the one-peak-per-cycle PIDL abstraction into a
FEM-like sequence of load factors while keeping the same strict FEM-mesh setup.
"""
from __future__ import annotations

import argparse
import os
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


def _parse_factors(raw: str) -> list[float]:
    if raw is None or str(raw).strip() == "":
        return []
    vals = [float(x) for x in str(raw).split(",") if x.strip()]
    if len(vals) < 2:
        raise argparse.ArgumentTypeError("need at least two substep factors")
    return vals


def _auto_state_cycles(total_steps: int, n_substeps: int | None, raw: str) -> str:
    if raw != "auto":
        return raw
    if n_substeps:
        return ",".join(str(i) for i in range(min(total_steps, 4 * n_substeps)))
    return "0,1,2,3"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=4,
                   help="Physical cycles for substep mode; PIDL cycles otherwise.")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    p.add_argument("--tag", default="")
    p.add_argument("--history-driver", default="active_degraded",
                   choices=("active_degraded", "raw", "lagged_degraded"))
    p.add_argument("--history-update-timing", default="post_fit",
                   choices=("post_fit", "pre_fit"),
                   help="State used to refresh fatigue history. post_fit is baseline; pre_fit tests whether the current fitted alpha suppresses wake history.")
    p.add_argument("--substeps", default="",
                   help="Comma-separated load factors, e.g. 0.25,0.5,0.75,1,0. Empty = one peak per cycle.")
    p.add_argument("--state-cycles", default="auto",
                   help="'auto' or comma-separated training step/cycle indices to export.")
    p.add_argument("--no-field-files", action="store_true",
                   help="Write only the state-timing CSV, not per-state npz fields.")
    p.add_argument("--gradient-balance", action="store_true",
                   help="Print/export grad norms for log(E_el), log(E_d), log(E_hist).")
    p.add_argument("--gradient-cycles", default="auto",
                   help="'auto' or comma-separated training step/cycle indices for gradient probes.")
    p.add_argument("--fracture-confirm-cycles", type=int, default=3)
    p.add_argument("--plot-every", type=int, default=20)
    p.add_argument("--compile", action="store_true")
    p.add_argument("--force-cpu", action="store_true")
    p.add_argument("--joint-epochs", type=int, default=None,
                   help="Override main-cycle RPROP epochs; mostly for smoke tests.")
    p.add_argument("--pretrain-mode", default="default",
                   choices=("default", "short", "off"),
                   help="default = current pretraining; short/off are diagnostics only.")
    p.add_argument("--pretrain-lbfgs-epochs", type=int, default=None)
    p.add_argument("--pretrain-rprop-epochs", type=int, default=None)
    args = p.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

    here = Path(__file__).resolve().parent
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config  # noqa: WPS433

    fem_mesh = _resolve_mesh_file(here, args.mesh_file)
    coarse_mesh = _resolve_mesh_file(here, config.coarse_mesh_file)
    factors = np.asarray(_parse_factors(args.substeps), dtype=float)

    # Strict benchmark controls: isolate timing/history behavior.
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
    config.local_patch_dict["enable"] = False
    config.fatigue_dict.setdefault("local_patch_training", {})["enable"] = False
    config.fatigue_dict.setdefault("staged_head_training", {})["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False
    if hasattr(config, "adaptive_sampling_dict"):
        config.adaptive_sampling_dict["enable"] = False
    if hasattr(config, "sidecar_S1_dict"):
        config.sidecar_S1_dict["enable"] = False
    if hasattr(config, "sidecar_S2_dict"):
        config.sidecar_S2_dict["enable"] = False
    if hasattr(config, "tip_local_net_dict"):
        config.tip_local_net_dict["enable"] = False
    config.symmetry_prior = False

    config.coarse_mesh_file = coarse_mesh
    config.fine_mesh_file = fem_mesh
    config.network_dict["compile"] = bool(args.compile)
    if args.joint_epochs is not None:
        config.optimizer_dict["n_epochs_RPROP"] = int(args.joint_epochs)
    config.fatigue_dict["history_driver_mode"] = args.history_driver
    config.fatigue_dict["history_update_timing"] = args.history_update_timing
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)

    if factors.size:
        disp_steps = np.tile(factors * float(args.umax), int(args.n_cycles))
        config.fatigue_dict["loading_type"] = "cyclic"
        config.fatigue_dict["explicit_cycle_substeps"] = int(len(factors))
        config.fatigue_dict["explicit_cycle_factors"] = [float(x) for x in factors]
        config.disp_cyclic = disp_steps
        total_steps = int(len(disp_steps))
    else:
        config.fatigue_dict.pop("explicit_cycle_substeps", None)
        config.fatigue_dict.pop("explicit_cycle_factors", None)
        config.rebuild_disp_cyclic()
        total_steps = int(args.n_cycles)

    state_cycles = _auto_state_cycles(
        total_steps,
        int(len(factors)) if factors.size else None,
        args.state_cycles,
    )
    gradient_cycles = _auto_state_cycles(
        total_steps,
        int(len(factors)) if factors.size else None,
        args.gradient_cycles,
    )
    config.fatigue_dict["state_timing_export"] = {
        "enable": True,
        "cycles": state_cycles,
        "write_fields": not bool(args.no_field_files),
        "dir": "pidl_state_timing",
    }
    config.fatigue_dict["gradient_balance_probe"] = {
        "enable": bool(args.gradient_balance),
        "cycles": gradient_cycles,
        "dir": "gradient_balance",
    }

    pretrain_cfg = {"mode": args.pretrain_mode}
    if args.pretrain_mode == "short":
        pretrain_cfg["lbfgs_epochs"] = (
            1 if args.pretrain_lbfgs_epochs is None
            else int(args.pretrain_lbfgs_epochs)
        )
        pretrain_cfg["rprop_epochs"] = (
            1000 if args.pretrain_rprop_epochs is None
            else int(args.pretrain_rprop_epochs)
        )
    else:
        if args.pretrain_lbfgs_epochs is not None:
            pretrain_cfg["lbfgs_epochs"] = int(args.pretrain_lbfgs_epochs)
        if args.pretrain_rprop_epochs is not None:
            pretrain_cfg["rprop_epochs"] = int(args.pretrain_rprop_epochs)
    config.training_dict["pretrain"] = pretrain_cfg

    fat = config.fatigue_dict
    sub_tag = (
        "_substeps_" + "-".join(f"{x:g}" for x in factors)
        if factors.size else "_onepeak"
    )
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_Nphys{fat['n_cycles']}_Nstep{total_steps}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    tag = _mesh_tag(fem_mesh, args.tag)
    suffix = (
        f"_femmesh_{tag}_stateTiming_{args.history_driver}"
        f"_histUpdate-{args.history_update_timing}"
        f"{sub_tag}_pretrain-{args.pretrain_mode}"
        f"{'_compile' if args.compile else ''}"
    )
    dir_name = (
        "hl_" + str(config.network_dict["hidden_layers"])
        + "_Neurons_" + str(config.network_dict["neurons"])
        + "_activation_" + config.network_dict["activation"]
        + "_coeff_" + str(config.network_dict["init_coeff"])
        + "_Seed_" + str(config.network_dict["seed"])
        + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
        + "_gradient_" + str(config.numr_dict["gradient_type"])
        + fatigue_tag
        + suffix
    )
    config.model_path = config.resolve_archive_dir(here, dir_name)
    config.trainedModel_path = config.model_path / Path("best_models/")
    config.intermediateModel_path = config.model_path / Path("intermediate_models/")
    config.model_path.mkdir(parents=True, exist_ok=True)
    config.trainedModel_path.mkdir(parents=True, exist_ok=True)
    config.intermediateModel_path.mkdir(parents=True, exist_ok=True)
    try:
        config.writer.close()
    except Exception:
        pass
    config.writer = config.SummaryWriter(config.model_path / Path("TBruns"))

    with open(config.model_path / "model_settings.txt", "w", encoding="utf-8") as f:
        f.write("runner: run_fem_mesh_state_timing_umax.py\n")
        f.write(f"umax: {args.umax}\n")
        f.write(f"n_cycles_physical: {args.n_cycles}\n")
        f.write(f"n_training_steps: {total_steps}\n")
        f.write(f"seed: {args.seed}\n")
        f.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        f.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        f.write(f"mesh_tag: {tag}\n")
        f.write(f"history_driver_mode: {args.history_driver}\n")
        f.write(f"history_update_timing: {args.history_update_timing}\n")
        f.write(f"substeps: {list(factors)}\n")
        f.write(f"state_cycles: {state_cycles}\n")
        f.write(f"write_state_fields: {not bool(args.no_field_files)}\n")
        f.write(f"gradient_balance: {bool(args.gradient_balance)}\n")
        f.write(f"gradient_cycles: {gradient_cycles}\n")
        f.write(f"pretrain: {pretrain_cfg}\n")
        f.write(f"joint_epochs: {config.optimizer_dict['n_epochs_RPROP']}\n")
        f.write(f"torch_compile: {bool(args.compile)}\n")
        f.write("purpose: strict FEM-mesh PIDL state-timing/history-refresh diagnostic\n")

    print("=" * 72)
    print("PIDL FEM-mesh state-timing diagnostic")
    print(f"  U_max       = {args.umax} | physical cycles = {args.n_cycles} | steps = {total_steps}")
    print(f"  FEM mesh    = {fem_mesh}")
    print(f"  history     = {args.history_driver}")
    print(f"  hist update = {args.history_update_timing}")
    print(f"  substeps    = {list(factors) if factors.size else 'one-peak-per-cycle'}")
    print(f"  state export= {state_cycles}")
    print(f"  grad balance= {bool(args.gradient_balance)} ({gradient_cycles})")
    print(f"  pretrain    = {pretrain_cfg}")
    print(f"  joint epochs= {config.optimizer_dict['n_epochs_RPROP']}")
    print(f"  archive     = {dir_name}")
    print(f"  full path   = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
