# E018 r2 completed matched representation screen — 2026-10-13

Execution complete:6/6 fresh seed7 runs, final step10000, fixed alpha.7. Primary registration `GLOBAL_LOCAL_THREE_STATE_UV_FIT_SCREEN_FAIL`; matched-control diagnostic `localization_helps_all_three=true`. Evidence review PASS; see evidence_review.md. Fixed FEM damage/history/fatigue, supervised UV only.

| State | Arm | Full RMS/Us | Damage conditional RMS/Us | Background conditional RMS/Us |
|---|---|---:|---:|---:|
| c20 | control | .00686215 | .05279405 | .00155062 |
| c20 | localized | .00381510 | .00544464 | .00378271 |
| c60 | control | .00720469 | .04639235 | .00185178 |
| c60 | localized | .00556679 | .02116648 | .00462207 |
| c83 | control | .00782297 | .04548251 | .00153890 |
| c83 | localized | .00423101 | .02119125 | .00229470 |

Against matched control, full RMS improves44.40/22.73/45.92%; damage conditional RMS improves89.69/54.38/53.41%, but background RMS worsens2.439/2.496/1.491x. This is measured absolute background deterioration, not merely a larger percentage caused by reducing damage error. Damage contribution saved exceeds background contribution added in all states, hence full improvement remains real. All3 candidate full errors exceed frozen.001.

Candidate background contributes96.73/67.38/28.58% of total squared error, versus control5.02/6.46/3.76%. Candidate errors outside local support alone account91.11/59.93/23.61% of total. Most added background contribution is outside support, where local output is identically zero. Thus window-edge leakage alone cannot account for the whole background regression; the trained global solution differs. This does not independently identify gradient conflict, optimizer inadequacy, cancellation or smooth-branch capacity as the cause.

E017 alpha.7 original8x400 ReLU full errors are .00307912/.00348781/.00330469. E018 localized errors are1.239/1.596/1.280x those. That context is a different architecture/procedure, not a matched causal comparison. Do not promote the improved E018/control ratio to overall pipeline superiority. Branch magnitudes/cross terms are recorded in monitoring.json; they are not errors and do not independently establish harmful cancellation. Late7000–10000 errors still decrease; no convergence or impossible-capacity claim. All BC errors0; strain improves versus control but rho_u worsens in all3 (secondary only).

## Evidence integrity

Producer exacte67d9701419fbb891ce570edd3530bf68aae5f4e clean checkout. Frozen aggregator rerun read-only on Taobo returns same6valid/no missing/no integrity errors. Independently recomputed saved-array whole and regional RMS using exact references agree with final monitor/metric at atol1e-14. Receipts and compact prediction/monitor/metrics hashes match. Separate remote audit verifies all6 actual output/archive file hashes, step10000, float64 tensors, parameter count1128058 and geometry. Compact local bundle excludes checkpoint weights; no local checkpoint reload/replication claimed. Compact SHA be8594807d7720771ebbdaeac0547333c28d1df10be5812cd7e8065d2edf94bb.

## Next solution gate

Retain local fitting benefit, repair background preservation. Propose a frozen E017 alpha.7 backbone plus zero-initialized compact local residual, same admitted geometry and full objective, with explicit inherited-compute accounting and new protocol/code review. Cheaper diagnostic frozen_base_outside_floor.csv computes the immutable outside-support error lower bound from exact E017 predictions. A lower bound below.001 only excludes that particular impossibility; it cannot guarantee training success or representability inside taper. No new training before external planning and exact code gates. No E018 retry, support/padding/activation sweep, Stage2, coupled FEM reproduction or teacher qualification.
