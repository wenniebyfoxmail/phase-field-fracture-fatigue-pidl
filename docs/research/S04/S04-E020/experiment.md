---
storyline_id: S04
experiment_id: S04-E020
protocol_revision: 20261015-r1-delayed-decay
status: code-ready-producer-approval-pending
---
# Delayed learning-rate decay on the frozen E019 local residual

Question: under the same10000-new-update budget, can a fixed delayed-decay schedule reach the unchanged three-state UV accuracy requirement while retaining the local repair's damage/background quality? This is synthetic, same-state conditional supervised producer imitation (C1 diagnostic route), not future prediction or physical validation. Origin/target: own c20s4,c60s4,c83s4 peak, exact qualified fixed-damage UV-derived references. Damage/history/fatigue fixed. One already development-exposed trajectory and seed7; no holdout or cross-seed independence. Allowed information identical to E019, including fixed damage, exact E017backbone and original anchored geometry. No new states/data accesses.

Planning basis: E019 bounded external review (2026-10-15, ../S04-E019/evidence_review.md) gives PLANPASS for design, implementation and nontraining checks only. Human now authorises this preparation. Independent exact-source Code Ready and exact transfer/producer approval remain absent; no training may start from this record.

## Single factor and actual-update indexing

Candidate keeps original E019 localized architecture, homogeneous BC, coordinates/C2window, damage>.1strata, alpha.7, seed7, AdamW defaults,10000new updates, final-only. Only actual-update LR profile changes. Old E019 code remains byte-identical to ae238713. E020's train/CLI and numerical validator are explicit derivatives; original model, sampler, loss, reference/backbone admission and metrics are imported unchanged. Nonfinite-gradient guard only terminates invalid execution.

Let k=1..10000 be the actual parameter update receiving the LR. Set eta(k)=1e-3 for k<=8000; otherwise eta(k)=1e-5 + (1e-3-1e-5)/2*[1+cos(pi*(k-8000)/2000)]. Exactly2000decaying updates8001..10000. The2000tail values are committed as float.hex strings (tail_lr_hex.json), avoiding a second platform's libm rounding changing the frozen LR vector. Formula tests verify them; the versioned binary64values define actual use.

| Actual update | LR used |
|---:|---:|
|1|.001|
|8000|.001|
|8001|.0009999993893183533|
|9000|.000505|
|9999|.000010000610681646757|
|10000|.00001|

Order: compute finite loss; validate scheduler.before_update(k); backpropagate; check finite gradients; optimizer.step() once; scheduler.step() records the actual group LR just used, then installs eta(k+1). After10000updates next_lr=None, final reported/group LR=last used1e-5. Calling update10001 or out-of-order updates fails. No optimizer action during schedule unit tests. Save all10000used values in learning_rates.npy; its file hash plus vector digest/count/index convention appear in checkpoint, metrics and receipt; independent aggregator verifies all against the exact frozen vector. Passive stdout records lr_used/lr_next. No hidden extra update.

## Three candidates and archived controls

Only3fresh candidate Runs, one per c20s4/c60s4/c83s4. Each inherits10000E017backbone updates and trains a NEW zero-output residual for10000updates; never resume E019 final residual/optimizer. E019localized R002/R004/R006 final assets are historical controls, not rerun or newly selected checkpoints. New cost30000updates; control and inherited sunk compute explicit. No from-scratch/same-total-budget superiority claim.

control_locks.json binds each control's exact RunID, ae238713source, reference,5actual file identities (checkpoint, prediction, metrics,monitoring,receipt), full geometry, backbone lock/tensor digest, initial residual digest and completed sampling-index SHA. Historical admission verifies file identities, reloads actual model/backbone/buffers, predicts within1e-12, independently recomputes full/damage/background errors within1e-14. Geometry uses E019's existing recursive1e-14comparison (mass reductions can vary at~1e-16); actual lower/upper/center/scale buffers stay exact. Candidate initialization/backbone/geometry verified before update1; completed sampling digest must equal paired original, otherwise no valid result. Local nontraining streaming replay verifies all10000draws match in each state, without saving a giant index array.

Formal runtime must match locked original torch/numpy/CUDA versions, GPU type, hostname, physical visibleGPU and CUBLAS setting. Mismatch stops before update1, no fallback/recalibration. Code, optimizer, data and sampler changes beyond this reviewed schedule-only implementation are not an LR-only comparison. Producer must be fresh attributable Taobo roots on /mnt/data2, detached, clean exact reviewed commit, explicit GPU0 and :4096:8. No producer transfer/launch performed here.

## Admission and portability boundary

Do not rewrite E019's primaryFAIL, strictMacINADMISSIBLE or rho equality tolerances. Historical paired-asset admission is a NEW byte/parameter/UV-identity check, not a rerun or repair of E019's full checker. It reports old versus current reference_rho separately and does not demand that a historical secondary residual's floating reduction be a byte identity. Exact references remain hash-pinned. E020's own same-run numerical validator retains the original reference-rho comparison and may exhibit the same cross-platform exception; no E020cross-platform success is promised. A portability repair remains separately versioned/reviewed work.

## Criterion feasibility, diagnostics and stop rules

Primary: all3valid final-step10000candidate full massUVRMS/abs(Us)<=.001. Lower is better. Preserve original meaningful engineering target and reference uncertainty rationale; teacher rho~5e-11 is not a displacement error bound. E019already attains.000704/.000689 atc20/c60; c83.003238needs~69%further RMS reduction. Fixed-exterior lower bounds.00022221/.00024724/.00014483rule out only exterior impossibility. Late onset and c83direction-oracle.003103make this a plausible but uncertain optimisation diagnostic, not demonstrated attainability or convergence. No revised threshold if it fails.

Report damage/background conditional RMS versus BOTH inheritedE017 and paired E019localized finals, plus full/error contributions and passive trajectories. The inherited component finding requires damage decrease beyond1e-14 and background<=inherited+1e-14 for all3; keep it separate from primary. Schedule benefit insufficient if c83improves but remains>.001; c20/c60regression above.001 still makes jointFAIL. Background superiority over unrestricted remains unclaimed.

Complete all3valid rows before comparison. Nonfinite loss/gradient/output, reference/BC/model/geometry/source/runtime/asset/sampling/LR-integrity failure, OOM or producer resource failure stops affected run/dispatcher safely. No training-performance early stop, best-checkpoint selection, added seed/state, automatic retry/resume, budget extension, LR/schedule sweep, window/capacity change or other viewed-result branch. No broad process kill. Missing/interrupted required rows=>INCONCLUSIVE; failed validity=>INADMISSIBLE; complete admissible all-pass=>DELAYED_DECAY_THREE_STATE_UV_SCREEN_PASS, any primary miss=>...FAIL. Integrity takes precedence. Execution/retrieval/numerical verdict distinct.

If schedule helps but misses, record useful-but-insufficient and investigate residual learning dynamics/local coordinate conditioning as next separately reviewed diagnostic; do not automatically launch it. FullFEMteacher, coupled evolution, transfer and Stage2remain unqualified/unauthorised.

## Minimum evidence and review

Three fresh receipts, actualLRvectors, checkpoints/predictions, final and fixed0/1000/...10000regional/support traces, archived control locks/admission, runtime/source checks, table/decision figure for all3states versus archivedcontrols at.001 and field/profile views from exact scored arrays; README_analysis.md. Secondary strain/rho retained. Externally review exactsource before use and completed evidence before unconditional closure. Mac work in this task is nontraining only. Review package preparation is authorised; outgoing review and producer actions require their own exact human approval.

## Code Ready review completed 2026-10-15

Human-requested independent Codex subagent review gives CODE READY PASS bound to671fba2e48f1202bc2dd89f9800bacf1849477a0. Independently128nontraining tests,3real control reloads/regional recomputations,3complete sampled streams and33manifest entries verified; no blocker. Scientific protocol above unchanged. No candidate/CUDAtraining or final production archive tested; no transfer/launch approval. [Review](code_ready_review.md). Earlier preparation/pending statements are historical snapshots.
