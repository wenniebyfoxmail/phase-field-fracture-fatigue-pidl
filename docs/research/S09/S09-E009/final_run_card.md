---
experiment_id: S09-E009
planned_run_id: S09-E009-R001-four-arm-damage-separation
status: PREPARED_FOR_EXACT_PRODUCER_PACKAGE_REVIEW__NO_EXECUTION
producer: Taobo GPU
forbidden_fallback: CSD3
---

# S09-E009 final run card

## Scientific action

Run the one frozen development-only comparison on the qualified S09-E008
packet. The mapping is

`(d_s00, [H, alpha_bar, q_prev, f]_s00, full prescribed path, mesh/material/boundary)`
`-> (d_s04, history_s04, u_s04)`.

The four arms are `R_current_pino_replay`, `S_data_only_scalar`,
`A0_damage_anchor_beta0`, and `A25_damage_anchor_beta0p25`. Each arm has its
own byte-identical model copy and empty AdamW state, exactly 500 updates, no
budget transfer, and evaluations at updates 0, 16, 64, 128, 256, 496, and 500.

## Frozen identities

| Item | Identity |
|---|---|
| Core review commit | `8b6a2e49b241ae73f433645cb30a69291f7aee53` |
| Runner integration review commit | `efeffbfae4395f95228c56e3f530e323f1ab8f6a` |
| Runner integration config SHA256 | `7994c8959ae5fc3adaa2b4037ba7be2619ddb28fccb00a9663a8a42009a283fd` |
| Protocol contract SHA256 | `92e9dfdcd70bf886a0b9f9dd416c9dc123ef75cd999056c4bed44b5bc05fa26f` |
| Base E008 config SHA256 | `0cf59c58dfed34b8e333bffde6ca276623c71f45adf787a6f7879498bb088e4b` |
| Input packet manifest SHA256 | `1658d2a2acc67c279b06e3e7965186bc1616aec50d6ee05179ff2606160272a6` |
| E008 replay first-500 gradient rows SHA256 | `50c746b8f6548f53493c6556b7f7281a4b97d2340c35aad5e9d63c87f9bddfe9` |
| Producer package reviewed commit | `TO_BE_FILLED_ONLY_AFTER_EXACT_COMMIT_PASS` |

## Fixed producer paths

```text
run root:     /mnt/data2/drtao/wennie/S09-E009-R001-four-arm-damage-separation
archive root: /mnt/data2/drtao/pidl_archives/S09-E009-R001-four-arm-damage-separation
staging root: /mnt/data2/drtao/wennie/s09-e009-config-staging
```

Both run and archive roots must be absent before launch. Do not reuse a partial
directory. Do not fall back to CSD3 or write run data under `/`, `/tmp`, or the
shared home directory.

## Final preflight and resolver

The later execution turn must first capture hostname, physical GPU UUID, PCI
bus id, GPU name, `CUDA_VISIBLE_DEVICES`, free space on `/mnt/data2`, current
commit, and tracked execution-file cleanliness. Those observed values are
passed to the resolver below. The resolver performs no optimiser step.

```bash
python scripts/resolve_s09_e009_producer_config.py \
  --packet-dir "$PACKET_DIR" \
  --integration-config docs/research/S09/S09-E009/runner_integration_config_20261017.json \
  --base-config docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json \
  --protocol docs/research/S09/S09-E009/experiment.md \
  --output-config /mnt/data2/drtao/wennie/s09-e009-config-staging/config_resolved.json \
  --approved-producer-commit "$PRODUCER_PACKAGE_REVIEWED_COMMIT" \
  --approved-hostname "$APPROVED_HOSTNAME" \
  --approved-gpu-name "$APPROVED_GPU_NAME" \
  --approved-gpu-uuid "$APPROVED_GPU_UUID" \
  --approved-gpu-pci-bus-id "$APPROVED_GPU_PCI_BUS_ID" \
  --approved-staging-root /mnt/data2/drtao/wennie/s09-e009-config-staging \
  --authorize-reviewed-run \
  --resolve-reviewed-config
```

The exact resolved JSON and its SHA256 must be retained in the execution
receipt. If any identity or environment field differs, stop before creating an
optimizer or run root.

## One authorised launch command

```bash
CUDA_VISIBLE_DEVICES="$APPROVED_VISIBLE_GPU" \
python scripts/run_s09_e009_producer.py \
  --packet-dir "$PACKET_DIR" \
  --resolved-config /mnt/data2/drtao/wennie/s09-e009-config-staging/config_resolved.json \
  --base-config docs/research/S09/S09-E008/p1_memorisation_run_config_20261016.json \
  --output-dir /mnt/data2/drtao/wennie/S09-E009-R001-four-arm-damage-separation \
  --execute-reviewed-run
```

Launch detached with a task-specific log only after the exact producer package
has passed review and the final execution action is authorised. Record command,
PID, cwd, commit, GPU identity, start time, log path, run root, archive root and
resolved-config SHA256. Never use broad process-kill commands on the shared
account.

## Fail-stop and evidence rules

- Run `R` first. Its update-0/update-500 numeric replay is the fail-stop gate;
  if that gate fails, stop before the other arms and mark cross-arm performance
  inadmissible. Report the new first-500 legacy gradient-log hash against the
  archived qualified reference as a diagnostic; a hash mismatch alone does not
  fail an otherwise numerically valid replay.
- An anchor norm at or below `1e-12` is `METHOD_INAPPLICABLE`, with its exact
  stop location and partial evidence. It is not an execution failure.
- Any nonfinite value, layout/order mismatch, incomplete gradient assignment,
  hard-constraint violation, identity drift or undeclared artifact state is
  `EXECUTION_FAILED`.
- A completed arm must contain exactly 500 optimiser steps, 500 complete train
  and gradient rows, all seven evaluation points, and its update-500 checkpoint.
- Every arm must write its conditional termination receipt. Shared evidence is
  `config_resolved.json`, packet identity, environment, decision JSON/CSV/PNG,
  per-cycle CSV, decision note and completion receipt.

## Interpretation boundary

Update 500 is the only decision checkpoint. The graded outcome is one of
`EXECUTION_INVALID`, `METHOD_INAPPLICABLE`, `NO_REPAIR_SIGNAL`,
`COMPONENT_SIGNAL_OR_MIXED_TRADEOFF`, `RELATIVE_REPAIR_SIGNAL`, or
`NOMINATE_CONFIRMATORY_P1`. A positive outcome supports only the next bounded
development test. It does not establish rollout, generalisation, FEM truth,
full fracture-evolution PINO performance, or real-road validity.
