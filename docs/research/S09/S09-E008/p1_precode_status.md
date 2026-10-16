# P1 pre-code and decoder status

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

### Direct-SSH update

The exact run and source were subsequently found on `CITPC12` without a GitHub
handoff. Stage-0A state sufficiency is now source-qualified. A fail-closed
read-only packet decoder and synthetic fixtures have been implemented; all 64
S09 tests pass. P1 remains closed because this decoder has not received an
independent review bound to its exact commit and no sealed scientific payload
has been decoded. The next gate is exact-commit decoder review, followed by the
read-only scientific data-capability audit if that review passes.

## 2026-10-16 Evidence Ready and run-package update

The decoder received exact-commit Code Ready approval after the MATLAB logical
schema repair. A002 then qualified 366 physical payloads, 438 logical bindings,
native weights and the frozen 16-cycle P1 selection. Haofan ChatGPT Pro
independently reviewed the complete 486,723-byte receipt and returned
`EVIDENCE_READY_PASS` after 44 checks, including full 366/438/72 enumeration.

The bounded P1 memorisation package and machine-readable config are now
prepared. They fix the development data, model, seed, 1,000-update budget,
multi-objective update algebra, acceptance buckets, stop rules and outputs.
Training remains closed until the packet exporter and trainer exist, their exact
commit and input packet are locked, and an independent Code Ready review passes.

## 2026-10-16 package-level review closure

The first package review returned three contract findings: float64 scale
consumption and the three/four-history-channel split; complete aligned gradient
vectors and dimensionally consistent epsilon semantics; and explicit hard-
constraint predicates/tolerances. All three were closed in commit `af25e1c` and
42 focused tests passed. A second review confirmed D1-D3 closed and found one
remaining textual conflict between Code Ready inputs and the later production
of the actual data lock/resolved config. Commit `0587796` separated those
objects cleanly between Code Ready and the final execution gate.

The third package review returned `PACKAGE_READY_PASS`. The next authorised work
is local implementation of the exporter/trainer and synthetic/no-training tests,
followed by exact-commit Code Ready review. Real packet export, remote execution
and training remain closed.
