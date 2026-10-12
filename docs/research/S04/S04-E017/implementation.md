# E017 implementation checks 2026-10-12

Dedicated runner and fail-closed aggregator preserve E014 source untouched.
Runner validates four exact references, freezes per-alpha allocation and
records alpha in checkpoint/metrics/receipt. Passive full-field monitoring
records conditional damage/background RMS and weighted contributions.
Aggregator requires12 distinct state-alpha pairs, independently reconstructs
thresholds, validates final checkpoint/sampler/hash/receipts, monitor/metric
consistency, regional RMS/contribution identities, then applies fixed primary
and sentinel rules. No best-alpha selection on incomplete matrices.

Local checks:47 tests passed (E017 + E014 + E013), py_compile succeeded;
read-only validator passed c20/c60/c83/c40 exact fields. No training on Mac.
Producer launch requires exact-commit independent Code Ready PASS.
