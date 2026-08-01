# Rebuilt initial MEX Qualification Design

## Purpose

Qualify the rebuilt GRIPHFiTH `initial.mexw64` before it is admitted to the
T1/T2/T3 toy-to-road runtime. The rebuild is a runtime compatibility repair
from unchanged GRIPHFiTH source, not a constitutive or solver-physics change.
No family trajectory may start until both qualification levels pass.

## Locked Identities

- GRIPHFiTH source commit:
  `355d4c83fefc2db88c32031a2dd2623b3de85c89`.
- Legacy crashing `initial.mexw64` SHA-256:
  `589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340`.
- Approved rebuilt `initial.mexw64` SHA-256:
  `ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db`.
- Legacy failure classification:
  `blocked_before_cycle1: incompatible_legacy_runtime_binary`.
- MATLAB runtime: R2025b Update 5,
  `25.2.0.3177638`, win64.
- Rebuild toolchain: Intel oneAPI Fortran 2025.3.2 through MATLAB's
  `Intel oneAPI 2025 for Fortran with Microsoft Visual Studio 2022`
  configuration, with Microsoft Visual Studio 2022 linker/toolchain.

The source checkout and runtime artifact are separate identities. The clean
source checkout must remain byte-clean at the locked commit. The rebuilt MEX
is stored under a separate immutable runtime-artifact root and must never be
used as evidence that the source checkout itself is clean.

## Runtime Lock

`RUNTIME_LOCK.json` records and requires:

- the old MEX hash and fatal `0xc0000005` evidence;
- the approved rebuilt MEX hash;
- the clean GRIPHFiTH source commit and clean-status receipt;
- MATLAB release, update, architecture, and version;
- C/C++ and Fortran compiler identities;
- the exact successful `mex` commands, flags, and complete build log;
- source hashes for every Fortran gateway/module consumed by the rebuild;
- hashes for rebuilt `initial`, unchanged `AMOR`, unchanged
  `AT1_HISTORY_FATIGUE`, and CHOLMOD `cholmod2`;
- proof that no `.cpp`, `.c`, `.h`, or `.m` source changed during rebuild;
- the required Q1 and Q2 evidence identities.

The legacy crashing hash must be rejected, the approved rebuilt hash must be
accepted, and every other hash must be rejected. Missing source, compiler,
build, binary, or qualification provenance fails closed.

All T1/T2/T3 receipts must bind to the exact same `RUNTIME_LOCK.json` digest
and rebuilt MEX digest. A runtime change after T1 starts invalidates the whole
family.

## Q1 Independent Source-Equivalence Assembly

Q1 runs in an isolated MATLAB process before any recovery, Newton solve, or
cycle. Its native input is the unmapped SENS mesh and the unrecovered hard
crack field constructed by the locked GRIPHFiTH initialization semantics.

The reference is an independent, pure MATLAB Q4 implementation. It must not
call an equilibrium MEX. It reproduces:

- Q4 Jacobians, positive-determinant validation, inverse Jacobians, global
  derivatives, and blocked-order B matrices;
- Gauss-point damage interpolation;
- `CC_dmg = ((1 - N*d)^2 + res_stiff) * CC`;
- element stiffness and global stiffness assembly;
- L2 projection matrix;
- strain and stress projection operators;
- all 12 gateway outputs in the original column-vector ordering.

Before invoking the rebuilt MEX, Q1 independently rejects malformed or
nonfinite mesh fields, connectivity, material IDs, quadrature, constitutive
data, damage, dimensions, index ranges, and nonpositive Jacobians.

### Q1 Acceptance

The six index outputs are compared item-by-item and must be exactly equal.
All 12 outputs must have formula-prescribed shapes; every output must be
finite; all indices must be integer-valued and in range; assembled sparse
dimensions must be exact.

For the global sparse tangent:

```text
norm(K_mex - K_matlab, 'fro') /
max(norm(K_matlab, 'fro'), 1e-30) <= 1e-12
```

Every other non-index numerical output uses relative L2 `<= 1e-12` and also
reports maximum absolute error. If a reference output is identically zero,
its maximum absolute error must be `<= 1e-14`; a relative denominator cannot
be used to pass it.

The fixed audit displacement has top-boundary y DOFs equal to
`0.25 * 0.12 = 0.03`; every other DOF is zero. Q1 compares:

```text
deterministic_internal_force_probe = K * u_probe
```

with relative L2 `<= 1e-12`. This quantity must never be named a Newton
residual, equilibrium residual, solver residual, or cycle-1 solution because
the free DOFs have not been equilibrated.

Q1 publishes a no-clobber receipt containing input/source/runtime hashes,
shapes, norms, relative errors, maximum absolute errors, and pass/fail state.

## Q2 Native-Parent Cycle-1 Replay

Q2 is a separate unchanged-parent diagnostic, not T1/T2/T3. It uses the
unmapped formal Umax `0.12` parent, parent recovery semantics, five retained
substeps, the complete locked solver, and one cycle only. A c1 diagnostic
terminal state is legal only for this qualifier and must remain impossible in
the family runner.

The replay must disclose and lock the exact effective retained factors and
the parent `rebuild_sys_after_recovery` behavior. It may not silently replace
historical parent behavior with the corrected family recovery behavior.

### Q2 Field Identities

The only valid mappings are:

```text
damage               = d_elem
history              = alpha_bar_elem
fatigue degradation  = f_alpha_elem
raw driver            = psi_raw_elem
damage degradation   = g_elem
active driver         = psi_active_elem
```

The active driver is defined strictly as:

```text
psi_active_elem = mean_gp(g_gp .* psi_raw_gp)
```

`f_alpha_elem` is not the active driver. Neither
`(1 - d_elem)^2 .* psi_raw_elem` nor any product of element means may replace
the Gauss-point product mean.

If the locked parent lacks native `g_elem` and `psi_active_elem` fields and
lacks sufficient locked Gauss-point evidence for strict reconstruction, Q2
must publish and return the applicable blocker:

```text
blocked_missing_parent_damage_degradation_field
blocked_missing_parent_active_field
```

It must not run a candidate and invent a substitute reference. A future
supplemental parent artifact is admissible only after its source identity,
ordering, semantics, and hashes are independently sealed. The currently
locked eight-file parent and the historical local c1 shard contain only
`d_elem`, `alpha_bar_elem`, `f_alpha_elem`, and raw `psi_elem`; the available
final checkpoint is not a c1 GP state. Therefore active Q2 is presently
blocked unless new authoritative parent evidence is supplied and sealed.

### Q2 Metrics

For every nonnegative field:

```text
L(q) = log10(max(q, 0) + 1e-14)
```

Any value below the permitted numerical negative tolerance fails before this
transform; clipping must not hide an invalid negative value.

For each field, define the support from the parent before reading candidate
results:

```text
M_q = q_parent > max(1e-14, 1e-12 * max(abs(q_parent)))
```

On `M_q`, report log10 MAE, log10 RMSE, and log10 correlation. Outside the
mask, require absolute MAE `<= 1e-12` and absolute maximum error `<= 1e-10`.
If the mask is empty, skip log metrics and require the whole field to pass
the absolute gates.

Reference zero variance is determined before candidate inspection by:

```text
max(q_M) - min(q_M) <= 1e-14 * max(1, max(abs(q_M)))
```

- If the reference has zero variance and the absolute gates pass, correlation
  is recorded as `not_applicable_zero_variance`.
- If the reference has nonzero variance and the candidate has zero variance,
  the correlation gate fails.
- Undefined correlation must never be encoded as one.
- Masks, floor, and variance tolerance are immutable after candidate data are
  observed.

### Q2 Acceptance Thresholds

Damage:

```text
MAE         <= 0.002
RMSE        <= 0.005
correlation >= 0.995
```

History, raw driver, and active driver on their fixed supports:

```text
log10 MAE         <= 0.05
log10 RMSE        <= 0.10
log10 correlation >= 0.99
```

The parent c1 fatigue degradation is identically one. It must pass absolute
MAE `<= 1e-12` and absolute maximum error `<= 1e-10`; its correlation is
recorded as `not_applicable_zero_variance`. Damage degradation uses the same
log10 MAE `<= 0.05`, log10 RMSE `<= 0.10`, and log10 correlation `>= 0.99`
gates as the active driver when its parent support has nonzero variance, plus
the fixed outside-mask absolute gates. These thresholds are immutable before
candidate execution.

Q2 publishes no-clobber replay state, predeclared masks, metric receipt,
runtime/source hashes, and terminal status. It is never counted as a family
trajectory.

## Fail-Closed Family Gate

The production launcher must reject before MATLAB solve when:

- the legacy, unknown, changed, or missing runtime hash is observed;
- source commit, clean-source receipt, compiler/build provenance, or any
  runtime hash is absent or mismatched;
- Q1 or Q2 evidence is absent, non-passing, malformed, or bound to another
  runtime/source/parent identity;
- the family runtime receipt differs across T1/T2/T3;
- the active parent field is blocked or substituted;
- any previous family member failed terminal validation.

The old crash is recorded only as
`blocked_before_cycle1: incompatible_legacy_runtime_binary`; it is not a T1
geometry, Newton, or numerical-convergence failure.

## Sealing And Execution Order

1. Implement runtime artifact/lock, Q1, Q2, and fail-closed tests with TDD.
2. Run Q1 in an isolated process.
3. Run Q2 only if all required parent fields, including true active evidence,
   are available and sealed.
4. Run complete Python and MATLAB test suites and verify source/runtime/API
   hashes.
5. Regenerate source manifest, README, evidence records, and durable evidence
   tag; independently review; seal and push.
6. Only after Q1 and Q2 both pass, use fresh roots and strict serial order:
   T1, terminal validation, T2, terminal validation, T3, terminal validation.
7. Any failure stops the family immediately. No next case is launched.

No qualification success may be inferred from assembly not crashing alone.
