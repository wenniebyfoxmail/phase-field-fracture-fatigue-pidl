#!/usr/bin/env python3
"""Run a void-like initial notch diagnostic for reverseBC fatigue.

The diagnostic keeps the baseline architecture/objective but excludes the
initial pre-crack corridor from energy and fatigue-history accumulation:

    x <= 0 and |y| <= half_width

This approximates FEM's void notch convention without changing PIDL into a true
internal-free-boundary geometry. Use ``--mesh-file meshed_geom_fem_baseline.msh``
for the FEM-mesh alignment variant.
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("umax", type=float)
    parser.add_argument("--n-cycles", type=int, default=100)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--mesh-file", default="meshed_geom2.msh")
    parser.add_argument("--tag", default="")
    parser.add_argument("--precrack-half-width", type=float, default=0.02)
    parser.add_argument("--precrack-x-max", type=float, default=0.0)
    parser.add_argument("--fracture-confirm-cycles", type=int, default=3)
    parser.add_argument("--plot-every", type=int, default=20)
    parser.add_argument("--element-diag-cycles", default="10,40,70,74")
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

    fine_mesh = _resolve_mesh_file(here, args.mesh_file)
    coarse_mesh = _resolve_mesh_file(here, config.coarse_mesh_file)

    # Baseline architecture/objective; isolate the void-like notch convention.
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False
    config.adaptive_sampling_dict["enable"] = False
    config.sidecar_S1_dict["enable"] = False
    config.sidecar_S2_dict["enable"] = False
    if hasattr(config, "tip_local_net_dict"):
        config.tip_local_net_dict["enable"] = False
    config.symmetry_prior = False

    config.coarse_mesh_file = coarse_mesh
    config.fine_mesh_file = fine_mesh
    config.network_dict["compile"] = bool(args.compile)
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    config.fatigue_dict["void_notch_mask"] = {
        "enable": True,
        "x_max": float(args.precrack_x_max),
        "half_width": float(args.precrack_half_width),
        "mask_energy": True,
        "mask_fatigue": True,
    }
    cycles = [int(c.strip()) for c in args.element_diag_cycles.split(",") if c.strip()]
    config.fatigue_dict["element_diagnostics"] = {
        "enable": True,
        "cycles": cycles,
        "every_n_cycles": None,
        "dense_sampling": True,
        "on_fracture": True,
    }
    config.rebuild_disp_cyclic()

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    mesh_tag = _mesh_tag(fine_mesh, args.tag)
    suffix = (
        f"_voidNotch_x{args.precrack_x_max:g}_hw{args.precrack_half_width:g}"
        f"_{mesh_tag}"
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

    with open(config.model_path / "model_settings.txt", "w", encoding="utf-8") as handle:
        handle.write("runner: run_void_notch_mask_umax.py\n")
        handle.write(f"umax: {args.umax}\n")
        handle.write(f"n_cycles: {args.n_cycles}\n")
        handle.write(f"seed: {args.seed}\n")
        handle.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        handle.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        handle.write(f"mesh_tag: {mesh_tag}\n")
        handle.write(f"void_notch_x_max: {args.precrack_x_max}\n")
        handle.write(f"void_notch_half_width: {args.precrack_half_width}\n")
        handle.write(f"torch_compile: {bool(args.compile)}\n")
        handle.write("purpose: void-like initial notch PIDL diagnostic\n")

    print("=" * 72)
    print("PIDL void-like notch diagnostic")
    print(f"  U_max       = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  fine mesh   = {fine_mesh}")
    print(f"  coarse mesh = {coarse_mesh}")
    print(f"  void mask   = x <= {args.precrack_x_max}, |y| <= {args.precrack_half_width}")
    print(f"  elem diag   = {cycles}")
    print(f"  archive     = {dir_name}")
    print(f"  full path   = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
