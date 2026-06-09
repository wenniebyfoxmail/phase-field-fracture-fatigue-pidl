#!/usr/bin/env python3
"""Run strict FEM-mesh PIDL with fatigue off and monotonic U=0.2 loading.

This keeps the current strict PIDL baseline architecture/objective controls but
uses the original nonuniform monotonic displacement sequence from config.py:

    0.025, 0.05, 0.075, 0.10, 0.105, ..., 0.20

The purpose is to compare against the old monotonic fatigue-off sanity check
without changing the loading path.
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
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--mesh-file", default="meshed_geom_fem_soft_hist0.msh")
    p.add_argument("--coarse-mesh-file", default=None,
                   help="Mesh used for pretraining; defaults to config.coarse_mesh_file.")
    p.add_argument("--tag", default="softHist0_monoU02_fatigueOff")
    p.add_argument("--plot-every", type=int, default=1)
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
    coarse_mesh = _resolve_mesh_file(here, args.coarse_mesh_file or config.coarse_mesh_file)

    # Strict current-baseline controls: disable optional representation/loss
    # branches and change only the fatigue switch/loading regime.
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
    config.local_patch_dict["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False
    config.fatigue_dict["void_notch_mask"]["enable"] = False
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
    config.fatigue_dict["fatigue_on"] = False
    config.fatigue_dict["loading_type"] = "monotonic"
    config.fatigue_dict["disp_max"] = 0.2
    config.fatigue_dict["n_cycles"] = len(config.disp)
    config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)

    tag = _mesh_tag(fem_mesh, args.tag)
    dir_name = (
        "hl_" + str(config.network_dict["hidden_layers"])
        + "_Neurons_" + str(config.network_dict["neurons"])
        + "_activation_" + config.network_dict["activation"]
        + "_coeff_" + str(config.network_dict["init_coeff"])
        + "_Seed_" + str(config.network_dict["seed"])
        + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
        + "_gradient_" + str(config.numr_dict["gradient_type"])
        + "_fatigue_off"
        + f"_femmesh_{tag}"
        + ("_compile" if args.compile else "")
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
        f.write("runner: run_fem_mesh_monotonic_fatigue_off.py\n")
        f.write("fatigue_on: False\n")
        f.write("loading_type: monotonic\n")
        f.write("disp_sequence: config.disp nonuniform 0.025...0.2\n")
        f.write(f"n_steps: {len(config.disp)}\n")
        f.write(f"seed: {args.seed}\n")
        f.write(f"coarse_mesh_file: {config.coarse_mesh_file}\n")
        f.write(f"fine_mesh_file: {config.fine_mesh_file}\n")
        f.write(f"mesh_tag: {tag}\n")
        f.write("bc_mode: original_pidl_top_bottom_u_fixed_vertical_ramp\n")
        f.write("bc_note: u=0 on top/bottom; v=0 bottom; v=lambda top; exact_bc/fem_anchor disabled\n")
        f.write("precrack_format: retained_material_soft_hist_alpha_init_AT1_squared_hat\n")
        f.write("void_notch_mask_enable: False\n")
        f.write(f"torch_compile: {bool(args.compile)}\n")
        f.write("purpose: strict baseline monotonic fatigue-off U=0.2 comparison\n")

    print("=" * 72)
    print("Strict PIDL FEM-mesh monotonic fatigue-off runner")
    print(f"  loading     = config.disp ({len(config.disp)} steps, final {float(config.disp[-1])})")
    print(f"  seed        = {args.seed}")
    print(f"  FEM mesh    = {fem_mesh}")
    print(f"  coarse mesh = {coarse_mesh}")
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
