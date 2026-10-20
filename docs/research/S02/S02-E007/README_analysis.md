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
