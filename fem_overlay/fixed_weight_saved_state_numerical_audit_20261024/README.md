# Fixed-weight saved-state numerical audit

This package prepares one bounded, offline audit of the already exposed
U0.115 and U0.125 native FEM archives. It is a source-bound reconstruction of
accepted saved states, not a FEM rerun and not a model-training task.

The source package is not an execution receipt: any staged run must be
evaluated from its separately captured launch, execution, and result artifacts.
It neither opens U0.1175 nor changes an FEM archive. The configuration factory
returns `execute=false`, and the MATLAB entry point rejects any configuration
until that value is changed manually after review.

This is a prepared, fail-closed launcher, not a locally executable-qualified
result. The package bytes alone do not establish that a target host can satisfy
the 862-source MEX ABI. The local frozen source evidence establishes the
relevant call semantics, but does not provide a complete runnable checkout at
that exact commit. The launch gate therefore requires the actual clean producer
checkout, validates its locked source interface before any MAT payload is
decoded, and stops without a metrics CSV if that source/runtime binding cannot
be established.

## What the audit evaluates

MATLAB independently admits exactly these two archive identities before it
opens any static or dynamic MAT payload. The Python preflight is a supplemental
cross-check only and cannot admit an archive:

| condition | physical states | physical transitions | producer commit |
|---|---:|---:|---|
| U0.115 | 516 | 515 | `862992a60edc7f59335365beacb5c71fc8592a7a` |
| U0.125 | 366 | 365 | `862992a60edc7f59335365beacb5c71fc8592a7a` |

The MATLAB admission check rehashes every member named by each
`SHA256SUMS.txt`, pins the manifest itself plus the fixed
index/static/config/source-receipt/run-summary hashes, verifies all 882 unique
physical payload hashes, and checks the complete chronological `s05 → s00`
alias chain. It also checks the original five-substep schedule (including the
`1e-6` cyclic endpoint used to avoid an exact zero during construction), the
stored effective factors, and imposed displacements with the producer's own
`1e-14` schedule-comparison precision. That number is only a load-metadata
identity check; it is not a numerical-result acceptance threshold. The `s00`
zero-load anchor occupies the first sealed schedule position, whereas the source
`uy_increment` contains the five physical transitions; the reconstruction
therefore compares its cumulative increments only to positions `s01` through
`s05` and supplies those same five positions to the chronological target loop.
The output receipt is written outside the archive roots. The Python receipt records an
additional run of those byte/topology checks but has
`archive_admission_authoritative=false`; it records the actual constrained
interpreter but cannot turn an unqualified archive into an admitted one.
Before that numerical comparison, MATLAB imports the index as text so it
parses the sealed decimal load tokens directly instead of re-parsing a
display-rounded floating-point value.

For each of the 880 chronological physical transitions, MATLAB then loads the
target payload only after rechecking its hash. It reconstructs `sys` from the
sealed static payload after checking the native Q4 mesh/connectivity,
four-point quadrature, material tuple `(E, ni, Gc, ell, res_stiff, alpha_T,
p)`, cyclic load schedule, and every stored displacement and phase-field DOF
partition against the source DOF equations and sealed native vectors. It verifies the actual target displacement
rows against reconstructed `fix_X`, `fix_Y`, `disp_X`, and `disp_Y` constraints
and the prescribed load, rather than relying only on payload metadata. It then
uses the original native assemblers:

```matlab
[~, R_u, psi_plus_recomputed, ~] = AMOR(MESH, DOFS, t, QUADRATURE, MAT_CHAR, CC, ...
    u, 0.0, d, stress_state, history_prev);
[~, R_d, ~, history_new] = AT1_PENALTY_FATIGUE(MESH, DOFS, t, QUADRATURE, ...
    MAT_CHAR, CC, d, d_lower, psi_plus_recomputed, stress_state, history_prev);
```

The launcher first requires the native AMOR third output to have the sealed Q4
shape and finite values, and then requires exact equality with the stored
`strain_en_undgr_gp`. It records the raw difference and stops on any nonzero
entry; it never introduces an energy tolerance or repair. The phase residual,
projected KKT, and history commit consume that recomputed AMOR energy, so their
causal inputs are target `u,d,psi_plus` plus the immediately preceding
*physical* state’s `d_lower` and `history_prev`. For the separate
post-acceptance history commit, the source first assigns `p_field_old =
`p_field`, so the launcher uses the target clipped `d` as that commit call’s
lower field while retaining the preceding state’s `history_prev`. Feeding the
target’s already committed history back into `AT1_PENALTY_FATIGUE` would advance
fatigue twice, so the launcher rejects a broken `s05 → s00` chain and never
does that.

It reports free-DOF mechanics residual norms, post-clip phase residual norms,
the source-compatible projected KKT diagnostic, lower/upper primal violations,
and exact MATLAB equality (`isequal`, after finite real-double output checks)
plus max-absolute raw history reassembly differences by H/alpha/q/f.
It additionally reports raw H/q minima and negative-entry counts, alongside
the raw H-versus-psi and q-versus-saved-degraded-driver differences. It
preserves all raw H/q values; there is no canonicalisation, clipping, or
tolerance-based acceptance rule in this package. If a tiny negative H/q entry
is reproduced by the second native history call, the receipt records that it
comes from the sealed target inputs and the unmodified AT1 MEX update—not from
an audit-side clip or conversion. It does not by itself identify a lower-level
floating-point cause beyond that replay.

`c0001_s00` is labelled
`post_clip_zero_load_recovery_pre_cycle_committed`: it is after the source’s
zero-load recovery and `[0,1]` clipping, with `p_field_old` set to that clipped
field and fatigue slots reset. Before it accepts that label, the launcher
requires exact zero `u,H,alpha,q` and energy fields, exact `f=1`, `d∈[0,1]`,
finite payload values, and exact zero load metadata. It is an initial condition
for the first transition, not an independently re-established unconstrained
phase-field KKT solution.

## Required environment

Run only on a Windows FEM host that has all of the following already available:

1. A **clean Git checkout** at commit
   `862992a60edc7f59335365beacb5c71fc8592a7a`, including the compatible
   `Sources`, `Dependencies`, and native `mexw64` assemblies.
2. MATLAB that can load the v7.3 payloads and invoke those MEX files.
3. An explicit existing absolute path to the reviewed Windows Python Launcher,
   currently `C:\Users\xw436\AppData\Local\Programs\Python\Launcher\py.exe`
   with SHA-256
   `e52553f941ceb9e715d239e7a211501ce5d6096eeeb90fb161b7bfedf6a61dab`, plus a
   registered CPython 3.11-or-newer runtime for the standard-library-only
   supplemental preflight. Confirm that live hash before creating `cfg`. The
   launcher is supplied as an argument, never found through `PATH`; the inert
   configuration records the canonical path in `cfg.python_launcher_path` with
   its SHA-256, and the audit rehashes that same path before invocation. MATLAB
   invokes it as `-3 -B -s -P`, and the receipt records the actual CPython
   executable, version, and isolation flags.
4. A new output-directory path outside both archive roots and outside the
   source checkout. Its parent must exist; the output directory itself must not
   already exist, because the launcher refuses to reuse it.

The source checkout is verified with `git rev-parse HEAD`, `git status
--porcelain`, the exact Git blobs for the two assembler modules and staggered
post-update code, plus MATLAB `which` resolution to the current-platform MEX
extension and a SHA-256 fingerprint for each runtime MEX. Any mismatch stops
the audit before a metric is emitted.
The runtime MEX fingerprints are recorded for review, but neither archive
contains a compiler/build receipt that proves a source-to-MEX binary mapping.

## Reviewed launch command

Copy this package to an isolated audit workspace on the FEM host without
altering the FEM source or either archive. In MATLAB, create the inert config
first with the explicitly inspected launcher path (no embedded arguments and
no `PATH` fallback; the audit supplies `-3 -B -s -P` itself):

```matlab
addpath('C:\q4runs\fixed_weight_saved_state_audit_20261024');
cfg = make_fixed_weight_saved_state_audit_config( ...
    'C:\path\to\clean\producer_862992_checkout', ...
    'C:\q4runs\fixed_weight_saved_state_audit_results_20261024_R001', ...
    'C:\Users\xw436\AppData\Local\Programs\Python\Launcher\py.exe');
```

After reviewing the resulting `cfg`, set `cfg.execute = true` and call:

```matlab
receipt = run_fixed_weight_saved_state_audit(cfg);
```

The launcher uses these fixed inputs; it does not accept a third condition:

| role | path or value |
|---|---|
| U0.115 archive | `C:\q4runs\hard5_new_runs_u0115_u0125_20260827_v1\hard5_u0115_stage0b` |
| U0.125 archive | `C:\q4runs\hard5_new_runs_u0115_u0125_20260827_v1\hard5_u0125_stage0b` |
| source | the `source_root` argument, a clean producer checkout at `862992a60edc7f59335365beacb5c71fc8592a7a` |
| audit output | the new `audit_root` argument, e.g. `C:\q4runs\fixed_weight_saved_state_audit_results_20261024_R001` |

The only files created are in `cfg.audit_root`:

- `preflight.json`
- `saved_state_transition_metrics.csv` (one row for each of the 880 transitions)
- `saved_state_audit_receipt.json`

`PACKAGE_SHA256SUMS.txt` records SHA-256 digests for the reviewed package files
(excluding the manifest itself). The inert configuration captures that
manifest's own SHA-256, and the launcher verifies both the configuration-bound
manifest and every named member before it creates its output directory. The
preflight path is fixed to the package-local script; an alternate script is
rejected. Before that supplemental script is invoked, MATLAB has already
performed the authoritative archive admission. Immediately before the first
MAT load it repeats that MATLAB admission, so a preflight receipt is never used
as a trust shortcut.

## Boundaries and blockers

The saved dynamic payloads do **not** retain the phase Newton iterate before
the source clips `d=max(d,d_lower)` and optionally clips the upper bound. They
also do not retain every Newton/staggered iterate or a direct `D_RHS_tract`
vector. For these prescribed-displacement archives, the launcher asserts that
there are no Neumann DOFs or traction faces and uses the resulting exact zero
external vector. If that assertion is false, it stops.

Consequently, a completed audit can establish only a saved-state reassembly
record. Its execution status is `completed_saved_state_audit` and its receipt
sets `numerical_admission_decision` to `not_evaluated`; it
does not prove Newton convergence, staggered fixed-point
convergence, a staggered `Δd` stopping criterion, an unprojected KKT theorem,
source-to-MEX build equivalence, physical benchmark agreement, or
independent-test status.
