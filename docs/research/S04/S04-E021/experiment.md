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
