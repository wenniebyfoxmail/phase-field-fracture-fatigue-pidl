# Review card: proposed HQ-ROAD-UQ-FEAS-002-R001

**State:** prepared for review; no execution authority recorded.

| Field | Exact proposal |
|---|---|
| Purpose | Test whether one pretrained-backbone repair makes CRACK500→new-public-B transfer and selective acceptance feasible under the existing contract. |
| Data A | Frozen CRACK500 train 1,860 crops/245 parents; validation 341/49; test 200. Existing exclusions unchanged. |
| Data B | GAPS384 author-published pixel reannotations: 384 pairs; primary 382 nonempty; two empty masks reported separately. |
| Single change | Replace scratch U-Net with `ResNet18UNet`; encoder initialized from torchvision ResNet18 `IMAGENET1K_V1`, SHA-256 `f37072fd…e07ec`. |
| Unchanged | Seed 20261011; Adam lr 1e-3; 0.5 BCE + 0.5 soft-Dice; batch 8; 320×320 training crop; A-validation-only checkpoint selection; native-pixel tiled inference; `U_LC`, `U_H`, `U_Z`. |
| Proposed producer | `gpu-server`, host identity must resolve to `D-26-09`, GPU 0, Windows CUDA. |
| Run budget | Exactly one run, `HQ-ROAD-UQ-FEAS-002-R001`; maximum 40 epochs; 5.5-hour training deadline; six GPU-hour hard deadline. No retry. |
| Stop rules | Stop with no automatic retry on identity/hash/environment drift, inventory mismatch, nonfinite loss/output, absent A-validated checkpoint, or hard budget. |
| Outputs | receipt, selection and fit status, best checkpoint, A val/test metrics, GAPS nonempty/empty metrics, risk curves, failures, result and analysis note. |
| Explicitly excluded | Road420 access; any new C/holdout; dataset mutation; extra seed; threshold tuning; second repair; publication or external message. |

Execution requires a new approval file tied to the final code snapshot, data-lock hash, environment, host and this single run ID. The earlier D1 execution approval does not cover this run.
