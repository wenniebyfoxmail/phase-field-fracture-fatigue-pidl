# D01 reference interface — working proposal, 2026-10-14

Status: local proposal and existing-output coverage audit; not a frozen new prediction experiment. E015/E016/E017 definitions, scores, annotations and human-preparation UI remain unchanged. No new annotator dispatch or external transmission.

当前工作定义见文末“2026-10-15 条件查询方案补充”：采用给定目标名义荷载L*的条件查询。较早的选择待定、计划可知性与执行顺序文字保留为历史，不作为当前条件查询的前置要求。仍未冻结新评估或授权执行。

## Decision to make

Recommended route: retain E015's **five-line-median transverse half-depth image width**, in first-frame native pixels within each beam. Treat central-row visible-edge AI/human annotation as a separate ambiguity/localisation check, not the truth for that width. This preserves the informative development signal without changing its meaning.

Alternative: predict central-row visible dark-boundary width. That requires a new protocol with the SAME definition at history, origin and target stages; old E015 predictions cannot silently become predictions of this new variable. User choice is pending. Neither route claims physical aperture in mm, fatigue state or phase-field damage.

## Existing data and exact missing work

Inventory sources: E015-D01-R001 `profile_measurements.csv` and `individual_forecasts.csv`; E017-D01-R001 `unique_task_comparison.csv`. No private answer key is needed. Supplemental audit: `S03-REFCOV-20261014-R001`, archive under `local_archive/diagnostics/`.

| Beam | Fixed-camera stages (kN) | Existing next-stage targets | AI crop-labelled stages | Targets without AI labels |
|---|---|---|---|---|
| 4 | 10, 30, 40, 50 | 40, 50 | 10, 50 | 40 |
| 5 | 10, 20, 30, 40, 50, 60 | 30, 40, 50, 60 | 10, 60 | 30, 40, 50 |
| 6 | 10, 20, 30, 40 | 30, 40 | 10, 40 | 30 |

All 14 stages already have 12 measured transects each. The current AI package checks only transects 3/6/9/12 at six first/last stages; its 24 unique crops include 16 visible and eight uncertain. Its three labelled final target stages therefore do NOT supply complete or same-definition reference coverage. Five intermediate target stages have no AI labels at all. For a visible-width route, history/origin coverage must also be added. Human reference in these owning records remains pending; no physical width reference is established.

## Minimal state interface to freeze before further prediction scoring

| Field | Current/proposed interpretation |
|---|---|
| `specimen_id`, `stage_index`, `nominal_stage_kN`, `transect_id`, `view_id` | Beam-stage-transect identity; fixed IB view only for this route |
| `measurement_definition_id`, `value`, `unit`, `valid`, `missing_reason` | E015 half-depth observable OR new visible-edge observable, never implicitly interchangeable; pixel unit per beam |
| `source_role` | observation / prediction / AI auxiliary / human auxiliary / qualified reference; region role crack/control stays separate |
| `available_through_stage` | Maximum input stage; origin-time eligibility must not use target visibility |
| `reference_available`, `reference_definition_id`, `reference_exposure` | Separate reference scoring support from deployment eligibility; uncertain is not zero |
| `next_load_availability`, `schedule_source` | Old code uses retrospectively indexed next nominal load. Origin-time schedule availability is assumed, not yet independently documented |
| `coordinate_frame`, `registration_source` | Per-beam first-frame native coordinates; retain stored registration provenance and its limitation |
| `evaluation_role` | All already-viewed beams are development; same-beam future continuation differs from new-beam generalisation |

These are proposed interface fields, not fields claimed already present in every old CSV. No synthetic timestamps, physical scale or qualified reference values may be invented.

## Smallest executable repair after choosing the observable

1. **Keep half-depth width (recommended):** first arrange an independent implementation/definition check on the unchanged native profiles and stored transforms, alongside blind visual ambiguity checks. This can establish reproducible computation of an image-defined observable, NOT physical width accuracy. Freeze origin-only eligibility and retrospective conditional-load semantics. Any new diagnostic rescore remains development evidence; physical/reference accuracy needs a separate matched measurement source.
2. **Choose visible-edge width:** prepare a new all-needed-stage blind package from unchanged first-frame transects, preserving uncertainties and no algorithm overlays. Freeze labels before joining outputs. New-context AI repeat reading is a procedural check only; qualified human/reference measurements and same-definition histories remain necessary for measurement or forecast validation. No new agent is dispatched by this draft.
3. **Future evaluation:** persistence versus secant, last two observed widths only, next declared nominal load conditional. One-step observation-updated predictions, not autonomous rollout. One primary comparison: beam-equal paired MAE difference on predeclared common support. Calibrate a meaningful margin from qualified reference/repeatability before formal acceptance; otherwise report descriptive differences, not a pass/fail threshold.

Do not add a neural model to solve a missing-reference problem. Preserve components separately: existing temporal signal, localisation robustness, annotation ambiguity, reference coverage and acquisition-time information. A missing reference limits what can be concluded, not whether the pipeline work was useful.

## Delivery and verification

The coverage script only counts existing outputs and validates their joins. It does not access pixels, detect boundaries, annotate, train, tune, read the private key or recompute forecast scores. Table and coverage figure are generated from the same rows; input SHA-256 hashes and code identity are recorded in `audit_receipt.json`. Generated data and figures remain local; compact summary may be copied to this directory after verification.

Completed 2026-10-14: the inventory assertions passed for 14 stages / 168 measured profiles, 24 unique AI crops, and eight existing forecast pairs. The PNG was visually inspected; PNG/PDF share a validated explanatory sidecar. Runtime 0.53 s on Mac (lightweight inventory only). All reference-qualification zeros are protocol/status assessments from these inspected records, not estimated numerical errors. No forecast score was recomputed. This script has not received independent code review and is not new measurement qualification.

- [Coverage figure](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/diagnostics/S03-REFCOV-20261014-R001/stage_reference_coverage.png)
- [Exact stage ledger](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/diagnostics/S03-REFCOV-20261014-R001/stage_reference_coverage.csv)
- [Source hashes and audit receipt](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/diagnostics/S03-REFCOV-20261014-R001/audit_receipt.json)

2026-10-15 decision: user chooses the recommended existing half-depth observable.
The choice above is no longer pending. [E018 independent computation/location
audit](S03-E018-D01/experiment.md) completed: reproducible computation, with
Beam4 local-correspondence risk selecting the next repair. This resolves the
observable choice, not the human/physical-reference or future-load-availability
gaps; visible-edge width remains a different, unselected target.

## 2026-10-15 read-only refinement — NOT a frozen evaluation protocol

This supplement updates the current plan without rewriting earlier decisions,
E015 scores, annotation answers or used protocols. Snapshot9112e549f15b8afc25628c08911ccfef48930025.
Only existing tracked records/code and the prior read-only memo were inspected;
no raw archive, sealed holdout, private answer key, new source download, script
execution, annotation, fit, registration, diagnostic or scoring in this review.
Shared Obsidian/Roadmap are left to the coordinating chat, unchanged here.

### A. What changed since the earlier review

| Item | Current evidence | What remains open |
|---|---|---|
| Observable choice | User selected retaining E015 point half-depth width; previous “choice pending” is historical | No switch to visible-edge or segment-median target |
| Same-definition computation | E018 independently reproduced all168 profiles/widths and raw-image quantised sampling exactly | Shared geometry/H are not independent physical coordinates or aperture truth |
| Background correspondence | E019 modest proxy improvement, typical paired width sensitivity change0 | Physical position correspondence unqualified |
| Spatial width response | E020 records spatial response and sparse half-level connectivity candidates, not disjoint-band switching | No-event is not physical smoothness or qualified width |
| Short support | E021 fixed4px median: typical paired sensitivity change0; individual stage amplitudes can be reduced | Do not substitute this support into E015 target/score |
| Stage differencing | E022 common offsets lower finite-grid RMS in35/36 original-H pairs | Common-offset assumption not achieved/verified physical correspondence;4pairs still flip |
| Independent human/physical reference | Owning records still human pending, physical false | Not created by AI agreement, independent code or arithmetic precision |

Sources: [E018 summary](S03-E018-D01/evidence/summary.json),
[E019](S03-E019-D01/evidence/summary.json), [E020](S03-E020-D01/evidence/summary.json),
[E021](S03-E021-D01/evidence/summary.json), [E022](S03-E022-D01/evidence/summary.json).
These are record checks, not reruns or fresh independent audits of archived data.

### B. Three different measurement definitions and reference roles

| Quantity | Unit/position/processing | Appropriate reference and allowed use |
|---|---|---|
| E015 half-depth image width, selected primary | Per-beam FIRST-frame native-coordinate pixels. Original fixed transect normal, normal offsets−60..60 at.25; gray values sampled at5 tangent lines−2..2 and median combined. Linear shoulder background, selected deficit peak within±15, interpolated half-depth crossings; width=right−left; original QC/censor rules unchanged | Same-definition future image operator value is the target for forecasting THIS observable. E018 independent recomputation qualifies software reproduction, not physical accuracy. Existing14stages×12=168 values available in records |
| Central-row visible dark-edge width, auxiliary/unselected target | Canonical crop pixel centresx0..120, central rowy24; human/AI visually chooses apparent left/right edges and ambiguity ranges; width=right−left. Display enlargement does not add spatial resolution; no five-line median or half-depth threshold | Independent human repeats/adjudication can qualify repeatability of THIS visual definition. E017 AI labels only auxiliary ambiguity evidence; disagreement with half-depth is not automatically algorithm error |
| Physical crack aperture, not established | Physical unit such asmm at a declared material location/load/acquisition condition | Requires suitable independent physical/calibrated measurement, visibility/geometry and repeatability evidence. A pixel scale alone does not turn the two optical definitions into physical aperture. No such qualified reference currently established |

Definition sources: [profile sampler/measure](../../../scripts/d01_crack_profile_diagnostic.py)
functions `sample_profile` L50–64 and `measure` L67–95;
[E017 definition](S03-E017-D01/experiment.md), [annotation interface](../../../scripts/d01_blind_edge_packet.html)
central row/display; [E018 boundary](S03-E018-D01/experiment.md), Outcome.

**Recommended first evaluation:** retain the unchanged half-depth image
observable and originalH as primary, not visible-edge width, segment median or
stage-difference target. Define the claim as prediction of a specified optical
measurement at a later declared observation/condition. For this bounded claim,
the same-definition target operator values plus independent computation checks
are relevant scoring evidence; it is unnecessary and incorrect to demand that
central-row human clicks become the truth for a different operator first.
Human/physical references remain necessary for their own accuracy claims.

This distinction removes a false prerequisite, not the actual limitations:
the eight existing outcomes are viewed DEVELOPMENT cases, not independent
future validation; material correspondence and origin-time load knowledge
remain unresolved. No new computation or rescoring of those eight is justified
merely because their unchanged operator was reproduced. A new visible-width
target would need a separate protocol and same-definition historical inputs,
origins and targets, not relabelling E015 predictions.

### C. Exact eight-pair reference inventory (metadata, not new scoring)

H=the two historical observations actually used by secant; O=current origin.
Every row evaluates T1…T12, not only the four visually checked transects.
“Operator available/reproduced” means E015+E018 software evidence, NOT
independent human/physical truth. AI coverage is crop inclusion, not a claim
that all included tasks are visible or qualified.

| Beam/pair | H (kN) | O→target (kN) | Transects | Same-definition target evidence | Existing AI visual coverage at H/O/target | Still missing for stronger claims |
|---|---|---|---|---|---|---|
| B4-1 | 10,30 | 30→40 | 1…12 | Operator available/reproduced,12target profiles | H10:T3/6/9/12;O30:none;target40:none | Independent coordinate/physical reference; human visual coverage if that definition is evaluated |
| B4-2 | 30,40 | 40→50 | 1…12 | Same,12 | H30/O40:none;target50:T3/6/9/12 only | Same; endpoint inclusion is not12-transect truth |
| B5-1 | 10,20 | 20→30 | 1…12 | Same,12 | H10:T3/6/9/12;O20/target30:none | Same |
| B5-2 | 20,30 | 30→40 | 1…12 | Same,12 | H20/O30/target40:none | Same |
| B5-3 | 30,40 | 40→50 | 1…12 | Same,12 | H30/O40/target50:none | Same |
| B5-4 | 40,50 | 50→60 | 1…12 | Same,12 | H40/O50:none;target60:T3/6/9/12 only | Same |
| B6-1 | 10,20 | 20→30 | 1…12 | Same,12 | H10:T3/6/9/12;O20/target30:none | Same |
| B6-2 | 20,30 | 30→40 | 1…12 | Same,12 | H20/O30:none;target40:T3/6/9/12 only | Same |

Pair/source evidence: [E015 aggregate prediction metadata](S03-E015-D01/evidence/forecast_metrics.csv),
[included stage list](S03-E012-D01/experiment.md) L14–25,
[prediction loop](../../../scripts/d01_crack_profile_diagnostic.py) L225–240;
[E018168-profile check](S03-E018-D01/evidence/summary.json).
Historical rows follow the two-observation slices in the code, not newly fitted
histories. Unique target stages8×12=96 software-reference measurements are
represented within the already reproduced168; no new values read/generated.

Endpoint package:24unique crops+6repeat views, six first/last beam-stage groups,
onlyT3/6/9/12. E01716/24unique representatives visually usable,8uncertain;
all six repeat pairs match quality and four visible pairs have identical
coordinates. These same-context/coarse-coordinate repeats do not establish
independent repeatability, zero noise, all-stage coverage or a half-depth truth.
Five intermediate targets have no AI crop labels; three final targets have
only partial, different-definition AI coverage. Neither fact erases available
same-definition operator values.
Sources: [E016 packet scope](S03-E016-D01/experiment.md),
[E017 protocol](S03-E017-D01/experiment.md), [summary](S03-E017-D01/evidence/summary.json).
No annotation answer table, duplicate key or sealed source was opened here.

### D. Human repeatability/adjudication plan — design only

1. Keep the existing24+6 endpoint packet and answers untouched. It can pilot
   visible-boundary ambiguity/repeatability; it is not the scoring set for all
   eight forecasts. Do not select clearer duplicates to replace uncertainties.
2. If human visible-edge evaluation is pursued, plan two independent readers
   with exposure recorded, identical definition/display and no algorithm or
   prediction overlay. Each first pass is frozen before comparison; no score
   feedback. Confirm actual availability, workload and identity before dispatch.
3. Use hidden repeats and a separated/re-randomised second reading to measure
   within-reader coordinate/quality differences; independent readers measure
   between-reader disagreement. Same-image rereads are not acquisition noise
   or material correspondence. Repeat count/spacing must be fixed before use;
   existing six pairs are only a small pilot, not a tolerance estimate.
4. Branch/spall/occlusion/indeterminate cases receive explicit reason and
   subjective endpoint ranges, not forced precise endpoints. A third expert
   adjudicates after initial annotations are frozen, blind to forecast scores;
   save original readings and adjudication separately. Unresolved stays missing.
5. Future same-definition human target coverage must match the declared
   T1…T12/needed-stage set; if visible width becomes the target, include all
   required histories/origins too. E018 independently verified half-depth
   values do not fill missing human visible-width observations, or vice versa.
6. Report denominator, quality agreement, paired repeat differences, drift
   and unresolved fraction before deriving any physically/decision-relevant
   tolerance. Do not infer tolerance0 from E017 identical answers. No numerical
   acceptance margin is prescribed without adequate reference evidence.

### E. Next-load availability: what is and is not established

| Evidence type | What inspected records support | What they do not establish |
|---|---|---|
| Released stop labels/workbook-derived mapping | Ordered included nominal stages and retrospectively matched image identities | A dated loading/photography plan available at each prediction origin |
| E012/E015 protocol calling next_load “scheduled” | An analyst-declared conditional problem | Proof that the researcher/operator actually knew that next included load/image stop beforehand |
| E015 forecast call | `loads[current+1]` comes from the complete selected-stage vector | Origin-time availability; absence of future image inputs alone does not prove this metadata was known |
| Filtered measured force/time tables, as reported by E004 | Recorded measurements,25Hz; nominal joins for nonfinal stops | Future actual force as an allowed input; exact synchronization or matching-error bounds |

Code provenance: [stage selection](../../../scripts/d01_stage_forecast_diagnostic.py)
L105–127 reads `load_stop_mapping.csv`, filters numeric/available labels and
sorts filename times; [forecast](../../../scripts/d01_crack_profile_diagnostic.py)
L98–104 and L225–236 passes the NEXT retrospective nominal label.
[E004](S03-E004/experiment.md) Evidence result records unsynchronised acquisition,
manual alignment and unavailable quantitative matching bounds; its old verdict
is unchanged. [E012](S03-E012-D01/experiment.md) narrows the question to nominal
stages, not exact force/seconds.

**Conclusion within this read-only scope:** no original, origin-available
load/photography schedule was located in the inspected local records/code.
This is not a claim that no such document exists anywhere in the full release;
original archived PDFs/tables were not reopened and nothing new was downloaded.
Need a source/page/field explicitly documenting intended load AND observation
stops, applicability per beam and availability before each origin. The next
included image stage after filtering is not automatically the next planned stop.

Until that provenance exists, separate two candidate questions:

- **Retrospective condition-query diagnostic:** estimate optical width at an
  explicitly supplied nominal loadL*. It is valid to state the condition is
  supplied retrospectively/hypothetically; do not call that verified deployable
  next-load knowledge. Preserve old eight-pair interpretation in this category.
- **No-known-next-load continuation:** target the next declared observation
  event without a next-load input; retain persistence. A stage-index increment
  rule may be a separately designed comparator, not the load-normalised E015
  secant. Unequal Beam4 gaps preclude silently assuming equal kN increments.
  No seconds/cycles/actual-future-force horizon is invented.

Seeking author/source clarification would be a separate proposed action; this
review sends no message, form or file externally.

### F. Minimal evaluation contract to freeze later

| Item | Proposed definition (unfrozen) |
|---|---|
| Claim | Single-step, observation-updated prediction of the declared half-depth optical width, not physical aperture/road transfer/autonomous rollout |
| Origin and horizon | Per eight-pair ledger, only past/current observations available; known-plan next nominal stage only with source proof, otherwise explicit retrospective condition-query or separate next-observation question |
| Information | Original first-image geometry and admitted past/current transforms/widths; no target pixels/transforms/visibility, future measured force or reference labels in predictor/eligibility |
| Target/reference | Frozen original operator and evaluation-only target transform; software-reproduced target values. Human visible width is auxiliary unless a new target is explicitly chosen; physical truth is a separate claim |
| Baselines | Persistence and unchanged load-secant only for an admissible specified-load condition; half-secant stays secondary diagnostic, not selected post hoc. For unknown next load, do not reuse load-normalised secant under a renamed interface |
| Evaluation unit | Per-transect errors averaged per forecast pair, within beam, then beams equally; disclose all denominators/three beam results. Existing beams/outcomes remain development; new same-beam states test continuation, new specimens assess transfer |
| Primary | Paired loss difference versus persistence on predeclared common scoring support; no acceptance threshold until a meaningful comparator/uncertainty/decision margin exists. Without one, descriptive result only |
| Origin eligibility | Derive before target access: fixed origin-selected transect, both historical widths finite/QC-admissible, allowed coordinate/information support. Generate/store every eligible prediction BEFORE testing future reference availability |
| Future scoring support | Independently flag target identity/operator validity/reference availability after prediction freeze. Score all arms on the same support; missing not zero, no best-variant or clear-case replacement. Report eligible, predicted, reference-available and scored counts/reasons separately |
| Prediction missing | Retain failure/abstention counts, not only conditional loss. Predeclare any selective/deployment penalty policy if needed; do not invent a target value or risk score for unobservable targets |
| Validation role | Existing8cases may audit a new bounded development repair, not become fresh holdout. Prospective frozen predictions/new unseen evaluation data needed for independent validation; no reusing inspected outcomes as confirmation |

One code-level issue for a FUTURE implementation: current E015 L226 computes
support over `widths[current-1:current+2]`, including target measurability,
before calling the prefix-only predictor. Existing168/168valid and96/96scored
records mean no observed support loss in that run, but this structure must not
be described as origin-only deployment eligibility. Split origin eligibility
from scoring support in a new reviewed implementation; this review changes no
code or old result.

### G. Dependency-ordered next work

1. Approve the narrowly bounded image-observable claim and reference roles;
   do not reopen the selected target solely because auxiliary visual labels differ.
2. Resolve whether load/observation plan is provably known at origin. If not,
   explicitly choose retrospective condition-query or a new no-known-load
   formulation before defining the final predictor interface.
3. Freeze/qualify relative-position correspondence support or its uncertainty;
   E022 gives a controllable lever, not proof it is already achieved. Keep
   cases sensitive even under common offsets in the evaluation population.
4. In parallel, prepare human visible-edge repeatability/adjudication only
   for its declared ambiguity/physical-measurement questions. It is not a
   substitute half-depth truth and not a mandatory relabelling of all images
   for a purely operator-defined forecast.
5. Specify new evaluation identity/exposure, origin mask, post-prediction
   reference mask, same-support baselines and primary comparison. Independent
   validation requires genuinely uninspected/prospective targets; all eight
   existing cases are development. Freeze any meaningful acceptance margin
   only once justified; otherwise retain a descriptive diagnostic.
6. Obtain reviewed final protocol/code and exact single-run approval before
   any new implementation execution. This document dispatches no annotator,
   creates no packet, accesses no sealed data and launches no calculation.

## 2026-10-15 条件查询方案补充——未冻结，仅文档

### Material Passport

- Origin Skill / Mode: academic-research-suite / experiment-agent plan；道路裂缝证据边界。
- Origin Date: 2026-10-15；Version Label: conditional_query_working_v1。
- Verification Status: UNVERIFIED（新方案未执行／未验证，不否认所引历史记录）。
- 文档基线：a9444bef1c3049b42d85c8a5b1dfe08d853c314d，原匹配工作树。
- 本次只读来源／代码并补充此草案；未运行训练、拟合、预测、评分、配准、诊断或测试，未改代码或历史协议，未下载或读取答案键／封存数据。共享Obsidian/Roadmap及跨聊天消息均不在本次修改范围。[CQ1]

本节更新的是**未冻结方案**，不追溯改写E015–E024。此前G.2“先解决下一计划荷载可知性”的要求，仅适用于升级为计划已知的前瞻预测；不再阻塞本节已选定的条件查询。下一步仍须另行冻结新评估与实施范围。[CQ1,CQ5,CQ8]

### 1. 可直接使用的研究问题定义

本研究考察受控钢筋混凝土梁试验中的半深度图像宽度条件查询：对同一梁、同一固定测线，给定截至观测起点的历史半深度图像宽度、历史名义荷载，以及外部明确指定的目标名义荷载L*，估计该荷载条件下同一定义的图像宽度，并与保持当前宽度的基线比较。观测量保留原单点测线、五行中位灰度剖面及半深度交点定义，单位为各梁首帧原生坐标像素。L*是查询条件，允许由分析者事后指定；这不证明该值在真实试验的预测起点已经可知。现有结果属于受控梁试验上的回顾性开发研究，不构成自主下一观测预测、物理开口预测、荷载干预因果效应或真实道路验证；八次已查看结果的身份与原评分保持不变。[CQ1–CQ5,CQ7,CQ8]

条件估计保留已观察历史及本数据的单调加载分支。不同加载路径或未观测内部状态可能在同一L*下产生不同图像；不假设L*唯一决定状态，也不声称最近两点已经是充分状态。[CQ1,CQ2,CQ5]

### 2. 信息表：两个时点与三种角色

区分“历史观测截止到阶段k”与“分析者构造查询的时点”。本任务允许事后构造查询，故L*在**调用时**明确给定，不要求其在当年试验起点已有记录。历史字段可用性按j≤k约束；原始标签的实际可获取时刻没有证据时标为未证实，不补写真实时间戳。[CQ1,CQ4,CQ8]

字段名是拟议接口，不声称旧文件已全部具备；质量和几何元数据用于测量／资格／追溯，不新增为secant数值特征。[CQ2,CQ3]

| 角色／拟议字段 | 内容与可用时点 | 可进入哪里 | 来源 |
|---|---|---|---|
|历史 `specimen_id, view_id, transect_id`|同梁、固定IB视角、预先固定测线；截止k的身份|分组和来源核对，不把测线当独立梁|CQ2:prepare；CQ4；CQ5|
|历史 `width_history`|j≤k同定义算法宽度；本两基线只用最近两次，px|数值预测器；不得以可见边界或物理开口替换|CQ2:50–104；CQ5；CQ7|
|历史 `measurement_definition_id, unit`|原单点、五行中位剖面、半深度交点；首帧原生像素|约束输入／输出同定义；定义版本在新目标前冻结|CQ2:50–95；CQ5|
|历史 `valid_history, missing_reason_history, origin_valid`|仅由首帧及j≤k历史剖面产生的有效性、对比度／截断等原因|起点资格；不把目标质量填入历史标志|CQ2:67–95、132–155；CQ3|
|历史 `nominal_load_history`|j≤k已经纳入历史的名义荷载；真实当时获取时间未证实时另标状态|数值预测器；不以未来实测力替换|CQ2:98–104；CQ4；CQ8|
|历史 `center, normal, coordinate_frame, ROI_source`|首帧确定的路径、中心、法线和既有ROI，之后不按目标重选|历史测量／追溯，不新增预测参数|CQ2:132–155；CQ5|
|历史 `historical_transform, registration_source`|只允许计算截至k历史观测所需的变换；其输入也不得含j>k|历史测量端；预测函数本身不接收H|CQ2:50–64；CQ3:182–216；CQ6,CQ7|
|查询 `query_nominal_load_kN=L*`|外部在调用时指定，可以事后／假设性指定；保留给定来源|条件输入；绝不自动命名为起点已知下一计划荷载|CQ1；CQ2:98–104；CQ8|
|查询 `query_role, supplied_by, selection_exposure`|记录是回顾性条件查询、如何选L*、目标是否已被看过|追溯／分层；不把事后选择包装为盲评|CQ1；CQ4；CQ5,CQ8|
|仅评价 `target_stage_id, target_nominal_label`|依据已声明规则核对目标记录是否对应L*|评价端匹配；不能按预测误差挑图|CQ4；CQ8|
|仅评价 `target_image, target_transform`|目标图像及其测量变换，可以在评价端用于同定义取值|不能进入预测器或起点资格，也不能参与历史变换拟合|CQ2:50–95；CQ3:196–216|
|仅评价 `target_valid, target_missing_reason, reference_available`|目标身份、取样支持和算法有效性；预测保存后判定|未来参考可测性与评分支撑，不是起点掩码|CQ3:223–240；CQ5,CQ7|
|仅评价 `target_halfdepth_width_px`|目标图像上同一固定测线／定义的算法值|计算误差；不是独立物理真值|CQ3；CQ5,CQ7|
|仅评价 `target_actual_force, future_logger_time`|未来机测力／记录器数据，如确有来源才用于评价匹配审计|不替代L*、不补历史荷载、不作为预测输入|CQ6；CQ8|
|仅评价／修复线索 `posthoc_position_diagnostic`|E023/E024若使用目标阶段残差或宽度响应，只是事后开发诊断|不得转作该起点的资格；T4/T6/T10优先级不是盲选验证集|CQ9；CQ10|
|禁止填入 `internal_damage, future_event, unobserved_state`|模拟内部损伤、未来事件或其他未观测状态|不补输入、标签或缺失值；无来源保持未知|CQ1；本节问题定义|

`planned_next_load`不是本问题的L*别名。将来使用该字段时，必须另带计划来源、版本、适用梁、起点可获取性和跳过规则；本节不伪造这些字段已经存在。[CQ1,CQ8]

### 3. 原基线、输出与两个掩码

**不改方法。**在原允许分支L*>L_k、L_k>L_(k−1)下，persistence保持w_k；原secant使用最近两点荷载斜率估计L*处宽度。两者继续沿用原函数的[0,120]px输出映射，不加单调增长、再平滑、参数拟合、ROI重选或新边界条件。原half-secant仍是固定辅助，不择优替换主对照。函数的`next_load`参数在本草案中解释为L*，本次不重命名代码或改变公式。[CQ2:98–104,CQ5]

**掩码一：历史起点资格E。**仅依据已固定测线／首帧资格、两次历史同定义宽度有效性、历史荷载顺序及允许的历史信息截止点判定。L*的域检查是显式查询校验，不读取目标可见性。E成立后，未来实现应先产生并保存各臂输出、输入快照、L*、截止点和预测失败／弃权原因，再允许评价端检查目标。[CQ2,CQ3,CQ5]

**掩码二：未来参考可测性R。**预测保存后，按冻结规则核对目标名义条件／身份、同定义取样与算法有效性。目标缺失、不确定或不可测保留原因，不置零，不以人工其他定义、其他阶段、未来实测力或模拟状态补填。[CQ3,CQ5–CQ8]

共同评分支撑由E、R及两臂均成功输出的交集导出，不能让各臂挑不同目标。分别报告：名义查询数、E成立数、每臂预测／失败数、R可用数、共同可评分数及分原因缺失。条件MAE不掩盖覆盖率／弃权；若需失败惩罚或决策效用，应另行预定，而不是本轮虚构。[CQ3,CQ5；前文F]

旧评价循环在调用预测器前就把目标可测性加入support；现有记录中168/168有效、96/96可评分，因此不能仅据结构问题断言旧数值已被改变。但旧循环不能被描述成已经实现上述两掩码接口。本次只指出未来实现的分离要求，不改代码或旧分。[CQ3:223–240,CQ5,CQ7]

任意给定L*都不自动拥有可评分图像。若未观测该名义条件，应记录“该条件无目标参考”，不能插值一个真值、换成最接近且有利的图像或把生成值当参考。[CQ4,CQ8；本节评价设计]

### 4. 已有依据、当前待补项与升级证据

| 状态 | 已有依据／待补内容 | 对当前条件查询的意义 | 来源 |
|---|---|---|---|
|已有|原论文§2描述预定义荷载停点；§4描述固定相机各停点图像|提供实验加载／观测设计背景；不单独证明八个精确下一事件在起点已知|CQ6；CQ8|
|已有|同梁IB历史名义标签和已查看目标；旧八查询身份固定|支持回顾性条件查询，不是新的独立验证|CQ4,CQ5,CQ8；前文C|
|已有|原同定义算法目标及E018独立计算／取样重放记录|支持软件定义量可复算；不证明物理开口或材料位置|CQ2,CQ5,CQ7|
|当前待补|新接口的逐字段来源、历史截止点、查询给定记录和两掩码实施|未来评估必需；旧代码未因此被宣称已经修好|CQ2,CQ3；本节2–3|
|当前待补|目标的固定名义身份／相机／测线／变换来源及缺失规则|足以定义注册图像坐标中的同一函数；真实材料位置仍需独立资格|CQ3,CQ4,CQ7–CQ10|
|当前待补|未冻结评估的案例身份、暴露记录、共同支撑、独立参考安排、主比较与合理阈值依据|不能由已看结果选有利阈值；无依据时仅描述，不强设物理门槛|CQ5；前文C/F；本节5|
|升级前瞻所需，不阻塞当前A问题|每梁事前计划的版本／来源、起点可获取记录、跳过停点或遗漏照片后的目标选择规则|只有升级到“计划已知的未来预测”时才作为额外要求|CQ1,CQ4,CQ6,CQ8|
|升级物理／其他观测所需，非算法量的替代真值|同材料位置的独立物理／几何参考；若评价可见边界需自己的标注定义和重复性|人眼可见宽度、物理开口和半深度函数分别评价，不混用|CQ7；前文B/D|

**位置与状态对应。**同一个测线ID表示同一冻结坐标定义，并不证明跨阶段同一材料位置。源图像映射、局部位移、背景到裂边的空间转移、法向误差、模板匹配及相机／记录器时序仍有限制。E023有限网格和E024背景代理帮助定位修复重点，但不能替代物理对应，也不要求所有位置先通过物理计量才允许陈述算法定义量的回顾性条件查询。[CQ6–CQ10]

### 5. 未来评价安排——仍未冻结

- **现有八查询：**B4为30→40、40→50；B5为20→30、30→40、40→50、50→60；B6为20→30、30→40kN；每查询T1–12。它们都已查看，保留原身份／评分，可用于方案梳理或另行批准的开发复查，不能成为新holdout。当前没有新增预测或评分。[CQ5,CQ8；前文C]
- **新评估身份：**在目标访问前，冻结梁／视角／测线／历史截止点／L*／目标来源／曝光角色，以及重复图像和缺失时如何选目标；不能按误差、未来可测性或E024事后分类选有利案例。新同梁状态只支持同梁续推；新梁才可研究跨梁迁移，仍不等于真实道路。[CQ4,CQ5,CQ9,CQ10；前文F]
- **主比较候选：**在共同支撑上比较secant相对persistence的配对MAE差，方向为负较好；沿用“测线→查询→梁等权”解释，报告各梁／各查询及覆盖率，不把96个条目当96个独立梁。等梁平均像素误差只是既有软件观测量的比较，不代表统一毫米精度。它是待冻结的新评价设计，不改旧聚合公式或分数。[CQ5；前文F]
- **阈值和独立性：**有合理误差／重复性／决策依据再定最小有意义差异，否则描述差值、不造通过线。预测和输入快照先固定，再由独立评价过程读取目标并计算同定义参考；真正独立验证需未查看／前瞻目标，不能靠换一个评价agent清洗已查看身份。[CQ7；前文C/F]
- **可用数据待定：**本次不访问封存目标、不联系或采集新数据。若只有旧八查询，下一次任何重算也只能叫开发复查；若计划独立验证，先明确可合法使用、此前未查看的具体数据来源和权限。[CQ1,CQ5,CQ8]

### 6. 最小下一步，按依赖顺序

1. **以本节已选A问题及不变项继续完善草案，不等待事前计划证明。**历史截止k、外部L*、原半深度函数／像素、persistence/secant、回顾性开发身份已在本节写清；事前计划证据仅列作B问题升级事项。[CQ1,CQ2,CQ8]
2. **下一项文档工作：冻结案例与信息来源清单。**逐行注明历史源、L*给定方式、目标名义对应、曝光角色及缺失规则；旧八对沿用前文C，不解封或新增数据。没有对应图像的L*保留为无评分参考。[CQ3–CQ5,CQ8]
3. **再冻结两掩码与评价分工。**写清E的历史字段、预测保存点、R的评价字段和共同评分／失败分母；不得用E023/E024目标信息倒筛起点。代码实现需后续另行授权。[CQ3,CQ9,CQ10]
4. **选择下一次工作的证据角色。**若重用已查看资料，明确开发复查；若要独立验证，先确定未查看或前瞻数据及独立同定义评价流程。当前不能凭“换agent”制造新独立性。[CQ5,CQ7；前文F]
5. **最后才是审核、授权和一次有界执行。**新实验ID／版本、命令、预算、停止条件及有依据的主比较阈值由后续方案决定；本次不生成或运行命令。局部对应／分数位置复算若有必要，单独列为候选诊断、等待批准，不暗中纳入本任务。[CQ9,CQ10；本节权限]

本轮不存在必须靠计算才能完成的文档项。需要新计算才能回答的是“新两掩码实现后的结果如何”及“代理指向的分数位置是否真的敏感”；候选路径分别是新冻结开发复查与固定小范围位置响应复算，均**未执行**。[CQ3,CQ9,CQ10]

### 7. 本节来源索引（全部为现有本地材料）

- **CQ1** 用户指定的[问题定义与荷载核读备忘录](/Users/wenxiaofang/Documents/Codex/2026-10-13/corotational-fem-dem-for-multiscale-and/outputs/S03_load_availability_and_question_20261015.md)，§1–4；本轮只读，不改外部聊天文件。
- **CQ2** [原半深度取样／测量函数](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp/scripts/d01_crack_profile_diagnostic.py:50)：L50–95定义；L98–104数值预测及clip；L132–155首帧几何准备。只读代码，没有运行其中self-test或任何函数。
- **CQ3** [原评价循环](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp/scripts/d01_crack_profile_diagnostic.py:182)：L182–216目标测量；L223–240原support与预测／评分顺序。
- **CQ4** [原回顾性阶段选择](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp/scripts/d01_stage_forecast_diagnostic.py:109)，L109–127：按数值／匹配状态选择、按文件时间排序，非起点计划证明。
- **CQ5** [E015已使用协议与原结果](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp/docs/research/S03/S03-E015-D01/experiment.md)，Frozen method / development result；本次不改其“scheduled”历史用语或数值。
- **CQ6** [原论文既有文本](/Users/wenxiaofang/phase-field-fracture-with-pidl/research_proposals/topology_crack_metrology_HQ_20261006/sources/metrology/sjolander_2023_dib_dataset.txt:210)，§2（L210附近）、§3（L267附近）与§4（L358附近）；本轮仅重读这些相关段落，不新增全文／附录验证声明。
- **CQ7** [E018独立计算复核记录](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp/docs/research/S03/S03-E018-D01/evidence/summary.json)，168同定义剖面复算、原图重放及physical_accuracy_validated=false；只读现有记录，不重跑。
- **CQ8** [E023荷载来源核查](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp/docs/research/S03/S03-E023-D01/evidence/load_knowledge_review.md)及[八查询来源字段](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp/docs/research/S03/S03-E023-D01/load_knowledge.json)：三采集表的具体单元格、主文依据与未读附录范围；本次不重开工作簿或新下载。
- **CQ9** [E023有限相对错位协议](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp/docs/research/S03/S03-E023-D01/experiment.md)，finite grid / Outcome：无连续位置或物理精度保证。
- **CQ10** [E024切向背景代理记录](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp/docs/research/S03/S03-E024-D01/evidence/summary.json)及[协议](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/crackmnist-tokenizer-mvp/docs/research/S03/S03-E024-D01/experiment.md)，代理类别、开发优先级及未执行的分数位置下一步；不转成新预测验证。

## 2026-10-15 八案例来源清单与两掩码实施约定 v1（待审核，未运行）

本次承接上述§6第2–3步。任务为S03条件查询接口准备；复用匹配工作树与分支，基线885f85ac0004be7013a454a9a3806021d0b1f0b7。仅新增机器可读[案例清单](d01_conditional_query_cases_v1.json)、本节和既有Obsidian里程碑；不改旧代码、协议、宽度、评分，不读取新图像／封存目标，不启动预测或位置复算。该清单是**拟实施的开发重放输入约定**，不是新数据验证结果，也不宣称已获独立审核或Code Ready。

### 案例清单：不是重新选样

| 案例 | 最近两次历史名义荷载（kN） | 给定L*（kN） | 原固定目标文件（Gx-IB_t=秒.JPG） |
|---|---|---|---|
|B4-K1-Q40|10,30|40|G4-IB_t=500.JPG|
|B4-K2-Q50|30,40|50|G4-IB_t=588.JPG|
|B5-K1-Q30|10,20|30|G5-IB_t=464.JPG|
|B5-K2-Q40|20,30|40|G5-IB_t=553.JPG|
|B5-K3-Q50|30,40|50|G5-IB_t=636.JPG|
|B5-K4-Q60|40,50|60|G5-IB_t=729.JPG|
|B6-K1-Q30|10,20|30|G6-IB_t=376.JPG|
|B6-K2-Q40|20,30|40|G6-IB_t=460.JPG|

八案例均展开为T1–12，共96个**名义查询×测线机会**；不是96个独立梁，亦不是本次新确认96个有效预测。JSON中列出14个阶段的原文件、零基阶段索引、历史两行键、首帧几何文件、E015同定义宽度表和E023逐个目标标签单元格。表和JSON沿用E012预先保存的选择，不新增B4的20kN，不择优替换目标或测线。所有E/R状态仍记`not_recomputed`。

路径解析：JSON的`sources`中档案路径相对`archive_root`，`*_repo`相对本工作树；`stages[].image`相对`raw_image_root`，`target_label_source`工作簿相对`workbook_root`，斜线后为表／单元格定位。`filename_time`只用于文件身份，不当作精确相机—力传感器同步。历史每行的名义标签／图像身份沿用E012清单；不补造物理试验起点时间戳。首帧几何沿用E015-R000，宽度行键固定`beam,stage_index,transect_id,role=crack`，唯一性异常即停止连接。

### 实施边界：先输出，再读取评价目标

整个JSON包含未来评价定位，**不得直接传给预测器**。未来实现必须先投影成仅含历史与查询字段的白名单payload；历史读取截至k，原两基线只取k−1、k。身份元数据不作为新增拟合特征。

| 时点／支撑 | 可读取字段与判断 | 必须落盘／报告 | 禁止行为 |
|---|---|---|---|
|历史资格E|首帧固定测线资格；两次历史同定义宽度有限且有效；同梁／单位／几何定义相符；历史荷载递增|每个名义机会的E与所有失败原因|读目标宽度／可见性／H或E024类别筛起点|
|查询域Q|显式给定有限L*且L*>L_k；不是目标可测性|L*值、给定来源、Q与原因|用未来实测力替换，或看目标后改L*|
|预测输出P|仅E∧Q的历史payload；原函数persistence、secant与[0,120]px映射不变|每臂输出或异常／非有限值原因；输入与输出先固定|等R后才预测、删失败条目；把整份清单交预测器|
|参考可测性R|只在输出固定后接入已列目标；同名义条件／同梁视角、固定图像与算子，目标值有限且有效|可测／缺失／歧义及原因；保留无参考的预测|就近荷载替换、插值真值、人工别定义宽度补填|
|共同支撑C|E∧Q∧R∧P_persistence∧P_secant|相同条目的配对误差；另报各臂成功覆盖|不同臂用不同参考／分母，或只报条件MAE|

Q显式单列，避免把查询参数不合法和未来无参考混为一谈。E/R是两个数据资格掩码，P是各臂执行状态，不新增科学成败标准。原conservative_secant如展示仅为既有固定辅助臂；它的失败不改变主两臂的C，单独报告其支撑，不能挑它替代主方法。

分母按梁／案例完整报告：N=12；N_E；N_(E∧Q)；每臂在E∧Q上尝试／成功／失败数；在E∧Q上N_R与分原因缺失；N_C。失败原因可多项并存，须另报互斥终态计数使其与N相加一致，不把多项原因之和伪称总缺失。没有E∧Q案例也保留空记录，MAE记不可计算而非0。

主比较保持描述性：在C上先测线平均绝对误差，再案例平均、梁等权；报告secant−persistence的配对MAE差（负值更好）和每梁／案例明细。若任一梁没有可评分案例，三梁等权总比较记不可计算，不静默删梁改权重；各梁可计算部分仍展示。无新显著性或物理精度门槛，不以旧52.408%结果反推成功阈值。该结构不追溯修改E015的旧结果。

### 最小代码验收与下一计算（计划，非已执行）

下一项实现只修正信息流／报告，**不改测量和基线**。首先用合成记录验收：改变或删除目标字段不改变E／预测；预测输出先于评价读取；缺目标保留预测且R=false；任一臂失败在共同支撑中同时退出并保留失败数；不重复键／不跨梁／不把缺失记0；不接受目标派生的历史资格。需检查历史H来源不含后续阶段，缓存全序列只允许连接层使用，不能充当预测payload。

之后独立代码审核应绑定精确代码与本清单版本，再为**旧八案例的一次开发重放**登记新Experiment/Run、固定命令与预算。届时才计算新两掩码报告与旧数值一致性，并配全部八案例的同尺度对比图；不训练、不扩数据、不筛T4/6/10。若确有差异，先定位行键／映射／数值原因，不通过调公式追平旧分。当前完成的是来源和信息边界，尚无新计算结果；T7/T9分数位置诊断仍是独立候选，未混入此任务。

这次为非数值准备：上方案例表与时点决策表是最小可视结构，结果曲线不适用。来源是CQ2–CQ5/CQ8所指代码／协议，加E012-R001既存选择JSON与E015-R000几何文件身份；未将旧实验的结果数值作为本次新输出。
