# BRIDGE-PS-v1.0 independent focused difference review v2

2026-10-19, Europe/London. Independent read-only reviewer `/root/bridge_exact_review`. **REVIEW_PASS, bounded code/contract review**. Both blocking findings in `independent_review_v1.md` are resolved by the exact difference below. The unchanged scientific code/algebra and interface findings from v1 carry forward. This is not runtime validation, scientific success, or execution authority.

## Exact identity

- Previous reviewed commit: `2ef6eec513742a5225d14f99779f1aa0ab61695f`.
- Revised reviewed commit: `d67f0ac68f4baa8c665ad4b9ee8eea83a1006782`.
- Worktree: `/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/mendeley-info-value-20261019`.
- Package: `docs/research/identification_uncertainty_prediction/bridge_ps_20261019`.
- Recomputed canonical package digest: `6d03ace1cf6550756d127cea99f1e24737a290368b0c1bfbe87e3420760a47a2`.
- Git HEAD resolved to the revised full commit and working status was clean. Exact committed difference contains only `supervise.py`, `test_state_contract.py`, and the corresponding two updated `package_lock.json` entries. All lock-listed hashes were verified by `contract.package_id`. No scientific code, design, config, input identity, estimator, threshold or budget changed.

## Performed focused checks and resolution

1. Read the complete exact controller/test/lock difference. Top-level `size` now catches the `FileNotFoundError` arising when an owned archive is renamed between `is_file` and `stat`. It does not catch arbitrary I/O failures or suppress budget exceptions. The polling path still observes both final and partial archive names; the worker also checks final archive size before renaming. A transient disappearing name therefore no longer causes an artificial no-retry stop. Independently reran the new artificial rename regression: passed.
2. `finish_record` now records `started_at_utc` and `ended_at_utc`, together with unchanged monotonic `wall_seconds`, package identity, worker PID, peak RSS and status. Both complete and stopped controller paths call this helper; controller claim also records UTC start. Stops after the exclusive run claim and before worker launch produce a stopped receipt with `worker_pid:null`. Refusal before successfully claiming a new run does not overwrite any existing run's receipt. Independently reran the completion/stopped timestamp fixture: passed.
3. Independently ran `worker.py --check`: metadata-only contract returned 19 groups, 1144 origins, 2288 horizon cases, production authority false. This does not read saved scientific arrays or test their actual availability.

The two new focused fixtures passed in this review. The prior 30 fixtures/algebra checks are carried forward from v1 because their scientific implementation is byte-unchanged. The owner's reported 32-fixture log is additional evidence, not substituted for the focused checks above.

## Unchanged limitations and next boundary

- No scientific arrays, raw CSV/XLSX, protected holdouts, real fit/forward, SSH, live resource preflight, producer run or mailbox operation was used. No worktree source was edited; only this review report was written.
- Mac BLAS RuntimeWarnings in the earlier artificial suite remain an explicit uncertainty; production warnings-as-errors and strict `<1e-11` replay/equivalence stops are unchanged. This difference review does not claim warning-free Linux behavior.
- Actual Linux process/controller integration, dependencies, input/source availability, true replay/equivalence, time/RSS and storage remain unmeasured. Proposed 1800 seconds / one thread / 8 GiB / zero GPU / 4 GiB outputs plus 4 GiB archive are caps, not observations.
- The descriptive implementation-commit field in approval remains a nonempty-string guard; exact runtime code identity is enforced by the approved package digest. The human execution card/approval must contain the actual full revised commit and this digest.
- No physical-state sufficiency, fatigue memory, calibrated physical UQ, independent specimen, autonomous rollout or road claim is supported by a code review. Common current-field anchor, 19 exposed released groups and release-step clock remain mandatory interpretation limits.

Within the current preparation-only delegation, return this exact reviewed package and receipt to HQ/user. Do not treat REVIEW_PASS as approval to SSH, inspect live resources or launch production. Any further lock-listed change needs a new digest and focused difference review.
