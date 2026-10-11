# FEM+Mask vs PIDL+Mask Region Audit

Date: 2026-06-10

This focused audit compares the PIDL precrack-fatigue-mask run against the
Windows FEM Request 22/23 explicit-step FEM+mask export using only local CSV
and PIDL NPZ diagnostics. It does not require reading the full FEM state MAT.

## Data Used

- FEM mask audit:
  `/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_latest_align_soft_hist0_precrackFatigueDriverMask_explicit_steps_20260609/precrack_fatigue_driver_mask_region_audit.csv`
- PIDL diagnostics:
  `precrack_fatigue_mask_complete_export_630111c_20260609/raw_archive/.../element_diagnostics_precrack_fatigue_mask/`

States audited:

```text
c1_peak  -> PIDL/FEM global step 3
c20_peak -> PIDL/FEM global step 98
c40_peak -> PIDL/FEM global step 198
c69_peak -> PIDL/FEM global step 343
```

Regions:

```text
left_precrack_line_audit: x <= 0.5 and |y - 0.5| <= 0.014 in FEM frame
mask_support:             x <= 0.5 and |y - 0.5| <= 0.02
outside_left_precrack_line_audit
```

## Main Result

For the masked precrack region, the requested fatigue-history mask now matches
between FEM and PIDL:

```text
alpha_bar = 0
masked_Dalpha = 0
f_fatigue = 1
```

This holds at both `c1_peak` and `c69_peak` for the left precrack audit band
and the full mask support.

The remaining difference in this reduced audit is the raw/active driver
bookkeeping inside the mask. FEM+mask intentionally reports nonzero raw
mechanics/raw `psi_plus` on the masked corridor, while the PIDL diagnostic NPZ
reports zero `psi_raw_elem` and zero `psi_active_elem` there. Therefore the
fatigue-history mask comparison is clean, but the raw-driver comparison inside
the mask should not be overinterpreted until the full FEM MAT is hydrated and a
field-definition audit is run.

## Outputs

- `tables/fem_mask_vs_pidl_mask_region_audit.csv`
- `tables/fem_mask_vs_pidl_mask_key_summary.csv`
- `tables/fem_mask_vs_pidl_mask_region_audit_manifest.json`
- `figures/fem_mask_vs_pidl_mask_region_audit.png`
- `figures/fem_mask_vs_pidl_mask_region_audit.pdf`

## Limitation

The full FEM field MAT is currently visible in OneDrive as an 8.7 GB file but
uses 0 bytes locally (`du=0B`), so it is a cloud-only placeholder on this Mac.
The full residual-map regeneration was stopped before field reading completed.
Hydrate or copy the MAT locally before running the full residual figures.
