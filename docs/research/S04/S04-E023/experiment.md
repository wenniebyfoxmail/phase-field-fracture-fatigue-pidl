---
storyline_id: S04
experiment_id: S04-E023
protocol_revision: 20261016-r1-fixed-initial-fullmass-head-rms
status: code-ready-no-producer-run
---
# Fixed initial full-mass RMS output-head parameterization

## Question and boundary

Does one fixed input-scale parameterization of the output head turn available descent directions into better three-state UV fitting while retaining E022's last-hidden leak? Synthetic, same-state conditional supervised imitation; c20s4 early / c60s4 middle / c83s4 transition peak, one exposed trajectory/seed. Current task is implementation and C0 Code Ready, not a producer run or C3 forecast claim. Full FEM teacher remains NOT_QUALIFIED; only existing fixed-damage/frozen-fatigue UV-derived references are admitted. E019/E021/E022 original scientific misses and strict Mac nativeLR/reference-rho failures stay unchanged.

E022-D001 removed c60's exact hard-zero condition but did not restore UV fit; c83 head-only attainable improvement remains unquantified. A small nonzero head residual does not prove material head optimization gain, and Gram concentration does not prove column RMS imbalance. This is one bounded optimization discriminator, without a demonstrated .001 attainability ceiling. Do not represent it as an already identified cause or guaranteed repair.

## One factor and exact initial calibration

Preserve E022 LastHiddenLeakyReLU(coeff*pre,.01), the original trainable coefficient, first seven layers, output parameter count, E021 coordinate map and physical BC/window, frozen E017 backbone/damage/history/fatigue. Add only outer-model head_rms/head_scale buffers; residual tensor initialization and all RNG draws remain unchanged. Actual components_physical and correction_physical share the same scaled head implementation.

Before any candidate update, CPU float64 / 2 threads / fixed1024-node chunks, using the original E022 zero-output initializer and full-node mass weights:

```
w_i = mass_i / sum(mass)
Phi0_ij = BC(x_i)*window(x_i)*[h0(x_i),1]_j/abs(Us)
s_j = sqrt(sum_i w_i*Phi0_ij**2)
D_j = 1                                   if s_j == 0
D_j = 1/max(s_j,1e-6*max(s))               otherwise
UV = backbone + BC*window*([h,1]*D)@B
```

All284columns include bias; u/v share the vector. D>0 finite and fixed throughout training; no batch-dependent statistics. Calibration does not accept target UV or residual labels, and never uses trained E021/E022 features. Known state Us and unchanged teacher-derived coordinate map retain their existing information scope. Abort on nonpositive/nonfinite max(s), invalid D or nonfinite forward/gradient. Zero-column rule and floor fixed for all states, no sweep. Chunk order and CPU threads are explicit numerical protocol, restored after calibration; formal runtime and exact stored calibration must independently reproduce. No Mac vector injection to qualify another platform.

For B_phys=diag(D)B the original function class remains, including bias. Same zero head means initial UV remains exactly backbone; synthetic nonzero-head tests must prove physical equivalence and g_new=diag(D)g_phys. The new parameterization changes AdamW gradient/moment/update geometry and subsequent hidden-feature learning. Scalar decoupled weight decay commutes with fixed D; it does not preserve Adam update paths. A future improved joint run is not a frozen-feature head-only optimality proof.

## Three paired states

| State | Direct comparator | Common historical controls | Candidate budget |
|---|---|---|---|
| c20s4 | own completed E022 R001 | own E021 / E019 localized | 10000 NEW updates |
| c60s4 | own completed E022 R002 | own E021 / E019 localized | 10000 NEW updates |
| c83s4 | own completed E022 R003 | own E021 / E019 localized | 10000 NEW updates |

Exact runIDs and all9 E022 files per state: e022_control_locks.json; source a540888497d1838a6aa202f59a884e6930e50fb4. E021 direct locks and E019 common locks stay unchanged. Fresh candidate from each original E017alpha.7seed7backbone and matching zero-output residual, never resume an old residual/optimizer or retrain a historical control. Same unbiased full-field mass objective, damage>.1 stratification, alpha.7 draws11469damage+4915background, seed7 PCG64 seed1000010, full10000 sampled-index digest required. Calibration consumes no sampling RNG. Backbone inherited10000 and historical sunk compute reported separately.

## Actual LR and stop rules

AdamW lr.001, betas(.9,.999),eps1e-8,weight_decay1e-8,amsgrad/maximizeFalse. Original native CosineAnnealingLR(T_max10000,eta_min1e-5), read actual LR before optimizer.step, scheduler.step after each update. First actual .001; last actual about1.0000024427270673e-5; post-final1e-5, nextactualNone, no10001. Before update1 replay parameter-free expected10000vector; actual=expected=nativeformal=ownE022 and E021 used vectors required. Formal runtime Torch2.7.0+cu126/NumPy1.24.4/CUDA12.6/RTX4090/GPUServer8/GPU0/CUBLAS:4096:8 preserved. Mac native bits differ; validation-only does not qualify producer runtime/LR.

Exactly10000 joint hidden/head updates per state; no extra head fitting or parameter steps, no least-squares/ridge calibration. Record final10000 only for scoring;0/1000/...10000 passive traces, no best checkpoint or state winner stitching. Immutable PRE_UPDATE before update1. Validate fixed D/s every update and final, class/leak/map/BC/backbone/source/seed/state/stream/actualLR/finite/artifact/archive identities. Failures stop row/dispatcher; no floor/GPU/seed/budget change or automatic retry. No producer start in this task.

## Strict decoder and evidence

Each row11files: original9 plus head_scale.json and head_gradient_preflight.json. The ten nonreceipt files are SHA-bound and copied into a distinct real producer archive, receipt records exact hashes; receipt also copied. Calibration JSON includes full s/D, input/initial-model digests and rule. A separate full-node initial gradient check uses saved E017 baseline/target only to audit g_new=D*g_phys; it never feeds the scale calculation. It performs head-copy autograd, no optimizer or actual model parameter update.

Bind head rule, E022 control lock and both new SHA fields in metrics/checkpoint/receipt/PRE_UPDATE. Strict decoder reconstructs fresh common initializer from trusted reference/backbone/map, recalculates s/D and gradient audit, checks exact sidecar content, then verifies actual checkpoint buffers and scaled-class forward, saved UV, every original final metric and baseline/support at unchanged tolerances. Rehashing a forged D/manifest/CP together cannot substitute for recomputation. Historical byte/UV admission is distinct from same-run strict numerical admission.

One primary scientific criterion unchanged: all3valid final mass UVRMS/abs(Us)<=.001. Damage improvement / background preservation vs backbone, E019, E021 and E022 reported separately, including inside/outside background and exterior invariance. Secondary strain/rho_u cannot rescue primary. New summaries use FIXED_INITIAL_HEAD_RMS_THREE_STATE_UV_SCREEN_PASS/FAIL, retain INADMISSIBLE/INCONCLUSIVE rules. Full/region RMS definitions unchanged; conditional RMSs do not add.

Future head diagnostics must show both original unscaled physical Phi basis and new parameterization, so a smaller scaled gradient cannot masquerade as optimization improvement. D statistics or head residual gains without UV gains are component-only, not scientific success. Preserve useful coordinate/leak components; if this bounded repair fails, do not automatically extend training or scan floors.

## Nontraining / review / next boundary

Required checks: same initial residual tensors/RNG/parameter counts; exact initial UV; synthetic nonzero-head function/gradient equivalence incl negative coefficient; full-mass/bias formula; tiny/zero/invalid sigma; fixed-buffer/rule/lock/hash tamper rejection; actual10000LR no10001 and full three-state sampler streams; positive temporary synthetic completion decoder plus coherent-hash tamper negatives. Temporary fixtures declare synthetic steps/runtime only, never evidence of training. Three real states admit exact reference/backbone/E022/E021/E019 controls and calibrate at bounded CPU memory. No training-loop entry on Mac.

Independent Codex Code Ready must bind exact committed source and data/rule locks after checks. Code Ready is not formal preflight, scientific success or authority to start a producer. Next after review: prepare exact-source package and concrete producer plan for user decision. All raw/check outputs under local_archive/experiments/S04-E023/nontraining_v1; compact checks and review here.

## Code Ready outcome — 2026-10-16

Independent Codex CODE_READY_PASS binds **c4ceb5d27fa8d408be1b9f02dcd6b10308f301a2**, no blockers. Root41checks/0skips and all3realasset/calibration/sampler/CLI checks passed. Independent10unitchecks, all3RMS re-evaluations with719chunks/einsum (maxsigma difference1.11e-16,Drelative8.88e-16), nonzero-head function equivalence and actualnonzero scaled-checkpoint decoder fixture all pass. Synthetic completion metadata is test-only, not candidate training. [Review](code_ready_review.md), [checks](nontraining_checks.json). Later doc commits do not replace the reviewed science snapshot. Formal canonical CPU/CUDA preflight and exactproducer-native LR remain future conditions; no training or scientific result. Next: concrete exact-source production package and approval plan.

## Exact-source production preparation — 2026-10-16

Two-file v1 package and single-launch script prepared locally for reviewed sciencec4ceb5d27fa8d408be1b9f02dcd6b10308f301a2; separate deployment28f6aa8801ad0d24660c08a6711d97383936b752 independently receives DEPLOYMENT_PREPARATION_PASS. All15deploymentchecks, shell/fourPythonblock syntax and minimal-base bundle reconstruction pass; reconstructed exactsource admits all3real validate-only calls. No SSH/transfer/formalproducerpreflight/training.

[Final approval action](producer/approval_action.md) lists exact account/newdirectory/twoSHA256s, sharingGPU0onlyfree>8192MiB and all-state-first formalpreflight. Trusted-initializer CPUfloat64/twothread/fullmass D and gradient sidecars are recomputed before each row and compared exactly; unchangedc4runner computes its own fixedD, checks buffers everyupdate, and archivedD must match formalpreflight after each row. No externalD injection/API barrier is claimed. OwnE022/E021 native10000LR, three-state pairing,10000NEWupdates and originalstop/aggregate rules unchanged. Await user approval of this precise transfer/start action. [Execution record](producer_execution.md), [independent deployment review](producer/deployment_review.md).

## Production approval / access pending — 2026-10-17

User approved the exact v1 transfer/conditional single launch; local hashes unchanged. SSH failed before authentication and read-only target verification also failed. No transfer, formalpreflight or training; target directory state unknown. Await existing Tunnelblick connectivity, then inspect before continuing approved action. No change to scientific source/design or old verdicts. See [execution record](producer_execution.md).
