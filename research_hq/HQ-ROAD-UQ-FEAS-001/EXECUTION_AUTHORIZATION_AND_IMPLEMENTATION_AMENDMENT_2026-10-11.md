# HQ-ROAD-UQ-FEAS-001 D1 execution authorization and implementation amendment

The user explicitly authorised D1 and `gpu-server` on 2026-10-11: “授权执行 HQ-ROAD-UQ-FEAS-001 D1，可使用 gpu-server。” The sole run identity is `HQ-ROAD-UQ-FEAS-001-R001`; producer alias `gpu-server`, expected hostname `D-26-09`, GPU 0, seed 20261011, maximum 40 epochs or six GPU hours, and no automatic retry or adjacent arm.

The frozen scientific contract remains the registered D1 contract. This implementation fixes native-pixel inference to reflect padding to a multiple of 16 and, only when an image exceeds the fixed 640-pixel window, deterministic 640×640 overlapping tiles with 96-pixel overlap and arithmetic probability averaging. This bounds memory without deformation resizing. CRACK500 validation alone selects the checkpoint. CFD is used once for the frozen feasibility gates. Road420 is represented only by its pre-recorded SHA-256 identity string; the runner accepts no Road420 path and may not enumerate or read that dataset.

The result class is limited to a positive-rich public published-reference segmentation feasibility diagnostic. It cannot establish physical crack truth, natural prevalence, independent-site generalisation, field safety, crack-width accuracy, or human-review utility.
