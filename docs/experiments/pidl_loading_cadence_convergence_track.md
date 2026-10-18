# PIDL loading-cadence convergence track

Status: `PRE-LAUNCH / NO RUN AUTHORIZED`  
Owner: Mac audit/design; any future producer is Taobo only  
Canonical decision package: `$PROJECT/local_archive/after_strict_setting_alignment/pidl_result/loading_cadence_convergence_gate_20260819/analysis/`

## Mechanism question

Does the locked hard-recovery PIDL trajectory approach a stable event, response, topology, and internal-field path when the retained states on one R=0 triangular displacement history are refined?

## Current evidence

- Hard5 `[.03,.06,.09,.12,0]`: first hit c89/step444.
- Hard8 absolute displacement `[.03,.06,.09,.12,.09,.06,.03,0]`: first hit c115/step916.
- The old normalized-interface hard8 attempt is `do-not-cite`.
- Hard5 -> hard8 is an unload-branch refinement, not a complete convergence sequence.
- At c60 the two retained trajectories already differ materially: damage MAE `0.018206`, active log10 MAE `0.194877`, damage IoU about `0.66-0.72`.
- Legacy confirmation counts raw substeps, not physical cycles.
- No compatible local 12/16 archive was found; remote Taobo status is unconfirmed after SSH timeout.
- Actual current SENS FEM/PIDL BC is bottom `ux=uy=0`, top `ux=0, uy=U`; the separate bottom-left-pin SENT family does not apply.

## Claim boundary

Current evidence supports strong cadence sensitivity only. It does not support a cadence-independent event, field mechanism, inverse result, teacher/corpus claim, physical validation, or real-road prediction.

## Active gate

Use a formal symmetric nested S4/S8/S16 triangular schedule, retain hard5 as a legacy unload-jump stress test, and add S32 only if the first three levels do not enter an asymptotic regime. Stage c3 semantics, seed1 c60, seed1 c120, then paired seeds. Separate raw first hit from connected peak confirmation and compare same-cycle, last-common-pre-event, and own-event states.

Full thresholds, assets, cost, and blockers are in `analysis/experiment_gate.md` in the canonical decision package.

## Next action

User approval is required for a Taobo **tooling smoke only** after external planning advice, attempt-ledger validation, remote archive recensus, and runner/export review. No production run is authorized.
