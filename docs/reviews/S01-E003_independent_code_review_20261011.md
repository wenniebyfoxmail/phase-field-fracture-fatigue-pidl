# S01-E003 independent read-only protocol/code review

Reviewer: separate Codex agent `e003_independent_review`, gpt-5.6-sol / Medium.
No producer training or fresh holdout access was performed by the reviewer.

## Bound review

- Verdict: PASS_WITH_NONBLOCKING_NOTES.
- Reviewed commit: `05a380ec3b5cddfc6206087d8d12d3b5a91a13c1`.
- Source manifest SHA-256:
  `27a3f2eb86ac54a642cc12fb9f0b16371f0152d7fd0f53b4cbcdba21247e5710`.
- All listed source hashes independently recomputed: PASS.
- E003 tests 7/7; inherited PaveTrack 32/32; tiled 12/12; compile/diff checks PASS.
- Frozen external artifact hashes and E002 geometric-score comparator checked.

## Superseded review

The first snapshot `9a03a07` failed on two blocking findings: runtime source was
not bound to the reviewed code, and low-IoU validation negative crops could
contain a crack after padding. Neither snapshot was used for training.

Both were repaired before execution. The wrapper now checks the externally
supplied source manifest hash and every listed runner, wrapper, dependency,
protocol, config and data-lock hash before any stage. The runner checks the
manifest and includes it in artifact lineage. The validation loss now excludes
negative padded crops that intersect a crack; a regression test covers this.

## Independent findings

The repaired partitions are disjoint. Validation candidates are frozen and the
old comparator is recomputed on the same boxes. New confirmation is inaccessible
until the selected model, validation, score and lineage freeze pass. Runtime
GPU UUID, device and version checks and duplicate-run markers fail closed.
The +0.05 absolute macro-recall target is acceptable as a practical five-point
improvement at unchanged FP burden, without claiming significance or population
validity. Partial positive improvements remain reportable without overriding
this gate.

## Nonblocking execution note

ReviewedCommit is receipt metadata; enforcement comes from the externally
supplied manifest hash. Launch must pass exactly the reviewed commit and
manifest hash above and execute the verified immutable Git archive.

Decision: code/protocol ready for one producer run under S01-E003-v1. New test
access remains separately gated by the declared validation improvement.
