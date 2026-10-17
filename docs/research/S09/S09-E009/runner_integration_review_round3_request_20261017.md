# S09-E009 runner-integration Round-3 narrow rereview request

Date: 2026-10-17  
Reviewer: Haofan / ChatGPT Pro  
Exact repair commit: `3aaa771b28e7730e97f4d9850889757ff991e544`  
Prior reviewed commit: `af7e79714a72c96f3495470bb84f2b0fbececa79`

Please return one first-line verdict:

- `RUNNER_INTEGRATION_READY_PASS` if the one residual F1 and five residual F2
  cases are closed for this exact commit; or
- `REVISE_AND_REREVIEW` followed by concrete remaining blockers.

Check only the Round-2 residuals:

1. The synthetic adapter verifies the actual trusted-reference bytes against
   the frozen E008 SHA256 before parsing them and applying only the 9-node/4-Q4
   substitution.
2. Hard-constraint counts are nonnegative native integers; completed and
   method-inapplicable receipts require all counts to be zero, while failed
   receipts may retain the real nonzero counts.
3. Every recorded evaluation update is no greater than completed optimiser
   steps; the stop location cannot precede the completed-step count.
4. A normal completion still requires the update-500 checkpoint. A failed arm
   cannot invent it before 500 complete/logged updates and update-500
   evaluation, but a later evidence-writer failure may preserve an already
   existing checkpoint and its artifact identity.

Local evidence for this exact commit:

```text
75 passed in 2.41s
py_compile: pass
git diff --check: pass
ruff --select F: pass
AdamW.step sentinel calls: 0
```

Do not reopen already closed configuration fields, conditional manifests,
shared comparison gates, numerical directions, core, losses, beta, thresholds
or protocol. A PASS closes only the no-training runner-integration gate and
authorises the next separately reviewed producer implementation layer. It does
not authorise an optimiser update, SSH/transfer, a Taobo launch, or any
scientific claim.
