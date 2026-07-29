# Corrected Pi-Transfer Controls Decision

## Verdict

**Accepted as a diagnostic/tooling control, not as road validation.** The
corrected convention is confirmed as

\[
w_1=G_c/\ell,\qquad w_{1,\mathrm{norm}}=1.
\]

The legacy `w1 = c_w G_c/ell` convention remains quarantine provenance only,
because `compute_energy.py` already applies the `1/c_w` factor inside the
phase-field functional.

## F1a: Exact-Pi Scaling/I-O Diagnostic

F1 used an archived eta0 FEM trajectory at `c20/c40/c60/c89` and replayed its
fields through two dimensional realizations:

| quantity | normalized FEM realization | dimensional candidate |
|---|---:|---:|
| `E` | 1 | 3 |
| `G_c` | 0.01 | 0.3 |
| `ell` | 0.01 | 0.1 |
| `L` | 1 | 10 |
| `h` | 0.01 | 0.1 |
| `Umax` | 0.12 | 1.2 |
| `alpha_T` | 0.5 | 1.5 |
| `w1=G_c/ell` | 1 | 3 |

All locked scalar Pi, plane-state/model-form/BC labels, and declared
geometry/load ratios were `matched`, including:

\[
\ell/L=0.01,\quad h/\ell=1,\quad G_c/(E\ell)=1,
\]

\[
\alpha_T/w_1=0.5,\quad E(U/L)^2/w_1=0.0144.
\]

After normalizing `alpha`, `alpha_bar/w1`, `raw/w1`, and `active/w1`, the
largest error over all four cycles was `1.7764e-15`; all area-weighted MAEs
were below `1e-13` and correlations were one to floating-point tolerance.
The event-state map is `c89 -> c89` by construction.

This is an **archived FEM exact-dimensional replay**. It validates only the
scaling, normalization, and field-I/O path. It does not satisfy F1b independent
solver invariance; the c89 event is inherited by construction. F1b remains
blocked pending an approved Windows-FEM producer output.

## F2: BC Negative Control

F2 used two archived FEM states on exactly identical element centroids and
areas. Material, geometry, load amplitude, mesh, AT1 model, plane strain, and
all observable scalar Pi groups match. The changed factor is the horizontal
constraint:

- reference: bottom-left `ux` anchor with free lateral response;
- candidate: top-and-bottom `ux` clamp (`reverseBC`).

The event changed from `c82` to `c74` (`Delta cycle = -8`). At each case's own
event, FEM-centred field differences were:

| field | metric | value |
|---|---|---:|
| alpha | area-weighted linear MAE | 0.0002110 |
| alpha | area-weighted linear RMSE | 0.0027594 |
| alpha | correlation | 0.9990784 |
| alpha_bar/w1 | area-weighted log10 MAE | 0.0973039 |
| alpha_bar/w1 | area-weighted log10 RMSE | 0.1251156 |
| alpha_bar/w1 | correlation | 0.9945853 |

Thus, matching scalar Pi groups is not sufficient when BC/model form differs.
The own-event alpha/history morphology remains close, so this result should be
read primarily as a timing/constraint sensitivity, not as evidence of a large
mechanism-field divergence. The free-lateral c82 archive lacks raw energy;
F2 raw and active-driver comparisons are explicitly `unobservable` and were
not imputed.

## Excluded Auxiliary Evidence

`Umax_012_all_versions_20260729` was reviewed but not promoted into the primary
F2. Its 2x2 factors change hard/soft initial crack and 5/8-step loading
protocol. It is useful protocol-sensitivity evidence, but the existing BC pair
is the cleaner single-factor negative control. None of those variants are
independent roads.

## Claim Boundary

These controls do **not** establish:

- validation on a real road or layered pavement;
- transfer across plane stress/plane strain/3D kinematics;
- temperature, viscoelastic, rate, healing, moisture, or heterogeneous-layer
  effects;
- calibration or identifiability of `E`, `G_c`, `ell`, or `alpha_T` from field
  measurements;
- mapping a computational cycle to axle passages, ESAL, calendar time, or RUL;
- forecast or inverse-model performance.

The next evidence rung is a genuinely independent dimensional F1 solve under
the same complete Pi vector, followed by one-factor plane-state/load-form
controls and only then measured layered-road anchoring.

## Primary Evidence

- `pi_transfer_audit.csv`: matched/mismatched/unobservable Pi audit.
- `fem_centred_field_metrics.csv`: area-weighted field gates.
- `event_state_map.csv`: same-cycle and own-event semantics.
- `scale_contracts.json`: dimensional and normalized contracts.
- `normalized_control_fields.npz`: locked normalized fields.
- `f1_f2_fem_centred_fields.png`: FEM, candidate, and residual panels.
- `RUN_MANIFEST.json` and `HASHES.sha256`: input/output provenance.
