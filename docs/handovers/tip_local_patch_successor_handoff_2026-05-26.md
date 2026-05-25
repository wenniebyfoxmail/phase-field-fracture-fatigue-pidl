# Tip-Local Patch Successor Handoff - 2026-05-26

## Code State

- Local worktree: `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/.claude/worktrees/exp/tip-local-net`
- Branch: `codex/exp/tip-local-net`
- Latest pushed commit: `229f5a0` (`Allow tip-local checkpoint mask compatibility`)
- Taobo code dir: `/mnt/data2/drtao/projects/phase-field-pidl-tip-local-net-68871eb`

The runner `SENS_tensile/run_tip_local_net_S1_umax.py` now supports:

```bash
--tip-arch mlp|fourier|siren
--output-mode all|uv|alpha
```

The global branch remains the baseline MLP. Only the compact crack-tip local correction head changes. Current production uses moving window (`follow_tip=True`) and `output_mode=all`.

## Important Distinction

Do not mix these two MLP cases:

- Static-window MLP N100 finished earlier in archive ending `_tipLocal_rt0.05_wr0.05_h3_n80` (no `_followTip`). It fractured at cycle 83 and confirmed stop at cycle 93, final `alpha_bar_max≈10.993`, `Kt≈989.6`.
- Follow-tip MLP N100 is archive ending `_tipLocal_rt0.05_wr0.05_h3_n80_followTip`. This is the fair comparator for Fourier/SIREN follow-tip. It was only N20-complete, then restarted from cycle 20 after commit `229f5a0`.

The `output_mask` issue was checkpoint compatibility only: old MLP checkpoints predate the new nontrainable channel-mask buffer. Loading now permits that single missing buffer and uses the code default `[1, 1, 1]` for `output_mode=all`.

## Taobo Runs

Last checked: 2026-05-26 05:05 CST.

| Method | PID | GPU | Status |
|---|---:|---:|---|
| Fourier follow-tip N100 | `4094754` | 3 | fracture detected c80; waiting confirmed stop |
| SIREN follow-tip N100 | `4094759` | 5 | fracture detected c78; waiting confirmed stop |
| MLP follow-tip N100 | `274630` | 4 | restarted from c20; running |

Logs:

```text
/mnt/data2/drtao/projects/phase-field-pidl-tip-local-net-68871eb/SENS_tensile/run_logs/tip_local_followTip_S1_fourier_umax0.12_N100_seed1_resume_20260526_010514.log
/mnt/data2/drtao/projects/phase-field-pidl-tip-local-net-68871eb/SENS_tensile/run_logs/tip_local_followTip_S1_siren_umax0.12_N100_seed1_resume_20260526_010514.log
/mnt/data2/drtao/projects/phase-field-pidl-tip-local-net-68871eb/SENS_tensile/run_logs/tip_local_followTip_S1_mlp_umax0.12_N100_seed1_resume_compat_20260526_045809.log
```

Archives:

```text
/mnt/data2/drtao/pidl_archives/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_sidecarS1_rt0.05_np1_tipLocal_rt0.05_wr0.05_h3_n80_archfourier_followTip
/mnt/data2/drtao/pidl_archives/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_sidecarS1_rt0.05_np1_tipLocal_rt0.05_wr0.05_h3_n80_archsiren_followTip
/mnt/data2/drtao/pidl_archives/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_sidecarS1_rt0.05_np1_tipLocal_rt0.05_wr0.05_h3_n80_followTip
```

## Latest Observed Metrics

Fourier follow-tip:

- Fracture detected at cycle 80: `alpha_bdy=1.0015`, 25 boundary nodes.
- Last observed near cycle 89 start: `alpha_bar_max≈8.2885`, `Kt≈821.9`.
- N20 diagnostic at c19: `local_corr_over_total≈0.0357`, `tip_grad_over_global≈5.48e-4`.

SIREN follow-tip:

- Fracture detected at cycle 78: `alpha_bdy=1.0007`, 27 boundary nodes.
- Last observed near cycle 82 start: `alpha_bar_max≈7.1036`, `Kt≈655.5`.
- N20 diagnostic at c19: `local_corr_over_total≈0.0603`, `tip_grad_over_global≈9.69e-3`.

MLP follow-tip:

- N20 completed earlier: c19 `alpha_bar_max=4.4916`, crack length `0.0585`.
- N100 restart after compatibility fix: last observed c22 start.

## Next Steps

1. Recheck logs until Fourier/SIREN confirmed stop and MLP follow-tip reaches fracture/confirmation.
2. Extract final stop cycle, `alpha_bar_max`, `Kt`, crack tip, and `tip_local_diagnostics.csv`.
3. Render alpha fields for key cycles: before fracture, detection, confirmed stop.
4. Compare MLP follow-tip vs Fourier follow-tip vs SIREN follow-tip, and keep static-window MLP as a separate historical baseline.
