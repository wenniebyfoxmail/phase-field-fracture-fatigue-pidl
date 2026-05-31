#!/usr/bin/env python3
"""Run strict FEM-mesh PIDL with a staged alpha optimisation path.

The physics objective, mesh, initial crack convention, and fracture criterion
match ``run_fem_mesh_umax.py``.  The only intended discriminator is the
per-cycle optimiser path:

    uv output head/branch -> alpha output head/branch -> normal joint RPROP

By default this is a low-risk proxy that trains selected rows of the final
output layer.  With ``--split-trunk`` it uses independent uv and alpha MLP
trunks, so the staged phases train whole physical branches rather than only
final output rows.
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


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh",
                   help="Triangular .msh generated from FEM mesh_geometry.mat")
    p.add_argument("--tag", default="softHist0_stagedAlpha",
                   help="Archive tag suffix; defaults to the strict benchmark tag")
    p.add_argument("--fracture-confirm-cycles", type=int, default=3)
    p.add_argument("--plot-every", type=int, default=20)
    p.add_argument("--uv-head-epochs", type=int, default=750)
    p.add_argument("--alpha-head-epochs", type=int, default=750)
    p.add_argument("--joint-epochs", type=int, default=10000)
    p.add_argument("--stage-rel-tol", type=float, default=5e-7)
    p.add_argument("--uv-optimizer", default="RPROP", choices=("RPROP", "ADAM", "LBFGS"))
    p.add_argument("--alpha-optimizer", default="RPROP", choices=("RPROP", "ADAM", "LBFGS"))
    p.add_argument("--uv-lr", type=float, default=1e-4,
                   help="Initial lr/step size for the uv-head stage.")
    p.add_argument("--alpha-lr", type=float, default=1e-5,
                   help="Initial lr/step size for the alpha-head stage.")
    p.add_argument("--split-trunk", action="store_true",
                   help="Use independent uv and alpha MLP trunks.")
    p.add_argument("--diagnostic-cycles", default="0,1,2,3,20,40,69,80,99",
                   help="Cycles for state/gradient export.")
    p.add_argument("--no-field-files", action="store_true",
                   help="Write state-timing summary only, not per-cycle npz fields.")
    p.add_argument("--no-gradient-balance", action="store_true",
                   help="Disable routine E_el/E_d/E_hist head-wise gradient reporting.")
    p.add_argument("--compile", action="store_true",
                   help="Enable torch.compile for a speed diagnostic on CUDA.")
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

    # Strict benchmark controls: same as run_fem_mesh_umax.py, then add only the
    # staged-alpha optimiser path.
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

    config.coarse_mesh_file = coarse_mesh
    config.fine_mesh_file = fem_mesh
    config.network_dict["compile"] = bool(args.compile)
    config.network_dict["split_trunk"] = {"enable": bool(args.split_trunk)}
    config.optimizer_dict["n_epochs_RPROP"] = int(args.joint_epochs)
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    config.fatigue_dict["staged_alpha"] = {
        "enable": True,
        "uv_head_epochs": int(args.uv_head_epochs),
        "alpha_head_epochs": int(args.alpha_head_epochs),
        "optim_rel_tol": float(args.stage_rel_tol),
        "uv_optimizer": args.uv_optimizer,
        "alpha_optimizer": args.alpha_optimizer,
        "uv_lr": float(args.uv_lr),
        "alpha_lr": float(args.alpha_lr),
    }
    config.fatigue_dict["state_timing_export"] = {
        "enable": True,
        "cycles": args.diagnostic_cycles,
        "write_fields": not bool(args.no_field_files),
        "dir": "pidl_state_timing",
    }
    config.fatigue_dict["gradient_balance_probe"] = {
        "enable": not bool(args.no_gradient_balance),
        "cycles": args.diagnostic_cycles,
        "dir": "gradient_balance",
    }
    config.rebuild_disp_cyclic()

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    tag = _mesh_tag(fem_mesh, args.tag)
    stage_tag = (
        f"_femmesh_{tag}_stagedAlpha"
        f"{'_splitTrunk' if args.split_trunk else ''}"
        f"_uv{args.uv_head_epochs}-{args.uv_optimizer}{args.uv_lr:g}"
        f"_a{args.alpha_head_epochs}-{args.alpha_optimizer}{args.alpha_lr:g}"
        f"_j{args.joint_epochs}"
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
        + stage_tag
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
        f.write("runner: run_fem_mesh_staged_alpha_umax.py\n")
        f.write(f"umax: {args.umax}\n")
        f.write(f"n_cycles: {args.n_cycles}\n")
        f.write(f"seed: {args.seed}\n")
        f.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        f.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        f.write(f"mesh_tag: {tag}\n")
        f.write(f"torch_compile: {bool(args.compile)}\n")
        f.write(f"uv_head_epochs: {args.uv_head_epochs}\n")
        f.write(f"alpha_head_epochs: {args.alpha_head_epochs}\n")
        f.write(f"joint_epochs: {args.joint_epochs}\n")
        f.write(f"stage_rel_tol: {args.stage_rel_tol}\n")
        f.write(f"uv_optimizer: {args.uv_optimizer}\n")
        f.write(f"alpha_optimizer: {args.alpha_optimizer}\n")
        f.write(f"uv_lr: {args.uv_lr}\n")
        f.write(f"alpha_lr: {args.alpha_lr}\n")
        f.write(f"split_trunk: {bool(args.split_trunk)}\n")
        f.write(f"diagnostic_cycles: {args.diagnostic_cycles}\n")
        f.write(f"gradient_balance: {not bool(args.no_gradient_balance)}\n")
        f.write("purpose: strict FEM-mesh PIDL staged-alpha optimisation discriminator\n")

    print("=" * 72)
    print("PIDL FEM-mesh staged-alpha runner")
    print(f"  U_max       = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  FEM mesh    = {fem_mesh}")
    print(f"  coarse mesh = {coarse_mesh}")
    print(f"  uv/alpha/j  = {args.uv_head_epochs}/{args.alpha_head_epochs}/{args.joint_epochs}")
    print(f"  split trunk = {bool(args.split_trunk)}")
    print(f"  opt/lr      = uv {args.uv_optimizer}@{args.uv_lr:g} | "
          f"alpha {args.alpha_optimizer}@{args.alpha_lr:g}")
    print(f"  diagnostics= {args.diagnostic_cycles} | gradient={not bool(args.no_gradient_balance)}")
    print(f"  compile     = {bool(args.compile)}")
    print(f"  device      = {config.device}")
    print(f"  archive     = {dir_name}")
    print(f"  full path   = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
