# S04-E013 Stage 1 supervised-capacity result

Result date: 2026-10-09
Reviewed code: `769396f93ae5258eb984e1585d4274f7990afb11`
Producer: Taobo GPU 0
Matrix attempt: B, runs R016--R027
Execution result: `SUPERVISED_CAPACITY_FAIL_FIXED_PROCEDURE`
Architecture representability: `UNRESOLVED`
Evidence review: pending

## Execution and integrity

Fresh matrix attempt B completed all twelve state-seed runs and the fail-closed
aggregator. The dispatcher ran from 2026-10-09 09:37:20 to 13:27:55 CST
(01:37:20 to 05:27:55 UTC). All runs reached 10,000 steps with batch size
16,384 and final scheduler learning rate `1e-5`.

The aggregator admitted twelve valid completed runs, found no missing rows and
no integrity error, and counted zero joint passes. All twelve run receipts bind
the clean reviewed commit, `CUDA_VISIBLE_DEVICES=0`, Taobo, fresh output and
archive roots, and `VERIFIED_COPY` archives. Every reference SHA was unchanged
before and after training. Every run recorded zero damage solves and zero
history commits.

Retrieved aggregate identities:

- `metrics.csv` SHA-256:
  `4ee95024f1574c0e2a442c697d16f2904afd9ae08c64d81f9b54d7923ed4d85a`
- `summary.json` SHA-256:
  `742aea7a9cd1857d431794dcca47b14404460597083c5bfb1f7652eb7950f510`
- dispatcher log SHA-256:
  `1b6f4b850a8e0641d71a840e87cce6cc3a1566d522827a9912730ff758971d17`
- retrieved 24-file metrics/receipt bundle SHA-256:
  `10e297513c6b9b2486d4a21dfe6edafc1524c604061d3d589704c6ae10cb394a`

The compact claim-critical copies are [stage1_metrics.csv](stage1_metrics.csv)
and [stage1_summary.json](stage1_summary.json). The normalized decision figure
and its reading boundary are documented in
[figures/README_analysis.md](figures/README_analysis.md).

## Result by early, middle, late and transition state

Each table entry is the mean over seeds 1, 7 and 19. Thresholds are displacement
`<=1e-3`, strain `<=1e-2` and `rho_u<=1e-3`.

| state | period | displacement RMS / |Us| | strain relative L2 | predicted rho_u | joint passes |
|---|---|---:|---:|---:|---:|
| c20s4 | early | 0.00491998 | 0.236624 | 74.5732 | 0/3 |
| c60s4 | middle | 0.00531775 | 0.207663 | 94.6404 | 0/3 |
| c82s4 | late | 0.00538457 | 0.186579 | 106.724 | 0/3 |
| c83s4 | transition | 0.00538262 | 0.172463 | 97.4761 | 0/3 |

All twelve essential-BC errors were exactly zero. Every run failed all three
remaining gates:

- displacement ranged from `0.00482078` to `0.00554792`, 4.82--5.55 times
  the threshold;
- strain relative L2 ranged from `0.170084` to `0.243146`, 17.0--24.3 times
  the threshold;
- predicted `rho_u` ranged from `71.3861` to `113.364`, while the gate is
  `1e-3`.

## Interpretation boundary

The fixed supervised procedure fails already at c20, so the failure is not
created only near the crack transition. Displacement error remains near
`5e-3` across all four states. Strain error decreases from c20 to c83 but
remains far outside the frozen gate. The mechanics residual increases from
c20 through c82 and then decreases at c83, so it does not support a monotonic
critical-amplification claim.

The same failure pattern across all three seeds supports a reproducible
negative result for this optimizer, sampling rule, architecture and 10,000-step
budget. It does not prove that the architecture cannot represent the fields.
The displacement gate itself fails, so the outcome cannot be explained only by
derivative-sensitive strain or residual evaluation.

Stage 2 remains unauthorized. Before any new training, a separate gate must
decide which bounded diagnostic can distinguish finite-budget optimization,
sampling/objective mismatch and representational limitation without changing
this completed result after seeing it.
