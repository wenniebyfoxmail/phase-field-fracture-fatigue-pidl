# Latest aligned FEM/PIDL state-field comparison

## Purpose

This archive compares the latest aligned soft-hist0 FEM field export against the
mapped-state PIDL export for the FEM-like substep PIDL branch.

The goal is to separate four possible sources of mismatch:

- initial state mismatch,
- cycle/state timing mismatch,
- stress/strain localisation mismatch,
- fatigue-history/degradation mismatch.

## Source data

FEM source:

- `FEM cyclic 012/cases/standard/raw_data/state_field_exports/latest_align_soft_hist0_state_field_export_20260608/latest_align_soft_hist0_state_fields.mat`
- `FEM cyclic 012/cases/standard/raw_data/state_field_exports/latest_align_soft_hist0_state_field_export_20260608/latest_align_soft_hist0_state_index.csv`
- standard cycle energy reference:
  `FEM cyclic 012/cases/standard/raw_data/reverseBC_u12_diffuse_precrack_soft_hist0_cyclewise_mechanism_metrics.csv`

PIDL source:

- `PIDL cyclic 012/cases/stateTiming_substeps025_untilFrac_Nphys120_Nstep600/analysis/mapped_state_fields_20260608/`

## Alignment rule

The FEM field export is on 45,000 quadrilateral element means. The PIDL mapped
export is on 90,000 triangular elements. PIDL coordinates are centred on
`[-0.5, 0.5] x [-0.5, 0.5]`, while FEM coordinates are on `[0, 1] x [0, 1]`.

For the comparison:

- PIDL element centroids are shifted by `+0.5` in `x` and `y`.
- Each PIDL triangle is assigned to its nearest FEM quadrilateral centroid.
- Exactly two PIDL triangles map to each FEM element.
- PIDL fields are area-averaged onto the FEM element grid before subtraction.

Mapping diagnostic:

- mean centroid distance: `0.001935`
- p99 distance: `0.003765`
- mapped triangle count per FEM element: exactly `2` for all 45,000 elements

## Outputs

Figures:

- `figures/energy_histories_latest_aligned.png`
- `figures/state0_c1_alignment_audit.png`
- `figures/state_scalar_reductions_latest_aligned.png`
- `figures/fem_c1_state_timing_fields.png`
- `figures/residual_fields_damage_history_degradation_peak_states.png`
- `figures/residual_fields_energy_drivers_peak_states.png`
- `figures/residual_fields_strain_stress_peak_states.png`

Tables:

- `tables/peak_energy_comparison_latest_aligned.csv`
- `tables/state_scalar_reductions_latest_aligned.csv`
- `tables/field_error_metrics_latest_aligned.csv`
- `tables/delta_alpha_bar_overlap_latest_aligned.csv`
- `tables/pidl_to_fem_mapping_diagnostics.csv`

## Main findings

### 1. Initial state is now essentially aligned

At `state0_initial_unloaded_prehistory`, FEM and PIDL agree on the initial soft
precrack:

- damage max: FEM `0.905`, PIDL `0.905`
- damage mean: FEM `0.0378045`, PIDL `0.0378045`
- `alpha_bar = 0` everywhere in both
- `f_fatigue = 1` everywhere in both
- unloaded strain, stress, and `psi` are zero in both

So the remaining mismatch is not mainly an initial-condition or coordinate
alignment problem.

Cycle-label note: the residual montages start at `c1_peak`, not at the initial
condition. `c1_peak` is after the first cycle's loaded substeps up to
`uy=0.12` and after the state history refresh. The
`state0_c1_alignment_audit` figure shows that `state0` is aligned and that the
first visible residual appears after the first loaded solve/history update.

### 2. Elastic energy is close early, but crack-surface energy diverges

At mapped peak states, PIDL/FEM energy ratios are:

| cycle | E_el PIDL/FEM | E_d PIDL/FEM |
|---:|---:|---:|
| 1 | 0.991 | 0.955 |
| 20 | 0.997 | 0.781 |
| 40 | 1.002 | 0.621 |
| 60 | 1.142 | 0.502 |
| 69 | 4.789 | 0.448 |

The cleanest scalar gap is `E_d`: FEM keeps accumulating crack-surface energy,
while PIDL remains near its initial diffuse-crack level. PIDL `E_hist` in the
saved mapped states is tiny, so it is not appearing as a large visible penalty
after the saved history refresh.

The plotted FEM field-integral check is
`int(g(d) psi_plus + psi_minus) dOmega` computed from the latest state MAT. It
is a reconstruction of FEM elastic energy from exported element fields and is
only used as a consistency check against the cyclewise FEM `E_el` column. It is
not the crack-surface energy and does not include the fatigue factor `f`.

### 3. Damage front is similar, but history/fatigue is not

The damage band/front is broadly in the same corridor, especially early. The
large difference is the accumulated history:

- c69 `alpha_bar_max`: FEM `19.53`, PIDL `2.00`
- c69 `alpha_bar_mean`: FEM `0.345`, PIDL `0.294`
- c69 `f_fatigue_min`: FEM `0.0146`, PIDL `0.170`

That means PIDL is much less fatigue-weakened at the most exhausted locations,
even though the phase-field damage band reaches a similar geometric route.

The left precrack band is a modelling trap. In this aligned soft-precrack FEM
setting, the precrack is retained material with high initial damage, not a
void. Therefore FEM can still accumulate tensile history and fatigue degradation
inside/near the old precrack band after loading. If the intended physical
meaning is "the old crack faces should not accumulate new fatigue history",
then this soft-precrack benchmark still needs a history/fatigue mask in the
initial crack band, or a void-notch benchmark should be used for that question.
The current comparison is valid for the chosen soft-precrack model, but it
exposes that FEM and PIDL treat old crack-band history evolution differently.

### 4. Raw driver is spiky in PIDL, not process-zone distributed

PIDL raw `psi+` has very large maxima, but its p99 is tiny compared with FEM.
For example at c69 peak:

- `psi_raw_max`: FEM `2433.7`, PIDL `2638.7`
- `psi_raw_p99`: FEM `500.1`, PIDL `0.555`

So PIDL can create raw spikes, but most of the process-zone distribution that
FEM carries is missing. This is exactly the reduction trap: max values alone
make PIDL look closer than the field distribution really is.

### 5. The degraded/effective response is the key late-cycle suspect

For the active driver `g(alpha) psi+`, PIDL is close early but too weak by p99
late:

- c1 `g psi+ p99`: FEM `0.0358`, PIDL `0.0341`
- c69 `g psi+ p99`: FEM `0.1059`, PIDL `0.0336`

For degraded/effective principal stress, the late-cycle relation flips:

- c69 `sigma_eff_p1_p99`: FEM `0.0189`, PIDL `0.274`

This suggests PIDL is not relaxing/degrading the local stiffness response in
the same way as FEM near the late crack/process zone.

### 6. Delta alpha_bar starts aligned, then loses the FEM process zone

Top-1% PIDL `delta alpha_bar` overlap with the FEM damaged process zone:

| interval | overlap with FEM d>0.95 |
|---|---:|
| state0 -> c1 peak | 0.829 |
| c1 peak -> c20 peak | 0.091 |
| c20 peak -> c40 peak | 0.129 |
| c40 peak -> c60 peak | 0.149 |
| c60 peak -> c69 peak | 0.084 |

So the first increment is well aligned, but the later cycle-to-cycle history
updates stop following the FEM process zone.

## Interpretation

The current strict comparison says the big gap is not caused by initial state,
coordinate convention, or mesh-cell mapping. The mismatch grows inside the
nonlinear feedback loop:

`strain/stress localisation -> g(alpha) psi+ -> alpha_bar/history -> f_fatigue -> local stiffness/degradation -> next strain/stress localisation`.

The next diagnostic should therefore focus less on another global architecture
change and more on FEM-like update timing/local degradation response:

- compare pre-history-refresh vs post-history-refresh PIDL fields at early
  cycles,
- test a FEM-like alternate minimisation micro-solve for c1/c2/c3,
- test whether PIDL should update fatigue/history inside substeps rather than
  only after the coupled NN fit,
- audit whether PIDL's effective stress/degradation split matches the FEM AMOR
  split in the fully damaged/process-zone region.

## Caveat

FEM `E_d` is taken from the standard cyclewise metrics, not recomputed from the
new MAT. The latest FEM MAT contains state fields, strain, stress, and `psi`,
but not phase-field gradient fields needed to reconstruct crack-surface energy
from scratch.
