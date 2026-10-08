---
storyline_id: S09
experiment_id: S09-E002
protocol_revision: v1-damage-only-ablation
status: closed
scientific_verdict: negative
---
# Damage-only supervised ablation

Purpose: test whether removing history/driver supervision permits bounded damage fitting in the same P1 setup. Synthetic processed-archive diagnostic, not a causal gradient-competition or predictive claim.

Single intervention: weights [1,0,0] on both raw and state channel losses, still mean over original3 outputs. Damage coefficient remains1/3. Do not change architecture, initialization, seed1, full17 inputs, output3, graph, optimizer/lr/weightdecay/clipping,16windows, budget1000, assess every50, first-pass stop, or area-weighted metric. Start fresh, not R002 checkpoint. Same config fields except experiment/protocol identity and explicit loss weights. Unsupervised history/driver outputs are not usable forecasts; P2 prohibited.

Reference: S09-E001 R002 joint supervision, exact codef58df2d, same16 windows, best0.9979861337183021 after up to1000updates. Data manifest/graph hashes remain configs/s09_e001.json values; new config configs/s09_e002.json. No old-model predictions used as labels; no test data.

Primary criterion: identical full-domain area-weighted damage increment MAE/persistence <=0.8, ratio of summed errors to summed true growth for16windows; rationale20% diagnostic in-sample margin. PASS supports this loss intervention permits fitting under this setup; FAIL means this intervention alone did not meet target. No claim of generalization, physics, or proof of gradient competition. Secondary difference vs priorbest descriptive only; cannot rescue FAIL.

Validity/stop: same locked source data, training statistics, window selection, bounds/finiteness, exact reviewed commit. Stop first passing assessed checkpoint or1000, invalid data/nonfinite -> execution failure. Missing growth -> not evaluable.

Producer Taobo GPUServer8, GPU0 if healthy capacity; fraction.33, no bytecode; fresh run. Evidence: receipt, config, data capability/windowCSV, history, initial/best/latest metrics,checkpoint, independent review, retrieval verification. No automatic P2/PINO or added budget. Code Ready pending exact commit.

## Execution result 2026-10-08

R001 completed1000 updates, best0.9900616084495109 at850, criterion<=0.8 not met. Execution succeeded; bounded fit negative. See decision_20261008.md. Independent evidence review PASS and retrieval verified; closed as bounded negative. No automatic additional run.
