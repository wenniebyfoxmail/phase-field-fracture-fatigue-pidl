# S04-E020 independent Codex subagent Code Ready review

Date:2026-10-15. Channel:Codex subagent `/root/e020_code_review`, explicitly requested by the human. Read-only, no modifications, no candidate training or optimizer parameter update. No new outgoing ChatGPT message or file upload.

**CODE READY PASS.** No producer-preflight-blocking implementation issue identified. Bound to scientific source `671fba2e48f1202bc2dd89f9800bacf1849477a0`, protocol `20261015-r1-delayed-decay`, source ZIP SHA256 `c96baf2d64fde1d46f92cd867fb2b4660b0a425a65fcecbdf2078dd8d4e05b0a`. Review-time HEAD29a8cc572002179a1001d608c45ce21603752744 differs only by7lines of review_preparation.md. Scientific files match; E019original source/failure states unchanged.

## Findings

1. Actual LR order is correct: check this update's LR after finite loss; backward/finite-gradient check; exactly one optimizer.step; record actual group LR in scheduler.step, then install next. Updates1–8000=.001;8001=.0009999993893183533;9999=.000010000610681646757;10000=.00001; no10001. Actual10000LRvector is bound in checkpoint/metrics/receipt/archive and independently validated.
2. Candidate initialization is the original E017backbone plus freshly recreated zero-output residual; no E019final residual or optimizer resume. Reference, real weights/window buffers, initial residual, backbone, full sampled stream and original runtime are explicitly checked.
3. Three-state completeness and integrity fail closed: missing=>INCONCLUSIVE; duplicate/corrupt/invalid=>INADMISSIBLE with precedence. Primary all-three .001 and regional component findings remain separate.
4. Historical byte/parameter/UV control admission is distinct from historical reference-rho equality. E019strictMacINADMISSIBLE stays intact; E020same-run strict comparison remains. No unconditional cross-platform reproducibility claim.

## Independently executed checks

- Six relevant test files:128passed in2.71s; no candidate training or optimizer.step, bytecode/cache writes disabled.
- Real three-state references/E017backbones/E019localized checkpoints loaded on CPU; full/damage/background values reproduced:

| State | Full | Damage | Background |
|---|---:|---:|---:|
|c20s4|.0007039144529734202|.005237329579855483|.00023720492201124475|
|c60s4|.0006885882301583295|.00424277319803712|.0002638378167518844|
|c83s4|.0032382383079330103|.01916744282518348|.0001634539302896372|

- Complete10000PCG64draws per state; all3sampling digests match controls,16.13/16.97/17.42seconds respectively.
- Runtime/geometry/initial residual/backbone lock fields checked against real controls.
-33ZIPmanifest entries match hashes;31files match exact source commit,2generated review differences. Source unchanged and worktree clean after review.
- Newly added admit_control preserves the caller CPU Torch RNG. This does NOT claim the entire prepare_baseline is RNG-neutral: constructing the original backbone consumes RNG; residual initialization separately uses seed/fork protection.

## Boundaries and next action

No candidate training, real CUDA updates, final E020result aggregation or production archive was exercised. Future production still requires actual original Taobo runtime, liveGPU/storage/real-asset/fresh-run-directory checks. CodeReadyPASS is implementation readiness only, not scientific success or producer authorisation. Human approval of concrete producer transfer/launch remains separate. The source ZIP remains local; the earlier proposed HaofanPro CodeReady send was not performed.
