# PIDL Variant Rescore Under Soft-Hist0 j0 Protocol

Date: 2026-05-29

## Question

The user asked why the FEM/PIDL gap grows with cycle count, and whether prior
PIDL representation/sampling variants should be compared again under the new
FEM setting, new history timing, and new criteria.

## Mechanism Explanation

The gap grows because this is a feedback loop, not a one-shot field fit:

```text
alpha field -> active psi_plus -> alpha_bar history -> fatigue degradation f
-> elastic relaxation and stress redistribution -> next active psi_plus
```

A small local mismatch early in `alpha_bar` or active `psi_plus` is remembered.
Then the next cycle sees a slightly different degraded stiffness, which moves
the stress concentration, which changes the next history increment.  The effect
is multiplicative over many cycles.

Under the corrected protocol, c1 is now well aligned:

```text
FEM c1 -> PIDL saved j0
alpha_bar tip_2l0 ratio ≈ 0.985
active psi_plus tip_2l0 ratio ≈ 1.013
```

So the late gap is not mainly a first-cycle indexing mistake.  By c40 the
near-tip active driver is already much lower in PIDL, while damage position can
still look close.  That means a position-only comparison hides the problem.

## Rescore Protocol

Current protocol:

```text
FEM reference: soft-hist0 retained-material reverseBC FEM
PIDL cycle mapping: FEM c -> PIDL saved j = c - 1
cycles compared: c1, c20, c40, c69
primary fields: damage_alpha, alpha_bar, psi_plus_active
primary metrics: tip_2l0_mean, p99, max
```

Generated artifacts:

```text
_analysis_fem_mechanism_20260528/variant_rescore_j0map/
```

## First Variant Pass

This first pass compares local archives that could be reconstructed post-hoc.
Strictness differs:

- `femmesh_softHist0` is the strictest current PIDL benchmark.
- `baseline_geom2`, `psiHack`, `spAlphaT_b08`, and `williams_v4` are old-PIDL
  settings re-scored against the new FEM reference.  They are diagnostically
  useful, but not final fair benchmarks.
- `fourier_v1` could not be reconstructed by the current posthoc loader because
  its historical checkpoint stores a 34-input network directly rather than the
  current `FourierFeatureNet` wrapper format.  This needs a small compatibility
  loader before fair rescoring.

Selected ratios:

| Method | Cycle | damage tip_2l0 | alpha_bar tip_2l0 | alpha_bar p99 | active psi tip_2l0 |
|---|---:|---:|---:|---:|---:|
| baseline_geom2 | 1 | 1.007 | 1.008 | 0.502 | 1.035 |
| baseline_geom2 | 40 | 1.084 | 0.870 | 0.466 | 0.342 |
| baseline_geom2 | 69 | 1.142 | 0.517 | 0.209 | 0.050 |
| femmesh_softHist0 | 1 | 1.008 | 0.985 | 0.421 | 1.013 |
| femmesh_softHist0 | 40 | 1.002 | 0.792 | 0.430 | 0.245 |
| femmesh_softHist0 | 69 | 1.012 | 0.466 | 0.191 | 0.029 |
| spAlphaT_b08 | 1 | 1.014 | 1.012 | 0.502 | 1.039 |
| spAlphaT_b08 | 40 | 1.075 | 0.507 | 0.441 | 0.231 |
| spAlphaT_b08 | 69 | 1.149 | 0.305 | 0.200 | 0.038 |
| williams_v4 | 1 | 0.994 | 1.003 | 0.510 | 1.030 |
| williams_v4 | 40 | 0.639 | 0.776 | 0.441 | 28.660 |
| williams_v4 | 69 | 0.367 | 0.464 | 0.197 | 56.998 |
| psiHack | 1 | 1.007 | 1.008 | 0.502 | 1.035 |
| psiHack | 40 | 1.084 | 0.870 | 0.466 | 0.342 |
| psiHack | 69 | 1.437 | 5.650 | 0.479 | 0.027 |

## Taobo Tiered Addendum

Taobo now has a tiered inventory in:

```text
docs/taobo_tiered_comparison_plan_2026-05-29.md
_analysis_fem_mechanism_20260528/taobo_tier_manifest_20260529.csv
```

The first strict/control Taobo rescore adds the `tol_ir=0.001` soft-hist0
forward archive.  The `reverseBC_softHist0_forward_tolir0.001` archive and the
controlled `tolir0.001_baseline` archive are checkpoint-identical at the sampled
states, so they count as one method.

Selected ratios:

| Method | Cycle | damage tip_2l0 | alpha_bar tip_2l0 | alpha_bar p99 | active psi tip_2l0 |
|---|---:|---:|---:|---:|---:|
| softHist0/tol_ir=0.001 | 1 | 1.028 | 1.011 | 0.511 | 1.038 |
| softHist0/tol_ir=0.001 | 20 | 1.118 | 1.057 | 1.026 | 1.692 |
| softHist0/tol_ir=0.001 | 40 | 1.272 | 0.883 | 0.476 | 0.188 |
| softHist0/tol_ir=0.001 | 69 | 1.464 | 0.516 | 0.216 | 0.033 |

Reading: loosening `tol_ir` increases local damage and early local history, but
does not recover the late near-tip active driver.  By c69, near-tip
`alpha_bar` remains about 0.52x FEM and active `psi_plus` remains about 0.03x
FEM.  This supports the current view that the late gap is a coupled
history/driver/localisation issue, not just an irreversibility tolerance issue.

## Interpretation

The old representation/sampling ideas do not simply become successful under
the new FEM setting and timing protocol.

Main readings:

1. Damage position/mean can remain close while the driver/history mechanism
   diverges.
2. FEM-mesh improves damage position, but does not fix late near-tip
   `alpha_bar` or active `psi_plus`.
3. Williams v4 creates very large active-driver ratios while damaging the
   damage-position comparison, so it is not a clean mechanism fix.
4. `spAlphaT_b08` and `psiHack` alter fatigue/history scalars but do not solve
   the late active-driver gap in a stable, FEM-like way.
5. The gap begins to be obvious by c40, before final boundary reach.  That makes
   c40 a better diagnostic gate than only c69/c75.

## Next Comparison Work

1. Add a compatibility loader for historical Fourier checkpoints.
2. Pull/rescore Taobo tip-local and patch-strength archives if not present
   locally, using the same c->j-1 mapping.
3. Wait for FEM Request 21 (`n_step=2/3/10`) and compare the FEM substep curve
   before launching a matched PIDL substep run.
4. Use c20/c40/c69 gates, not only N_f:

```text
damage tip_2l0 and width
alpha_bar p99 / tip_2l0
active psi_plus tip_2l0
Delta E_d from c1
```

## Bottom Line

The growing gap looks like a cumulative history/driver feedback issue.  The
old NN representation/sampling changes should be re-scored, but the first
posthoc pass says they did not remove the aligned FEM/PIDL mechanism gap.
