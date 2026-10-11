# Retrospective Comparison Intent

Date: 2026-06-10

Purpose: compare the PIDL precrack-fatigue-mask complete export against the
Windows FEM Request 22/23 export:
`latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_20260609`.

This is not a new PIDL run. It reuses the PIDL archive from:

```text
precrack_fatigue_mask_complete_export_630111c_20260609
```

FEM reference:

```text
Alignment check 2/FEM cyclic 012/cases/precrack_fatigue_mask_explicit_steps_20260609/raw_data/state_field_exports/latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_20260609
```

Primary question: after applying the PIDL-equivalent FEM fatigue-history mask
(`mask_fatigue=true`, `mask_energy=false`) and explicit five-substep state
mapping, does the c1/c69 masked-precrack comparison close the confusing
left-precrack history discrepancy?

State mapping:

```text
cN_peak     -> PIDL/FEM global step 5*(N-1)+3
cN_unloaded -> PIDL/FEM global step 5*(N-1)+4
```

This case intentionally preserves the original standard-FEM comparison outputs
in the source PIDL case and writes separate analysis artifacts here.
