# E017 completed ratio comparison — 2026-10-13

Status: complete valid numerical matrix; independent Evidence review pending.

## Question and procedure

Compare fixed alpha=.5/.7/.9 at c20 early, c60 middle, c83 transition, plus
c40 early-middle sentinel under identical8x400 network, seed7,10k steps and
unbiased full-field displacement objective. Targets are same-state conditional
UV references with fixed FEM damage/frozen history and fatigue. (u,v) RMS is
primary; strain/rho_u remain secondary. c40 comes from the separately admitted
early replay, not an asserted continuous same-execution trajectory.

## Execution and independent numeric verification

All12 fresh runs finished at10000 with no missing/integrity error. Code:
ed3adcef880e711aed175578a7da7861cfb746aa, clean, Taobo GPU0, final-only.
Compact prediction/metric/monitor/receipt/log package retrieved locally; checkpoints
remain on Taobo in verified output and archive copies. Read-only remote checkpoint
inspection verified SHA, step10000, float64 and reference identity for all12.
Local independent saved-array recomputation against all4 exact admitted references
matches final whole-field and conditional A/B RMS within atol1e-14. Compact bundle
SHA2ed61b0fab27d667ee23715bb5477b515d581f4caa768e01ff39df0349b91d71.

## Final field errors

All values below are dimensionless RMS/abs(Us); damage/background are conditional
on their own nodal mass. They are not their weighted full-field contributions.

| State | alpha | Whole field | Damage A | Background B | A share of squared full error |
|---|---:|---:|---:|---:|---:|
| c20s4 | 0.5 | 0.00326879 | 0.02571026 | 0.00028225 | 99.266% |
| c20s4 | 0.7 | 0.00307912 | 0.02423486 | 0.00024024 | 99.401% |
| c20s4 | 0.9 | 0.00321176 | 0.02528131 | 0.00024643 | 99.421% |
| c40s4 | 0.5 | 0.00417045 | 0.03037873 | 0.00034500 | 99.328% |
| c40s4 | 0.7 | 0.00328196 | 0.02391178 | 0.00026281 | 99.371% |
| c40s4 | 0.9 | 0.00318489 | 0.02318942 | 0.00028012 | 99.241% |
| c60s4 | 0.5 | 0.00355630 | 0.02362461 | 0.00023894 | 99.559% |
| c60s4 | 0.7 | 0.00348781 | 0.02315391 | 0.00026780 | 99.424% |
| c60s4 | 0.9 | 0.00338344 | 0.02246415 | 0.00025342 | 99.452% |
| c83s4 | 0.5 | 0.00326720 | 0.01934050 | 0.00015922 | 99.769% |
| c83s4 | 0.7 | 0.00330469 | 0.01956076 | 0.00016678 | 99.753% |
| c83s4 | 0.9 | 0.00343512 | 0.02032966 | 0.00018381 | 99.722% |

## Decision and bounded interpretation

- None of the three fixed alphas passes max(c20,c60,c83)RMS<=.001.
  Register NO_ALPHA_RECOVERS_THREE_STATE_DISPLACEMENT_GATE.
- Four-state worst errors: .5=.00417045; .7=.00348781; .9=.00343512.
  Frozen development ranking selects .9. Its advantage over .7 in worst error
  is only about1.51%; this single-seed result is not a statistical robustness claim.
- Statewise lowest whole-field error: c20 .7, c40/c60 .9, c83 .5. These explain
  variation; they cannot be assembled into a fictitious adaptive-alpha pass.
- Final squared-error concentration in damage is99.24–99.77%. Conditional damage
  RMS=.01934–.03038 versus background=.000159–.000345. Damage-region
  fitting remains the measured bottleneck; the causal role of sampling frequency
  versus global-network representation/optimization is not fully identified.
- E014 alpha.9 c20/c83 whole-field metrics are exactly reproduced by the new
  runs, providing an internal same-environment repeatability control, not new seeds.

## Trajectories and background tradeoffs

Exclude step0 initialization when reporting training excursions. c20/.7 has
background share42.81% at step2000; c83/.5 has33.62% at step4000; c83/.9 has51.29%
at step6000. c83/.7's maximum sampled checkpoint background share is4.24%, yet its
final whole-field error still fails. Lower alpha reduces some excursions but does
not uniformly stabilize all states or reach the primary displacement tolerance.

All9 primary-state final errors exceed .0025, activating the preregistered
DESCRIPTIVE common-error-floor screen. The curves still change in the late tail;
this does not prove convergence, a true optimization floor or architectural
non-representability. We do not extend the viewed budget or cherry-pick checkpoints.

## Next solution experiment

Advance the pre-reviewed E018 r2 matched smooth-global plus anchor-local
representation screen after this Evidence review closes. It keeps its prior
alpha=.7 and c20/c60/c83 × control/localized, seed7,10k, final-only. .7 enables
an exact frozen E017 comparator, not post-result alpha selection. The new arms
are parameter/activation matched to each other; the observed intervention is
the local coordinates+anchored compact window package. Narrow support is4.12%,
5.86%,7.20% domain mass. All island nodes remain in sampling/loss/evaluation.

Keep sampling as a useful ingredient; this matrix says ratio tuning alone
has not solved the UV-fit gate. If E018 improves all states but misses the gate,
retain that component finding and use the frozen repair logic. No coupled FEM,
Stage2, history-energy reproduction or qualified-teacher claim is established.
