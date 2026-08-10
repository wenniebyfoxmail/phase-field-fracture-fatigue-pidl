# Versioned Physical-Input Projection Design

## Purpose

Close the P0/P0R repeatability gate without changing or regenerating either
experiment package. The legacy package manifests hash the complete
`INPUT_SNAPSHOT.json`, which necessarily differs because `case_id` differs
between `P0_parent` and `P0R_parent_repeat`. That byte-level provenance
difference must remain auditable but must not be treated as a physical or
numerical input difference.

## Immutable evidence boundary

- Preserve every existing P0 and P0R output, manifest, checksum inventory,
  receipt, shard, and log byte-for-byte.
- Do not rerun P0 or P0R.
- Read the two terminal packages through the existing external package
  validator before adjudication.
- Write all new evidence outside both immutable `output` package roots.

## Projection schema

Add `toy_road_physical_input_projection_v1` with the exact canonical payload:

```json
{
  "schema_version": "toy_road_physical_input_projection_v1",
  "case_physics": { "...": "the complete existing case_physics tree" }
}
```

`case_physics` is an allowlisted closed tree containing exactly the declared
`mesh`, `material`, `loading`, `numerics`, `recovery`, and `event` objects.
Every leaf in that tree participates in the hash. Canonical JSON uses sorted
keys, ASCII encoding, compact separators, and a trailing newline; SHA-256 is
computed over those bytes.

The projection intentionally excludes `case_id`, authorization scope, source
commit, runtime and execution-lock identities, filesystem paths, and other
run provenance. Those fields remain in the legacy snapshots and receipts.

## Adjudication

Add an external adjudicator that:

1. independently validates P0 as `P0_parent` and P0R as
   `P0R_parent_repeat` using the existing terminal-package validator;
2. captures and preserves both legacy snapshot and manifest hashes;
3. builds and hashes both versioned physical-input projections;
4. requires the projection hashes to match;
5. applies the existing event, state0, c5, shard identity, and trajectory-field
   repeatability checks without substituting or modifying either package;
6. publishes an exclusive, canonical
   `toy_road_external_repeatability_adjudication_v1` receipt outside the
   package roots.

The receipt status is `PASS` only when terminal validation passes, projection
hashes match, c70/c73 events match, c5 passes for both cases, and every field
metric is within the predeclared thresholds. It separately records that the
legacy full-snapshot hashes differ by provenance serialization.

## Downstream chain

The T1 launch chain may consume the new adjudication receipt after rechecking
its bytes and the immutable package snapshots it binds. It must not accept a
diagnostic-only file or a receipt whose projection schema, status, package
identities, or hashes differ. This change does not authorize T2 or T3 and does
not alter solver, mesh, physics, runtime, MEX binaries, thread settings, or
convergence thresholds.

## Tests

- Changing only `case_id` preserves the v1 projection hash.
- Changing every allowlisted physical/numerical leaf, one at a time, changes
  the v1 projection hash.
- The actual immutable P0 and P0R snapshots produce identical projection
  hashes.
- Existing legacy package validation still passes and existing bytes remain
  unchanged.
- The adjudicator publishes PASS for the actual P0/P0R pair and rejects a
  mismatched projection or changed bound package.

## Failure handling

All new outputs use exclusive creation and fail closed. A failed adjudication
does not modify either package, does not authorize an experiment, and does not
permit automatic retry or downstream launch.
