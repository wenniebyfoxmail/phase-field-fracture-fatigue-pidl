# LTPP spatial-registration v2 owner-carrier Tier B packet result — 2026-08-11

## Decision

`PENDING_EXTERNAL_REVIEW__DO_NOT_ANNOTATE`

The replacement blind-packet engineering loop completed, but control
collection has not begun. This does not alter v1
`SPATIAL_REGISTRATION_NOT_QUALIFIED__NO_2D_MODEL` and does not establish that
independent controls are available.

## Diagnosis closed by this packet

The historical A/B packet was generated from obsolete automatically detected
`grid_results` crop bounds. It cannot validate the newer eight-date carrier
constructed from the official 0–50 ft source maps and the owner-accepted outer
frames. The historical packet and its empty records remain untouched.

The replacement review candidate uses the same original official-map pixels
as the accepted carrier packet. Its only new operation is the frozen
axis-aligned four-corner bounding box plus 48-source-pixel margin. It performs
no rectification, enhancement, grid detection, control extraction, transform
fitting, or cross-date comparison.

## Immutable review candidate

Path:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_06_1253_spatial_registration_v2_owner_carrier_tier_b_review_candidate_v2_20260811/`

| Receipt | SHA-256 |
|---|---|
| `public_packet_manifest.sha256` | `85938bcb21fad50f8f636970637e0ea86a510068da00448a1ac4c7a792c52ff9` |
| `packet_status.json` | `50d282c95a62dea0e8b29b2515b697da1d2090260aa0fdfaf35dc25889e2a492` |
| packet builder | `044be72f36e380a2c26568f9df255a434e00ff144eb29992fe7f535440056bb1` |
| builder tests | `0cff8d55ef6113a852c2b67754beb6d4564c799d9ab1000a9af4457468281d52` |
| amendment | `f965ac01dbec5e09d9889a42a4a964d4794106b6c8aeda6ef1a24f706ae574be` |
| review-bundle receipt | `71139c9071dd722616ea72cfa0e12a8fe73a8a4764af192d0bf9cd3b2fe9ae69` |

The public manifest verified all 35 entries. The packet contains 8 blinded
images and 8 records per annotator. All 16 records are unlocked, and all
1,056 candidate task statuses are null. The sealed date/role mapping was not
opened during verification.

The first path without the `_v2_` suffix is retained as a pre-review
superseded candidate. A whitespace-only EOF normalization changed the frozen
amendment/test/request hashes before commit, so no annotation was allowed and
a new non-overwriting packet was generated. Only the `_v2_` path above is the
review candidate.

## Tests

The packet-specific and existing Tier B annotation/consensus tests passed:

`7 passed`

They check the unchanged 66-point role partition, deterministic half-open crop
bounds and clipping, empty/unlocked HOLD records, malformed-point rejection,
and the existing two-click consensus rule.

The broader LTPP suite passed `89 passed, 2 skipped` after excluding exactly
`test_ltpp_enriched_oracle.py` and `test_ltpp_enriched_posterior.py`; those two
unrelated modules cannot be collected in the current Mac environment because
the optional `arviz` dependency is absent.

## Next gate

An independent reviewer must return
`APPROVE_OWNER_CARRIER_TIER_B_COLLECTION_ONLY` before either annotation role
opens the packet. If approved, two eligible humans—not the user or
implementer—independently annotate their blinded role. Only after both roles
lock may the custodian run mechanical consensus and report whether every date
has all required development/final points and at least eight non-collinear fit
points.

No registration model is optimized at this stage, and the final gate remains
closed.
