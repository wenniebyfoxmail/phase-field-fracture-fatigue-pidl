#!/usr/bin/env python3
"""Inverse alpha_T retry on the strict FEM-mesh soft-hist0 PIDL setting.

The forward PIDL setting is intentionally the same family as
``run_fem_mesh_umax.py``: reverseBC-compatible baseline ansatz, FEM triangular
mesh, soft-hist0 mesh, fixed irreversibility weight, and no adaptive residual
reweighting. The only trainable physical scalar is Carrara ``alpha_T``.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


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


def _bool_mask_from_kind(kind, pidl_centroids, *, x_min, y_abs_max):
    if kind == "full":
        return None

    import torch

    cx = torch.from_numpy(pidl_centroids[:, 0])
    cy = torch.from_numpy(pidl_centroids[:, 1])
    if kind == "boundary":
        return cx >= x_min
    if kind == "crack_path":
        return (cy.abs() <= y_abs_max) & (cx >= 0.0)
    if kind == "boundary_or_crack":
        return (cx >= x_min) | ((cy.abs() <= y_abs_max) & (cx >= 0.0))
    raise ValueError(f"unknown mask kind {kind!r}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    p.add_argument("--tag", default="softHist0")
    p.add_argument("--fem-dir", default="")
    p.add_argument("--K", type=int, default=69,
                   help="Last FEM cycle used for observation loss.")
    p.add_argument("--fem-cycle-offset", type=int, default=1,
                   help="FEM cycle used at PIDL index j is j + offset.")
    p.add_argument("--lambda-alpha", type=float, default=1.0)
    p.add_argument("--supervised-every", type=int, default=10)
    p.add_argument("--mask-kind", default="boundary_or_crack",
                   choices=["full", "boundary", "crack_path", "boundary_or_crack"])
    p.add_argument("--mask-x-min", type=float, default=0.45)
    p.add_argument("--mask-y-abs-max", type=float, default=0.05)
    p.add_argument("--alphaT-init", type=float, default=0.25)
    p.add_argument("--alphaT-min", type=float, default=0.05)
    p.add_argument("--alphaT-max", type=float, default=2.0)
    p.add_argument("--tol-ir", type=float, default=5e-3,
                   help="PIDL irreversibility tolerance; default matches strict FEM-mesh baseline.")
    p.add_argument("--fracture-confirm-cycles", type=int, default=3)
    p.add_argument("--plot-every", type=int, default=20)
    p.add_argument("--diagnostic-cycles", default="0,19,39,68",
                   help="PIDL j indices saved with raw/active element diagnostics.")
    p.add_argument("--force-cpu", action="store_true")
    args = p.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = [
        "run_fem_mesh_inverse_alphaT_umax.py",
        "8", "400", str(args.seed), "TrainableReLU", "1.0",
    ]

    here = Path(__file__).resolve().parent
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import numpy as np
    import torch

    import config
    from construct_model import construct_model
    from fem_supervision import FEMSupervision
    from field_computation import FieldComputation
    from input_data_from_mesh import prep_input_data
    from model_train import train

    fem_mesh = _resolve_mesh_file(here, args.mesh_file)
    coarse_mesh = _resolve_mesh_file(here, config.coarse_mesh_file)

    # Strict FEM-mesh soft-hist0 PIDL baseline knobs.
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
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

    diag_cycles = [int(c.strip()) for c in str(args.diagnostic_cycles).split(",") if c.strip()]

    config.coarse_mesh_file = coarse_mesh
    config.fine_mesh_file = fem_mesh
    config.PFF_model_dict["tol_ir"] = float(args.tol_ir)
    config.fatigue_dict["accum_type"] = "carrara"
    config.fatigue_dict["degrad_type"] = "asymptotic"
    config.fatigue_dict["alpha_T"] = 0.5
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    config.fatigue_dict["enable_E_fallback"] = False
    config.fatigue_dict["element_diagnostics"] = {
        "enable": True,
        "cycles": diag_cycles,
        "every_n_cycles": None,
        "dense_sampling": True,
        "on_fracture": True,
        "dir": "element_diagnostics",
    }
    config.rebuild_disp_cyclic()

    fem_dir = Path(args.fem_dir).expanduser() if args.fem_dir else None
    fem_sup = FEMSupervision(umax=float(args.umax), fem_dir=fem_dir)

    pffmodel, matprop, network = construct_model(
        config.PFF_model_dict, config.mat_prop_dict, config.network_dict,
        config.domain_extrema, config.device,
        williams_dict=config.williams_dict,
        fourier_dict=config.fourier_dict,
    )
    inp_tmp, t_conn_tmp, _, _ = prep_input_data(
        matprop, pffmodel, config.crack_dict, config.numr_dict,
        mesh_file=config.fine_mesh_file, device=config.device,
    )
    inp_np = inp_tmp.detach().cpu().numpy()
    t_np = t_conn_tmp.cpu().numpy() if torch.is_tensor(t_conn_tmp) else t_conn_tmp
    cx = (inp_np[t_np[:, 0], 0] + inp_np[t_np[:, 1], 0] + inp_np[t_np[:, 2], 0]) / 3.0
    cy = (inp_np[t_np[:, 0], 1] + inp_np[t_np[:, 1], 1] + inp_np[t_np[:, 2], 1]) / 3.0
    pidl_centroids = np.column_stack([cx, cy])
    obs_mask = _bool_mask_from_kind(
        args.mask_kind,
        pidl_centroids,
        x_min=args.mask_x_min,
        y_abs_max=args.mask_y_abs_max,
    )

    mit8_dict = {
        "enable": True,
        "K": int(args.K),
        "fem_cycle_offset": int(args.fem_cycle_offset),
        "lambda": float(args.lambda_alpha),
        "fem_sup": fem_sup,
        "pidl_centroids": pidl_centroids,
        "loss_kind": "mse_lin",
        "every_n_epochs": int(args.supervised_every),
        "mask": obs_mask,
        "target_kind": "alpha",
    }
    inverse_dict = {
        "enable": True,
        "target": "alpha_T",
        "initial_value": float(args.alphaT_init),
        "min_value": float(args.alphaT_min),
        "max_value": float(args.alphaT_max),
    }

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aTlearnInit{args.alphaT_init:g}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    tag = _mesh_tag(fem_mesh, args.tag)
    inv_tag = (
        f"_femmesh_{tag}_inverseAlphaT_K{args.K}"
        f"_lamA{args.lambda_alpha:g}_tolir{args.tol_ir:g}"
        f"_mask{args.mask_kind}_fixedEirrev"
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
        + inv_tag
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
        f.write("runner: run_fem_mesh_inverse_alphaT_umax.py\n")
        f.write("baseline_family: strict FEM-mesh soft-hist0 MLP\n")
        f.write("bc_setting: reverseBC-compatible PIDL baseline ansatz\n")
        f.write("fixed_E_irrev: true\n")
        f.write("inverse_target: alpha_T\n")
        f.write("obs_target: FEM alpha/d_elem\n")
        f.write("raw_active_guard: element_diagnostics saves psi_raw_elem, psi_active_elem, g_alpha_elem\n")
        f.write(f"umax: {args.umax}\n")
        f.write(f"n_cycles: {args.n_cycles}\n")
        f.write(f"seed: {args.seed}\n")
        f.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        f.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        f.write(f"tol_ir: {config.PFF_model_dict['tol_ir']}\n")
        f.write(f"alphaT_init: {args.alphaT_init}\n")
        f.write(f"alphaT_bounds: [{args.alphaT_min}, {args.alphaT_max}]\n")
        f.write(f"fem_dir: {fem_sup.fem_dir}\n")
        f.write(f"fem_cycles: {fem_sup.cycles}\n")
        f.write(f"obs_K: {args.K}\n")
        f.write(f"obs_fem_cycle_offset: {args.fem_cycle_offset}\n")
        f.write(f"obs_lambda: {args.lambda_alpha}\n")
        f.write(f"obs_mask_kind: {args.mask_kind}\n")
        f.write(f"diagnostic_cycles_pidl_j: {diag_cycles}\n")

    n_mask = "full" if obs_mask is None else f"{int(obs_mask.sum().item())}/{len(obs_mask)}"
    print("=" * 72)
    print("PIDL FEM-mesh inverse-alpha_T retry")
    print(f"  U_max       = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  FEM mesh    = {fem_mesh}")
    print(f"  FEM dir     = {fem_sup.fem_dir}")
    print(f"  FEM cycles  = {fem_sup.cycles}")
    print(f"  obs         = alpha target, PIDL j -> FEM c = j+{args.fem_cycle_offset}, "
          f"K={args.K}, lambda={args.lambda_alpha}, mask={n_mask}")
    print(f"  alpha_T     = init {args.alphaT_init}, bounds [{args.alphaT_min}, {args.alphaT_max}]")
    print(f"  raw/active  = element diagnostics enabled at PIDL j {diag_cycles}")
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
    )
    field_comp.net = field_comp.net.to(config.device)
    field_comp.domain_extrema = field_comp.domain_extrema.to(config.device)
    field_comp.theta = field_comp.theta.to(config.device)

    train(
        field_comp, config.disp_cyclic, pffmodel, matprop,
        config.crack_dict, config.numr_dict,
        config.optimizer_dict, config.training_dict,
        config.coarse_mesh_file, config.fine_mesh_file,
        config.device,
        config.trainedModel_path, config.intermediateModel_path,
        config.writer,
        fatigue_dict=config.fatigue_dict,
        mit8_dict=mit8_dict,
        adaptive_sampling_dict=getattr(config, "adaptive_sampling_dict", None),
        inverse_dict=inverse_dict,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
