# FF frozen-prediction sensitivity localisation

Question: where do the two existing FF alternating-error reversals arise, and how do they co-occur with position and growth?
Evidence: R001 frozen predictions and published labels; R002 fixed seven radii and both alternating phases; A002 v1. Controlled experiment, one FF specimen, all33 development-exposed evaluation windows. No refit or model forward.

Read: ff_locality.png A (observed and frozen B1/M0/M1), B (both signed shifts), C (public CSV coordinates and hole), D (past growth). Exact values: windows_ranked.csv, all_radius_windows.csv and groups.csv.

## Contributions at the existing maximum radius

| Phase | Original D mm | Perturbed D mm | Gross lowering sum mm | Offsetting sum mm | Top5 lowering share |
|---|---:|---:|---:|---:|---:|
| alternating_positive | 0.003485745 | -0.003221881 | 0.393511758 | 0.172160117 | 72.26% |
| alternating_negative | 0.003485745 | -0.003135289 | 0.240029308 | 0.021535213 | 36.85% |

Top5 rule: mean gross lowering over BOTH phases, fixed k=5, origin-cycle tie break. Shares use gross lowering rather than net shift. All33 remain scored.

| Origin -> target | Origin x mm | Past dx mm | Target dx mm | Mean lowering mm | Origin hole projection |
|---|---:|---:|---:|---:|---|
| 111000 -> 112000 | 27.1700 | 0.6210 | 0.8970 | 0.105212129 | over_projection |
| 104000 -> 105000 | 22.9090 | 0.7410 | 0.6940 | 0.026735043 | over_projection |
| 105000 -> 106000 | 23.6030 | 0.6940 | 0.7290 | 0.019745033 | over_projection |
| 102000 -> 103000 | 21.4960 | 0.6890 | 0.6720 | 0.017494486 | before |
| 97001 -> 98001 | 18.6640 | 0.4630 | 0.4960 | 0.017208831 | before |

## Geometry and growth comparisons

| Phase | Group | N | Window share | Gross lowering share | Share / window share |
|---|---|---:|---:|---:|---:|
| alternating_positive | all | 33 | 100.00% | 100.00% | 1.000 |
| alternating_positive | hole_before | 24 | 72.73% | 36.49% | 0.502 |
| alternating_positive | hole_over_projection | 8 | 24.24% | 63.51% | 2.620 |
| alternating_positive | hole_after | 1 | 3.03% | 0.00% | 0.000 |
| alternating_positive | low_past | 11 | 33.33% | 8.02% | 0.241 |
| alternating_positive | other_past | 22 | 66.67% | 91.98% | 1.380 |
| alternating_positive | low_realised_retrospective | 11 | 33.33% | 11.82% | 0.355 |
| alternating_positive | other_realised_retrospective | 22 | 66.67% | 88.18% | 1.323 |
| alternating_negative | all | 33 | 100.00% | 100.00% | 1.000 |
| alternating_negative | hole_before | 24 | 72.73% | 77.72% | 1.069 |
| alternating_negative | hole_over_projection | 8 | 24.24% | 22.28% | 0.919 |
| alternating_negative | hole_after | 1 | 3.03% | 0.00% | 0.000 |
| alternating_negative | low_past | 11 | 33.33% | 22.97% | 0.689 |
| alternating_negative | other_past | 22 | 66.67% | 77.03% | 1.155 |
| alternating_negative | low_realised_retrospective | 11 | 33.33% | 22.97% | 0.689 |
| alternating_negative | other_realised_retrospective | 22 | 66.67% | 77.03% | 1.155 |

Low past cutoff (relative lowest11/33)=0.245000000 mm; retrospective target cutoff=0.248000000 mm; overlap=10/11.

## Allowed and blocked conclusions; storyline impact

These tables localise a deterministic scoring phenomenon on the existing FF tail. Larger lowering share than window share indicates descriptive concentration only. Time, position and growth co-vary in this single dependent trajectory; no causal or population inference is identifiable.
Projection overlap [22.5,27.5] is defined from origin x and does not mean proximity to the physical hole edge. The CSV gives Euclidean origin-tip-to-hole-edge distance separately. Target geometry is retrospective, not input context.
The low-growth groups are exposed evaluation-tail ranks, not a calibrated physical regime or new predictor. The realised target group is retrospective and mathematically related to label-error sensitivity; it cannot independently establish a growth mechanism.
Per-edge d(y) is constant outside the interval of the two predictions on either side. Moving a hypothetical label through that interval changes the score difference. Prediction spacing, target alignment and error phase can explain concentration algebraically, without evidence that actual labels are noisy.
The assumed 68.48 micrometre coordinate bound is uncalibrated. Alternation is a witness, not a measured or likely error process. No label correction, removal of windows, retraining benefit, physical hole effect, true tip accuracy or road generalisation follows.
R001 negative verdict, R002 results and equal-record primary criterion remain unchanged. Stop after the fixed descriptive diagnostic; await author timing/processing and repeatability evidence before any physical attribution or new modelling.
