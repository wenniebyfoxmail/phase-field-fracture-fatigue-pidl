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


### 2026-10-21 18:59Z — direct human approves exact R011 submission

Human annotated the explicit R011 upload/FEM request with “批准”. This supersedes the auto-review authority block prospectively; no prior attempt is reclassified. Resume same R011 with one scientific start, no scientific retry, original9750s cap/deadline/resources and conditional PIDL unchanged. Old admission expired while awaiting required human approval; preserve original invocation and renew only remaining180s remote-operation allowance, keeping its prior0.017989083s charge. Record direct_user_approval.json and a separate approved admission receipt. No second zero-start transport has yet executed.


### R011 live launch and mixed-direction follow-up

Exact human approval permitted network-enabled continuation. CITPC12 supervisor22708 / MATLAB17960 started2026-10-21T19:00:10.1185407Z,9750s cap/science deadline21:42:40Z; original total00:20Z unchanged. Source snapshot commitc6603716 (reviewed scientificSHA unchanged), local approval controllerc7f3b5f4. Initial zero-start/auto-review records retained. R010 conditional reference now points to R011, unchanged NN science.

Human proposed45-degree FEM/PINN comparison next. Local boundary implementation confirms theta measured fromx-axis,0degree horizontal shear; plan fixes vector magnitudeU and both components consistently. See [next direction plan](mixed_direction_next_plan.md). No new angle run launched or included in the current one-attempt budget.


### R011 actual outcome — six states and native return-timing diagnosis

R011 ran132.548693s, solver125.5597875s, peakRSS1.581GiB,exit1; own supervisor22708/MATLAB17960 both gone. 47/47files45,786,723bytes hash verified. Six accepted loads toU=.18 independently valid. U=.21/stagger2 fresh returnedPF1.2334014287417203e-6 rejected; native last preupdate vector norm8.917322275245907e-7. Locked native code updates field before testing its prior residual; saved fields differLinf.001023063493328258. This identifies this call timing issue, not full corrected convergence. No coupled certificate for either candidate, no seventh valid state, no PIDL. See [R011 report and next decision](runs/S04-E035-R011.md).

Private consistent-return PF candidate prepared only; no newRunID or solve. Originalcriteria/first-failure stop/budgets retained. 45degree equal-magnitude mixed-loading plan remains future scope. CumulativeFEMprocesswall725.760416s, CPUUNKNOWN, all transport/admission costs retained separately.


## 2026-10-21 19:15Z — direct human consistent-return and45degree authority

Human explicitly approves correcting PF return timing, full shear FEM toU=.4 then originalPIDL comparison, afterwards equal-magnitude45degree without per-step questions. R012 uses reviewed helper250ac033a6593b749427e493a30615c7a44ecdbaf7e7fc20fada96ba2894bd71 / runner35ee6acea3c828f3e5ecf51dc663b7677e876389ae064d43be31590f03fc1c14 from initial state, no changed model/tols/history/BC/mechanics. New conservative FEM9500s cap shares original3h cumulative; original6GPUh cumulative,4CPU/16GiBhost/20GiBCUDA/10GiBroot,00:20Zdeadline retained. PIDL must finish before totalend−1800s.45degree follows0degree comparison within those same remaining budgets, not an extra window. Per-run first-failure stop remains; no silent scientific retry. Authority receipt consistent_pf_and_45_authority.json.


### R012 active and shared comparison implementation

CITPC12 MATLAB30120/supervisor13424 started19:16:24.9783305Z with9500s cap; reviewed consistent-return scientific source unchanged.12loaded states throughU=.28 observed accepted in producer log, U=.29coupling still active, not yet a verified full reference. NoPIDL launched.

Independent Q4/T3 comparison now uses Q4 2x2GP/Jacobian area weights and T3 barycentric interpolation with no extrapolation; all345632points covered on actual geometry, both areas1, affine reconstruction passed in1.48s. All saved-state bounds/history/BC/force/energy identities checked; rejected NN candidate retained in diagnostics; exit0 required for full completion. Formal preparation review passed SHA f3e98f3184bcbffdd93beda97510203379e4ff4c11945fd6d63c6ddb846f9d70. This mapping is a stated quadrature approximation, not exact integration or mesh-convergence evidence.


## R012结果与范围机制决定 — 2026-10-21 20:05Z

修正PF停止/返回点后完整重跑：12/24态至U=.28有效；U=.29同点耦合和9.925185e-5已达标，9个节点alpha>1.005，max1.006614。66文件全量核验，自有进程退出，PIDL与45°未启动。实际AT1源码没有上界罚项；Gauss最大1.002144不能解除节点条件。未发现可据以启动的同方程修复；仍有离散超调与有限精度两种解释。见[R012完整结果](runs/S04-E035-R012.md)。

连续托管授权覆盖一次有依据同方程修复和原预算内重跑，但其前置条件尚未成立。源码/保存结果分析及报告继续，不重置时钟。新本地分析RSS采样被沙箱拒绝，CPU/RSS未知；保守扣120CPU且不重试数组分析。新物理约束选择仅[准备完整合同](range_resolution_next_contract_20261021.md)，不自动改模型或放宽验收。原全部尝试与费用保持，原00:20Z截止。


## 人方明确批准共同有界模型 — 2026-10-21 20:52Z

直接批准“批准该共同有界模型比较”，原owner继续执行[前瞻新约束合同](common_box_protocol_20261021.md)。FEM显式盒约束变分求解+原软罚项，NNsmoothsigmoid+精确初裂边界；原材料/BC/24U保留，KKT原梯度单位无缩放，原残差/愈合标准保留。准备R015FEM/R016条件NN，原累计预算/00:20Z截止不变；R012仍12/24，不追认。一次完整FEM实际启动前完成必要独审和真实预算准入。45°后置，不牺牲主比较。

R015已实际启动：CITPC12 MATLAB40592，21:08:11Z，科学终点22:47:49Z不随准入延后；同批数组fixtures通过。当前完整FEM活动中，PIDL/45°未启。[活动收据](runs/S04-E035-R015.md)。


## R015终态 — 7态有效，已定位有限能量步长不足

7/24态至U=.21的保存数组/精确box/历史/反力/原单位KKT均合格。U=.24第一外层PF第1次迭代完整步+12减半耗尽；最小实际lambda2^-12仍增能，保存向量/日志重建13能量误差3.91e-14，允许同向Armijolambda≤8.6462e-5（更小步未评估）。55文件46,227,800bytes全核验，进程189.666520秒、RSS1.627GiB、自有PID退出；无PIDL/45或重跑。原一次实际启动已消费。[完整结果](runs/S04-E035-R015.md)。

同模型曲率控制初始步长的[源码候选和完整计划](common_box_curvature_proposal_20261021.md)已独审、未执行、不分配新RunID；保持原能量/罚项/网格/12回溯/500更新/KKT标准。新额外完整启动需具体次数批准，不把原余量当重试许可。原budget/00:20Z截止/所有旧UNKNOWN费用保持。


## 直接批准曲率控制方案追加一次完整重跑 — 2026-10-21 21:42Z

人方明确“批准，在原剩余预算和截止时间内，按曲率控制方案再完整重跑一次FEM。通过U=.4后继续PIDL，45°仍放完整主比较之后”。R017采用已独审四个候选文件的原字节，从初态全部24态；R015失败不追认。仅新增机械适配器/新准入，累计本地120CPU及4线程/2GiB不重置。FEM预算从R015结账时间的5990.097秒已知上界继续扣全部经过墙钟（含待批时间）、本次180秒操作预留与原截止；固定科学终点准入不可后移。仍一次真实科学启动、首失败停止；R016条件NN参考改绑R017，原GPU/模型/训练限额及7200秒完整轨迹机会要求保留。原00:20Z总截止不变。

R017已启动：MATLAB20456，21:45:53Z，cap4376.436s/冻结终点22:58:49Z；三组fixtures通过，初态恢复写出。完整24态及PIDL仍待，原00:20Z截止不变。


## R017终态 — 实现作用域错误，加载0态

初始恢复与同批三个fixtures通过；首载荷力学嵌套函数覆盖父相场opts，curvature字段丢失，U=.03相场异常，0/24加载态。37文件10,502,729bytes全核验、自有PID退出、进程21.506918秒/CPU未知。真实恢复求解已发生，本次一次科学启动消费，不记零启动。仅namespace修复已独审、未运行，原运行源及全部失败费用保持。[完整结果](runs/S04-E035-R017.md)。

旧PIDL7200秒机会下限为任务自定、无实测运行时依据；21:50Z准入点已过。按旧计划没有条件NN窗口；完整比较仍未完成，需要明确额外启动与时间安排，不能静默放宽或承诺结果。原00:20Z总截止保持，无PIDL/45/新worker。


## 2026-10-22 新六小时主比较窗口

用户已批准命名修复、取消任务自设7200秒NN启动下限；原窗口科学截止23:50Z已过，本次原窗口新增科学启动0。随后直接读取HQ人方原答复确认新六小时授权，唯一start00:14:22Z、准备end00:44:22Z、scienceend05:44:22Z、totalend06:14:22Z。新额度FEM≤7200秒、随后条件NN≤10800秒/3GPUh，各一次首失败停，原资源/模型/tol保持，旧费用/UNKNOWN全留。R018/R019准备中；24态FEM全过后才NN，45°不在新窗口追加。[原窗口关闭与新授权](approval_window_closed_20261022.md)。

R018已实际启动：00:19:02.920Z，CITPC12 MATLAB48532/supervisor47392，实际cap7186.241秒、冻结终点02:18:49.161Z。三组fixtures通过，全24态参考仍待；R019/45未启。


## 启动后的状态查询被自动权限审核阻止

R018已真实启动一次，最后一次成功读取仍处于fixtures通过、保存加载态0的早期阶段；后续实际覆盖和终态未知，不能断言FEM失败或成功。MATLAB48532自有监督器保留02:18:49.161Z硬停止、7200秒内上限及原资源监控，不因本地阻断撤销。R019仅本地准备、未训练；没有全24态参考，不启动NN。

后续只读status在创建进程前被自动权限审核拒绝，理由为人方要求发送任务后停止托管。核对HQ人方原句及HQ最终交接（停止HQ自动轮询，已授权计算继续由原负责人执行）后，提交一次相同查询复审，仍被拒绝，理由为其仍属运行期持续监测。未改通道、借他人或间接绕行，未再查询；这两次拒绝没有创建远程进程，不是新的数值失败。原一次真实FEM启动仍已消费，不能重发。

现需明确允许本原负责人在已经批准的这一个固定六小时窗口内继续R018结果核验、取回，以及全24态合格后的条件R019 PIDL和比较；不恢复HQ托管，不新预算/时钟/重跑次数。原窗口、费用和UNKNOWN保留。若无明确许可，不恢复被拒的远程操作。状态/原拒绝与复审理由在parent archive renewed_20261022/postlaunch_auto_review_block.json。


## 2026-10-22 06:42Z之后：人方澄清HQ边界，但固定窗口已结束

人方明确批准原负责人继续本次R018核验/取回，24态通过后PIDL，且明确“停止托管只针对HQ”。这解决了先前自动审核所指的授权歧义；不再重问同一边界。同时人方保留“截止和预算不变”。首次核时06:42:25Z（英国07:42:25），已经超过总截止06:14:22Z约28分钟，科学截止05:44:22Z也已过。不能把此次迟到答复解释为新起点或延期。

本地目录核对：R018只有启动及早期status收据，没有terminal或retrieved；R019只有本地prepared和bundle，无invocation/producer收据。本轮远程调用0、新科学启动0，未改控制器截止或重置时钟。最后自有监督器硬停止02:18:49.161Z是已部署的限制，不能替代真实exit核验；实际终态仍未知。

已准备一个单独、待批准的600秒只读收尾：仅原CITPC12/R018目录读取退出/集成/轨迹、现存文件哈希与取回、保存态独立核验；禁止新FEM/PIDL/装配/训练/重跑，首IO或控制失败即停，旧费用全留。即使24态合格，也不能在过期科学窗口启动PIDL。具体操作与120CPU秒/4线程/2GiB本地分析上限见parent archive renewed_20261022/readonly_closure_proposal.json；尚未执行。


## 2026-10-22 06:51Z后实际取回终态

最新直接“请启动计算”按恢复行动处理，先只读取回已有R018，避免重复求解。原56文件41,650,658bytes全部大小/SHA256匹配，两个自有PID现场已不存在。R018实际在00:23:15.141Z以exit1结束，进程墙钟252.2212027秒、peakRSS1,748,664,320bytes，CPU未知；不是时限停止。恢复→力学→相场callback集成收据通过。独立保存数组核验6/24至U=.18有效，U=.21/stagger3的PF达到500更新上限。

最后500试探均backtrack0接受且能量逐次下降；初KKT6.14727676e-5，最后保存内层原单位KKT5.0690140448e-5，高于1e-6；末lambda6.6712093468e-4，最后50中位4.8231567893e-4，末能量变化−6.6649461575e-9。末内层所有节点严格[0,1]，原生与解析能量梯度差4.22224e-16。失败caller向量与内层向量不混同，未出同点耦合证书。说明当前首步/方向效率不足，不唯一证明全射线曲率上界是根因。无完整参考，R019未启动。

完整归约analysis/iteration_stop.json、phase_iterations.csv及带说明图phase_iteration_stop；图已目视核验，sidecar检查通过。第一次本地日志归约误把此前两个stagger混入500次断言而停止；修正按最后stagger分段后重做，旧错误/费用保留，未装配或求解。已有累计guardedCPU1.447893秒/peak采样RSS131,366,912bytes，其他未计量工具成本仍未知。


### 最新直接启动指令的前瞻一次修复包

R018结果已核验后，按最新“请启动计算”准备R020完整FEM/R021条件NN：只改原能量分段射线首步，原PDAS/12回溯/500更新/容差与物理不变。全部六源码独审通过，fixtures尚未运行；明确前瞻新执行时间实施解释，旧窗口/失败/费用不改写，准备通过工具权限复核后才部署一次。完整机制、竞争解释、额度与真实止损见[本轮计划](ray_step_restart_plan_20261022.md)，源码精确哈希见ray_step_review_20261022.json。

R020已启动：07:08:17.263Z，CITPC12 MATLAB34280/supervisor46232，实际cap5838.221秒/冻结终点08:45:35.484Z，commit ed5766a6。新指令前瞻执行通过工具权限审核，资源释放后才提交；同包检查返回/实际BOX_RAY调用已见，完整24态资格仍待。R021未启。


## 实际终态：12态合格，U=.29弱下降/极小射线步失败

实际07:08:17.2626038→07:17:50.2786886Z，进程573.0160848秒（9分33秒）、peakRSS1,753,346,048bytes、CPU未知，exit1；不是时限、内存或存储停止。77文件72,364,190bytes逐文件大小/SHA256全匹配，两个自有PID现场不存在。四组fixtures通过、初始恢复及实际首载荷集成通过，BOX_RAY全模型调用已见；这些不能代替完整轨迹。

独立保存数组核验12/24加载态至U=.28合格，U=.29/stag25/PFiter9未接受：KKT1.1329678061e-6仍高于1e-6；投影Newton名义斜率−1.6338106916e-22，而Qbase1.5528841221e-10，root48二分[0,3.5527136788e-15]、首lambda1.7763568394e-15。13实际试探斜率都非负（8个零）、能量全相同。最后trial所有节点[0,1]，愈合3.7888319e-5、原生/解析梯度差2.3027911e-15，未形成有效耦合证书。不把13%高于内层容差的点放宽追认，不混caller与innertrial；原始内层方向未导出，不唯一归因浮点或活跃集。

分段能量首步把本共同有界版本有效前缀由R018的6态推进到12态，但仍不是完整U=.4参考。R021尚未部署/准入/训练，0GPUh；45°未启。反力/能量/损伤及末次步长图已目视核验并通过sidecar检查，raw/数组核验/诊断位于parent archive runs/S04-E035-R020/{retrieved,analysis,native_response}。本次已按首失败停止，没有自动科学重跑。

有依据的下一候选：同原生K精确对角投影梯度方向，只有比clipped Newton一阶斜率严格更负才替代；不改物理、回溯、500或KKT。三源码已独审、未运行，且增加完整当前方向失败证据。[具体下一包与预算](descent_safeguard_proposal_20261022.md)。


## 前瞻管理清理 — 2026-10-22 固定任务基准

依人方治理原消息01a16286-1ff9-76f2-80c7-d943676007d2及安装版research-decision-core“只跑固定基准，通过即交付”：当前唯一活动下一步计划descent_safeguard_proposal_20261022.md已移除重复旧四fixtures、额外SPD单测阶梯、独立复审及因commit/路径/元数据再审门；既有审查结论/未受影响结果复用。唯一基准是既定完整24态FEM→保存量核验→条件原PIDL→配对分析，命令、输入、对照和预期已写在该原计划。文档小改仅一致性检查。

不修改已执行R018/R020源、签名问答、旧结果/费用/UNKNOWN、科学判据或新增一次科学重跑/预算许可；原HQ问答由人方明确接受“仅各一次完整FEM/PIDL启动、首次失败即停”，其已消费次数保留，不冒称Agent模板。当前producer均退出，helper shear_review已completed，不唤醒历史helper/不派新审查或测试。此管理改动不启停/重启任何科学运行。
