# Producer stop evidence review v1

REVIEW_PASS — saved stop evidence and bounded interpretation only.

Exact source `43af56d43150f4ae8cf8799ceec4669564d67ef0`, artifact `6b0ef3bf36ffbedf3c33170b2f641c06873684276a18be3f6726537e4d7c4585`, cardv2 SHA256 `da119752c2ee81443dcee43b31cbe1fe2942ae70b39acf115dc1712005d8a125` match the prior v4 review and launch receipts. All 17 deterministic metadata, threshold and arithmetic checks passed. Saved Linux full-input identity, runtime/resources and five-state native replay receipts close the former runtime-admission pending items for this launch; this review performed no SSH or new live admission.

The pipeline accepted train_A step1 (reference label generation, not NN training) in 56.9524244s, solver 55.1839253s, two outer iterations. Recorded Ru L2=2.20221918e-15, scaled damage KKT infinity=1.47986888e-08, Ru+Rd L2=1.47995252e-07, primal violation0 and fatigue residual0 satisfy the frozen card. f_min=1 does not cover fatigue degradation. These are saved certificate values, not independently recomputed array residuals.

Step2 then hit `physical-substep hard wall cap`. Its marker-to-terminal epoch difference is 120.5613201s, consistent with the card's120s cooperative/watchdog trigger plus observation/termination delay. The raw executor terminal status remains `failed`. Step2 has no persisted internal work or worker-failure record, so its blocking stage and numerical cause are unknown; the first step's profile cannot locate the second step's cause.

Durable version1, journal step1, load index1 and snapshot state ID agree with the accepted receipt. Saved inspection reports no crash lock, bad journal line or reconciliation need. Both owned PIDs1054983/1055156 are absent at the terminal observation; only train_A has a numerical archive directory. This is saved observer evidence, not a fresh remote check.

Formal job wall=187.867064742s, summed phase wall=186.645618166s, supervisor overhead=1.221446577s. Recorded child CPU=251.959305s (0.069988696coreh);16-core allocation upper=0.834964732coreh. Job GPU time=0s. Prelaunch transfer/install/admission preparation lies outside this formal job ledger; these figures are not total research cost. No NN fit or test phase was reached.

Allowed conclusion: the exact reviewed implementation passed actual saved admission and completed one constrained reference transition, then could not finish the next transition within its frozen per-step operational budget. The whole study remains incomplete. No field-agreement gain, hybrid speedup, qualified complete training trajectory, fatigue-degraded coverage or mathematical algorithm-failure conclusion follows. This review authorizes no retry, resume, partial fit or threshold change.

Reviewed evidence SHA256:

- `launch_snapshot_v1.json`: `adad9c4b8bf7152b8fe50f65baf978be4d09d94cc7cb0cd65db11017ac160522`
- `first_accepted_snapshot.json`: `83ad85248a597b4423349681a2fa14f18fde606a59d7f44b3e393b67179f38ae`
- `terminal_snapshot_v1.json`: `f559ed1748c64c4d787f00b9a13d645f1c1d952b3e9e32eee4b0371cef3cd7e0`

Prior `producer_review_v4.json` SHA256 `443e326fe47a06ae2b0f9166dc4cd01c1f694f651bbf13ba229b87ed475397d0`. No source edits, scientific arrays/models, SSH, training or new FEM solve were performed.

Supplemental report wording: source/damage_conditioned_equilibrium.py:344 first allocates zeros, then349–351 constructs a boundary-driven linear-y initial guess. Thus “starts each mechanics solve from zero displacement” is inaccurate; use “rebuilds a boundary-driven linear initial guess without reusing the previous converged u.” First-step mechanics46.1803s/56.9524s=81.09% is supported; it does not identify the second-step stop cause. Owner notified; no code or scientific change requested.
