#!/usr/bin/env python3
"""run_exact_bc_fourier_umax.py — C4 exact-BC + C10 Fourier-feature stack.

Stacks two architectural mitigations:
  - C4 (`run_exact_bc_umax.py`): Sukumar-style plane-strain Poisson lifting + tb·side^2
    correction gating, forces sigma_xx = sigma_xy = 0 at x = +/-0.5 by construction.
  - C10 (`run_fourier_features_umax.py`): random Fourier features at sigma=30 sweet spot
    (Tancik 2020, Xu 2025), prepended as gamma(x) = [cos(2*pi*B*x), sin(2*pi*B*x)]
    before the NN, mitigates spectral bias at the tip-zone high-frequency content.

Motivation:
  - C4 alone: V7 PASS by construction, V4 RMS = 0.003. alpha_max @ u=0.12 N=100 = 23.05.
  - Fourier sigma=30 alone (Windows-PIDL Request 8/9): alpha_max @ c50 = 14.26 but V7
    sigma_xx ringing at free edges, 73.9% (2.8x baseline) -- Tancik 2020 known trade-off.
  - This runner tests whether the two stack: V7 closed by C4's analytical sigma_xx=0 +
    Fourier's spectral lift kept for alpha_max.

The config knobs are orthogonal: exact_bc_dict mutates the BC composition layer in
FieldComputation.fieldCalculation (post-NN), fourier_dict mutates the NN input wrapper
(pre-NN). They are independent and can be enabled together without mutual exclusion.

Usage:
  python run_exact_bc_fourier_umax.py 0.12 --n-cycles 50 --seed 1 --sigma 30 --nu 0.3
"""
import argparse
import os
import sys
from pathlib import Path


def _rewrite_model_settings(config, runner_name: str) -> None:
    fat = config.fatigue_dict
    exact_bc = config.exact_bc_dict
    fr = config.fourier_dict
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
        f.write(f"\naccum_type: {fat.get('accum_type')}")
        f.write(f"\ndegrad_type: {fat.get('degrad_type')}")
        f.write(f"\nalpha_T: {fat.get('alpha_T')}")
        f.write(f"\n--- exact_bc ---")
        f.write(f"\nexact_bc_enable: {exact_bc.get('enable', False)}")
        f.write(f"\nexact_bc_mode: {exact_bc.get('mode')}")
        f.write(f"\nexact_bc_nu: {exact_bc.get('nu')}")
        f.write(f"\n--- fourier ---")
        f.write(f"\nfourier_enable: {fr.get('enable', False)}")
        f.write(f"\nfourier_sigma: {fr.get('sigma')}")
        f.write(f"\nfourier_n_features: {fr.get('n_features')}")
        f.write(f"\nfourier_seed: {fr.get('seed')}")
        f.write(f"\n[runner] {runner_name}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=50)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--nu", type=float, default=0.3,
                   help="Poisson ratio used in the plane-strain lifting field (C4)")
    p.add_argument("--sigma", type=float, default=30.0,
                   help="Fourier feature std (C10; default 30 = sweet spot)")
    p.add_argument("--n-features", type=int, default=128,
                   help="Number of Fourier frequencies (C10)")
    p.add_argument("--fourier-seed", type=int, default=0,
                   help="B-matrix random init seed (C10)")
    p.add_argument("--force-cpu", action="store_true",
                   help="Hide CUDA before importing config; Mac dev smoke")
    args = p.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

    here = Path(__file__).parent
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config

    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.symmetry_prior = False

    config.fatigue_dict["disp_max"] = args.umax
    config.fatigue_dict["n_cycles"] = args.n_cycles
    config.rebuild_disp_cyclic()

    config.exact_bc_dict = {
        "enable": True,
        "mode": "sent_plane_strain",
        "nu": float(args.nu),
    }

    config.fourier_dict["enable"] = True
    config.fourier_dict["sigma"] = float(args.sigma)
    config.fourier_dict["n_features"] = int(args.n_features)
    config.fourier_dict["seed"] = int(args.fourier_seed)

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
        + f"_exactBCsent_nu{args.nu}"
        + f"_fourier_sig{args.sigma}_nf{args.n_features}"
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
    _rewrite_model_settings(config, "run_exact_bc_fourier_umax.py")

    print("=" * 72)
    print("C4 exact-BC + C10 Fourier-feature STACK runner")
    print(f"  U_max       = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  nu (C4)     = {args.nu}")
    print(f"  sigma (C10) = {args.sigma} | n_features = {args.n_features}")
    print(f"  device      = {config.device}")
    print(f"  archive     = {dir_name}")
    print(f"  full path   = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
