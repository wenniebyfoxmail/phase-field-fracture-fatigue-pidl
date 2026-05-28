# Diffuse-Precrack FEM vs Baseline PIDL Comparison

Date: 2026-05-28

## Purpose

This compares the newest FEM result, `SENT_PIDL_12_diffuse_precrack_reverseBC`,
against the baseline PIDL archive. This is the closest FEM notch convention to
the baseline PIDL convention because both retain material in the initial crack
region and prescribe/encode an initially damaged pre-crack.

## Inputs

Diffuse-precrack FEM handoff:

```text
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_2026-05-28
```

PIDL baseline archive:

```text
SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12
```

Generated outputs:

```text
_analysis_fem_mechanism_20260528/diffuse_precrack_fem_centered_metrics.csv
_analysis_fem_mechanism_20260528/diffuse_fem_baseline_pidl_cyclewise_mechanism_comparison.csv
_analysis_fem_mechanism_20260528/pidl_baseline_vs_fem_reference_ratio_summary.csv
_analysis_fem_mechanism_20260528/figures/diffuse_fem_baseline_pidl_cyclewise_mechanism_comparison.png
_analysis_fem_mechanism_20260528/figures/diffuse_fem_baseline_pidl_cyclewise_mechanism_comparison.pdf
```

## Coordinate / Definition Note

The diffuse FEM export uses plate coordinates with the initial band defined as:

```text
x <= 0.5 and |y - 0.5| <= 0.02
```

For comparison with PIDL, x/y location columns were centred by subtracting
`0.5`. Scalar energies and field reductions were not otherwise changed.

Absolute `E_d` is not directly comparable because diffuse FEM integrates the
prescribed `d=1` pre-crack band from cycle 1. Incremental `E_d` from c1 is the
fairer quantity.

## Main Result

Baseline PIDL is much closer to diffuse-precrack FEM than to void-notch FEM for
some local mechanism metrics, especially history max and `Kt`. It is not closer
for everything.

Median PIDL/FEM ratios over c10-c69:

| FEM reference | `E_el` | abs `E_d` | incr. `E_d` | hist max | hist mean | `f_min` | `Kt` |
|---|---:|---:|---:|---:|---:|---:|---:|
| old void FEM | 1.065 | 2.830 | 0.251 | 0.071 | 0.554 | 52.80 | 0.006 |
| fine void FEM | 1.082 | 2.657 | 0.236 | 0.092 | 0.615 | 30.43 | 0.011 |
| diffuse-precrack FEM | 1.124 | 0.405 | 0.255 | 4.182 | 0.758 | 0.078 | 0.460 |

Interpretation:

- `E_el` remains close for all references until the FEM fracture cliff.
- Incremental `E_d` is still low in PIDL: about `0.25x` FEM, even for the
  diffuse-precrack reference.
- History max flips direction. Against void FEM, PIDL was far too low. Against
  diffuse FEM, PIDL is about `4.2x` higher.
- History mean is much closer against diffuse FEM (`0.76x`).
- `f_min` also flips direction. Against void FEM, PIDL degradation was too weak
  (`f_min` too large). Against diffuse FEM, PIDL degradation is too strong
  (`f_min` too small, about `0.078x` FEM).
- `Kt` is much closer against diffuse FEM (`0.46x`) than against void FEM
  (`0.006x` to `0.011x`), though still lower overall.

## Selected Cycle Values

| Cycle | Metric | Diffuse FEM | PIDL |
|---:|---|---:|---:|
| 1 | `E_d` | 0.012719 | 0.005471 |
| 40 | `Delta E_d` from c1 | 0.002131 | 0.000547 |
| 69 | `Delta E_d` from c1 | 0.005306 | 0.001659 |
| 40 | history max | 1.565 | 7.202 |
| 69 | history max | 2.082 | 8.660 |
| 40 | `f_min` | 0.242 | 0.0169 |
| 69 | `f_min` | 0.155 | 0.0119 |
| 40 | `Kt` | 22.05 | 9.56 |
| 69 | `Kt` | 12.10 | 15.55 |
| 40 | centred `x_tip_d095` / PIDL `x_tip` | 0.199 | 0.160 |
| 69 | centred `x_tip_d095` / PIDL `x_tip` | 0.499 | 0.373 |

## What This Means

Your intuition is right in an important sense: the newest diffuse FEM result is
closer to baseline PIDL in the local scalar loop than the void-notch FEM
references are. The huge void-FEM gap in `Kt` and local history is partly a
notch-representation effect.

But this does not mean PIDL is now mechanism-matched. The remaining gaps are:

```text
PIDL incremental E_d is still only about 0.25x FEM.
PIDL local history peak is now too high relative to diffuse FEM.
PIDL f_min is now too low relative to diffuse FEM.
PIDL tip position still lags near c69.
```

So the best interpretation is:

```text
void-notch FEM and diffuse-precrack FEM are two different local mechanisms.
Baseline PIDL is much closer to diffuse-precrack FEM in local scalar amplitude,
but still dissipates/advances damage differently.
```

The next fair comparison should be with the currently running PIDL
void-notch-mask runs. Those will tell us whether aligning PIDL toward the FEM
void-notch convention moves it toward the void FEM mechanism, or whether the
baseline diffuse PIDL is naturally closer to the diffuse-precrack FEM target.
