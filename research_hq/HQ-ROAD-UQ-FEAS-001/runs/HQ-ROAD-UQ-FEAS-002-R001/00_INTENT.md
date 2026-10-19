# HQ-ROAD-UQ-FEAS-002-R001 intent

- **Purpose:** determine whether the single locked ImageNet-pretrained ResNet18 encoder repair makes CRACK500-to-GAPS384 published-label transfer and selective acceptance feasible under the frozen D2 contract.
- **Single change:** replace the D1 scratch U-Net with `ResNet18UNet`; all data roles, A-validation checkpoint selection, seed, loss, optimizer, uncertainty scores and gates follow `d2_protocol.json`.
- **Primary evidence:** F1 on 382 nonempty GAPS384 labels and F2 risk reduction at the first 95 accepted images. `U_Z` is retained only if its risk is strictly below `U_LC` at the same coverage.
- **Run:** exactly `HQ-ROAD-UQ-FEAS-002-R001`, one seed, GPU 0 on `D-26-09`, maximum 40 epochs, 5.5-hour training deadline and six GPU-hour hard deadline. No retry.
- **Stops:** identity/hash/environment or inventory drift, nonfinite loss/output, no A-validated checkpoint, or hard budget.
- **Boundary:** finite public published-label diagnostic only. Road420 remains sealed; no physical-truth, width, independent-site, safety or human-review claim.
- **Authorization:** explicit user message on 2026-10-19 authorizing this exact run and resource/budget boundary.
