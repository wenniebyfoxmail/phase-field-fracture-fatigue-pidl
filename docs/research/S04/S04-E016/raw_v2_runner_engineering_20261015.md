# Physical-raw V0/V1 runner: engineering evidence, review pending

Date:2026-10-15 Europe/London. Owner:S04-E016 implementation-preparation scope.
Branch:`codex/s04-e016-request31-storage-block-20261009`; base287854c.
User approved implementation/toy/resource preparation under design45b8d32,
NOT real-data fitting/scoring, solver work or sending the code-review request.

## Implementation and reuse

| Path | Role |
|---|---|
| `SENS_tensile/s04_raw.py` | scalar physical residual; two-pass weighted moments/Gram; nested early veto; all-fold decision; terminal invalid/unidentified paths |
| `SENS_tensile/s04_raw_guard.py` | joint300s/2GiB/100MiB fit+report guard; attributed child-tree RSS; no retry |
| `SENS_tensile/s04_raw_report.py` | saved-output-only R/G and fixed C20 raw report, no fit/selection |
| `SENS_tensile/s04_raw_checks.py` | independent toy dense oracle, causal/normalizer/decision tests; full-size generated-data pipeline |
| `SENS_tensile/s04_raw_guard_checks.py` | mocked wall/RSS/output cap and owned-child cleanup tests; no real child or oversized allocation |

Reuse search inspected s04_d0.py/checks/guard/report and the approved
s04_g5_features.py. Reuse original cycle weights, weighted merge moments,
frozen loader/lock and JSON serializer. The unchanged feature module retains
signed PIN damage and both h/r transforms. New streamed accumulation contracts
are scalar, not R002's old33x3 cross matrix; no old model/metric is overwritten.
The independent dense oracle tests this NEW physical scalar model, not numeric
equivalence to the different R002 scientific estimand.

Source implementation committed82e588e; cap-mock helper added8ef6c2d. The four
runner/feature-using engineering paths are byte-identical between those commits
(`git diff82e588e -- <four paths>` empty). Unit03 ran at8ef6c2d. The full resource
pipeline at82e588e remains applicable to those unchanged paths; no expensive
synthetic rerun was needed merely for adding an isolated mocked test helper.
Original feature module, loader, data lock and reviewed design45b8d32 unchanged.

## What actually executed — generated inputs only

Archive base:
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E016/engineering/raw_v2_20261015/`.
Final unit evidence:`unit_03/unit_receipt.json`; earlier unit01/02 retained as
development history, not different scientific runs. Mock evidence:
`guard_mock_02/mock_guard_receipt.json`; virtual guard receipts explicitly use
MOCK identities and are not physical resource measurements.

Full measured engineering pipeline:
`RAW_SYNTHETIC_FULL_01_guard_receipt.json`, matched fit-stage receipt and
`RAW_SYNTHETIC_FULL_01/receipt.json`, at exact82e588e.

| Test | Observed result | Boundary |
|---|---|---|
| weighted dense/stream Gram | maxabs1.5543e-15 | toy only; not bitwise equivalence |
| coefficients | maxabs1.1789e-16 | constants, unequal weights and std-floor cases included |
| both full-domain PIN scales | maxabs2.2204e-16 vs independent formula | no heldout scale statistics |
| nested physical R/G | maxabs5.3517e-16, identical alpha/fallback/outcome | four generated cases,164 outer toy rows |
| percycle physical errors | maxabs5.2188e-19 | final mapped predictions, not latent raw sum |
| zero target/residual and projection | passed | d/history identical relative to V0, not signed PIN |
| nonfinite/bounds/solver/undefined | terminal, not ordinary fallback | injected synthetic errors, no real source |
| eps boundaries/partial/all fallback | passed | all four folds retained, early regression first |
| cap handling/cleanup | wall/RSS/output virtual faults stopped only owned virtual PID; no report/retry | mocked, no2GiB allocation or actual long timeout |
| real CLI without separate authorization | blocked before output/source creation | no approval file fabricated |
| output reuse | rejected before another child launch | tested against completed synthetic path |

General toy numeric assertions use rtol1e-7/atol1e-10 unless a stricter scale/
mapped-score test is specified; exact std-floor masks, alpha/fallback decisions
and eps branching are separately checked. These are engineering comparison
tolerances, not scientific acceptance margins. Actual observed differences are
listed above rather than calling floating arithmetic bitwise equivalent.
Independent review should assess the numerical/conditioning coverage.

The independent dense oracle's platform matmul emits divide/overflow/invalid
RuntimeWarnings, as in earlier preflight. Warnings remain visible; oracle and
new implementation outputs are finite and the differences above pass. The
production Gram/prediction contractions use explicit einsum and the full
measured engineering log contains no such warning. Do not claim a proven root
cause for the platform warning or hide it as normal model fallback.

### Measured full pipeline

- Host:Wennies-MacBook-Pro-14.local; Python
  `/Users/wenxiaofang/miniconda3/bin/python3`; CPU4/noGPU.
- Four GENERATED trajectories with121/99/82/55 cycles,86408 cells,85112 scoring
  cells; source-array residency863,734,368bytes. Synthetic Q4 geometry, not the
  actual FEM geometry or measured trajectory. Loading-transient proxy: three
  extra touched122x86408 float32 arrays, released before fitting.
- Same production scalar fit/select/evaluate/report functions, six inner
  training pairs, all inner alphas, four outer folds,357 outer percycle rows.
- Joint elapsed94.3410s; sampled aggregate guard+child-tree RSS
  1,718,075,392bytes =1.60008GiB; outputs11,306,056bytes (~10.78MiB) at final
  receipt measurement. Fit and report both exit0, statusCOMPLETED.
- Original caps300s/2GiB/100MiB retained; no fallback producer or retry.

All engineering worker receipts declare actual_inputs_opened=false,
actual_fit=false,actual_score=false. Here 'actual' means real archive data;
synthetic closed-form fitting DID execute as authorized. The engineering
process replaces the real loader with a deny function and blocks source/lock/
confirmation paths via an audit hook. No scientific payload .1175/.125 opened.

Limit: generated residency plus a transient proxy is NOT an actual NPZ/MAT
decode benchmark. Real loading transients, I/O speed, actual feature conditioning
and scientific performance remain unmeasured. Real-mode guard additionally
imports the authorization/runner dependencies; the measured synthetic guard
does not fully model that parent import overhead. Preflight is below cap, not
a guarantee of future real completion; full real guard remains mandatory.

## Render QA and asset endpoint

Inspected both emitted PNGs: R/G comparator and fixed C20 FEM/V0/V1/error.
Titles visibly say SYNTHETIC ENGINEERING—NOT METHOD EVIDENCE; no blank or
transposed panels, native-style1-based Q4 connectivity rendered, three value
panels share linear0-to-max limits and error is symmetric about0. Nearly zero
toy ratios are expected from the constructed fixture, not research gains.
Source exact tables/arrays stay next to `README_analysis.md`; no manuscript
or independent scientific figure handoff. No real-result plot was generated.

## Future real interlock and readiness

No real-data command was invoked. Actual guard requires a separate authorization
JSON with explicit user-approved-real-fit flag, independent code-review verdict,
exact runtime HEAD, design45b8d32, original lock identity, new Experiment/Run ID
and exact fresh output path. These fields are an execution interlock, not a
cryptographic substitute for actual human authorization. This turn creates no
such artifact. Source paths must be tracked/clean and reviewed design unchanged.
Child also requires guard-bound run/code/start environment before loading data.

New Experiment/protocol/Run registration is deferred until an actual run is
separately authorized; no E016/E017 reuse. The prepared code can be reviewed
for design fidelity now, but is NOT a Run Ready package for a named real run.

Readiness:IMPLEMENTED+ENGINEERING_CHECKED; INDEPENDENT_CODE_REVIEW_PENDING.
No real feasibility result, teacher/physics/confirmation approval or NN/MOO
activation follows. Source/output/type checks and fault tests are not evidence
that this affine raw model transfers on real heldout archive trajectories.

## Coordination / unique next action

Main chat remains sole physical-raw implementation/engineering owner. Existing
method chat is read-only reviewer, not another executor. Its compact snapshot
was idle; separately discussed S04-E017 remains outside this task's approvals.
An incoming other-chat request based on the older R001-only state does not
replace the current human-approved45b8d32 task; no reply or unrelated work was
sent/launched. R001 remains RSS_CAP/inconclusive; R002 remains mixed diagnostic.

Prepare the exact independent code-review request for user send approval,
binding this code/evidence/design scope. Do NOT send it yet. Ask reviewer to
inspect only, not repeat synthetic or real fitting/resource tests. No real
data fit until subsequent review, a registered fresh run and explicit approval.
Obsidian topic and single Roadmap entry summarize readiness and limitations.
