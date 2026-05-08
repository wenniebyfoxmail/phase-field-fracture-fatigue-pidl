#!/usr/bin/env python3
"""run_mirror_alpha_umax.py — soft symmetry penalty + A1 post-hoc mirror α (ratchet break).

Motivation (2026-05-08, after expert ratchet diagnosis + strac penalty oscillation):
  Cyclic Carrara accumulator (Δᾱ = ReLU(Δψ⁺)·Δψ⁺) is unidirectional. Tiny
  initial asymmetry from NN/optim/sampling → amplified cycle-by-cycle through
  memory feedback (ᾱ → f(ᾱ) → easier damage → larger Δᾱ next cycle). The strac
  AD-mode penalty experiment (Queue F, May 8) showed bimodal V7 oscillation
  10-30% / 500-2000% — penalty fights ratchet but cannot stabilise.

A1 intervention:
  At end of each cycle, symmetrise hist_fat about y=0:
      hist_fat[i] = 0.5 * (hist_fat[i] + hist_fat[mirror(i)])
  where mirror(i) = element with centroid closest to (x_i, -y_i).
  Mesh is fixed → mirror map computed ONCE at fatigue init.

  SENT geometry is exactly symmetric about y=0 under symmetric BCs, so this is
  a physically defensible operator (not changing the constitutive equation —
  enforcing the geometric symmetry the solution should already have).

This runner = baseline NN + soft sym penalty (Queue E) + mirror α (A1).
NO strac penalty, NO Williams, NO Enriched.

Smoke test:
  python run_mirror_alpha_umax.py 0.12 --n-cycles 5 --seed 1
Production:
  python run_mirror_alpha_umax.py 0.12 --n-cycles 300 --seed 1 \\
      --lam-alpha 1 --lam-u 1 --lam-v 1
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path


def _rewrite_model_settings(config, runner_label):
    fat = config.fatigue_dict
    sym = fat.get('symmetry_soft', {})
    mir = fat.get('mirror_alpha_y', {})
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
        f.write(f"\nmirror_alpha_y: {mir}")
        f.write(f"\n[runner] {runner_label}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=300)
    p.add_argument("--seed",     type=int, default=1)
    # Symmetry penalty (kept on by default — has independent V4 benefit beyond mirror α)
    p.add_argument("--lam-alpha", type=float, default=1.0,
                   help="Soft α-symmetry penalty weight (default 1.0)")
    p.add_argument("--lam-u",     type=float, default=1.0,
                   help="Soft u_x even penalty weight (default 1.0)")
    p.add_argument("--lam-v",     type=float, default=1.0,
                   help="Soft u_y odd penalty weight (default 1.0)")
    p.add_argument("--no-sym",    action="store_true",
                   help="Disable soft symmetry penalty (mirror α only)")
    args = p.parse_args()

    if not (0.05 <= args.umax <= 0.20):
        raise SystemExit(f"umax={args.umax} out of sensible range [0.05, 0.20]")

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
    config.symmetry_prior = False

    config.fatigue_dict["disp_max"] = args.umax
    config.fatigue_dict["n_cycles"] = args.n_cycles
    config.rebuild_disp_cyclic()

    # Soft symmetry penalty
    sym_enabled = not args.no_sym
    config.fatigue_dict["symmetry_soft"] = {
        "enable":       sym_enabled,
        "lambda_alpha": float(args.lam_alpha),
        "lambda_u":     float(args.lam_u),
        "lambda_v":     float(args.lam_v),
    }

    # ★ A1: post-hoc mirror α
    config.fatigue_dict["mirror_alpha_y"] = {"enable": True}

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    sym_tag = (f"_symSoft_la{args.lam_alpha}_lu{args.lam_u}_lv{args.lam_v}"
               if sym_enabled else "_noSym")
    mir_tag = "_mirrorA1"

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
        + mir_tag
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
    _rewrite_model_settings(config, "run_mirror_alpha_umax.py")

    print("=" * 72)
    print("Soft symmetry + A1 post-hoc mirror α PIDL runner")
    print(f"  U_max         = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  sym penalty   = {sym_enabled}  (λ_α={args.lam_alpha}, λ_u={args.lam_u}, λ_v={args.lam_v})")
    print(f"  mirror α (A1) = ON  (hist_fat symmetrised about y=0 each cycle)")
    print(f"  archive       = {dir_name}")
    print(f"  device        = {config.device}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
