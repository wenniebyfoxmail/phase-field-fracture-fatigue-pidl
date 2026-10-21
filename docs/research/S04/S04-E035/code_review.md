# Independent read-only implementation review

Reviewer: independent Codex subagent `shear_review`; required by project
Code Ready instructions. Numerical runners reviewed at `2bed8f5e`; focused
CUDA placement correction reviewed at `eff3fa0db567e5dba363f22696faea79ef8092c9`.
No training, MATLAB execution or remote mutation was delegated to the reviewer.

Result: no must-fix implementation defects remain for the explicitly
exploratory pair, conditional on the staged supervisor, runtime checks and
resource admission. This is not evidence of numerical convergence or agreement.

Checks covered: material and AMOR energy normalization; matched horizontal
clamped BCs and 30-state schedule; soft initial AT1 segment; FEM final accepted
residual reassembly before history update; direct neural nodal reaction;
positive T3 orientation and total mesh area; fresh output/launch claim;
exact-child watchdog; explicit GPU release prerequisite. Reviewer mesh check:
86756 nodes / 86408 Q4 / 172816 T3, total area 1.

The first review missed CPU network placement; parent final prep found it and
`eff3fa0d` moves net to CUDA before field/optimizer construction. The reviewer
independently rechecked that correction. Unchanged findings carried forward.

Installed native source copies were fetched for review to
`local_archive/experiments/S04-E035/preparation/native_sources/`:
Newton, staggered post-update, material characteristics, AMOR and AT1/PENALTY
MEX gateways. They confirm required `verbose` and `regularize_pf_only` options
and compatible native interfaces. Native checkout:
`C:/Users/xw436/GRIPHFiTH`, commit `2098dc9114fe9e8140f1f25607e1c74ddc4a032e`,
with pre-existing dirty files; the source inventory is recorded in preparation.

Known limits: Q4 2×2 versus T3 elastic centroid quadrature; T3 three-point
irreversibility only; distinct AT1 recovery/alpha-bound implementations;
one seed; native mesh not a shear convergence study. All remain explicit.
Watchdog polling granularity is 30 seconds, so nominal four-hour or storage
limits may be detected at the next poll. GPU0 remains reserved for D5; an idle
sample does not authorize this task. No device substitution is allowed.

Local verification: `python scripts/shear/test_shear_contract.py` — two
no-training tests pass (arbitrary-NN essential BCs, affine shear energy and
direct reaction with both Q4 orientations). Python compile succeeds.
Windows MATLAB static-check completion was pending at that review stage.

## Subsequent checks and first attempt

Actual Windows checkcode completed with STATIC_CHECK_DONE and engine exit0
after file-backed streams/task-local preferences; only two unused-variable
warnings remained. Windows NumPy3 removed 2D np.cross; explicit determinant
fix `98c75285` was independently reviewed and both CPU mechanics tests then
passed on Windows. No PIDL training occurred.

R001 later stopped at the damage-validity assertion; numerical agreement is
inconclusive, and missing rejected vectors prevent identifying the clause.
The independent reviewer checked its retained logs/receipts and confirmed the
outcome record is faithful. No source replay was performed.

The separately prepared diagnostic/control changes at `a5d65d21` passed focused
review: rejected-field export before unchanged assertion, one-state option,
distinct prefix completion, cached child handle and a shortened remaining-time
watchdog. This clears preparation only; fresh execution authority is pending.
Analysis review fixed stale-output risk and snapshot-state identity checks;
zero loaded states correctly generate no scientific comparison figures.

## Prepared single-call diagnostic transport

After R003's local budget guard prevented any SSH, the controller was assembled
outside a new producer attempt. Independent focused review at `276a1306`
passed after checking timeout/partial-output persistence, archive-decoding
failure receipts, invocation-specific retrieval, an exclusive local claim and
hashes for five retained dirty-native source files. Reviewer's local mocked
checks covered successful retrieval, byte/text timeouts and malformed base64;
no SSH, numerical replay or scientific code was run. The source hashes do not
pin compiled MEX identity. All earlier numerical limits carry forward.

Final numerical candidate remains `a5d65d21`; prepared transport is
`scripts/shear/execute_shear_diagnostic.py` at `276a1306`. Default invocation
is prepare-only. Execution requires a fresh explicit authority timestamp and
retains the original180-second boundary and90-second maximum native child;
there is no retry loop. This review creates no new execution authority.

## Revision2 full FEM admission

Independent same-channel reviewer shear_review confirmed FEM Code Ready at e6dcc2b88b347dab51034c2c7f7213788e3d58c9. Differential checks: identical251-node geometric essential-alpha masks; native non_hom_pf excludes those DOFs while retaining alpha1, future path free; unchanged physics/loading/thresholds; failure fields/invariants retained without re-evaluation; exact-child4CPU/16GiB/10GiB controls and absolute science deadline capped at total−600s; compiled installedMEX byte identities plus MATLAB which path checks; exclusive single-admission transport preserving timeout streams and totaldeadline-clamped calls. Local3no-training tests and actualmesh float32/float64 mask check pass. Prior findings carried forward. No reviewer remote operation, solve or training. GPU execution remains uncleared pending explicitHQrelease and GPUcontroller review. This review grants no additional attempt beyond the recorded authority.

## R005 outcome and prepared control correction

Independent evidence audit confirms one consumed start submission,0actualadmission/worker/solve: SSH banner exchange failed before command execution; readonly attribution rootabsent/states0 agrees with root-before-worker control order. Identity+upload+start53.699565s; including12.502696s attribution66.202261s,6.202261s above60s. This is a retained mechanical budget deviation within the unchanged8h total; no numerical conclusion or new submission follows.

Prepared-only correction independently confirmed at cd5e6cb0019bc0f107ef158c5c09f5c17c3659b8: claim/local timer/remote admission deadline share cumulative mechanical_remaining; all unknown-start calls clamp to that remainder, timeout streams persist, consumed preparation cannot overwrite payload, outerpath/hash persisted before transfer, verified start/terminal receipts distinguish monitoring/retrieval. Two local mocked no-remote checks pass. R005 stays closed; no new execution authority and no remote validation of this correction. Prior source payload and costs unchanged.

## Field/energy analysis extension

Independent focused analysis review at abccd72a confirms grouped native [ux;uy] DOFs, two-child T3 vector weighting and common signed scales per component/error; primary damage MAE unchanged. Pure-array check on the existing geometry finds identical affine nodal fields ux=.3(y+.5),uy=−.1x yield vectorMAE4.79211645e−5 solely from declared Q4nodalmean/T3areamean reductions on distorted cells. Therefore the secondary metric is combined field/discretization/reduction discrepancy, not pure NN error. This caveat is included in the generated README/sidecars. Actual R2 arrays and numerical takeaways still require retrieval verification and rendered-figure inspection. No reviewer remote operation, solve or training.

## R006 independent evidence review

Same independentreviewer recomputed all6rawacceptedstates: exacthistorychaining/BCs/251cracknodes/bounds/healing; CSVreactions matchrawforces, freeforceDOFresidualnorm matchesstoredru; maximumresidualsum≈8.875e−5<1e−4,maxhealing.000413357237777, top/bottomRximbalance≤8.525e−10. Mesh/profile/schedulematchR004. PFresidual checked as saveddiagnostic, not independently reassembled. Failed7finite/unaccepted,569.324160sstep; resu/respfNaNplaceholders andemptyforce mean finalresidualunknown. FailedPFcandidate differs fromstate6 and is not an equilibratedreference. Correctedfigures/README preserve boundaries; no must-fix evidence issue found. No reviewerremote/solve/training; proposedboundedmechanicalglobalization is designonly, no newexecutionauthority.

## R007 focused mechanics/control review

The same independent reviewer checked bounded residual-merit Armijo, native AMOR/cholmod2, actual accepted-cache timing and rejected-trial rollback, unchanged PF and final acceptance, finite exceptions, full-plus12 trial bound and500updates. Requested finite computed-merit checks and pre/trial overflow fixtures were implemented at63f79342/2cefc340;10array-only MATLAB fixtures remain unexecuted locally and must pass before FEM within the single production batch. The focused controller/watchdog review supports the7200s maximum,06:10Z total/retrieval reserve, cumulative120s mechanical budget including prior identities and30s attribution reserve, exact-child step/resource controls and no implicit retry. Final available-direction failure-payload correction is9ac5b1bc. No reviewer remote operation, FEM solve or training. Review applies to this bounded algorithm and controller; it does not establish convergence or a scientific result, and GPU admission remains pending separate explicit release/review.
