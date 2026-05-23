#!/usr/bin/env python3
"""run_tip_local_net_S1_umax.py — Tip-local correction net on fixed S1 mesh.

First smoke from the 2026-05-23 handoff:
  python run_tip_local_net_S1_umax.py 0.12 --n-cycles 20 --seed 1
  python run_tip_local_net_S1_umax.py 0.12 --n-cycles 40 --seed 1

The runner keeps the physical loss unchanged, disables competing
representation/loss variants, enables static S1 crack-tip refinement, and adds
a compact local correction head near the initial tip.
"""
import argparse
import os
import sys
from pathlib import Path


def _rewrite_model_settings(config, runner_name: str) -> None:
    fat = config.fatigue_dict
    s1 = config.sidecar_S1_dict
    tln = config.tip_local_net_dict
    with open(config.model_path / Path("model_settings.txt"), "w") as f:
        f.write(f"hidden_layers: {config.network_dict['hidden_layers']}")
        f.write(f"\nneurons: {config.network_dict['neurons']}")
        f.write(f"\nseed: {config.network_dict['seed']}")
        f.write(f"\nactivation: {config.network_dict['activation']}")
        f.write(f"\ncoeff: {config.network_dict['init_coeff']}")
        f.write(f"\nPFF_model: {config.PFF_model_dict['PFF_model']}")
        f.write(f"\nse_split: {config.PFF_model_dict['se_split']}")
        f.write(f"\ngradient_type: {config.numr_dict['gradient_type']}")
        f.write(f"\ndevice: {config.device}")
        f.write(f"\n--- fatigue ---")
        f.write(f"\nfatigue_on: {fat.get('fatigue_on')}")
        f.write(f"\nn_cycles: {fat.get('n_cycles')}")
        f.write(f"\ndisp_max: {fat.get('disp_max')}")
        f.write(f"\nalpha_T: {fat.get('alpha_T')}")
        f.write(f"\n--- sidecar S1 (static-tip oversampling) ---")
        f.write(f"\nS1_enable: {s1.get('enable')}")
        f.write(f"\nS1_tip_xy: {s1.get('tip_xy')}")
        f.write(f"\nS1_r_tip_sample: {s1.get('r_tip_sample')}")
        f.write(f"\nS1_n_refine_passes: {s1.get('n_refine_passes')}")
        f.write(f"\n--- tip_local_net ---")
        f.write(f"\ntip_local_enable: {tln.get('enable')}")
        f.write(f"\ntip_local_x_tip: {tln.get('x_tip')}")
        f.write(f"\ntip_local_y_tip: {tln.get('y_tip')}")
        f.write(f"\ntip_local_r_tip: {tln.get('r_tip')}")
        f.write(f"\ntip_local_window_radius: {tln.get('window_radius')}")
        f.write(f"\ntip_local_hidden_layers: {tln.get('hidden_layers')}")
        f.write(f"\ntip_local_neurons: {tln.get('neurons')}")
        f.write(f"\ntip_local_zero_init: {tln.get('zero_init')}")
        f.write(f"\n[runner] {runner_name}")


def _resolve_mesh_file(here: Path, filename: str) -> str:
    local = here / filename
    if local.exists():
        return filename

    # Worktrees do not carry ignored .msh files. Reuse the main upload-code
    # mesh copy when this runner is launched from a clean experiment worktree.
    for parent in here.parents:
        main_repo_mesh = parent / "SENS_tensile" / filename
        if main_repo_mesh.exists():
            return str(main_repo_mesh)

    return filename


def main():
    p = argparse.ArgumentParser()
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=20)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--r-tip", type=float, default=0.05,
                   help="S1 refinement radius and local coordinate scale")
    p.add_argument("--window-radius", type=float, default=0.05,
                   help="Compact local-net taper radius")
    p.add_argument("--n-passes", type=int, default=1,
                   help="S1 static refinement passes")
    p.add_argument("--tip-hidden-layers", type=int, default=3)
    p.add_argument("--tip-neurons", type=int, default=80)
    p.add_argument("--tip-x", type=float, default=0.0)
    p.add_argument("--tip-y", type=float, default=0.0)
    p.add_argument("--force-cpu", action="store_true")
    args = p.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

    here = Path(__file__).resolve().parent
    os.chdir(here)
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config

    config.coarse_mesh_file = _resolve_mesh_file(here, config.coarse_mesh_file)
    config.fine_mesh_file = _resolve_mesh_file(here, config.fine_mesh_file)

    # Isolate representation: no other architectural or loss-weighting variants.
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False
    config.adaptive_sampling_dict["enable"] = False
    config.sidecar_S2_dict["enable"] = False
    config.symmetry_prior = False

    config.fatigue_dict["disp_max"] = args.umax
    config.fatigue_dict["n_cycles"] = args.n_cycles
    config.rebuild_disp_cyclic()

    config.sidecar_S1_dict["enable"] = True
    config.sidecar_S1_dict["tip_xy"] = (float(args.tip_x), float(args.tip_y))
    config.sidecar_S1_dict["r_tip_sample"] = float(args.r_tip)
    config.sidecar_S1_dict["n_refine_passes"] = int(args.n_passes)

    config.tip_local_net_dict["enable"] = True
    config.tip_local_net_dict["x_tip"] = float(args.tip_x)
    config.tip_local_net_dict["y_tip"] = float(args.tip_y)
    config.tip_local_net_dict["r_tip"] = float(args.r_tip)
    config.tip_local_net_dict["window_radius"] = float(args.window_radius)
    config.tip_local_net_dict["hidden_layers"] = int(args.tip_hidden_layers)
    config.tip_local_net_dict["neurons"] = int(args.tip_neurons)
    config.tip_local_net_dict["zero_init"] = True

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    tip_tag = (
        f"_tipLocal_rt{args.r_tip}_wr{args.window_radius}"
        f"_h{args.tip_hidden_layers}_n{args.tip_neurons}"
    )
    s1_tag = f"_sidecarS1_rt{args.r_tip}_np{args.n_passes}"
    dir_name = (
        "hl_" + str(config.network_dict["hidden_layers"])
        + "_Neurons_" + str(config.network_dict["neurons"])
        + "_activation_" + config.network_dict["activation"]
        + "_coeff_" + str(config.network_dict["init_coeff"])
        + "_Seed_" + str(config.network_dict["seed"])
        + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
        + "_gradient_" + str(config.numr_dict["gradient_type"])
        + fatigue_tag
        + s1_tag
        + tip_tag
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
    _rewrite_model_settings(config, "run_tip_local_net_S1_umax.py")

    print("=" * 72)
    print("Tip-local correction net on fixed S1 mesh")
    print(f"  U_max      = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  tip_xy     = ({args.tip_x}, {args.tip_y})")
    print(f"  S1 r_tip   = {args.r_tip} | n_passes = {args.n_passes}")
    print(f"  local head = {args.tip_hidden_layers}x{args.tip_neurons} | window = {args.window_radius}")
    print(f"  device     = {config.device}")
    print(f"  archive    = {dir_name}")
    print(f"  full path  = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
