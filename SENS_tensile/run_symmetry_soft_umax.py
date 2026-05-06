#!/usr/bin/env python3
"""run_symmetry_soft_umax.py — baseline architecture + soft symmetry penalty (B path).

Soft mirror-symmetry regularization for SENT geometry. Unlike the hard
y² input transformation (run_symmetry_prior_umax.py), this approach:

- Keeps NN architecture and input distribution UNCHANGED (no y² rescale,
  no architectural restriction on NN output parity)
- Adds a 3-term penalty to the variational loss on NN raw correction:
    L_alpha = lam_alpha * ‖α(x,y) − α(x,−y)‖²   (even, after constraint)
    L_u     = lam_u     * ‖u_x_corr(x,y) − u_x_corr(x,−y)‖²
    L_v     = lam_v     * ‖u_y_corr(x,y) + u_y_corr(x,−y)‖²
- Single forward pass per epoch via batch doubling (~2× compute vs baseline)

Expected vs hard y² prior:
- Speed: ~2× baseline (vs hard y² ~12×)
- Symmetry: V4 d-skew rms small but NOT 0 (soft enforcement)
- N_f / Kt: closer to baseline (no architectural restriction)

Usage:
  python run_symmetry_soft_umax.py 0.12 --n-cycles 10 --seed 1
  python run_symmetry_soft_umax.py 0.12 --n-cycles 300 --seed 1 --lam-alpha 10 --lam-u 1 --lam-v 1
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path


def _rewrite_model_settings(config, runner_label):
    """Re-write model_settings.txt in the corrected archive path."""
    fat = config.fatigue_dict
    sym = fat.get('symmetry_soft', {})
    with open(config.model_path / Path("model_settings.txt"), "w") as f:
        f.write(f"hidden_layers: {config.network_dict['hidden_layers']}")
        f.write(f"\nneurons: {config.network_dict['neurons']}")
        f.write(f"\nseed: {config.network_dict['seed']}")
        f.write(f"\nactivation: {config.network_dict['activation']}")
        f.write(f"\ncoeff: {config.network_dict['init_coeff']}")
        f.write(f"\nPFF_model: {config.PFF_model_dict['PFF_model']}")
        f.write(f"\nse_split: {config.PFF_model_dict['se_split']}")
        f.write(f"\ndisp_max: {fat['disp_max']}")
        f.write(f"\nn_cycles: {fat['n_cycles']}")
        f.write(f"\naccum_type: {fat['accum_type']}")
        f.write(f"\ndegrad_type: {fat['degrad_type']}")
        f.write(f"\nalpha_T: {fat['alpha_T']}")
        f.write(f"\nR_ratio: {fat['R_ratio']}")
        f.write(f"\nsymmetry_soft: {sym}")
        f.write(f"\n[runner] {runner_label}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=300)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--lam-alpha", type=float, default=1.0,
                   help="Soft α-symmetry penalty weight (default 1.0)")
    p.add_argument("--lam-u", type=float, default=1.0,
                   help="Soft u_x_corr even penalty weight (default 1.0)")
    p.add_argument("--lam-v", type=float, default=1.0,
                   help="Soft u_y_corr odd penalty weight (default 1.0)")
    args = p.parse_args()

    if not (0.05 <= args.umax <= 0.20):
        raise SystemExit(f"umax={args.umax} out of sensible range [0.05, 0.20]")

    sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]
    here = Path(__file__).parent
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config

    # Baseline architecture only (no Williams, no Enriched, no hard symY2)
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.symmetry_prior = False  # explicit: NOT using hard prior

    # Override run controls
    config.fatigue_dict["disp_max"] = args.umax
    config.fatigue_dict["n_cycles"] = args.n_cycles
    config.rebuild_disp_cyclic()

    # ★ Soft symmetry penalty configuration (B path)
    config.fatigue_dict["symmetry_soft"] = {
        "enable":       True,
        "lambda_alpha": float(args.lam_alpha),
        "lambda_u":     float(args.lam_u),
        "lambda_v":     float(args.lam_v),
    }

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    sym_tag = f"_symSoft_la{args.lam_alpha}_lu{args.lam_u}_lv{args.lam_v}"
    dir_name = (
        "hl_" + str(config.network_dict["hidden_layers"])
        + "_Neurons_" + str(config.network_dict["neurons"])
        + "_activation_" + config.network_dict["activation"]
        + "_coeff_" + str(config.network_dict["init_coeff"])
        + "_Seed_" + str(config.network_dict["seed"])
        + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
        + "_gradient_" + str(config.numr_dict["gradient_type"])
        + fatigue_tag
        + sym_tag
    )
    config.model_path = here / Path(dir_name)
    config.trainedModel_path = config.model_path / Path("best_models/")
    config.intermediateModel_path = config.model_path / Path("intermediate_models/")
    config.model_path.mkdir(parents=True, exist_ok=True)
    config.trainedModel_path.mkdir(parents=True, exist_ok=True)
    config.intermediateModel_path.mkdir(parents=True, exist_ok=True)

    # Rebuild TensorBoard writer to point to correct archive path
    try:
        config.writer.close()
    except Exception:
        pass
    config.writer = config.SummaryWriter(config.model_path / Path("TBruns"))
    _rewrite_model_settings(config, "run_symmetry_soft_umax.py")

    print("=" * 72)
    print("Soft mirror-symmetry baseline PIDL runner (B path)")
    print(f"  U_max         = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  λ_alpha       = {args.lam_alpha}")
    print(f"  λ_u           = {args.lam_u}")
    print(f"  λ_v           = {args.lam_v}")
    print(f"  archive       = {dir_name}")
    print(f"  device        = {config.device}")
    print("=" * 72)

    # Now exec main.py contents with the prepared config
    main_path = here / "main.py"
    exec(compile(main_path.read_text(), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
