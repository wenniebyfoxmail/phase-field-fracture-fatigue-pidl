# Focused physical/identity producer review — v4

**REVIEW_PASS**, exact commit `43af56d43150f4ae8cf8799ceec4669564d67ef0`, artifact `6b0ef3bf36ffbedf3c33170b2f641c06873684276a18be3f6726537e4d7c4585`, cardv2 SHA256 `da119752c2ee81443dcee43b31cbe1fe2942ae70b39acf115dc1712005d8a125`. All29committed manifest-file hashes and canonical artifact ID verified.

The hybrid-only kernel uses fixed-order binary64 operations for Q4J/det/inverse/gradients, correct native GP order and interleaved engineering-shear B. It preserves the original mathematical operator; it does not drop B/det from identity, round coefficients to admit a mismatch, change the feasible domain or relax tolerances. NativeQ4Backend still rebuilds and compares full B/det strictly. Old PIDL/native functions remain unchanged.

Migration checks every source asset hash and old state/physics identity, creates a fresh target, changes only mesh ID and resulting state fingerprint, verifies all field bytes unchanged and retains old input/state/mesh provenance. Other assets are hardlinked, not rewritten. Independently tested on an artificial distortedQ4 state with nontrivial damage/opaque:6field arrays bitwise unchanged, original bytes unchanged, derivation IDs correct, hardlinks confirmed and tampered old asset rejected. Independent LAPACK B/det differences were1.11e-16/5.55e-17 in this fixture.

Exact exported package regression: **46passed in0.74s**, exit0, including distorted-element operator comparison and linear displacement patch. Inspected the existing Mac native replayv2 receipt:5/5 at unchanged1e-10, with max raw/history approximately1.584e-12; no new labels or solves. Did not rerun project-array replay or inspect new scientific arrays.

New cardv2 changes only input/state identities and derivation wording. Prior design/core/lifecycle/test-isolation/fair-cost/deadline findings carry forward. This does not guarantee identical future nonconvex trajectories after floating-point arithmetic changes, and does not reinterpret old outcomes.

**Linux admission remains incomplete.** HQ reports strict initial mesh/state identities now match, but full asset hashes, --check and five-field Linux replay are still pending. Reviewer performed no SSH/GPU/producer work. Fresh runtime/resource admission and final package display remain required. Use cardv2/new inputs/manifestv4/reviewv4 in the final CLI; the older cardv1 example cannot consume this receipt. No training/new FEM or scientific success is authorized or established by review alone.
