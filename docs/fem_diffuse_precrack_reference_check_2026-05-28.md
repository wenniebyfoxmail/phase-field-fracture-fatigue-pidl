# FEM Diffuse-Precrack Reference Check

Date: 2026-05-28

## Purpose

This checks the reciprocal FEM diagnostic requested after we noticed the notch
definition mismatch:

```text
FEM void slit/notch
vs
FEM continuous material with a prescribed d=1 diffuse pre-crack band
```

The goal is to understand the FEM-side effect of changing the initial crack
representation before using the new result as a PIDL target.

## Inputs

Old void FEM reference:

```text
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_cyclewise_mechanism_2026-05-28/reverseBC_u12_cyclewise_mechanism_metrics.csv
```

Fine void FEM reference:

```text
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_fine_reverseBC_u12_cyclewise_mechanism_2026-05-28/fine_reverseBC_u12_cyclewise_mechanism_metrics.csv
```

Diffuse-precrack FEM diagnostic:

```text
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_2026-05-28/reverseBC_u12_diffuse_precrack_cyclewise_mechanism_metrics.csv
```

Generated outputs:

```text
_analysis_fem_mechanism_20260528/fem_notch_variant_cyclewise_comparison.csv
_analysis_fem_mechanism_20260528/fem_notch_variant_cyclewise_summary.csv
_analysis_fem_mechanism_20260528/figures/fem_notch_variant_cyclewise_comparison.png
_analysis_fem_mechanism_20260528/figures/fem_notch_variant_cyclewise_comparison.pdf
```

## Mesh / Geometry Notes

| FEM case | Cycles | Nodes | Elements | Initial notch/pre-crack |
|---|---:|---:|---:|---|
| old void FEM | c1-c74 | 77900 | 77730 | void slit/notch |
| fine void FEM | c1-c69 | 10401 | 10261 | void slit/notch |
| diffuse pre-crack FEM | c1-c69 | 45591 | 45000 | material retained, hard `d=1` band |

The diffuse-precrack README reports a plate-coordinate mask:

```text
x <= 0.5 and |y - 0.5| <= 0.02
```

For crack-tip plotting, the diffuse-precrack `x_tip` values are shifted by
`-0.5` to compare with the centred void-FEM coordinates.

Important caveat: the usual `x_tip_d095` metric is contaminated by the
prescribed `d=1` band at early cycles. It should be read as a front-position
proxy after centring, not as the same physical crack-tip detector as in the void
notch cases.

## Selected Values

| Cycle | Metric | Old void FEM | Fine void FEM | Diffuse pre-crack FEM |
|---:|---|---:|---:|---:|
| 1 | `E_d` | 5.08e-7 | 2.27e-7 | 0.012719 |
| 40 | `Delta E_d` from c1 | 0.002159 | 0.002303 | 0.002131 |
| 69 | `Delta E_d` from c1 | 0.004610 | 0.005589 | 0.005306 |
| 40 | history elem max | 103.071 | 80.830 | 1.565 |
| 69 | history elem max | 212.334 | 126.288 | 2.082 |
| 40 | `f_min` | 2.96e-4 | 5.54e-4 | 2.42e-1 |
| 69 | `f_min` | 2.62e-4 | 1.65e-4 | 1.55e-1 |
| 40 | `Kt_proxy` | 1591.51 | 868.75 | 22.05 |
| 69 | `Kt_proxy` | 3330.61 | 4101.52 | 12.10 |
| 69 | centred `x_tip_d095` | 0.414 | 0.499 | 0.499 |

## Interpretation

The diffuse-precrack FEM run answers two different questions at once.

First, absolute `E_d` is not comparable across notch conventions. The
diffuse-precrack case starts with a large prescribed fracture/damage energy:

```text
E_d(c1) = 0.012719
```

This is expected because the material is retained and a hard `d=1` band is
integrated as damage energy. Therefore, only incremental `E_d` after c1 is a
reasonable scalar comparison.

Second, the incremental global energy response is surprisingly close to the
void-notch FEM references. By c69:

```text
old void Delta E_d    = 0.004610
fine void Delta E_d   = 0.005589
diffuse Delta E_d     = 0.005306
```

So changing the notch convention does not destroy the global energy scale after
the initial offset is removed.

The local mechanism is very different. The diffuse-precrack case has much lower
history peaks, much weaker fatigue degradation, and much smaller `Kt_proxy`:

```text
at c40:
  history max: 1.56 diffuse vs 80.83 fine void
  f_min:       0.242 diffuse vs 5.54e-4 fine void
  Kt_proxy:    22.0 diffuse vs 868.7 fine void
```

This means the prescribed diffuse band removes much of the void-notch local
stress/history concentration mechanism. It still reaches the right boundary by
c69, but it does so with a different local driving chain.

## Consequence For PIDL

This result is useful, but it should not be treated as "the new ground truth"
without caveats. It shows that PIDL's diffuse-damage notch convention can be
made FEM-consistent in a scalar/global sense, but the local mechanism becomes a
different FEM problem from the void-notch reference.

For PIDL comparison we should therefore report three FEM references:

1. old void FEM,
2. fine void FEM,
3. diffuse-precrack FEM.

The strongest fair test for the current PIDL void-notch diagnostic is:

```text
Does PIDL move toward diffuse-precrack FEM in absolute notch convention
while also moving toward void-FEM in local crack-tip concentration?
```

If the PIDL void-notch mask run only changes the scalar `E_d` baseline but does
not improve local history, `f_min`, `Kt`, or field shape, then the original
mechanism diagnosis still stands.
