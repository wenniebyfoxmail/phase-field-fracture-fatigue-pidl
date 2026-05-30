#!/usr/bin/env python3
"""Run strict FEM-mesh PIDL with an FBPINN-style local subdomain chain.

This is the stronger domain-decomposition discriminator after the additive
single-patch branch was weak/negative.  Instead of adding one small correction,
this runner uses several overlapping local networks along the expected crack
path and blends their raw outputs with the global MLP through a smooth
partition weight.  Inside a local window, the local subnet carries the field.

The variational energy, fatigue law, history timing, FEM-mesh benchmark, and
event criterion are otherwise unchanged.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from run_fem_mesh_local_patch_umax import _mesh_tag, _resolve_mesh_file


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    p.add_argument("--tag", default="softHist0_fbpinnChain")
    p.add_argument("--fracture-confirm-cycles", type=int, default=3)
    p.add_argument("--plot-every", type=int, default=20)
    p.add_argument("--joint-epochs", type=int, default=10000)
    p.add_argument("--patch-warm-epochs", type=int, default=1500)
    p.add_argument("--patch-rel-tol", type=float, default=5e-7)
    p.add_argument("--n-patches", type=int, default=6)
    p.add_argument("--x-start", type=float, default=0.0)
    p.add_argument("--x-end", type=float, default=0.45)
    p.add_argument("--wr", type=float, default=0.12)
    p.add_argument("--patch-hidden-layers", type=int, default=3)
    p.add_argument("--patch-neurons", type=int, default=80)
    p.add_argument("--patch-scale", type=float, default=1.0)
    p.add_argument("--diagnostic-cycles", default="20,40,69")
    p.add_argument("--force-cpu", action="store_true")
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

    config.local_patch_dict.update({
        "enable": True,
        "x_tip": 0.0,
        "y_tip": 0.0,
        "wr": float(args.wr),
        "output_mode": "all",
        "hidden_layers": int(args.patch_hidden_layers),
        "neurons": int(args.patch_neurons),
        "activation": "TrainableReLU",
        "init_coeff": 1.0,
        "scale": float(args.patch_scale),
        "blend_mode": "partition",
        "n_patches": int(args.n_patches),
        "x_start": float(args.x_start),
        "x_end": float(args.x_end),
    })

    diag_cycles = [int(c.strip()) for c in str(args.diagnostic_cycles).split(",") if c.strip()]

    config.coarse_mesh_file = coarse_mesh
    config.fine_mesh_file = fem_mesh
    config.network_dict["compile"] = False
    config.optimizer_dict["n_epochs_RPROP"] = int(args.joint_epochs)
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    config.fatigue_dict["local_patch_training"] = {
        "enable": True,
        "warm_epochs": int(args.patch_warm_epochs),
        "optim_rel_tol": float(args.patch_rel_tol),
    }
    config.fatigue_dict["element_diagnostics"] = {
        "enable": True,
        "cycles": diag_cycles,
        "every_n_cycles": None,
        "dense_sampling": True,
        "on_fracture": True,
        "dir": "element_diagnostics",
    }
    config.rebuild_disp_cyclic()

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    tag = _mesh_tag(fem_mesh, args.tag)
    fbpinn_tag = (
        f"_femmesh_{tag}_fbpinnChain_n{args.n_patches}"
        f"_wr{args.wr}_x{args.x_start}to{args.x_end}"
        f"_h{args.patch_hidden_layers}_n{args.patch_neurons}"
        f"_warm{args.patch_warm_epochs}_j{args.joint_epochs}"
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
        + fbpinn_tag
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
        f.write("runner: run_fem_mesh_fbpinn_umax.py\n")
        f.write(f"umax: {args.umax}\n")
        f.write(f"n_cycles: {args.n_cycles}\n")
        f.write(f"seed: {args.seed}\n")
        f.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        f.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        f.write(f"mesh_tag: {tag}\n")
        f.write(f"joint_epochs: {args.joint_epochs}\n")
        f.write(f"patch_warm_epochs: {args.patch_warm_epochs}\n")
        f.write(f"patch_rel_tol: {args.patch_rel_tol}\n")
        f.write("local_patch_enable: True\n")
        f.write("local_patch_output_mode: all\n")
        f.write(f"local_patch_wr: {args.wr}\n")
        f.write(f"local_patch_hidden_layers: {args.patch_hidden_layers}\n")
        f.write(f"local_patch_neurons: {args.patch_neurons}\n")
        f.write(f"local_patch_scale: {args.patch_scale}\n")
        f.write("local_patch_blend_mode: partition\n")
        f.write(f"local_patch_n_patches: {args.n_patches}\n")
        f.write(f"local_patch_x_start: {args.x_start}\n")
        f.write(f"local_patch_x_end: {args.x_end}\n")
        f.write(f"element_diagnostic_cycles: {diag_cycles}\n")
        f.write("purpose: strict FEM-mesh FBPINN-style subdomain-chain discriminator\n")

    print("=" * 72)
    print("PIDL FEM-mesh FBPINN-chain runner")
    print(f"  U_max       = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  FEM mesh    = {fem_mesh}")
    print(f"  chain       = {args.n_patches} patches, wr {args.wr}, "
          f"x {args.x_start} -> {args.x_end}")
    print(f"  patch net   = h{args.patch_hidden_layers} n{args.patch_neurons}")
    print(f"  warm/joint  = {args.patch_warm_epochs}/{args.joint_epochs}")
    print(f"  archive     = {dir_name}")
    print(f"  full path   = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
