---
storyline_id: S09
experiment_id: S09-E013
protocol_revision: v2-local-support-ranking-two-arm
status: revised-code-awaiting-focused-rereview
primary_storyline: S09
related_experiments: [S09-E010, S09-E011, S09-E012]
---

# Localisation-aware ranking from the frozen B25 state

## Question

On the same exposed 16-cycle synthetic development trajectory, can a pairwise
ranking loss applied to **target-support minus background predicted growth**
repair more of the eight wrong local contrasts than an exact replay of the
E011 global-amplitude ranking loss, under the same 500 updates and optimizer
state?

The two arms are `G25_global_ranking_replay` and
`L25_local_support_ranking_beta0p25`. Both start from the E010 B25 update-500
model and AdamW state. Architecture, information set, base objectives, beta,
rank coefficient, projection, clip, pair order, evaluator, RNG and budget are
identical. Only the scalar ranked by `L_R` differs.

## Mapping and physics

The operator remains the fixed-mesh field transition

`G_theta: (d_s00, H_s00, alpha_bar_s00, q_prev_s00, f_s00, prescribed s00..s05 load path, mesh/material/BC data) -> (d_s04, H_s04, alpha_bar_s04, q_prev_s04, f_s04, u_s04)`.

`beta=0.25` weights the unchanged native-Q4 AMOR free-displacement equilibrium
residual. This is a limited PINO term; it does not impose damage stationarity,
history evolution or the full incremental variational inequality.

## New observable

For each cycle, freeze `m_i = 1[target Δd_i > 1e-15]` and nodal quadrature
weights `w_i`. With `p_i=max(d_pred,i-d_pre,i,0)`, define

`S_local = sum(w_i m_i p_i)/sum(w_i m_i) - sum(w_i (1-m_i) p_i)/sum(w_i (1-m_i))`.

The local arm ranks `S_local,growth - S_local,stagnant`; the global arm ranks
the E011 weighted mean absolute increment. Both use
`softplus(-(score_growth-score_stagnant)/(D*0.01))`, with zero margin,
`D=1.6864539921617467e-4`, projected coefficient 4096 and no sweep.

This differs from E010 `L_S` and `L_A`: those are per-cycle target-support
pointwise error and per-cycle global-amplitude error. `L_R_local` is a
cross-cycle relational loss on support-background contrast. The truth mask is
used only as an exposed-development training label; it is never an operator
input, conditioning channel, inference mask or output correction.

## Admission and budget

The read-only zero-step audit performs no optimizer step. Admission requires:
all eight initially wrong local pairs have finite local-contrast gradients above the frozen numerical epsilon; the actual next-AdamW
local arm improves at least one and strictly more wrong local margins than the
global replay; the protected global cohort is exactly 17 pairs and no more than three of those margins
cross zero. Directional tiers are 1--5, 6--7 and 8 helpful wrong-local pairs.

If admitted, run exactly 500 updates per arm, total cap 1000 and wall cap one
GPU-hour on Taobo GPU5. No retry, weight/temperature scan, fresh holdout,
checkpoint selection, architecture change or unused-budget transfer. The global arm must finish with model and AdamW state exactly equal to the frozen E011 ranking checkpoint; otherwise execution stops before the local arm.

## Result definition

Primary exploratory signal: local pair score `2W+T` gains at least 2 over the
global replay. A gain of at least 4 with `G`, `F`, `L_P` and `L_judge` ratios
all no greater than 1.10 is a robust local-objective repair tier. All component
metrics, local/global AUC, per-cycle amplitudes, wrong-pair repairs,
correct-pair losses and equal-scale fields remain visible even when the primary
threshold is missed. Endpoint decisions are computed only after strict reload
of each validated update-500 checkpoint. The same reconstructed fields feed
the local score, decision, CSV/NPZ evidence and figures.

This run can establish only exposed-state objective fit. It cannot establish
holdout generalisation, rollout stability, physical-teacher truth, transfer or
real-road validity.

## Review repair closure

The v2 implementation hard-stops unless the eight wrong local contrasts are all gradient-usable and the global protection cohort contains exactly 17 pairs. It durably records each completed pair/arm audit item, checks the absolute wall deadline before and after every independent pair/arm zero-step collection and every endpoint cycle replay, and publishes READY only after a final deadline check. A saved-checkpoint reconstruction test covers the prior failure mode in which live memory fields could disagree with the checkpoint while retaining the same global amplitude.
