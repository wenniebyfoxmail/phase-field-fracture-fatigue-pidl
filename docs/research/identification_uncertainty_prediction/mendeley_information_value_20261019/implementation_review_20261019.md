# Implementation review and launch authority — 2026-10-19

User explicitly authorised checking this package and proceeding when sound; SCB mail must not be sent. This authorises in-contract correctness/performance repairs and the proposed 1-thread/4h/8GiB/0-GPU experiment, not new scientific arms, retries or budget expansion.

Evidence stage is development-exposed exploration, so the installed research-review-channels workflow calls for local checks; no external review or subagent was dispatched. This receipt is the implementing agent's code review, not an independent formal-review verdict.

Findings and resolutions:
- Live metadata preparation admits all19 released groups:1144 origins/2288 horizon-cases, common cohort across arms;1963 candidate origins cross PT chunks and228 lack required stages. No actual machine-cycle or physical-independence claim.
- Repeated PT/field-feature reading would unnecessarily dominate runtime. Added bounded owning frame cache (8192*2*128*128 float32 <=1GiB) plus small derived-state cache. Eight PT-container LRU retained; scenario cached features exactly equal original direct computation in artificial-array tests. Model, targets, histories, grouping, alpha grid and primary loss unchanged.
- Save float64 coarse predictions/envelopes so archived outputs reproduce float64 scoring; record fold training fixed-width value for inference reconstruction.
- Oracle block-mean output projection remains a future-informed diagnostic, not a forecast competitor or mathematical MAE lower bound.
- All learned arms share native current-field persistence as an output skip connection. The representation comparison concerns what the **increment predictor** encodes, not whether the complete forecast ever accesses a native current field. This narrows interpretation, without changing the approved algorithm.
- Available-case windows are conditioned on complete finite published observations; exclusions are retained. No unconditional missing-data, calibrated physical-error, true-crack-length or untouched-source claim.
- Four metadata and four artificial-array correctness tests pass (no fitting on Mac). Actual tensor import, pinned-file mapping, native shapes and finite values to be checked on producer before fitting. Production evaluation stays on Taobo CPU.

Taobo inspected live:GPUServer8,64CPU,~379GiB available RAM,~620GiB free on/mnt/data2; /usr/bin/python3 provides numpy1.24.4/torch2.7.0+cu126/matplotlib3.10.3. CUDA hidden; no GPU requested. Import under8GiB address-space limit succeeds (~3.48GiB VmSize,~417MiB RSS). No shared processes altered.

No scientific results at review time. Run stops on error/budget with no automatic retry; partial outputs preserved. User approval applies to this bounded repaired deployment; no further confirmation is needed for these routine repairs under the explicit check-and-proceed request.
