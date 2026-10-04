---
storyline_id: S04
experiment_id: S04-E002
protocol_revision: draft-20261005
status: draft
scientific_verdict: pending
---
# Supervised native-Q4 projection followed by frozen-state physics polish

Purpose: separate approximation under a controlled fitting procedure from movement under the frozen PIDL physical objective. This is an auxiliary supervised diagnostic, not physics-only simulation or a trajectory/generalization result.

Existing work checked: bounded two-arm step413 matrix and bounded adaptive Picard completed in another active task. Smooth-B0/direct-Q4 code is being advanced there; do not duplicate those runs or edit that task's worktree.

State issue: canonical production has a U=0 recovery step. c83 peak is step414, and the true preceding accepted state is step413 at 0.75 peak. The historical step412-to-peak experiment is a distinct skipped-substep counterfactual pending state-label reconciliation, not automatically the actual production next step.

Source assets: native production aaf13fd full_selected checkpoint/network413; native-Q4 exact peak FEM c83 s004 v2.1. Actual FEM boundary values and coordinate domain checked: [-.5,.5]^2, bottom (0,0), top (0,.11999988), matching the original displacement lifting.

Reuse: source ff42cb9 Q4/energy/network/field kernels, plus existing optimizer/objective-discriminator logic. The old alpha0_fem_to_pidl_projection.py is a mesh-field aggregation audit, not a supervised network fitter; do not reuse it as an expression test.

External Pro design review requested before new loss/threshold implementation. No training admitted until protocol freeze, meaningful unit tests, exact-commit independent review and producer smoke. Windows D-26-09 expressly authorized by user; inspect scheduler before each actual run. Runtime setup is task-local and is not a numerical run.

## Input preparation evidence (2026-10-05)

Read-only `scripts/censor_projection_diagnostic/audit_inputs.py` passed. Exact FEM coordinates converted to production float32 plus int64 connectivity hash to `e16c9b230c07cc747f5544de1b2bc4afa42be0f6ff645f67b81671307c7eea0e`, matching checkpoint413. There are 86,756 nodes and 86,408 cells. FEM bottom UV and top U are exactly zero; top V is exactly 0.11999988. FEM damage is [0,1]; accepted PIDL413 damage is [-0.0101727592,1.0008522272]. Consequently this proposed follow-up is still a projected legacy-history counterfactual, not a fully bounded-history restart.

Input manifest and read-only audit: `local_archive/experiments/S04-E002/inputs/manifest.json` and `analysis/input_audit.json` (project-root archive). Production log lines 2104/2109 independently identify step413/414 load values. Three source assets are content-hashed before copying.

Private Windows runtime installed torch 2.8.0+cu128 (official PyTorch wheel; CUDA runtime12.8); imports verified alongside numpy2.1.3/scipy1.14.1/h5py3.12.1. This import check uses no GPU compute. Initial PowerShell pipeline aborted on pip's script-PATH warning; repeat used `--no-warn-script-location` and succeeded. Environment preparation is not a scientific run or GPU admission.

Design review: https://chatgpt.com/c/6ac2e1ce-9940-83ed-a562-b17182126205 (pending). No thresholds or optimization admitted by the draft.

## S04-E002-R001 environment probe

Tooling-only Condor admission, independent of the pending scientific protocol: request1GPU/8CPU/32GB RAM/20GB scratch. Fail unless the machine ad assigns exactly one GPU UUID, expose only that UUID before importing torch, verify device identity, run an analytic three-value CUDA autograd check and the existing twelve native-Q4/history unit tests. No neural optimization. Success means environment readiness only; it does not admit the subsequent numerical experiment. Output: execution.json, scheduler ads and unit_tests.txt.
