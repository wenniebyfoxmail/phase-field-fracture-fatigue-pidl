#!/usr/bin/env python3
"""Run strict FEM-mesh PIDL with a nonstandard fatigue-history driver.

This is a diagnostic only.  The default PIDL/FEM-aligned history driver is
``active_degraded`` = g(alpha_now) * psi_raw.  The branches here test whether
the late history/active-work gap is caused by degraded-driver collapse.
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
    p.add_argument("--history-driver", required=True,
                   choices=("raw", "lagged_degraded"))
    p.add_argument("--n-cycles", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    p.add_argument("--tag", default="")
    p.add_argument("--fracture-confirm-cycles", type=int, default=3)
    p.add_argument("--plot-every", type=int, default=20)
    p.add_argument("--compile", action="store_true")
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

    # Strict benchmark controls: only the fatigue-history driver changes.
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
    config.fatigue_dict["history_driver_mode"] = args.history_driver
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    config.rebuild_disp_cyclic()

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    tag = _mesh_tag(fem_mesh, args.tag)
    suffix = f"_femmesh_{tag}_histdrv_{args.history_driver}{'_compile' if args.compile else ''}"
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
        f.write("runner: run_fem_mesh_history_driver_umax.py\n")
        f.write(f"umax: {args.umax}\n")
        f.write(f"n_cycles: {args.n_cycles}\n")
        f.write(f"seed: {args.seed}\n")
        f.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        f.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        f.write(f"mesh_tag: {tag}\n")
        f.write(f"torch_compile: {bool(args.compile)}\n")
        f.write(f"history_driver_mode: {args.history_driver}\n")
        f.write("purpose: strict FEM-mesh fatigue-history-driver diagnostic\n")

    print("=" * 72)
    print("PIDL FEM-mesh history-driver diagnostic")
    print(f"  history     = {args.history_driver}")
    print(f"  U_max       = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  FEM mesh    = {fem_mesh}")
    print(f"  archive     = {dir_name}")
    print(f"  full path   = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
