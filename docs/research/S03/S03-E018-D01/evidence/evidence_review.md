# Independent evidence review — 2026-10-15

Reviewer: `/root/halfdepth_code_review`, read-only; completed after numerical
execution and visible QA. Bound to computation commit
`08222d861c53c9d9e1c812b73fae20e09f46197b` and final figure commit
`ad125bf8563e0339ff1e1738ee9ee0b7b24cb27f`. No new sampler execution or private
answer key; old numerical outputs were read only after implementation freeze.

Conclusion: **Evidence Ready for the bounded C1 diagnostic**, no remaining
numerical/visual blocker; can close computation-reproducibility question.

Independently verified code/input identities, clean runtime, thread environment,
14 original-image sizes/CRCs and stage paths; 168 distinct same-profile rows,
168 replay rows, 840 unique position variants and complete ALL5 support.
Recomputed old-versus-independent width discrepancy is zero; quantised replay
profile difference is zero. Actual CPU 1.342663s / wall 1.388896s meets budget.

From raw tables, reviewer independently confirmed per-beam medians:

| Beam | max location-change median, px | adjacent-stage absolute-change median, px | adjacent pairs |
|---|---:|---:|---:|
| 4 | 1.441718594 | 0.777005170 | 36 |
| 5 | 0.747782661 | 0.868318017 | 60 |
| 6 | 0.696487483 | 0.954470200 | 36 |

Coordinate count 2020200 matches the grid; coordinate/roundtrip residuals only
establish software consistency. Continuous interpolation max width difference
0.11682020444751728 px is an interpolation diagnostic, not a new forecast error.
Six examples exactly T6 B4 stages0/3, B5 stages0/5, B6 stages0/3; arrays match
safe stored profiles and replay tables. Original stored forecast CSV has 24
rows (including conservative_secant); explanation figure displays 16 rows for
two comparators across all eight pairs. Seven/eight favour secant, original
equal-beam MAEs 0.923453/0.439486 confirmed; no new error calculation.

R003 first three PNGs and four numerical CSVs byte-identical to R002; summary
identical. The moved legend exposes the previously partly covered B5 point.
All four final figures are readable with shared/explicit scales, no visible
crop or physical-unit overclaim; fixed example selection respected.

Claim boundary: retain image-defined half-depth observable and its software
reproducibility; prioritise local correspondence/independent reference, notably
Beam4. Do not promote zero numerical discrepancy/shared-H roundtrip to zero
physical error, validated registration, physical metrology, generalisation or
new forecasting validity. Same-model/shared data remains limited independence.
