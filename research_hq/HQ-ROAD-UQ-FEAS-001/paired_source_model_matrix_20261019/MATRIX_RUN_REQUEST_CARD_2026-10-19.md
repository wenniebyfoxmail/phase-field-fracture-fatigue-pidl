# Review card: proposed HQ-ROAD-UQ-MATRIX-001-R001

**State:** implementation and exact inputs prepared; no execution authority recorded.

| Field | Exact proposal |
|---|---|
| Decision | Distinguish repair-package gain from source easiness and label-location incompatibility using the complete old/new checkpoint × CFD/GAPS matrix. |
| Models | Frozen D1 scratch U-Net checkpoint `43423f84…205d`; frozen D2 ResNet18UNet checkpoint `92cd9374…27e2`. No fitting or weight change. |
| Sources | Existing CFD 118 labels and GAPS384 382 nonempty + 2 empty labels. Both are development sources. |
| Reused evidence | D1 old/CFD CSV and D2 repair/GAPS CSV remain authoritative for their frozen verdicts and are hash locked. |
| Added computation | One common-backend inference batch for the two missing cells plus strict/tolerance diagnostics required for comparability; A-validation-only `U_Z` fit separately for each frozen model. |
| Outputs | Four cell CSVs, per-source degeneracy/strict and 2/4-pixel overlap, LC/H/Z risk curves at 25%, paired bootstrap error deltas, frozen-rule failure panels, diagonal consistency checks, summary and receipt. |
| Proposed producer | `gpu-server`, `D-26-09`, GPU 0. |
| Budget | Exactly one no-training evaluation run, `HQ-ROAD-UQ-MATRIX-001-R001`, maximum two GPU hours, no retry. |
| Stops | Any checkpoint/data/environment/hash drift, diagonal strict-metric mismatch above `1e-5`, nonfinite output, or two-hour deadline. |
| Excluded | Training, new seed/model/source, threshold tuning, pooled-source headline, Road420 access, tolerant-metric rescue of D1/D2, publication or external message. |

The matrix result will choose among: representation gain across both sources; GAPS-only source effect; tolerance-only label/location effect; simple-confidence retention; or route redirect because absolute risk remains unusable.
