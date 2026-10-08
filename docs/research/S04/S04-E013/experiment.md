---
storyline_id: S04
experiment_id: S04-E013
protocol_revision: 20261008-r0
status: stage1-code-ready-pass; frozen-taobo-matrix-authorized-not-run
---
# Freeze separate PIDL evaluation contracts after S04-E012

## PIDL Experiment Gate

- Mechanism question: can the project distinguish displacement representation/optimization failure from free-running trajectory failure by evaluating the same candidate under two separately frozen estimands?
- Claim changed if success: a candidate may earn either `UV_BLOCK_REPRODUCED` under the conditional strict-physics reference or `NATIVE_FEM_FIDELITY_REPRODUCED` under the original FEM trajectory contract. Neither status is a full-teacher claim.
- Claim changed if failure: identify whether the first failed stage is reference/asset admission, supervised representability, unsupervised UV physics, or free-running trajectory fidelity.
- Cheaper diagnostic first: inventory existing FEM/PIDL assets and freeze metrics before any training. Do not rerun a long trajectory while early/middle/late or within-cycle outputs are missing.
- Minimal output asset: reviewed evaluation contract, machine-readable coverage table, and an executable result schema before producer launch.
- Code/producer alignment: Mac performs contract and asset audit only. Any training or full trajectory rerun must use an approved producer after exact-commit review.
- Success criteria: the contract keeps training signal separate from evaluation reference, assigns every row a state/comparison class, uses identical evaluation for supervised and unsupervised UV branches, and prevents either route from upgrading the other.
- Failure criteria: missing c20/c60/c82/c83 plus s2/s4/s5 coverage is hidden; late states are substituted for early states; supervised labels leak into the unsupervised loss; or any UV-only pass is promoted to full FEM-teacher validity.
- Registry destination: S04 storyline and `censor.md` after independent design review; experiment inventory after an executed attempt.
- Decision: diagnose and freeze first; no training launch in this experiment.

## Stage sequence

0. **Asset and identity closure.** Admit exact references, mappings, hashes, state labels, and complete export coverage. Missing assets remain `NOT_EVALUABLE`.
1. **Supervised UV capacity ceiling.** With FEM damage fixed, fit displacement to the conditional UV-derived reference. This asks whether the representation can express the target field.
2. **Unsupervised UV physics reproduction.** With the same fixed inputs and evaluation metrics, train from the physics/energy objective without reference displacement in the loss. This asks whether the objective and optimizer recover the field.
3. **Native FEM fidelity.** Run a free trajectory and compare same-cycle c20/c60/c82/c83 at s2/s4/s5, plus own-event fields. This asks whether the model reproduces the original FEM output path under its native acceptance semantics.
4. **Claim assignment.** Report route-specific statuses. `UV_BLOCK_REPRODUCED` and `NATIVE_FEM_FIDELITY_REPRODUCED` are separate. `FULL_FEM_REPRODUCTION` and `QUALIFIED_FEM_TEACHER` remain unavailable under the current evidence.

The detailed contract is in [evaluation_contract.md](evaluation_contract.md). Current assets and blockers are in [coverage.csv](coverage.csv).

The c60 reference runner and paired-control exporter are specified in [stage0_implementation.md](stage0_implementation.md). Their execution is Stage 0 asset production only and does not authorize candidate training.

The c60 launcher-only retry `S04-E013-R002-c60-uv` completed with exit code 0 and passed its frozen UV-block gate. The independent Stage 0 review returned `Evidence PASS`, so c60s4 is admitted only as a conditional fixed-damage/frozen-fatigue UV reference; `full_teacher=NOT_QUALIFIED` remains fixed. The corrected paired exporter at commit `19a5c13d5dcc2d1888528621dc6ff459c59dbe3d` received exact-commit `Code Ready PASS`; formal Taobo run `S04-E013-R003-paired-export` produced all 13 declared rows, and remote plus post-retrieval local verification passed. The same Evidence review admitted the 12 same-cycle rows and c85s4 own-event row as `PAIRED_CONTROL_ASSETS_READY`. Candidate training, route promotion and Stage 0 scientific closure remain unauthorized; see [stage0_evidence_review.md](stage0_evidence_review.md).

The Stage 1 planning gate first returned `NO-GO` because the proposed capacity interpretation, stochastic loss, residual semantics and implementation constants were underspecified. The corrected finite-budget reproducibility contract then received `PLAN PASS`. The runner and 12-run aggregator are implemented, and all four admitted references pass the local no-training identity/evaluator check. Producer training remains blocked until the implementation receives exact-commit `Code Ready PASS`; see [stage1_training_authorization.md](stage1_training_authorization.md).

The first exact-commit Code Ready review of `5767e6c` found fail-open aggregation paths and returned `NO-GO`. Commit `769396f93ae5258eb984e1585d4274f7990afb11` added independent gate recomputation, strict metric types, complete checkpoint/prediction/receipt and archive verification, explicit `INADMISSIBLE` handling, and corruption-path tests. Re-review returned `CODE READY PASS`. The frozen 12-run Taobo matrix is authorized but has not been launched; see [stage1_code_review.md](stage1_code_review.md).
