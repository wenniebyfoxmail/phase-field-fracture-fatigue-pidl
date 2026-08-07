# LTPP 06-1253 MON_DIS Acquisition and Timeline Contract

## Purpose

Freeze the official section-scoped `MON_DIS*` records and build an auditable
event ledger before comparing official distress quantities with the exploratory
single-annotator vectors.

## Source and scope

- Source: FHWA LTPP InfoPave SDR 39 public Table Export interface.
- Section filter: State `06`, SHRP ID `1253`, internal LDW section ID `2056`.
- Tables: every table exposed by the official Table Export page whose name starts
  with `MON_DIS`.
- Timeline: the already frozen official `GetTimelineData` response.

The acquisition must fail if the official page exposes no `MON_DIS` tables, more
than 60 matching tables, a row escapes the section filter, or a server row count
does not match the deduplicated frozen rows.

## Evidence boundary

- Raw official records are external quality-control inputs, not pixel or vector
  ground truth.
- Official quantity totals and our vector geometry may use different survey
  rules, units, extents, and revision statuses; no direct equality is assumed.
- The primary single-annotator labels remain unchanged.
- The official timeline exposes no maintenance or rehabilitation event for this
  section, but absence in the viewer is not proof that unrecorded work did not
  occur.
- The section is marked Out-of-Study on 2011-06-01. Later map dates must be
  explicitly flagged as post-monitoring geometry.

## Authorized next gate

After acquisition, identify the manual asphalt distress tables and predeclare a
date/type/severity/unit aggregation before comparing their quantities with the
vectorized lengths and areas.
