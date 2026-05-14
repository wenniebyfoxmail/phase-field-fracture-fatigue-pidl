#!/usr/bin/env python3
"""run_sidecar_S2_umax.py — Sidecar S2 runner (adaptive refinement).

Spec: docs/sidecar_true_adaptive_sampling.md (Stage S2).

Two modes (selected via --mode):
  - "tip_following" (S2a): each cycle, re-refine around the CURRENT crack-tip
    x_tip (read from the running tip history). Pure geometry, no score.
  - "score_driven"  (S2b): each cycle, re-refine the top `target_fraction` of
    elements by detached Deep Ritz residual |E_el_e|+|E_d_e| computed at the
    end of the previous cycle. Score is detached so it acts only as a
    sampling-density signal, NOT as a loss reweight (sidecar Rule 1).

In both modes, hist_fat / psi_plus_prev / score live in the ORIGINAL mesh's
element coordinates throughout the run via the expand/aggregate transport
(see `source/sidecar_sampling.py: aggregate_to_original`). Each cycle's
refinement is a one-step operation from the canonical reference mesh — no
compounding interpolation drift.

Mutual exclusion: must not be enabled with sidecar_S1, tip_weight_cfg,
adaptive_sampling_dict (C6). Runner enforces.

Differences vs run_sidecar_S1_tip_oversample_umax.py:
  - S1 refines ONCE before training and keeps the mesh fixed.
  - S2 re-refines BEFORE EACH CYCLE based on the current tip / score, so
    the dense region tracks the active crack.
Differences vs run_adaptive_sampling_umax.py (C6 reweight):
  - C6 reweights the per-element loss inside log(sum E).
  - S2 changes only collocation density. Loss formula untouched.

Usage:
  python run_sidecar_S2_umax.py 0.12 --n-cycles 5 --seed 1 --mode tip_following
  python run_sidecar_S2_umax.py 0.12 --n-cycles 50 --seed 1 --mode score_driven --target-fraction 0.07

Output archive tag suffix: `_sidecarS2_<mode-short>_rt<r>_tf<target_fraction>`
"""
import argparse
import os
import sys
from pathlib import Path


def _mode_short(mode: str) -> str:
    return {"tip_following": "tipfol", "score_driven": "scored"}.get(mode, mode)


def _rewrite_model_settings(config, runner_name: str) -> None:
    fat = config.fatigue_dict
    sdct = config.sidecar_S2_dict
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
        f.write(f"\n--- sidecar S2 (adaptive refinement) ---")
        f.write(f"\nS2_enable: {sdct.get('enable')}")
        f.write(f"\nS2_mode: {sdct.get('mode')}")
        f.write(f"\nS2_tip_xy: {sdct.get('tip_xy')}")
        f.write(f"\nS2_r_tip_sample: {sdct.get('r_tip_sample')}")
        f.write(f"\nS2_n_refine_passes: {sdct.get('n_refine_passes')}")
        f.write(f"\nS2_target_fraction: {sdct.get('target_fraction')}")
        f.write(f"\nS2_min_count: {sdct.get('min_count')}")
        f.write(f"\n[runner] {runner_name}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=10)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--mode", choices=["tip_following", "score_driven"], default="tip_following")
    p.add_argument("--r-tip", type=float, default=0.05,
                   help="Refinement radius (S2a; fallback for S2b cycle 0)")
    p.add_argument("--n-passes", type=int, default=1)
    p.add_argument("--target-fraction", type=float, default=0.07,
                   help="S2b: fraction of elements to refine each cycle")
    p.add_argument("--min-count", type=int, default=50,
                   help="S2b: floor on n_marked elements (avoid degenerate masks)")
    p.add_argument("--hysteresis-fraction", type=float, default=0.25,
                   help="Skip re-refinement when |Δtip|_L1 < this × r_tip_sample (default 0.25)")
    p.add_argument("--plot-every", type=int, default=None,
                   help="Override fatigue_dict.plot_every_n_cycles (default config=20). "
                        "Set 1 for full per-cycle alpha snapshots (diagnostic plots).")
    p.add_argument("--tip-x0", type=float, default=0.0,
                   help="Initial tip x (used for cycle 0 in S2a if no tip history yet)")
    p.add_argument("--tip-y0", type=float, default=0.0)
    p.add_argument("--force-cpu", action="store_true")
    args = p.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

    here = Path(__file__).parent
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config

    # ── Disable all competing variants (sidecar Rule 4) ──
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fourier_dict["enable"] = False
    config.exact_bc_dict["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False
    config.adaptive_sampling_dict["enable"] = False    # C6 off
    config.sidecar_S1_dict["enable"] = False           # mutex with S2
    config.symmetry_prior = False

    # Fatigue + loading
    config.fatigue_dict["disp_max"] = args.umax
    config.fatigue_dict["n_cycles"] = args.n_cycles
    config.rebuild_disp_cyclic()

    # Enable sidecar S2
    config.sidecar_S2_dict["enable"] = True
    config.sidecar_S2_dict["mode"] = args.mode
    config.sidecar_S2_dict["tip_xy"] = (float(args.tip_x0), float(args.tip_y0))
    config.sidecar_S2_dict["r_tip_sample"] = float(args.r_tip)
    config.sidecar_S2_dict["n_refine_passes"] = int(args.n_passes)
    config.sidecar_S2_dict["target_fraction"] = float(args.target_fraction)
    config.sidecar_S2_dict["min_count"] = int(args.min_count)
    config.sidecar_S2_dict["hysteresis_fraction"] = float(args.hysteresis_fraction)
    if args.plot_every is not None:
        config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    if args.mode == "tip_following":
        S2_suffix = f"_sidecarS2_{_mode_short(args.mode)}_rt{args.r_tip}_np{args.n_passes}"
    else:
        S2_suffix = f"_sidecarS2_{_mode_short(args.mode)}_tf{args.target_fraction}_np{args.n_passes}"
    dir_name = (
        "hl_" + str(config.network_dict["hidden_layers"])
        + "_Neurons_" + str(config.network_dict["neurons"])
        + "_activation_" + config.network_dict["activation"]
        + "_coeff_" + str(config.network_dict["init_coeff"])
        + "_Seed_" + str(config.network_dict["seed"])
        + "_PFFmodel_" + str(config.PFF_model_dict["PFF_model"])
        + "_gradient_" + str(config.numr_dict["gradient_type"])
        + fatigue_tag
        + S2_suffix
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
    _rewrite_model_settings(config, "run_sidecar_S2_umax.py")

    print("=" * 72)
    print(f"Sidecar S2 adaptive refinement PIDL runner ({args.mode})")
    print(f"  U_max     = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  mode      = {args.mode}")
    if args.mode == "tip_following":
        print(f"  r_tip     = {args.r_tip} | n_passes = {args.n_passes}")
        print(f"  tip0      = ({args.tip_x0}, {args.tip_y0})  (first-cycle fallback)")
    else:
        print(f"  target_fraction = {args.target_fraction} | r_tip (cycle-0 fallback) = {args.r_tip}")
        print(f"  min_count = {args.min_count} | n_passes = {args.n_passes}")
    print(f"  device    = {config.device}")
    print(f"  archive   = {dir_name}")
    print(f"  full path = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
