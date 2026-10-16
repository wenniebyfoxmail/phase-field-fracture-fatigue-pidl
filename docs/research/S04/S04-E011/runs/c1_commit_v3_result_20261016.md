# C1 sequence v3 — original regression stops at s3, 2026-10-16

Windows admission passed. Original s1/s2 reproduced their archived states,
including original outer counts, and each saved one accepted history version.
Original s3 stopped at the frozen raw-energy pointwise regression gate; repaired
arm never started. This is not a paired repair outcome. Keep the strict gate
miss and all frozen E003/E011/CR-v3 conclusions unchanged.

## Execution and integrity

Explicit v3approval covered15files72706bytes,8ordinary input copies156839354bytes,
local independent review substitution; source clean commit
3d2d7386c7537f73d4477a637ca1f65270147b39,
branchcodex/hard5-q4-t3-2x2-20261005, CITPC12/AD\xw436,
root C:\Users\xw436\jobs\E011_C1_20261016_v3.
ManifestSHA ad5f0584f29fc57e21405978fbf130734eb999885e921c7953eba81108ceb586.
Preflight09:47:22.776Z noMATLAB/rootabsent,20666384KBfreeRAM,
85322592256bytesdisk. Upload15SHA/sizes matched;8copies staged/hashverified.
WMIwrapper8304, launcher31364, worker7468; start09:47:29.7371537Z,
MATLABR2025b CPU1thread. At09:52:49.932Z observed terminalfailure/noownprocess.
No restart, changed remote files or other-process disturbance.

All13strictcheckcode, source/which/MEX checks,22algebra/file selftests and same
worker8input fullread/mesh geometry passed. Shared original phase-only recovery
34calls, one fatigue reset and original cachedpredictorKK; recovered nodal
state0maxerr2.77555756e-16. Mesh86756nodes/86408nativeQ4/GP4; fixed original
material/load/solver/budget and no new trial-f or damping changes.

Retrieval42files406754040bytes, everySHA/size verified, independently rehashed.
Raw/receipts outsideGit:
local_archive/experiments/S04-E011/runs/pf_s04e011_c1_commit_20261016_v3/.
No repaired folder, sequencefinished marker or original s3accepted_commit.
Local common-Q4 replay and figure-sidecar audit passed. Figures visually checked.

## Frozen original regression and first miss

Tolerances remain1e-10: u/d absolute nodal max; raw/history max absolute delta
scaled by max(1,abs(reference)); history2:4 uses actual proposedhistory. Outer
count must exactly match. H(channel1) remains preserved/inactive separately.

|c1 step|outer vs archive|u maxerr|d maxerr|raw scaled maxerr|history2:4 scaled maxerr|durable version|
|---|---:|---:|---:|---:|---:|---:|
|s1 .02999988|2=2|2.4633e-16|1.1102e-14|7.5995e-14|7.5995e-14|1|
|s2 .05999988|3=3|8.2052e-16|6.8556e-15|3.2263e-13|3.2263e-13|2|
|s3 .08999988|9=9|1.2767e-12|1.5181e-12|5.0122e-10 FAIL|4.1001e-12|none|

Only raw pointwise error fails at s3;4/345632GP exceed the original threshold.
Global GP/Jacobian-weighted rawrelativeL2 is1.63940528e-12, active-relativeL2
4.47256520e-12. This is not evidence of a large damage/trajectory branch.
The strict frozen prerequisite nevertheless failed; do not relax it or start
repair retrospectively.

Worstscalederror: zero-basedelement68430/GP0,xy(-.4015869167,-.0015779382),
initial left crackwake. Candidate/reference raw2.6056593475813927 /
2.6056593462753845, delta1.30600819e-9. Independent same-Q4/Amor replay of each
ownu gives delta1.30601041e-9 there; ownstored-vs-replay scaledmax9.2254e-13 /
1.2728e-12. Allfiveoldreference ownrawchecks are<=2.3002e-12. Thus the energy
response to tiny u differences explains the field mismatch; no raw timing or
operator inconsistency was found. Upstream source of those u differences,
including runtime/linearalgebra/roundoff/cache possibilities, is NOT isolated.

## What history and residual evidence actually says

|step|fresh Ru|fresh feasible Rd|PRE-COMMIT C|native accepted|durable accepted|
|---|---:|---:|---:|---|---|
|s1|1.03621838e-5|5.12575858e-6|1036.21838|yes|yes|
|s2|2.18094653e-4|1.05734838e-5|21809.4653|yes|yes|
|s3|3.84718750e-5|1.26294037e-5|3847.18750|yes|no: reference miss|

Original cached acceptance is preserved. All three final points miss the new
freshjointscreen; C is dominated by Ru/1e-8, phasealsoexceeds4e-6. The first
twocommits are single durable version advances under the original rule; they
were not preceded by strict fresh joint closure. Independent residual replay
maxerr<3.5e-17 for both accepted points. Their weightedalpha means are
.0004509687754 and.001653598404, fmean1; these are original arm observations,
not repaired improvements.

s3precommit fields/proof and historyproposal exist; phasecommit mapping and
readonlypostaudit preceded reference comparison. Accepted=pre=version2,
proposalversion3 has no durable record. Event/proposal is not an accepted commit.
Failure stage label remains postcommit_readonly_audit from the caller; actual
exception is E011:BaselineRegression, not a failed idempotence audit. Original
u/dcalls8/45,11/82,51/291 across three attempts; s3totalphase291 spans9outers,
within original caps, not repaired250cap. Shared recovery34phasecalls separate.
No new history reset after initialization and no repaired trial/commit.

## Analysis, disposition and next discriminator

Reproduction scripts: tools/s04_e011_analysis/analyze_c1_commit.py for two
accepted transactions; audit_c1_regression_failure.py for allthreeobserved
candidates, actualproposal history, frozen-error test, ownu rawreplay and version
failure checks. JSON records exactinput/code SHA. Outputs:
analysis/commit_trace.csv, c1_commit_analysis.json,
regression_localization.csv/json/png/md, original c1_commit_decision.png/md.
Allobservedstates shown; missing s4/s5/repaired explicit. Comparison figure is
regression_localization.png; its companion narrative is authoritative.

Runexecution failed at prerequisite; retrieval verified. Primary paired
state-transition verdict inadmissible here (original5state prerequisite missed),
repair efficacy inconclusive/unassessed. Disposition repair reference-admission
method first, not retune damage solver. No claim of physical truth, teacher,
120cycle repair, c83onset or error accumulation law.

Next local discriminator is separate ownfield rawconsistency from rawresponse
to allowed nodal perturbations, with a mathematically specified bound and a new
reviewed protocol; current ownu replay supplies evidence, not a new acceptance
criterion. Do not substitute a larger rawthreshold to rescue v3. Any future
producer repetition/changedcomparison/repairarm requires frozen newconditions,
exactversion approval and a freshroot. No v4bundle or producer run is launched.
