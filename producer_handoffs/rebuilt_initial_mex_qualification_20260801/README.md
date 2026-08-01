# Rebuilt initial MEX Qualification

This handoff qualifies one rebuilt `initial.mexw64` runtime before the
toy-to-road T1/T2/T3 FEM family can run. It keeps the clean GRIPHFiTH source
identity separate from the runtime binary identity and fails closed unless
both Q1 and Q2 produce canonical, hash-bound passing evidence.

## Locked Identities

- GRIPHFiTH source commit:
  `355d4c83fefc2db88c32031a2dd2623b3de85c89`
- approved rebuilt `initial.mexw64` SHA-256:
  `ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db`
- rejected legacy `initial.mexw64` SHA-256:
  `589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340`
- legacy failure classification:
  `blocked_before_cycle1: incompatible_legacy_runtime_binary`
- MATLAB/toolchain: R2025b Update 5 and the compiler/build provenance sealed
  in `RUNTIME_LOCK.json` and `build/`.

`RUNTIME_LOCK.json` is the authority for source, compiler, dependency, and
runtime-artifact identity. `SOURCE_SHA256SUMS.txt` is a separate exact-byte
inventory of the qualification source package. It excludes itself to avoid a
self-reference and excludes `runtime/initial.mexw64`, whose identity is
already locked and independently validated by `RUNTIME_LOCK.json`.

## Qualification Gates

Q1 compares all 12 outputs of the rebuilt MEX with an independent pure MATLAB
Q4 implementation. Its fixed `K*u` check is named
`deterministic_internal_force_probe`; it is not a Newton or equilibrium
residual. Q1 must pass exact index, shape, finite, matrix, numerical-output,
and runtime-resolution gates before publishing a receipt.

Q2 is a one-cycle replay of the unmapped Umax=0.12 Hard-recovery, eta=0,
five-retained-step parent. It requires authoritative fields with this mapping:

```text
damage              = d_elem
history             = alpha_bar_elem
fatigue degradation = f_alpha_elem
raw driver          = psi_raw_elem or psi_elem
damage degradation  = g_elem
active driver       = psi_active_elem = mean_GP(g_GP .* psi_raw_GP)
```

Element-level approximations, `f_alpha_elem` as active, and a product of
element means are forbidden.

## Current Execution Status

The reviewed pre-execution source was sealed at commit `5dafe4e64aa42f6ac387f42ab3f788282c29a513`
and tag `toy-road-rebuilt-mex-preexecution-20260801`. The production
qualification was then run from a fresh output root:

```text
C:/q4diag/rebuilt_initial_mex_qualification_20260801_run1
```

Q1 passed with the approved rebuilt MEX. All eight index vectors were exact;
the stiffness relative Frobenius error was `1.4374484646311128e-16`, and the
`deterministic_internal_force_probe` relative L2 error was
`1.7835846492874314e-16`. The Q1 result is bound to runtime SHA-256
`ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db`
and clean GRIPHFiTH commit `355d4c83fefc2db88c32031a2dd2623b3de85c89`.

Q2 parent validation then confirmed that the locked eight-file parent does
not contain authoritative native/GP evidence for `g_elem` or
`psi_active_elem`. It published both fail-closed statuses:

```text
blocked_missing_parent_damage_degradation_field
blocked_missing_parent_active_field
```

The launcher stopped before recovery, `System`, Newton, or cycle 1.
`QUALIFICATION_EVIDENCE_LOCK.json` remains intentionally absent. Therefore
the current state is exactly `EvidenceLockUnsealed`: there is no family
authorization, and T1/T2/T3 must not start.

## Static Verification

Static verification may validate source bytes, runtime provenance, API
resolution, and tests. It must not invoke the production qualification
launcher or create Q1/Q2 output roots.

1. Verify every line of `SOURCE_SHA256SUMS.txt` against exact repository
   bytes and require complete, case-unique inventory coverage.
2. Run `validate_runtime_lock` against the qualification `RUNTIME_LOCK.json`,
   the committed `runtime/` artifact, and the clean GRIPHFiTH checkout.
3. Record `which` results for the rebuilt overlay `initial`, GRIPHFiTH AMOR,
   AT1-history-fatigue, all required MATLAB helper APIs, and CHOLMOD. Require
   the rebuilt overlay to resolve first and hash every resolved binary.
4. Run the complete Python, qualification MATLAB, family MATLAB, and
   PowerShell contract suites plus MATLAB Code Analyzer.
5. Verify a fresh checkout with both `core.autocrlf=true` and `false`; all
   manifest bytes must remain identical because package text is LF-locked.

Runtime/API evidence must record the repository commit, GRIPHFiTH commit,
MATLAB release/update, canonical resolved path, file SHA-256, and pass/fail for
each required API. Such preflight evidence is diagnostic only and cannot be
substituted for Q1/Q2 receipts or `QUALIFICATION_EVIDENCE_LOCK.json`.

## Execution Boundary

After a later source commit is independently reviewed and sealed, run the
qualification launcher from a fresh, non-existing `C:/q4diag` output root.
It checks the process inventory before Q1 and again before Q2. If parent
validation returns either blocker above, it stops before recovery, `System`,
Newton, or cycle 1. Only canonical passing Q1 and Q2 receipts bound by a sealed
`QUALIFICATION_EVIDENCE_LOCK.json` may authorize the strictly serial family:

```text
T1 -> terminal validation -> T2 -> terminal validation -> T3 -> terminal validation
```

The three cases must use the same exact rebuilt MEX and runtime-lock digest.
