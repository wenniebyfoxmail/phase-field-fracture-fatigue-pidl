# Field-Level Comparison Metric Plan

Date: 2026-05-28

Purpose: define a common FEM/PIDL gate before launching another representation
experiment. The metric should decide whether a new method improves field
likeness, not merely `N_f`, `alpha_bar_max`, or visual impression.

## Scope

First target is Phase-1 toy-unit SENT at `Umax=0.12`, reverse/FEM-anchor BC
alignment where available. PCC should reuse the same structure later, but should
not be mixed into this first metric.

Working convention after discussion: for the current evidence base, use
**reverseBC FEM** as the primary aligned field-level reference because most PIDL
variants have already been evaluated against it and FEM reruns are cheap. Use
**femAnchorBC PIDL** as the complementary alignment diagnostic, not as the only
default baseline.

## Principle

Compare FEM and PIDL on the same spatial probes and the same cycle/stage
definitions. Native FEM mesh plots and native PIDL collocation plots are useful
for visual audit, but not enough for a decision metric.

## Primary Data

Use common probes:

- FEM projected to PIDL probes / shared centroids when available.
- PIDL evaluated on the same probe coordinates.
- Current starting artifacts:
  - `SENS_tensile/alignment_mesh_probe_u012_baseline.csv`
  - `SENS_tensile/alignment_mesh_probe_u012_femAnchorBC.csv`
  - `SENS_tensile/alignment_compare_baseline_vs_femAnchorBC.csv`
  - existing FEM reverseBC snapshots used by the montage.

Missing P0 artifact for the primary reference:

- `SENS_tensile/alignment_mesh_probe_u012_reverseBC.csv` -- completed after
  Windows-FEM handoff `5c9c0e5`.

The full reverseBC `u12` `.mat` handoff is a MATLAB v7.3/HDF5 combined file.
`SENS_tensile/posthoc_mesh_probe_alignment.py` now supports this format through
`--fem-combined-mat`.

Use matched cycles:

- fixed physical cycles: `N = 40, 70, 82` for Phase-1 `Umax=0.12`;
- optional event-normalized checkpoints: `0.5 N_f`, `0.85 N_f`, `N_f`;
- report both if a new method shifts `N_f` substantially.

## Metric Blocks

### A. Probe Field Error

For each matched cycle and region, compare:

- damage field: FEM `d` vs PIDL `alpha`;
- fatigue history: `alpha_bar`;
- tensile driver: `psi_plus`;
- degraded driver: `g(alpha) psi_plus`;
- fatigue-weighted driver: `f(alpha_bar) psi_plus`.

Regions:

- full domain;
- tip ball `B_l0`;
- tip ball `B_2l0`;
- crack strip;
- right-boundary band.

Reductions:

- mean;
- p95 / p99;
- top-1% mean;
- area integral where area weights are available.

Distance:

```text
J_probe = mean_abs_log_ratio(PIDL_metric, FEM_metric)
```

Use log-ratio rather than raw difference so that order-of-magnitude failures are
visible without letting one peak dominate the whole score.

### B. Morphology Error

This block tests the shape of the localized process zone, not only its peak.

For thresholded masks on common probes:

- damage mask: `d or alpha > 0.5`, `> 0.9`;
- fatigue-history mask: `alpha_bar > alpha_T`, `> 2 alpha_T`;
- driver mask: top 1% and top 5% of `g psi_plus` or `f psi_plus`.

Report:

- connected area;
- centroid `(x_c, y_c)`;
- covariance widths `(sigma_x, sigma_y)`;
- aspect ratio `sigma_x / sigma_y`;
- boundary-contact fraction at the right edge;
- number of connected components;
- skeleton length / area, if grid interpolation is reliable.

Distance:

```text
J_morph = weighted_log_ratio(widths, area, aspect, boundary_contact)
          + centroid_distance / l0
```

Important caveat: this is where "thin band" must become measurable. Until this
block is computed, use wording such as "centerline-dominated" or
"boundary-saturating", not "narrower than FEM".

### C. Trajectory Error

Use the existing `a(N)` / boundary evolution logic:

- crack-tip or boundary-hit trajectory RMS;
- `alpha_bar_max(N)`;
- right-boundary damage pre-`N_f`;
- process-zone integrals over cycle.

This remains secondary because a good endpoint `N_f` can hide field mismatch.

### D. Guardrails

A representation passes the field gate only if it does not break:

- reaction / energy same-order calibration;
- V7 side-boundary residual audit;
- symmetry audit where symmetry is expected;
- no NaN / no optimizer collapse.

These guardrails are not the field score itself; they prevent a visually better
field from being achieved by an unphysical solution.

## Proposed Composite Score

Lower is better:

```text
J_field =
  0.35 * J_morph_damage
+ 0.20 * J_probe_alpha_bar
+ 0.20 * J_probe_driver
+ 0.15 * J_trajectory
+ 0.10 * J_guardrail_penalty
```

The first implementation should report all components separately. The composite
is for ranking, not for hiding tradeoffs.

## Promotion Rule

A new representation is worth promoting to `N=100` or a broader sweep only if:

1. `J_morph_damage` improves over the aligned baseline, reported against
   reverseBC FEM first and femAnchorBC PIDL second where available;
2. `J_probe_driver` improves in the tip region;
3. `N_f` does not become worse by more than about 15%;
4. guardrails remain acceptable.

If only `N_f` or `alpha_bar_max` improves while morphology remains
centerline-dominated / boundary-saturating, close the variant as another scalar
metric fix.

## Branch Plan

1. Implement the common-probe metric first.
2. Re-score baseline, reverseBC-referenced evidence, femAnchorBC,
   adaptive/refinement, and Exp18 representative runs.
3. Use the score to choose the next representation.

Update after the 2026-05-28 audit: a Heaviside/XFEM jump-head discontinuity
branch (`claude/exp/alpha3-xfem-jump`) was already tried. It passed early
sanity/fatigue smoke tests but only reached T4 modal stationarity `0.50`, below
the planned `>= 0.95` gate. Therefore the next clean architecture discriminator
should be FBPINN/domain-decomposed tip patch, unless the discontinuity branch is
explicitly revived with fixed tip tracking and judged by this metric.
