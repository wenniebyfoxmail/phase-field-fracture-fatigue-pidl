# Exact future execution card — NO EXECUTION AUTHORITY

**Current instruction is development/review only. Do not run this card now.** No SSH, live preflight, scientific array access, real fit/prediction, new data/holdout or mailbox action is authorised. B is sole future production/Obsidian owner. Scientific identity is the sealed package, not the design owner's commit. Exact implementation commit/package digest and review verdict are in package_manifest.json and REVIEW_RECEIPT.md after review.

## Proposed bounded single job

- Run ID reserved: IU-BRIDGE-PS-20261019-R003 (freshness not live-checked).
- Intended producer: existing gpu-taobo / GPUServer8 route; actual host/resources NOT verified this step.
- Run root: /mnt/data2/drtao/wennie/IU-BRIDGE-PS-20261019-R003.
- Code: <run root>/code; outputs/cache/tmp/logs all under the same root. No /tmp/home fallback.
- Read-only input: /mnt/data2/drtao/wennie/IU-PUBLISHED-DIC-20261019-R001/inputs/mendeley, 180 files/2309814734 bytes.
- R002 features/replay source: /mnt/data2/drtao/wennie/IU-RESPONSE-STATE-20261019-R002; exact IDs locked in config and copied verification records.
- 6 learned arms, 228 predictor archives +38 equivalence archives; 912 predictor fits +76 input fits max. 20592 case-method scores +2288 derived B* rows.
- Total controlled worker cap 1800 seconds, one CPU thread, zero GPUs; 8GiB RSS/address space, total new outputs/tmp/cache/logs4GiB, archive4GiB. This is unmeasured design allowance, not observed performance.
- No resume, model retry, machine switch, tolerance relaxation or alternative dataset. Stop at first exception/nonfinite/source mismatch/semantic warning/replay or pullback mismatch>=1e-11/budget breach.

## Required final approval and controlled entry

HQ/user must approve THIS source/config/package, run identity, input boundary, budget, and remaining differences. Only after direct approval may B prepare a receipt external to the sealed code with `human_approved:true`, exact `package_sha256`, `implementation_commit`, `run_id`, actual `authority_source` and exact `approval_text`. No such receipt is created in this preparation. A receipt/flag by itself never grants authority.

After that approval only, B may check shared CPU/RAM/storage, confirm /mnt/data2 rather than / or /home and future dependency versions, deploy the sealed snapshot to the fresh code root, and run the one controller entry:

```text
/usr/bin/python3 /mnt/data2/drtao/wennie/IU-BRIDGE-PS-20261019-R003/code/supervise.py --config /mnt/data2/drtao/wennie/IU-BRIDGE-PS-20261019-R003/code/config.producer.json --approval-receipt /mnt/data2/drtao/wennie/IU-BRIDGE-PS-20261019-R003/approval.json
```

Use detached controlled invocation after approval; record exact command, source/package, hostname/runtime, controller and worker PID, start/end/time/RSS/exit and logs. The controller creates the single run claim, exports CUDA_VISIBLE_DEVICES empty and BLAS thread variables1, applies8GiB RLIMIT_AS, monitors entire worker and both storage caps, and kills only its new child process group on first failure. It refuses code outside the sealed run-root snapshot or config outside the package. Linux controller paths and process exit/atomic-write races were statically reviewed and artificial budget checks exercised; no live Linux probe occurred here.

## Expected evidence and interpretation

Before first fit, check all180 inputs, frozen cohort, R002 source/feature/replay identities and actual tensor schema. Reuse cached R002 inputs, never regenerate a missing artifact or silently rebaseline. Per fold/horizon: preserve selected alpha, train/validation/development/test IDs, m parameters and donor IDs/distances, B* inner losses/choice, saved coarse predictions and models, pullback generalized penalty and transformed coefficients, replay checks and completed counts. All scoring remains on native field after shared current anchor.

Save all group/H scores and true/predicted signed increments, centered spatial errors, fixed-band errors, L1 mass ratios with explicit exact-zero handling, signed masses and local peak/error positions. Plot fixed middle and worst-H_INNOV case (marked post-hoc failure) for every group/H, both channels with shared scales, and each group's conditional origin-to-horizon readout; no new forward for plots.

Primary delta L(B*)−L(H_INNOV), per-H/group and leave-one-group-out effects, H_DONOR−H_INNOV, and10,000 seed20261019 full-group reweighting draws must all be reported. Mean>1e-11 is a numerical positive only. The direction diagnostics are not a physical-success conjunction; positive mean with unstable H/group/donor comparisons remains positive component evidence but does not warrant time-model expansion. Compare magnitude to R002 nominal0.006723 without promoting it to a physical tolerance. No fatigue-memory, independent-unit, state-sufficiency, crack-truth, autonomous-rollout or road claim.

After completion retrieve results.tar.gz plus archive_receipt.json and controller_receipt.json; verify bytes,266 predictor/equivalence archives,38 selector decisions,20592+2288 score rows, independent score recomputation, and complete plot/selection records. Update the existing SCB owner note and single Roadmap entry only after retrieval is explicit. On failure preserve the first-stop state and do not automatically launch again.
