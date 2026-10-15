# Displacement re-equilibration / constrained damage closure — r1, 2026-10-15

S04 / S04-E011; synthetic C1 numerical diagnostic. Prepared locally, no new
upload or native execution authorized yet. Proposed run
`pf_s04e011_coupled_repair_20261015_v1`, CITPC12 / `AD\xw436`, new root
`C:\Users\xw436\jobs\E011_CR_20261015_v1`. Preserve frozen production E003/E011.

## Question and comparator

Can alternating displacement re-equilibration and the existing constrained
phase solver close both fresh residuals at the same peak u,d, without changing
accepted history? Previous [fixed-u repair](runs/damage_repair_v1_result_20261015.md)
passed all four phase subproblems but retained mechanical residuals
7.93469638e-5 / 5.26444778e-6 (c1) and 2.41066330e-4 / 3.08923851e-4 (c83).
This is the next missing coupling test, not a new full fatigue trajectory.

Exactly four starts: **previous DR-v1 constrained endpoints**, labelled by
original saved c1 outer3/13 and c83 outer20/28. Do not initialize from original
peak damage or the v2 clipped endpoint. Retain original accepted s3 nodal lower
bound and history per case, native source/MEX/state hashes, mesh86756nodes /
86408Q4cells, 2x2GP, E1, nu.3, Gc.01, ell.01, alphaT.5,p2,eta0, native GP
penalties421875/13781.25. All are peak substep4 at actual U=.11999988.
No new seed, checkpoint training, event selection or forward prediction.

Previous DR used captured raw at fixed u. Admission first reproduces that
fixed-raw phase residual, then initializes coherent raw freshly from the same
u,d; record the initial raw change separately. A tiny change is not silently
assigned to coupling. Old source oracle and frozen accepted predecessor must
reproduce before updates. Report previous fixed-raw phase norm alongside the
new coherent initial norm.

## Frozen numerical method and sole primary criterion

Each full block: (1) solve u with d fixed; (2) solve constrained d using that
u's fresh raw; (3) assemble equilibrium/raw again and then phase/history at the
identical returned u,d. Never compare a cached pre-update residual to a
post-update field. Native Kuu/cholmod2 is unchanged: no symmetrization, shift,
retry, damping or line search. Fresh mechanical inner stop <=1e-8.

`e011_damage_solve.m` is byte-identical to completed DR-v1 (SHA256
`9ba0a0ecc17811c1be0651623a712026d90a99076f7b7621e9a5b2bd232596b5`):
nodal lower<=d<=1, active-set/Picard, continuous natural-residual
backtracking and fixed-diagonal fallback, inner feasible residual<=4e-6.
No trial-f chain correction. Source-native GP penalties remain. This is a
constrained native residual/VI diagnostic, not a claim of a convex energy
minimum at c83. The phase helper's inner globalization is not outer damping.

**Primary, per complete same-field point:** finite fields, unchanged prescribed
DOFs, nodal bounds (1e-12), and

`C = max((||Ru_free||2 + ||Rd_feasible||2)/4e-6, ||Ru_free||2/1e-8) <= 1`.

Feasible phase residual uses the existing1e-10 bound filter, with coincident
lower=upper entries zeroed. Root final audit independently reassembles both
native equations before reporting success; replay errors must be<1e-10.
This coupled criterion is intentionally stricter than the previous phase-only
criterion. Failure does not retract the old phase-subproblem result. No
monotonic decrease of C or active-field disagreement is assumed or enforced.

## Budget, stop rules and conditional order

At most20 completed u→d blocks per state. Each case has **250 equilibrium and
250 phase native assembly calls total**, including admissions, callbacks,
rejected/failed attempts and final audits; four-case maximum2000calls.
Old-state oracle costs1u/1d; prior fixed-raw replay adds1d. Controller includes
these admission offsets, caps each total at249, reserving root final1u/1d.
It reserves the next fresh joint audit before starting each inner stage. Stop
on budget, inner miss, factorization/nonfinite error, or exact u/d stagnation.
If phase is just below4e-6 but Ru makes the sum miss, unchanged updates terminate
as exact stagnation; **do not secretly tighten tolerances**.

Run both c1 saved starts first. Only if **both final joint_pass** are true may
the two c83 cases execute. A numerical c1 miss yields c1-negative/c83-skipped;
identity/source/static/selftest failures abort. No retries, adaptive budgets,
new loading, accepted history writes or outer-max damage lower bounds.

Keep original s3 history/lower immutable in all inner callbacks; refresh trial
alpha/active/f from that immutable state, never from an inner committed state.
History commits=0, including terminal candidate. At c1 the earlier f=1 result
motivates a low-cost discriminator; nonlinear u/d coupling still needs testing.
A bounded miss is not an irreducible residual-floor proof.

## Outputs and predeclared analysis

Save coherent initial, first-u-only diagnostic (not a completed block), first
complete block, every block's scalar trace, overwriting task-owned last-complete
checkpoint, final point, attempted/evaluated failure states and inner traces.
Preserve returned data before root final audit; final-audit failures get a
separate file. `failure_stage` is the last stage even after a normal stop and
must not alone classify a failure.

Offline analyzer independently reconstructs Q4 raw, mechanics force, phase
residual and trial history234, verifies frozen bounds/history/BCs, same-field
norms and counters. Compare initial/first-u/first-block/final against DR-v1:
u/d max changes and locations, mechanical/phase residuals, active integral,
weighted relative L2 and weighted correlation. Optional **predeclared secondary**
comparison to existing paired-Q4 PIDL c1s4/c83s4 checkpoints4/414 uses both fixed
PIDL and varying FEM denominators and integral gaps; it changes no primary
criterion. No new training. This601-state paired archive includes step0;
steps are5*cycle−1, not arbitrary index shifts.

One closure figure shows completed blocks only, C=1 threshold, explicit c83
skips; same-stem sidecar provides provenance/reading/limitations. Visually
inspect generated figure after approved run. Partial outputs or SSH loss never
mean success. Retrieval must verify all bytes/hashes before final report.

## Review and transfer sequence

Local independent source review covers controller, budget/failure semantics,
builder/entry, analyzer and exact final nine-file manifest. Local Python compile,
imports and deterministic bundle checks are preparation, not native numerical
validation. On Windows, all seven MATLAB files undergo checkcode (only NASGU /
MSNU allowed) and12 tiny algebraic selftests before native cases. Existing
MATLAB process, receipt, output, failure/selftest/log marker prevents relaunch.
Check actual CITPC12/AD\xw436 identity, >=10GB disk and>=6GB free RAM. One CPU
thread, no GPU, no process disturbance.

New nine-file transfer requires user approval of account/root/full content and
hashes. The approval text explicitly includes replacing legacy Pro external
review for **this version** with local independent review; prior permission was
version-specific. No external message, upload, launch or GitHub push is covered
by local preparation. Raw results stay outside Git; commit compact code/docs
locally. Update track/registry before research frontier, then mesh对齐.md.

Claim boundary: numerical coupled-control sensitivity only. No physical
certificate, qualified teacher, repaired120-cycle trajectory or removal of
fixed-committed-f versus trial-f / joint Deep-Ritz versus staggered differences.

## Locator-only amendment r2 — 2026-10-15, before any coupled result

[Approved v1 attempt](runs/coupled_repair_v1_attempt_20261015.md) failed during
original s3 file identity, before native residual evaluation;12selftests pass,
0completednative states. Old production directory was separately removed after
backup verification. Fresh remote full hashes confirm c1/c83 accepted s3 files
under the identical-content OneDrive backup. No criterion or input content changed.

Prepare new9-file **v2** / run `pf_s04e011_coupled_repair_20261015_v2`, root
`C:\Users\xw436\jobs\E011_CR_20261015_v2`. Manifest only relocates predecessor
paths to `C:\Users\xw436\OneDrive - University of Cambridge\griphfith\S04_E011_raw_outputs_ad749c8_20261005_backup_20261015\S04_E011_FEM_Q4_C120\request28_post_commit`,
retaining original paths and unchanged SHA256. All6solver/selftest MATLAB
files unchanged; entry root and launcher root/runID/commit change. Launcher
additionally checks existence/fullSHA of all14unique locked state/capture/
prior-DR/predecessor files before creating a MATLAB process, to catch path drift
during approval. Source/MEX and native same-state admission checks remain.

Same12producer selftests and c1-double-pass conditional c83,20blocks and250u+
250d per state. No numerical retuning, state reconstruction, backup writing,
restore, v1 restart or history commit. Exact-v2 transfer and local-independent-
review substitution require new user approval; until then prepare locally only.
