# Constrained variational FEM–neural hybrid

Current delivery — 2026-10-19: complete development-library/API implementation independently reviewed PASS at `a76825eb2fdc750557b5a4c0bb2d542d2ee11c60`; 33 engineering checks passed. This is not producer-ready or a measured scientific improvement. No project FEM solve, training, GPU or held-out access occurred. Existing seen c1 data was read only for the expressly requested label audit.

- [Current implementation and scope](implementation_v2.md): full nodal-K damage/complete mechanical coupling, accepted/trial history, transaction and frozen native-graph network API.
- [Independent code review](code_review_v2.md), [JSON](code_review_v2.json): v1 R1–R4 resolved; exact source and document hashes verified. V1 review retained.
- [Checks](implementation_checks_v2.json), [exact snapshot](implementation_snapshot_v2.json), [delivery receipt](implementation_delivery_v2.json).
- [Existing label audit](existing_label_audit_v2.json): 5 reusable seen c1 candidates, 0 certified new-framework training labels, 0 qualified complete trajectories. Old native acceptance conclusions remain unchanged.
- [Complete validation budget proposal](validation_budget_v2.md), [machine-readable budget](validation_budget_v2.json): 3600 numerical substeps, 12GPUh, 136CPU wallh/2176coreh and 128+128GiB storage caps; not authorized/executed. Includes GPU host CPU and all offline/correction/fallback costs.

Original design phase: [frozen design v1](design_v1.md), [independent design review](review_v1.md), [design decision](decision.md). Design SHA256 `ca50ad0e4913308165745311ece5ff1226f93b8c5c3b5e17512e7df240531b0d` is unchanged. Design and v1 implementation/budget artifacts retain their historical scope; v2 is the current implementation/inventory/budget.

No claim of trained-model availability, numerical convergence on project fields, field improvement, acceleration, teacher qualification or generalization follows from these unit checks/reviews. Future numerical work is one integrated method comparison, not a compulsory scientific micro-test sequence.
