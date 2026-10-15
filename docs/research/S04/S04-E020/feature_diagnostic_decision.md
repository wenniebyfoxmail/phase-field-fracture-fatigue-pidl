# E020 endpoint diagnosis — completed exploratory analysis, 2026-10-15

Question: why did the delayed schedule fail, and which bounded repair should be prepared next? Existing c20/c60/c83 × reconstructed initial/E019final/E020final, all86756nodes. Source6a3b154, CPUfloat64, chunk1024, no optimiser/model fitting or parameter updates. Checkpoints/references/buffers admitted and saved UV/regions reproduced; all9parameter/buffer digests unchanged, .grad unset.64.38s, process maxRSS839958528bytes<2GiB. Three analytic/chunking/zero-output-gradient tests passed. Findings remain exploratory pending independent review; no frozen E019/E020score changed.

## State-by-state observations

| State | E019→E020 damage-ever-positive units at last layer | Spatial feature rank at relative1e-8 | All-parameter damage/background gradient cosine |
|---|---:|---:|---:|
| c20 |82→71 /283|35→23|−.805→−.954|
| c60 |77→3 /283|67→4|+.067→−.994|
| c83 |172→117 /283|145→86|+.250→+.516|

Ever-positive means positive for at least one damaged node, not simultaneously active everywhere. Mean mass-weighted last-layer positive fraction c60E020=.0000817855(0.00818%). c60input-layer damage-gradient norm drops from1.15421e-5 to4.73289e-10 (~24387times); most remaining gradient lies in output parameters. This is an endpoint feature/gradient collapse relative to E019, not proof of when/why it arose. No negative activation coefficients observed across these endpoints.

c83 is different: many features remain active, input damage gradient remains2.54e-5(E019)/2.55e-6(E020), aggregate regional gradient cosines are positive. A dead-network or dominant regional-gradient-conflict explanation is therefore not established for c83. Successful c20also has sparse last activations and opposing regional gradients. Neither low activity nor gradient opposition alone is a failure test.

Feature Gram includes physical BC/window and output bias, not the full parameter Jacobian. Bias/common modes dominate the uncentred spectrum; entropy rank is not an attainable-fit/capacity bound. Absolute gradient norms across different parameterisations are not optimisation rates. Endpoints cannot recover trajectory dynamics or Adam moments; no causal learning-path claim.

## Geometry check and selected repair hypothesis

Inherited residual-energy centroid in the physical window core stays near x=−.27, while the original geometry-centred input origin moves fromabout−.219 to−.104 to0 overc20/c60/c83. In original normalized x coordinates the centroid offset growsabout−.175/−.413/−.517. Core transverse residual std is onlyabout.0071/.0076/.0092of original yscale. Narrow bands also occur in successfulc20; these are conditioning clues, not proof of the cause.

All-damage raw moments were checked first and retained in residual_coordinate_moments.json; c60yvariance is sensitive to a tiny exterior residual. Proposed mapping uses only original window-core damage, never modifies the window itself. No new locations or hidden FEM states used.

Selected next experiment draft: **one local-coordinate preconditioner vs original E019**, with E019's original cosine schedule, not the failed E020hold. Centre coordinates on inherited core-damage residual-energy moments and cap diagonal scale sharpening at4×; keep physical support, BC, frozenbackbone, width/depth, fullobjective, sampler, seed7 and10000newupdates. This tests coordinate conditioning instead of asserting insufficient capacity or changing loss weights. S04-E021/experiment.md and coordinate_maps.json freeze the proposed rule and exact3maps. New prototype passes3nontraining checks plus3real full initial-prediction admissions (max1.27e-15difference from inherited). No candidate trained, runner/aggregator and exactindependentCodeReady/producerapproval still absent.

## Numerical audit and assets

v1 NumPy matmul emitted warnings though saved values were finite. Preserve that attempt. v2 uses TorchGram plus explicit scalar reductions, first-chunk independent Gram-submatrix checks, finiteness checks and warnings-as-errors; completes without warnings. All9v1/v2spectra agree (maxeigenabsolute difference0), activation and gradient reductions agree. No warning suppression or score/tolerance relaxation.

Tables feature_diagnostic_summary.csv/feature_gradients.csv, detailed localresults/summary.json, execution_receipt.json, reduction_crosscheck.json. Finalfigures in local_archive/experiments/S04-E020/nontraining_feature_diagnostic_v2/analysis_core_final; inspect README_analysis.md. Original E020primaryFAIL, strictMacINADMISSIBLEreference-rho exception and pending Evidence review unchanged. No external send, producer access/job, sweep or addedtraining.
