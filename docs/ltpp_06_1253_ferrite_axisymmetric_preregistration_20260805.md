# LTPP 06-1253 axisymmetric Ferrite diagnostic preregistration

Status: `PREREGISTERED_NOT_LAUNCHED`

## PIDL Experiment Gate

- Mechanism question: can a section-conditioned layered-elastic model calibrated
  on 1989-1998 FWD basins predict the complete 2003 basin event?
- Claim changed if success: FWD observations can constrain a useful conditional
  elastic transition prior on this one section.
- Claim changed if failure: the current layered-elastic abstraction is not a
  reliable mechanical prior, so no Ferrite field may enter the real-road route.
- Cheaper diagnostic first: observation-side pressure-normalized repeatability
  and load-linearity audit, followed by numerical unit/half-space checks.
- Minimal output asset: one decision note plus numerical gates, six LODO metrics,
  parameter ensemble, and 2003 predictions.
- Code/producer alignment: new Ferrite axisymmetric elasticity code; never reuse
  the SENT phase-field producer. A smallest deterministic Ferrite diagnostic may
  run locally; PIDL training remains prohibited on Mac.
- Success criteria: all numerical gates, LODO, 2003 holdout, baseline improvement,
  and uncertainty-coverage gates below.
- Failure criteria: any fail-closed numerical gate or any primary predictive
  threshold failure.
- Registry destination: `docs/research_frontier.md` and the dedicated attempt
  ledger under the local FWD diagnostic archive.
- Decision: `diagnose first`; no inversion until the observation-linearity and
  numerical solver gates pass.

## Frozen evidence

- Raw SDR 39 package:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_fwd_full_sdr39_v2_20260805`
- Qualification package:
  `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_fwd_qualification_v1_20260805`
- Qualification decision: `QUALIFIED_FOR_LAYERED_ELASTIC_DIAGNOSTIC_ONLY`.
- Evidence label: `ltpp_observation_plus_ferrite_prior`.

## Model

Use infinitesimal, isotropic, quasi-static axisymmetric elasticity in `(r,z)`.
The implementation must include axisymmetric integration weight and hoop strain;
2D plane strain is prohibited.

| Medium | Thickness | Treatment |
|---|---:|---|
| effective surface | 96.52 mm | chip seal merged with AC |
| granular base | 388.62 mm | crushed-gravel base |
| subgrade | to far boundary | homogeneous continuation; no artificial boundary at sampling depth |

Interfaces are perfectly bonded. Viscoelasticity, inertia, damping, nonlinear
base/subgrade response, layer slip, cracking, moisture, and fatigue are outside
this diagnostic.

### Parameters

The maximum inversion vector is:

`log(E_surface_20C), beta_T, log(E_base), log(E_subgrade)`

with `log(E_surface(T)) = log(E_surface_20C) - beta_T * (T - 20 C)`.

| Parameter | Frozen bound |
|---|---:|
| `E_surface_20C` | 0.5-15 GPa |
| `beta_T` | 0-0.12 / C |
| `E_base` | 50-800 MPa |
| `E_subgrade` | 20-300 MPa |

Poisson ratios are not inverted. Run three declared scenarios:

| Scenario | surface | base | subgrade |
|---|---:|---:|---:|
| low | 0.30 | 0.30 | 0.35 |
| nominal | 0.35 | 0.35 | 0.40 |
| high | 0.40 | 0.40 | 0.45 |

## Load and observation mapping

- Apply raw `DROP_LOAD` as uniform pressure in `kPa` over `r <= 0.15 m`.
- Do not apply the derived total force as a second load.
- Derived check: `F_kN = q_kPa * pi * (0.15 m)^2`.
- Compare vertical surface displacement at physical absolute offsets, not sensor
  numbers.
- Common primary offsets are `0, 203, 305, 457, 610, 914, 1524 mm`.
- The 2003 `-305 mm` observation is reserved for the axisymmetry audit.
- The 1995 flagged `1524 mm` sensor is excluded exactly as frozen in the
  qualification package.

## Split and leakage

- Calibration candidate dates: 1989-11-14, 1991-06-10, 1993-07-14,
  1995-10-24, 1997-02-28, and 1998-04-07.
- Internal validation: six leave-one-date-out folds. Each held-out unit contains
  every location, lane, load level, repeated drop, and sensor from that date.
- Final holdout: the complete 2003-05-15 event.
- Repeated drops are grouped by `date x point x lane x drop-height`; they are
  technical repeats, not independent samples.
- The 2003 pressure and temperature may be supplied as known test inputs; 2003
  deflections may not enter fitting, model choice, thresholds, or weights.
- Because aggregate 2003 properties have already been inspected, use the phrase
  `frozen code-level temporal holdout`, never `analyst-blind holdout`.
- 2003-05-15 FWD is prohibited for prediction of the 2003-05-14 distress map.

## Cheaper observation gate

Compute pressure-normalized deflection and robust relative dispersion
`1.4826 * MAD / abs(median)` for two distinct tests:

- repeatability within each calibration
  `date x point x lane x drop-height x offset` group;
- load linearity across the drop-height medians within each calibration
  `date x point x lane x offset` group.

- Pass: both tests have median dispersion <= 5% and p90 <= 10%.
- Fail: `FAIL_OBSERVED_LOAD_LINEARITY`; stop before inversion.
- Empty `NON_DECREASING_DEFL` means only `not flagged`, not independent quality
  certification.

## Numerical preregistration

- Primary domain: radius 6.4 m and depth 6.4 m.
- Extended-domain check: radius 9.6 m and depth 9.6 m.
- Axis: `u_r=0`; outer side: `u_r=0`; bottom: `u_z=0`; unloaded top free.
- Use Q2 axisymmetric elements.
- Near-load/surface target mesh sizes: 25, 12.5, and 6.25 mm for
  coarse/medium/fine, with outward growth ratio <= 1.25.

Fail closed before inversion unless all pass:

| Gate | Threshold |
|---|---|
| reaction balance | relative error <= 1e-5 |
| doubled-pressure linearity | relative displacement error <= 1e-8 |
| homogeneous half-space | sensor displacement error <= 1% |
| medium versus fine | every sensor <= max(0.5 micrometre, 1%); objective change <= 0.5% |
| primary versus extended domain | every sensor <= max(0.5 micrometre, 0.5%) |

## Objective and uncertainty

- Equal total weight for each date.
- Equal weight for each point/lane/drop-height group.
- Equal one-third weight for offset zones `0-305`, `457-610`, and
  `914-1524 mm`.
- Use Huber loss with transition 1.5 on residuals scaled by training-fold-only
  `max(2 micrometres, 2% of median absolute deflection, 1.4826 MAD)`.
- Run 16 log-Latin-hypercube initializations for each Poisson-ratio scenario and
  each LODO fold.
- Profile each free parameter at at least 15 points.
- Retain every solution within 2% of the best objective.

A parameter may be called conditionally identifiable only when its 90% ensemble
interval does not touch a bound, `P95/P5 < 3`, and all absolute parameter
correlations are below 0.95. Otherwise report basin predictions as an ensemble
without a unique modulus claim.

## Frozen predictive metrics

Primary prediction metric: zone-balanced RMS relative error, computed after
technical-repeat aggregation. Comparison baseline: calibration-only robust
regression using physical offset, pressure, pavement-surface temperature, and
their predeclared low-order interactions.

The diagnostic passes only if all hold:

- median six-fold LODO error <= 10%;
- every LODO date error <= 15%;
- 2003 common-seven-offset error <= 10%;
- every 2003 offset-zone error <= 15%;
- at least 10% relative improvement over the observation-only baseline on 2003;
- 90% predictive ensemble coverage between 80% and 100%;
- median 90% interval width <= 30% of observed magnitude;
- at least 75% of 2003 paired `+/-305 mm` observations agree within
  `max(5 micrometres, 10%)`.

Decision labels:

- `PASS_CONDITIONAL_EFFECTIVE_MODULI`;
- `PASS_BASIN_ONLY_NONIDENTIFIABLE`;
- `FAIL_LAYERED_ELASTIC_DIAGNOSTIC`;
- numerical failure: `STOP_BEFORE_INVERSION`.

## Required assets

- `00_preregistration.json`;
- `01_run_provenance.json`;
- `02_numerical_gates.csv`;
- `03_lodo_metrics.csv`;
- `04_parameter_ensemble.csv`;
- `05_holdout_2003_predictions.csv`;
- `decision.md`.

Any generated figure requires a same-stem research sidecar. Provenance must
include raw/qualification manifest hashes, source and environment hashes, Julia
and Ferrite versions, exact command, mesh specifications, parameter bounds, and
the timestamp at which 2003 individual residuals were first evaluated.

## Claim boundary

Passing supports only same-section FWD basin prediction by a conditional
quasi-static effective-stiffness ensemble. It does not authorize phase-field
teacher status, real mechanical labels, crack geometry/tip/initiation claims,
traffic/moisture selection, PIDL training, or cross-road generalization.
