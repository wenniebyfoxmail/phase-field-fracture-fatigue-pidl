# HQ-ROAD-UQ-MATRIX-001-R001 intent

- **Authorization:** user message on 2026-10-19 explicitly authorized `HQ-ROAD-UQ-MATRIX-001-R001`.
- **Purpose:** complete the frozen old/new checkpoint × CFD/GAPS matrix under one inference and scoring backend, separating repair-package effects from source and label-location effects.
- **Execution:** exactly one no-training evaluation run on `gpu-server` / `D-26-09`, physical GPU 0, maximum two GPU hours, no retry.
- **Frozen inputs:** D1 scratch U-Net checkpoint `43423f84…205d`; D2 ResNet18UNet checkpoint `92cd9374…27e2`; CFD 118 labels; GAPS384 382 nonempty plus 2 empty labels; CRACK500 A validation cohort used only to fit each frozen model's `U_Z` reference statistics.
- **Snapshot:** evaluator/protocol `49271e498b9019ed6d239e9df368ed9474a9bcb5e9a373efb12f2f26654e89b8`; data lock `1a4a80fb370e89258c24eb623cd166d81ba53da22f3db7321f3a7e71211d51ba`.
- **Stops:** any identity, environment, checkpoint, data, diagonal-comparability or finite-value failure; two-hour deadline. Failure is terminal for this run ID.
- **Excluded:** fitting, optimizer steps, new seeds/models/sources, threshold tuning, pooled-source headline, Road420 access, publication and external messages.

Execution success is only a capability result. Scientific interpretation requires retrieval, independent metric recomputation, decision-facing figures and a bounded claim audit.
