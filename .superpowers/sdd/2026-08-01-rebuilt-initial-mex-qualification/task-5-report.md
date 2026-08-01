# Task 5 Report

## Scope

Implemented qualification orchestration and the fail-closed T1/T2/T3 family gate from base `72047a306e27208e081ca6916e2bba2a456b7191`.

## Delivered

- Q1 and Q2 run in separate MATLAB processes, in order, under a fresh no-clobber qualification root.
- Q1 failure stops before Q2; parent blockers stop Q2 before recovery/System/Newton/cycle and prevent a family receipt.
- `validate_qualification_receipts` verifies passing Q1/Q2 schemas, artifact hashes, approved rebuilt MEX identity, source/runtime provenance, parent locks, and mesh ordering, then publishes one no-clobber family qualification receipt.
- The family launcher requires and revalidates that receipt, rejects legacy/unknown/runtime/source/parent mismatches, verifies previous finalized package manifests, and enforces T1 -> T2 -> T3 with one unchanged qualification/runtime identity.
- The rebuilt MEX is exposed through a temporary package overlay ordered before the clean GRIPHFiTH source path; source and runtime identities remain separately recorded.
- Each case records `FAMILY_RUNTIME_RECEIPT.json`; the finalizer binds it to launch provenance and includes qualification/runtime digests in the validation summary and package manifest.

## Verification

- Qualification MATLAB tests: 92/92 passed (Task 1-4 regression 86 plus Task 5 receipt tests 6).
- Family MATLAB tests: 105/105 passed.
- Family Python launcher/handoff tests: 46/46 passed before the final manifest-hardening change; affected launcher tests 7/7 passed after it.
- Task 5 receipt tests: 6/6 passed.
- PowerShell launcher contracts: 2/2 passed.
- MATLAB Code Analyzer: 0 findings.
- `git diff --check`: clean.

## Runtime Status

No production Q1, Q2 replay, recovery, System, Newton, cycle, or T1/T2/T3 FEM launch was run. The current real parent remains fail-closed with:

```text
blocked_missing_parent_damage_degradation_field
blocked_missing_parent_active_field
```

Consequently no family launch is currently authorized.

## Fix Round 1

Addressed all four Important review findings with fail-closed tests:

- Clean GRIPHFiTH `Sources` are added first and the rebuilt runtime overlay is
  added last with `'-begin'`; launch still requires `which(initial)` to resolve
  to the exact overlay binary.
- Qualification receipt validation now invokes canonical runtime-lock
  validation against the real source/runtime roots, parses Q1/Q2 MAT artifacts,
  enforces schemas and threshold identities, and cross-checks identities,
  metrics, hashes, and byte sizes. Synthetic text MAT and rehashed substitutes
  are rejected.
- Qualification orchestration process-gates immediately before Q1 and again
  immediately before Q2. Controlled tests prove an existing MATLAB/FEM process
  is rejected while the completed Q1 process is not mistaken for a conflict.
- Scoped `.gitattributes` files lock hashed text to LF. Fresh checkouts with
  `core.autocrlf=true` and `false` both validate; deliberate byte conversion
  fails the manifest check.

Fix-round verification:

```text
Qualification receipt focused suite: 7 passed, 0 failed
PowerShell launcher contracts: PASS, PASS
Family Python regression: 48 passed
MATLAB Task 1-4 relevant regression: 30 passed, 0 failed, 0 incomplete
MATLAB Code Analyzer: 0 findings
```

No production Q1/Q2/FEM path was triggered. The real parent blocker is
unchanged: required parent damage-degradation and active-driver fields are
absent, so T1/T2/T3 remain unauthorized.
