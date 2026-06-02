# Active Driver Co-location Audit

Question: why can PIDL have high raw `psi` but tiny active `g(alpha) * psi_raw` and tiny history increments?

Reference: FEM Request21 `n_step=2` (`[1,0]`) projected onto the strict FEM-mesh PIDL probes.

## Ratio Summary

| cycle | effective g tip2 | corr(raw,g) tip2 | top raw/active overlap | top active/dalpha overlap | distance max raw-active |
|---:|---:|---:|---:|---:|---:|
| 1 | 0.4423 | 0.6656 | nan | 1.261 | 1.004 |
| 2 | 0.4509 | 0.6667 | nan | 1.239 | 1.018 |
| 3 | 0.454 | 0.6668 | nan | 1.239 | 1.014 |
| 20 | 1.41 | 1.009 | nan | 2.147 | 7.766 |
| 40 | 0.2981 | 1.017 | 7.232 | 12.06 | 3.338 |
| 69 | 0.01342 | 1.034 | 5.875 | 4.996 | 1.918 |

## Reading

The late-cycle failure is not simply that PIDL lacks raw tensile energy. The audit checks whether raw tensile energy is spatially aligned with low damage/degradation, active driver, and the fatigue-history increment. If the top raw-psi elements do not overlap the top active-driver/history-increment elements, the crack-tip mechanism is de-coupled even when scalar raw `psi` is large.

At c69, the tip-region raw `psi` mean is larger in PIDL than FEM
(`142.44` vs `94.89`), but the effective degradation in the same region is much
smaller (`1.85e-6` vs `1.38e-4`). This converts into active `psi` of only
`2.63e-4` in PIDL versus `1.31e-2` in FEM, and the history increment follows
the same starvation (`Delta alpha_bar` tip2 `2.63e-4` vs `2.93e-2`).

The late PIDL max raw-psi element is also not the useful crack-driving element:
at c69 it sits at the left precrack boundary (`x=-0.499`, `y=-0.0007`) with
`g_alpha≈1e-6`, so the raw energy is almost fully killed before entering the
fatigue update. The max active-driver / max history-increment element is instead
around `x=0.355`, while FEM's event-cycle max active driver is already near the
right side (`x=0.457`). This supports the interpretation that the remaining
gap is a local active-driver/history-feedback problem, not a missing raw-energy
problem.

The extrema table records the element and location of max raw `psi`, max active `psi`, and max `Delta alpha_bar` for each method/cycle.

Generated files:

- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/strict_femmesh_soft_hist0_alignment_20260529/2_figures/pidl_vs_fem_nstep2_active_driver_colocation_summary.csv`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/strict_femmesh_soft_hist0_alignment_20260529/2_figures/pidl_vs_fem_nstep2_active_driver_colocation_extrema.csv`
- `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/experiments/strict_femmesh_soft_hist0_alignment_20260529/2_figures/pidl_vs_fem_nstep2_active_driver_colocation_ratios.png`
