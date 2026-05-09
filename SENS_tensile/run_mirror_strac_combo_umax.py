#!/usr/bin/env python3
"""run_mirror_strac_combo_umax.py — soft sym + A1 mirror α + Strac side-traction penalty.

Combo runner stacking three V7/V4 mitigations:
  1. Soft symmetry penalty (V4 14× reduction)        — commit 90f2297
  2. A1 post-hoc mirror α (Carrara ratchet break)    — commit 6a8d778
  3. Strac side-traction penalty (V7 boundary push)  — commit 6bf05d3

Motivation (2026-05-09, Request 6 Phase C from Mac):
  A1 alone introduces a LEFT-edge σ_xx spike (Windows Request 5 outbox: raw
  240-280 vs Strac baseline 0.01, L/R ratio ~2700×). Question: does adding
  Strac penalty rescue this LEFT spike (i.e. mitigations are stackable) or
  does the spike persist (i.e. destructive interaction at representation
  level)?

This runner combines all three; CLI keeps separate weights so individual
penalties can be turned on/off via flags.

Usage:
  python run_mirror_strac_combo_umax.py 0.12 --n-cycles 5 --seed 1
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path


def _rewrite_model_settings(config, runner_label):
    fat = config.fatigue_dict
    sym  = fat.get('symmetry_soft',     {})
    mir  = fat.get('mirror_alpha_y',    {})
    strc = fat.get('side_traction_soft',{})
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
        f.write(f"\nside_traction_soft: {strc}")
        f.write(f"\n[runner] {runner_label}")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=300)
    p.add_argument("--seed",     type=int, default=1)
    # Symmetry penalty
    p.add_argument("--lam-alpha", type=float, default=1.0)
    p.add_argument("--lam-u",     type=float, default=1.0)
    p.add_argument("--lam-v",     type=float, default=1.0)
    # Side-traction penalty
    p.add_argument("--lam-xx",    type=float, default=1.0)
    p.add_argument("--lam-xy",    type=float, default=1.0)
    p.add_argument("--sigma-ref", type=float, default=1.0)
    p.add_argument("--n-bdy-pts", type=int,   default=51)
    # On/off toggles for ablation
    p.add_argument("--no-sym",    action="store_true")
    p.add_argument("--no-mirror", action="store_true")
    p.add_argument("--no-strac",  action="store_true")
    args = p.parse_args()

    if not (0.05 <= args.umax <= 0.20):
        raise SystemExit(f"umax={args.umax} out of sensible range")

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

    sym_enabled    = not args.no_sym
    mirror_enabled = not args.no_mirror
    strac_enabled  = not args.no_strac

    config.fatigue_dict["symmetry_soft"] = {
        "enable":       sym_enabled,
        "lambda_alpha": float(args.lam_alpha),
        "lambda_u":     float(args.lam_u),
        "lambda_v":     float(args.lam_v),
    }
    config.fatigue_dict["mirror_alpha_y"] = {"enable": mirror_enabled}
    config.fatigue_dict["side_traction_soft"] = {
        "enable":    strac_enabled,
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
    mir_tag   = "_mirrorA1" if mirror_enabled else "_noMirror"
    strac_tag = (f"_strac_xx{args.lam_xx}_xy{args.lam_xy}_sref{args.sigma_ref}"
                 if strac_enabled else "_noStrac")

    dir_name = (
        "hl_" + str(config.network_dict["hidden_layers"])
        + "_Neurons_" + str(config.network_dict["neurons"])
        + "_activation_" + config.network_dict["activation"]
        + "_coeff_" + str(config.network_dict["init_coeff"])
        + "_Seed_" + str(config.network_dict["seed"])
        + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
        + "_gradient_" + str(config.numr_dict["gradient_type"])
        + fatigue_tag + sym_tag + mir_tag + strac_tag
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
    _rewrite_model_settings(config, "run_mirror_strac_combo_umax.py")

    print("=" * 72)
    print("Soft sym + A1 mirror α + Strac penalty COMBO runner")
    print(f"  U_max         = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  sym penalty   = {sym_enabled}    (λ_α={args.lam_alpha}, λ_u={args.lam_u}, λ_v={args.lam_v})")
    print(f"  mirror α (A1) = {mirror_enabled}")
    print(f"  strac penalty = {strac_enabled}  (λ_xx={args.lam_xx}, λ_xy={args.lam_xy}, σ_ref={args.sigma_ref})")
    print(f"  archive       = {dir_name}")
    print(f"  device        = {config.device}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
