#!/usr/bin/env python3
"""Run strict FEM-mesh PIDL with fatigue/history masked in the precrack.

This is not the old void-notch diagnostic.  The precrack corridor remains in
the variational energy, but its fatigue history is frozen:

    mask_energy=False, mask_fatigue=True

Use this as the retained-material benchmark for the question: should the
already-damaged initial crack keep accumulating alpha_bar/fatigue damage?
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
    vals = [float(x) for x in raw.split(",") if x.strip()]
    if len(vals) < 2:
        raise argparse.ArgumentTypeError("need at least two substep factors")
    return vals


def _diag_steps(physical_cycles: list[int], n_substeps: int) -> list[int]:
    steps = {0}
    for cyc in physical_cycles:
        if cyc < 1:
            continue
        base = (cyc - 1) * n_substeps
        steps.add(base + n_substeps - 2)  # peak for default [..., 1, 0]
        steps.add(base + n_substeps - 1)  # unloaded
    return sorted(steps)


def _parse_cycles(raw: str) -> list[int]:
    return [int(x) for x in raw.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("umax", type=float)
    parser.add_argument("--n-cycles-physical", "--n-cycles", dest="n_cycles_physical",
                        type=int, default=120)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh",
                        help="Triangular .msh generated from soft-hist0 FEM mesh_geometry.mat")
    parser.add_argument("--coarse-mesh-file", default=None,
                        help="Pretraining mesh; defaults to config.coarse_mesh_file.")
    parser.add_argument("--tag", default="precrackFatigueMask_softHist0_stateTiming")
    parser.add_argument("--substeps", type=_parse_factors,
                        default=_parse_factors("0.25,0.5,0.75,1,0"))
    parser.add_argument("--history-driver-mode",
                        choices=("current_active", "lagged_g", "raw"),
                        default="current_active")
    parser.add_argument("--precrack-half-width", type=float, default=0.02)
    parser.add_argument("--precrack-x-max", type=float, default=0.0)
    parser.add_argument("--diag-physical-cycles", default="1,2,3,20,40,60,69",
                        help="Physical cycles for peak/unloaded element diagnostics.")
    parser.add_argument("--element-diag-steps", default=None,
                        help="Override diagnostics with explicit training-step indices.")
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
    coarse_mesh = _resolve_mesh_file(here, args.coarse_mesh_file or config.coarse_mesh_file)

    # Strict benchmark controls: no optional enrichment, weighting, or symmetry prior.
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

    factors = np.asarray(args.substeps, dtype=float)
    disp_steps = np.tile(factors * float(args.umax), int(args.n_cycles_physical))
    total_steps = int(len(disp_steps))

    if args.element_diag_steps:
        diag_steps = _parse_cycles(args.element_diag_steps)
    else:
        diag_steps = _diag_steps(
            _parse_cycles(args.diag_physical_cycles),
            n_substeps=len(factors),
        )

    config.coarse_mesh_file = coarse_mesh
    config.fine_mesh_file = fem_mesh
    config.network_dict["compile"] = bool(args.compile)
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles_physical)
    config.fatigue_dict["loading_type"] = "cyclic"
    config.fatigue_dict["explicit_cycle_substeps"] = int(len(factors))
    config.fatigue_dict["explicit_cycle_factors"] = [float(x) for x in factors]
    config.fatigue_dict["history_driver_mode"] = args.history_driver_mode
    config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    config.fatigue_dict["void_notch_mask"] = {
        "enable": True,
        "x_max": float(args.precrack_x_max),
        "half_width": float(args.precrack_half_width),
        "mask_energy": False,
        "mask_fatigue": True,
    }
    config.fatigue_dict["element_diagnostics"] = {
        "enable": True,
        "cycles": diag_steps,
        "every_n_cycles": None,
        "dense_sampling": True,
        "on_fracture": True,
        "dir": "element_diagnostics_precrack_fatigue_mask",
    }
    config.fatigue_dict["gradient_diagnostics"] = {
        "enable": True,
        "cycles": diag_steps,
        "every_n_cycles": 1,
        "dense_sampling": True,
        "on_fracture": True,
    }
    config.disp_cyclic = disp_steps

    fat = config.fatigue_dict
    mesh_tag = _mesh_tag(fem_mesh, args.tag)
    # Keep the archive directory below common filesystem filename limits.
    short_sub = "-".join(f"{x:g}" for x in factors)
    dir_name = (
        f"pfmask_hl{config.network_dict['hidden_layers']}"
        f"_n{config.network_dict['neurons']}"
        f"_seed{config.network_dict['seed']}"
        f"_{config.PFF_model_dict['PFF_model']}"
        f"_{config.numr_dict['gradient_type']}"
        f"_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}"
        f"_Ncyc{fat['n_cycles']}_Nstep{total_steps}"
        f"_U{fat['disp_max']}"
        f"_{mesh_tag}"
        f"_{args.history_driver_mode}"
        f"_x{args.precrack_x_max:g}_hw{args.precrack_half_width:g}"
        f"_s{short_sub}"
        f"{'_compile' if args.compile else ''}"
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
        handle.write("runner: run_fem_mesh_precrack_fatigue_mask_umax.py\n")
        handle.write(f"umax: {args.umax}\n")
        handle.write(f"n_cycles_physical: {args.n_cycles_physical}\n")
        handle.write(f"n_training_steps: {total_steps}\n")
        handle.write(f"seed: {args.seed}\n")
        handle.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        handle.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        handle.write(f"mesh_tag: {mesh_tag}\n")
        handle.write(f"torch_compile: {bool(args.compile)}\n")
        handle.write(f"history_driver_mode: {args.history_driver_mode}\n")
        handle.write(f"explicit_cycle_substeps: {fat['explicit_cycle_substeps']}\n")
        handle.write(f"explicit_cycle_factors: {fat['explicit_cycle_factors']}\n")
        handle.write(f"void_notch_mask: {fat['void_notch_mask']}\n")
        handle.write(f"element_diagnostics_steps: {diag_steps}\n")
        handle.write("element_diagnostics_fields: mechanics+energy+driver\n")
        handle.write("gradient_diagnostics: pre_history_refresh_every_step\n")
        handle.write(
            "gradient_diagnostics_columns: step,E_el,E_d,E_hist,"
            "grad_E_el,grad_E_d,grad_E_hist\n"
        )
        handle.write(
            "purpose: retained precrack benchmark; variational energy kept, "
            "fatigue/history masked in the precrack corridor\n"
        )

    print("=" * 72)
    print("PIDL FEM-mesh retained-precrack fatigue/history mask")
    print(f"  U_max          = {args.umax} | physical cycles = {args.n_cycles_physical}")
    print(f"  training steps = {total_steps} | seed = {args.seed}")
    print(f"  substeps       = {list(factors)}")
    print(f"  FEM mesh       = {fem_mesh}")
    print(f"  coarse mesh    = {coarse_mesh}")
    print(f"  history driver = {args.history_driver_mode}")
    print(f"  precrack mask  = x <= {args.precrack_x_max}, |y| <= {args.precrack_half_width}")
    print("  mask_energy    = False")
    print("  mask_fatigue   = True")
    print(f"  elem diag      = {diag_steps}")
    print(f"  compile        = {bool(args.compile)}")
    print(f"  device         = {config.device}")
    print(f"  archive        = {dir_name}")
    print(f"  full path      = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
