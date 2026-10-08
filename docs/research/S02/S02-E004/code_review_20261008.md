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
