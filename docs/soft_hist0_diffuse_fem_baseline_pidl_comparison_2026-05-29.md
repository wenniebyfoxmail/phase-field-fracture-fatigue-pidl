# Soft-Hist0 Diffuse FEM vs Baseline PIDL

Date: 2026-05-29

## Purpose

This compares the new FEM Request 18 result,
`SENT_PIDL_12_diffuse_precrack_soft_hist0_reverseBC`, against the historical
PIDL baseline. This is the cleanest current FEM/PIDL setting alignment for the
baseline PIDL because it uses:

- retained material in the precrack region,
- soft AT1-like diffuse precrack rather than a void slit,
- `alpha_bar=0` initially,
- `f_alpha=1` initially,
- reverseBC with `fix_X` on top and bottom.

## Inputs

FEM handoff:

```text
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28
```

PIDL baseline archive:

```text
SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N300_R0.0_Umax0.12
```

Generated outputs:

```text
_analysis_fem_mechanism_20260528/soft_hist0_diffuse_fem_baseline_pidl_cyclewise_mechanism_comparison.csv
_analysis_fem_mechanism_20260528/soft_hist0_diffuse_selected_cycle_comparison.csv
_analysis_fem_mechanism_20260528/pidl_baseline_vs_fem_reference_ratio_summary_with_soft_hist0.csv
SENS_tensile/alignment_mesh_probe_u012_soft_hist0_diffuse.csv
_analysis_fem_mechanism_20260528/soft_hist0_common_probe_residual_summary.csv
_analysis_fem_mechanism_20260528/figures/soft_hist0_common_probe_residual_damage_alpha.png
_analysis_fem_mechanism_20260528/figures/soft_hist0_common_probe_residual_alpha_bar.png
_analysis_fem_mechanism_20260528/figures/soft_hist0_common_probe_residual_fatigue_f.png
_analysis_fem_mechanism_20260528/figures/soft_hist0_common_probe_residual_psi_plus_active.png
_analysis_fem_mechanism_20260528/figures/soft_hist0_diffuse_fem_baseline_pidl_cyclewise_mechanism_comparison.png
_analysis_fem_mechanism_20260528/figures/soft_hist0_diffuse_fem_baseline_pidl_cyclewise_mechanism_comparison.pdf
```

## FEM Initial-State Audit

From the FEM README:

- mesh: 45591 nodes, 45000 Q4 elements,
- material retained; no void slit or duplicated crack faces,
- soft AT1-like squared-hat phase-field initial condition,
- initial `alpha_bar=0`,
- initial `f_alpha=1`,
- precrack element-mean `d` mean/max at initialization: `0.3132 / 0.905`,
- GRIPHFiTH `tol_irrev=0.001`, AT1 penalty coefficient `421875`,
- FEM `E_d` still includes the prescribed diffuse precrack damage energy.

## Main Result

Once the initial notch/history convention is aligned, baseline PIDL is much
closer to FEM than in the void-notch or hard/pre-fatigued diffuse comparisons.

Median PIDL/FEM ratios over cycles c10-c69:

| FEM reference | `E_el` | abs `E_d` | incr. `E_d` | hist max | hist mean | `f_min` | `Kt` |
|---|---:|---:|---:|---:|---:|---:|---:|
| old void FEM | 1.065 | 2.830 | 0.251 | 0.071 | 0.554 | 52.80 | 0.006 |
| fine void FEM | 1.082 | 2.657 | 0.236 | 0.092 | 0.615 | 30.43 | 0.011 |
| hard/pre-fatigued diffuse FEM | 1.124 | 0.405 | 0.255 | 4.182 | 0.758 | 0.078 | 0.460 |
| soft-hist0 diffuse FEM | 1.029 | 0.763 | 0.245 | 0.994 | 1.053 | 0.422 | 0.799 |

The largest improvement is in the local scalar loop:

```text
history max: PIDL/FEM median moves from 4.18x to 0.99x
history mean: PIDL/FEM median moves from 0.76x to 1.05x
Kt proxy: PIDL/FEM median moves from 0.46x to 0.80x
absolute E_d: PIDL/FEM median moves from 0.41x to 0.76x
```

The remaining weak point is incremental damage/fracture dissipation:

```text
incremental E_d remains about 0.25x FEM
```

So the setting alignment removes much of the apparent scalar-mechanism gap, but
does not remove the PIDL under-dissipation / crack-lag issue.

## Common-Probe Check

The soft-hist0 FEM fields were also projected onto the PIDL element probes with
FEM coordinates shifted from `[0,1]^2` to PIDL's `[-0.5,0.5]^2`. The projection
had zero nearest-neighbour fallbacks after centering, so the coordinate mapping
is now valid.

Selected same-probe ratios:

| Cycle | Field/metric | PIDL / projected FEM |
|---:|---|---:|
| 1 | damage `tip_2l0_mean` | 1.021 |
| 1 | active `psi_plus` `tip_2l0_mean` | 1.034 |
| 1 | `alpha_bar` p99 | 0.994 |
| 40 | damage `tip_2l0_mean` | 1.087 |
| 40 | raw `psi_plus` p99 | 1.107 |
| 40 | `alpha_bar` max | 0.982 |
| 40 | `fatigue_f` right-band mean | 0.999 |
| 69 | damage p99 | 0.993 |
| 69 | active `psi_plus` p99 | 1.378 |
| 69 | `alpha_bar` max | 0.443 |
| 69 | `alpha_bar` p99 | 0.210 |

This says the aligned FEM/PIDL fields are genuinely close on many common-probe
metrics through c40. Near c69, scalar means can still look close while the
history distribution differs: FEM has a much larger late local `alpha_bar`
peak/p99, and PIDL still lags in crack advance.

The residual-field figures visualize the same statement. Each row is one cycle;
columns are FEM projected to PIDL probes, PIDL at those probes, and
`PIDL - FEM`. The FEM projection is area-averaged where possible, with
nearest-value gap filling used only for visualization so the plot does not show
white holes where a PIDL triangle received no FEM centroid.

Main visual readings:

- damage residual: c1 is nearly zero in the precrack; by c69 PIDL and FEM both
  form a band, but the band-tip position/shape differs near the right side;
- fatigue-history residual: c40 is close around the crack path, while c69 shows
  FEM developing a stronger late local history peak than PIDL;
- active tensile-driver residual: early/c40 drivers are broadly aligned near
  the tip, but c69 shows a shifted high-driver zone as the FEM crack reaches
  the boundary and PIDL lags.

## Selected Cycle Values

| Cycle | Metric | hard/pre-fatigued diffuse FEM | soft-hist0 diffuse FEM | PIDL baseline |
|---:|---|---:|---:|---:|
| 1 | `E_d` | 0.012719 | 0.005699 | 0.005471 |
| 1 | history max | 1.013742 | 0.237152 | 0.736716 |
| 1 | `f_min` | 0.436479 | 1.000000 | 0.653822 |
| 1 | `Kt` | 4.205532 | 10.797873 | 7.584732 |
| 40 | `Delta E_d` from c1 | 0.002131 | 0.002210 | 0.000547 |
| 40 | history max | 1.564733 | 7.331894 | 7.201604 |
| 40 | history mean | 0.301251 | 0.217952 | 0.229258 |
| 40 | `f_min` | 0.242092 | 0.040204 | 0.016859 |
| 40 | `Kt` | 22.047506 | 13.067986 | 9.555184 |
| 40 | `x_tip_d095` / PIDL `x_tip` | 0.199000 | 0.193000 | 0.159512 |
| 69 | `Delta E_d` from c1 | 0.005306 | 0.005461 | 0.001659 |
| 69 | history max | 2.082295 | 19.532206 | 8.659918 |
| 69 | history mean | 0.380455 | 0.345204 | 0.342233 |
| 69 | `f_min` | 0.155209 | 0.014591 | 0.011918 |
| 69 | `Kt` | 12.097988 | 10.562066 | 15.547702 |
| 69 | `x_tip_d095` / PIDL `x_tip` | 0.499000 | 0.499000 | 0.372961 |

## Interpretation

This result strongly supports the concern that setting differences were
changing the apparent mechanism.

The old hard/pre-fatigued diffuse FEM started with a large prescribed damage
energy and pre-degraded crack band. The new soft-hist0 FEM starts much closer
to PIDL:

```text
cycle-1 FEM E_d: 0.0127 -> 0.0057
cycle-1 PIDL E_d: 0.0055
```

That is not a small correction; it changes the energy baseline before crack
growth begins.

The remaining gap is now more specific:

```text
FEM and PIDL can have similar elastic energy, local history mean, and Kt scale,
but PIDL still dissipates too little incremental fracture energy and reaches
the right boundary later.
```

This points less toward "baseline PIDL has the wrong initial physics" and more
toward:

- NN representation/optimization not widening or advancing the damage zone in
  the FEM-like way,
- PIDL one-peak-per-cycle fatigue update versus FEM substep history update,
- PIDL weaker irreversibility penalty (`tol_ir=5e-3` versus FEM `tol_irrev=1e-3`),
- triangle/NN quadrature versus FEM Q4 Gauss/history averaging.

## Next Step

Use the soft-hist0 diffuse FEM as the main aligned reference for baseline PIDL.
Before another architecture conclusion, run or evaluate these controlled checks:

1. PIDL with `tol_ir=1e-3` against soft-hist0 FEM.
2. PIDL with explicit cycle substeps on a short c1-c40 diagnostic.
3. Field residuals for soft-hist0 FEM vs PIDL at c1, c40, and c69.
4. Continue the void-notch track separately: void FEM should only be compared
   with PIDL void-mask diagnostics, not with baseline diffuse PIDL.
