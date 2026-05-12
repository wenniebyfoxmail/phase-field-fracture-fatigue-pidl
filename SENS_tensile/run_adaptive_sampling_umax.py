#!/usr/bin/env python3
"""run_adaptive_sampling_umax.py — Branch 2 C6 (Gao 2023 FI-PINN reweight variant).

Per-cycle reweights the per-element Deep Ritz loss by the residual proxy
**|E_el_e| + |E_d_e|** computed at the previous cycle's α field. Reweight
formula: w_e = (1 + β·(r_e / r_mean)^power) / mean(·)  ← mean-1 normalized.

Mechanism: forces NN to allocate more capacity to high-residual elements
(typically tip ROI) without modifying the ansatz architecture. Differs from
Direction 3 (`tip_weight_cfg`, ψ⁺-only proxy) by using both the elastic AND
the dissipation contribution to the Deep Ritz functional — the C6 hypothesis
is that ψ⁺ alone misses the damage-side residual contribution that becomes
dominant once d > 0.

Note on residual scope (2026-05-13 doc-correctness pass):
The proxy is the Deep Ritz residual |E_el|+|E_d|, NOT |E_el|+|E_d|+|E_hist|.
The irreversibility penalty E_hist is a regularizer layered on top of the
energy functional, not a physics residual; it is also numerically ≈ 0 by
the time the C6 block runs (hist_alpha was just refreshed at model_train.py:538).
See source/adaptive_sampling.py module docstring for the option-B variant
discussion if E_hist sensitivity ever matters.

Note on Direction 3 history:
The "Direction 3 negative result for N_f" claim from Apr-15 is suspect:
crack_tip_weights was never forwarded into fit() until commit `f33069e`
(2026-05-13 P0 fix). A clean re-test of Direction 3 with this fix is now
possible — separate task.

References:
  - Gao, Yan, Liang, Tan, Cheng 2023. FI-PINN. SIAM J. Sci. Comput. 45(4).
  - Hook map: upload code/references/branch2_hook_map.md (local-only)

Usage:
  python run_adaptive_sampling_umax.py 0.12 --n-cycles 10 --seed 1 --beta 2.0 --power 1.0
  python run_adaptive_sampling_umax.py 0.12 --n-cycles 50 --seed 1 --beta 3.0 --power 1.5

Output archive tag suffix: `_adaptiveS_b<β>_p<power>` (matches tipw pattern).

Compose-with notes:
  - Mutual exclusion with fatigue_dict.tip_weight_cfg (both write into
    crack_tip_weights). model_train.py raises ValueError if both enabled.
  - Composes cleanly with Fourier (`fourier_dict`) and exact-BC (`exact_bc_dict`).
    Add `--fourier-sigma` / `--exact-bc` flags here once a C6+Fourier or
    C4+C6 stack is desired (see run_exact_bc_fourier_umax.py for the pattern).
"""
import argparse
import os
import sys
from pathlib import Path


def _rewrite_model_settings(config, runner_name: str) -> None:
    fat = config.fatigue_dict
    asd = config.adaptive_sampling_dict
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
        f.write(f"\n--- adaptive_sampling (C6 FI-PINN reweight) ---")
        f.write(f"\nas_enable: {asd.get('enable')}")
        f.write(f"\nas_beta: {asd.get('beta')}")
        f.write(f"\nas_power: {asd.get('power')}")
        f.write(f"\nas_start_cycle: {asd.get('start_cycle')}")
        f.write(f"\nas_residual_source: {asd.get('residual_source')}")
        f.write(f"\n[runner] {runner_name}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("umax", type=float)
    p.add_argument("--n-cycles", type=int, default=10)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--beta", type=float, default=2.0,
                   help="Reweight magnitude (β=0 → uniform; β=1-5 typical)")
    p.add_argument("--power", type=float, default=1.0,
                   help="Residual-ratio exponent (1.0=linear, 2.0=quadratic emphasis)")
    p.add_argument("--start-cycle", type=int, default=1,
                   help="First cycle to apply reweighting (0=immediately after pretrain)")
    p.add_argument("--force-cpu", action="store_true")
    args = p.parse_args()

    if args.force_cpu:
        os.environ["CUDA_VISIBLE_DEVICES"] = ""

    sys.argv = ["main.py", "8", "400", str(args.seed), "TrainableReLU", "1.0"]

    here = Path(__file__).parent
    sys.path.insert(0, str(here))
    sys.path.insert(0, str(here.parent / "source"))

    import config

    # Disable competing architectural variants
    config.williams_dict["enable"] = False
    config.ansatz_dict["enable"] = False
    config.fatigue_dict["spatial_alpha_T"]["enable"] = False
    config.fatigue_dict["psi_hack"]["enable"] = False
    config.symmetry_prior = False
    # Mutual-exclusion: must not collide with Direction 3 tip_weight_cfg
    config.fatigue_dict["tip_weight_cfg"]["enable"] = False

    config.fatigue_dict["disp_max"] = args.umax
    config.fatigue_dict["n_cycles"] = args.n_cycles
    config.rebuild_disp_cyclic()

    # Enable C6 FI-PINN reweight
    config.adaptive_sampling_dict["enable"] = True
    config.adaptive_sampling_dict["beta"] = float(args.beta)
    config.adaptive_sampling_dict["power"] = float(args.power)
    config.adaptive_sampling_dict["start_cycle"] = int(args.start_cycle)
    config.adaptive_sampling_dict["residual_source"] = "full"

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
        + f"_adaptiveS_b{args.beta}_p{args.power}"
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
    _rewrite_model_settings(config, "run_adaptive_sampling_umax.py")

    print("=" * 72)
    print("C6 FI-PINN adaptive sampling (reweight variant) PIDL runner")
    print(f"  U_max     = {args.umax} | n_cycles = {args.n_cycles} | seed = {args.seed}")
    print(f"  β         = {args.beta} | power = {args.power} | start_cycle = {args.start_cycle}")
    print(f"  residual  = full (|E_el| + |E_d| + |E_hist| per element)")
    print(f"  device    = {config.device}")
    print(f"  archive   = {dir_name}")
    print(f"  full path = {config.model_path}")
    print("=" * 72)

    main_path = here / "main.py"
    exec(compile(main_path.read_text(encoding="utf-8"), str(main_path), "exec"),
         {"__name__": "__main__", "__file__": str(main_path)})


if __name__ == "__main__":
    main()
