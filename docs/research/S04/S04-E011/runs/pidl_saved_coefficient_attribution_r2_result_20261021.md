# PIDL c20 saved-coefficient attribution R002 — actual result

Purpose: locate the common PIDL derivative mismatch before resuming hidden-feature optimization. The state is the same frozen c20s4, FEM damage, source PIDL history, B0 Smooth Boundary, original UV boundary, actual Phi/T0, seed173/scales/h=1e-6 and original head threshold1e-10. This is a saved-array derivative diagnostic, not a new FEM or PIDL physical solution.

## Execution and provenance

Authority HQ-MESH-SAVED-COEFFICIENT-TRANSPORT-R002-20261021/human_delegated_hq explicitly amends Mac transport AS control and permits one new case. Execution source496638e9, branch codex/hard5-q4-t3-2x2-20261005. Scientific script SHA256 ad17cf246fff617b6f9e1129aef7a941ad9707c4c2fb5699a7f7658d1c6b52e1 unchanged. Old source run pf_s04e011_frozen_completion_r2_hq_20261021, manifest964c92eec66a5edce6da3d87623db5a04c67864711dbc8b2317f91d2105dee8b. All74 input bindings verified.

One SSH to gpu-taobo performed CPU analysis and completed streaming retrieval in the same process. New output /mnt/data2/drtao/wennie/pf_s04e011_saved_coeff_attr_r2_20261021; local case /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/saved_coefficient_transport_r2_20261021. All48 returned files/SHA/bytes verified, 37,513,865 raw bytes,26,010,485 network bytes; no Phi transfer. No second SSH, GPU query, new model/checkpoint/AD/JVP/VJP/force/K/FEM/SVD, perturbation, factorization, optimization or history commit. Ten vector solves/twenty triangular solves reuse old factors; zero new factors.

## What was decomposed

For each stored side, q_s=r_s+B_s z_s; w_s=z_s-z0. The authentic RHS is a_s=minus the original initial gradient at z0, from the accepted Newton journal, not a global b constructed as H*z_end. The journal, old factor identity, one alpha=1 accepted step and exact z_s=z0-stored_solution were checked. Constant/zero source z0 norms are0/2.80e-14.

With delta meaning centered coefficient secant, Jsec=delta r+delta B*z0; e_s=H_s*w_s-a_s. The old FD is decomposed into Jsec, B0*H0^-1*delta a, finite-B and finite-H cross terms, independent RHS residuals and offline field-reconstruction differences. Old analytic Q is independently reconstructed as J_AD-B0*H0^-1*U. See the unchanged [full algebra](../saved_coefficient_attribution_20261021/README.md). Saved endpoint defects are separately reported; e-end_defect is an observed affine-consistency discrepancy, not certified pure rounding. Offline field reconstruction includes new CPU product arithmetic.

## Numerical result

All norms below use the original free-UV ordering and unweighted Euclidean L2. Q/FD are PIDL derivative fields, not FEM/PIDL physical displacement errors.

|Quantity|Frozen constant target|Frozen zero root|
|---|---:|---:|
|Original ‖Q−FD‖₂|0.009506254089|0.009506254020|
|Independent old-Q reconstruction error|4.46e-11|6.38e-11|
|Coefficient-secant Qsec versus old FD|0.000788231860|0.000788231828|
|Complete decomposition closure|4.43e-10|4.40e-10|
|Closure / original mismatch norm|4.66e-8|4.62e-8|
|AD–secant J component norm|0.008109730444|0.008109730443|
|AD–secant head component norm|0.004878376627|0.004878376548|
|Finite-B component norm|0.003926166388|0.003926166723|
|Finite-H component norm|0.003921174597|0.003921174922|
|Endpoint-head-defect component norm|1.28e-9|1.95e-9|

The two AD–coefficient-secant components have combined signed projection0.989677 along the original mismatch; net finite-B/H projection is0.010323. Projection means dot(component,mismatch)/‖mismatch‖². It is descriptive vector attribution, not a causal percentage, physical improvement or fraction of independent error. Individual component norms cannot be added: B/H components cancel strongly. The smaller Qsec-FD mismatch is an offline diagnostic substitution, not an accepted optimization update.

![Component norms and signed projections](/Users/wenxiaofang/obsidian/attachments/S04-E011/2026-10-21/pidl_saved_coeff_r2_coefficient_decomposition.png)

![Constant-target derivative mismatch and decomposed fields](/Users/wenxiaofang/obsidian/attachments/S04-E011/2026-10-21/pidl_saved_coeff_r2_coefficient_fields.png)

Both figures inspected visually: labels/color scales legible, source/derivative identity explicit. Spatial panels use the same cell-RMS magnitude scale; magnitudes do not add even when underlying vectors do. They localize derivative discrepancy, not a new crack or physical displacement error.

## Conclusion and exact remaining uncertainty

The saved-array equality closes much more tightly than the original0.009506 mismatch. At this frozen state, direction and h, the dominant mismatch direction is between the source analytic derivative and actual stored coefficient secants. Endpoint root defects are small in this decomposition. Constant versus zero root gives essentially the same localization. This does not establish that AD is implemented incorrectly or that all numerical errors are bounded.

Two live explanations remain: (1) finite-h curvature/truncation along the actual parameter-to-coefficient path; (2) floating-point parameter/feature/basis arithmetic amplified by cancellation/conditioning. Jsec norm~53032 versus corrected Q norm~13 shows cancellation exposure, not causal proof. Actual rounded parameter endpoint arrays were not saved; nominal direction/scales and binary64 dtype cannot reconstruct that path. A complete force/assembly/field forward arithmetic certificate is still absent; exact algebra closure is not such a certificate. Global b was not independently saved, although the authentic initial-gradient RHS and exact accepted update were bound.

Next design only: a scale-aware same-path coefficient/profile check that persists actual parameter endpoints and separates path curvature from arithmetic amplification, before restoring hidden optimization. No new h/direction/precision sweep, parameter update or3000-second chain in this case. Do not infer fixed-feature or network-capacity limitations from this diagnostic.

## Physical comparison remains unchanged

Frozen FEM c20s4: E=0.00432057602453, free Ru~3.776e-15. Prior PIDL endpoint evaluated under the same FEM damage: E=0.00526840000522, free Ru=0.0134889412, UV mass-relative-L2=7.54865147%, active weighted-relative-L2=6.1208993, correlation0.102517986. No new accepted PIDL field/evolution or FEM result. Spatial-operator and Carrara commit-state alignment does not remove committed-f versus FEM trial-f or joint Deep-Ritz versus staggered/Picard method differences.

## Costs and checks

Whole budget1200seconds,00:53:54–01:13:54UTC; CPU300seconds split remote220/transport25/postprocess25/reviewer10/metadata20. Remote total-process CPU17.6429seconds, wall23.918654seconds, peak RSS938,250,240bytes, hard AS16GiB/CPU220, one thread. Primary pre-tar math CPU2.69824seconds is not the total remote cost. Input hashing921,517,113bytes; logical array reads8,694,697,536bytes; physical disk bytes UNKNOWN (ru_inblock113448 raw).

Mac client CPU6.881136seconds plus SSH child0.36659seconds, wall28.477095seconds. Transport sampled owned RSS51,216,384bytes, max sample gap0.147643seconds at configured0.1seconds. Recorded VM867,363,717,120bytes is not RSS/scientific allocation. Explicit AS exemption applies; sampled RSS512MiB is user-space monitoring, not a kernel hard guarantee. Plot total CPU1.624057seconds, sampled RSS297,058,304bytes, max gap0.150516seconds. One local controlled lifecycle fixture CPU0.194354/wall0.758184seconds. Measured subtotal26.709037CPU seconds excludes unmeasured metadata/reviewer; do not call it complete whole-task CPU. Whole final closure checkpoint and result review are recorded beside this report.

No resource/identity refusal or monitor failure; all selected returned hashes checked, current source clean before result recording. Prior failed first saved-attribution attempt remains stopped before SSH with793.671966wall/CPUUNKNOWN; prior producer failures and all physical endpoints remain unchanged. Compact JSON/receipt/CSV/review are in the adjacent directory; large arrays stay in local/remote archives.

## Final record audit

Independent scalar/receipt/figure review passed; no original arrays/solves were rerun. Figure sidecars and Git whitespace checks passed. Result/receipt hashes match the independent review; scientific script and copied figures match recorded SHA256. Final audit checkpoint 2026-10-21T01:09:11.715986+00:00, whole wall 917.716seconds before commit, within1200seconds. Reviewer metadata measured0.030119CPU seconds; reading cost otherwise UNKNOWN.

Resource-record limitation: later local stdlib report writing and shell reads/checks were not RSS sampled; their CPU/RSS are UNKNOWN. This does not change the saved numerical result, but whole-task resource conformity is not established for that metadata segment. Remote science, transport, plots and reviewer controls retain their measured records. No scientific/model/array operation was performed in the unmonitored metadata segment.
