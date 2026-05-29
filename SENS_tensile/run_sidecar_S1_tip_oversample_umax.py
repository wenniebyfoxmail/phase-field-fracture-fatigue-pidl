#!/usr/bin/env python3
"""run_sidecar_S1_tip_oversample_umax.py — Sidecar S1 runner.

Spec: docs/sidecar_true_adaptive_sampling.md (Stage S1).

What this runner does:
  - Enable `sidecar_S1_dict` (static-tip mesh oversampling, 1-to-4 red refinement
    with edge-midpoint sharing + green closure near the crack tip).
  - Keep the Deep Ritz / Carrara loss formula untouched.
  - Disable all competing architectural / loss-weighting variants so the test
    is interpretable in isolation (Rule 4: same baseline stack except sampling).

Differences vs `run_adaptive_sampling_umax.py` (C6 FI-PINN reweight):
  - C6 reweights per-element loss inside log10(sum E). S1 changes ONLY mesh
    density. No reweighting.
  - C6 writes into crack_tip_weights. S1 does not touch the loss path.

Usage:
  python run_sidecar_S1_tip_oversample_umax.py 0.12 --n-cycles 5 --seed 1
  python run_sidecar_S1_tip_oversample_umax.py 0.12 --n-cycles 10 --seed 1 --r-tip 0.05 --n-passes 1
  python run_sidecar_S1_tip_oversample_umax.py 0.12 --n-cycles 10 --seed 1 --r-tip 0.05 --n-passes 2

Output archive tag suffix: `_sidecarS1_rt<r_tip>_np<n_passes>`.
"""
import argparse
import os
import sys
from pathlib import Path


def _rewrite_model_settings(config, runner_name: str) -> None:
    fat = config.fatigue_dict
    sdct = config.sidecar_S1_dict
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
        f.write(f"\nalpha_T: {fat.get('alpha_T')}")
        f.write(f"\n--- sidecar S1 (static-tip oversampling) ---")
        f.write(f"\nS1_enable: {sdct.get('enable')}")
        f.write(f"\nS1_tip_xy: {sdct.get('tip_xy')}")
        f.write(f"\nS1_r_tip_sample: {sdct.get('r_tip_sample')}")
        f.write(f"\nS1_n_refine_passes: {sdct.get('n_refine_passes')}")
        f.write(f"\n[runner] {runner_name}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=10)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--r-tip", type=float, default=0.05,
                   help="Refinement radius around tip (centroid distance, default 0.05)")
    p.add_argument("--n-passes", type=int, default=1,
                   help="Number of sequential refinement passes (1=4x, 2=16x density)")
    p.add_argument("--tip-x", type=float, default=0.0)
    p.add_argument("--tip-y", type=float, default=0.0)
    p.add_argument("--force-cpu", action="store_true")
    args = p.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

    here = Path(__file__).parent
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config

    # ── Disable all competing variants so S1 effect is isolated (sidecar rule 4) ──
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False
    config.adaptive_sampling_dict["enable"] = False    # C6 reweight off
    config.symmetry_prior = False

    # ── Fatigue + loading ──
    config.fatigue_dict["disp_max"] = args.umax
    config.fatigue_dict["n_cycles"] = args.n_cycles
    config.rebuild_disp_cyclic()

    # ── Enable Sidecar S1 ──
    config.sidecar_S1_dict["enable"] = True
    config.sidecar_S1_dict["tip_xy"] = (float(args.tip_x), float(args.tip_y))
    config.sidecar_S1_dict["r_tip_sample"] = float(args.r_tip)
    config.sidecar_S1_dict["n_refine_passes"] = int(args.n_passes)

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
        + f"_sidecarS1_rt{args.r_tip}_np{args.n_passes}"
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
    _rewrite_model_settings(config, "run_sidecar_S1_tip_oversample_umax.py")

    print("=" * 72)
    print("Sidecar S1 static-tip oversampling PIDL runner")
    print(f"  U_max     = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  tip_xy    = ({args.tip_x}, {args.tip_y})")
    print(f"  r_tip     = {args.r_tip} | n_passes = {args.n_passes}")
    print(f"  device    = {config.device}")
    print(f"  archive   = {dir_name}")
    print(f"  full path = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
