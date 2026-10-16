# P1 pre-code status while producer provenance is pending

## Return check

On 2026-10-12, Request 32 had no response in the fetched shared-repository
branches, Windows-FEM outbox, Mac `_pidl_handoff_v2` or the local OneDrive
sync. Exact producer state sufficiency therefore remains blocked.

## Independent work completed

Without adding a scientific payload reader, the repository now contains:

- an in-memory deterministic implementation of the reviewed 73-to-16 cycle
  selection, growth/near-stagnant groups and fail-closed group counts;
- strict stored-float64 and finite-value checks;
- representable half-ULP export-resolution calculations and fixed teacher RMS
  normalisers for damage, four GP-history channels and two displacement
  components;
- deterministic gradient norm equalisation, fixed cyclic conflict projection,
  zero-gradient handling and merged-gradient clipping;
- tests for deterministic selection, positive scales, dtype/group failures,
  conflict projection, clipping and nonfinite rejection.

The earlier phrase "half the least positive float64 subnormal" was corrected:
that value is not representable and underflows to zero. The implementation now
clamps half-ULP values below by the least positive float64 subnormal.

## Verification and boundary

Fifty-seven focused S09 tests pass. These utilities accept only arrays already
held in memory and cannot open the sealed trajectory. They are preparatory code,
not P1 Code Ready. State sufficiency, payload decode, selected real cycle IDs,
normaliser values, optimisation execution and training remain blocked pending
Request 32 and a separate review.

## 2026-10-16 recheck

Request 32 still has no direct return. The newly located peak6 and Stage-2A
packages were checked and rejected as replacements because they do not match
both the exact run and the required full causal trajectory. No real-field
normaliser, cycle group or optimiser step was produced from them. Details are
recorded in `provenance_return_recheck_20261016.md`.
