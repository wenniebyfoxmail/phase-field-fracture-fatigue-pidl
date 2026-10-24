# Source interface binding

The launcher binds its executable source checkout to clean commit
`862992a60edc7f59335365beacb5c71fc8592a7a`. It refuses a different `HEAD`, a
dirty checkout, an assembler that MATLAB resolves outside that checkout, or a
resolution that is not the current-platform native MEX extension.
The archive `source_receipt.json` for both accepted roots is separately pinned
to that same clean commit by MATLAB's archive admission, together with the
sealed run summary, full manifest, index topology, and payload inventory. The
package-local Python preflight is a supplementary cross-check and cannot admit
an archive. It is launched only through the explicit absolute launcher path
captured in the inert config (currently
`C:\Users\xw436\AppData\Local\Programs\Python\Launcher\py.exe`, SHA-256
`e52553f941ceb9e715d239e7a211501ce5d6096eeeb90fb161b7bfedf6a61dab`), whose
live bytes must be checked against that value before config creation, then are
SHA-256-bound at config creation and rechecked at execution; it is never
resolved through `PATH`. The launcher must select CPython 3.11+ with
`-3 -B -s -P`, and its receipt records the actual interpreter executable,
version, implementation, and isolation flags.
At launch MATLAB also resolves the three Git blobs below and writes
a SHA-256 fingerprint of each runtime MEX into the output receipt. The
fingerprint identifies the executable used for that audit, but it is not proof
of a source-to-binary compiler/build relationship: the sealed archives do not
retain such a build receipt.

The package itself has only been statically inspected. No MATLAB/MEX ABI call
was made while preparing it, and the local provenance snapshot is not a full
runnable checkout at that exact commit. Accordingly, the documented calls are
a runtime-gated plan: if the actual clean checkout cannot satisfy the source
lock and resolve the required native functions, the launcher stops before it
opens a static or dynamic MAT payload and emits no numerical metrics.

The package copies the **call semantics**, not an alternate solver. It invokes
the native AMOR and AT1 penalty-fatigue MEX routines directly. The source blobs
whose identity was checked for this archive family are:

| relative source path | Git blob |
|---|---|
| `Sources/+phase_field/+mex/Modules/fem/assembly/equilibrium/amor.f90` | `6a30c52161b2999889b7bc1b57a17cbd6e4c6db5` |
| `Sources/+phase_field/+mex/Modules/fem/assembly/pf/at1_penalty_fatigue.f90` | `d3d03cdd2ee1d894893f1cbb584a7e94947ec6b7` |
| `Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m` | `e74c95ac7b4a439bbc7815561ff45c071428c065` |

The same gate requires and records the Git blobs for the two MEX wrapper
sources, `phase_field.System`, `phase_field.fem.solver.step.params`, and
`solve_fatigue_fracture.m`. The commit lock binds those latter files; the
explicit three-blob checks above bind the reviewed mechanics, fatigue, and
staggered-update semantics used by this audit.

## Exact residual call interfaces

The source-reference oracle has SHA-256
`8dac483a9e4e7bfe7a6fbec296bdd310a87889706ded119ffafe4a9e23aba9e8` and
uses these calls:

```matlab
[~, R_u_assembled, psi_plus_recomputed, ~] = assembly_equilibrium_fh( ...
    sys.MESH, sys.DOFS, sys.GEOM.t, sys.QUADRATURE, sys.MAT_CHAR, sys.CC, ...
    displ, 0.0, p_field, sys.stress_state.as_number, history_vars_old);
R_u_full = R_u_assembled - D_RHS_tract;

[~, R_d_full, ~, history_new] = assembly_pf_fh( ...
    sys.MESH, sys.DOFS, sys.GEOM.t, sys.QUADRATURE, sys.MAT_CHAR, sys.CC, ...
    p_field, p_field_old, psi_plus_recomputed, sys.stress_state.as_number, ...
    history_vars_old);
```

The frozen reference is
`local_archive/experiments/S04-E036/gap_attribution_20261022/run_workspace/fem_b_assets_v1/payload/native/Sources/+phase_field/+audit/assemble_residual_oracle.m:1`.
Its first 54 lines construct the exact force/phase residuals and free-DOF
partition. The launcher inlines only that simple assembly sequence so it can
require the actual producer MEX handles at run time.

The MEX wrapper’s AMOR comment and implementation show that old field/history
arguments are ignored by the mechanics calculation. The current target `u,d`
and the source-static system determine the assembled mechanics residual and
the third-output undegraded GP energy. The launcher requires that third output
to be finite, Q4-shaped, and exactly identical to the sealed payload's
`strain_en_undgr_gp`; it then feeds the recomputed energy into both AT1 calls.
Any difference fails before phase/KKT/history metrics are emitted. The launcher
also requires both MEX residuals, the AMOR energy output, and the committed
history output to be real, `double`, finite, and shape-compatible before it
uses them in norms or history comparisons. It still supplies the prior raw
history in the source signature and retains it unchanged.

For this archive the static payload has no Neumann DOFs and no traction faces.
The launcher asserts both facts, then uses the resulting exact zero
`D_RHS_tract`. A nonzero external-load configuration is a hard blocker, not a
reason to infer or approximate a force vector.

## Causal history and KKT reconstruction

The source solver performs the phase Newton solve with `p_field_old` and
`history_vars_old`, then applies `p_field = max(p_field,p_field_old)` and the
optional upper clip before its staggered post-update. Only after the accepted
step does it commit history by calling the same phase assembler again. See the
frozen solver at
`Scripts/fatigue_fracture/solve_fatigue_fracture.m:115-195`.

Therefore for every target post-commit payload the launcher uses:

| input | source |
|---|---|
| `u`, `d` | target payload |
| `psi_plus` | native AMOR recomputation from target `u,d`, required to equal the sealed target energy exactly |
| phase residual/KKT `p_field_old` / lower damage | immediately preceding physical payload |
| history commit `p_field_old` | target clipped `d` after the source assignment |
| `history_vars_old` for both calls | immediately preceding physical payload |

The source uses the preceding lower field for the phase solve, then at
`solve_fatigue_fracture.m:182-194` assigns `p_field_old=p_field` and calls the
assembler again to commit history. The AT1 fatigue routine creates `q`,
`Δalpha`, `alpha`, and `f` from the target field plus the preceding history.
Its update is visible in
`at1_penalty_fatigue.f90:85-99`: `q=((1-d_gp)^2+eta)*psi`,
`Δalpha=H_+(q-q_prev)`, `alpha_new=alpha_prev+Δalpha`, and the source fatigue
expression produces `f`. The launcher reports exact MATLAB equality (`isequal`
after the real/finite checks) and raw differences between this reassembled
`history_new` and the target payload; it never feeds target history back in as
input.

The projected KKT diagnostic follows the preserved pure MATLAB function with
SHA-256 `ad8e27ef6d6ba69b7478e1bba65a53e3784a62695d5bb195e8e72f1f9b16ecd2`:
`projected_kkt_metrics(residual_phi_full,d,d_lower,active_dof_pf,epsilon)`.
It applies the source-reference `epsilon=1e-12` only to classify bound-active
DOFs for reporting. It is not an admission tolerance and it does not modify
any archive value.

The AT1 module assigns history slot 1 directly from `strain_en_undgr` and slot
3 from `((1-d_gp)^2+res_stiff)*strain_en_undgr`. The audit records H/q minima,
negative-entry counts, and exact reassembly deltas without changing them. A
negative entry that is exactly replayed is therefore evidence about the sealed
source-state/MEX computation; this bounded replay cannot identify an unlogged
inner-iteration or hardware-rounding mechanism beyond that fact.

## Why the initial state has a special label

`run_SENS_hard_recovery_native_q4_capture.m` carries out zero-load recovery,
clips the recovered `p_field` into `[0,1]`, assigns `p_field_old=p_field`, and
then resets fatigue slots before emitting `c0001_s00`. The static writer saves
the native mesh/DOFs/quadrature/material/BC/geometry/stress state/config
(`write_stage0b_static.m:65-88`); each dynamic payload records post-commit
fields (`write_stage0b_state.m:8-93`). Since the pre-clip iterate and
inner-solver trace are not retained, the audit labels that state as
`post_clip_zero_load_recovery_pre_cycle_committed` rather than claiming it as a
fresh unconstrained KKT solve.
