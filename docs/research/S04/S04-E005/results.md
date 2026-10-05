# S04-E005 cross-cycle same-field residual result

## Execution and qualification

S04-E005-R001 ran on D-26-09 as Condor `64.0` from exact code commit `5fc9894393d40385c6e71edd30b9efd8c5ea1889`; it terminated normally with exit 0. All 16 remote tests passed (one known PyTorch conversion warning). The run performed no training, optimizer call, FEM/PIDL solve, trajectory advance or history commit. Independent Code Ready and Evidence Ready reviews passed.

The only qualified pairings are c76 `379<-378`, c82 `409<-408`, and c83 `414<-413`. Their same-field free-UV vector scaled differences are `1.342e-11`, `9.712e-12`, and `1.108e-11`, all below the frozen `1e-9` gate. c20/c40/c60 lack a same-contract native pre-phase input plus original MATLAB weak-form oracle and remain `INELIGIBLE`.

## Per-cycle result

| cycle | role | rho_u | box rho_d common-free | UV screen | damage screen | feasibility | max healing gap |
|---:|---|---:|---:|---|---|---|---:|
| 76 | bridge | 1.01373271 | 0.16819730 | FAIL | FAIL | FAIL | 0.28892736 |
| 82 | terminal | 1.35334532 | 0.17338598 | FAIL | FAIL | FAIL | 0.30213899 |
| 83 | terminal first-detect | 0.04133148 | 0.17479701 | FAIL | FAIL | FAIL | 0.30220191 |

All stationarity decisions use the unchanged `1e-3` screen. The maximum healing gap occurs at zero-based element 2096, GP 3, approximately `(-0.11639, 0.00811)` for all three rows. This makes each row an infeasible cross-history counterfactual; the values are not a qualified trajectory state or full KKT certificate.

## Frozen temporal decisions

- Early presence over `E={20,40,60}`: `NOT_EVALUABLE`.
- Full early-to-terminal factor-3 comparison: `NOT_EVALUABLE`.
- Local c76-to-`{c82,c83}` UV ratio: `0.0407716`, below 3, `FAIL`.
- Local c76-to-`{c82,c83}` damage ratio: `1.0308488`, below 3, `FAIL`.

Thus mismatch is already observed by c76 under this frozen cross-history diagnostic, but the predeclared local terminal-amplification rule does not pass. UV increases from c76 to c82 and then drops sharply at c83; the damage scalar changes only slightly. This is not evidence that mismatch begins before c76, that no mismatch exists at c20/c40/c60, or that a causal late-cycle amplification mechanism is absent.

## Spatial change

With fixed native coordinates and no registration, more than `99.996%` of the nodal-mass-weighted squared UV-density change lies in the fixed right crack-tip box (`x>=0.4`, `|y|<=0.03`) for both c76->c82 and c82->c83. The UV maximum change occurs at approximately `(0.45803,-0.00289)`.

Damage-correction changes are instead distributed along the narrow crack strip: more than `99.93%` lies within `|y|<=0.03`, while about half lies in the right-tip box. This locates residual-map change only; it does not establish damage-field error growth or a causal crack-tip mechanism.

## Assets and boundary

- Tables: [cycle residuals](results/cycle_residuals.csv), [pairing coverage](results/state_pairing.csv), [interval changes](results/interval_changes.csv), [trend summary](results/trend_summary.json), [spatial summary](results/spatial_change_summary.json).
- Figures: [trend](results/figures/cross_cycle_trend.png), [spatial fields](results/figures/cross_cycle_spatial.png), [spatial changes](results/figures/cross_cycle_spatial_change.png).
- Full reconstructable fields, logs and execution provenance remain under project-root `local_archive/experiments/S04-E005/runs/S04-E005-R001/`.

Allowed conclusion: same-field numerical equivalence, per-cycle screen/feasibility status, local factor-3 failure, and bounded residual-map localization. Blocked conclusion: onset before c76, a complete early-to-terminal trend, FEM teacher/equilibrium validity, field-error growth, full native KKT validity, or causal attribution to fatigue, optimizer or architecture. S04-E006 is a separate fixed-field diagnostic and is not substituted into this trend.
