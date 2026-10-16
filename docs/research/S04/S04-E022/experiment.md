---
storyline_id: S04
experiment_id: S04-E022
protocol_revision: 20261016-r1-last-hidden-leak001
status: production-package-awaiting-approval
---
# Last-hidden fixed-leak discriminator

Question: does replacing only the local residual's eighth hidden activation improve c60/c83 UV fitting without losing early-state/background accuracy? Exploratory synthetic same-state conditional supervised producer imitation; one exposed trajectory/seed, no holdout/forecast/physical-teacher claim. E021 endpoint evidence identifies exact c60 background last-layer zeros; c83 remaining-error mechanism remains a hypothesis. Original E019/E020/E021 verdicts and strict Mac portability exceptions remain unchanged.

## One factor and frozen lineage

Only residual.activations[7] changes from relu(coeff*pre) to leaky_relu(coeff*pre,negative_slope=.01). Reuse its original learned coeff Parameter; no added parameters, RNG draws or initial tensor differences. First seven actual TrainableReLU classes/coefficients and all architecture/parameter counts unchanged (residual564029,total1688839). Activation manifest lists all8layers, expressions/index/slope/coefficient keys; bound in PRE_UPDATE/checkpoint/metrics/receipt. Strict loader reconstructs actual activation and rejects wrong/missing manifest. Tensor digest alone cannot identify this behavior.

Candidate starts afresh from original E017alpha.7seed7backbone and original matched Xavier/zero-output residual initialization; no E021/E019 trained residual/optimizer resume. E021 teacher-derived coordinate maps reused unchanged. Same physical geometry/window/taper/BC, FEM reference, damage/history/fatigue freeze; qualified fixed-damage UV subset only, full teacher NOT_QUALIFIED. Zero-output initial UV equals backbone; leak has no effect on initialized output despite changing hidden features.

Exact c20s4/c60s4/c83s4 peak references and own backbones. Direct comparator: each E021 v2 localized row pinned by nine-file e021_control_locks.json, source98c6206. Common task comparator: each E019localized R002/R004/R006 using unchanged ../S04-E020/control_locks.json. Historical controls not retrained. Match formal runtime exactly (Torch2.7.0+cu126,NumPy1.24.4,CUDA12.6,RTX4090,GPUServer8,GPU0,CUBLAS:4096:8) AND candidate native10000LR vector to original E021 actual vector BEFORE update1. Otherwise stop; no runtime fallback. Thus direct paired interpretation is conditional on passing these frozen-runtime/asset controls, not proof a concurrent randomized treatment pair. Actual producer preflight still future work.

## Objective, sampler, budget and actual LR

Unchanged two-component full-domain mass UV squared objective, unbiased damage>.1 strata, alpha.7:11469damage+4915background draws perbatch, seed7+1000003=1000010 PCG64, damage_then_background_no_shuffle; all10000drawstream must match historical digest. No loss reweight/leak sweep/state selection.

Each candidate10000NEW parameter updates, residual only, same AdamWlr.001,betas(.9,.999),eps1e-8,weight_decay1e-8,amsgradFalse,maximizeFalse; inherited10000backbone steps/historical sunk compute explicit. Original native CosineAnnealingLR(T_max10000,eta_min.00001), read LR before updatek, finite backward, exactlyone optimizer.step, then scheduler.step. Nominal formula eta_min+(.001-eta_min)/2*(1+cos(pi*(k-1)/10000)), k1..10000; native recurrence retained. Actual examples .001 at1,.0005051555088337877 at5000,.00010462801334558344 at8000,1.0000024427270673e-5 at10000 (formal/runtime exactvector is authoritative). Post-final scheduler reaches1e-5; next actualLR=None, no10001. Before first update parameter-free replay writes expected_learning_rates.npy; record each actually used rate in learning_rates.npy; arrays exactequal, allreceipt/CP/hash/index checks inherited.

## Decision and stop rules

One primary criterion unchanged: all3valid finalupdate10000 full massUV RMS/abs(Us)<=.001. Same earlier qualifiedUV benchmark; no newly estimated physical tolerance, no threshold relaxation. Regional RMS uses conditional mass normalization. Damage/background/insidebackground gains and c20/c60E019 preservation are separate component outcomes against inherited,E019,E021; activation restoration alone is not success. E021c83=.00116782, existingdiagnosticshows fixingbgonly insufficient; leak is a discriminating repair, not an attainability guarantee.

Allthree fixed states complete before comparing route. Score finalstep only, record0/1000/...10000passive traces; no bestcheckpoint/earlyperformance stop. Nonfinite loss/gradient/output or identity/source/runtime/nativeLR/geometry/BC/backbone/reference/map/activation/sampling/pre-update/archive/resource failure stops row/dispatcher, no retry/resume/budgetincrease/GPUfallback. Fresh attributable producer directories and explicit visibleGPU required; /mnt/data2 mounted/free>8GiB and GPU0free>8GiB; any sharing policy belongs to later approved producerplan. No other process interference.

Integrity errors->INADMISSIBLE(exit2), missing->INCONCLUSIVE(exit3), all3valid anyfullmiss->LAST_HIDDEN_LEAK_THREE_STATE_UV_SCREEN_FAIL(exit0complete), allpass->...PASS(exit0). Secondary strain/rho never vote on primary. Damage progress/background preservation flags computed separately vs both controls. If activation pathways recover but UV still misses, retain negative result and reconsider bottleneck; no automatic next experiment.

## Evidence, checks and authority

Reuse E021 runner/strict decoder without changing old source; new E022 code validates trained leaky reconstruction and candidate full numerical metrics at original tolerances. Nine outputs perrow incl PRE_UPDATE/nativevectors/map, separate real archivecopies. Historical byte/UV admission preserves E021/E019 strictMacfailures; localTorch2.11native bits differ formal, reference-rho differences remain reportonly for historicalidentity. Same-run candidate checker is unchanged strict; no Mac portability exception waiver.

Before production: exact CodeReady commit + reviewed runtime/pairing/activation manifest + concrete producerplan. This task authorizes implementation and nontraining checks/internal Codexreview only, no training/transfer/SSH. Temporary synthetic completion envelopes in tests declare fictitious step/runtime metadata; no optimizer parameter step, not producer evidence. For the local positive decoder fixture only, reference_data direct-rate expectation is explicitly synthetic Mac-native metadata; production prepares that value from original formal E021 files and rejects a different vector. Tests must separately show that mismatch rejection and production precheck failure on Mac.

Minimal assets: exact three-state pairing/admission JSON, tests/CLI/LR/samplerchecks, independent source-bound CodeReady report; after any future actualrun, preciseUV/componenttables, decisionplot/README, independent evidence review and censor/Roadmap. Keep generated assets local_archive/experiments/S04-E022, compact docs inthisfolder. No training enabled by a green local test or CodeReady review.

## Code Ready outcome — 2026-10-16

Independent Codex subagent CODE_READY_PASS binds scientific source a540888497d1838a6aa202f59a884e6930e50fb4, no remaining blockers. Exact final suite68passed/0skipped; independent11unitchecks plus all3realasset/zeroUV/tensoridentity checks. Root all3full10000samplerstreams match, peakRSS1063747584bytes; all3validate-only pass, emptyaggregate INCONCLUSIVEexit3. Initial map-admission bug fixed with exactsaved E017UV, oldfailedlog preserved, no tolerance change. [Review](code_ready_review.md), [checks](nontraining_checks.json). Formal nativeprofile/runtime producerpreflight remains unperformed; CodeReady does not authorise training or prove repair success. Subsequent doc-only commits do not replace this science snapshot.

## Production preparation — 2026-10-16

Exactscientificsourcea540888 bundle andone-shotdispatcher prepared, deployment84a6cda independentlyreviewed. Fullplan/commands/bytehashes in[producer execution](producer_execution.md). Freshroot/proposedsharedGPU0>8GiB,60remoteexistingfilecopies, all3formalpreflights,10000nativeLRperrow,correctE021/E019pairingandstrictrow/archivechecks areexplicit. Userapprovalpending; noSSH/transfer/producerpreflight/training.
