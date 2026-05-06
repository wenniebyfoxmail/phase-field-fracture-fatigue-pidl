#!/usr/bin/env python3
"""run_symmetry_prior_umax.py — baseline architecture + y² symmetry prior smoke/production runner.

Purpose
-------
Launch a pure-physics baseline PIDL run with the new geometry-aware symmetry prior:

  - NN input uses (x, y²) on the baseline branch
  - u_x correction is even in y
  - u_y correction is odd in y (implemented as y * raw_v)
  - alpha is even in y

The affine loading term and BC bubble remain unchanged; the prior is on the NN
correction only.

Usage
-----
  python run_symmetry_prior_umax.py 0.12 --n-cycles 10 --seed 1
  python run_symmetry_prior_umax.py 0.12 --n-cycles 300 --seed 1
"""
import sys
import argparse
from pathlib import Path


def _rewrite_model_settings(config, runner_name: str) -> None:
    fat = config.fatigue_dict
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
        f.write(f"\n--- williams ---")
        f.write(f"\nwilliams_enable: {config.williams_dict.get('enable', False)}")
        f.write(f"\nwilliams_theta_mode: {config.williams_dict.get('theta_mode', 'atan2')}")
        f.write(f"\nwilliams_r_min: {config.williams_dict.get('r_min', 1e-6)}")
        f.write(f"\n--- enriched_ansatz ---")
        f.write(f"\nansatz_enable: {config.ansatz_dict.get('enable', False)}")
        f.write(f"\nansatz_x_tip: {config.ansatz_dict.get('x_tip', 0.0)}")
        f.write(f"\nansatz_y_tip: {config.ansatz_dict.get('y_tip', 0.0)}")
        f.write(f"\nansatz_r_cutoff: {config.ansatz_dict.get('r_cutoff', 0.1)}")
        f.write(f"\nansatz_nu: {config.ansatz_dict.get('nu', 0.3)}")
        f.write(f"\nansatz_c_init: {config.ansatz_dict.get('c_init', 0.01)}")
        f.write(f"\nansatz_modes: {config.ansatz_dict.get('modes', ['I'])}")
        f.write(f"\n--- symmetry ---")
        f.write(f"\nsymmetry_prior: {config.symmetry_prior}")
        f.write(f"\n--- spatial_alpha_T ---")
        sp = fat.get("spatial_alpha_T", {})
        f.write(f"\nspAlphaT_enable: {sp.get('enable', False)}")
        f.write(f"\nspAlphaT_beta: {sp.get('beta', 0.0)}")
        f.write(f"\nspAlphaT_r_T: {sp.get('r_T', 0.1)}")
        f.write(f"\nspAlphaT_x_tip: {sp.get('x_tip', 0.0)}")
        f.write(f"\nspAlphaT_y_tip: {sp.get('y_tip', 0.0)}")
        f.write(f"\n[runner] {runner_name}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=10)
    p.add_argument("--seed", type=int, default=1)
    args = p.parse_args()

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

    # Override run controls
    config.fatigue_dict["disp_max"] = args.umax
    config.fatigue_dict["n_cycles"] = args.n_cycles
    config.rebuild_disp_cyclic()
    config.symmetry_prior = True

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
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
        + "_symY2"
    )
    config.model_path = here / Path(dir_name)
    config.trainedModel_path = config.model_path / Path("best_models/")
    config.intermediateModel_path = config.model_path / Path("intermediate_models/")
    config.model_path.mkdir(parents=True, exist_ok=True)
    config.trainedModel_path.mkdir(parents=True, exist_ok=True)
    config.intermediateModel_path.mkdir(parents=True, exist_ok=True)
    # Rebuild TensorBoard writer after archive-path override.
    # Without this, logs keep going to the import-time baseline path in config.py.
    try:
        config.writer.close()
    except Exception:
        pass
    config.writer = config.SummaryWriter(config.model_path / Path("TBruns"))
    _rewrite_model_settings(config, "run_symmetry_prior_umax.py")

    print("=" * 72)
    print("Symmetry-prior baseline PIDL runner")
    print(f"  U_max     = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  archive   = {dir_name}")
    print(f"  full path = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
