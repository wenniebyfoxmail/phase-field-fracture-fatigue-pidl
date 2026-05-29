#!/usr/bin/env python3
"""Fixed-alpha_T PIDL forward diagnostic for soft-hist0 reverseBC FEM.

This is the gate before inverse calibration: train the ordinary reverseBC PIDL
forward model with alpha_T fixed at the FEM value, then compare fields post hoc
against the soft diffuse-precrack, alpha_bar=0 FEM handoff.

Do not run this training loop on Mac.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=69)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--alpha-T", type=float, default=0.5)
    p.add_argument("--tol-ir", type=float, default=1e-3,
                   help="PIDL irreversibility tolerance; 1e-3 matches the FEM export.")
    p.add_argument("--fem-dir", default="",
                   help="Optional FEM handoff dir, recorded and sanity-checked but not used as loss.")
    args = p.parse_args()

    sys.argv = [
        "run_reversebc_soft_hist0_forward_umax.py",
        "8", "400", str(args.seed), "TrainableReLU", "1.0",
    ]

    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config

    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
    config.symmetry_prior = False
    config.adaptive_sampling_dict["enable"] = False
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.fatigue_dict.pop("symmetry_soft", None)
    config.fatigue_dict.pop("side_traction_soft", None)

    config.PFF_model_dict["tol_ir"] = float(args.tol_ir)
    config.fatigue_dict["accum_type"] = "carrara"
    config.fatigue_dict["degrad_type"] = "asymptotic"
    config.fatigue_dict["alpha_T"] = float(args.alpha_T)
    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.fatigue_dict["enable_E_fallback"] = False
    config.fatigue_dict["fracture_confirm_cycles"] = 10
    config.rebuild_disp_cyclic()

    fem_cycles = None
    fem_dir = Path(args.fem_dir).expanduser() if args.fem_dir else None
    if fem_dir is not None:
        from fem_supervision import FEMSupervision
        fem_sup = FEMSupervision(umax=float(args.umax), fem_dir=fem_dir)
        fem_cycles = fem_sup.cycles
        fem_dir = fem_sup.fem_dir

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    run_tag = f"_reverseBC_softHist0_forward_tolir{args.tol_ir:g}"
    dir_name = (
        "hl_" + str(config.network_dict["hidden_layers"])
        + "_Neurons_" + str(config.network_dict["neurons"])
        + "_activation_" + config.network_dict["activation"]
        + "_coeff_" + str(config.network_dict["init_coeff"])
        + "_Seed_" + str(config.network_dict["seed"])
        + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
        + "_gradient_" + str(config.numr_dict["gradient_type"])
        + fatigue_tag
        + run_tag
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
        f.write("runner: run_reversebc_soft_hist0_forward_umax.py\n")
        f.write("purpose: fixed-alpha_T forward gate for soft-hist0 reverseBC FEM inverse\n")
        f.write("exact_bc_enable: false\n")
        f.write("pidl_bc: baseline hard ansatz; u_x clamped on top/bottom by construction\n")
        f.write(f"umax: {args.umax}\n")
        f.write(f"n_cycles: {args.n_cycles}\n")
        f.write(f"seed: {args.seed}\n")
        f.write(f"alpha_T: {config.fatigue_dict['alpha_T']}\n")
        f.write(f"tol_ir: {config.PFF_model_dict['tol_ir']}\n")
        f.write(f"fem_dir: {fem_dir}\n")
        f.write(f"fem_cycles: {fem_cycles}\n")

    print("=" * 72)
    print("Fixed-alpha_T PIDL forward diagnostic for soft-hist0 reverseBC FEM")
    print(f"  U_max    = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  alpha_T  = {args.alpha_T:g} fixed")
    print(f"  tol_ir   = {args.tol_ir:g}")
    print("  BC       = PIDL baseline hard ansatz (reverseBC-compatible)")
    print(f"  FEM dir  = {fem_dir}")
    print(f"  archive  = {dir_name}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
