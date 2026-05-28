# Tip-Local Exp18 Summary (2026-05-28)

## Purpose

This matrix tested whether a compact moving tip-local correction head can fix the
Phase 1 field-level mismatch without changing the baseline physics loss.

The discriminator was not `N_f` alone. The gate was whether the final alpha field
becomes more FEM-like near the process zone, rather than another coherent
centerline/right-boundary, boundary-saturating path.

## Inputs

- Taobo code dir: `/mnt/data2/drtao/projects/phase-field-pidl-tip-local-net-18runs-f2d648`
- Log dir: `/mnt/data2/drtao/projects/phase-field-pidl-tip-local-net-18runs-f2d648/SENS_tensile/run_logs/exp18_tiplocal_matrix_20260526_070118`
- Local artifact dir: `docs/figures/tiplocal_exp18_20260528/`

Main local artifacts:

- `docs/figures/tiplocal_exp18_20260528/exp18_all_logs_summary_20260528.csv`
- `docs/figures/tiplocal_exp18_20260528/finished_runs_key_table.csv`
- `docs/figures/tiplocal_exp18_20260528/finished_runs_field_energy_summary.csv`
- `docs/figures/tiplocal_exp18_20260528/final_alpha_vs_reverseBC_FEM_montage.png`
- `docs/figures/tiplocal_exp18_20260528/finished_runs_diagnostics.png`

## Key Results

| Variant | first hit | confirmed stop | final alpha_bar_max | final Kt | field-shape note |
|---|---:|---:|---:|---:|---|
| MLP S1 alpha | 79 | 82 | 6.59 | 611 | centerline-dominated path |
| MLP S1 uv | 81 | 84 | 10.53 | 886 | centerline-dominated path |
| MLP S2 all | 76 | 79 | 10.85 | 784 | centerline path, many boundary nodes |
| MLP S2 all + adaptive hist | 76 | 79 | 10.85 | 784 | identical to fixed hist in final metrics |
| Fourier S1 alpha | 81 | 84 | 9.03 | 741 | centerline-dominated path |
| Fourier S1 uv | 80 | 83 | 10.88 | 921 | centerline-dominated path |
| Fourier S2 all | 76 | 79 | 8.02 | 772 | centerline-dominated path |
| Fourier S2 uv short | 78 | 81 | 11.29 | 948 | centerline-dominated path |
| SIREN S1 alpha | 79 | 82 | 7.00 | 619 | centerline-dominated path |
| SIREN S1 uv | failed | failed | n/a | n/a | NaN/failure |
| SIREN S2 all | 75 | 78 | 6.83 | 713 | centerline-dominated path |
| SIREN S2 all + adaptive hist wr=0.10 | 76 | 79 | 10.40 | 544 | centerline-dominated path |
| SIREN S2 uv | 77 | 80 | 9.57 | 1176 | centerline-dominated path |

The completed matrix spans roughly:

- first boundary hit: `N=75-81`
- confirmed stop: `N=78-84`
- final `alpha_bar_max`: `6.6-11.3`
- final `Kt`: `~400-1176`

## Interpretation

The tip-local correction head changes scalar metrics and fracture timing, but
does not recover the FEM-like process-zone field. The montage against reverseBC
FEM shows the same qualitative failure mode across the finished variants:
damage reaches the right boundary through a coherent centerline/right-edge path,
whereas the FEM reference has a broader, noisier localized process zone.

Width caveat: this is a morphology claim, not a same-probe measured claim that
the PIDL high-alpha core is always narrower than FEM. By visual judgement, the
bright core widths can look similar. The stronger observed difference is that
PIDL is more coherent, centerline-dominated, and boundary-saturating, while FEM
has a more diffuse and irregular process-zone envelope. A strict width claim
requires common FEM/PIDL morphology metrics.

The SIREN local head increases correction activity in some runs, but this does
not translate into a better field. `uv_only` often raises `Kt` and can keep
`alpha_bar_max` high, while `alpha_only` gives larger local correction ratios;
neither mode fixes the spatial morphology. S2 refinement and adaptive
`lambda_hist` also do not change the conclusion.

## Decision

Close this tip-local head family as a field-level closure route unless the next
method changes the representation more fundamentally. It is useful evidence
that small local correction heads and output-mode switches are not enough.

The next clean method, if we continue method development, should be a stronger
representation-localization discriminator:

- SDF/discontinuity embedding, or
- FBPINN/domain-decomposed tip patch with its own local coordinates and overlap
  conditions.

Do not launch another broad sweep until the field-level comparison metric is
defined first.
