# LTPP spatial-registration v2 Tier B blind annotation handoff

## Authorization and boundary

External re-review returned `APPROVE_V2_AVAILABILITY_DIAGNOSTIC_ONLY`.
This handoff authorizes independent printed-grid control collection only. It
does not authorize registration fitting, disclosure of final controls, final
audit, or 2-D crack modelling.

## Who does what

| Role | May access | Must not access |
|---|---|---|
| Annotator A | `annotator_a/` only | `annotator_b/`, custodian folder, v1 output, dates, other maps, crack outcomes |
| Annotator B | `annotator_b/` only | `annotator_a/`, custodian folder, v1 output, dates, other maps, crack outcomes |
| Custodian | Both completed roles and sealed mapping | Registration fitting or final-control disclosure to implementer |
| Implementer | Code, protocol, public packet manifest | Any sealed mapping or post-annotation final-control coordinate |

The original user and current implementer have seen v1 results, so neither can
serve as a final-control annotator.

## Packet

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_spatial_registration_v2_tier_b_packets_20260807`

The public manifest and sealed manifest have been verified. The sealed mapping
must remain unopened until the protocol's consensus step.

## Annotator A launch

```bash
/Users/wenxiaofang/miniconda3/bin/python3 \
  "/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_registration_control_annotator_server.py" \
  --packet-root "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_spatial_registration_v2_tier_b_packets_20260807" \
  --role annotator_a --host 127.0.0.1 --port 8770
```

Annotator B uses `--role annotator_b --port 8771` in a separate browser
session. Each annotator locks a map only after all 66 candidates have one of
the frozen statuses. No task may be reopened after lock.

## Custodian action after both passes lock

```bash
/Users/wenxiaofang/miniconda3/bin/python3 \
  "/Users/wenxiaofang/phase-field-fracture-with-pidl/upload code/scripts/ltpp_consensus_spatial_registration_v2_controls.py" \
  --packet-root "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_spatial_registration_v2_tier_b_packets_20260807" \
  --output "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_spatial_registration_v2_tier_b_consensus_20260807"
```

The custodian shares only the availability summary and stops immediately at
any `INSUFFICIENT_INDEPENDENT_CONTROLS__NO_2D_MODEL` condition. Do not share
final-control coordinates with the implementer.
