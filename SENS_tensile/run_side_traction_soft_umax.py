#!/usr/bin/env python3
"""run_side_traction_soft_umax.py — baseline + soft symmetry + soft side-traction penalty.

Extends the B-path soft symmetry runner with an additional soft traction-free
boundary penalty on x=±0.5 (the side edges of the SENT specimen).

Motivation (FEM-8 result, 2026-05-08):
  PIDL V7 (traction residual on side edges) = 17–30% relative.
  FEM V7 = 0.12% (satisfied via natural BC in weak form).
  Gap = 140–250×.  Root cause: side BCs are measure-zero in the Deep Ritz
  energy integral, so the NN learns them poorly.

Penalty added to loss each training step:
  L_strac = lam_xx * mean((σ_xx / σ_ref)²)
          + lam_xy * mean((σ_xy / σ_ref)²)
  evaluated at n_bdy_pts query points on {x=−0.5} ∪ {x=+0.5}
  via AD-mode displacement gradient at fixed boundary sample points.

Combined loss per cycle:
  L = log10(E_el + E_d + E_hist) + L_sym + L_strac

Smoke test usage:
  python run_side_traction_soft_umax.py 0.12 --n-cycles 5 --seed 1
Full run:
  python run_side_traction_soft_umax.py 0.12 --n-cycles 300 --seed 1 \\
      --lam-alpha 1 --lam-u 1 --lam-v 1 --lam-xx 1 --lam-xy 1

Key CLI options:
  --lam-alpha, --lam-u, --lam-v   symmetry penalty weights (default 1.0)
  --lam-xx, --lam-xy              side-traction penalty weights (default 1.0)
  --sigma-ref                     stress normalisation (default 1.0 = E=1 unit)
  --no-sym                        disable symmetry penalty (run traction-only)
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path


def _rewrite_model_settings(config, runner_label):
    """Re-write model_settings.txt in the archive path."""
    fat = config.fatigue_dict
    sym  = fat.get('symmetry_soft',   {})
    strc = fat.get('side_traction_soft', {})
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
        f.write(f"\nside_traction_soft: {strc}")
        f.write(f"\n[runner] {runner_label}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles",  type=int,   default=300)
    p.add_argument("--seed",      type=int,   default=1)
    # Symmetry penalty
    p.add_argument("--lam-alpha", type=float, default=1.0,
                   help="Soft α-symmetry penalty weight (default 1.0)")
    p.add_argument("--lam-u",     type=float, default=1.0,
                   help="Soft u_x_corr even penalty weight (default 1.0)")
    p.add_argument("--lam-v",     type=float, default=1.0,
                   help="Soft u_y_corr odd penalty weight (default 1.0)")
    # Side-traction penalty
    p.add_argument("--lam-xx",    type=float, default=1.0,
                   help="σ_xx traction penalty weight (default 1.0)")
    p.add_argument("--lam-xy",    type=float, default=1.0,
                   help="σ_xy traction penalty weight (default 1.0)")
    p.add_argument("--sigma-ref", type=float, default=1.0,
                   help="Stress normalisation σ_ref (default 1.0 = E=1 unit scale)")
    p.add_argument("--n-bdy-pts", type=int,   default=51,
                   help="Boundary query points per side edge (default 51)")
    # Flags
    p.add_argument("--no-sym",    action="store_true",
                   help="Disable symmetry penalty (run side-traction only)")
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
    config.symmetry_prior = False

    # Override run controls
    config.fatigue_dict["disp_max"] = args.umax
    config.fatigue_dict["n_cycles"] = args.n_cycles
    config.rebuild_disp_cyclic()

    # ★ Soft symmetry penalty (B path) — disable if --no-sym
    sym_enabled = not args.no_sym
    config.fatigue_dict["symmetry_soft"] = {
        "enable":       sym_enabled,
        "lambda_alpha": float(args.lam_alpha),
        "lambda_u":     float(args.lam_u),
        "lambda_v":     float(args.lam_v),
    }

    # ★ Soft side-traction penalty
    config.fatigue_dict["side_traction_soft"] = {
        "enable":    True,
        "lam_xx":    float(args.lam_xx),
        "lam_xy":    float(args.lam_xy),
        "sigma_ref": float(args.sigma_ref),
        "n_bdy_pts": int(args.n_bdy_pts),
    }

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    sym_tag   = (f"_symSoft_la{args.lam_alpha}_lu{args.lam_u}_lv{args.lam_v}"
                 if sym_enabled else "_noSym")
    strac_tag = f"_strac_xx{args.lam_xx}_xy{args.lam_xy}_sref{args.sigma_ref}"

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
        + strac_tag
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
    _rewrite_model_settings(config, "run_side_traction_soft_umax.py")

    print("=" * 72)
    print("Soft symmetry + soft side-traction PIDL runner")
    print(f"  U_max         = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  sym penalty   = {sym_enabled}  (λ_α={args.lam_alpha}, λ_u={args.lam_u}, λ_v={args.lam_v})")
    print(f"  strac penalty = ON  (λ_xx={args.lam_xx}, λ_xy={args.lam_xy}, σ_ref={args.sigma_ref})")
    print(f"  archive       = {dir_name}")
    print(f"  device        = {config.device}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
