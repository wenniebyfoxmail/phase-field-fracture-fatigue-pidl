---
storyline_id: S04
experiment_id: S04-E001
protocol_revision: reproduction-v1
status: ready
primary_storyline: S04
scientific_verdict: pending
---
# Reproduce archived native-Q4 diagnostics on Windows Condor

## Question and scope
Do unchanged archived Q4 replay, field-region attribution, GP cross-swaps, bounded-alpha counterfactual and fixed-damage equilibrium reproduce on a second environment? This is a migration-on-touch of deterministic diagnostic evidence, not a new training design.

## Reuse and frozen protocol
- Source base: ff42cb9, clean snapshot from codex/hard5-native-mesh-pidl-20260929.
- Archive scripts: hard5_native_q4_production_20260929/analysis/followup_diagnostics_20261003/{run_region_energy_attribution.py,run_gp_crossswap_equilibrium.py}, copied unchanged.
- Data: FEM Hard5 native-Q4 exact-peak v2.1 c76/c82/c83; PIDL native-Q4 production aaf13fd, steps379/409/414/424.
- Original archived results are retained. Wrapper only changes runtime paths and logging; CPU-only numerical kernels unchanged.
- Primary numerical gate: existing audit_native_q4_operator.py checks and thresholds, unchanged.
- Remaining metrics remain diagnostics without a new performance threshold. Compare against historical values and explicitly report numerical drift.
- Stop on replay failure, missing input, nonfinite values or failed reconstruction; do not claim PINN expression/trajectory closure.
- Mac validation: 12 Q4/history tests passed, 2026-10-04. No local training.

## Review boundary
Existing native-Q4 plan review is inherited for context. This run repeats unchanged deterministic diagnostics under the project skill's rerun exception; no new scientific criterion or method is approved here. Independent review of any new interpretation or promotion remains pending. Mechanical replication is not Evidence Ready promotion.

## Runs
| Run | Purpose | Execution | Retrieval |
|---|---|---|---|
| S04-E001-R001 | CPU deterministic replay/cross-swap/equilibration on gpu-server | prepared | pending |

## Assets
Local: /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E001/runs/S04-E001-R001/
Remote: C:/Users/xw436/jobs/censor_diag_20261004_r001/
Wrapper: scripts/censor_diagnostic_reproduction/
User-authorized host: gpu-server; ad\xw436; Condor 8 CPUs/32GB/0 GPUs. No remote service or shared environment change.

## Claim impact
Pending numerical reproduction. No new PINN fitting, fatigue rollout, architecture sweep or broad producer authorization.
