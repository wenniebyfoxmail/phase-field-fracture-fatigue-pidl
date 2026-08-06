# LTPP geoforecast spatial-registration audit v1 result

## Decision

`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL`

Only `2/8` frozen `06-1253` dates passed the externally reviewed, one-shot
conditional internal-grid gate. The current eight-date carrier is therefore
not qualified for 2-D crack-position or continuation-tip modelling.

## Frozen execution

- Preregistration SHA-256:
  `3701136ae9a030e1db0f65ad06a3a818b3f35d151d92054f80a7c021bd7f3dce`
- Script SHA-256:
  `5f787b2ffdcc1e9d5d3a2ca10bc3a558b08e3f0fc201c92466a43538c211bac1`
- Frozen grid receipt SHA-256:
  `5b787c11f69d61fadd124cbdd488f24c12d0cbab8a0ab2d8b3ec2c03d37f6e42`
- Freeze commit: `5e4b32eea92177237ff5a6034a107a34e5de814b`
- Result manifest SHA-256:
  `5eedf777653eab0a50d98b74cb91fa70896170d935c96d3142e8ebac8df6dbb3`
- Audit-result SHA-256:
  `925ceeaa7dd86a7b457067544f162ecdc7492a0ce95a974c859046c88d5b7666`

No prediction model or perturbation analysis was run. Frozen crack labels were
not modified.

## Per-date result

| Survey date | Status | Missing lines | Median m | p95 m | Max m |
|---|---|---:|---:|---:|---:|
| 1991-06-10 | not qualified | 0 | 0.1056 | 0.1573 | 0.1586 |
| 1995-10-24 | insufficient controls | 9 | — | — | — |
| 1997-02-28 | not qualified | 0 | 0.0479 | 0.1342 | 0.1379 |
| 1998-04-07 | qualified | 0 | 0.0290 | 0.0589 | 0.0674 |
| 2001-09-13 | insufficient controls | 3 | — | — | — |
| 2003-05-14 | not qualified | 0 | 0.1384 | 0.2073 | 0.2074 |
| 2007-11-06 | insufficient controls | 4 | — | — | — |
| 2012-04-17 | qualified | 0 | 0.0169 | 0.0263 | 0.0280 |

The frozen gates were median `<=0.05 m`, linear-quantile p95 `<=0.10 m`, and
maximum `<=0.20 m`, with every fixed calibration and held-out line present.

## Interpretation

The failure is not merely one bad year. Three dates lacked the fixed required
controls, and three more had complete controls but failed at least one spatial
error threshold. In particular, 2003 exceeded the maximum gate, while 1991 and
1997 failed median or p95 gates.

This supports only the narrow statement that the **existing frozen
deskew/crop/resize carrier** is inadequate for eight-date 2-D position/tip
modelling. It does not prove that LTPP maps can never be registered, and it does
not invalidate separately reviewed scalar crack-length work.

## Consequence and next action

- Do not train a 2-D crack-position, tip, field, CNN, GNN, or PIDL model on this
  eight-date carrier.
- Do not delete failed dates or try a transform rescue inside v1.
- Preserve the current scalar-length track with explicit measurement-noise
  limitations.
- A future spatial route requires a new, independently reviewed registration or
  acquisition track with an external validation signal; it is not an amendment
  to this failed v1 audit.

## Result assets

The complete local package is:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_spatial_registration_audit_v1_20260806`

It contains the JSON receipt, per-date and per-axis CSV files, control points,
decision note, eight-panel overlay with validated sidecar, manifest, and attempt
ledger. All manifest entries and the figure-sidecar validator pass.
