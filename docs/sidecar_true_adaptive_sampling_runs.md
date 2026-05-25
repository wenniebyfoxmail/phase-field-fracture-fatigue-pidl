# Sidecar Run Ledger: True Adaptive Sampling

**Status**: active ledger  
**Branch**: true adaptive sampling / batch composition sidecar  
**Owner**: Mac-PIDL  
**Rule**: append-only

## Purpose

This file is the run ledger for the true adaptive sampling sidecar. It records what was run, under which code/config state, and what the short verdict was.

This is not the place for long interpretation. Keep each entry compact. If a run changes the branch-level conclusion, record that in:

- `docs/sidecar_true_adaptive_sampling_decisions.md`

The canonical branch spec lives in:

- `docs/sidecar_true_adaptive_sampling.md`

## Required fields for each entry

- date
- run label
- code state or commit
- sampler type
- seed
- `Umax`
- horizon
- archive or output path
- key metrics
- short verdict

## Template

Copy this block for each completed run.

```md
## YYYY-MM-DD · <run label>

- **Code state**: <commit or local working state>
- **Sampler**: <S1-static-tip / S2-detached-score / S3-hybrid>
- **Seed**: <seed>
- **Umax**: <value>
- **Horizon**: <N=... or cycle range>
- **Config summary**: <only branch-defining knobs>
- **Output**: <archive path / log / figure path>
- **Key metrics**: <V4 / V7 / alpha_bar_max / process-zone metrics / N_f if available>
- **Verdict**: <one sentence>
```

## Entries

## 2026-05-12 · branch initialization

- **Code state**: documentation only; no implementation run yet
- **Sampler**: none
- **Seed**: none
- **Umax**: none
- **Horizon**: none
- **Config summary**: sidecar spec created; run ledger and decision memo initialized
- **Output**: `docs/sidecar_true_adaptive_sampling.md`
- **Key metrics**: none
- **Verdict**: branch opened as a documentation-first sidecar; first intended implementation target is `S1-static-tip`

## 2026-05-25 · baseline adaptive lambda-hist N100

- **Code state**: Taobo run under `phase-field-pidl-adapthist-af5a533`
- **Sampler**: baseline mesh/sampling plus adaptive `lambda_hist` loss-balancing diagnostic
- **Seed**: 1
- **Umax**: 0.12
- **Horizon**: N=100, stopped after fracture confirmation at cycle 92
- **Config summary**: baseline geometry, adaptive `lambda_hist` schedule enabled; not a pure sampling-only change because it modifies loss weights
- **Output**: `/mnt/data2/drtao/projects/phase-field-pidl-adapthist-af5a533/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_baseline_adapthist`
- **Key metrics**: fracture detected cycle 82, confirmed stop cycle 92; final `alpha_bar_max=12.0835`, `Kt=765.88`, crack tip `(0.5000,0.0288)`; late logs show `hist_grad=0` and `lambda_hist=1.0`
- **Verdict**: fractures, but adaptive `lambda_hist` did not become an active balancing mechanism and field-level alpha mismatch remains.

## 2026-05-25 · v4 add-only refinement adaptive lambda-hist N100

- **Code state**: Taobo run under `phase-field-pidl-adapthist-af5a533`
- **Sampler**: v4 add-only cumulative refinement plus adaptive `lambda_hist` loss-balancing diagnostic
- **Seed**: 1
- **Umax**: 0.12
- **Horizon**: N=100, stopped after fracture confirmation at cycle 90
- **Config summary**: cumulative tip-following add-only refinement (`rt=0.05`, `np=1`) with adaptive `lambda_hist`; this tests remesh/transport and loss-balance together rather than pure sampling alone
- **Output**: `/mnt/data2/drtao/projects/phase-field-pidl-adapthist-af5a533/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_sidecarS2_cumulative_tipfol_rt0.05_np1_adapthist_sched1`
- **Key metrics**: fracture detected cycle 80, confirmed stop cycle 90; final `alpha_bar_max=11.8556`, `Kt=916.21`, crack tip `(0.5000,0.0010)`; late logs show `hist_grad=0` and `lambda_hist=1.0`
- **Verdict**: v4 avoids repeated rebuild/transport as designed, but it still does not recover FEM-like field localization.

## 2026-05-25 · hard irreversibility N100 pair

- **Code state**: Taobo hard-irreversibility runs from commit family `6525a9f`
- **Sampler**: baseline and v4 add-only refinement; hard alpha floor `alpha = hist_alpha + (1 - hist_alpha) * sigmoid(raw_alpha)`
- **Seed**: 1
- **Umax**: 0.12
- **Horizon**: N=100, completed to cycle 99
- **Config summary**: compares hard irreversibility on baseline vs v4; this is a constraint-form diagnostic, not an adaptive-sampling-only change
- **Output**: baseline `/mnt/data2/drtao/projects/phase-field-pidl-hardirr-6525a9f-runs/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_baseline_hardirr`; v4 `/mnt/data2/drtao/projects/phase-field-pidl-hardirr-6525a9f-runs/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_sidecarS2_cumulative_tipfol_rt0.05_np1_hardirr`
- **Key metrics**: baseline final `alpha_bar_max=75.481`, `Kt=10.64`, `alpha_max@bdy=0`, no fracture; v4 final `alpha_bar_max=75.969`, `Kt=10.73`, `alpha_max@bdy=0`, no fracture
- **Verdict**: hard irreversibility no longer NaNs with the sigmoid floor, but it traps the field evolution near the notch while fatigue history grows very large; negative as a closure route.
