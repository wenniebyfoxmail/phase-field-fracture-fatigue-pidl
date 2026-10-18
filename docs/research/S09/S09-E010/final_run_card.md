---
experiment_id: S09-E010
planned_run_id: S09-E010-R001-support-amplitude-three-arm
status: CODE_READY_AWAITING_EXECUTION
producer: Taobo GPU
forbidden_fallback: CSD3
---

# S09-E010 final run card

## Scientific action

Run the one frozen development-only three-arm comparison on the already qualified S09-E008 packet. The learned operator maps

`(d_s00(x), [H, alpha_bar, q_prev, f]_s00(x_gp), full prescribed load path, fixed mesh/material/boundary)`
`-> (d_s04(x), state_s04(x_gp), u_s04(x))`.

The three arms are `A25_exact_e009_replay`, `B25_balanced_beta0p25`, and `B0_balanced_beta0`. Each starts from a byte-identical model copy and empty AdamW state, receives exactly 500 updates with no budget transfer, and is evaluated at updates 0, 16, 64, 128, 256, 496, and 500.

The PINO physics term is the native-Q4 AMOR mechanical-equilibrium residual on free displacement degrees of freedom at the predicted peak state. It does not enforce damage stationarity, fatigue evolution, or all within-cycle load steps.

## Frozen identities

| Item | Identity |
|---|---|
| Producer package reviewed commit | `010281be8045301f7e56b938de82969982c89bc9` |
| Runner integration review commit | `51835e1626e536b2079adb4e1b878da7256a46c0` |
| Runner integration config SHA256 | `ecdfc678c5a71e3a44a1a05665466cf0d717b76e6790e2bb2dc6acb7af6f8e70` |
| Protocol contract SHA256 | `c8f20e9d129bc603dfea0621bc25f7bdd0aba157be3c7c46ecd62816a9a2d2fa` |
| Base E008 config SHA256 | `0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b` |
| Input packet manifest SHA256 | `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6` |
| Frozen E009 A25 replay reference SHA256 | `4bdfd493195ee0c77a0fe0af2280d2b23905c3da832785cdfddf19d0c3691bc7` |

## Fixed producer paths

```text
run root:     /mnt/data2/drtao/wennie/S09-E010-R001-support-amplitude-three-arm
archive root: /mnt/data2/drtao/pidl_archives/S09-E010-R001-support-amplitude-three-arm
staging root: /mnt/data2/drtao/wennie/s09-e010-config-staging
```

All three roots must be fresh at launch. CSD3 and all unlisted machines are forbidden fallbacks.

## Final resolver

```bash
python scripts/resolve_s09_e010_producer_config.py \
  --packet-dir "$PACKET_DIR" \
  --integration-config docs/research/S09/S09-E010/runner_integration_config_20261018.json \
  --base-config docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json \
  --protocol docs/research/S09/S09-E010/experiment.md \
  --output-config /mnt/data2/drtao/wennie/s09-e010-config-staging/config_resolved.json \
  --approved-producer-commit 010281be8045301f7e56b938de82969982c89bc9 \
  --approved-hostname "$APPROVED_HOSTNAME" \
  --approved-gpu-name "$APPROVED_GPU_NAME" \
  --approved-gpu-uuid "$APPROVED_GPU_UUID" \
  --approved-gpu-pci-bus-id "$APPROVED_GPU_PCI_BUS_ID" \
  --approved-staging-root /mnt/data2/drtao/wennie/s09-e010-config-staging \
  --authorize-reviewed-run \
  --resolve-reviewed-config
```

Record the resolved config SHA256. Any identity or environment mismatch stops before an optimiser or run root is created.

## One authorised launch

```bash
CUDA_VISIBLE_DEVICES="$APPROVED_VISIBLE_GPU" \
python scripts/run_s09_e010_producer.py \
  --packet-dir "$PACKET_DIR" \
  --resolved-config /mnt/data2/drtao/wennie/s09-e010-config-staging/config_resolved.json \
  --base-config docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json \
  --output-dir /mnt/data2/drtao/wennie/S09-E010-R001-support-amplitude-three-arm \
  --execute-reviewed-run
```

Launch detached with a task-specific PID and log. Record hostname, commit, clean execution-file state, GPU index/name/UUID/PCI id, start time, command, PID, cwd, run/archive/log paths, and resolved-config hash.

## Fail-stop and evidence rules

- Any `EXECUTION_FAILED` arm, identity drift, nonfinite value, hard-constraint violation, unreadable or hash-drifting required artifact, or completed-A25 exact-replay mismatch stops the run globally.
- A25 `METHOD_INAPPLICABLE` is arm-local only when all four frozen start-identity clauses pass. It permits B25 and B0 to finish their own fixed budgets, but the final scientific status remains `METHOD_INAPPLICABLE` with no performance classification.
- Shared/start identity failure always precedes method status and is `EXECUTION_INVALID`.
- Every completed arm must contain 500 updates, 500 complete train rows, 500 gradient rows, all seven evaluations, and the update-500 checkpoint.
- Do not retry automatically. Preserve the first stopped, failed, method-inapplicable, or completed result.

## Frozen decision

The primary B25-versus-A25 criterion is an integer AUC pair-score gain of at least 4, equivalent to `Delta_AUC >= 0.08`. A balanced local repair additionally requires B25/A25 protected ratios `G<=1.05`, `F<=1.05`, `L_P<=1.10`, and `L_judge<=1.05`. B25-versus-B0 is conditional physics attribution only and cannot rescue the primary comparison.

## Execution record — 2026-10-19 Taobo local time

The single approved run was executed once from reviewed commit
`010281be8045301f7e56b938de82969982c89bc9` on `GPUServer8`, physical GPU UUID
`GPU-ea68e432-5acb-5488-5be1-4ba9a2053beb`. All three arms completed 500
updates. Exact A25 replay and shared identity passed; all outputs were finite
and all hard-constraint counts were zero. The completion receipt SHA256 is
`a5e104e0ec401a8fcbd3d1416f1ab86a85353957ed8e4bd47d90143b458d9be4`.

The frozen outcome is `NO_TARGETED_RANKING_SIGNAL`: `A25` and `B25` both had
AUC 0.68 and pair score 34, giving delta 0 rather than the required 4. All
protected ratios passed. No retry was launched. Full interpretation and field
evidence are in `run_analysis_20261019.md` and `results/`.

Any positive result supports only a next bounded development test. It does not establish rollout, generalisation, FEM truth, full fracture-evolution PINO performance, or real-road validity.
