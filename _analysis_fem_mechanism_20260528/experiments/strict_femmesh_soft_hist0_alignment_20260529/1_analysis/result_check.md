# Result Check: strict_femmesh_soft_hist0_alignment_20260529

## Artifact Completeness

| gate | status | evidence path | note |
|---|---|---|---|
| sync/provenance | complete | `../0_sync/SYNC_SOURCES.md` | Taobo, local sync, FEM references, model settings, log, scalar arrays recorded. |
| early state timing | partial | `../2_figures/strict_femmesh_soft_hist0_alignment_state_timing_j0_j1.png` | Confirms the corrected `FEM c1 -> PIDL j0` mapping; not a full pre/post-history export package for this old run. |
| FEM-reference residual fields | complete | `../2_figures/strict_femmesh_soft_hist0_alignment_*_residual_c1_c20_c40_c69.png` | Damage, `alpha_bar`, `f_fatigue`, and active `psi+` residual figures are copied. |
| cyclewise mechanism trajectory | complete | `../2_figures/strict_femmesh_soft_hist0_alignment_reference_tiers_c1_c20_c40_c69.png` | Standard and n_step10 FEM references compared on common probes. |
| energy/incremental energy | complete | `../2_figures/strict_femmesh_soft_hist0_alignment_energy_tiers.csv` | Absolute and incremental `E_d` are separated. |
| gradient/loss balance | missing | n/a | This benchmark predates the later mandatory head-wise gradient export. |
| method-specific diagnostics | not-applicable | n/a | This is the strict benchmark, not a new intervention method. |

Evidence maturity: **retrospective-partial**.

## Verdict

**Negative mechanism-alignment result, retrospective-partial.** The strict
FEM-mesh / soft-hist0 benchmark removes the main bookkeeping mismatches.  Using
Request 21 `n_step10` as the primary FEM reference, it still does not close the
PIDL/FEM forward-field mechanism gap. Damage near the tip is roughly aligned,
and raw `psi+` is not too small; the failure is the degraded active driver
`g(alpha) psi+`, which becomes far too small near the process zone and leaves
`alpha_bar` plus incremental `E_d` behind FEM.

## Run Health And Provenance

- Workspace: `/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529`
- Archive: `/mnt/data2/drtao/projects/pidl-align-soft-hist0-20260529/SENS_tensile/hl_8_Neurons_400_activation_TrainableReLU_coeff_1.0_Seed_1_PFFmodel_AT1_gradient_numerical_fatigue_on_carrara_asy_aT0.5_N100_R0.0_Umax0.12_femmesh_softHist0`
- Local synced archive subset: `../0_sync/`
- Mesh: `meshed_geom_fem_soft_hist0.msh`
- Primary FEM reference: Request 21 soft-hist0 retained-material reverseBC
  `n_step10` FEM, `Umax=0.12`
- Secondary FEM sensitivity reference: standard soft-hist0 retained-material
  reverseBC FEM, `Umax=0.12`
- Invalid source warning: the local compact MAT mirror under
  `_analysis_fem_mechanism_20260528/source_handoff_soft_hist0/` is zero bytes
  and is not used.
- FEM cycle mapping: `FEM c -> PIDL saved j = c - 1`
- Seed: 1
- Cycles: `N=100`
- Confirm cycles: 3
- Event status: first right-boundary hit at PIDL j82, confirmed stop at j85
- Enabled intervention: none beyond strict FEM-mesh / soft-hist0 alignment

## Setting Alignment Audit

Aligned in this benchmark:

- reverseBC boundary condition
- retained-material diffuse precrack
- soft-hist0 fatigue initialisation: `alpha_bar=0`, `f=1`
- FEM-derived PIDL mesh/probe comparison
- Request 21 `n_step10` FEM as the primary reference
- standard FEM retained only as a secondary sensitivity check
- fixed-cycle and matched-event checks
- absolute and incremental `E_d` separated

This means the remaining gap is no longer explained by the old void-notch,
hard-precrack, mixed c1 timing, or old PIDL mesh comparison.

## Early State And Timing Check

The corrected timing map is `FEM c1 -> PIDL saved j0`. Under that map, the
first-cycle near-tip fields are close:

| reference | comparison | damage tip2 | alpha_bar tip2 | active psi tip2 |
|---|---|---:|---:|---:|
| standard FEM | c1 -> j0 | 1.008 | 0.985 | 1.013 |
| n_step10 FEM | c1 -> j0 | 1.018 | 0.982 | 1.017 |

This removes the previous c1 bookkeeping trap from the main interpretation.

## Request 21 Primary Field-Level FEM/PIDL Comparison

Fixed-cycle ratios against Request 21 `n_step10` FEM:

| cycle | damage tip2 | alpha_bar tip2 | alpha_bar p99 | raw psi tip2 | active psi tip2 |
|---:|---:|---:|---:|---:|---:|
| c1 -> j0 | 1.018 | 0.982 | 0.581 | 2.411 | 1.017 |
| c20 -> j19 | 0.996 | 0.901 | 0.949 | 0.967 | 0.909 |
| c40 -> j39 | 0.996 | 0.660 | 0.466 | 1.202 | 0.125 |
| c69 -> j68 | 1.008 | 0.373 | 0.202 | 1.583 | 0.0233 |

This is the cleanest current analysis because Request 21 controls the FEM
load-step/history cadence. It shows that the early fields are aligned enough to
compare, but the active driver collapses as the cycles progress.

## Secondary Standard-FEM Sensitivity Check

Fixed-cycle c69 ratios:

| reference | damage tip2 | alpha_bar tip2 | alpha_bar p99 | raw psi tip2 | active psi tip2 |
|---|---:|---:|---:|---:|---:|
| standard FEM | 1.012 | 0.466 | 0.191 | 1.330 | 0.0287 |
| n_step10 FEM | 1.008 | 0.373 | 0.202 | 1.583 | 0.0233 |

The standard FEM reference gives the same qualitative conclusion as Request 21:
the damage field is roughly in the correct near-tip region, and the raw tensile
driver is comparable to or larger than FEM. The degraded active driver is the
failure mode.

## Energy And Incremental Energy

Against Request 21 `n_step10`, incremental damage energy grows slowly but is
still only one quarter of FEM by c69:

| cycle | abs E_d PIDL/FEM | Delta E_d PIDL/FEM |
|---:|---:|---:|
| c1 -> j0 | 0.954 | n/a |
| c20 -> j19 | 0.854 | 0.110 |
| c40 -> j39 | 0.743 | 0.201 |
| c69 -> j68 | 0.609 | 0.250 |

At c69, the standard-FEM sensitivity check gives the same one-quarter
incremental-energy result:

| reference | Delta E_d PIDL/FEM |
|---|---:|
| standard FEM | 0.2505 |
| n_step10 FEM | 0.2500 |

Absolute `E_d` is less useful because the diffuse initial precrack contributes
to the starting damage energy. The incremental comparison is the proper gate.

## Gradient/Loss-Balance Check

Missing for this exact historical benchmark. The result should therefore remain
`retrospective-partial`, not a full protocol pass. Later PIDL diagnostics should
use head-wise gradient balance before final interpretation.

## Event And Trajectory Check

Matched-event comparison against FEM c69:

| reference | PIDL state | damage tip2 | alpha_bar tip2 | raw psi tip2 | active psi tip2 |
|---|---|---:|---:|---:|---:|
| standard FEM | fixed j68 | 1.012 | 0.466 | 1.330 | 0.0287 |
| standard FEM | detected j84 | 1.027 | 0.469 | 1.420 | 0.0058 |
| standard FEM | confirmed j85 | 1.027 | 0.469 | 1.420 | 0.0066 |
| n_step10 FEM | fixed j68 | 1.008 | 0.373 | 1.583 | 0.0233 |
| n_step10 FEM | detected j84 | 1.013 | 0.368 | 1.648 | 0.0046 |
| n_step10 FEM | confirmed j85 | 1.013 | 0.368 | 1.648 | 0.0052 |

Waiting until PIDL's own event state does not rescue the active-driver
mechanism; it makes the active `psi+` gap sharper.

## Method-Specific Diagnostics

Not applicable. This folder packages the strict benchmark and protocol-aligned
comparison, not a new method variant.

## Interpretation In Plain English

The strict alignment fixed the bookkeeping problem but exposed a real forward
mechanism mismatch. PIDL can place damage in roughly the same near-tip region as
FEM, and the raw tensile field is not weak. But once damage degradation is
applied, the active work available to drive fatigue history is almost gone.
That is why `alpha_bar` and incremental damage energy lag behind FEM even when
the crack position looks superficially aligned.

The bottleneck is the coupled loop:

```text
damage/degradation -> active psi+ -> alpha_bar history
-> fatigue degradation -> next damage/energy increment
```

## Links To Evidence

- `../2_figures/strict_femmesh_soft_hist0_alignment_request21_primary_summary.csv`
- `../2_figures/strict_femmesh_soft_hist0_alignment_request21_primary_ratios.png`
- `../2_figures/strict_femmesh_soft_hist0_alignment_reference_tier_summary.csv`
- `../2_figures/strict_femmesh_soft_hist0_alignment_fixed_vs_event_summary.csv`
- `../2_figures/strict_femmesh_soft_hist0_alignment_energy_tiers.csv`
- `../2_figures/strict_femmesh_soft_hist0_alignment_common_probe_c1_c20_c40_c69.csv`
- `../2_figures/strict_femmesh_soft_hist0_alignment_reference_tiers_c1_c20_c40_c69.png`
- `../2_figures/strict_femmesh_soft_hist0_alignment_fixed_vs_event_c69.png`
- `../2_figures/strict_femmesh_soft_hist0_alignment_incremental_energy_c1_c69.png`
- `../2_figures/strict_femmesh_soft_hist0_alignment_state_timing_j0_j1.png`
