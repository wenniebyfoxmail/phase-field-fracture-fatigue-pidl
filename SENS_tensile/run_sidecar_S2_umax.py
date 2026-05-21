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

State transport across cycle swaps (v3.2 design, 2026-05-15):
  - hist_fat / psi_plus_prev (per-ELEMENT cumulative): nearest-element
    transport between consecutive refined meshes (sidecar_sampling.
    nearest_element_transport).
  - hist_alpha (per-NODE irreversibility floor): L2 edge-lineage transport
    (sidecar_sampling.edge_lineage_transport, conservative max reduction on
    midpoint endpoints) PLUS a NN-prediction floor — transport must never be
    weaker than the NN's current α (the trained-state lower bound).
  - score (S2b only, per-ELEMENT density): density-aware aggregate to original
    mesh's element coordinates, then top-K mask for next cycle's refinement.
Each cycle's refinement is one-step from the canonical reference mesh — mesh
size stays bounded.

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


def _resolve_archive_dir(here: Path, dir_name: str) -> Path:
    """Resolve archive location, optionally redirecting the real dir to a big disk.

    If PIDL_ARCHIVE_DIR is set, the archive lives at
    `$PIDL_ARCHIVE_DIR/<dir_name>` and `here/<dir_name>` is a symlink to it.
    Existing real directories under `here` are left untouched so old runs remain
    auditable and resumeable until they are explicitly moved.
    """
    archive_link = here / dir_name
    archive_root = os.environ.get("PIDL_ARCHIVE_DIR")
    if not archive_root:
        archive_link.mkdir(parents=True, exist_ok=True)
        return archive_link

    archive_real = Path(archive_root) / dir_name
    if archive_link.exists() and not archive_link.is_symlink():
        return archive_link

    archive_real.mkdir(parents=True, exist_ok=True)
    if archive_link.is_symlink():
        if archive_link.resolve() != archive_real.resolve():
            archive_link.unlink()
            archive_link.symlink_to(archive_real, target_is_directory=True)
    else:
        archive_link.symlink_to(archive_real, target_is_directory=True)
    return archive_link


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
        alh = fat.get('adaptive_lambda_hist', {})
        f.write(f"\nadaptive_lambda_hist_enable: {alh.get('enable', False)}")
        f.write(f"\nadaptive_lambda_hist_initial: {alh.get('initial', 1.0)}")
        f.write(f"\nadaptive_lambda_hist_min: {alh.get('min', 1e-3)}")
        f.write(f"\nadaptive_lambda_hist_max: {alh.get('max', 1.0)}")
        f.write(f"\nadaptive_lambda_hist_smooth: {alh.get('smooth', 1.0)}")
        f.write(f"\n--- sidecar S2 (adaptive refinement) ---")
        f.write(f"\nS2_enable: {sdct.get('enable')}")
        f.write(f"\nS2_mode: {sdct.get('mode')}")
        f.write(f"\nS2_refine_mode: {sdct.get('refine_mode', 'cumulative')}")
        f.write(f"\nS2_tip_xy: {sdct.get('tip_xy')}")
        f.write(f"\nS2_r_tip_sample: {sdct.get('r_tip_sample')}")
        f.write(f"\nS2_n_refine_passes: {sdct.get('n_refine_passes')}")
        f.write(f"\nS2_hysteresis_fraction: {sdct.get('hysteresis_fraction')}")
        f.write(f"\nS2_target_fraction: {sdct.get('target_fraction')}")
        f.write(f"\nS2_min_count: {sdct.get('min_count')}")
        f.write(f"\nS2_include_root_tip: {sdct.get('include_root_tip')}")
        f.write(f"\nS2_root_tip_xy: {sdct.get('root_tip_xy')}")
        f.write(f"\nS2_r_root_sample: {sdct.get('r_root_sample')}")
        reeq = sdct.get('post_refine_reeq', {})
        f.write(f"\nS2_post_refine_reeq_enable: {reeq.get('enable', False)}")
        f.write(f"\nS2_post_refine_reeq_optimizer: {reeq.get('optimizer', 'RPROP')}")
        f.write(f"\nS2_post_refine_reeq_n_epochs: {reeq.get('n_epochs', 3000)}")
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
    p.add_argument("--hysteresis-fraction", type=float, default=1.0,
                   help="Skip re-refinement when |Δtip|_L1 < this × r_tip_sample (default 1.0)")
    p.add_argument("--refine-mode", choices=["cumulative", "rebuild"], default="cumulative",
                   help="cumulative=v4 add-only incremental refine (no diffusion); "
                        "rebuild=legacy v2/v3.2 rebuild-from-original. Default cumulative.")
    p.add_argument("--plot-every", type=int, default=None,
                   help="Override fatigue_dict.plot_every_n_cycles (default config=20). "
                        "Set 1 for full per-cycle alpha snapshots (diagnostic plots).")
    p.add_argument("--fracture-confirm-cycles", type=int, default=None,
                   help="Override fatigue_dict.fracture_confirm_cycles for this run.")
    p.add_argument("--tip-x0", type=float, default=0.0,
                   help="Initial tip x (used for cycle 0 in S2a if no tip history yet)")
    p.add_argument("--tip-y0", type=float, default=0.0)
    p.add_argument("--include-root-tip", action="store_true",
                   help="S2a: refine the union of the current tip zone and a fixed root zone.")
    p.add_argument("--root-tip-x", type=float, default=0.0,
                   help="Fixed root-zone x coordinate for --include-root-tip.")
    p.add_argument("--root-tip-y", type=float, default=0.0,
                   help="Fixed root-zone y coordinate for --include-root-tip.")
    p.add_argument("--r-root", type=float, default=None,
                   help="Root refinement radius for --include-root-tip (default: --r-tip).")
    p.add_argument("--tag-suffix", type=str, default="",
                   help="Optional archive suffix for diagnostic reruns, e.g. diag_hf.")
    p.add_argument("--adaptive-lambda-hist", action="store_true",
                   help="Enable Wang-style REFINE-time adaptive weighting for E_hist.")
    p.add_argument("--lambda-hist-min", type=float, default=1e-3,
                   help="Lower clip for adaptive lambda_hist.")
    p.add_argument("--lambda-hist-max", type=float, default=1.0,
                   help="Upper clip for adaptive lambda_hist.")
    p.add_argument("--lambda-hist-smooth", type=float, default=1.0,
                   help="Moving-average update fraction for lambda_hist (1.0 = no smoothing).")
    p.add_argument("--lambda-hist-initial", type=float, default=1.0,
                   help="Initial lambda_hist before the first adaptive update.")
    p.add_argument("--post-refine-reeq", action="store_true",
                   help="After each S2 REFINE, run an extra fit before fatigue-history update.")
    p.add_argument("--post-refine-reeq-epochs", type=int, default=3000,
                   help="Max epochs for the post-REFINE re-equilibration fit.")
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
    config.sidecar_S2_dict["refine_mode"] = args.refine_mode
    config.sidecar_S2_dict["include_root_tip"] = bool(args.include_root_tip)
    config.sidecar_S2_dict["root_tip_xy"] = (float(args.root_tip_x), float(args.root_tip_y))
    config.sidecar_S2_dict["r_root_sample"] = (
        float(args.r_root) if args.r_root is not None else float(args.r_tip)
    )
    config.sidecar_S2_dict["post_refine_reeq"] = {
        "enable": bool(args.post_refine_reeq),
        "optimizer": "RPROP",
        "n_epochs": int(args.post_refine_reeq_epochs),
    }
    if args.plot_every is not None:
        config.fatigue_dict["plot_every_n_cycles"] = int(args.plot_every)
    if args.fracture_confirm_cycles is not None:
        config.fatigue_dict["fracture_confirm_cycles"] = int(args.fracture_confirm_cycles)
    config.fatigue_dict["adaptive_lambda_hist"] = {
        "enable": bool(args.adaptive_lambda_hist),
        "initial": float(args.lambda_hist_initial),
        "min": float(args.lambda_hist_min),
        "max": float(args.lambda_hist_max),
        "smooth": float(args.lambda_hist_smooth),
        "eps": 1e-30,
    }

    fat = config.fatigue_dict
    fatigue_tag = (
        f"_fatigue_on_{fat['accum_type']}_{fat['degrad_type'][:3]}"
        f"_aT{fat['alpha_T']}_N{fat['n_cycles']}_R{fat['R_ratio']}"
        f"_Umax{fat['disp_max']}"
    )
    if args.mode == "tip_following":
        S2_suffix = (
            f"_sidecarS2_{args.refine_mode}_{_mode_short(args.mode)}"
            f"_rt{args.r_tip}_np{args.n_passes}"
        )
        if args.include_root_tip:
            S2_suffix += f"_rootrt{config.sidecar_S2_dict['r_root_sample']}"
    else:
        S2_suffix = (
            f"_sidecarS2_{args.refine_mode}_{_mode_short(args.mode)}"
            f"_tf{args.target_fraction}_np{args.n_passes}"
        )
    if args.tag_suffix.strip():
        _tag = args.tag_suffix.strip().replace(" ", "_")
        if not _tag.startswith("_"):
            _tag = "_" + _tag
        S2_suffix += _tag
    elif args.adaptive_lambda_hist:
        S2_suffix += "_adapthist"
    if args.post_refine_reeq:
        S2_suffix += f"_reeq{args.post_refine_reeq_epochs}"
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
    _rewrite_model_settings(config, "run_sidecar_S2_umax.py")

    print("=" * 72)
    print(f"Sidecar S2 adaptive refinement PIDL runner ({args.mode})")
    print(f"  U_max     = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  mode      = {args.mode}")
    if args.mode == "tip_following":
        print(f"  r_tip     = {args.r_tip} | n_passes = {args.n_passes}")
        print(f"  tip0      = ({args.tip_x0}, {args.tip_y0})  (first-cycle fallback)")
        if args.include_root_tip:
            print(
                f"  root union= ({args.root_tip_x}, {args.root_tip_y}) | "
                f"r_root = {config.sidecar_S2_dict['r_root_sample']}"
            )
    else:
        print(f"  target_fraction = {args.target_fraction} | r_tip (cycle-0 fallback) = {args.r_tip}")
        print(f"  min_count = {args.min_count} | n_passes = {args.n_passes}")
    if args.adaptive_lambda_hist:
        print(
            f"  λ_hist   = adaptive | initial={args.lambda_hist_initial} | "
            f"clip=[{args.lambda_hist_min}, {args.lambda_hist_max}] | "
            f"smooth={args.lambda_hist_smooth}"
        )
    else:
        print("  λ_hist   = 1.0 (fixed)")
    if args.post_refine_reeq:
        print(f"  post-REFINE reeq = RPROP max_epochs={args.post_refine_reeq_epochs}")
    print(f"  device    = {config.device}")
    print(f"  archive   = {dir_name}")
    print(f"  full path = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
