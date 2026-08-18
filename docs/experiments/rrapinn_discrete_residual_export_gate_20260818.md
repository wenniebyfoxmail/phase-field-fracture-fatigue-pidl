# RRaPINN discrete residual export gate preregistration

Date: 2026-08-18
Status: `locked diagnostic design / not authorized to train`

## Five-question gate

1. **Mechanism question:** can the Formal PIDL checkpoint expose genuine
   discrete equilibrium and projected-KKT residuals whose tails are distinct
   from element-energy magnitude?
2. **Claim change:** pass permits implementation review of an opt-in
   residual-risk loss; fail rejects or revises the residual definition. Neither
   outcome changes the current fracture-prediction claim.
3. **Cheaper diagnostic:** frozen-checkpoint autograd and finite-difference
   checks on U0.12 before any optimizer/training loop.
4. **Minimal output:** `residual_metrics.csv`, `manifest.json`, one residual map
   with a same-stem sidecar, and `decision.md`.
5. **Checklist entry:** update the canonical RRaPINN track and add exactly one
   diagnostic row to `docs/pidl_experiment_inventory.md` after completion.

## Frozen input

- Development amplitude only: U0.12.
- Primary state: Formal PIDL c82 peak / raw step409, the last common
  pre-first-detect cycle against FEM.
- Code baseline for physics/state semantics: Formal hard-recovery five-substep
  family at commit `b6d56102daa7d45a6c196b72055010170e5f39fb`.
- No FEM field enters residual construction. FEM may appear only in a separately
  labelled posthoc location overlay.

Resolved local state assets:

- `checkpoint_step_409.pt` SHA256
  `581304ad5ac236da6be40c04aa694242c2a1d1ce3e28b45bb070c5a10b36faaa`;
- `trained_1NN_409.pt` SHA256
  `94e7a3e249fc5b16f850382be9f027d5ff86dccc64b35b94c59458e15683fe00`;
- `model_settings.txt` SHA256
  `015fe8ddf563b2b9d81b8a681705e2a35f9044206311a6a7e26f40a7dc9c1047`.
- lower-bound/fatigue state `checkpoint_step_408.pt` SHA256
  `11cbe7f62f5e14c1a5f1946cfbb9f853138616a28a748b7b2688911d2c771d06`.

Step409 is the evaluated peak field. Step408 is the immediately preceding
substep and supplies the frozen `d_old=hist_alpha` and `hist_fat` that were
available to the step409 fit. Step409 post-commit histories are forbidden as
the lower bound because that would leak the evaluated state into `d_old`.

If the complete c82 checkpoint bundle needed for autograd cannot be resolved
and hash-verified, the gate stops as `blocked_missing_input`; it must not fall
back to c58, own-event, confirmation, or a different model family.

## Frozen residual semantics

Let `Pi = E_el + E_d` with the fatigue degradation and old history frozen at the
evaluated raw step.

### Mechanical residual

For free displacement degrees of freedom:

`r_u = dPi/du`, `r_v = dPi/dv`.

Dirichlet-constrained degrees of freedom are excluded, not assigned zero and
included in the tail denominator. Report component scales and the normalized
vector magnitude separately from damage.

### Damage residual

With lower bound `d_old`, upper bound one and positive diagnostic step `tau`:

`r_d = [d - Proj_[d_old,1](d - tau*dPi/dd)] / tau`.

The exporter must demonstrate tau-insensitivity over a predeclared safe set
after normalization; it may not choose tau by matching FEM.

The primary diagnostic scale is fixed without FEM as
`tau_ref = 0.01 / weighted_p95(abs(dPi/dd))`, where the percentile uses nodal
lumped area. This makes the 95th-percentile unconstrained trial move equal to
0.01 damage. Sensitivity scales are `{0.1, 1, 10} * tau_ref`; the normalized
CVaR95 and CVaR99 must remain finite and their active-set interpretation must
be reported, not silently tuned.

`E_hist` and `abs(E_el,e)+abs(E_d,e)` must be exported only as explicitly named
regularizer/proxy sensitivity channels. They are forbidden from the primary
residual columns.

## Required tests

- directional derivative of `Pi` versus the residual inner product;
- free/constrained DOF mask count and boundary-coordinate audit;
- projected-KKT sign tests for inactive, lower-active and upper-active states;
- positive finite lumped weights and exact fractional-tail allocation;
- finite mean, p95, CVaR95, p99 and CVaR99 for each residual family;
- permutation invariance and mesh-area rescaling invariance of normalized tail
  summaries;
- no gradient path through detached thresholds/selection in diagnostic mode;
- explicit non-equivalence label for the old energy proxy.

Directional derivatives use deterministic seed 20260818, direct physical-field
perturbations, central differences at `h in {1e-4, 3e-5, 1e-5}`, and separately
test free displacement and damage directions. The best stable relative error
must be at most `5e-4`; all calculations for this check are recomputed in
float64 from the frozen float32 checkpoint output.

## Pass/fail

Pass requires all semantic/unit checks, a hash-complete manifest and independent
review of the residual map. No numerical FEM-fit improvement is required or
claimed at G1.

Fail immediately on a directional-derivative mismatch, active-set sign error,
boundary leakage, non-finite residual, missing state hash, or any attempt to
substitute an energy magnitude for a residual.

## Post-pass decision

Passing G1 does not launch training. It permits a separate G2 implementation
and preregistration that freezes the mean-excess form, alpha, threshold update,
risk scaling and risk-off equivalence tolerance. Only after G2 passes may a
Taobo short smoke be proposed.
