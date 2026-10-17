---
storyline_id: S04
experiment_id: S04-E021
protocol_revision: v1
status: closed
primary_storyline: S04
related_storylines: []
scientific_verdict: supports
closed_at: 2026-10-15
---

# Physical-raw V0/V1 development feasibility diagnostic

2026-10-15 Europe/London. Prepared for human approval; NOT an execution permit.
New scientific question after S04-E016 R002; S04-E017 remains held. S04-E018–020
already used elsewhere; E021 checked against local worktrees/all local refs.

## Question, scope and reference

Can one physical-raw residual ridge improve the worst whole-Umax development
holdout over an equally admissible V0, without early-regime harm?
Claim class:C2 matched current-state field diagnostic; domain:synthetic.
Origin:nominal-peak s4 post-history, horizon0, native P0 query representation.
External correction only; PINN frozen, no state feedback or future prediction.

Reference is the admitted native archive, NOT qualified physical truth/teacher.
Retain E016 G5 archive-imitation admission and immutable lock
`cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c` at
`docs/research/S04/S04-E016/paired_s4_lock_candidate_20261013.json`.
Historical candidate/pending strings in that lock remain unchanged; the separate
`g5_archive_admission_verdict_20261013.md` supplies the narrow admission.
Contract B supports native simultaneous s4 reductions; Contract A teacher/
physical confirmation remains held. Nominal load factors PIN1 versus FEM0.999999
are not exact imposed-displacement equality; do not rescale them here.

| Development trajectory | Fixed prefix | Cycles |
|---|---|---:|
| U0.11 | C1–121 | 121 |
| U0.115 | C1–99 | 99 |
| U0.12 | C1–82 | 82 |
| U0.13 | C1–55 | 55 |

357 cycles; 85,112 admitted of86,408 cells; native-area weighting, not exact
conservative spatial projection. C0 unavailable, never fabricated. Event-based
prefixes are retrospective development admission only, not deployment features.
These four already-viewed trajectories are not fresh confirmation or four
independent material replicates. U0.1175/U0.125 remain sealed; no access here.

## Frozen method and grouping — unchanged45b8d32

Authoritative equations/error/selection rules are v2 at45b8d32 in
`S04-E016/design_revision_raw_physical_v2_20261015.md`; its historical status
text is superseded only by dated review records, not edited in place.

- V0=(clip(PIN.d,0,1), max(0,PIN.ab), max(0,PIN.raw)).
- V1.d/ab=V0.d/ab; V1.raw=max(0,PIN.raw+r_T*t_hat(X)). Raw Delta may be signed.
- Original signed PIN damage inputs unchanged. No learned damage/history head,
  time projection, mechanics constraint, f/H/active target or upper raw cap.
- Same32 causal PIN-only features/current+past2/missing masks/geometry9NN,
  current globals/load/physical cycle. No FEM event/field or future input.
- Each inner pair and outer triple has independent full-domain training-PIN
  h_T/r_T means, equal training-case and equal C1–20/C21–40/C41+ strata weights.
  h/r must be finite >1e-12. Both scales remain inputs despite one output.
- Train2048 geometry-systematic cells/cycle, native sample area renormalized;
  label=(FEM.raw-PIN.raw)/r_T. Weighted training-only X/label mean/std;
  finite std<1e-12 becomes1. Unpenalized intercept, ridge alpha=.01,1,100.
  Stable streamed moments then normalized Gram, physical inverse reconstruction.
- Four outer whole-Umax holdouts; each has three inner validations on the
  remaining cases. Six reusable inner training pairs; no cycle/node random split.
  All outer scores use every admitted cell, not sampled training rows.
- Eligibility:every inner early G<=1+eps. Minimize worst inner all-cycle R;
  exact objective tie chooses larger alpha. Learn only if best worst R<1-eps;
  otherwise preselect V0 for the entire outer trajectory. No outer-target rescue.

## One primary criterion and minimal early guard

Let M(u,s,V) be full-area physical raw MSE, averaged equally over cycles in
stratum s. E(u,V)=mean of the three stratum M values.
R(u)=sqrt(E(u,V1)/E(u,V0)); G(u)=sqrt(M(u,early,V1)/M(u,early,V0)).
Primary Q=max R over ALL FOUR outer cases; lower is better, V0 reference=1.
Fatal early-regression guard:all outer G<=1+eps; eps=1e-10, numerical tie ONLY.
Score final nonnegative outputs, not latent sums or log targets.

| Priority / condition after validity | Frozen diagnostic result | Bounded verdict |
|---|---|---|
| Any G>1+eps | EARLY_REGRESSION | negative for stated no-early-harm feasibility |
| All G<=1+eps; Q>1+eps | RAW_REGRESSION | negative |
| All G<=1+eps; Q<1-eps | DIRECTIONAL_DEVELOPMENT_GAIN | supports only this development diagnostic |
| All G<=1+eps; 1-eps<=Q<=1+eps | NUMERICAL_TIE | negative for strict directional improvement, not proof of zero signal |

Fallback fold must have R=G=1 and remains included; any fallback prevents strict
Q improvement. All-fallback adds NO_SELECTED_LEARNED_CORRECTION, never success.
Partial fallback does not hide regression elsewhere. Damage/history cannot
rescue raw failure; they are identical between arms, not extra voting metrics.

Feasibility/threshold rationale:no physical uncertainty or practical margin is
qualified. Do not invent10% gain/5% early loss or infer significance from cells.
Q>=0 analytic ceiling; zero target correction is available via fallback, but
does not guarantee an eligible model. Prior R002 motivates physical-scale repair,
not expected effect size. Four viewed development cases cannot support general
transfer. eps prevents numerical tie promotion, not a meaningful effect claim.
This jointly revised target/output/selector is a repair-package test, not a
causal ablation of which individual change helped.

## Validity, stopping and evidence

- Source/lock/state/support/shape/weights/scales/admission failure:terminate
  INVALID_INPUT, inadmissible. Nonfinite intermediate/solver/overflow:terminate
  INVALID_NUMERICS; mapped bounds or changed V1.d/ab:INVALID_IMPLEMENTATION.
- Any required inner/outer all/early baseline denominator<=1e-24:terminate
  INCONCLUSIVE_UNIDENTIFIED, never floor/exclude/fallback.
- Cap, child failure or missing required evidence:freeze partials, incomplete/
  inconclusive unless a specific validity failure is established. Execution
  failure is not a negative method comparison. No retry/resume/budget increase.
- Single joint pipeline ≤300s/2GiB aggregate sampled guard+child-tree RSS/
  100MiB generated outputs+logs+guard receipts. Internal295s reserve retained.
  Exact timer/sampling scope and limitations are disclosed in run_card.md.
- Required successful package:bound terminal guard/fit receipts, receipt.json,
  models/selection/decision JSON,357-row percycle.csv, four-fold folds.csv,
  fixed U0.115/C20 snapshot, both PNGs and README_analysis.md. No partial scores
  promoted as complete. Verify native IDs, finite values, all folds/fallbacks,
  ranges and damage/history identity; preserve warnings, do not rerun fits.
- Decision visualization:all four physical R and early G versus1, fallback
  labels; fixed U0.115/C20 FEM/V0/V1/error on shared physical linear scales,
  native mesh. Both are development s4 horizon0 archive evidence, not road truth.
  Use existing runner outputs only; no full trajectory prediction retained for
  plotting. Visually inspect outputs; table and frozen outcome rule authoritative.

Component findings select subsequent *proposals*, not extra runs:cap/integrity
failure→freeze and diagnose implementation; all/partial fallback→inspect saved
eligibility/ratios for absent eligible gain; early harm→inspect saved early
errors; raw harm→inspect saved R/physical field amplitude. A directional gain
permits discussion of a next validation, not automatic NN/confirmation/MOO.
No new ablation, fit or threshold relaxation follows automatically.

## Reuse, review and approval

Reuse s04_raw.py/guard/report/checks, s04_d0.py loader/moments and
s04_g5_features.py. No source changes/new numerical tests for this registration.
Design45b8d32 accepted; base code reviewab34c46 plus path difference review
c883bfd accepted. Review/engineering lineage remains in E016:
`raw_v2_code_review_result_ab34c46_20261015.md` and
`raw_v2_runner_engineering_20261015.md`.
Difference approval message:msg_015d0a19570ed14a016ad0f3cdff148191a1cad42a99e8cb50.
The E021 protocol only instantiates those accepted scientific rules; it is a
human-approval draft, not a newly obtained independent review of this document.
Any semantic/code change requires renewed exact review, not inherited approval.

Sole owner:current main chat. Method chat01a12d15-9b60-7280-8248-18386d6ef741
read-only; S04-E017/MOO/NN/producer work held. No cross-chat message this turn.
Fresh isolated branch codex/s04-e021-physical-raw-20261015, basec7528d1;
source byte-identical to acceptedc883bfd. Readiness remains draft until explicit
human approval and the run-card preconditions are satisfied. No authorization
JSON, data links, output directory, child, fit or new test created here.

## Runs and next action

Reserved only:S04-E021-R001, exactly one joint V0/V1 attempt (not one attempt
per arm/fold). Execution:not started; retrieval:not applicable; verdict:not yet
determined. See [run_card.md](run_card.md) for exact proposed command and scope.
Next:human reviews this v1 protocol/card and separately approves or declines
that single execution. After a permitted attempt, freeze and review evidence;
append outcome here and update the shared Obsidian task note, never rescue R002.

## Run update — 2026-10-15

The user approved exactly one `S04-E021-R001` execution at runtime commit
`6aa21e3c469d53c92240c9689d07a3ffb316d67c`, Mac CPU4, with the frozen
300 s / 2 GiB sampled RSS / 100 MiB generated-output limits and no retry. The
guard completed fit and report once in 106.373 s, with peak sampled RSS
1,648,459,776 bytes and guard-reported output 7,408,410 bytes before writing its
own terminal receipt. Final frozen inventory is 7,410,199 bytes including that
1,789-byte receipt; both totals are below100MiB. Both children
exited zero; no attributed process remained after completion.

The frozen decision file reports `DIRECTIONAL_DEVELOPMENT_GAIN`: all four
outer trajectories selected a learned correction, the worst all-cycle ratio is
`Q=0.967385295278036`, and all four early ratios are below one. Outer `(R,G)`:

| Holdout | R | G |
|---|---:|---:|
| U0.11 | 0.967385295278036 | 0.9097163623531194 |
| U0.115 | 0.9478121482522815 | 0.9319751006077125 |
| U0.12 | 0.847612534200584 | 0.8411589707385613 |
| U0.13 | 0.9083381014799462 | 0.9185162821123296 |

Local saved-output verification found the required 357 cycle rows and four
fold rows, continuous declared cycle coverage, no fallback, no negative final
raw output, zero reported negative area, and damage/history identity on every
row. Both required figures were opened and were nonblank, legible and
consistent with the tables. This is an execution-complete computed development
result, not yet an independently accepted scientific verdict. It supports
neither teacher status, physical truth, fresh-amplitude confirmation, neural
training nor deployment.

See `run_result.md`. Next action is one read-only independent evidence
review of the frozen package. No fit, rerender, new arm or confirmation access
is authorised by this result.

## Unified finalization owner — 2026-10-15

User now designates this main chat (`01a1131d-017c-7b03-a95a-ad73ba8fcc9c`) as
sole result-record, Obsidian and review-send owner. The coordination chat
`讨论 Azinpour 与 FEM/PIDL 对齐` (`019fa60d-9b72-72f3-a711-ab2126197932`) is idle;
its completed9c1bbcf result record, figure explanations and earlier draft remain
preserved. It monitored the already-running attempt, did not launch another.
No further writing/computation is assigned there. Method chat
`01a12d15-9b60-7280-8248-18386d6ef741` is read-only reviewer only; S04-E017 held.
No cross-chat notification sent without separate exact-message approval.

This is record reconciliation, not a v1 scientific amendment. Metadata status
analysis and blank final scientific_verdict reflect pending independent evidence
review; the local frozen-rule outcome remains DIRECTIONAL_DEVELOPMENT_GAIN.
Runtime protocol/code at6aa21e3 and all frozen outputs unchanged. No new fit,
score/selection recomputation, test, renderer, source export or confirmation
access during this consolidation. Existing audit/receipts and recorded values
were reconciled; raw-evidence write permissions remain removed.

## Independent evidence review and closure — 2026-10-15

User-approved exactbb875ac request sent once; independent review passed with no
blocking findings and no rerun required. See evidence_review.md for delivery/
response identity and main-chat item-by-item reconciliation. Only the frozen
v1 directional-development claim is supported; metadata supports/closed refers
to that narrow diagnostic, not general teacher/physical qualification.

Newly explicit caveat:U0.11 C41+ RMSE rises1.6083% (81cycles, ratio1.01608312895644),
despite improved equal-stratum total and early errors. It does not alter the
original fatal early guard or primary Q; no post-result criterion added.
Independent review did not replay all point predictions:other-cycle MSE and
inner R/G remain saved-output evidence, not a full numerical reproduction.
Both caveats added to run_result.md and shared Obsidian. S04 receives its dated
claim-impact entry at../claim_impact.md; existing v1 contract/outputs unchanged.

Run:succeeded; local retrieval:verified; evidence review:accepted within scope;
research disposition:advance to proposal preparation only. No further fitting
or execution authorized. At separately approved human handoff request a minimum
no-refit replay plan is prepared in next_validation_plan_v1.md, not implemented
or run. S04-E017/MOO/NN held; U0.1175/U0.125 remain closed. Main chat sole writer.

## Frozen-model replay supplement closed — 2026-10-16

Separately approved S04-E021-REPLAY-R001 (runtime08242ea) completed once and
its result snapshot0a3178c received independent read-only acceptance after the
user-approved exactf88da75 request. See replay_run_result_20261016.md and
replay_evidence_review_result_20261016.md for scope and item-by-item reconciliation.
Saved357cycle arithmetic and R/G/Q reproduce within unchanged tolerances;
U0.11 C41+1.6083% RMSE increase remains. C20 pointwise fields, actual input
content and full-domain bounds were not independently decoded/revalidated in
this review; they remain reviewed-code/worker evidence. Other-cycle pointwise
equality to unsaved original fields is not established. No new scientific
method gain, physical/teacher or confirmation claim; original v1 verdict stands.
This C0/C1 supplement is closed without rerun or same-round re-review.
Next suggestion is only to prepare a minimal read-only late-regression
attribution plan for separate approval. No new computation, fit, input/holdout
access or S04-E017/MOO/NN authority follows; main chat remains sole writer.

## Artificial binding engineering supplement — 2026-10-17

Separately approved S04-E021-LATE-BINDING-MOCK-R001 ran once under sourcee7bce63,
v2 card9f00a6e, launch checkout5d10aad. Five artificial check groups and eight
sentinel ratio probes completed:0.111917s, 52.375MiB aggregate sampled RSS,
10,575bytes in three frozen read-only files, below60s/512MiB/5MiB. No retry,
real-data read, fit or confirmation access. See late_binding_mock_R001_result_20261017.md.
This is C0 engineering evidence only; the original scientific verdict is unchanged.
Next proposal only:prepare the minimal real read-only handoff scope/run card for
approval; no real launcher, source access or late attribution is authorised here.

## Restricted real-file access proposal — 2026-10-17

At separate preparation-only approval, the exact four-source scope, parent/child
authorization handoff, 60s/512MiB/5MiB budget and stop rules are drafted in
late_real_readonly_access_scope_and_run_card_v1_20261017.md for human approval.
The proposed LATE-DIAG-R001 is access/snapshot verification only, not describe,
attribution, fitting or performance recomputation. Real launcher/source commit/
command are not yet implemented; the card cannot be executed. No source
metadata/content, mock or real Run was accessed/executed in this preparation.
Next:scope approval only, then implementation and independent code review;
final-version real execution requires a separate explicit approval. Main chat
remains sole writer; original scientific verdict and confirmation seal unchanged.

## Restricted access implementation and static review — 2026-10-17

User approved implementation within ea9cafb, not execution or any real input
access. Sourcefd4700f adds the bounded authorization worker and fixed launcher;
independent static review found one timer-origin issue, corrected at33feec6
and independently accepted on static diff review. See
late_real_access_code_review_result_33feec6_20261017.md for reconciliation.
No import/CLI/test/mock, real source metadata/content, fit or Run creation.
Default real switch remainsFalse, but a restricted real entry now exists;
neither its permit nor approval references authenticate human consent.
Runtime/resource/OS behavior remains untested. Next proposal only:prepare the
exact final command/card for separate approval, not launch or repeat mock.
Main chat remains sole writer; original science and confirmation seals unchanged.

## Final access command/card prepared — 2026-10-17

At user-approved preparation only, the final single access command and v2 card
are drafted in late_real_access_R001_run_card_v2_20261017.md, bound to full
source33feec6813347177649cffbcc0ba39297937a09e and the actual independent
acceptance messagemsg_015d0a19570ed14a016ad39fd210048191a8f8c550d8c5caab.
The fixed card-specific approval index is prospective only:it is not valid
until a subsequent explicit human execution approval for this exact card.
Four sources, access-only scope and60s/512MiB/5MiB/no-retry contract unchanged.
Only document-token/Git checks were performed; no source path probe, import,
mock, real access, fitting, authorization/output creation or execution.
Next:human approves or declines this one real-file access. No automatic launch;
main chat sole writer, original scientific verdict and confirmation seals unchanged.

## Approved real-file access R001 completed — 2026-10-17

Actual user message01a14ab6-a34f-7062-9411-009fb113707c approved card33351e2,
code33feec6 and its exact approval index for one S04-E021-LATE-DIAG-R001.
It completed once:0.101251s, 36.0625MiB aggregate sampled RSS, 12,638bytes in
four read-only frozen outputs, no cap/retry. Four actual scalar sources were
read (79,377bytes); identity/schema/357-row coverage and saved scalar checks
passed. See late_real_access_R001_result_20261017.md for approval mapping,
command, provenance, own-output verification and claim boundary.
This is access-only C0/C1 evidence, not attribution; no describe/report,
fit/replay or confirmation access. No source rows persisted and the one
access approval is consumed. Next proposal only:prepare the minimal genuine
late-attribution implementation/run scope under9984226 for separate approval;
do not rerun access or treat a generated-only report as a real report.
Original scientific verdict unchanged; main chat sole writer, holdouts closed.

## Minimal real attribution proposal prepared — 2026-10-17

User authorised document preparation only, retaining9984226 definitions and
decision branches. See late_attribution_real_plan_and_run_card_v1_20261017.md:
proposed S04-E021-LATE-ATTR-R001, distinct from consumed access-only DIAG-R001;
same four scalar sources,357-row validity check, only U0.11 C41–121 decomposed.
Primary descriptive localisation is k50, with positive/improvement/net amounts,
all81 harm/improve/tie counts and the original closure/identifiability rules.
One60s/512MiB/5MiB budget includes reading, analysis, the frozen two-panel
figure, all control outputs and run-owned caches. No extra fit or holdout.
No implementation, real metadata/content read, Run creation or execution in
this preparation; the genuine report/authorization purpose still needs a
separately approved implementation and independent review. Next:human scope
approval only, then implement/review; final exact-version execution separately
approved. Original science/outputs and main-chat sole writing ownership remain.

## Minimal real attribution implementation — 2026-10-17

User approved implementation and independent code review of the scope in
2f0ff22, **not source access or execution**. Same dedicated branch/worktree;
base 2f0ff22d26818ece7aa02f509451301c0cefb7d2. No producer coordination needed:
no jobs started, running code or old Run output changed.

- New `s04_late_real_attribution.py` / `_guard.py` implement the distinct
  ATTR-R001 purpose, fixed output, version-2 grant with execution references,
  original `describe()` and a genuine saved-file report. The adapter admits
  only this explicit additional purpose; global real acquisition remains False.
  Old access entry, generated report, mathematical core and 9984226/2f0ff22
  contracts are unchanged. A scoped Python permit is not a sandbox or human
  authentication; the operator must inspect actual review and final approval.
- Sources/357-row validation, late81 metrics/tolerances/branches and other-case
  saved-only background are retained. Seven core outputs plus run-owned caches;
  no rows/fields/models duplication, fit, replay or confirmation opening.
- Guard starts timing at execute entry, fixes non-optimised single-thread CPU
  child configuration, monitors aggregate sampled RSS and all owned output
  including caches, reserves 2s/16KiB, retains first failure, and reuses reviewed
  own-process-group cleanup. 60s/512MiB/5MiB is one sampled budget, not a tested
  hard OS guarantee. Plot/font initialisation is inside the supervised worker.
- Worker records metadata/read attempts, returned content bytes, describe and
  plotting entry. Failed reporting preserves completed access/analysis flags;
  absent or invalid child control record leaves these unknown in the parent.
  Real data is labelled synthetic viewed development, not engineering generated
  data or physical truth. The two-panel plot specification is implemented but
  no image was generated or visually verified.

Validation this turn: stdlib AST parse of three changed/new source files and
Git diff/contract-identity checks only. No project import, CLI/help, unit/mock,
resource run, real metadata/content/control-file read, Run/authorization/cache
creation, numerical analysis, fitting or holdout access. Runtime and visual
behaviour remain unverified. Independent static review will bind the exact
code commit; final execution needs its own exact-version card and human approval.
Main chat is sole writer; method chat may review only, not implement or compute.

Independent static review of 5ddecdb returned two mandatory fixes: active-worker
cache disappearance must not spuriously abort sampling; known describe checks
need safe distinguishable reason codes. Main chat corrected only those issues:
FileNotFoundError tolerance is restricted to cache paths while the child is
observed active; final inventory/core files/links/other exceptions stay strict.
Known unchanged-core constant messages and numeric overflow get whitelist codes;
unknown failures still expose stage/type only, never raw exception text/values.
AST/diff checks only, no execution/mock/real access; exact revision is submitted
for static difference review before any run-card preparation.

Difference review accepted `ab489652d4b4bb55c166782c8b9de9645a5f569b` with
both findings closed and no new mandatory issue (turn
01a14b70-fb6b-7643-b408-66045fe4a09a). Main chat read back and checked the
diff; see `late_real_attribution_code_review_result_ab48965_20261017.md`.
Static-only acceptance, not tested runtime/resource/visual readiness or run
permission. Next only prepare exact-SHA/final-command ATTR-R001 card for human
approval; no execution, mock, real access, fitting or confirmation opening.

## ATTR-R001 final command/card prepared — 2026-10-17

User authorised card preparation only. See
`late_real_attribution_R001_run_card_v1_20261017.md`: accepted source
ab489652d4b4bb55c166782c8b9de9645a5f569b and actual independent review message
msg_015d0a19570ed14a016ad3d35251548191b22c1d021d6e269a are bound to one fixed
guard command, new ATTR-R001 output, version-2 attribution purpose and the
card-specific approval index S04-E021-LATE-ATTR-R001-CARD-v1-ab48965. The index
has no authority until a human explicitly approves this final card/version;
old DIAG or implementation approval cannot be inherited. Scope, original
metrics/branches,60s/512MiB/5MiB including caches/report/control, and no retry
are unchanged. This turn changes docs only: no project execution/import,
real metadata/content/archive-path probe, Run/output/grant creation, mock,
analysis or fitting. Source/contract Git-equivalence and static command-text
checks only. Runtime/resources/visuals remain unverified. Main chat alone
updates Obsidian; no new task/compute dispatch to method chat. Await human
single-run execution approval, not an additional implementation or trial run.

## ATTR-R001 executed once and frozen — 2026-10-17

User explicitly approved97dd337/card-v1 andab48965 for exactly one four-source
real saved-scalar attribution/report (actual message
01a14b77-a884-7151-a192-56663074c791). Approval is now consumed. See
`late_real_attribution_R001_result_20261017.md` for command, human/review refs,
Run receipt and frozen asset pointer. Guard66697/worker66720 exited0; COMPLETED /
READONLY_ATTRIBUTION_REPORTED, no caps/errors/retry.8.805456s, sampled aggregate
232.375MiB,253398bytes across7core outputs plus font cache. Four science reads,
79377bytes,357-row validation; attribution/plot=true,fit/confirmation=false.

Saved U0.11 C41–C121 result: harm54/improve27/tie0; k50=22/81, S_plus22108.3600,
S_minus10890.8029, S_net11217.5571; late RMSE ratio1.0160831289564438 matches
the frozen reference. k50 covers half positive excess, not half net error.
Original branch selects PROPOSE_PHASE_OBJECTIVE_REPRESENTATION_QUESTIONS;
only a contribution-distribution branch, not physical/gradient-cause proof. Old E021
verdict unchanged; no source reopened or numerical attribution recomputed
after execution. Main-chat own-output integrity/figure check passed; all8files
and directories frozen0444/0555, no independent result review yet. Same PNG
copied/embedded in the existing Obsidian note, main chat sole writer. Next only
propose frozen-result read-only review; no additional analysis, fit or confirms.

## ATTR-R001 independent result review — 2026-10-17

User authorised a frozen-output read-only review only. Sent once to the method
chat; turn01a14b7c-6b21-7241-83ed-c9c177bc7606 completed/error=null, final
message msg_015d0a19570ed14a016ad3d67b3a1481918779ee2f2d9fac8b. See
`late_real_attribution_R001_result_review_20261017.md` for scope and point-by-point
main-chat check. Saved metric definitions/control declarations and existing
PNG consistency acceptable; one text fix closed: k50=22 describes the number
of ranked cycles reaching half positive excess and, with saved n_harm54,
selects the original phase-question branch. It **does not rule out a shared
upstream cause or provenance anomaly**, or justify excluding any cycle.

Review is not an independent recomputation/source authentication/OS peak or
physical-cause validation; core seven files checked, eighth cache/whole-tree
total not independently re-certified. Frozen outputs, numbers, figure, code,
contract and old E021 verdict unchanged; only main-chat interpretation/records
amended. No four-source reopening, describe/plot/fit/holdout or other calculation
by either chat. Obsidian/Roadmap updated by main chat alone, same PNG retained.
Next only prepare minimal phase-objective/representation design questions for
human approval, not implement a chosen loss or launch an extra fit/diagnostic.

## Minimal phase/representation proposal — 2026-10-17

User requested design/next-validation preparation only and explicitly preferred
less stringent exploratory validation. See
`phase_representation_minimal_proposal_v1_20261017.md`. Git evidence and feature/
ridge definitions only: no four-source or frozen numeric-file reopening,
recomputation, implementation/loss change, fitting or confirmation access.

Proposal separates saved facts (54/27,k50=22; record/visual review only, no cause
excluded) from H1: one existing PIN fatigue-state×raw interaction might add
value over the32-feature additive ridge. Existing32 already include cycle/
history/fatigue; no claim they lack phase information. Keep raw target and
output rules; add only z=(1-current_global_fatigue_f)*current_raw_log_feature.
Future exploratory B32/C33 both fixedalpha1, train the other3viewed cases,
evaluate seenU0.11, no inner search,2fits/one joint task only. Not historical
selectedV1 replication or fresh confirmation; would need a new Experiment,
precise input approval, implementation/review and separately approved run.

One proposed primary signal: lateC33/B32 RMSE direction. No imposed5%/10% gain,
all-case/all-phase/all-variable victory or p-value requirement; small gain is
weak evidence, early/overall changes disclosed as costs rather than an automatic
fatal guard. Old E021Q/early rule/verdict not relaxed. Necessary validity and
nonnegative/damage-history-identity/resource boundaries remain. Proposed new
fit ceiling300s/2GiB/100MiB, not reuse of consumedATTR60s/512MiB/5MiB. No Run,
directory or execution command reserved; design approval pending. Main chat
alone updates Obsidian; no task/compute dispatch or duplicate writing.
