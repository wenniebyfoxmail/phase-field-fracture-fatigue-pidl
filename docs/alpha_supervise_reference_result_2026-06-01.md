# Alpha-Supervision FEM-Reference Check, 2026-06-01

## Source

- PIDL archive: `/mnt/data2/drtao/pidl_archives/field_supervision_90dd3ad/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N20_R0.0_Umax0.12_femmesh_softHist0Nstep10_supalpha_K20_lam1_lossmse_lin_pretrain-off`
- FEM reference: `/mnt/data2/drtao/projects/pidl-field-supervision-90dd3ad/_fem_handoff/nstep10/reverseBC_u12_soft_hist0_nstep10_element_fields_c1_c69.mat`
- Local figure: `_analysis_fem_mechanism_20260528/figures/alpha_supervise_reference/alpha_supervise_fem_reference_residuals_c1_c2_c3_c10.png`
- Local metrics: `_analysis_fem_mechanism_20260528/figures/alpha_supervise_reference/alpha_supervise_fem_reference_residual_metrics.csv`

## Protocol Verdict

This is a useful diagnostic but not a mechanism fix. The run completed the
`N20` window without right-boundary fracture, but the crack advanced only to
about `x_tip=0.042` by PIDL index 19. The FEM-referenced residuals show that
supervising `alpha` keeps the phase-field damage itself close in the near-tip
crop, while `alpha_bar` and the elastic drivers still drift early.

Important indexing caveat: with the current PIDL loop, `N20` logs indices
`0..19`, so this run supervised FEM cycles `c1..c19`; it did not reach a true
PIDL index 20 export.

## Key Early-Cycle Findings

At `c1`, FEM reference has `alpha_bar_max=0.2398`, while PIDL has
`alpha_bar_max=0.7928`. By `c10`, FEM has `alpha_bar_max=1.7507`, while PIDL has
`alpha_bar_max=3.1664`. Thus the fatigue/history channel is already hotter than
FEM even when `alpha` itself is supervised.

For the raw elastic driver, the near-tip residual is a log ratio with FEM as the
denominator. At `c1`, the mean residual is about `+1.33` decades, and by `c10`
it is about `+2.18` decades. This says the PIDL raw driver is much larger than
the FEM reference in the near-tip crop under this supervised-alpha branch.

The routine gradient gate remains consistent with previous diagnostics: actual
`E_el` and `E_d` contributions are comparable, `E_hist` must be inspected before
history refresh, and the alpha branch receives much larger updates than the
uv/displacement branch.

## Interpretation

Alpha supervision suppresses the spurious right-boundary failure, but it does
not align the coupled mechanism. The remaining gap is not just "can the network
draw alpha"; it is in the coupled history-driver-displacement timing and
relaxation loop.
