---
storyline_id: S04
experiment_id: S04-E016
protocol_revision: v3-resume-equivalence
status: g5_hold_paired_semantics_and_input_lock
started_at: 2026-10-08
primary_storyline: S04
related_storylines: [S09]
scientific_verdict:
---

# Two additional Hard5 Umax trajectories

## Purpose

Add one development trajectory and one untouched confirmation trajectory after
S04-E015 showed that the frozen 99-feature ridge map did not transfer across the
existing three Umax trajectories.

## Roles

| Umax | Role | Permitted use before the next protocol is frozen |
|---:|---|---|
| 0.115 | development | qualification, feature/model development, training |
| 0.125 | sealed confirmation | integrity/schema checks only; no event or field inspection |

## Claim boundary

This is a data-acquisition experiment. Passing means only that two exact-family
synthetic FEM trajectories were produced with valid identity, timing, mesh,
field, event, and provenance evidence. It does not establish a successful Delta
network, FEM physical truth, PIDL improvement, or real-road validity.

## Frozen producer contract

- Producer: `CITPC12` Windows-FEM / GRIPHFiTH only.
- Source: exact Hard5 eta0 five-substep family used for U0.11/U0.12/U0.13.
- Intervention: Umax only.
- Cycle scope: first-hit search through c160, plus confirmation-only cycles
  first_hit+1..+3 (absolute ceiling c163); otherwise right censoring at c160.
- State: exact existing cycle export semantics—within-cycle maximum raw driver
  plus end-cycle committed damage/history/degradation, with frozen reductions.
- Common grid: native 86,408-element Q4 order.
- Channels: native `d`, `alpha_bar`, `f_alpha`, and peak raw tensile driver.
- Development/confirmation firewall: U0.125 result stays in a Windows-local
  non-OneDrive opaque archive; only its overall hash and aggregate QA booleans
  are public until the next predictive protocol and unsealing rule are frozen.
- Two phases: Windows first returns the source/state0/mesh/config/export/event
  hash lock and a U0.115 c1 smoke. Long runs require `LOCK_ACCEPTED_PROCEED`.
- Smoke comparison: recompute U0.115 c1 reductions from retained native state;
  do not compare U0.115 field values against U0.12. A c1 cyclemax=s4 check is
  not evidence that this equality holds at later cycles.

Full execution and acceptance contract:
`docs/handovers/windows_griphfith_request_31_u0115_u0125_peak_trajectories_20261008.md`.

## Primary acquisition criterion

Both trajectories must pass all nine Request 31 acceptance clauses. A failed or
unidentified clause makes acquisition `BLOCKED`; it cannot be rescued by model
training or by changing solver settings.

## Stop rule

Stop when the qualified U0.115 package and sealed U0.125 package are available.
Do not train or unseal within S04-E016. The next experiment must freeze the
Delta-model development protocol before U0.125 is opened.

## Status

- 2026-10-12: U0.115 acquisition exited0 in4h16min. Terminal audit verifies
  503 continuous checkpoint/model states0..502, finite retained histories,
  and complete s4/s5 through physicalc100. Native first detectionstep499 is
  c100/s4; native three-step confirmation stopsstep502=c101/s2, not three
  physical cycles. G5 remains HOLD for explicit projection/field/input
  qualification. See `u0115_pinn_terminal_audit_20261012.md`.

- 2026-10-12: user approved missing U0.115 PINN acquisition after Code Ready.
  Independent v3 PASS, single launch on Taobo GPU7, supervisor840976 ->
  training840977, Run `pf_u0115_acquire_39f8108fe96d406385e4011700cb47f9`.
  London deadline2026-10-14 18:35:49, 48h/50GiB bound, no retry. Initial
  runtime health verified; complete paired-data/G5 verdict remains pending.
  See `u0115_pinn_launch_receipt_20261012.md`.

- 2026-10-12 G5: Contract A has all 95 cycle files; Contract B has 95
  post-history s4 rows. Roles/exclusion policy is retained, but paired
  predictive readiness does not pass: existing FEM composite cycle summaries
  and PINN peak states differ in timing/reduction; complete U0.115 PINN pairing
  is unverified; exact derived f/active heads require native support. See
  `g5_contract_role_input_audit_20261012.md`. Reuse D003 evidence; next is the
  paired-asset metadata lock, not D0 repetition or NN training.

- 2026-10-12: fresh v10 completed with MATLAB exit 0. Producer semantic
  validation passes 7/7. External terminal audit rehashed all 1,116 manifest
  payloads with no missing/changed/extra files; 476 unique and 570 logical
  states are complete. Manifest identity is
  `55b9f7e923fd7a00170761ec470fb63629e72d28cf82c168edbaa2644e7be561`.
  This is terminal/integrity evidence only. G5 independent qualification and
  Contract A/B derivation review remain; confirmation fields are sealed and
  no model training or restart was executed.

- 2026-10-11: independently reviewed fresh-c0 v10 is the active production
  path and is running once on CITPC12. At the latest read-only check, MATLAB
  launcher/engine PIDs were 21684/30732 and 28 states had reached c0006_s02.
  No terminal receipt exists yet; this is not completion or scientific
  validity.
- 2026-10-11: independent review of restart candidate v11 returned
  `CODE_READY FAIL`. v12 repairs the finite/schema comparator, callback/I/O
  ordering, terminal receipt boundary and executable tests. Its Mac/Windows
  manifest is `4f4360edaa8f0935151c2f521a1b5b35a9bb93e808462aad8d890f45a33d0493`
  with 20/20 payload hashes matching. It remains an offline diagnostic:
  no MATLAB or FEM execution while fresh v10 is active.

- 2026-10-08: user approved both trajectories.
- 2026-10-08: Request 31 prepared for Windows-FEM dispatch.
- 2026-10-08: Phase A c1 smoke completed but v1 failed: cyclemax raw driver
  is not identical to s4 raw driver, and `alpha_elem` must be mapped explicitly
  to the actual `alpha_bar_elem` s5-committed field.
- 2026-10-08: independent ChatGPT review verdict `FAIL_HOLD`; no long run is
  authorised. Existing U0.115/U0.125 archives require reuse and contamination
  audits before the exact Phase B scope can be decided.
- 2026-10-08: v2 read-only repair completed. Existing U0.115 qualifies for
  read-only reuse/reseal without a new solve; U0.125 is
  `exposure_unknown_not_cleared`; the frozen metadata-only rule conditionally
  selects fresh U0.1175. Status is `AWAITING_CHATGPT_REREVIEW`; authorised long
  runs remain zero. See `request31_v2_readonly_audit_20261008.md`.
- 2026-10-08: external v2 review returned `PASS_ONE_U01175_LAUNCH` and issued
  `LOCK_ACCEPTED_PROCEED` for exactly one fresh U0.1175 run. Producer preflight
  then failed closed on storage before MATLAB start: C: had 20.194 GiB free,
  versus 13.75 GiB estimated c163 output plus the unchanged 15 GiB reserve
  (28.75 GiB required; 8.556 GiB deficit). No second qualified writable volume
  exists and U: is unavailable. Long runs started: zero. U0.115 was resealed
  by read-only reference; U0.125 remained closed. Receipt:
  `C:\q4runs\request31_u01175_preflight_20261008_v1\launch_preflight_blocked.json`.
- 2026-10-09: read-only CITPC12 storage-recovery audit completed. Live C: free
  space was 22.013 GiB; MATLAB count was zero and the intended output root was
  absent. The unchanged 28.750 GiB gate therefore still fails by about
  6.737 GiB. A 9.675 GiB low-risk candidate pair was identified in the July
  U0.11/U0.12/U0.13 canonical roots and verified against the Mac/OneDrive
  mirror across all 459 files with identical tree SHA256
  `52d546a498c946eb9c0edbb568e5a962c3261159aea1d7762509bdde58a4468f`.
  No deletion, move, compression, MATLAB start, or FEM run occurred. Explicit
  human storage-mutation approval and a fresh unchanged preflight remain
  mandatory. See `request31_citpc12_storage_recovery_audit_20261009.md`.
- 2026-10-09: v9i supersedes v9f after adding the two missing behavior assets:
  an actual identity-matched owned-tree cleanup with unrelated sidecar control,
  and a manifest/run/nonce-bound machine-readable Mac A-return-before-B-start
  timeline. Compact suite: MATLAB 11/11, authorization 10/10, spawn 13/13,
  detachment/identity/cleanup 11/11, release behavior 7/7 and cross-SSH probe
  PASS. Final MATLAB=0 and production output is absent. Status is
  `PASS_REQUEST31_V9I_LAUNCHER`; no production retry is authorised. See
  `request31_u01175_v9i_launcher_candidate_20261009.md`.
- 2026-10-09 11:25 UTC: the user authorised exactly one v9i U0.1175
  production run. Fresh full preflight passed with the frozen parent and
  payload identities, Contract A/B, zero competing MATLAB processes, absent
  output and 35,566,350,336 free bytes. Connection A returned before the
  independent connection B released worker 48012; the live chain is worker
  48012 -> MATLAB launcher 21260 -> R2025b engine 13956. At 11:28 UTC stdout
  had advanced to 48,730 bytes, stderr remained zero, and the output tree had
  created `fem_archive/`, `provenance/`, `states/`, and `static/`. Status is
  `RUNNING_HEALTH_CONFIRMED`, not completion or scientific validation.
- 2026-10-09 11:40 UTC: a fresh live check matched the same nonce and exact
  process chain. The `states/` directory contained 51 files and had completed
  `c0010_s05.mat`; `c0010_s04.mat` and all five c10 substeps were present.
  The latest state write advanced to 11:40:09 UTC, while no worker-exit or
  terminal sentinel existed. This is active production progress only.
- 2026-10-09 13:12 UTC: the sole authorised run terminated abnormally during
  c64 step 4. The final state write is `c0064_s04.mat` at 13:12:50 UTC; the
  state directory contains 320 files totalling 4,620,877,610 bytes. Native
  stderr is empty, while MATLAB's crash dump records an R2025b `abort()` at
  13:12:50 UTC and stdout ends with `MATLAB is exiting because of fatal
  error`. The worker heartbeat's `WORKER_POWERSHELL_EXCEPTION` and
  `powershell.exe` `System.IO.IOException` followed in the next second, after
  MATLAB had broken the native stream; they are secondary reporting failures,
  not the primary termination. The worker-exit receipt is zero bytes. No MATLAB
  process remained at the 16:23 UTC audit, and C: still had 28,585,717,760
  bytes free, so the observed evidence does not support a disk-full or a
  solver-convergence verdict. Status is `INFRASTRUCTURE_FAILED_PARTIAL_C64`.
  The partial states are diagnostic-only: they do not satisfy Contract A/B,
  cannot establish event/right-censor outcome, and cannot be resumed as a
  scientific trajectory until restart equivalence is separately qualified.
  No retry was launched.
- 2026-10-11: the failed asset was frozen externally without mutating its raw
  tree. The frozen inventory is 749 files / 6,640,762,683 bytes; its sorted
  SHA256 manifest digest is
  `f43c79f252ecc8fed6c7254f58c3f80d7c72961b1c53a37f9b5fca02e01fc5ab`.
  MATLAB read-only loading verified `checkpoint.mat` at c63 and
  `step_checkpoint.mat` at c64 s3 with all restart/event fields present;
  `step_checkpoint_tmp.mat` is corrupt and is timestamp-aligned with the c64
  s4 fatal abort. Direct resume remains disallowed because the current Stage 0b
  case runner and producer are fresh-only and the producer would repeat
  zero-load recovery. Decision: prepare a bounded cloned-workspace resume
  amendment, recompute c64 s4 only, and require restart equivalence before any
  separately authorised long continuation. Status:
  `FROZEN_FAILED_ASSET__RESUME_AMENDMENT_REQUIRED`.
- 2026-10-11: a clean, isolated non-FEM probe hung on its first invocation of
  the exact native `phase_field.mex.output.dat_output` binary used by v9i. A
  five-argument pure-MATLAB text-only replacement completed 10,000 calls and
  8/8 append/parse/fail-closed contract tests. This strongly localises an
  infrastructure defect in the native logger, but the production crash dump
  contains no stack, so it does not prove the exact crashing source line. A
  v10 fresh-run candidate therefore replaces only this text logger; physics,
  mesh, solver MEX kernels, tolerances, update order, Contract A/B capture and
  event policy remain frozen. The c64 partial will not be resumed.
- 2026-10-11: protocol amendment `v3-resume-equivalence` was frozen before
  execution. It permits one c64/s3 -> c64/s4 restart-equivalence Run only, with
  a fresh Run ID, exact frozen input hashes, no fresh recovery, a one-load-step
  stop, and predeclared `1e-12` scaled-max/relative-L2 field tolerances. A pass
  advances only to a separate end-of-cycle infrastructure smoke; it does not
  authorize long continuation. See
  `amendment_v3_resume_equivalence_20261011.md` and the storyline-level
  `../fem_pidl_delta_top_level_design_20261011.md`.
- 2026-10-11: the exact v11 candidate was mirrored to CITPC12 with manifest
  SHA256
  `ce6ecf3ce7b86964fdb51c39953b7ea3fcbb8323114fb27d1abd0a62684f2714`.
  Windows `validate_only` returned `VALIDATED_NOT_EXECUTED`; all 3 no-solver
  contract tests passed, with `solver_called=false` and `fem_started=false`.
  The target output root remains absent and MATLAB returned to zero. Status is
  `AWAITING_INDEPENDENT_CODE_REVIEW__NO_SOLVER_RUN`; the one-step numerical
  probe is not yet authorised, and no s5/long continuation is implied.
- 2026-10-11 22:19 UTC: the separately selected v10 fresh-run route passed an
  independent read-only implementation review bound to manifest
  `9b1721b667266400caffb21134d15d9ea14f43ddaf85de65b0e3bc0e24133b46`.
  Its live preflight passed with MATLAB=0, absent output and 36,116,197,376
  free bytes against the 30,870,077,440-byte gate. The single authorised fresh
  c0 run entered `RUNNING` through the two-session release contract: worker
  49600 -> MATLAB launcher 21684 -> R2025b engine 30732. Early read-only checks
  showed growing output/stdout, zero stderr and no terminal receipt. This is
  launch/health evidence only, not completion, convergence, Contract A/B
  acceptance or scientific validation. The v11 restart candidate is held and
  may not execute while v10 is running.
- 2026-10-13: G5 existing-state audit advanced to native64 geometry. v3 exact
  old/native identity FAILED; old center/area values exactly replay float32
  intermediates. Reviewed v4 repair retains that FAIL and independently admits
  85,112 native-center cells (98.6069% native area), excludes1,296, removes only
  cell57509 with no domain expansion. Independent method dialogue approved the
  mapping input identity. The unique CPU U0.115 PINN export then exited1 after
  2s on c1/s4 negative current-alpha admission; no trajectory NPZ was produced.
  Frozen nonsmooth ansatz permits signed tails (min -1.3258e-4 in that state),
  so a v5 signed-input/bounded-FEM-target amendment is awaiting exact code
  review. Original bounds FAIL preserved, no clipping, no training retry,
  no FEM full export and no D0. See g5_export_review_progress_20261013.md,
  g5_native64_mapping_amendment_20261013.md,
  g5_pin_input_bounds_diagnostic_20261013.md and
  g5_signed_pin_input_amendment_20261013.md. Main dialogue remains sole
  executor; method dialogue is read-only reviewer. G5 HOLD; no confirmation
  fields or U0.125 opened. Obsidian topic/Roadmap updated.
- 2026-10-13 final data-review milestone: independent review admitted the
  exact native64/signed-PIN archive lock cb9f63f8…868c for retrospective
  horizon0 imitation only:357 common-pre-event cycles/85112 cells. Detector
  traces have no earlier resets/gaps;U0.11 boundary checkpoint bytes and26
  model tensors match at600/605 (serialization file bytes differ). Four FEM
  s4 exports and100-row PIN export completed/verified. Original geometry and
  bounded-PIN FAILs remain;teacher/physics/Contract A full qualification HOLD.
  See g5_archive_admission_verdict_20261013.md. Unique next step is B0/B1
  closed-form runner preparation and exact Code Ready review, capped
  300s/2GiB/100MiB. No D0 fit,NN or confirmation scoring started. Ownership
  and Obsidian/Roadmap synchronized;no duplicate solve/training.
- 2026-10-13 D0 execution: exact cb86a118 independently Code Ready PASS,
  unique S04-E016-D0-R001 launched on Mac CPU4, then guard RSS_CAP at56.53s
  (sampled2.269GiB>2GiB), own child terminated. Six inner fits logged but no
  complete outer/percycle/models/figures persisted; no retry. Execution failed,
  method verdict INCONCLUSIVE; no Delta/NN/physical negative inferred. See
  d0_code_review_and_run_20261013.md and external local_archive/experiments/
  S04-E016/runs/S04-E016-D0-R001_guard_receipt.json. Minimum method evidence
  unavailable, Evidence Ready not reached. Next prepared engineering repair:
  cycle-streamed moments/Gram, dense-equivalence and working-set checks; a
  fresh actual R002 needs renewed exact review and authorization. Archive data
  admission unchanged;teacher/physics/Contract A HOLD, .1175/.125 still closed.
- 2026-10-15 R002 terminal: exact3f78309 final review request sent with the
  user's per-send approval; independent code review passed. Sole authorized
  B0/B1 execution COMPLETED without retry:97.73s, peakRSS1.468GiB, output
  about27.1MiB, below the unchanged300s/2GiB/100MiB joint limits. All12
  transformed all-cycle ratios improve, but C1-20 damage regresses in all
  four holdouts, physical raw driver regresses in three, and mean damage
  bound-violation area is40.2%-67.1%. Verdict MIXED diagnostic, not physical
  correction qualification or shared-network gradient-conflict evidence.
  See d0_streaming_checks_and_run_20261014.md and external R002 analysis/figures.
  Obsidian topic and single Roadmap entry updated. Next is read-only review of
  existing early-cycle/raw/bound regressions; no automatic D1/NN, refit,
  clipping, retry or confirmation access. No new outbound result send approved.
- 2026-10-15 authorized read-only R002 cause audit: no new fit/prediction,
  producer access or confirmation opening. Existing scores show equal stratum
  weights do not prevent late damage MSE dominance (68%-96% of B0 total);
  early regression persists after excluding C1-C2. Saved C20 decompositions
  identify oversized damage corrections in3/4 cases, raw high-value suppression
  (reference top~1% area contains>99.5% of B1 physical raw error), and deeper
  damage-bound violations despite less violating area. These fixed-snapshot
  explanations are not full-trajectory causal ablations or new acceptance gates.
  See d0_R002_readonly_cause_audit_20261015.md and its derived JSON pointer.
  Disposition: repair estimator/acceptance design before MOO, preserving external
  horizon0 architecture, data lock and splits. Unique next step is a no-compute
  design amendment choosing physical estimand/admissible representation/minimal
  test; no training or refit authorized. Obsidian/Roadmap updated; no outbound
  result message sent. Existing R002 verdict and original outputs unchanged.
- 2026-10-15 design-only follow-up prepared at user request: proposed
  design_revision_raw_physical_v1_20261015.md narrows the next question to
  single-output physical raw residual ridge, a fixed nonnegative output map,
  identical pointwise-admissible d/history controls, worst-whole-Umax physical
  error and inner early-regime veto with preselected whole-trajectory fallback.
  No new fit, counterfactual, runner implementation or outgoing request.
  Historical R002 untouched; new estimand/selector would need a new Experiment
  ID, separate exact implementation review and explicit run authorization.
  Existing300s/2GiB/100MiB cap is proposed only, not renewed execution authority.
  Method-chat design-review request drafted for per-send user approval;
  Obsidian/Roadmap updated to design-pending status, confirmation remains closed.
- 2026-10-15 independent design review received: exact approved410fffc message
  sent once and receipt/final verified. Reviewer directionally endorses the
  single-raw scope and common admissible baseline but requires three document
  fixes: explicit h/r input scales, terminal numerical errors rather than
  normal fallback, consistent tolerance/tie/partial-fallback routing. Main chat
  checked all three against unchanged410fffc and agrees. See
  design_review_result_410fffc_20261015.md for source message and exact findings.
  Status revision-required, not design/code/run approval. Unique next action
  is document-only v2 then a newly approved review request; no design rewrite,
  implementation, fitting or new computation in this turn. Obsidian/Roadmap
  updated; no additional outgoing message or confirmation access.
- 2026-10-15 user-authorized document-only v2 prepared: see
  design_revision_raw_physical_v2_20261015.md. Both full-domain training-PIN
  h/r means now explicit for each independent inner/outer fit; terminal
  identity/numerical/map failures cannot become ordinary fallback; unidentified
  denominators stop inconclusively; eps/tie/partial-fallback branches consistent.
  Original signed PIN input and V0/V1 scope unchanged. Future toy cases specified
  only, not implemented/executed. v1/410fffc and R002 remain unchanged.
  Exact re-review request is being prepared for per-send approval; no sending,
  implementation, fitting, producer access or new Experiment/Run in this turn.
  Obsidian/Roadmap updated to v2-pending status, not review or run approval.
- 2026-10-15 v2 independent re-review completed: exact user-approved45b8d32
  request sent once; returned final explicitly confirms all three issues
  resolved and no new mandatory corrections. Main chat checked scale,
  terminal-error and tolerance/fallback clauses against unchanged45b8d32.
  See design_review_result_45b8d32_20261015.md for delivery/response identity.
  Design is accepted as a basis for implementation discussion only; no code,
  tests, producer access, fit or further message this turn. Other S04-E017
  material in the reviewer response is not inherited as approval here.
  Recommended next step requires separate user authorization for runner/toy
  preparation and subsequent exact code/resource review; fitting needs its
  own later approval. Obsidian/Roadmap updated; confirmation remains closed.
- 2026-10-15 user-approved implementation/engineering preparation under45b8d32:
  raw scalar V0/V1 runner, joint guard/report and synthetic/mocked checks prepared
  at82e588e/8ef6c2d. No real inputs opened, real fit/score, SSH, confirmation access
  or code-review send. Toy dense/stream Gram maxdiff1.55e-15; nested selections
  and physical scores agree. Full generated357-cycle/86408-cell pipeline exits0:
  94.34s, aggregate sampledRSS1.60008GiB, output10.78MiB. Original caps unchanged;
  source-sized arrays plus loading-transient proxy, not actual decode/I/O.
  See raw_v2_runner_engineering_20261015.md for exact code/evidence/limitations.
  Figures visibly marked engineering-only; mocked cap cleanup tests pass.
  Main chat sole executor, method chat read-only; no duplicate/other-chat work
  launched. Exact code-review request is next and still needs per-send approval.
  Independent Code Ready and a named actual-run protocol/approval remain absent.
  Obsidian/Roadmap updated; original R001/R002/design/data identities preserved.
- 2026-10-15 exact user-approved ab34c46 code-review request sent once; final
  review received and checked against unchanged code. NEEDS REVISION: one P2,
  caller-relative authorization path is passed unchanged to a child whose cwd
  becomes repository root. h/r, physical residual/final map, error/fallback and
  four-fold/tolerance logic otherwise align with45b8d32. See
  raw_v2_code_review_result_ab34c46_20261015.md for per-item source checks and
  delivery/response IDs. Unique proposed next action is localized path repair
  plus one mocked non-root-cwd handoff check, then difference-only re-review;
  no full-size resource rerun needed for this change. No implementation, tests,
  actual archive reads, real fit/score or producer access this turn. Main chat
  sole execution owner; method chat read-only, S04-E017 held. Obsidian/Roadmap
  updated; new actual-run protocol and separate approval remain required.
- 2026-10-15 user-approved path-only repair completed at c883bfd. Guard resolves
  authorization once against caller cwd; parent validator/env/child argv agree.
  One isolated non-repository-cwd mock handoff test passed, no actual approval
  artifact/source/child/fit. See appended raw_v2_code_review_result_ab34c46_20261015.md
  for command, exact evidence pointer and mocked real-mode receipt caveat.
  No full resource/cap/model tests rerun; model/data/design/budgets unchanged.
  Difference-only review request prepared for per-send approval, NOT SENT;
  no new assignment to method chat, which remains read-only. Obsidian/Roadmap
  updated; no code approval, actual-run protocol or real fitting authorized.
