# Existing-state s4 exports — verified retrieval, not G5 full PASS

All outputs are derivative read-only exports, not FEM/PINN solves or training. Failed v3 old/native geometry and v4 bounded-PIN input verdicts remain frozen. v4 native64 geometry and v5 signed-input exporter had independent Code Ready/data-input review before execution.

| Producer / Run | Execution / retrieval | Admitted meaning |
|---|---|---|
| Taobo pf_g5_u0115_s4_export_20261013_v5 | exit0;11:37:14–11:37:30UTC;CPU4/noGPU/300s;100 s4 rows;NPZ/control retrieved and SHA matched | signed current PIN coordinate, histories/raw/f/proxy; no clipping |
| CITPC12 g5_export_run_20261013_v3 | MATLAB -singleCompThread exit0;four MATs/receipt retrieved, all hashes matched;solver_started=false | native Q4 nodal/GP s4 reductions, not cyclemax/s5 |
| Native64 mapping |85112 admitted/1296 excluded;98.60692258% area;only removed cell57509/no new admission | declared centroid P0 query, not conservative area integration |

Local payload root: local_archive/experiments/S04-E016/g5_export_20261013 (pin_v5_retrieved/fem_v3_retrieved/geometry_native64_v4). Original archives remain unchanged and remote. Code identities: Python5fa18adb…2f2d7, MATLABcc846227…a8e7; see signed/native64 amendments for full identities. Mac base5b1eec29…249, owning task branch dirty snapshot explicitly recorded. Windows had an unrelated E011_BT single-thread MATLAB chain5480→39452; it was identified, not stopped or modified. This task started only a built-in load/reduce/save exporter, no second Request31 FEM solve.

PINN body audit: five fields (100,86408) float32, all admitted values finite, all1296 excluded columns NaN, cycles/raw steps exact5c-1. All100 diagnostic histories exactly equal their checkpoints **at export float32 precision**. Native signed current alpha range[-0.00023812137078493834,1.001720666885376]; admitted min -0.00022201149840839207. This is not physically bounded qualification. Proxy factor may exceed1; no native active closure claimed.

FEM body audit:122/83/59/100 rows for .11/.12/.13/.115; five finite float32 channels;d/f in[0,1],history/raw/active nonnegative;all four native meshes identical in exporter. Index/static and each s4 payload identity were checked against sealed source manifests. Native FEM areas now provide weighting, never old float32 intermediate areas. Nominal s4 load matches; FEM effective factor0.999999 vs PIN1 remains explicitly distinct.

Old-three structural/value audit: assignments exactly match candidate mapping; peak steps5c-1;qualified-prefix finite checks passed for d/ab/f/raw/active. Signed current d is preserved;all other field bounds held. Prior R3 export summary freezes cross-runtime tolerances scaled-max1e-3,scaled-mean1e-4,relative-L2.01, with exact history/f spot checks. Source posthoc triangle means/direct numerical strain energy and residual_stiffness0 match declared proxy semantics. No old export rerun, field score or D003 recomputation.

Candidate common pre-event rows: .11c1..121/.12c1..82/.13c1..55/.115c1..99,357 total. U0.13 replay is post-native-event and excluded. Terminal native PIN detector keys checked, but full episode/reset evidence still pending; terminal fields alone do not establish earliest detector episode. Candidate lock paired_s4_lock_candidate_20261013.json is NOT approved. PINN-only32-feature pipeline with whitelist/causal lags/globals/neighbors and toy future-perturbation test is under independent review;scalers/model runner still must enforce nested training-only fits.

G5 full/teacher/Contract A independent numerical qualification remains HOLD. Contract A is audit-only, not D0 labels;U0.1175 scientific confirmation/U0.125 remain closed. The proposed next decision is a separately labelled archive-imitation D0 admission only, after all source/reset/input locks and independent review. No D0, Delta NN or further producer run occurred.
