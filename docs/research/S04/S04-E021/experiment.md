---
storyline_id: S04
experiment_id: S04-E021
protocol_revision: 20261015-r1-coordinate-preconditioning
status: completed-primary-fail
---
# Bounded residual-coordinate preconditioning — frozen pre-training protocol

Question: can one local-coordinate preprocessing rule improve the frozen-backbone residual correction under the same10000-new-update budget while retaining early/middle/transition-state accuracy and background? Synthetic same-state conditional supervised producer imitation, own c20s4/c60s4/c83s4 peak. Exact qualified fixed-damage UV-derived references, original E017alpha.7seed7backbones, frozen damage/history/fatigue. One exposed trajectory/seed, no holdout, predictive or physical qualification. E019/E020scientific verdicts and strict Mac failures remain unchanged. Human authorised implementation/nontraining checks and an internal Codexsubagent CodeReady review; producer transfer/launch not authorised.

## Single factor and controls

Control: exact archived E019localized R002/R004/R006 (ae238713), not E020. Existing ../S04-E020/control_locks.json reused as immutable historical-control identity, including five actual files perstate, reference/backbone/initialresidual/geometry/sampler/runtime. Do not rerun controls or resume residual/optimizer. Candidate retains8×283TrainableReLU, parametercounts564029residual/1688839total, Xavier/zero-output initialisation and seed7, alpha.7 (11469damage+4915background), full PCG64drawstream seed1000010, AdamWlr.001/betas(.9,.999)/eps1e-8/weight_decay1e-8/amsgradFalse/maximizeFalse and ORIGINAL E019nativecosine schedule. Only the local input-coordinate rule changes. Physicalsupport/window/taper/BC/frozenbackbone and full mass objective unchanged. Each candidate costs10000newupdates; inherited10000backboneupdates and historicalcontrol sunk compute remain explicit, no from-scratch/same-total-budget superiority claim.

For Q={damage>.1 AND original lower<=xy<=upper}, let e_i=mass_i*||UV_FEM−UV_backbone||², normalised overQ toq. μ=Σq_i xy_i, σ_j²=Σq_i(x_ij−μ_j)². Newcoordinates=(xy−μ)/s, s_j=min(s0_j,max(s0_j/4,3σ_j)). Fixed constants3and4, no sweep. Original windowcore chosen because small exterior residuals distort secondmoments; those errors remain fully scored. coordinate_maps.json freezes exact3maps, physicalgeometry and reference/backbone identities. Recompute rule from pinned archived backbone predictions/reference, check derived summaries at existing1e-14 tolerance, instantiate the locked local_center/local_scale binary64buffers exactly. Separate original physicalgeometry buffers stay unchanged. One composite mapping hypothesis; cannot attribute centring and scaling individually.

Targets are already available to both supervised methods; candidate uses them once in this explicit teacher_target_used preprocessing. Record map derivation time. This is not an estimator of future-state coordinates without the target and does not establish predictive value.

## Actual update LR and native arithmetic

Use torch.optim.lr_scheduler.CosineAnnealingLR(T_max=10000,eta_min=.00001) on the actual AdamW, exactly as E019. Order: validate LR/index before actual parameter updatek; backward and finite-gradientcheck; ONE optimizer.step(); native scheduler.step(); record LR USED, then expose next LR. Exactly10000actualupdates, no10001. Nominal eta(k)=eta_min+(eta0−eta_min)/2*(1+cos(pi*(k−1)/10000)), k1..10000; do not replace native recurrence with closed-form arithmetic or E020hold.

| Actual update | LR used, local metadata replay example |
|---:|---:|
|1|.001|
|1000|.0009758210072067898|
|5000|.0005051555088337877|
|8000|.00010462801334558344|
|9999|.000010000097709080377|
|10000|.000010000024427270673|

The AFTER-update10000schedulerLR is exactly.00001; next actual update isNone, not an extra step. The table is a MacTorch2.11metadata replay, not a Taobo measurement. Before first parameterupdate the same process replays nativeCosineAnnealingLR for10000LRs using an EMPTY parameter-free MetadataOnlyOptimizer whose step() always raises. It only advances scheduler metadata. The one expected warning about scheduling before optimiser stepping is explicitly captured/checked in this metadata-only replay; any other warning fails. No parameter/gradient/model exists in replay.

Freeze that producer's expected_learning_rates.npy and PRE_UPDATE.json BEFORE update1. Native wrapper checks every actual LR and scheduler index against this replay, stores all10000used values in learning_rates.npy, and asserts equality at completion. Checkpoint/metrics/receipt bind both files, mapping file and PRE_UPDATE hash. Passive0/1000/...10000records include lr_used/lr_next. Exact native recurrences are runtime-bound; formal torch2.7.0+cu126,numpy1.24.4,CUDA12.6,RTX4090,GPUServer8,visibleGPU0,CUBLAS:4096:8 must match original control beforeupdate1. No runtime fallback. This preserves original runtime-native arithmetic rather than forcing a Mac-generated portable LR table into E019's schedule.

## Pairing, pre-update admission and exports

Before first update: exactcleanreviewedsource and fresh output/archive, explicit CUDAproducer, /mnt/data2mounted/free>8GiB, GPU0free>8GiB; actual references, E017checkpoint/cache and five E019controlfiles admitted. CurrentCUDAbackboneUV must agree with savedUV at1e-12 and fullRMS at1e-14. Original initial residual/backbone/physicalgeometry digests match controls; new actual mapbuffers exact, zero-output fullUV equals evaluatedbackbone exactly. PRE_UPDATE records source/runtime, zero steps, original and full coordinate-model initial digests, expectednativeprofile, lockedmap and UTCbeforetrainingstart. Historicalcontrol file hashes checked again at completion, reference/backbone/pre-updatefiles unchanged. No reweighting or hidden damage/history update.

Outputs: final_step_10000.pt, prediction.npz, monitoring.json, metrics.json, learning_rates.npy, expected_learning_rates.npy, coordinate_map.json, PRE_UPDATE.json, RUN_RECEIPT.json; all eight payloads verified in separate producer archive, same receipt copied. Paths fresh under /mnt/data2/drtao/wennie/<run_id>, /mnt/data2/drtao/pidl_archives/<run_id>; logs/caches under taskroot. Caller must detach and redirect stdout/stderr to declared logpath, check current shared resources and preserve others' processes. No launcher/producer action in this task.

Aggregator independently reloads mapped model and checks actual physical/local buffers, base/initial/model/source/runtime/control/sample/map/LR/file/archive/pre-update identities, timing and zero pre-updatecount; independently recomputes UV, regional/support metrics, strain/rho and baseline at original tolerances. PRE_UPDATE/start/finish must be timezone-aware and ordered; receipt andmetrics times agree. Same-run numericalchecks unchanged. Cross-platform replay may reject nativeLRbits and/or reference_rho equality; preserve that result separately, never relax tolerances or call this a portability repair. Historical-control admission only proves pinnedbytes/UV identity and reports rho old/current separately; old strictfailures remain recorded.

## Criterion, interpretation, stopping

Primary: all3valid final-step full two-component massUVRMS/abs(Us)<=.001. RegionRMS conditions on damage>.1/background complement. Fulltarget unchanged; exterior lowerbounds below.001 are necessary only, no demonstrated capacity/attainability guarantee. Mapping changes the learned direction; E020failure does not prove a capacity ceiling. Report exact full/damage/background vs BOTH inherited and E019control; inherited and E019relative damage-improvement/background-preservation conditions reported separately (damage decrease>1e-14, background<=comparator+1e-14). Also report inside/outside-window background and exterior drift. Secondary strain/rho never rescue/veto primary UV result. Finalstep only, complete all3before routecomparison.

Nonfinite loss/gradient/passive/finaloutput, source/runtime/resource/reference/backbone/map/geometry/BC/LR/sample/archive/pre-update integrity failure stops affectedrun/dispatcher. No performanceearlystop, bestcheckpoint, resume/retry, addedstate/seed, extra steps, GPUfallback, LR/map sweep or post-result branch. Missing/interrupted rows=>INCONCLUSIVE; invalid=>INADMISSIBLE; all3valid allpass=>COORDINATE_PRECONDITIONED_THREE_STATE_UV_SCREEN_PASS, anyprimarymiss=>...FAIL. CLI exit2invalid,3incomplete,0complete (including scientificallynegative). Execution success and scientificclaim distinct. No Stage2/fullFEMteacher/transfer promotion.

If valid butmissed, retain any damage/background gain and inspect which state/component limits the result; do not repeat unchanged or mix per-state winners. Any further repair needs a separately reviewed design. An invalid result is diagnosed without automatically modifying/restarting the producer.

## Verification and next gate

See implementation.md and the tracked CLI/schedule/sampler/empty-matrix checks. Real nontraining controls/initialUV/maps and all3complete10000drawstreams checked; local full numericaldecoder positive/tamper cases use TEMPORARY SYNTHETIC completion envelopes and are not evidence of training. No actual E021candidate/trainedcheckpoint/GPUpreflight/producerarchive or scientificoutcome exists. Native replay localTorch2.11does not prove formalTorch2.7execution. Codexsubagent independently reviews exactcommittedsource/protocol/data locks/tests; only a bound CodeReady result can close this preparation step. Transfer, live producerpreflight and launch require the concrete final package and exact humanapproval.

## Code Ready outcome — 2026-10-15

Independent Codex subagent review PASS binds scientific source `98c620637b2b2ef06ec86983220a4e7f9f1053b7`: 162 nontraining tests passed, no skips. First source9b627979 was NO-GO because final candidate diagnostics were not independently recomputed; repaired E021 decoder rejects the same valid-hash tamper. All original tolerances and E019/E020 sources remain unchanged. See [review and remaining limits](code_ready_review.md). No producer access, transfer or training occurred. Future production must use the reviewed scientific source, not a later documentation commit, and an explicitly approved concrete run plan.

## Execution milestone — 2026-10-16

User approved exact v2 production package after the separate v1 initial-resource stop (zero training updates). V2 uses the unchanged reviewed science98c6206 and permits shared GPU0 with >8GiB free, with every other scientific/runtime/budget/stop rule unchanged. All-state formal CUDA preflight passed; c20 runner active and c60/c83 queued. No final scientific outcome yet. See [producer execution and provenance](producer_execution.md). Execution metadata does not amend the frozen scientific protocol.

## Final result and evidence closure — 2026-10-16

Original dispatcher completed2026-10-16T10:29:02Z. All three rows completed10000new updates and passed the unchanged producer decoder; original matrix3valid/0missing/0integrityerrors, scientific verdict COORDINATE_PRECONDITIONED_THREE_STATE_UV_SCREEN_FAIL. Final fullUVRMS c20=.0006606794692071773,c60=.0007864496867545542,c83=.0011678189737359475. Relative E019 changes -6.142079%,+14.211898%,-63.936596%; c60 retains .001 criterion but not E019 accuracy. Inside-background changes -1.642704%,+13.704084%,+6.823897%; saved outside-window UV unchanged exactly. See [decision](decision.md), exact paired CSV and [evidence review](evidence_review.md).

66files45560202bytes retrieved with all size/SHA checks;27rowfiles additionally match real producer archives. Reviewed scientific source98c6206 unchanged; v2 deployment4692b6a. All10000 actual LR entries match each row expected vector and formal preflight; maps, PRE_UPDATE, sampling and control identities admitted by producer. Strict unmodified Mac full replay remains0/3 INADMISSIBLE due native LR bits, with separate reference-rho portability exceptions retained. Independent saved-field/Q4-mass evidence review passed its bounded scope, not scientific or complete portability qualification. No retries, source/budget changes, external review or new training.

Next: six existing endpoint feature/output-head/regional-gradient diagnostic proposal only; see [next step](next_step_proposal.md). Implementation and diagnosis remain future work. Monitoring closes after evidence recording; no new producer action authorised here.

## 2026-10-16 — authorised read-only endpoint diagnostic completed

Allsix E019/E021 endpoints measured without optimizer/fitting/updates; independent code and evidence review complete. c60inside-background last-hidden features exactlyzero; c83 current regionalgradientcompatible, no demonstrated historicalconflict. Sourcec22376d, SHA1ef8da78, peakRSS723664896bytes; originalscientificFAIL/strictMacexceptions unchanged. [Diagnosis](endpoint_diagnostic_decision.md), [one proposed last-hiddenleak repair, unexecuted](minimal_repair_proposal.md).
