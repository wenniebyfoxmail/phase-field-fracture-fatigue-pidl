# LTPP spatial-registration v2 owner-carrier packet external review — 2026-08-11

## Verdict

`APPROVE_OWNER_CARRIER_TIER_B_COLLECTION_ONLY`

`Blocking issues: none.`

## Review provenance

The frozen request, amendment, execution-state summary, and SHA-256 receipt
were submitted to the same external-method review conversation used for the
earlier protocol reviews:

- conversation: `协议复审流程`
- conversation ID: `6a759e9b-8964-83eb-b97c-224a53f29e30`
- URL: `https://chatgpt.com/c/6a759e9b-8964-83eb-b97c-224a53f29e30`
- submitted amendment SHA-256:
  `f965ac01dbec5e09d9889a42a4a964d4794106b6c8aeda6ef1a24f706ae574be`
- submitted review-bundle receipt SHA-256:
  `71139c9071dd722616ea72cfa0e12a8fe73a8a4764af192d0bf9cd3b2fe9ae69`

The reviewer was asked to return only
`APPROVE_OWNER_CARRIER_TIER_B_COLLECTION_ONLY` or
`REVISE_OWNER_CARRIER_PACKET_BEFORE_COLLECTION` and to identify any blocking
issue.

## Reviewer findings

The reviewer found that the unique axis-aligned bounding box, fixed
48-source-pixel margin, explicit `floor/ceil/+1` bounds, source clipping, and
half-open slicing remove per-page crop discretion. The unrectified crop is
only an evidence window; crop clicks return to source coordinates by adding
the sealed integer origin.

The reviewer also found the owner corners sufficiently isolated from Tier B
audit controls: owner corners only choose the packet window and are not fit,
development, or final controls and cannot produce residuals. The 66 frozen
`G[i,j]` candidates and the original two-person blind Tier B protocol remain
the only audit-control route.

The reported pre-approval state—16 unlocked records, 1,056 null task statuses,
sealed mapping unopened, public manifest 35/35 verified, no consensus,
transform, residual, or final gate—was accepted as consistent with the stop
condition. These checks were not interpreted as registration-performance
evidence.

## Authorization boundary

The immutable `_review_candidate_v2_20260811` packet may now be released to
two people who satisfy the original independent-annotator eligibility rules.
After both roles are complete and locked, the custodian may run only the
already frozen mechanical Tier B availability consensus.

This approval does **not** authorize transform fitting or tuning, registration
residual evaluation, final-control disclosure, the one-shot final v2 gate, or
any 2-D model. Missing required controls must trigger the existing fail-closed
termination; they may not trigger packet changes, control replacement, or a
more flexible registration method.
