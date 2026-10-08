# S02-E004 pre-run code review

Date: 2026-10-08

Review type: independent, read-only

Verdict: `PASS` for formal Round A packet execution

## Reviewed identities

- Protocol v1 scientific contract SHA-256:
  `0bdccf0d551232ee263252d3fecbfaa03b1a341fdcab4c1852592bc024b12f50`
- Runner SHA-256:
  `82e6eeb9ef4647efc6be86115eca8455cc506b076ba6aaf0a146f572ec2effcd`

The protocol identity precedes only the administrative transition from `draft`
to `ready` and insertion of this review record. No estimand, selection rule,
metric, threshold, validity gate, or outcome map changed afterward.

## Review history

Round 1 blocked immediate creation of both rounds, reversible public tokens,
mutable input identities, incomplete central-directory validation, missing
cardinality guards, and image metadata leakage.

Round 2 verified most corrections and blocked caller-supplied embargo timing,
publicly reversible hash tokens, mutable sealed selection, and the absence of a
member-level extraction receipt.

Round 3 verified those corrections and blocked nonfinite/out-of-image numeric
entries, incomplete annotation-to-image identity checks, and an undeclared
`0.01 mm` arithmetic tolerance.

Round 4 passed the exact snapshots above. It verified:

- fixed ZIP MD5, tail SHA-256/count, and workbook receipt SHA/size/CRC locks;
- HTTP range, `Content-Range`, local-header, size, and CRC validation;
- fifteen unique selected members and exact packet cardinality;
- full TIFF decode and pixel-preserving metadata-stripped re-encoding;
- a sealed random HMAC secret and disjoint opaque round tokens;
- a validated Round A completion record written by the runner and an enforced
  24-hour Round B embargo;
- sealed selection/extraction digests and canonical/Round-A pixel identity;
- finite, in-image measurement fields, blank unresolved fields, and the frozen
  projected-length arithmetic rule.

The reviewer did not execute the formal packet builder or edit the files.

## v1.1 amendment review

R001-A stopped before formal selection or extraction because processed cycle 0
mapped to the first H01-1 TIFF at cycle 1, while v1 allowed only half of the
sole forward interval. The v1.1 amendment uses one full adjacent interval at
the first and last TIFF and retains half the smaller adjacent interval for all
internal TIFFs.

The reviewer confirmed that this is a symmetric input-boundary repair, not
outcome tuning. Specimens, state indices, images, measurement endpoint, primary
metric, and threshold remain unchanged. R001-A remains preserved as failed.

- Reviewed protocol v1.1 SHA-256:
  `94beac29884e38ee02534bc94286e11a113440e41e683011809aad798083e7c9`
- Reviewed v1.1 runner SHA-256:
  `602c870f16a995a664131d94b95fe3b8d911ce03e7c55591d8ab54f725f50f16`
- Verdict: `PASS` for commit and R002-A.

## v1.2 amendment review

R002-A stopped before extraction at H05-1 processed cycle 1050 because TIFF
cadence changes from 10 to 100 cycles around the selected cycle-1000 frame.
Revision v1.2 uses the directional nearest-neighbour cell: half the next
interval when the processed cycle lies to the right, half the previous interval
when it lies to the left, one full adjacent interval outside the sequence
boundary, and zero for an exact match.

The reviewer confirmed that earlier-cycle tie selection is unchanged, midpoint
equality is accepted, all 15 frozen indices pass a value-blind mapping audit,
and no measurement outcome, crack length, metric, or threshold informed the
repair. R001-A and R002-A remain preserved as failed pre-extraction runs.

- Reviewed protocol v1.2 SHA-256:
  `21ccf342e5846b123c3572ffff59dff4bb56e7dd54eea9d441ee1471fcf13347`
- Reviewed v1.2 runner SHA-256:
  `d3e1f56821a36f32da5edfc9469a64669a7a0d059ad5bdcd9fe6711a978100f4`
- Verdict: `PASS` for commit and R003-A.
