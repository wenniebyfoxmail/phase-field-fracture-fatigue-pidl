# S09-E009 runner-integration narrow rereview request

Date: 2026-10-17  
Reviewer: Haofan / ChatGPT Pro  
Exact repair commit: `af7e79714a72c96f3495470bb84f2b0fbececa79`  
Prior reviewed commit: `77ab15254e8b444a37ae9f11c9a91791f2e1d906`

Please return one first-line verdict:

- `RUNNER_INTEGRATION_READY_PASS` if both Round-1 findings are closed for this
  exact commit; or
- `REVISE_AND_REREVIEW` followed by concrete remaining blockers.

This is a narrow rereview. Please check only:

1. **F1 / configuration identity.** The normal entry point must require the
   independently frozen E008 base-config SHA256 and protocol SHA256. The
   explicit synthetic test adapter may replace only `native_nodes=9` and
   `native_q4_elements=4`; it must reject every other base-runtime change.
   Protocol revision, complete budget including no transfer, all producer
   fields and unresolved source fields must fail closed.
2. **F2 / conditional evidence.** Common and completed-only outputs must be
   separated. The frozen receipt validator must distinguish `COMPLETED`,
   `EXECUTION_FAILED` and `METHOD_INAPPLICABLE`, preserve partial counts and
   the last valid evaluation, require update-500 checkpoint only on normal
   completion, and keep shared-identity/replay failure from entering cross-arm
   performance comparison.
3. **No regression.** The fixed four-arm schedule, reviewed direction math,
   same-forward `g_D`, model/buffer/optimiser isolation, single clip and
   no-training boundary must remain unchanged.

Local evidence for the exact commit:

```text
69 passed in 2.15s
py_compile: pass
git diff --check: pass
ruff --select F: pass
AdamW.step sentinel calls: 0
```

The expanded suite contains all 64 arm/cycle direction comparisons, explicit
buffer-storage isolation, the base-constraint counterexample, the three
reviewer-named field drifts, additional producer alias/root/fallback drifts,
all three terminal receipt branches, and both cross-arm shared gates.

Do not reopen the core formulas, losses, beta values, thresholds or protocol.
A PASS closes only the no-training runner-integration gate and authorises the
next implementation/review layer for the producer loop, resolver and full
evaluator/evidence writer. It does not authorise an optimiser update, SSH or
transfer, a Taobo launch, or any scientific claim.
