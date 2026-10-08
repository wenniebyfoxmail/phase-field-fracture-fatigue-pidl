---
storyline_id: S09
experiment_id: S09-SIDE-DIAG-20261008
protocol_revision: v1-cause-isolation-candidate
status: prepared_pending_independent_review
---
# Side conversation: bounded cause-isolation diagnostics

Purpose: check candidate explanations for E002 damage-only in-sample failure. Synthetic processed-archive C0/C1 diagnostics; not physics or held-out prediction. Parent-thread code/workspace and historical FAILs remain untouched.

Evidence: exact E002 config/data locks, two training trajectories U011/U013,16 frozen P1 windows, seed1, full three-state input, damage-only output supervision, original /3 coefficient. No warm start; no development/test scoring. Same area-weighted full-domain damage MAE ratio versus persistence. Target <=0.8 remains engineering fit target, not physical tolerance.

## Completed read-only audit (exploratory, separate from training arms)

Compute persistence and constrained secant from admitted current/previous damage only; inspect training target scale and area support. No fitted coefficients and no future input. Record baseline results, do not promote to independent forecast validation. Inspecting these results is not a new training run.

## Frozen proposed checks

| Arm | Single intervention vs E002 | Maximum updates | What it can answer |
|---|---|---:|---|
| single_window | train/evaluate only central selected list member index8, U011 origin95 |1000| Can this model fit this one window? Not a data-volume/generalization test; exposure increases |
| scale_x10 | damage increment scale multiplied10 in raw target and output decode |1000| Sensitivity to increment parameterization/optimization scale, not proof of unique causal defect |
| balanced_support | training loss assigns half mass to target delta_d>1e-7 region and half background, then original /3 |1000| Whether training emphasis on sparse growth helps; labels only in loss, never inputs or evaluation |
| lr_x10 | AdamW lr3e-4 ->3e-3 |1000| Sensitivity to this higher LR only |
| budget_x5 | same seed/init/lr, max1000 ->5000 updates |5000| Whether larger budget is sufficient; fresh run and first-pass stopping |
| width_x2 | hidden width64 ->128, rank8/radius/coarse bins unchanged |1000| Sensitivity to width; tensor dimensions change so identical initial weights are impossible |

All16 evaluation windows remain for every arm except single_window. Radius and kernel rank are not changed in width arm. Window labels are already observed; these are explicitly post-hoc follow-up hypotheses, not blind confirmatory tests. No result may rescue E001/E002 original FAIL.

## Execution and stops

Independent exact-code/data/protocol review required before producer. Sequential fresh runs on Taobo GPUServer8 only; explicitCUDA, .33 memory fraction, no bytecode, fresh attributable directories. Each run assesses every50 updates, stops first ratio<=.8 or budget; nonfinite/error stops that run. No automatic extra arms beyond table, no search for best seed. Each arm receives its own verdict; 'any arm passes' is not an overall scientific success gate. Each exact checkpoint/history/metrics/receipt is retrieved and checked. Findings beyond simple capability require independent evidence review.

Prefer one-window check first. If it exposes invalid state identity/nonfinite implementation, stop remaining arms for repair. If it merely fails the fitting target, remaining candidate checks stay interpretable and may proceed after review. Stop remote work on resource shortage rather than kill shared processes.

## Outcome map and blocked conclusions

validity failure -> inadmissible; finite full budget but ratio>.8 -> intervention insufficient; ratio<=.8 -> bounded fit support for named unit/intervention. Auxiliary diagnostics explain only. More budget/width or loss changes do not establish model generalization or causal gradient mechanisms.

Data insufficiency for generalization cannot be settled from two training trajectories and one already-used development trajectory. No synthetic "independent" samples from shuffling windows. A later data learning-curve study needs a fitting configuration and additional independently held-out trajectories; that evidence axis is not available in this package.

Prepared, NOT LAUNCHED. Independent review is pending because side-conversation subagents are prohibited. An external reviewer must be explicitly authorized here or the package returned to the main thread by the human.
