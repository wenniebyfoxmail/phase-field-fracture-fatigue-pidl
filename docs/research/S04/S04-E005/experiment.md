---
storyline_id: S04
experiment_id: S04-E005
protocol_revision: 20261005-r1-frozen
status: protocol-frozen; awaiting-code-review
---
# Cross-cycle same-field FEM/PIDL residual diagnostic

## PIDL Experiment Gate

- Mechanism question: on native FEM peak fields, is the frozen same-field residual mismatch already observable at qualified early checkpoints, and does it further increase near the independently fixed c83 first-detect transition?
- Claim changed if success: qualified states may support a bounded temporal statement about when residual screening failures are observed and whether both UV and damage channels meet the predeclared growth effect size.
- Claim changed if failure: retain only per-cycle diagnostics; do not claim absence of mismatch or absence of growth.
- Cheaper diagnostic first: reuse archived states, true predecessor checkpoints and original MATLAB weak-form vectors; no solve, training or trajectory advance.
- Minimal output asset: six-row pairing table, qualified-cycle residual table, trend summary, raw spatial vectors, three figure sets and a decision note.
- Code/producer alignment: Mac code/light tests only; exact reviewed commit executes CPU float64 on user-authorized D-26-09 HTCondor in a fresh run root.
- Success criteria: strict pairing and input qualification; free-UV difference-vector gate at `1e-9`; unchanged `rho_u` and `boxrho_d` definitions/scales; explicit `1e-3` stationarity results; no state mutation.
- Failure criteria: missing lineage/oracle, fingerprint or state-semantic mismatch, wrong mesh/DOF/GP order, nonfinite output, vector-gate failure, or input mutation. Stationarity failure is a result, not an exclusion.
- Registry destination: one diagnostic row in `docs/pidl_experiment_inventory.md` after evidence review.
- Decision: launch analysis only after exact-commit Code Ready PASS.

## Frozen question and known-result disclosure

S04-E003 already exposed c83 values, so E005 is a frozen extension after known local evidence, not a blind six-point preregistration. The current field at each eligible row is the native FEM peak field. The primary temporal branch evaluates that field under the true predecessor PIDL accepted damage/history and committed fatigue coefficient. The archived FEM oracle is reported beside it and is never selected post hoc as a more convenient branch.

The two scientific axes are independent and may both be true:

1. Was a screen failure already observed in the fixed early group `E={20,40,60}`?
2. Did the fixed terminal group `T={82,83}` exceed the early envelope by a predeclared amount?

Cycle 76 is a bridge point only. FEM first detection is independently fixed at c83; therefore c76->c82 is pre-transition, while comparisons including c83 are “near/to first detection,” not wholly pre-critical.

## Immutable definitions and gates

Inherit the exact definitions and implementation from S04-E003 numerical commit `4c80e91`: `rho_u`, box-projected `rho_d`, total-domain lumped Q4 mass fractions, nominal energy `Es=A*E*(Us/H)^2`, nominal force `Es/Us`, `Us=0.11999988`, common free UV and damage partitions, GP order `(++,-+,+-,--)`, PIDL penalty coefficient 16875, and the production float32 fatigue map promoted to float64 for differentiation. No current-energy, active-domain, crack-length, or per-cycle maximum rescaling is allowed.

- stationarity screen: each channel separately `<=1e-3`;
- same-field numerical equivalence: mass-dual norm of the raw free-UV difference vector divided by `max(reference mass-dual norm, Es/Us) <=1e-9`;
- local bridge-to-terminal growth, separately for `k in {u,d}`:
  `G_k = min(r_k(82),r_k(83))/max(1e-3,r_k(76))`, with a frozen effect-size gate `G_k>=3`;
- complete early-to-terminal envelope, separately by channel:
  `min_T r_k / max(1e-3,max_E r_k) >=3`, evaluable only if all of c20/c40/c60/c82/c83 qualify.

The factor three is a benchmark-specific predeclared effect-size rule, not a physical constant or statistical significance test. UV and damage are never averaged, summed or converted into a synthetic total score. Report raw values, threshold multiples and decisions separately.

## Candidate and missing-data rule

The candidate set is fixed at `{20,40,60,76,82,83}`. Every row remains in `state_pairing.csv`. c20/c40/c60 currently lack same-contract native `pre_phase_input` plus original MATLAB weak-form oracle, and therefore are `INELIGIBLE`. Existing post-commit/cycle-end/psi-only assets cannot substitute. The complete early-presence and early-to-terminal verdicts must remain `NOT_EVALUABLE`; c76 cannot be moved into the early group.

Eligible mappings are fixed from real production lineage and log records, not inferred only from a step formula:

| FEM native peak | PIDL target | true predecessor checkpoint |
|---|---:|---:|
| c76 s4 | 379 | 378 |
| c82 s4 | 409 | 408 |
| c83 s4 | 414 | 413 |

The target step's own post-commit checkpoint is forbidden as predecessor input. The native v1 `pre_phase_input/p_field_old` is the accepted FEM prior damage; `pre_phase_input/p_field` is the last staggered predictor and is not substituted. Old fields must equal the oracle copies. v1 current u/v/d must equal v2.1 exactly at every admitted cycle.

## Five independent result layers

Each cycle records: input/pairing qualification, numerical equivalence, feasibility of the FEM current damage under the PIDL predecessor constraint, stationarity screening, and temporal-interpretation eligibility. A feasibility failure is retained with magnitude and location; the FEM current field is not clipped or repaired before evaluation. A vector-gate failure blocks same-field cross-trend interpretation. A stationarity failure does not invalidate the row.

## Frozen spatial and trend outputs

Use real cycle x coordinates and separate log-scale UV/damage panels with the unchanged `1e-3` line. Missing cycles remain missing and are not joined. Spatial maps use globally assembled nodal UV residuals, the box-projected damage correction, common cross-cycle colour scales, native material coordinates and FEM damage contours. Fixed changes are c76->c82 and c82->c83; no crack-tip translation or per-panel normalization is allowed. Raw vectors, coordinates, masses and masks are archived so figures are reconstructable.

## Allowed and blocked conclusions

Allowed: per-cycle same-field numerical equivalence, screen/feasibility status, and the local c76-to-c82/c83 threefold result for each channel. If early assets remain ineligible, the strongest temporal wording is “by c76 the observed status was X; from c76 to both terminal points the frozen local growth gate did/did not pass.”

Blocked: onset before c76; a complete early-to-terminal verdict; “no early mismatch” from missing data; FEM teacher/equilibrium qualification; field-error growth; causal attribution to the optimizer, architecture or fatigue mechanism; a full native KKT claim from a nodal box diagnostic; or replacing this analysis with the separate S04-E006 rebalanced field.
