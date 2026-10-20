# ISTRUST sixth-epoch replay — aggregate reproduced, specimen differences retained

The released R004–R006 batch completed all six physical test folds and all three fixed seeds without training or observation-uncertainty experiments. Independent float64 recomputation from every archived draw gives primary held-out normalized MAE **0.257049984675**, within the predeclared **[0.255,0.265)** bin for the published **0.26**. Other fixed seeds give0.257469778669 and0.257622716631. This is aggregate display-precision reproduction; **only1/6 primary specimen cells matches its Table2 rounding bin**, so full Table2 reproduction has not been established.

| Specimen | Published test MAE | Primary MC40 replay |
|---|---:|---:|
| A009 |0.14|0.13484|
| A011 |0.41|0.41053|
| A012 |0.15|0.15588|
| A013 |0.31|0.32818|
| A014 |0.29|0.27797|
| A019 |0.21|0.20237|

All six normalization reconstructions passed before any model forward (max mean/std differences5.96e-8/1.19e-7; max-training-RUL differences0). Independent checks covered634test/3626training-eval windows per seed, finite raw draws, unique keys, physical folds, metric recomputation and unchanged parameters/BN buffers. The predeclared five-draw diagnostic gives0.26263800 and does not restore every fold; it does not replace the primary. Paper training rows are online/augmented/dropout0.1 losses, whereas frozen training-eval uses saved weights/unaugmented data/dropout0.3. Python/Linux/GPU and historical RNG differences are documented without attributing all residuals to them.

[Full comparison, trajectories, differences and costs](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S02-E007/runs/S02-E007-R004/analysis/README_analysis.md). [Raw-derived comparison](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S02-E007/runs/S02-E007-R004/analysis/comparison.json). [Table2 CSV](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S02-E007/runs/S02-E007-R004/analysis/table2_complete_comparison.csv). [Run receipt](run_S02-E007-R004.json).

![Six-specimen published versus replay comparison](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S02-E007/runs/S02-E007-R004/analysis/published_vs_replay.png)

See: the aggregate rounds to0.26, but several specimen points miss the published bins consistently across the three streams.
Therefore: use this saved-weight component baseline with its stated discrepancies; do not claim exact Table2/training-from-scratch reproduction, observation-uncertainty benefit or future crack-geometry validation. The trajectory plot also shows structured bias/camera differences; dropout SD-bootstrap shading is not a calibrated predictive interval.

Implementation remains b9b72c5e24f584f2550a50675b14d4c731976f62 and runtime archive af22a199f65f5ff35e66e86b17736b15d42bc998eb19b5d9924df8b06dbd77e7. Actual Linux15checks, numeric PCI mask and physical driver UUID admission passed. Controller3729307 and worker3744277 exited0; retrieved exit evidence confirms live=[] and noGPU5compute-apps,4MiB/0%.220retrieved files were individually hash-verified. Current execution charge1308.752054seconds includes460prelaunch+22.222339admission+826.529715controller;412.239578worker seconds are inside that controller duration. Retrieval10.568449seconds and local closing costs are separately retained. Sampled RSS4.723GiB/task13.006GiB fit the32/40GiB limits. Exact all-history cost and actual GPU busy time remain unavailable rather than zero.

Human-delegated HQ approval and later scheduling release were verified and transparently recorded. The one released batch consumed its authority; no further inference/retry/seed or UQ follows automatically. The old R001 failure and immutable reviewed launcher remain intact. D2 computation/recomputation is complete; D3 concerns the residual publication differences. Observation uncertainty remains deferred as requested.

## Earlier admission and preparation record

# ISTRUST sixth-epoch reproduction: admission stop

The baseline has **not been reproduced**. The loader ordering fix, frozen replay and source/checkpoint package passed independent local review; the first Taobo CUDA admission returned exit 1 before the controller was launched. No dataset extraction, image preprocessing, model forward, training or observation-uncertainty comparison occurred. The published 0.26 MAE has not been measured anew.

| Component | Verified result | Meaning |
|---|---|---|
| Public assets | Full local ZIP SHA/CRC/decode and all270 checkpoints audited; six epoch-six pairs packaged/strictly loaded | Assets are available; no forecast result |
| Original replay implementation | Commit5daa9f2b,15 local checks, independent review passed | Ready subject to producer admission |
| Isolated runtime | All seven pinned CPU-import versions agree | Numerical/image versions prepared; Python3.10/Linux differs from paper3.9/Windows |
| GPU admission | Scalar probe exited1; controller absent; original probe stderr was not retained | Execution stopped, not a test of published accuracy |
| Read-only compatibility diagnosis | Actual installed torch1.13 parser: UUID→{-1}; numeric5→{5}; NVML count logic gives0 versus1 for eight devices | Confirmed compatibility bug sufficient to explain the assertion; other CUDA problems remain possible |
| Proposed correction | Numeric PCI-ordered mask plus CUDA-driver physical UUID proof before torch import/allocation; complete stdout/stderr and owned-process receipts | Exact code/launcher review passed; fresh human retry approval pending |

## Preserved evidence and differences

Original source/epoch-six archive SHA-256 remains1cb85f1b93c1c32801b9bf973d3f5e122276bbbe03a78965525c0c411f49f1a6. Published data ZIP remains1d5f2be8ab0ef0547f7fd4ade517d1f91076d1bdec4dcf156b6a089dff000c25. Raw provenance,19 retrieved failure/runtime/source files, pure CPU parser audit and old preparation failures are under local_archive/experiments/S02-E007/runs/S02-E007-R001; see run_S02-E007-R001.json for absolute paths.

The only approved author-source change is sorted filename iteration in a copied loader. Preserve A003 training membership, j/j+3/j+6 inputs→j+7 target (median52s ahead), retrospective RUL<4000 selection, six physical test folds/634 windows, and original MC dropout. Table2's online training row differs from frozen-model training-eval; historical SD-bootstrap bands are not calibrated RUL prediction intervals. Original CSV reconciliation0.2606646 is historical evidence, not a new replay. No default-best epoch search or training is included.

The public data endpoint's bounded1MiB range probe returned206 but only28,938bytes/s. Reviewed intake amendment1.2 therefore uses32 disjoint validated ranges with10MiB/s total cap, four CPU cores and90minutes inside the same four-hour batch limit. No full producer data intake has started.

## Next decision

Prepare amendment1.3/fresh proposed R004–R006 with the same original seeds and scientific criterion. Require independent review of the exact corrected package and launcher. Fresh human approval is required before another CUDA admission or producer replay; the first stop remains unchanged. If approved, verify pinned CPU versions,15 synthetic Linux checks, admitted physical UUID and scalar CUDA operation, then execute the bounded intake/preprocessing/replay. Any further failure stops without automatic retry. Observation uncertainty remains deferred until an interpretable baseline exists.

## Final local review record — execution still pending

Implementation b9b72c5e24f584f2550a50675b14d4c731976f62 passed20 local checks and independent read-only review. The exact corrected launcher SHA25663e315c9574276cbf89a0d7685f79d2edfd2efc47a9afca6e9a30f166f8c5233 and28,442-byte runtime snapshot SHA256af22a199f65f5ff35e66e86b17736b15d42bc998eb19b5d9924df8b06dbd77e7 also passed independent review. All16 snapshot files matched that commit. This status update is report-only; the reviewed runtime archive remains bound to b9b72c5e.

The final reviewable scope and approval state are in local_archive/experiments/S02-E007/runs/S02-E007-R001/retry_v13_candidate/README_READY_FOR_APPROVAL.md. Fresh R004 has not been created and no corrected CUDA call has occurred. Actual Linux admission and numerical replay remain pending direct human approval under the frozen first-stop rule.
## 2026-10-20 evening — delegated HQ authorization; scheduling hold

A newly verified direct user delegation in HQ thread01a14bb9-6cd1-7ee2-9647-5190d786f7ba (user message01a15b4c-2e3a-7772-b74b-46f4ab752766) authorizes HQ research coordination and computation until21October09:00Europe/London. HQ prospectively approved the unchanged reviewed b9b72c5e corrected admission and R004–R006 baseline within the original14400-second total and unchanged scientific/resource/first-stop limits. This new authority is recorded as human delegation plus HQ approval; it does not recast the consumed R001 attempt or fabricate a direct task approval.

GPU5 is scheduled for Mesh first. HQ currently permits only local preparation and expressly prohibits SSH probing, transfers or GPU execution until its explicit release based on Mesh exit/resource facts. Local authorization adaptation and receipts are under /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S02-E007/runs/S02-E007-R001/retry_v13_candidate/delegated_hq_launch/. The numerical runtime archive remains unchanged. The separate release receipt is false and preparation cost remains unfilled, both preventing launch. Seven local authorization checks passed; narrow launch-control review uses the already selected reviewer and carries forward the unchanged numerical review.

The active scientific decision remains whether the frozen sixth-epoch checkpoints reproduce Table2. No new producer operation, CUDA admission, image processing or model forward has occurred under this prospective authority. Observation uncertainty remains deferred. On explicit HQ release, verify any unknown prior launch status before spawning once; charge active preparation/transport/admission/replay to the original total, retain all outputs/costs and stop at the first failure without retry or later-seed rescue. No further human approval is required for unchanged in-scope mechanical completion.
