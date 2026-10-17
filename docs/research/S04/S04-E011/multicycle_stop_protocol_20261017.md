# S04-E011-MCS/r1 — cycle transfer of post-damage re-equilibration diagnosis

User authorized direct execution and reporting on2026-10-17. This amendment
preserves all original E011, C1 and S2SO outcomes. Synthetic C1 numerical/state
diagnostic: do the c1s2 post-damage mechanical bottleneck and overlapping
joint-sum/outer-u stopping effects persist at c20/60/80/83? Separately, how do
original and locally re-equilibrated FEM fields disagree with the unchanged
latest complete paired-Q4 PIDL baseline? Agreement never selects a FEM solve.

## State and scope

Latest complete matched baseline is E011 native-Q4 production, FEM/PIDL120
cycles, sourcead749c8, common86756nodes/86408Q4/2x2GP and retained five-substep
schedule .02999988,.05999988,.08999988,.11999988,0 after recovery. More recent
FEM repairs contain only a fullc1 or conditionalc83 states, not a replacement
complete trajectory. Never stitch their histories into a new trajectory.

Natural cases: cycles1,20,60,80,83 each substeps2 AND4. s2 is a first-loading
state atc1 but a reloading state later; s4 checks actual peak damage advance.
Each uses its own original postcommit s1/s3 predecessor, with its committed
history and nodal d as frozen lower. Initialu/d=that predecessor's u/d. Rebuild
KK at that same initialfield and apply actual pre_iter_update(substep,...).
Record KK inputs/count, full predictor and target boundary displacement;
natural cases are defined conditional restarts, not automatically original
production prefixes. Assert actual cycle, predecessor substep, geometry/DOFs,
prior/targettopuy and load factors, not just filename or counter arithmetic.

One separate common-start c1s2 anchor must first reproduce archived S2UJ U1J1
u/d/raw/history, r4 and exactouter19, with its own saved predecessor/start and
predictor. It is not the naturalc1 case: its max(O1d,R1d) initial damage differs.
Source data: immutable backed-up original Q4 postcommit files onCITPC12;
20s1..s4 snapshots independently transferred/size/hash verified, plus old common
geometry/mesh and anchorcase. Same-worker full input reads before any case.

## Native diagnostic and budget

Reuse unchanged S2UJ/S2RA native operators, constrained damage/globalization,
fresh residual controller and mechanical helper. Fix inneru1e-8, innerd4e-6,
strictsum4e-6, outeru1e-8; all material/bounds/penalties eta0 and trial-f rules
unchanged. Actual substep is passed, not hardcoded2. Mandatory one complete
u/d/fresh block, even if initial point passes. Store all complete points,
before/after damage Ru, feasibleRd, actual returned/evaluatedu/raw, u/d,
trial-f range, histories, innertrials/counters and failure state.

11 total cases: separate anchor, then naturalc1s2/s4, c20s2/s4, c60s2/s4,
c80s2/s4, c83s2/s4. Per case20completeouter/250u+250phase inclusiveobservations;
controller248/248 pluscasecache1u, sharedsetup1u separate. No historycommit,
recovery/reset, propagation to other cases, extra budget, damping/tol rescue or
automatic retry. Anchor mismatch/identity/nonfinite/IO/programmingfailure is
globalfatal; finite inner/budget/stagnationmiss is saved and other independent
cases may continue. A last complete miss is never an accepted FEM reference.

FreshCITPC12AD\xw436 rootE011_MCS_20261017_v1,R2025bCPU1thread detachedWMI.
Read-only availability/noMATLAB/6GiBRAM/10GiBdisk before staging and launch;
never disturb a process. Clean exact Maccommit/package/input review first.

## Stop-only policy replay and comparisons

After integrity/nativeoperator qualification, scan each observed strict path
for FIRST eligible completepoint under Ssum(4e-4,4e-6) x Vouteru(4e-4,1e-8).
Source inspection must reconfirm these thresholds only affect exit. Respect
original budget/stagnation/inner-miss exits and actual savedhorizon; an absent
crossing remains missing. No interpolation or continuation beyond source path.
Report indices/each gate margin and full conditional field differences. Both
singleton gates selecting the same endpoint means overlapping sufficient
restrictions only there; never unique dominance or50/50 physical contribution.

Mechanism evidence: per-state complete-block counts of before-damageRu passing
and post-damageRu failing, feasibleRd/sum/outeru components, phase-inner misses
and actualcost. A phase miss can be the bottleneck; do not infer mechanics from
the subset whose phase solve completed. No fitted binary dominance threshold.

Compare A=original target FEM u/d, B=first strict completeblock, C=acceptedstrict
endpoint(or explicitly lastcompleteMISS), P=same-state unchanged PIDL. Evaluate
raw(u),damage/g,active, nodal u/d, histories/f separately. For trialhistory or
common-residual replay, condition all candidate fields on that FEM predecessor
history/lower, explicitly labelled conditional. Own archived postcommit history
is retained separately and its one-commit mapping discrepancy is measured, not
silently fixed or required to match a known stale nativehistory. For PIDL own
objective/gradient diagnostics use its OWN previous checkpoint history/f and
penalty state; FEM-conditioned residuals are not its training objective.

Metrics: unaveraged nativeGP/Jacobian absoluteL2, relativeL2 with fixedPIDL norm
and separately each FEM norm, correlation, integrals and near-tip/wake support.
Near-zero denominators yield absolute metrics rather than huge percentages.
Policy-induced change uses each state's firststrictblock norm plus fixedPIDL
norm; legacyc1common55.89610% retains its separate S2DJ00 denominator. Do not
compare those percentage magnitudes as physical error-growth rates. Report
all10natural states, accepted/miss labels and anchor separately. A smaller FEM
residual is not automatically closer PIDL/physical truth.

## PIDL baseline, plateau and next action

Export exact stored PIDL models/checkpoints at globalstepk=5(c-1)+s, verify
checkpoint physical metadata where present and original settings/source, own
previoushistoryk-1, own immutable trainingloss array and all current GP state
shapes. k=0 recovery is not a physicalcycle. No inference from a flat loss alone.
Prefer CPU1thread inference/gradient readout on authorized producer if no safely
usable GPU exists; no Mactraining or sharedGPU collision. Any new objective
direction/optimizer diagnostic needs a separately exact-code reviewed bounded
package before execution, fixed prehistory/integration/model and no accepted
history update or overwrite. Distinguish parametergradient, nodal equilibrium/
feasiblegradient and representational/projection limitations. If optimizerstate
was not saved, do not claim exact RPROP continuation. No new full PIDL training
or change to the E011 baseline is included in this FEM diagnostic.

## Minimum evidence and disposition

Qualified existing archives lack strict naturalc20/60/80/83 prefixes, so a small
native diagnostic is justified. Newproducerrunidpf_s04e011_mcs_20261017_v1;
code/protocol/package/source/input binding and independentreview before launch.
Retrieve fullroot and verify terminalfilecount/sizes/hashes. Independently
replay native raw/Ru/Rd/history under frozenprehistory, source BC/DOFs/predictor/
counters/limits and original state timing. Keep codeReady/runReady/evidenceReady
separate, and preserve misses. Minimum decision visualizations: residual/gate
trajectories and firststop grid; all selected same-state FEM/PIDL fields and
signed differences; phase/cycle field-disagreement evolution with naturalstate
and localrepair labels, not a fictional repaired120cycle trajectory. Include
exact tables/JSON, README_analysis/sidecars/renderinspection, independent
numerical/narrative review, compact trackedresult/manifest, experiment/track/
registry thenfrontier, mesh对齐.md andonecurrentRoadmapline; embedselectedPNGs.

If strict local FEM qualifies, it is a conditional numerical candidate, not a
globalphysicalteacher. If phase/assemblybudget misses, diagnose that recorded
bottleneck without raising caps here. PIDL tuning should follow the qualified
FEM subset and its OWN objective-stationarity evidence, not select FEM by PIDL
agreement. No new coherent fatigue trajectory/life, unique equilibrium or
physical truth claim. Spatial/Carrara alignment leaves committed-f/trial-f and
jointDeep-Ritz/staggered-Picard differences.
