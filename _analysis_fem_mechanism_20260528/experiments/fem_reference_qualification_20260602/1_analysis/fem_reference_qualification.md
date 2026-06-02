# FEM Reference Qualification

## Artifact Completeness

| gate | status | evidence path | note |
|---|---|---|---|
| sync/provenance | partial | `0_sync/SYNC_SOURCES.md` | main source paths recorded; large MATs are not copied |
| qualification spreadsheet | complete | `2_figures/fem_reference_qualification_matrix.csv` | lists required FEM data by result-check gate |
| cycle/state plan | complete | `2_figures/fem_reference_cycle_plan.csv` | lists required cycles and timing states |
| evidence-map figure | complete | `2_figures/fem_reference_data_map.png` | visual summary of FEM data needed by protocol |
| source integrity | partial | `0_sync/SYNC_SOURCES.md` | local compact MAT mirror is zero-byte and should not be used |

Evidence maturity: `reference-checklist-complete`, source sync `partial`.

## What FEM Result Is Needed?

For a PIDL experiment to be judged under the result-check protocol, the FEM
reference must support these gates:

1. setting and initial-state alignment,
2. common-probe field comparison,
3. cyclewise energy and incremental energy comparison,
4. event and trajectory comparison,
5. figure generation for field residuals and trajectories.

FEM does not need to provide neural-network gradients.  The `E_el/E_d/E_hist`
gradient-balance gate is PIDL-side only.

## Minimum FEM Reference Package

The minimum package is:

- mesh geometry: nodes, connectivity, centroids, element areas;
- initial audit: precrack profile, initial `alpha_bar`, initial `f_fatigue`;
- cyclewise fields: `d/alpha`, `alpha_bar`, `f_fatigue`, `psi_plus`;
- cyclewise energies: `E_el`, `E_d`, total energy where available;
- event audit: native FEM fracture cycle and boundary/event criterion;
- timing metadata: whether each field is peak-load, unloaded, pre-history, or
  post-history.

For the strict soft-hist0 reverseBC benchmark, the main reference is:

```text
/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28
```

The n-step10 cadence reference is:

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/request21_fem_nstep/source_handoff/_pidl_handoff_reverseBC_u12_soft_hist0_nstep10_2026-05-29
```

## Current Qualification Warning

The local compact MAT mirror:

```text
_analysis_fem_mechanism_20260528/source_handoff_soft_hist0/reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat
```

is zero bytes on 2026-06-02.  It should be treated as invalid until re-synced.
Use the OneDrive source MAT or the Request 21 source folder instead.

## How To Use This Folder

Use the matrix CSV as a checklist before generating a PIDL experiment report.
If a PIDL result folder lacks the FEM data required by a gate, mark that gate as
`partial` or `missing` and label the result as provisional or
retrospective-partial.

The figure is meant as a quick visual reminder: FEM reference data feed the
field, energy, event, and state-timing gates; PIDL alone supplies gradients.
