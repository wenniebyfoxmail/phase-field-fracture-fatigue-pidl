#!/usr/bin/env python3
"""run_fem_anchor_symmetry_soft_umax.py — FEM-anchor BC + soft symmetry penalty.

This is the soft counterpart to run_fem_anchor_symmetry_prior_umax.py. It keeps
the GRIPHFiTH essential-BC alignment from run_fem_anchor_bc_umax.py, but uses
the existing soft mirror-symmetry loss instead of the hard y^2 parity prior.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--lam-alpha", type=float, default=1.0)
    p.add_argument("--lam-u", type=float, default=1.0)
    p.add_argument("--lam-v", type=float, default=1.0)
    args = p.parse_args()

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
    config.exact_bc_dict["enable"] = True
    config.exact_bc_dict["mode"] = "fem_anchor"

    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.rebuild_disp_cyclic()

    config.fatigue_dict["symmetry_soft"] = {
        "enable": True,
        "lambda_alpha": float(args.lam_alpha),
        "lambda_u": float(args.lam_u),
        "lambda_v": float(args.lam_v),
    }

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    sym_tag = f"_femAnchorBC_symSoft_la{args.lam_alpha}_lu{args.lam_u}_lv{args.lam_v}"
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

    try:
        config.writer.close()
    except Exception:
        pass
    config.writer = config.SummaryWriter(config.model_path / Path("TBruns"))

    sym = config.fatigue_dict["symmetry_soft"]
    with open(config.model_path / Path("model_settings.txt"), "w") as f:
        f.write(f"hidden_layers: {config.network_dict['hidden_layers']}")
        f.write(f"\nneurons: {config.network_dict['neurons']}")
        f.write(f"\nseed: {config.network_dict['seed']}")
        f.write(f"\nactivation: {config.network_dict['activation']}")
        f.write(f"\ncoeff: {config.network_dict['init_coeff']}")
        f.write(f"\nPFF_model: {config.PFF_model_dict['PFF_model']}")
        f.write(f"\nse_split: {config.PFF_model_dict['se_split']}")
        f.write(f"\ntol_ir: {config.PFF_model_dict['tol_ir']}")
        f.write(f"\nexact_bc_enable: {config.exact_bc_dict['enable']}")
        f.write(f"\nexact_bc_mode: {config.exact_bc_dict['mode']}")
        f.write(f"\nsymmetry_prior: {config.symmetry_prior}")
        f.write(f"\nsymmetry_soft: {sym}")
        f.write(f"\ndisp_max: {fat['disp_max']}")
        f.write(f"\nn_cycles: {fat['n_cycles']}")
        f.write(f"\naccum_type: {fat['accum_type']}")
        f.write(f"\ndegrad_type: {fat['degrad_type']}")
        f.write(f"\nalpha_T: {fat['alpha_T']}")
        f.write(f"\nR_ratio: {fat['R_ratio']}")
        f.write("\n[runner] run_fem_anchor_symmetry_soft_umax.py")

    print("=" * 72)
    print("Controlled alignment: FEM-anchor BC + soft symmetry penalty")
    print(f"  U_max     = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print("  BC        = v bottom/top hard, u fixed only at bottom-left anchor")
    print(f"  symmetry  = soft la={args.lam_alpha}, lu={args.lam_u}, lv={args.lam_v}")
    print(f"  archive   = {dir_name}")
    print(f"  full path = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
