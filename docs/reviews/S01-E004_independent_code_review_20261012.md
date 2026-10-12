# S01-E004 independent code/protocol/analysis review

Separate read-only reviewer `e003_independent_review`, gpt-5.6-sol / Medium.

- Verdict PASS, exact commit `928c519f613e6d89137430632765b303dc19c78a`.
- Source manifest SHA-256:
  `a3396b0ec253a94ba30dc8ba36299157543dde746b7c619e749ead785e391057`.
- 30/30 source entries independently matched; 64 relevant deterministic tests
  passed, compilation and source audit passed.

Train/validation/confirmation are disjoint. The head uses all 63,202 inherited
train proposals: 1,736 valid and 61,466 invalid, including 10,116 partial-overlap
invalid detections. No GT/IoU field enters prediction features. Train-only
statistics, float64 balanced BCE+L2, fixed features and optimizer, zero-initial
objective replay, frozen E003 comparator, runtime/GPU1 identity, identical-box
metrics, duplicate-run guards and the +0.05 authorization boundary are coherent.

The first reviewed snapshot required downloader/acquisition lineage and initial
loss replay repairs, plus analysis handling for an unidentifiable primary.
All were repaired before fitting or fresh access. The bound downloader is
byte-identical to the prior range/CRC extractor (SHA e1b19c00...), and acquisition
URL/size/locations/files/CRC are checked and bound into downstream evidence.
Analysis asserts TP/FP/used-prefix counts, atomic ties and null outcomes.

Reviewer performed no producer contact, fitting, training or fresh pixel access.
Decision: ready for one producer Run under v1. Fresh confirmation remains gated
by validation delta>=+0.05 and complete freeze verification.

Nonblocking test-runner note: default pytest across both analysis directories
has duplicate module basename test_analysis.py; targeted suites or pytest
--import-mode=importlib work (64/64). Runtime is unaffected.
