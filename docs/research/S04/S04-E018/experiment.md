---
storyline_id: S04
experiment_id: S04-E018
protocol_revision: v1-physical-raw-feasibility
status: superseded__do_not_execute
started_at: 2026-10-15
primary_storyline: S04
related_storylines: [S09]
scientific_verdict:
---

# Physical-scale raw-driver correction feasibility

> **SUPERSEDED — DO NOT EXECUTE.** This local candidate used an experiment ID
> already allocated elsewhere. The globally checked, sole physical-raw run
> candidate is `S04-E021-R001` at commit `6aa21e3c469d53c92240c9689d07a3ffb316d67c`.
> No `S04-E018` authorization or output was created.

## Road-Fracture Experiment Gate

- **Claim class / evidence domain:** C1 evidence-validity / synthetic archive.
- **One question:** can the reviewed single-output physical residual ridge V1
  improve physical `psi_raw_direct` over the identically admissible V0 control
  on every complete development Umax holdout without worsening C1–20?
- **Evaluation unit:** one complete Umax trajectory. Cells and cycles are not
  independent units.
- **Origin / horizon:** `cN_s4_post_history_commit`, horizon 0.
- **Allowed input:** reviewed 32-column causal PIN-only feature recipe; current
  and two lags, missing masks, geometry, Umax, physical cycle, current causal
  globals and neighbours. No FEM/event/confirmation input at inference.
- **Target estimand:** admitted native-cell mean `psi_raw_direct` in original
  archive units. It is not true stress, reaction, active support or an energy
  integral.
- **Evidence identity:** admitted lock SHA
  `cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c`;
  U0.11 c1–121, U0.115 c1–99, U0.12 c1–82 and U0.13 c1–55; 357 cycles,
  85,112 cells. U0.1175/U0.125 and C0 remain closed/unavailable.
- **Comparator:** V0, the same pointwise-admissible control as V1 with zero raw
  residual. Damage/history are identical between arms.
- **Candidate:** V1, one streamed scalar physical-residual ridge with nested
  alpha selection `{0.01,1,100}` and fixed nonnegative raw output map.
- **Primary criterion:** with full-domain native-area physical MSE and equal
  early/middle/late weighting, `Q=max_u R(u) < 1-1e-10`, while every outer
  early ratio `G(u) <= 1+1e-10`. The tolerance is numerical only; this is a
  directional development diagnostic, not a practical-effect threshold.
- **Validity:** exact lock/source/state/support; finite calculations; final
  V0/V1 damage in `[0,1]`, history/raw nonnegative, V1 damage/history exactly
  equal V0; every required denominator identified; all four folds retained.
- **Stop rule:** first identity/numerical/map/cap failure stops the single Run.
  No retry, budget increase, new alpha, outer retuning or baseline substitution.
- **Minimum evidence:** guard/fit/final receipts, selection/models/decision JSON,
  all-cycle per-cycle table, all four R/G, fixed U0.115 C20 snapshot, comparator
  and field figures, and `README_analysis.md`.
- **Blocked conclusion:** no teacher/physics/road/forecast/confirmation, process-
  zone closure, NN, shared representation or multi-objective claim.
- **Decision before execution:** one development-only Run candidate is prepared;
  execution requires a separate exact user approval.

## Provenance and reviewed implementation

- Accepted design: `45b8d32da2b8088ce697047343bebf0a848e69ce`.
- Independently accepted runtime code: `c883bfd8e4ecd37d2ae32dc3717a63db018f1ae2`.
- Accepted path-fix review record: governance lineage through `c7528d1`.
- Runtime worktree:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-e018-runtime-c883bfd`.
- The runtime worktree is detached at exact `c883bfd`. Its only allowed
  untracked entry is `local_archive`, a declared symlink to the project archive
  root needed by the reviewed relative lock paths. Reviewed source paths must
  remain tracked and clean; the receipt must preserve the full dirty-status text.

The lock's historical internal status string remains byte-identical. Admission
is recorded separately in S04-E016 `g5_archive_admission_verdict_20261013.md`;
it permits only the bounded retrospective archive-imitation diagnostic here.

## Arms and decision map

```text
V0.d   = clip(PIN.d,0,1)
V0.ab  = max(0,PIN.ab)
V0.raw = max(0,PIN.raw)

V1.d   = V0.d
V1.ab  = V0.ab
V1.raw = max(0, PIN.raw + r_train*t_hat(X))
```

For each outer fold, nested selection uses only its three training trajectories.
A normal fallback is selected for the whole holdout before outer scoring when
no alpha is early-eligible or strictly improves the worst inner R. Numerical or
identity failures never become fallback.

| Complete result | Experiment verdict | Research disposition |
|---|---|---|
| any validity failure | inadmissible | repair only the failed contract; no score claim |
| cap/incomplete evidence or unidentified denominator | inconclusive | freeze; no automatic retry |
| any outer `G>1+eps` | negative: early regression | stop this scalar repair; inspect information/local representation |
| all G valid and `Q>1+eps` | negative: raw regression | stop this scalar repair; inspect information/local representation |
| all G valid and Q numerical tie | negative: no strict worst-fold gain | retain V0; no NN escalation from this result |
| all G valid and `Q<1-eps` | supports directional development gain | independent evidence review before any next method |

Even a directional gain only establishes archive-imitation value on the four
viewed development trajectories. It does not qualify FEM as physical truth or
authorize S04-E017, confirmation access or deployment.

## Criterion feasibility and resource boundary

R002 showed that transformed gains can coexist with physical raw regression;
three of four folds worsened physically. This run directly aligns fitting and
selection with the physical raw estimand and early veto, so it can distinguish
objective mismatch from a simple representation/information ceiling. No
material/reference uncertainty supports a practical margin, hence the strictly
directional diagnostic criterion.

Engineering evidence on generated source-sized arrays completed in 94.3 s,
1.60 GiB aggregate sampled RSS and 10.8 MiB output. It did not measure actual
NPZ/MAT decode, I/O or real conditioning. The real Run therefore retains the
hard joint caps `300 s / 2 GiB / 100 MiB`; cap failure is inconclusive, not
permission to increase limits or retry.

## Prepared Run

Exactly one candidate exists: `S04-E018-R001`. See `run_R001.md` and
`authorization_candidate_NOT_APPROVED.json`. The candidate authorization has
`user_approved_real_fit=false` and cannot pass the reviewed guard. No actual
authorization artifact or output directory has been created.
