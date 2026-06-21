# Taobo Tiered PIDL Comparison Plan

Date: 2026-05-29

Status: Historical Taobo run-tiering and rescore plan. Use this to understand
old-run inventory and ranking decisions; do not use it as the current
case-level evidence protocol.

## Purpose

This manifest prevents old Taobo runs from being compared as if they all
shared the current soft-hist0 FEM/PIDL protocol.  Each run gets a tier
before it enters a scoreboard.

## Tier Rule

- Tier 0: strict benchmark.  Use for absolute FEM-vs-PIDL comparison.
- Tier 1: mechanism diagnostic.  Use for ranking ideas; rerun winners under Tier 0.
- Tier 2: legacy architecture evidence.  Use for idea mining only.
- Tier 3: out of current benchmark.  Exclude unless doing a different sensitivity.

## Inventory Counts

- Tier 0 - strict benchmark: 2
- Tier 1 - controlled alignment diagnostic: 2
- Tier 1 - mechanism diagnostic: 74
- Tier 2 - legacy architecture evidence: 54
- Tier 3 - bookkeeping: 4
- Tier 3 - out of current benchmark: 20

## Family Counts

- Tier 0 - strict benchmark / FEM-mesh / soft-hist0 alignment: 1
- Tier 0 - strict benchmark / irreversibility tolerance: 1
- Tier 1 - controlled alignment diagnostic / explicit cycle/substep timing: 1
- Tier 1 - controlled alignment diagnostic / irreversibility tolerance: 1
- Tier 1 - mechanism diagnostic / FEM-mesh / soft-hist0 alignment: 3
- Tier 1 - mechanism diagnostic / adaptive lambda_hist: 1
- Tier 1 - mechanism diagnostic / branch restart: 3
- Tier 1 - mechanism diagnostic / hard irreversibility: 4
- Tier 1 - mechanism diagnostic / patch strength: 1
- Tier 1 - mechanism diagnostic / sidecar / tip-follow sampling: 38
- Tier 1 - mechanism diagnostic / tip-local patch: 19
- Tier 1 - mechanism diagnostic / wider local patch: 5
- Tier 2 - legacy architecture evidence / Fourier representation: 8
- Tier 2 - legacy architecture evidence / baseline: 3
- Tier 2 - legacy architecture evidence / enriched ansatz: 1
- Tier 2 - legacy architecture evidence / exact boundary condition: 1
- Tier 2 - legacy architecture evidence / explicit cycle/substep timing: 1
- Tier 2 - legacy architecture evidence / irreversibility tolerance: 2
- Tier 2 - legacy architecture evidence / oracle zone: 2
- Tier 2 - legacy architecture evidence / other: 20
- Tier 2 - legacy architecture evidence / psi/history hack: 1
- Tier 2 - legacy architecture evidence / symmetry / side-traction: 15
- Tier 3 - bookkeeping / FEM-mesh / soft-hist0 alignment: 2
- Tier 3 - bookkeeping / explicit cycle/substep timing: 1
- Tier 3 - bookkeeping / irreversibility tolerance: 1
- Tier 3 - out of current benchmark / Fourier representation: 2
- Tier 3 - out of current benchmark / baseline: 12
- Tier 3 - out of current benchmark / exact boundary condition: 3
- Tier 3 - out of current benchmark / oracle zone: 2
- Tier 3 - out of current benchmark / other: 1

## First Rescore Queue

| Tier | Family | Status | Max saved index | Action | Remote path |
|---|---|---:|---:|---|---|
| Tier 0 - strict benchmark | FEM-mesh / soft-hist0 alignment | complete | 85 | rescore with FEM c -> PIDL j=c-1 on common probes | `/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_femmesh_softHist0` |
| Tier 0 - strict benchmark | irreversibility tolerance | complete | 68 | rescore with FEM c -> PIDL j=c-1 on common probes | `/mnt/data2/drtao/projects/phase-field-pidl-inverse-alphaT-5eb7a73/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N69_R0.0_Umax0.12_reverseBC_softHist0_forward_tolir0.001` |
| Tier 1 - mechanism diagnostic | adaptive lambda_hist | complete | 92 | rescore with j0 protocol, then rerun winners under Tier 0 settings | `/mnt/data2/drtao/projects/phase-field-pidl-adapthist-af5a533/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_baseline_adapthist` |
| Tier 1 - controlled alignment diagnostic | explicit cycle/substep timing | complete | 199 | rescore with j0 protocol and verify initial crack, mesh, and history timing before promoting | `/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_Ncyc40_Nstep200_R0.0_Umax0.12_explicitCycle_0-0.5-1-0.5-0` |
| Tier 1 - mechanism diagnostic | hard irreversibility | complete | 99 | rescore with j0 protocol, then rerun winners under Tier 0 settings | `/mnt/data2/drtao/projects/phase-field-pidl-hardirr-6525a9f-runs/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_baseline_hardirr` |
| Tier 1 - controlled alignment diagnostic | irreversibility tolerance | complete | 95 | rescore with j0 protocol and verify initial crack, mesh, and history timing before promoting | `/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_tolir0.001_baseline` |
| Tier 1 - mechanism diagnostic | sidecar / tip-follow sampling | complete | 99 | rescore with j0 protocol, then rerun winners under Tier 0 settings | `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_sidecarS2_tipfol_rt0.05_np1_adapthist` |
| Tier 1 - mechanism diagnostic | sidecar / tip-follow sampling | complete | 99 | rescore with j0 protocol, then rerun winners under Tier 0 settings | `/mnt/data2/drtao/projects/phase-field-pidl-hardirr-6525a9f-runs/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_sidecarS2_cumulative_tipfol_rt0.05_np1_hardirr` |
| Tier 1 - mechanism diagnostic | sidecar / tip-follow sampling | complete | 93 | rescore with j0 protocol, then rerun winners under Tier 0 settings | `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_2_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_sidecarS1_rt0.05_np1` |
| Tier 1 - mechanism diagnostic | sidecar / tip-follow sampling | complete | 92 | rescore with j0 protocol, then rerun winners under Tier 0 settings | `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_3_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_sidecarS1_rt0.05_np1` |
| Tier 1 - mechanism diagnostic | sidecar / tip-follow sampling | complete | 90 | rescore with j0 protocol, then rerun winners under Tier 0 settings | `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12_sidecarS1_rt0.05_np1` |
| Tier 1 - mechanism diagnostic | sidecar / tip-follow sampling | complete | 90 | rescore with j0 protocol, then rerun winners under Tier 0 settings | `/mnt/data2/drtao/projects/phase-field-pidl-adapthist-af5a533/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_sidecarS2_cumulative_tipfol_rt0.05_np1_adapthist_sched1` |
| Tier 1 - mechanism diagnostic | sidecar / tip-follow sampling | complete | 88 | rescore with j0 protocol, then rerun winners under Tier 0 settings | `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_sidecarS2_tipfol_rt0.05_np1_hyst1_resume` |
| Tier 1 - mechanism diagnostic | sidecar / tip-follow sampling | complete | 87 | rescore with j0 protocol, then rerun winners under Tier 0 settings | `/mnt/data2/drtao/projects/phase-field-pidl/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_sidecarS2_tipfol_rt0.05_np1` |
| Tier 1 - mechanism diagnostic | sidecar / tip-follow sampling | complete | 80 | rescore with j0 protocol, then rerun winners under Tier 0 settings | `/mnt/data2/drtao/projects/phase-field-pidl-adapthist-af5a533/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N82_R0.0_Umax0.12_sidecarS2_cumulative_tipfol_rt0.05_np1_diag_batch_c81_adapthist` |
| Tier 1 - mechanism diagnostic | sidecar / tip-follow sampling | complete | 80 | rescore with j0 protocol, then rerun winners under Tier 0 settings | `/mnt/data2/drtao/projects/phase-field-pidl-adapthist-af5a533/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N82_R0.0_Umax0.12_sidecarS2_cumulative_tipfol_rt0.05_np1_diag_batch_c81_fixed` |
| Tier 1 - mechanism diagnostic | sidecar / tip-follow sampling | complete | 76 | rescore with j0 protocol, then rerun winners under Tier 0 settings | `/mnt/data2/drtao/projects/phase-field-pidl-adapthist-af5a533/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N78_R0.0_Umax0.12_sidecarS2_cumulative_tipfol_rt0.05_np1_diag_batch_c77_adapthist` |
| Tier 1 - mechanism diagnostic | sidecar / tip-follow sampling | complete | 76 | rescore with j0 protocol, then rerun winners under Tier 0 settings | `/mnt/data2/drtao/projects/phase-field-pidl-adapthist-af5a533/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N78_R0.0_Umax0.12_sidecarS2_cumulative_tipfol_rt0.05_np1_diag_batch_c77_fixed` |

## Comparison Protocol

1. Score Tier 0 first with `FEM c -> PIDL j=c-1`, common probes, and
   separate absolute versus incremental `E_d`.
2. Score Tier 1 with the same posthoc metrics, but label the output as
   mechanism ranking under old settings.
3. Promote only Tier 1 winners into new strict soft-hist0/FEM-mesh reruns.
4. Keep Tier 2 as evidence for what is worth rebuilding, not as final
   FEM/PIDL evidence.

Primary gates: c20/c40/c69 `damage`, `alpha_bar`, active `psi_plus`,
p99/p999, near-tip integrals, process-zone width, and `Delta E_d` from c1.

## Generated Manifest

CSV: `_analysis_fem_mechanism_20260528/taobo_tier_manifest_20260529.csv`

## Immediate Rescore Result

The strict FEM-mesh soft-hist0 benchmark and the Taobo `tol_ir=0.001`
forward archive have now both been rescored with the current `FEM c -> PIDL
j=c-1` protocol.  The `reverseBC_softHist0_forward_tolir0.001` archive and
the controlled `tolir0.001_baseline` archive are checkpoint-identical for the
sampled states, so they should not be counted as two independent methods.

| Method | Cycle | damage tip2 | alpha_bar tip2 | alpha_bar p99 | active psi tip2 | active psi p99 |
|---|---:|---:|---:|---:|---:|---:|
| FEM-mesh softHist0 | 1 | 1.008 | 0.985 | 0.421 | 1.013 | 1.053 |
| FEM-mesh softHist0 | 20 | 0.996 | 0.946 | 0.928 | 1.150 | 1.018 |
| FEM-mesh softHist0 | 40 | 1.002 | 0.792 | 0.430 | 0.245 | 0.994 |
| FEM-mesh softHist0 | 69 | 1.012 | 0.466 | 0.191 | 0.029 | 1.374 |
| softHist0/tol_ir=0.001 | 1 | 1.028 | 1.011 | 0.511 | 1.038 | 1.129 |
| softHist0/tol_ir=0.001 | 20 | 1.118 | 1.057 | 1.026 | 1.692 | 1.009 |
| softHist0/tol_ir=0.001 | 40 | 1.272 | 0.883 | 0.476 | 0.188 | 0.967 |
| softHist0/tol_ir=0.001 | 69 | 1.464 | 0.516 | 0.216 | 0.033 | 1.312 |

Reading: the tolerance change does not close the late-cycle mechanism gap.
It increases near-tip damage relative to FEM, but the late near-tip fatigue
history and active degraded driver are still far below FEM.  Therefore
`tol_ir=0.001` is not a field-mechanism fix by itself.
