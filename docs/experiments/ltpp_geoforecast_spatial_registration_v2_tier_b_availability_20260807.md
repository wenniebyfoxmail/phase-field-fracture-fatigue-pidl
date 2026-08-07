# LTPP spatial-registration v2 Tier B availability work

## Authorization

`APPROVE_V2_AVAILABILITY_DIAGNOSTIC_ONLY`

External re-review approved only independent Tier A/B control collection and
adjudication. It does not authorize transform tuning, final-control disclosure,
the one-shot final v2 gate, or 2-D crack-model training.

## PIDL Experiment Gate

- **Mechanism question:** Do all eight maps contain the independently observed
  printed-grid controls required for a credible v2 audit?
- **Claim changed if success:** A frozen fit/development/final control packet
  can be prepared for a separately authorized registration implementation.
- **Claim changed if failure:** `INSUFFICIENT_INDEPENDENT_CONTROLS__NO_2D_MODEL`.
- **Cheaper diagnostic first:** Historical v1 candidate inventory, completed
  without transform fitting.
- **Minimal output asset:** Dual blind packets, custodian consensus receipt,
  and availability summary.
- **Code/producer alignment:** Offline Mac packet preparation only; no PIDL,
  FEM, training, or registration transform.
- **Success criteria:** Every date has all eight development and eight final
  candidates eligible, plus at least eight non-collinear fit controls.
- **Failure criteria:** Any missing/ambiguous required candidate, insufficient
  fit controls, or broken final-control blinding.
- **Registry destination:** This experiment document and the spatial
  registration track; research frontier only if the active 2-D route changes.
- **Decision:** Prepare blind packets; do not run consensus until both human
  annotation roles are locked.

## Packet roles

`annotator_a` and `annotator_b` receive separately permuted, date-coded source
image packets. The sealed mapping and final-role information are stored only in
`custodian_sealed_do_not_open/`. The implementer must not inspect that folder
or any final-control coordinate after generation.

## Custodian commands

Prepare packet once:

```bash
/Users/wenxiaofang/miniconda3/bin/python3 scripts/ltpp_prepare_spatial_registration_v2_annotation_packets.py \
  --grid-results /absolute/path/grid_gate_results.json \
  --protocol docs/experiments/ltpp_geoforecast_spatial_registration_v2_tier_b_annotation_protocol_20260807.md \
  --output-root /absolute/new/packet-root
```

Run one role at a time on separate browser sessions:

```bash
/Users/wenxiaofang/miniconda3/bin/python3 scripts/ltpp_registration_control_annotator_server.py \
  --packet-root /absolute/packet-root --role annotator_a --port 8770
```

Only after both roles lock all eight maps, the custodian runs:

```bash
/Users/wenxiaofang/miniconda3/bin/python3 scripts/ltpp_consensus_spatial_registration_v2_controls.py \
  --packet-root /absolute/packet-root --output /absolute/new/custodian-consensus-root
```
