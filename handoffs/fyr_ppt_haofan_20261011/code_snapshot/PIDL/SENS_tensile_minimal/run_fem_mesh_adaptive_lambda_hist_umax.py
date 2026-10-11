#!/usr/bin/env python3
"""Run strict FEM-mesh PIDL with adaptive E_hist/lambda_hist balancing."""
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("umax", type=float)
    parser.add_argument("--n-cycles", type=int, default=100)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    parser.add_argument("--coarse-mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    parser.add_argument("--tag", default="softHist0")
    parser.add_argument("--lambda-hist-min", type=float, default=1.0e-3)
    parser.add_argument("--lambda-hist-max", type=float, default=1.0)
    parser.add_argument("--lambda-hist-smooth", type=float, default=0.0)
    parser.add_argument("--lambda-hist-initial", type=float, default=1.0)
    parser.add_argument("--lambda-hist-start-cycle", type=int, default=1)
    parser.add_argument("--fracture-confirm-cycles", type=int, default=3)
    parser.add_argument("--plot-every", type=int, default=20)
    parser.add_argument("--compile", action="store_true")
    parser.add_argument("--force-cpu", action="store_true")
    args = parser.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

    here = Path(__file__).resolve().parent
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config  # noqa: WPS433

    fem_mesh = _resolve_mesh_file(here, args.mesh_file)
    coarse_mesh = _resolve_mesh_file(here, args.coarse_mesh_file)

    # Strict FEM-mesh controls: keep architecture/objective baseline, then add
    # only adaptive lambda_hist on E_hist.
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
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    config.fatigue_dict["adaptive_lambda_hist"] = {
        "enable": True,
        "lambda_hist_min": float(args.lambda_hist_min),
        "lambda_hist_max": float(args.lambda_hist_max),
        "lambda_hist_smooth": float(args.lambda_hist_smooth),
        "lambda_hist_initial": float(args.lambda_hist_initial),
        "start_cycle": int(args.lambda_hist_start_cycle),
    }
    config.rebuild_disp_cyclic()

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    tag = _mesh_tag(fem_mesh, args.tag)
    suffix = f"_femmesh_{tag}_adapthist{'_compile' if args.compile else ''}"
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

    with open(config.model_path / "model_settings.txt", "w", encoding="utf-8") as handle:
        handle.write("runner: run_fem_mesh_adaptive_lambda_hist_umax.py\n")
        handle.write(f"umax: {args.umax}\n")
        handle.write(f"n_cycles: {args.n_cycles}\n")
        handle.write(f"seed: {args.seed}\n")
        handle.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        handle.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        handle.write(f"mesh_tag: {tag}\n")
        handle.write(f"torch_compile: {bool(args.compile)}\n")
        handle.write("adaptive_lambda_hist: true\n")
        handle.write(f"lambda_hist_min: {args.lambda_hist_min}\n")
        handle.write(f"lambda_hist_max: {args.lambda_hist_max}\n")
        handle.write(f"lambda_hist_smooth: {args.lambda_hist_smooth}\n")
        handle.write(f"lambda_hist_initial: {args.lambda_hist_initial}\n")
        handle.write(f"lambda_hist_start_cycle: {args.lambda_hist_start_cycle}\n")
        handle.write("purpose: PIDL strict FEM-mesh training with adaptive E_hist/lambda_hist\n")

    print("=" * 72)
    print("PIDL FEM-mesh adaptive lambda_hist runner")
    print(f"  U_max       = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  FEM mesh    = {fem_mesh}")
    print(f"  coarse mesh = {coarse_mesh}")
    print(
        "  lambda_hist = "
        f"init {args.lambda_hist_initial}, "
        f"bounds [{args.lambda_hist_min}, {args.lambda_hist_max}], "
        f"smooth {args.lambda_hist_smooth}, start cycle {args.lambda_hist_start_cycle}"
    )
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
