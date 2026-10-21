# S04-E035 — Monotonic shear FEM/PIDL comparison

Purpose: extend the tensile solver comparison to a different loading mode;
exploratory synthetic numerical comparison, not material/road validation.

Goal anchor: tensile mechanism comparison → shear under an explicit common
material/loading/initial-state contract. User-directed fork on 2026-10-20;
existing tensile results and negative results are unchanged. One owner: this
Experiment. Branch `codex/fem-pidl-shear-20261020`; explicit remote base
`bf14e16a15173bc416d67f86ee2cac02025bbc56`. In scope: `scripts/shear/`, this
Experiment record and a concise Obsidian milestone. Shared source is reused
without modification. No public push, third-party communication, cyclic
fatigue, parameter sweep, or physical-validation claim is included.

## D1 reuse and option inventory

Searched the installed GRIPHFiTH `Scripts/{elasticity,brittle_fracture,fatigue_fracture}`,
`Sources/+specimen/+internal`, the existing `examples/SENS_shear`, shared PIDL
`SENS_tensile/field_computation.py`, `source/{compute_energy,fit,optim,utils}.py`,
and prior Windows handovers. Decision: reuse loading and model components;
fork a fresh shear case. The old `examples/SENS_shear` config names
`meshed_geom1.msh`, while only `meshed_geom1ses.msh` is present: do not blindly
execute the historical directory.

| Option | Actual installed source | Interpretation/readiness |
|---|---|---|
| Clamped single-edge-notched shear | `Scripts/brittle_fracture/INPUT_SENS.m` | Native MIEHE/AT2, sharp notch, E=210000/Gc=2.7, Ux=.015. Not interchangeable with normalized PIDL. |
| Simple plate horizontal displacement | `Scripts/elasticity/INPUT_SHEAR.m` | Bottom fixed, top Ux prescribed, top Uy free; differs from clamped SENS. |
| Tension | `Scripts/brittle_fracture/INPUT_SENS_tensile.m` | Existing AT1/AMOR normalized reference. |
| Three-point bending | `Scripts/fatigue_fracture/INPUT_TPB.m`; `Sources/+specimen/+internal/tpb.m` | Existing force-controlled bending setup, separate geometry/contact/support comparison required. |
| Mixed horizontal/vertical loading | `Sources/+phase_field/+fem/+bc/set_boundaries.m`; step params | X/Y displacements and tractions are supported. A mixed-mode case must explicitly define both components and supports. |
| Compression / reverse cyclic shear | BC primitives only | Do not infer qualified crack contact/friction or cyclic shear physics from available sign changes. Outside this first case. |

## Active decision and contract (revision 1, before execution)

**D2 active:** can the existing physics-informed NN reproduce the native FEM's
monotonic shear response and damage pattern? The mechanism is rotation of the
driving strain field and freedom for the crack to kink, while the material law
is kept at AT1/AMOR. No horizontal crack-growth or tensile mirror constraint.

- 1×1 domain centered at zero; retained material; initial crack segment
  x∈[-.5,0], y=0. Diffuse AT1 squared-distance profile with support 2ell.
- Plane strain; E=1, nu=.3, Gc=.01, ell=.01; residual stiffness=0;
  irreversibility penalty tolerance=.005; fatigue off.
- Bottom u=v=0; top u=U,v=0; sides natural free boundaries.
- Reuse historical PIDL shear schedule: .03,.06,…,.21,.24,.25,…,.46 (30 states).
  FEM native mesh `Dependencies/meshes/sens_mesh.m` Q4; PIDL uses the identical
  nodes with each Q4 split into two positively oriented T3 cells. Parent map
  and areas retained. This is a Q4/T3 comparison, not identical discretization.
- FEM retains native AT1 recovery penalty; PIDL retains its nonsmooth alpha
  map and three-point T3 irreversibility quadrature. These implementation
  differences remain explicit; do not attribute every discrepancy to NN capacity.
  In particular, T3 elastic/degradation energies use one-point centroid
  integration, while native Q4 FEM uses 2×2 integration; only the PIDL
  irreversibility penalty uses three points.
- PIDL 6×100 TrainableReLU seed1; existing log-energy/RPROP and weight decay
  1e-5; first-state LBFGS plus up to 10000 RPROP epochs per state; existing
  early stopping 5e-7. No FEM displacement/damage supervision.
- State0 is explicitly exported before any solve. Each state key is
  `(trajectory=shear-r1,U,step,post_solve_pre_history_update,support,channel)`.
  No fatigue-cycle mapping is imported from the tensile archives.

Primary descriptive observable: trajectory-mean area-weighted damage MAE on
the common Q4 cells over all states with accepted FEM output and a saved NN
candidate, with coverage and NN validity violations reported. No NN candidate
is removed to improve the score; an invalid candidate cannot support an
agreement claim. This clarification precedes any paired output. FEM nodal Q4
mean and area-weighted child-T3 means are declared
reductions. No ex-post binary accuracy threshold or superiority claim.
Diagnostics: direct top/bottom Rx, free-DOF equilibrium residual, E_el/E_d,
damage bounds/healing, forward damage morphology and selected matched-U fields.
PIDL reaction is sum of discrete nodal elastic internal forces at top DOFs,
obtained by differentiating E_el with respect to independent nodal u/v;
`2 E_el/U` is never substituted. FEM reaction comes from native assembly.
Raw/active AMOR energies, strain components and pre-update history retained.

Minimum output: explicit initial mesh/profile, per-state fields, scalar CSV,
source/runtime receipt and matched-U reaction/field plots plus README. Invalid
FEM states are not accepted. Incomplete/invalid NN states are reported as such;
an epoch limit is not convergence. Keep numerical status separate from errors.

## Bounded execution authority and resources

User request directly authorizes preparing and computing one shear FEM result
and its matching PIDL result. Conservative task-selected ceilings: one FEM
attempt ≤4 wall hours on `citpc12-ssh` (CITPC12); one PIDL attempt ≤4 single-GPU
hours on `gpu-server` (D-26-09); ≤10 GiB output per producer. These are ceilings,
not measured runtimes or additional authorizations for sweeps/retries. Stop on
nonfinite output, failed native acceptance, exhausted time/storage, or resource
conflict. No scientific retry or load/model change is silently allowed. At most
three short zero-start resource/environment rechecks within the ceiling.
Use fresh task directories, detached process and watchdog, immutable local
code snapshot; preserve shared installations/environments and other processes.
Independent read-only implementation review is complete; see code_review.md.

Resource coordination received from original research HQ at 22:25 UTC:
D-26-09 GPU0 is reserved for D5's authorized 40-epoch comparison. The earlier
idle snapshot does not admit this PIDL task. Hold PIDL launch until D5 exits
and the coordinated release is established; do not switch devices to bypass
the reservation. FEM producer has a one-experiment-at-a-time rule; recheck
MATLAB processes immediately before its launch. No reply/message to another
chat is sent by this task without human authorization.

## Decision ladder

| Step | Evidence / decision |
|---|---|
| D1 complete | Reuse native shear BCs + historical normalized PIDL loading; use AT1/AMOR in both. |
| D2 active | Review/validate the paired implementation, then execute one native shear trajectory and corresponding independent NN trajectory under resource admission. |
| D3 pending | Retrieve both; compare jointly valid U states, diagnose discretization/optimization/model differences; decide cyclic shear or another loading mode only from the result and new scope authority. |

## 2026-10-20 first-attempt outcome

R001 stopped at U=.03 after about31.22 supervisor seconds: final residual
assertion passed, combined damage-bounds/healing assertion failed. Accepted
loaded states 0/30; specific offending invariant was not exported. Initial
state/logs/code archive retrieved; no shear/FEM-PIDL agreement result exists.
See [run receipt](runs/S04-E035-R001.md). D2 remains active at reference repair;
R002 PIDL is prepared, not launched. No repeated attempt is implied.

The export-only diagnostic correction and bounded one-state proposal are ready
in [diagnostic_proposal.md](diagnostic_proposal.md), with fresh authority still
pending. Preserve R001, its consumed attempt and original thresholds. The
scientific verdict for the requested comparison remains inconclusive.

## R003 authority and local no-launch outcome

The original research HQ subsequently approved exactly the proposed one-state
diagnostic under its human-delegated night authority, adding 4CPU/16GiB RSS
limits and a total180-second envelope. Local resource-binding preparation
consumed148.92 seconds; the guard found only31.08 seconds left and stopped
before SSH. No R003 stage/worker/solve exists. The envelope was not reset.
See [R003 preparation receipt](runs/S04-E035-R003-preparation.md).

The single-call deployment is now assembled, with transport-failure receipts
and dirty-native source checks. It is preparation only pending a fresh execution
window; no additional scientific result, complete trajectory, or PIDL training
is claimed. The original shear comparison goal is unchanged.

## R004 diagnostic outcome and next decision

R004 retrieved the failing vector under the new900s total window. Both bounds and residuals pass; healing.00960853>.005 fails on250nodes, all on the initial fully damaged line. Independent recomputation confirms localisation and identical initial data. Accepted loaded states0/30; PIDL still not launched. See [receipt](runs/S04-E035-R004.md) and [prospective paired repair/resource proposal](repair_and_comparison_plan.md). D2 now awaits review/authority for the common hard initial-crack condition; no further solve is authorised by R004. Earlier pending-status paragraphs are historical.

## Prospective revision 2 — paired hard initial crack, 21 October BST

HQ-SHEAR-PAIRED-PRECRACK-20261020 (human_delegated_hq) authorises the proposed common alpha=1 condition on the existing251-node segment in both solvers, review, one full30-state FEM and—only if reference complete and HQ explicitly releases GPU0—one matching PIDL. Off-line initial profile, original material/load/penalty/tolerances unchanged. Contract family now shear-r2-hard-initial-crack. This does not replace or rehabilitate revision1 negatives.

Total new package hard8hours INCLUDING preparation, review, queue, both runs, retrieval, analysis and Obsidian. Conservatively count from23:17:49Z; stop07:17:49Z, earlier than HQ absolute07:50Z. Native/PIDL each≤4hours,4CPU,16GiB hostRSS,10GiB output including temp/archive; GPU allocated/reserved≤24GiB, physical free≥4GiB. First scientific failure stops whole package. One≤60s zero-start admission per producer. See authority_paired_precrack.json; older proposed extra1hour is superseded, not additive. First FEM state is production prefix, no new diagnostic/pilot.

## R005 zero-launch transport outcome

Revision2 implementation and full FEM controller passed independent review. Actual native boundary/DOF source and installed21MEX byte identities verified;3no-training checks and actualmesh masks pass. One upload succeeded but SSH start failed during banner exchange; readonly attribution confirms freshproducerroot absent,0actualadmission/0worker/0solve/0acceptedstate. The one mechanical submission is consumed and not reset; see [R005 receipt](runs/S04-E035-R005.md). D2 remains preparation-complete/transport-blocked; no new scientific inference, no PIDL SSH/training. No additional start is authorised by this report.

R005 control-accounting limitation: all remote identity/upload/start/attribution66.202s exceed60s mechanical envelope by6.202s; startpath53.700s alone was below60s. Required attribution lacked a remaining-mechanical-time clamp. Preserve this defect and costs; no scientific work or rerun.

## R006 active production under authorised recovery

HQ-SHEAR-R006-ZERO-LAUNCH-RECOVERY-20261020 allowed one fresh120s mechanical recovery with≥30s unknown-attribution reserve, retaining the original8h whole-package deadline and scientific attempt limits. Same reviewed numerical contract/source. R006 successfully created supervisor1696 and native MATLAB19184 at23:43:27.6983129Z. Initial status serialization over-expanded ETS metadata; its retained partial output already proved native activity. One compact monitoring check under the HQ existing-worker instruction recovered exact launch/root/commit ownership. No resubmission. See [R006](runs/S04-E035-R006.md);6loaded states written at first compact observation, full raw qualification pending. D2 is actively computing the full FEM reference. Science watchdog03:43:27.6983129Z; entire package07:17:49Z. No PIDL connection/training or GPU release.

## R006 result — six valid states, full reference stopped

The firstscientificfailure stopped this entirepairedpackage. Independent raw-array review confirms6/30accepted shearstates U=.03–.18 with original residual/bounds/healing checks, correctBC/history/reactions and251fixedinitialcracknodes. The revisedfirstpointmaximumhealing.000413357 is below.005 (priorR004.009608532 rejected); this supports the targetedinitialcrackrepair over the observedprefix only.

U=.21 failed displacementNewton at500iterations; finitefailedfields retained but finalresiduals notexported. Native653.213085swall/1.573311GiBpeak; all27files44,772,697bytesretrieved. No fullreference, no PIDLexecution or comparison; no secondscienceattempt. DecisionD2: preserve validprefix and newnegative; nextprospective design targets boundedmechanicalglobalization with unchangedphysicalcontract, see newton_globalization_proposal.md. Freshauthorityrequired; unusedoriginaltime is not a retry. D3pairedcomparison remains pending.

## R007 bounded mechanics — authorised preparation

HQ-SHEAR-BOUNDED-MECHANICAL-GLOBALIZATION-R007-20261021 grants one fresh full30-state attempt with the same revision2 physical contract. Only displacement Newton globalization changes: original AMOR tangent and cholmod2, residual-norm Armijo, full trial plus at most12halvings, at most500updates per mechanics call. Native PF/staggering and final acceptance criteria remain unchanged. Actual installed native line_search has an unbounded loop and is not enabled. See [frozen R007 protocol](r007_protocol.md).

The inclusive six-hour package deadline is conservatively06:10:00Z, within the original07:17:49Z deadline. FEM≤2h, each step≤600s,4CPU/16GiBRSS/10GiB root; one cumulative120s mechanical submission including25.517391s already spent reading actual helpers. Ten array-only MATLAB fixtures must pass before FEM within the single production process. No R007 worker/solve has started at this preparation record. First scientific failure stops the package; no R008 or automatic retry. Fullvalid30FEM and explicitHQGPU0release remain prerequisites for PIDL; GPU host has not been contacted for R007.

## R007 outcome — twelve valid states; package stopped

R007 crossed the previousU=.21stop and verified12/30states throughU=.28. U=.29 exhausted the600s step budget at79thouterstagger;78completedstaggers stillhaveprintedcombinedresidual.00023059. Savedunacceptedalpha_max1.0060855 exceeds1.005 on3nodes, finalPFresidualmissing. Nativeprocess1099.898947s/1.588GiBpeak. No completeFEM, PIDLexecution or pairedcomparison. Fullremotevectors retained; selectedprimaryfields/traces verified locally. See [R007 receipt](runs/S04-E035-R007.md).

Frozenlastcall's rawoktrue/exception contradiction and capturedcounterlabels are retained; localstatus/livecounterrepairs are preparationonly,11thfixtureunexecuted. Earlier12states independently require clean mechanics reports and unchangedfinalchecks. D2 nowneeds a new design/authority for outercoupledconvergence and damageovershoot; increasing inneriterations or clippingfields is not an establishedrepair. Existingfailedattempts/costs remain. D3pairedcomparison remains pending, and firstscientificfailure prohibits a newproducer or PIDL under this package.

Independentoutcomereview is complete; see code_review.md. The options, result and bounded next-decision plan are consolidated in [r007_outcome_and_next_decision.md](r007_outcome_and_next_decision.md). This plan creates no newattempt or training authority.

## Saved outer-coupling decision package — stopped before analysis

HQ-SHEAR-SAVED-OUTER-COUPLING-DECISION-20261021 authorised read-only existing arrays/source only. The first CPU guard failed during childpreexec before data analysis/RSSsampling; per explicit condition no repair/retry followed. A-vs-B mechanism and newintervention remainundetermined; no newscience or newfigure. See [failure record](saved_outer_coupling_decision_20261021.md). R007results/costs and no-R008/PIDL boundary unchanged.

## Saved mechanism analysis complete

Fresh user30min/120CPU approval: saved arrays/source analysed, same-equation PFglobalization/freshcertificate design reviewed, NOT executed. See [decision](saved_phase_mechanism_decision_20261021.md). Original failures/costs retained; noR008/PIDLauthority.

## Manav static-loading comparison — 2026-10-21

User requested the paper comparison before further computation. Complete local
arXiv v1 checked, including Fig.8/11/12 and Appendix G/I; see
[comparison and prospective recommendation](manav_static_shear_comparison_20261021.md)
and its single JSON reading record. Static shear is an appropriate benchmark;
current initial-condition handling, FEM penalty and NN setup differ from the paper.
The paper compares at Up=.4, explicitly reports FEM convergence issues above .4,
and shows NN-only extension at .47. A future contract should distinguish the
common reference range from an NN extension; this is a recommendation, not an
amendment of the stopped30-state package or its launch preconditions. Current
12 valid states, U=.29 failure and absence of PIDL results remain unchanged.
Literature/source review only; no producer operation or new execution authority.

## Direct user authorisation — published Manav static reproduction to U=.4

On2026-10-21 user requested the published article, alignment to its static
shear settings, a concrete budget and continued execution. This is fresh
authority for a new paper-setting protocol, not a revival of R007. The actual
published21-page PDF is present in project root (DOI10.1016/j.cma.2024.117104).
See [plan and budget](manav_static_reproduction_plan_20261021.md).
R008 FEM uses .001 irreversibility penalty and initial unloaded recovery;
prepared R009 NN uses .005,8x400/m0=3/seed1, analytic history without hard
crack mask, independent retained author T3 mesh and centroid quadrature.
Both use24common loads ending.4. Total12h ceiling ends00:20Z October22;
FEM3h, NN6singleGPUh,4threads/16GiBhost/20GiBCUDA/10GiBoutput each.
Onlyseed1 is included, not the paper's8-seed statistics. Public repository
links verified; exact current upstream code bytes not fetched due anti-bot
response. Localsource and mesh identities recorded. This permits necessary
checks/review and one fresh paired attempt; no silent retry/change of model.

### R008 execution result

FEM actually started onCITPC12 PID47368,11fixtures passed, then initial
recovery first PF direction exhausted the task-local residual Armijo trials.
Process15.3017841s/peakRSS1,717,030,912bytes; solver5.4858461s. No accepted
state, no loaded step, no PIDL. All24remote files/SHA256 verified locally.
This is failure of the added step-acceptance rule on this trajectory, not
evidence that the paper's native recovery or static shear physics fails.
See [R008 receipt and prepared recovery-only repair](runs/S04-E035-R008.md).
The one attempt is consumed; the prepared native-recovery alternative is
not deployed/run, and no newRunID has been minted. Original12hdeadline and
all old costs/results remain; no automatic scientific retry.

### User-authorised recovery repair — 2026-10-21

User explicitly approved exactly one recovery repair rerun within the original
remaining window, followed by PIDL and comparison only if FEM passes through
U=.4. New FEM R009 uses the reviewed recovery-only source SHA256
707ee43448a362b90b68484ec24c40fd79b1a8e485e1dcc021d351eab4313873.
Original deadline00:20Z October22 remains. Deduct prior15.301784 FEM seconds
from3h (new cap10784.698216s), carry prior9.18602854 admission seconds into
the same180s cumulative ceiling, preserve R008 and all older costs. PIDL R010
is conditional, capped by6GPUh and actual remaining time with retrieval reserve.
No new physics, clipping, load schedule, or loaded-solver change. Metadata-only
deployment adaptation carries forward the preparation review; no repeated
human confirmation is required for checks, submission or conditional PIDL.

### R009 outcome — recovery fixed; seven valid loaded states

The explicitly authorised repair ran onCITPC12 PID44308. Native recovery
passed;7/24loads throughU=.21 independently verified. U=.24 step8/outer1
PFNewton72 exhausted the remaining task-local residual line-search trials.
This is not evidence of native PF Newton failure. Candidate damage stayed
within the range/healing conditions, but no coupled certificate exists.
All50files/50,136,428bytes hash verified; process577.909939s/peakRSS1.582GiB.
See [R009 result and prepared integrated native-PF candidate](runs/S04-E035-R009.md).
FEM did not reachU=.4, so conditional PIDL R010 was not launched. Its source,
same-process environment and UUID-bound deployment are prepared only.
One repair attempt consumed; no further producer operation or new scienceRunID.
The original deadline and prior costs remain. Next integrated candidate
restores all PF Newton blocks, retains physics/criteria, and is unexecuted.


## 2026-10-21 18:54Z — prospective HQ native-PF authority

Verified actual human HQ turn `01a15fc9-e8c3-7410-995a-a57981d43556` resumes research-window management. HQ issued one new full native-PF repair; source `human_delegated_hq`, not direct_user and not reuse of consumed R009. R011 starts from initial state with reviewed full native-PF SHA e585ae62d7ca7cee321fe6d096f14909b86e01199e579b946168a1134b72f58a. No changed physics, mechanics or acceptance. One scientific start; first numerical/control/IO failure closes package.

Original deadline00:20Z unchanged. Prior process593.211723s plus conservative old remote-operation272.530373s and new admission180s are reserved from3h, giving new FEM cap9750s rounded down. CPU seconds remain unknown. Zero-start max2/180s (stricter than HQ300s). Original resource and single-step limits retained; PIDL R010 remains conditional on full24state validation and real GPU admission with useful whole-trajectory time before deadline minus1800s. Authority receipt: local_archive/experiments/S04-E035/manav_static_20261021/native_pf_authority.json.


### R011 remote admission stopped before scientific start

First SCP DNS resolution failed before upload (0.017989083s), no SSH launch command issued. The next transport required sandbox escalation; automatic approval review rejected it before command creation, stating consumed R009 permission and no accepted explicit permission for new remote FEM submission/code transfer. No workaround attempted. R011 remains prepared, scientific starts0/PID none; PIDL not started. Invocation retained without resetting its180s clock. See archive runs/S04-E035-R011/approval_review_stop.json. Explicit human approval for one new remote upload/FEM submission is now required by auto-review; original00:20Z deadline and cumulative costs still apply.
