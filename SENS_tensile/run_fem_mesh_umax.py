#!/usr/bin/env python3
"""Run PIDL on a triangularized FEM reference mesh.

This is a mesh-effect diagnostic: the variational objective and architecture are
kept at the baseline settings, while the main fatigue solve uses a mesh produced
from GRIPHFiTH's FEM `mesh_geometry.mat` by `make_fem_mesh.py`.
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


def _parse_cycles(raw: str) -> list[int]:
    return [int(x) for x in raw.split(",") if x.strip()]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--mesh-file", default="meshed_geom_fem_baseline.msh",
                   help="Triangular .msh generated from FEM mesh_geometry.mat")
    p.add_argument("--coarse-mesh-file", default=None,
                   help="Mesh used for pretraining; defaults to config.coarse_mesh_file.")
    p.add_argument("--tag", default="", help="Archive tag suffix; defaults to mesh stem")
    p.add_argument("--history-driver-mode",
                   choices=("current_active", "lagged_g", "raw"),
                   default="current_active",
                   help="Fatigue-history driver diagnostic; default preserves baseline.")
    p.add_argument("--element-diagnostics-cycles", default="",
                   help="Comma-separated cycle indices for full element diagnostics.")
    p.add_argument("--element-diagnostics-dir", default="element_diagnostics",
                   help="Output directory name inside the archive.")
    p.add_argument("--fracture-confirm-cycles", type=int, default=3)
    p.add_argument("--plot-every", type=int, default=20)
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
    coarse_mesh = _resolve_mesh_file(here, args.coarse_mesh_file or config.coarse_mesh_file)

    # Baseline objective/architecture only.  This runner isolates mesh effects.
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
    config.fatigue_dict["history_driver_mode"] = args.history_driver_mode
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    if args.element_diagnostics_cycles.strip():
        diag_cycles = _parse_cycles(args.element_diagnostics_cycles)
        config.fatigue_dict["element_diagnostics"] = {
            "enable": True,
            "cycles": diag_cycles,
            "every_n_cycles": None,
            "dense_sampling": True,
            "on_fracture": True,
            "dir": args.element_diagnostics_dir,
        }
    else:
        diag_cycles = []
    config.rebuild_disp_cyclic()

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    tag = _mesh_tag(fem_mesh, args.tag)
    suffix = f"_femmesh_{tag}{'_compile' if args.compile else ''}"
    if args.history_driver_mode != "current_active":
        suffix += f"_histdrv_{args.history_driver_mode}"
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
        f.write("runner: run_fem_mesh_umax.py\n")
        f.write(f"umax: {args.umax}\n")
        f.write(f"n_cycles: {args.n_cycles}\n")
        f.write(f"seed: {args.seed}\n")
        f.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        f.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        f.write(f"mesh_tag: {tag}\n")
        f.write(f"history_driver_mode: {args.history_driver_mode}\n")
        f.write("hist_alpha_update: max(previous,current)\n")
        f.write(f"tol_ir: {config.PFF_model_dict['tol_ir']}\n")
        f.write(f"alpha_constraint: {config.numr_dict['alpha_constraint']}\n")
        f.write(f"residual_stiffness_eta: {config.PFF_model_dict.get('residual_stiffness', 0.0)}\n")
        f.write(f"exact_bc_enable: {config.exact_bc_dict.get('enable', False)}\n")
        f.write(f"element_diagnostics_cycles: {diag_cycles}\n")
        f.write(f"element_diagnostics_dir: {args.element_diagnostics_dir if diag_cycles else ''}\n")
        f.write(f"torch_compile: {bool(args.compile)}\n")
        f.write("purpose: PIDL main training on triangularized FEM reference mesh\n")

    print("=" * 72)
    print("PIDL FEM-mesh runner")
    print(f"  U_max       = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  FEM mesh    = {fem_mesh}")
    print(f"  coarse mesh = {coarse_mesh}")
    print(f"  history drv = {args.history_driver_mode}")
    print(f"  elem diag   = {diag_cycles if diag_cycles else 'off'}")
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
