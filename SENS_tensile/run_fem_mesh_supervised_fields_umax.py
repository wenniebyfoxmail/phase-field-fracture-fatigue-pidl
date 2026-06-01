#!/usr/bin/env python3
"""Run strict FEM-mesh PIDL with cyclewise FEM field supervision.

This discriminator asks which early field, if forced toward FEM for c1-cK,
most reduces the PIDL/FEM mechanism gap:

  alpha      : phase-field damage d
  alpha_bar  : fatigue/history variable after the candidate refresh
  psi_raw    : undegraded tensile elastic driver
  psi_active : active fatigue driver g(alpha) * psi_raw
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import numpy as np
import torch


DEFAULT_FEM_HANDOFF_NAME = "_pidl_handoff_reverseBC_u12_soft_hist0_nstep10_2026-05-29"


def _default_fem_handoff_dir() -> Path:
    env = os.environ.get("PIDL_FEM_HANDOFF_DIR")
    if env:
        return Path(env).expanduser()
    here = Path(__file__).resolve().parent
    rel = (
        Path("_analysis_fem_mechanism_20260528")
        / "request21_fem_nstep"
        / "source_handoff"
        / DEFAULT_FEM_HANDOFF_NAME
    )
    candidates = [here.parent / rel]
    for parent in here.parents:
        candidates.append(parent / "upload code" / rel)
        candidates.append(parent / rel)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return here.parent / rel


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


def _default_loss(target: str) -> str:
    return "mse_lin" if target in {"alpha", "alpha_bar", "history"} else "mse_log"


def _parse_cycles(raw: str) -> str:
    return ",".join(str(int(x)) for x in raw.split(",") if x.strip())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("umax", type=float)
    p.add_argument("--target", required=True,
                   choices=("alpha", "alpha_bar", "history", "psi_raw", "psi_active"))
    p.add_argument("--K", type=int, default=20,
                   help="Last cycle with FEM supervision.")
    p.add_argument("--n-cycles", type=int, default=20)
    p.add_argument("--lambda", dest="lam", type=float, default=1.0)
    p.add_argument("--loss-kind", default="auto",
                   choices=("auto", "mse_log", "mse_lin", "mse_rel"))
    p.add_argument("--supervised-every", type=int, default=1)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    p.add_argument("--fem-fields-mat", type=Path,
                   default=_default_fem_handoff_dir() / "reverseBC_u12_soft_hist0_nstep10_element_fields_c1_c69.mat")
    p.add_argument("--fem-mesh-mat", type=Path,
                   default=_default_fem_handoff_dir() / "mesh_geometry.mat")
    p.add_argument("--tag", default="")
    p.add_argument("--diagnostic-cycles", default="0,1,2,3,10,20")
    p.add_argument("--no-field-files", action="store_true")
    p.add_argument("--fracture-confirm-cycles", type=int, default=3)
    p.add_argument("--plot-every", type=int, default=20)
    p.add_argument("--joint-epochs", type=int, default=None)
    p.add_argument("--pretrain-mode", default="default",
                   choices=("default", "short", "off"))
    p.add_argument("--pretrain-lbfgs-epochs", type=int, default=None)
    p.add_argument("--pretrain-rprop-epochs", type=int, default=None)
    p.add_argument("--compile", action="store_true")
    p.add_argument("--force-cpu", action="store_true")
    args = p.parse_args()

    if not (1 <= args.K <= args.n_cycles):
        raise SystemExit(f"K={args.K} must be in [1, n_cycles={args.n_cycles}]")
    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]
    here = Path(__file__).resolve().parent
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config  # noqa: WPS433
    from construct_model import construct_model
    from fem_supervision import CyclewiseFEMFieldSupervision
    from field_computation import FieldComputation
    from input_data_from_mesh import prep_input_data
    from model_train import train

    fem_mesh = _resolve_mesh_file(here, args.mesh_file)
    coarse_mesh = _resolve_mesh_file(here, config.coarse_mesh_file)

    # Strict aligned benchmark controls. This runner changes only the FEM
    # supervised auxiliary target; the variational physics remains unchanged.
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
    config.local_patch_dict["enable"] = False
    config.discontinuity_dict["enable"] = False
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
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    config.rebuild_disp_cyclic()

    diagnostic_cycles = _parse_cycles(args.diagnostic_cycles)
    config.fatigue_dict["state_timing_export"] = {
        "enable": True,
        "cycles": diagnostic_cycles,
        "write_fields": not bool(args.no_field_files),
        "dir": "pidl_state_timing",
    }
    config.fatigue_dict["gradient_balance_probe"] = {
        "enable": True,
        "cycles": diagnostic_cycles,
        "dir": "gradient_balance",
    }
    pretrain_cfg = {"mode": args.pretrain_mode}
    if args.pretrain_lbfgs_epochs is not None:
        pretrain_cfg["lbfgs_epochs"] = int(args.pretrain_lbfgs_epochs)
    if args.pretrain_rprop_epochs is not None:
        pretrain_cfg["rprop_epochs"] = int(args.pretrain_rprop_epochs)
    if args.pretrain_mode == "short":
        pretrain_cfg.setdefault("lbfgs_epochs", 1)
        pretrain_cfg.setdefault("rprop_epochs", 1000)
    config.training_dict["pretrain"] = pretrain_cfg

    loss_kind = _default_loss(args.target) if args.loss_kind == "auto" else args.loss_kind
    target_tag = args.target.replace("history", "alpha_bar")
    mesh_tag = _mesh_tag(fem_mesh, args.tag)
    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    suffix = (
        f"_femmesh_{mesh_tag}_sup{target_tag}_K{args.K}"
        f"_lam{args.lam:g}_loss{loss_kind}_pretrain-{args.pretrain_mode}"
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

    fem_sup = CyclewiseFEMFieldSupervision(args.fem_fields_mat, args.fem_mesh_mat)
    pffmodel, matprop, network = construct_model(
        config.PFF_model_dict, config.mat_prop_dict,
        config.network_dict, config.domain_extrema, config.device,
        williams_dict=config.williams_dict,
        fourier_dict=config.fourier_dict,
        discontinuity_dict=config.discontinuity_dict,
    )
    inp_c, T_conn_c, _, _ = prep_input_data(
        matprop, pffmodel, config.crack_dict, config.numr_dict,
        mesh_file=config.fine_mesh_file, device=config.device,
    )
    inp_np = inp_c.detach().cpu().numpy()
    T_np = T_conn_c.detach().cpu().numpy()
    pidl_centroids = inp_np[T_np].mean(axis=1)
    target_c1 = fem_sup.target_at_cycle(args.target, 1, pidl_centroids)

    mit8_dict = {
        "enable": True,
        "K": int(args.K),
        "lambda": float(args.lam),
        "fem_sup": fem_sup,
        "pidl_centroids": pidl_centroids,
        "loss_kind": loss_kind,
        "every_n_epochs": int(args.supervised_every),
        "mask": None,
        "target_kind": args.target,
    }

    with open(config.model_path / "model_settings.txt", "w", encoding="utf-8") as f:
        f.write("runner: run_fem_mesh_supervised_fields_umax.py\n")
        f.write(f"umax: {args.umax}\n")
        f.write(f"n_cycles: {args.n_cycles}\n")
        f.write(f"K: {args.K}\n")
        f.write(f"target: {args.target}\n")
        f.write(f"lambda: {args.lam}\n")
        f.write(f"loss_kind: {loss_kind}\n")
        f.write(f"supervised_every: {args.supervised_every}\n")
        f.write(f"seed: {args.seed}\n")
        f.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        f.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        f.write(f"fem_fields_mat: {args.fem_fields_mat}\n")
        f.write(f"fem_mesh_mat: {args.fem_mesh_mat}\n")
        f.write(f"fem_available_targets: {fem_sup.available_targets()}\n")
        f.write(f"diagnostic_cycles: {diagnostic_cycles}\n")
        f.write(f"pretrain: {pretrain_cfg}\n")
        f.write(f"joint_epochs: {config.optimizer_dict['n_epochs_RPROP']}\n")
        f.write("purpose: c1-cK field-specific FEM supervision discriminator\n")

    print("=" * 72)
    print("Strict FEM-mesh field-supervised PIDL")
    print(f"  U_max       = {args.umax} | n_cycles={args.n_cycles} | K={args.K}")
    print(f"  target      = {args.target} | lambda={args.lam} | loss={loss_kind}")
    print(f"  FEM fields  = {args.fem_fields_mat}")
    print(f"  FEM mesh    = {args.fem_mesh_mat}")
    print(f"  PIDL mesh   = {fem_mesh}")
    print(f"  target c1   = max {target_c1.max().item():.3e}, mean {target_c1.mean().item():.3e}")
    print(f"  diagnostics= {diagnostic_cycles}")
    print(f"  archive     = {dir_name}")
    print(f"  full path   = {config.model_path}")
    print("=" * 72)

    field_comp = FieldComputation(
        net=network,
        domain_extrema=config.domain_extrema,
        lmbda=torch.tensor([0.0], device=config.device),
        theta=config.loading_angle,
        alpha_constraint=config.numr_dict["alpha_constraint"],
        williams_dict=config.williams_dict,
        ansatz_dict=config.ansatz_dict,
        l0=config.mat_prop_dict["l0"],
        symmetry_prior=config.symmetry_prior,
        exact_bc_dict=config.exact_bc_dict,
        local_patch_dict=config.local_patch_dict,
    )
    field_comp.net = field_comp.net.to(config.device)
    field_comp.domain_extrema = field_comp.domain_extrema.to(config.device)
    field_comp.theta = field_comp.theta.to(config.device)

    train(
        field_comp, config.disp_cyclic, pffmodel, matprop,
        config.crack_dict, config.numr_dict,
        config.optimizer_dict, config.training_dict,
        config.coarse_mesh_file, config.fine_mesh_file,
        config.device, config.trainedModel_path, config.intermediateModel_path,
        config.writer,
        fatigue_dict=config.fatigue_dict,
        adaptive_sampling_dict=config.adaptive_sampling_dict,
        mit8_dict=mit8_dict,
    )


if __name__ == "__main__":
    main()
