# Sync Sources: strict_femmesh_soft_hist0_alignment_20260529

Created: 2026-06-02.

## Run ID

`strict_femmesh_soft_hist0_alignment_20260529`

## Protocol

- Result-check protocol: `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/.codex/worktrees/pidl-state-timing-diagnostic/docs/pidl_experiment_result_check_protocol_2026-06-01.md`
- Alignment protocol: `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/docs/pidl_fem_alignment_protocol_2026-05-29.md`

## FEM Sources

- Primary FEM reference for this analysis: Request 21 n_step10 reference:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/request21_fem_nstep/source_handoff/_pidl_handoff_reverseBC_u12_soft_hist0_nstep10_2026-05-29`
- Secondary sensitivity reference: standard soft-hist0 reverseBC reference:
  `/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28`
- Invalid local mirrored standard FEM fields, do not use:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/source_handoff_soft_hist0/reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat`
  This file was checked on 2026-06-02 and is zero bytes.  Use the OneDrive
  standard source or the Request 21 source instead.

## PIDL Sources

- Taobo workspace:
  `/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529`
- Taobo strict FEM-mesh archive:
  `/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_femmesh_softHist0`
- Local sync folder:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/taobo_alignment_diag_20260529/femmesh_softHist0`
- Local event checkpoint pull:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/taobo_event_checkpoint_pull/femmesh_softHist0`

## Synced Into This Package

`0_sync/model/`:

- `model_settings.txt`
- `event_checkpoint_model_settings.txt`

`0_sync/logs/`:

- `femmesh_softHist0_u012_N100_seed1_retry.log`
- `femmesh_softHist0_u012_N100_seed1_retry.pid`

`0_sync/scalars/`:

- `alpha_bar_vs_cycle.npy`
- `x_tip_vs_cycle.npy`
- `Kt_vs_cycle.npy`
- `E_el_vs_cycle.npy`

`2_figures/` contains the copied analysis CSVs and figures used by
`1_analysis/result_check.md`.

## Files Not Duplicated

Large checkpoint and model files remain in the local event checkpoint pull and
on Taobo. Source paths are listed above.

## Evidence Maturity Note

This is a retrospective package for an experiment that predated the final
routine gradient-balance requirement. Field, event, timing, and energy evidence
are available; a dedicated gradient/loss-balance CSV for this exact run is not.
