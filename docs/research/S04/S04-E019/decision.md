# E019 result: retain the local repair; isolate the late optimisation failure

Execution: succeeded, all six fresh arms reached step10000; final receipt finished 2026-10-15T00:49:38.412323Z (01:49:38 BST). Residual-loop times sum3893.90 seconds (~64.90 GPU-minutes); wall time from dispatcher about67.37min. Retrieval: verified61files/201979097bytes against remote SHA256. All original files retained on Taobo; no producer mutation or rerun during analysis.

Primary producer verdict: **FROZEN_BASE_LOCAL_RESIDUAL_SCREEN_FAIL**. c20/c60 localized full errors pass .001, c83 fails; the all-three claim remains negative. Separate component finding from saved arrays: all three damage errors improve and all three total-background errors decrease against exact inherited backbone. This is same-state synthetic fitting, one seed and trajectory; no transfer, coupled trajectory or full FEM-teacher qualification.

## Exact final metrics

All quantities normalized by abs(Us). Full metric is mass-weighted two-component UV RMS. Region metrics condition on damage>.1 or its complement, and are not additive RMS contributions. Comparison is against exact fixed-damage UV-derived references, fixed history/fatigue.

| State | Arm | Full UV RMS | Damage RMS | Background RMS |
|---|---|---:|---:|---:|
| c20s4 | inherited backbone | 0.003079122 | 0.024234862 | 0.000240243 |
| c20s4 | unrestricted | 0.003078102 | 0.024229880 | 0.000235109 |
| c20s4 | localized | 0.000703914 | 0.005237330 | 0.000237205 |
| c60s4 | inherited backbone | 0.003487814 | 0.023153913 | 0.000267800 |
| c60s4 | unrestricted | 0.003466325 | 0.023017849 | 0.000252643 |
| c60s4 | localized | 0.000688588 | 0.004242773 | 0.000263838 |
| c83s4 | inherited backbone | 0.003304686 | 0.019560764 | 0.000166779 |
| c83s4 | unrestricted | 0.003302739 | 0.019552478 | 0.000155146 |
| c83s4 | localized | 0.003238238 | 0.019167443 | 0.000163454 |

Compared with inherited E017, localized full error decreases77.1391%/80.2573%/2.0107%, damage RMS78.3893%/81.6758%/2.0108%, and background RMS1.2644%/1.4794%/1.9935% (c20/c60/c83). Thus E018's final background regression is repaired relative to the stronger inherited baseline. Localized background remains **higher than matched unrestricted control** in all3states; preserve this distinction. It is not the best-background arm.

## What is and is not reproduced locally

Producer frozen aggregator admits6/6, no missing or integrity errors, same sampled streams in each pair, backbone unchanged and localized exterior drift<8.4e-17. All61downloaded files match remote bytes. Independent saved-array recomputation matches all18final full/damage/background metrics within absolute1e-14. Stored localized predictions equal original archived backbone predictions exactly outside support in all3states (independent array check).

**Unmodified Mac CPU aggregator replay is INADMISSIBLE (0/6).** Retain `recomputed_aggregate/summary.json`; do not overwrite it or relax the frozen checker. Diagnosis identifies only `baseline_metrics.reference_rho_u`: Linux values4.93906052e-11/4.80200347e-11/4.40580808e-11 versus Mac4.95692588e-11/4.81957941e-11/4.39640755e-11, absolute differences1.79e-13/1.76e-13/9.40e-14, above its1e-14 baseline-equality tolerance. This is reference-operator numerical portability, not a UV-error disagreement: the same difference occurs even with saved baseline UV. All reference rho values remain far below the frozen admission threshold. Do not call the complete cross-platform checker reproduced or Evidence Ready; original producer admission and the independent UV-array check are separate results. External Evidence review must assess this discrepancy before closure; no changed tolerance or source patch used here.

## Why c83 is the next bottleneck

99.7525% of localized c83 final squared full error is in damage. More than99.9999998% of its damage-error contribution lies inside the window core (window=1), with negligible damage error outside support. The missed .001 goal cannot be attributed principally to background transfer, taper attenuation or damage excluded by this window.

Passive traces show c20 improvement emerging between4k–5k steps, c60 between6k–7k, and c83 only near9k–10k, while the original cosine learning rate is already small. This supports a delayed-learning hypothesis; it does not prove an optimiser or capacity cause, nor establish convergence. A post-hoc scalar amplitude oracle on the **final learned correction** gives optimal scales1.00022/1.00294/5.39267 and full errors.000703914/.000688515/.003103044. Merely amplifying c83's learned direction cannot reach .001; the missing correction shape must also be learned or represented differently. Oracle is an offline diagnostic, never a replacement prediction.

## Disposition and next decisive step

Disposition: repair; preserve frozen-backbone/local-window design. Prepare one schedule-only diagnostic: original cosine versus delayed decay (hold lr1e-3 to step8000, then cosine to1e-5 at10000) under the exact same backbone, zero residual initialization, sampler stream, alpha.7, seed7, architecture, window, full objective and10000-new-step budget. Archive E019 localized finals as controls; avoid rerunning an unchanged matrix merely to obtain more scores. Cover c20/c60/c83. Primary all-three full<=.001 and damage/background component definitions unchanged; final step only. This is a **draft hypothesis**, not an approved new producer run or a proven repair. A new Experiment, exact code review and specific transfer/launch approval are needed before execution. If delayed decay fails, inspect residual features/local conditioning before adding capacity or expanding windows.

Local Evidence-review packet including the CPU discrepancy and this bounded repair draft is prepared under local_archive/experiments/S04-E019/evidence_review_v1/ (approval_preview.md contains full draft and attachment identity). No new external message or file send is authorised. No Stage2, new seed, extra steps or scientific retry.

## Assets and figures

Authoritative producer table `metrics.csv` and summary `summary.json`; independent9row baseline/control/candidate table `regional_metrics.csv`. Raw receipt, checkpoints, final predictions, fixed0/1000/...10000traces, real references and backbones: local_archive/experiments/S04-E019/producer_execution_v1/raw. Native strain/rho are secondary diagnostics and do not rescue or veto the frozen UV primary. History/damage did not evolve; no autonomous trajectory assets generated.

Decision figures and exact diagnostic tables: `local_archive/experiments/S04-E019/producer_execution_v1/analysis_render_v2/` (all states, native Q4 near-crack fields, final regional comparison, fixed trajectories). Local failed full replay and successful independent array check are both retained. Independent external Evidence review remains pending.
