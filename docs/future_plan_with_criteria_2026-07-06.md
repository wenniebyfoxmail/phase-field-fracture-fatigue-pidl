# Future Plan With Criteria

**Date**: 2026-07-06  
**Scope**: PIDL/FEM mechanism work plus road-DT/M2S validation after strict-result cleanup.

## North Star

Do not optimize for more runs. Optimize for one claim-changing diagnostic at a
time. The current main comparison is hard-recovery PIDL `c89_peak/step444`
versus SENS recovery FEM `N_f=89`: event timing is now essentially aligned, but
the field mechanism remains mismatched through local degraded active-driver /
history / process-zone feedback.

## Global Experiment Gate

Before launching any new experiment, answer:

1. What mechanism question does this run answer?
2. If it succeeds or fails, which claim changes?
3. Is there a cheaper diagnostic that can answer it first?
4. What is the minimal output asset: table, figure, state export, or decision note?
5. How will it enter the main checklist after completion?

## Plan

| Step | Mechanism question | Cheaper diagnostic first | Minimal asset | Success criteria | Failure / stop criteria |
|---|---|---|---|---|---|
| 0. Registry cleanup | Which results are aligned enough for current claims? | Use existing inventory and handoffs only. | `docs/aligned_result_registry_2026-07-06.md`. | Every active claim points to a primary/supporting asset; quarantine rows are out of daily decisions. | If an artifact lacks mapping/state semantics, it stays in quarantine. |
| 1. Clear comparison board | What is the one clean PIDL/FEM pair for the main story? | Use existing hard-recovery PIDL and SENS recovery FEM package. | `docs/pidl_fem_clear_comparison_board_2026-07-07.md`. | c89 is established as the hard-recovery event-scale comparison; c69 is kept as legacy diagnostic only. | If another comparison is proposed, it must name why it supersedes this pair. |
| 2. Active-driver/process-zone gate | Can a candidate improve field co-location, not just fracture timing? | Recompute existing process-zone metrics before training. | Table using `docs/active_driver_process_zone_metric_2026-06-28.md`. | Tip/process-zone active `psi`, `alpha_bar`, and `Delta E_d` ratios move toward FEM without worsening V7/reaction. | If only `N_f`, `alpha_bar_max`, or boundary hit improves, do not promote. |
| 3. C1 / early feedback diagnostic | Is the active-driver mismatch already seeded by early alpha-to-uv coupled feedback? | Extend existing c1 alt-min/frozen-alpha analysis, no N100 run. | C1 table/figure with `psi_raw`, `psi_active`, `eps_eq`, `grad(E_hist)`. | A change identifies which substage creates or suppresses the raw/active mismatch. | If it only changes final scalar event timing, stop and return to field gate. |
| 4. Event-window field diagnosis | Why can event timing align at c89 while fields do not? | Use state0/c69/c89 existing analysis tables first. | Decision note plus 2-3 field panels for damage/history/fatigue/active driver. | Cleanly states which mechanism is mismatched at c89. | If fields are not state-comparable, stop and fix state export semantics before any run. |
| 5. M2S validation | Can road-DT/M2S be validated without hiding forward PIDL field mismatch? | Use existing M2S scripts on stricter multi-trajectory exports. | Holdout table: trajectory split, sparse/noisy observations, RUL MAE. | State-driver proxies improve RUL on leave-one-trajectory-out, not just same-trajectory cadence. | If strict trajectories are nearly identical or leakage dominates, label as too easy. |
| 6. Producer run promotion | Is a production run justified after diagnostics? | Review Steps 1-5 and code alignment. | `00_intent.md`, `01_monitor.md`, `decision.md`, table/figure. | Producer launch has commit, dirty status, command, output root, archive root, log, PID/GPU, and registry destination. | Missing provenance or missing minimal asset blocks launch. |

## Code-Execution Criteria

| Work type | Machine | Allowed on Mac? | Code alignment |
|---|---|---:|---|
| Import/unit sanity, posthoc CSV/figure, registry docs | Mac-PIDL | yes | Use current `upload code` branch; do not touch dirty user files unless needed. |
| PIDL training, N-cycle smoke, production runs | Taobo / CSD3 / Windows-PIDL | no | Read `docs/taobo_gpu_submission_protocol.md` for Taobo; record commit, output, archive, log, PID/GPU. |
| FEM reference generation/export | Windows-FEM | no | Use handover inbox/outbox; export state index and field semantics with every package. |
| Surrogate/tooling smoke | Mac or Taobo depending GPU need | Mac only if no training loop | Mark as tooling-only; never cite as physics evidence. |

## Promotion Rule

A future experiment is promoted from diagnostic to evidence only if it changes a
named claim in `docs/research_frontier.md` or this plan. Otherwise it remains a
negative/diagnostic row in the inventory.
