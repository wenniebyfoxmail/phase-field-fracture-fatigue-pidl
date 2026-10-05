---
storyline_id: S04
experiment_id: S04-E004
protocol_revision: r0-20261005
status: stopped-before-run; A1-trial-f-rejected
scientific_verdict: negative diagnostic; no producer solve
---

# Fully direct native-Q4 equation-closure discriminator

## Mechanism question

After state, operator and residual semantics are shown to match the native FEM
equations, can a completely non-neural native-Q4 staggered solver close the
mechanics, constrained-damage and trial-fatigue fixed point on the true
`step412 -> step413 -> step414/c83` path?

This experiment removes both neural field parameterization and neural
optimizers.  It does not test supervised approximation, which belongs to
S04-E002.

## Scientific dependency and stop rule

S04-E003 is the mandatory cheaper diagnostic.  It must evaluate FEM c83 using
the lineage-qualified pre-phase state and compare the native FEM assembled
residual with the candidate native-Q4 energy derivative.  If the trial-fatigue
candidate remains nonstationary because of a formulation, boundary,
normalization or state-semantics mismatch, S04-E004 stops before a producer
solve.  A direct optimizer result under a mismatched functional cannot diagnose
FEM/PIDL optimization capacity.  Admission is machine-readable: the runner
must consume a SHA-256-bound
`s04-e003-native-cross-stationarity-admission-v1` receipt whose state labels,
native-capture identity, mesh signature, GP order, directional-derivative and
two residual-equivalence checks match the frozen schema, and whose
`trial_cross_stationarity_pass` and `admit_s04_e004` fields are both true.
Missing, stale, malformed or negative receipts stop before assembly.  The
receipt validator independently requires both trial residuals at or below the
frozen `1e-3` screen and the smooth-patch directional-derivative error at or
below its frozen `1e-5` threshold; true booleans cannot override failing
numerical values.

The older S04-E002 frozen-PIDL413 counterfactual already failed its `1e-3`
screen (`rho_u=0.04133148`, box `rho_d=0.17479701`).  It motivates this gate but
does not substitute for S04-E003 because its previous history is not the
lineage-qualified FEM predecessor.

## Frozen solver contract

1. Use the native 86,756-node / 86,408-cell Q4 mesh, four Gauss points per
   element and the declared GP order.  Record coordinate, connectivity and
   state identities before solving.
2. Mechanics block: fixed damage, direct sparse AMOR equilibrium with its
   trace-sign active-set iteration.  No neural network and no learned
   optimizer.
3. Damage block: fixed displacement and fixed fatigue degradation.  Assemble
   the standard AT1 objective as a sparse convex QP only after verifying
   nonnegative tensile energy/fatigue coefficients, symmetric Hessian and a
   PSD diagnostic.  Strict convexity and uniqueness are not assumed.
4. Enforce `0 <= d <= 1` and `N_gp d >= d_gp_previous_accepted` as linear
   constraints.  The previous accepted nodal field supplies a feasibility
   witness; failure of that check is a state-transfer/representation failure.
5. The committed-fatigue branch is a semantic ablation.  The trial-fatigue
   branch is the FEM-consistent candidate.  Trial history is rebuilt on every
   outer iteration from one immutable accepted state; it is never accumulated
   between outer iterations.  The rebuilt `f_trial` is frozen during each
   mechanics/damage pair.
6. Accepted history, previous driver, committed fatigue and accepted damage are
   updated exactly once, only after the complete load-step gate passes.  A
   library success flag or iteration cap never permits a commit.
7. The physical route is `step412 -> step413(U=0.08999988) ->
   step414/c83(U=0.11999988)`.  The old direct jump from step412 to peak remains
   a skipped-substep counterfactual and is not renamed.
8. FEM-seeded oracle restart and PIDL-seeded continuation are separate arms and
   never share trial state.  FEM fields are not used for stopping, selection or
   tuning.

## Primary gate

The sole scientific admission is the Equation Closure Gate:

`max(rho_u, rho_d, rho_field_fixed_point, rho_fatigue_fixed_point) <= 1e-3`.

- `rho_u`: normalized free-DOF mechanical equilibrium residual.
- `rho_d`: maximum of independently recomputed constrained-QP stationarity,
  primal feasibility, dual sign and complementarity residuals.
- `rho_field_fixed_point`: scaled infinity-norm change in displacement and
  damage across an outer iteration.
- `rho_fatigue_fixed_point`: scaled infinity-norm change in trial fatigue and
  its accumulator rebuilt from the immutable accepted state.

Raw `1e-4` and `1e-5` pass columns are saved as diagnostics; they cannot replace
the frozen `1e-3` gate.  FEM field distance, correlations and active-energy
ratios are computed only after a closed endpoint and are never used to select a
restart or branch.

## Stages

1. **A0 identity:** mesh/GP/material/BC/state/formula checks.  Any mismatch
   stops the run.
2. **A1 stationarity dependency:** consume S04-E003.  A trial-fatigue semantic
   mismatch stops B/C.
3. **B solver qualification:** one small or known accepted transition verifies
   QP feasibility, primal/dual certificate, mechanics closure and immutable
   commit state.  It carries no Hard-5 field claim.
4. **C scientific path:** run the true two-substep continuation for committed
   and trial fatigue, with FEM-seeded and PIDL-seeded arms kept distinct.
5. **D sensitivity:** initial-condition and critical-substep sensitivity are
   permitted only after at least one reference arm passes Equation Closure.

## Success and failure meaning

- Closed trial-fatigue direct reference near FEM supports the claim that the
  shared-network/optimizer path is a principal remaining limitation for this
  state and branch.
- Closed direct reference far from FEM supports a discrete objective, state or
  solution-branch difference; it does not support choosing the closer arm.
- Committed fails while trial closes supports load-step fatigue timing as a
  structural discriminator.
- Neither branch closes under valid identities is a solver/fixed-point failure
  for this frozen contract, not proof that physics-only PINNs are impossible.
- A0/A1 failure makes later optimization inadmissible for a FEM-reproduction
  claim.

## Minimal evidence

- `equation_closure.csv`: every outer iteration and all four gate components.
- `qp_certificate.json`: symmetry/PSD/feasibility checks plus primal/dual/KKT
  certificate and solver identity.
- `accepted_states.npz`: immutable input and conditionally committed endpoint
  states with exact labels.
- `decision.md`: allowed conclusion, blocked conclusion and next branch.
- One compact run receipt containing commit, command, producer, PID, paths and
  retrieval status.

On completion, add one row to `docs/pidl_experiment_inventory.md` and one dated
S04 claim-impact entry.  Do not start a 120-cycle calculation from this
experiment.
