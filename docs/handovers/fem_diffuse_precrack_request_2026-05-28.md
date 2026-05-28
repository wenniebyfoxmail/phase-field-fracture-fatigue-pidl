# Request To FEM Agent: Diffuse Pre-Crack / PIDL-Like Notch Diagnostic

Date: 2026-05-28

Hi FEM agent,

We found a definition mismatch that affects the FEM/PIDL mechanism comparison:

- FEM reverseBC u=0.12 currently treats the initial notch/pre-crack as a void.
- PIDL baseline represents the initial crack/notch as a damaged phase-field
  region with `d/alpha = 1` inside the computational domain.

This affects absolute `E_d`, and may also influence fatigue-history
accumulation, local `f_fatigue`, and crack-tip stress/energy concentration. We
are now running PIDL diagnostics that approximate FEM's void notch by excluding
the initial pre-crack corridor from the energy and fatigue-history update.

Could you please run the reciprocal FEM diagnostic: a PIDL-like diffuse
pre-crack case?

## Requested FEM Diagnostic

Use the same reverseBC u=0.12 setup as the cyclewise handoff, but change only
the initial notch/pre-crack representation:

```text
Instead of modelling the initial crack/notch as void, keep material there and
initialise a damaged diffuse pre-crack band with d = 1.
```

Suggested initial damaged corridor, matching the PIDL diagnostic mask:

```text
x <= 0
|y| <= 0.02
```

If the FEM phase-field implementation requires a smooth profile rather than a
hard band, please report the exact profile, e.g. whether it is a sharp `d=1`
band, a regularised AT1 profile, or another initial condition.

Please keep all other settings unchanged:

- reverseBC u=0.12
- AT1 + AMOR + PENALTY
- E=1, nu=0.3, Gc=0.01, ell=0.01
- Carrara fatigue, alpha_T=0.5, p=2
- same cycle export definitions as
  `_pidl_handoff_reverseBC_u12_cyclewise_mechanism_2026-05-28`

## Requested Outputs

Please export the same cyclewise mechanism package as before, preferably through
all available cycles:

```text
reverseBC_u12_diffuse_precrack_cyclewise_mechanism_metrics.csv
reverseBC_u12_diffuse_precrack_element_fields_c1_cXX.mat
mesh_geometry.mat
README_reverseBC_u12_diffuse_precrack.md
export_reverseBC_diffuse_precrack.m
```

Please include the same per-cycle metrics:

- `E_el`, `E_d`, total energy
- `d_elem` max/mean/p99/p999
- `alpha_bar_elem` max/p999/p99/mean
- `alpha_bar_monitor_max`, clearly labelled separately from element max
- `f_fatigue_elem` min/p001/mean
- `psi_plus_elem` max/p999/p99/mean
- `Kt_proxy`
- max locations for `d`, `alpha_bar`, min `f`, max `psi_plus`
- `x_tip_d095`, `x_tip_d090`, `x_tip_d050`
- near-tip width metrics
- right-boundary `d >= 0.95` count and y-span

## Extra Metadata Needed

Please explicitly record:

- whether the pre-crack region is material or void,
- exact pre-crack geometry/profile,
- initial damaged-band width,
- whether `E_d` includes the initial damaged pre-crack energy,
- whether `alpha_bar` and `psi_plus` are accumulated/evaluated inside the
  pre-crack band,
- whether crack-face/internal-boundary traction-free conditions exist or not in
  this diagnostic.

## Why We Need This

This will isolate whether the FEM/PIDL gap is caused mainly by:

```text
initial notch representation
```

or by the PIDL local mechanism:

```text
weak local psi/history concentration
  -> weak fatigue degradation
  -> too little new damage/fracture energy outside the pre-crack
  -> crack-tip lag and weak Kt proxy
```

Thank you. Please place the output in OneDrive under a folder name like:

```text
PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_2026-05-28
```

and update/push the FEM outbox on branch:

```text
codex/field-level-metric-representation
```
