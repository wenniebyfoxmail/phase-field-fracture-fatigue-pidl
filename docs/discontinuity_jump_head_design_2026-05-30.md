# Discontinuity / Jump-Head Design Branch

Date: 2026-05-30

Branch:

```text
codex/discontinuity-jump-head-design
```

Purpose:

```text
Revive the XFEM/SDF-style discontinuity idea under the strict FEM-mesh
soft-hist0 benchmark, with fixed field-level gates.
```

## Why This Branch Exists

The strict FEM/PIDL audit has narrowed the gap:

```text
mesh/timing/reference choice/final polish/head-staging/additive local patch
do not close the active-driver/history field mismatch.
```

The previous Heaviside/XFEM jump-head attempt was not promoted because it only
reached marginal stationarity and had tip-tracking/field-shape concerns.  This
branch should not simply rerun that old experiment.  It should fix the design
and judge it by c20/c40/c69 plus matched-event fields.

## Candidate Ansatz

Use the existing global network as a regular field and add a localized
discontinuity/jump component:

```text
raw_output = global_MLP(x, y) + W_tip(x, y) * H_eps(phi(x, y)) * jump_MLP(z)
```

where:

```text
phi(x, y)     signed-distance-like crack-face coordinate, initially y
H_eps(phi)    smoothed Heaviside / tanh(phi / eps)
W_tip         compact support around current/expected crack path
z             local coordinates, e.g. (x, y, r_tip, theta_tip) or scaled (x,y)
```

Start conservatively:

```text
jump applies to u/v first, not alpha
alpha gets SDF/crack-path features or a separate smooth local head only if needed
tip tracking is fixed or cycle-lagged; no unstable live jumps to boundary
```

## Non-Negotiable Gates

Do not promote by `N_f` alone.  Score:

```text
damage/alpha field
alpha_bar
psi_raw_elem
psi_active_elem = g(alpha)*psi_raw
Delta E_d
right-boundary saturation
residual field against FEM common probes
```

Main cycles:

```text
c20, c40, c69, detected event, confirmed event
```

## Implementation Notes

Keep this branch isolated from the FBPINN chain branch.  If a useful
discontinuity module emerges, merge/pick it back after field-gate evidence.

Use the new diagnostics naming:

```text
psi_plus_elem    backward-compatible active driver
psi_active_elem  active driver
psi_raw_elem     undegraded raw tensile driver
```
