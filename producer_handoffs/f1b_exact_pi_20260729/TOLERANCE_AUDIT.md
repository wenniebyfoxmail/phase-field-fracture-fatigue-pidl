# F1b Solver Tolerance and Residual Audit

This audit is frozen before producer launch. The exact-Pi candidate uses
`s_E=3`, `s_L=10`, and `s_t=10`. Damage and load factors are dimensionless.

## Active convergence controls

| Control | Quantity and units | Reference | Candidate | Treatment |
|---|---|---:|---:|---|
| displacement Newton residual | assembled equilibrium residual, force | `1e-6` | `3e-4` | scaled by `s_E s_L s_t = 300` |
| phase-field Newton residual | derivative of total energy with respect to dimensionless damage, energy | `4e-4` | `1.2` | scaled by `s_E s_L^2 s_t = 3000` |
| hard-recovery phase residual | same phase-field residual, energy | `4e-4` | `1.2` | same energy scaling |
| staggered residual | upstream code adds force and energy residuals | `4e-4` | `4e-4` in normalized space | replace raw dimensional sum by `||R_u||/300 + ||R_d||/3000` |
| PF diagonal shift floor | phase tangent, energy | `1e-8` | `3e-5` | scaled by energy factor `3000` |
| PF diagonal shift seed | phase tangent, energy | `1e-12` | `3e-9` | scaled by energy factor `3000` |
| AT1 recovery tolerance | damage increment, dimensionless | `1e-3` | `1e-3` | retained |
| irreversibility tolerance | damage increment, dimensionless | `1e-3` | `1e-3` | retained |
| crack threshold | damage, dimensionless | `0.95` | `0.95` | retained |
| confirmation rule | node count and explicitly resolved cycles | `3`, `3` | `3`, `3` | retained |

The force scaling follows `stress x boundary area = E x L x t`. The energy
scaling follows `energy density x volume = E x L^2 x t`; it is also
`w1 x L^2 x t` because `w1` scales by three. The phase residual and tangent
share this energy scale because damage is dimensionless.

## Dimensionless or discrete controls retained

- Newton and staggered maximum iteration counts: `250`, `250`, and `1000`.
- Eight load steps, explicit loading plus unloading, `R=0`, and load factors.
- Maximum cycle `120`, damage upper bound `1`, minimum hit-node count `3`, and
  three post-hit confirmation cycles.
- Same mesh topology and quadrature; coordinates and thickness are scaled, so
  `h/ell`, element aspect ratios, and integration-point layout are unchanged.

## Inactive controls

- Line search is disabled, so line-search iteration and acceptance parameters
  cannot affect this run.
- Cycle jump is disabled, so jump tolerances and extrapolation parameters are
  inactive.
- PF-CZM damping is inactive because the locked law is AT1/AMOR.

## Controlled numerical mismatch

The floating-point `eps` floor in the reported `Kt` denominator is retained.
It affects only that scalar diagnostic; it is not used by residual assembly,
field evolution, history update, or event detection. No F1b acceptance gate
uses `Kt`.

## Fresh-solve acceptance basis

Floating-point identity is not required. The locked field gates are:

- linear damage: area-weighted MAE `<=0.002`, RMSE `<=0.005`, correlation
  `>=0.995`;
- normalized history, raw driver, and active driver in log10 space: MAE
  `<=0.05` decades, RMSE `<=0.10` decades, correlation `>=0.99`;
- active support at the area-weighted reference p99: IoU `>=0.90`, area ratio
  in `[0.90,1.10]`, and centroid shift no greater than one local reference
  support-cell diameter;
- first-hit and confirmed-event cycle errors each `<=1` explicit cycle.

The field limits are an engineering invariance gate tied to the normalized
phase residual tolerance and the unchanged mesh resolution, not a mathematical
error bound. They are applied at same-cycle c20/c40/c60 and at first-hit and
confirmed own-event states. They may not be relaxed after results are seen.
