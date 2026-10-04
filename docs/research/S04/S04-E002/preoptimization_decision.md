# S04-E002 pre-optimization diagnostic

Status: input identity and target/history overlap measured; new supervised or polish training NOT launched.

Canonical recovery offset maps c83 peak to step414, preceded by step413 at0.08999988. The old step412-to-peak matrix is a skipped-substep counterfactual. FEM/PIDL mesh signatures exactly match.

FEM c83 damage is lower than the projected accepted PIDL413 damage at some GP locations. Positive-part previous-minus-target gap: maximum0.30220191498735444, area RMS0.02624947705585787, area mean0.004395031326867521; node maximum0.3057798044384788. The positive-area fraction0.042498980102569486 uses zero tolerance and is descriptive only.

This directly establishes conflict between exact FEM-target reproduction and strict no-healing relative to this PIDL history; it does not quantify the response of a soft-penalty optimizer or prove network incapacity. Do not attribute future polish departure solely to optimizer or architecture without cross-residual and history compatibility controls.

Independent Pro design requests were sent at https://chatgpt.com/c/6ac2e1ce-9940-83ed-a562-b17182126205. Only interim reasoning was visible so far; no final DESIGN PASS is recorded. Protocol remains draft.

Reproduction: scripts/censor_projection_diagnostic/audit_inputs.py and target_history_overlap.py; input fingerprints in ../inputs/manifest.json. These are lightweight read-only array analyses; no Mac training.

Environment: R002/Condor57 passed CUDA identity/autograd,12unit tests and scheduler exit0 after process-local WMI fallback; R001 failure remains archived. This is tooling-only and does not admit supervised training.
