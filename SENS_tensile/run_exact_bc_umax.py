#!/usr/bin/env python3
"""run_exact_bc_umax.py — C4 exact-BC SENT runner.

Sukumar-inspired, geometry-specific trial function for the SENT setup:

1. keep exact prescribed vertical displacement on top/bottom,
2. build in plane-strain Poisson lateral contraction as the particular solution,
3. multiply NN correction by top-bottom bubble × side-distance² so the
   correction and its x-derivative vanish on x=±0.5.

This is meant to attack V7 at the representation level rather than with a soft
penalty. Baseline defaults remain unchanged unless this runner is used.
"""
import argparse
import os
import sys
from pathlib import Path


def _rewrite_model_settings(config, runner_name: str) -> None:
    fat = config.fatigue_dict
    exact_bc = config.exact_bc_dict
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
        f.write(f"\nloading_type: {fat.get('loading_type')}")
        f.write(f"\nn_cycles: {fat.get('n_cycles')}")
        f.write(f"\ndisp_max: {fat.get('disp_max')}")
        f.write(f"\nR_ratio: {fat.get('R_ratio')}")
        f.write(f"\naccum_type: {fat.get('accum_type')}")
        f.write(f"\nn_power: {fat.get('n_power')}")
        f.write(f"\nalpha_n: {fat.get('alpha_n')}")
        f.write(f"\ndegrad_type: {fat.get('degrad_type')}")
        f.write(f"\nalpha_T: {fat.get('alpha_T')}")
        f.write(f"\nkappa: {fat.get('kappa')}")
        f.write(f"\n--- exact_bc ---")
        f.write(f"\nexact_bc_enable: {exact_bc.get('enable', False)}")
        f.write(f"\nexact_bc_mode: {exact_bc.get('mode', 'sent_plane_strain')}")
        f.write(f"\nexact_bc_nu: {exact_bc.get('nu', 0.3)}")
        f.write(f"\n--- symmetry ---")
        f.write(f"\nsymmetry_prior: {config.symmetry_prior}")
        f.write(f"\n[runner] {runner_name}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=10)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--nu", type=float, default=0.3,
                   help="Poisson ratio used in the plane-strain lifting field")
    p.add_argument("--sym-prior", action="store_true",
                   help="Also enable the hard y^2 symmetry prior for combo smoke")
    p.add_argument("--force-cpu", action="store_true",
                   help="Hide CUDA before importing config; useful for Mac dev smoke")
    args = p.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

    here = Path(__file__).parent
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config

    # Baseline architecture only
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.symmetry_prior = bool(args.sym_prior)

    config.fatigue_dict["disp_max"] = args.umax
    config.fatigue_dict["n_cycles"] = args.n_cycles
    config.rebuild_disp_cyclic()

    config.exact_bc_dict = {
        "enable": True,
        "mode": "sent_plane_strain",
        "nu": float(args.nu),
    }

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    sym_tag = "_symY2" if args.sym_prior else ""
    dir_name = (
        "hl_" + str(config.network_dict["hidden_layers"])
        + "_Neurons_" + str(config.network_dict["neurons"])
        + "_activation_" + config.network_dict["activation"]
        + "_coeff_" + str(config.network_dict["init_coeff"])
        + "_Seed_" + str(config.network_dict["seed"])
        + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
        + "_gradient_" + str(config.numr_dict["gradient_type"])
        + fatigue_tag
        + f"_exactBCsent_nu{args.nu}"
        + sym_tag
    )
    config.model_path = here / Path(dir_name)
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
    _rewrite_model_settings(config, "run_exact_bc_umax.py")

    print("=" * 72)
    print("Exact-BC SENT PIDL runner (C4)")
    print(f"  U_max     = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  nu        = {args.nu}")
    print(f"  sym prior = {args.sym_prior}")
    print(f"  device    = {config.device}")
    print(f"  archive   = {dir_name}")
    print(f"  full path = {config.model_path}")
    print("  note      = if you launch this on Windows, prefer `PYTHONUTF8=1 python ...`")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
