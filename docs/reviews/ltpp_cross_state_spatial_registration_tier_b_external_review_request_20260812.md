# External review request: cross-state Tier B collection extension

## Requested scope

Review only the frozen collection-window amendment for `27-6251 c3` and
`08-1053 c2` and the HOLD-only packet builder. No annotations, consensus,
transform, residual, or registration result exist.

## Unchanged protocol

The 66-point universe, fixed fit/development/final roles, two-person blind rule,
4.0-source-pixel consensus limit, physical coordinates, missingness rules,
model ladder, error thresholds, and one-shot termination remain unchanged.

## Exact change

Each all-date-pass source map is copied without rectification into a blind
evidence crop formed by the frozen automatic grid rectangle plus a fixed
48-source-pixel margin. The automatic rectangle is used only for packet
windowing and is prohibited from becoming a control or residual.

## Blocking questions

1. Is this construction-only use of a previously frozen automatic rectangle
   sufficiently isolated from the independent Tier B controls?
2. Does the deterministic crop and hash boundary preserve source-pixel
   coordinates and prevent per-date discretion?
3. If every record is verified empty and unlocked, may the immutable packet be
   released to two eligible annotators for collection only?

## Allowed decisions

- `APPROVE_CROSS_STATE_TIER_B_COLLECTION_ONLY`
- `REVISE_CROSS_STATE_PACKET_BEFORE_COLLECTION`

Approval cannot authorize consensus beyond availability checking, transform
fitting, final-control disclosure, the final gate, or any 2-D model.

## Frozen review candidate

Path:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/real_road_acquisition/ltpp_cross_state_spatial_registration_tier_b_review_candidate_20260812/`

The deterministic build produced 14 blind images and 14 empty records for each
annotator: six Minnesota maps and eight Colorado maps. All 28 records are
unlocked; all 1,848 candidate statuses are null. No annotation, consensus,
transform, residual, or final gate was run. Four sampled packet images were
visually checked: the printed map carrier and its outer frame remain readable;
page-side and handwritten ink remain visible but are explicitly forbidden
evidence under the unchanged occlusion/ambiguity rules.

| Receipt | SHA-256 |
|---|---|
| amendment | `d5cfaf245838cf337d1a0b5f532ce8d43b261916a85cbf971a47e46adc59e078` |
| packet builder | `30a76b3bfaad7292aba524fb9a12c4be6d4dd8fcc0a30412a9e6c7dab8a51fe0` |
| builder tests | `5a2a63ff459d906c44550877cb65d40e387eddcc5969f78ccd1b86837487e8a5` |
| packet status | `adb86849722c2a11d9f7b18a1a209c01cbe2196688f1896298a78da7b5e98e0f` |
| public manifest | `3a186637c93c450d60d5280e1bbba61e248ba7b7fc2cd80909bf14017551c1f5` |
| sealed manifest | `aa6756a60c1032c8f60117fdce2ceaa1c0647ff1ed065773187edade7b083b0e` |

The focused builder suite passed `4 passed`. Both public and sealed manifests
were independently rechecked without mismatch.
