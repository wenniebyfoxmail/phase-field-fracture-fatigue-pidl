# One c1 loading–unloading sequence and accepted-history commit — r1, 2026-10-15

S04 / S04-E011 supplementary synthetic C1 numerical/state-transition diagnostic.
Status: **local preparation only**. New run proposed:
`pf_s04e011_c1_commit_20261015_v1`; CITPC12 (`citpc12-ssh`), `AD\xw436`,
`C:\Users\xw436\jobs\E011_C1_20261015_v1`. No new transfer or solve authorized yet.
This does not amend frozen E003/E011 production estimands.

## Question, unit and honest comparator

Can the repaired solver advance one complete c1 sequence while accepting
history exactly once after fresh joint convergence at each substep? Compare
with the original native flow from an identical full recovered initial state.
The previous [four-start closure](runs/coupled_repair_v3_result_20261015.md)
proved same-peak frozen-history closure; c83 active agreement worsened, so a
sequential/history test is the next missing component. This is not a new
fatigue-life trajectory, c83 onset estimate, or isolated bounds-only ablation.

Unit: two independently propagated arms through the five c1 substeps.
Origin: shared zero-load hard-crack recovery; horizon: one loading/unloading
cycle, with imposed displacements `.02999988,.05999988,.08999988,.11999988,0`.
Use the native increments, including floating roundoff at nominal zero; never
silently change the predictor or clamp displacement. All five original c1
states and state0 are existing development evidence, not a new holdout.

Comparator: original Q4 Newton/clip/cached stopping/native commit semantics.
First reproduce original archived c1s1–s5 fields and outer counts; only then
execute the repaired arm. Fresh joint auditing is observational in the original
arm and must not change its original acceptance/advance rule. It may therefore
commit at a state that fails the stricter joint screen; report this explicitly.
Repaired arm uses the previously verified coupled, displacement and constrained
phase helpers byte-for-byte. Both arms have their own accepted histories.

## Exact original ordering and common initial state

Frozen `solve_fatigue_fracture.m` SHA d3603548… has one commit branch after
native `stag_converged`: first `p_field_old=p_field`, then phase assembly with
final d, **new lower=d**, fresh post-iteration raw, and **old accepted history**.
The returned history is assigned once, followed by `break`. This source-level
single assignment does not prove fresh joint convergence before commitment.

Shared recovery reproduces the original phase-only Newton, clipping and one
initial reset of channels2/3 to0 and channel4 to1. Save full u/d/lower/raw/all4
history channels, geometry, free DOFs, version0 and initial predictor KK. Match
recovered nodal damage to original `state0_analysis.mat` at absolute1e-10.
Keep the native System stiffness cache based on its constructor hard-precrack
field: the original phase-only recovery does not refresh this predictor KK.
Do not replace it with a post-recovery reassembly while calling it reproduction.
Both arms receive exact value copies and restore this same initial KK; subsequent
steps use their own returned-field tangent. No further fatigue reset in c1.

The locked AT1 penalty Fortran module reads old channels2/3 and writes new2/3/4;
it does not define/read H(channel1). Retain all4 native channels unchanged,
require exact frozen/predecessor identity with NaN-aware equality, and qualify
native/offline history mappings on2:4 only. Record channel1 finite status and
archive differences separately; never silently assume or force H=0.

## Frozen spatial/material/solver contract

Native mesh86756nodes /86408Q4, native2x2GP ordering/Jacobians, plane strain,
AT1/Amor, E1,nu.3,Gc.01,ell.01,alphaT.5,p2,eta0, native GP penalties
421875/13781.25. Native source, actual which paths and MEX identities remain
locked, including System/stiffness-cache/step predictor and initial MEX.

Original: native displacement1e-6 /phase4e-4 /staggered4e-4, caps250/250/1000,
original regularization and clipping; no newly added line search/damping.
The exact numerical loop is extracted from the locked source, not rewritten.
Read-only snapshots/counters replace output capture only, not numerical rules.
Repaired: unchanged native Kuu/cholmod2, fresh-return u<=1e-8; unchanged
constrained phase helper with its existing inner globalization, phase<=4e-6.
No new outer damping/line search, trial-f chain correction, or threshold tuning.

## Sole primary and commit transaction

Repaired sequential claim requires all five accepted substeps to satisfy:

`C=max((||Ru_free||2+||Rd_feasible||2)/4e-6, ||Ru_free||2/1e-8)<=1`

at finite, bounded, fixed-BC fields under the **PRE-COMMIT old lower/history**,
and exactly one version advance/durable accepted record per substep, with the
native history mapping at those final fields. These clauses are necessary for
one claim: accepted state-transition consistency. Phase feasibility uses the
existing1e-10 bound filter, with coincident bounds zeroed; primal tolerance1e-12.
Postcommit new-lower/history residuals are separately labelled and cannot rescue
a precommit miss. Baseline native acceptance remains a comparator observation.

1. Freeze previous accepted state/version. Every trial and audit receives it
   read-only; no iteration-local trial history becomes the next trial's input.
2. Solve the next load and independently audit both equations at identical
   returned u/d/raw under that old state. Save `precommit.mat` before deciding.
3. Repaired requires fresh joint pass; original requires its native acceptance.
   Reject duplicate/out-of-order `(arm,c1,substep)` before the commit callback.
4. Compute one proposal via the original map: lower_new=d; native phase history
   from final d/raw plus old accepted history. Check channels2:4 against the
   precommit trial history at the same final fields.
5. Read-only postcommit audit checks the proposal/idempotence without assignment
   or an extra version advance. It is not a second accepted commit.
6. Save preimage, proof, proposed state, event, post-audit, counters and reference
   into a fresh same-directory partial, then move to `accepted_commit.mat`.
   **Only after helper success** assign the accepted state and continue. No
   overwrite, restart, resume, retry or next substep after any failure.

This is a same-directory application transaction, not a claim of power-loss
fsync/crash recovery. Synthetic file tests cover save failure and duplicate
receipts, not all possible move/OS/crash failures. Logs and saved failure state
must distinguish a proposal/callback from an actually accepted version.

## Budgets and failure rules

Shared initialization: one initial stiffness/setup MEX assembly, separately
reported; original recovery <=250 phase callbacks, reset once. Predictor uses
one original linear solve per substep/arm, recorded separately from assemblies.

Repaired per step: <=20complete blocks, <=250u+250d native callbacks **including**
initial/trial/failed/rejected evaluations, fresh precommit audit, commit mapping
and postcommit audit. Controller caps248u/247d reserve preaudit1u/1d,
commit0u/1d and postaudit1u/1d. Five-step arm cap1250u+1250d.

Original preserves its native caps rather than changing its stopping for equal
budget: per step<=1000*(250u+1post-iterationu)+2auditu=251002u;
<=1000*250d+preaudit1d+commit1d+postaudit1d=250003d. The large bound is the native
maximum, not expected usage or a speed benchmark. Count wrapper calls exactly;
per-outer counters permit reconstruction. Both arms have at most5accepted commits.

Static/source/input/selftest failure aborts before native callbacks. Recovery
identity or any original c1 reference mismatch makes the paired comparison
inadmissible and prevents repaired launch. Repaired joint miss/cap/error saves
last accepted state and failure/attempt, commits0for that step and stops. No
adaptive budget, tolerance tightening, trial-history accumulation or120cycles.

Feasibility rationale: old c1 same-peak tests closed within4/1blocks and250+250;
exact original source replay previously reproduced c83. Sequential c1 state
feedback remains untested, so five passes are not assumed. A bounded miss is
not an irreducible residual-floor proof; identify the first failing substep.

## Input, execution and evidence

Prepare15files locally:13MATLAB including entry, input_manifest.json,
launch_wmi.ps1. Proposed8ordinary Windows-local input snapshots total156839354
bytes: original state0, metadata, five c1 postcommit MATs, and identical native
mesh from the existing approved CR-v3 ordinary file. Copy only into own new
inputs directory, verify source/target SHA/bytes before/after, reject
reparse/offline/recall. Never alter original source/archive/old run roots.
Exact full contents and final hashes belong to the versioned approval manifest.

Actual same MATLAB worker must before native solves: strict checkcode of all13
MATLAB files (NASGU/MSNU only),6damage+6coupled+10commit/file guards, source/
which/MEX locks, all8input full reads/hash/size and exact geometry. Recovery
must run in an isolated helper to avoid nested/static workspace with native
initialization scripts. The22tests are preparation until executed on Windows.
No new local Mac native solves or training. CPU single thread, no GPU.

Launch only after exact-version user approval, fresh CITPC12/AD\xw436 checks,
>=10GB disk/>=6GiB RAM, no MATLAB process and no attempt markers. WMI detached,
record source commit/branch/dirty status/PID/command/log/root/start. SSH loss is
visibility loss; never relaunch. Source static review is not Windows execution.

Retrieve terminal root including inputs/code/receipts/logs and all common,
precommit, accepted, failure and trial records. Verify every SHA/size. Offline
analyzer reconstructs raw/mechanics/phase/C, original archive regression,
predecessor identity, version/event counts, same-field commit and idempotence
from GP weights; audits active history2:4 and records unused channel1. Duplicate
same-field commits can be numerically idempotent: values alone are insufficient;
source review, actual ledger/version transitions and guard tests all matter.

Minimum decision figure: original/repaired PRE-COMMIT C across all observed
c1substeps with C=1, plus committed weighted alpha; missing steps explicit.
Primary table remains authoritative. Secondary paired u/d/active/alpha/f
changes explain the effect, not acceptance. Zero unloading denominators are
reported unavailable with absolute errors retained. Required figure sidecar,
README_analysis, decision and independent evidence review follow retrieval.

Outcome: valid+five-step primary pass supports only this synthetic one-cycle
transition claim; valid miss is negative for that bounded claim, with first
failed stage selecting a repair; identity failure inadmissible; missing evidence
inconclusive. No teacher, unique energy branch, physical truth, repaired full
fatigue trajectory, c83 fracture onset or linear/exponential accumulation claim.
PIDL committed-f vs FEMtrial-f / joint Deep-Ritz vs staggered distinctions remain.
New transfer and execution require approval of this final package and its local
independent review replacing legacy Pro review for this version. No push.


## Operational amendment v2 — 2026-10-16

v1 stopped at strict checkcode before native work; preserve the attempt. v2 fixes two comma forms, explicitly consumes native returned diagnostics without feedback, uses isscalar, and predeclares three script variables before hash-frozen native initialization with shape assertions afterwards. Frozen source overwrites placeholders before use. No solver/formula/tolerance/budget/acceptance/history change. Newroot E011_C1_20261016_v2; same15file count/8input contents. Native22tests and five original regressions remain prerequisites, not already passed. New version requires fresh user approval before upload/copies/execution; NASGU/MSNU whitelist unchanged. See runs/c1_commit_v1_attempt_20261016.md.


## Operational amendment v3 — 2026-10-16

v2static checks passed but binary manifest parsed ascell because lastobject keys differed in order. Normalize binarykeys(name,path,sha256), retainvalues/arrayorder; validate homogeneous ordered schema/types/SHA locally for source/binary/staging and assert struct/count10 inentry. Numerical contract and all12nonentryMATLAB files unchanged. Newroot E011_C1_20261016_v3 and exactapproval required before anytransfer/execution. See runs/c1_commit_v2_attempt_20261016.md and runs/c1_commit_v3_preparation_20261016.md.
