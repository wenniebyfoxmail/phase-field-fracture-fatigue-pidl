# Sync Sources: FEM Reference Qualification 2026-06-02

## Purpose

This folder qualifies which FEM reference data are needed before a PIDL
experiment can pass the result-check protocol.  It is a reference-data audit,
not a PIDL method result.

## Main FEM References

| reference | path | status | role |
|---|---|---|---|
| soft-hist0 main FEM | `/Users/wenxiaofang/Library/CloudStorage/OneDrive-UniversityofCambridge/PIDL result/_pidl_handoff_reverseBC_u12_diffuse_precrack_soft_hist0_2026-05-28` | present | main strict aligned reverseBC retained-material soft diffuse-precrack reference |
| Request 21 n-step10 FEM | `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/request21_fem_nstep/source_handoff/_pidl_handoff_reverseBC_u12_soft_hist0_nstep10_2026-05-29` | present | FEM load-step/history cadence sensitivity reference |
| mirrored compact MAT | `/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/_analysis_fem_mechanism_20260528/source_handoff_soft_hist0/reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat` | warning: zero-byte file on 2026-06-02 | do not use unless re-synced |

## Files Verified Present

Main soft-hist0 FEM folder contains:

```text
mesh_geometry.mat
reverseBC_u12_diffuse_precrack_soft_hist0_cyclewise_mechanism_metrics.csv
reverseBC_u12_diffuse_precrack_soft_hist0_element_fields_c1_c69.mat
README_reverseBC_u12_diffuse_precrack_soft_hist0.md
INPUT/main/export/solver audit files
```

Request 21 n-step10 FEM folder contains:

```text
mesh_geometry.mat
reverseBC_u12_soft_hist0_nstep10_cyclewise_mechanism_metrics.csv
reverseBC_u12_soft_hist0_nstep10_element_fields_c1_c69.mat
README_reverseBC_u12_soft_hist0_nstep10.md
INPUT/export audit files
```

## Sync Rule

Large `.mat` field files do not need to be duplicated into this folder, but
their source paths and validity status must be recorded here.  Any zero-byte,
missing, or stale mirror must be treated as invalid until re-synced.
