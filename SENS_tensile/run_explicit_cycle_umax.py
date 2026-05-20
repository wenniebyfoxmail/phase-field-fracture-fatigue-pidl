#!/usr/bin/env python3
"""run_explicit_cycle_umax.py — loading-cycle alignment runner.

Controlled alignment Variant 4:
  replace the one-peak-per-cycle abstraction with explicit within-cycle load
  substeps for a short diagnostic run.

Default substep factors for R=0:
  [0.0, 0.5, 1.0, 0.5, 0.0] * Umax

Important:
  - `--n-cycles` is physical cycles.
  - the training loop still logs/saves by substep index, so N=10 with 5 substeps
    produces 50 training steps/checkpoints.
  - intended for N=5 or N=10 smoke only; do not launch production without first
    checking alpha_bar slope and psi+/boundary diagnostics.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


def _parse_factors(raw: str) -> list[float]:
    vals = [float(x) for x in raw.split(",") if x.strip()]
    if len(vals) < 2:
        raise argparse.ArgumentTypeError("need at least two substep factors")
    return vals


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=5,
                   help="Physical cycles; total training steps = n_cycles * len(substeps)")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--substeps", type=_parse_factors, default=_parse_factors("0,0.5,1,0.5,0"),
                   help="Comma-separated load factors multiplying Umax")
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
    config.exact_bc_dict["enable"] = False

    factors = np.asarray(args.substeps, dtype=float)
    disp_steps = np.tile(factors * float(args.umax), int(args.n_cycles))

    config.fatigue_dict["disp_max"] = float(args.umax)
    config.fatigue_dict["n_cycles"] = int(args.n_cycles)
    config.fatigue_dict["loading_type"] = "cyclic"
    config.fatigue_dict["explicit_cycle_substeps"] = int(len(factors))
    config.fatigue_dict["explicit_cycle_factors"] = [float(x) for x in factors]
    config.fatigue_dict["log_every_n_cycles"] = 1
    config.disp_cyclic = disp_steps

    fat = config.fatigue_dict
    total_steps = len(disp_steps)
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_Ncyc{fat['n_cycles']}_Nstep{total_steps}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    sub_tag = "_explicitCycle_" + "-".join(f"{x:g}" for x in factors)
    dir_name = (
        "hl_" + str(config.network_dict["hidden_layers"])
        + "_Neurons_" + str(config.network_dict["neurons"])
        + "_activation_" + config.network_dict["activation"]
        + "_coeff_" + str(config.network_dict["init_coeff"])
        + "_Seed_" + str(config.network_dict["seed"])
        + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
        + "_gradient_" + str(config.numr_dict["gradient_type"])
        + fatigue_tag
        + sub_tag
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

    with open(config.model_path / Path("model_settings.txt"), "w") as f:
        f.write(f"hidden_layers: {config.network_dict['hidden_layers']}")
        f.write(f"\nneurons: {config.network_dict['neurons']}")
        f.write(f"\nseed: {config.network_dict['seed']}")
        f.write(f"\nactivation: {config.network_dict['activation']}")
        f.write(f"\ncoeff: {config.network_dict['init_coeff']}")
        f.write(f"\nPFF_model: {config.PFF_model_dict['PFF_model']}")
        f.write(f"\nse_split: {config.PFF_model_dict['se_split']}")
        f.write(f"\ntol_ir: {config.PFF_model_dict['tol_ir']}")
        f.write(f"\ndisp_max: {fat['disp_max']}")
        f.write(f"\nn_cycles_physical: {fat['n_cycles']}")
        f.write(f"\nn_training_steps: {total_steps}")
        f.write(f"\nexplicit_cycle_substeps: {fat['explicit_cycle_substeps']}")
        f.write(f"\nexplicit_cycle_factors: {fat['explicit_cycle_factors']}")
        f.write(f"\naccum_type: {fat['accum_type']}")
        f.write(f"\ndegrad_type: {fat['degrad_type']}")
        f.write(f"\nalpha_T: {fat['alpha_T']}")
        f.write(f"\nR_ratio: {fat['R_ratio']}")
        f.write("\n[runner] run_explicit_cycle_umax.py")

    print("=" * 72)
    print("Controlled alignment Variant 4: explicit-cycle runner")
    print(f"  U_max          = {args.umax} | physical cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  substeps       = {list(factors)}")
    print(f"  training steps = {total_steps}")
    print(f"  archive        = {dir_name}")
    print(f"  full path      = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
