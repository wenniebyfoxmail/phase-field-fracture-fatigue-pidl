# FEM/PIDL Pre-Crack-Masked Baseline Comparison

Date: 2026-05-28

## Question

FEM and PIDL use different initial notch/pre-crack representations:

- FEM treats the notch as a void.
- PIDL treats the initial crack/notch as a `d=1` damaged region inside the
  computational domain.

This affects absolute `E_d` and may also affect fatigue/damage accumulation.
To test whether the mechanism gap is only caused by the initial crack region,
we recomputed diagnostics outside a shared geometric pre-crack corridor:

```text
exclude x <= 0 and |y| <= 0.02
```

The half-width `0.02` is about `2*l0`.

## Outputs

```text
_analysis_fem_mechanism_20260528/baseline_fem_pidl_precrack_masked_comparison.csv
_analysis_fem_mechanism_20260528/figures/baseline_fem_pidl_precrack_masked_comparison.png
```

The PIDL scalar exporter now also writes outside-precrack columns to:

```text
_analysis_fem_mechanism_20260528/baseline_pidl_cyclewise_scalar_diagnostics/element_diagnostics_summary.csv
```

## Mask Caveat

The same geometric mask excludes different element counts because FEM and PIDL
use different meshes:

| Method | Elements in pre-crack mask | Elements outside mask |
|---|---:|---:|
| FEM | 2053 | 75677 |
| PIDL | 11599 | 55677 |

This is expected and should be reported whenever masked scalar comparisons are
used.

## Key Results

Selected outside-precrack values:

| Cycle | FEM hist max | PIDL hist max | Ratio | FEM min `f` | PIDL min `f` | Ratio |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 10.988 | 2.502 | 0.228 | 3.03e-2 | 1.11e-1 | 3.67 |
| 40 | 98.355 | 3.828 | 0.039 | 1.38e-2 | 5.34e-2 | 3.88 |
| 70 | 215.476 | 4.046 | 0.019 | 3.50e-3 | 4.84e-2 | 13.82 |
| 74 | 227.955 | 4.158 | 0.018 | 3.46e-3 | 4.61e-2 | 13.31 |

Selected incremental damage energy:

| Cycle | FEM `Delta E_d` | PIDL outside-precrack `Delta E_d` | Ratio |
|---:|---:|---:|---:|
| 40 | 0.002159 | 0.000541 | 0.250 |
| 70 | 0.004718 | 0.001649 | 0.349 |
| 74 | 0.005445 | 0.001823 | 0.335 |

Median ratios over c10-c74:

| Quantity | PIDL/FEM median |
|---|---:|
| outside history max | 0.035 |
| outside history mean | 0.641 |
| outside min `f` | 4.000 |
| outside `psi_plus` max | 2.1e-5 |
| outside incremental `E_d` | 0.258 |

## Interpretation

The different notch representation is real and important, but it does not
explain away the baseline mechanism gap.

After excluding the initial crack corridor:

- FEM still develops a much stronger outside-precrack history peak.
- PIDL outside-precrack `f_min` remains several to more than ten times larger,
  so local fatigue degradation is still too weak.
- PIDL outside-precrack incremental damage energy is only about one quarter to
  one third of FEM's incremental damage energy.
- PIDL outside-precrack `psi_plus` peak is orders of magnitude below FEM's
  element-field peak.

This supports the mechanism:

```text
notch convention affects absolute E_d and early accumulation
but the persistent gap is outside the initial notch:
weak local psi/history concentration
  -> weak local fatigue degradation
  -> too little new damage/fracture energy outside the pre-crack
  -> crack-tip lag and weak Kt proxy near fracture
```

The comparison should be repeated for new reruns using the same mask and the
same reported half-width. A useful sensitivity check is to repeat the mask with
half-widths `0.01`, `0.02`, and `0.03`.
