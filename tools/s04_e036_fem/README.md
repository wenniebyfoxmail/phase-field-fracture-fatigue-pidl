# S04-E036 — final-state FEM acceptance adapter

Prepared locally for the audited CITPC12 Hard-5 source `862992a6`; **not applied
to CITPC12 and not executed in MATLAB**. This directory changes acceptance and
history-commit plumbing only. It does not add a FEM solve algorithm or launch a
run. Existing source remains the default control when the option is absent.

## Reused implementation and exact target

- `tools/s04_e011_analysis/coupled_repair/e011_coupled_solve.m`: fresh final
  mechanical assembly followed by phase assembly at the same fields, and
  exclusion of prescribed boundary DOFs.
- `tools/s04_e011_analysis/c1_commit/e011_commit_once.m`: frozen predecessor,
  evaluate the commit mapping from final fields and **old** history once,
  compare trial/commit histories, and persist a proposal before assignment.
- `e036_final_candidate.m` extracts those mechanisms into pure callbacks; it
  never solves, projects fields, or changes the incoming state.
- `build_overlay.py` accepts only the exact audited solver and runner bytes.
  It writes a new overlay directory and refuses input drift, missing/duplicate
  anchors and existing output. It never changes the supplied source directory.

## Explicit problem and acceptance contract

Primary S04-E036 configuration:

```matlab
options.e036_final_acceptance = struct('enabled',true, ...
    'policy',phase_field.audit.e036_policy( ...
        'fresh_original_tolerances','nodal_box_kkt'));
```

The name means use the existing magnitude choices at the **same final state**:
`joint_tol=4e-4`, `u_tol=1e-6`, feasibility tolerance `1e-8`, active-bound
tolerance `1e-10`, history identity tolerance `1e-10`. The final mechanical
`u_tol` check is explicit here; the legacy solver only imposed its displacement
Newton tolerance before its subsequent damage solve. This is therefore not
claimed as a pure cache-refresh intervention.

The final candidate must already satisfy the physical bounds `0 <= d <= 1`
exactly; only the predecessor condition `d >= d_old - bound_tol` uses the
declared `1e-8` tolerance. Incoming `d_old` is nonnegative and the upper bound
is exactly `1`. This ensures an accepted field can be the next step's incoming
lower without clipping. `active_tol` cannot exceed `bound_tol`.
The adapter does not clip it. Prescribed displacement
and damage DOFs are removed. Let `Ru` be fresh force minus traction on free
displacement DOFs. For the phase residual `Rd` on free damage DOFs, use

```text
rKKT_i = min(Rd_i,0)    on the lower bound
       = max(Rd_i,0)    on the upper bound
       = 0             where lower==upper
       = Rd_i          in the interior
C = max((||Ru||_2 + ||rKKT||_2)/joint_tol, ||Ru||_2/u_tol)
accept iff feasible and C <= 1
```

This makes the existing FEM projected output domain an explicit **nodal box
variational-inequality acceptance target**. It does not claim that the old
soft-penalty Newton plus post-hoc projection algorithm already solves that
target. It is not a Gauss-point KKT certificate. Both PIDL and FEM must use the
same nodal domain, predecessor and prescribed DOF sets before comparing this
criterion. Infeasible points cannot be accepted by discarding bound forces.
If a nonzero interval is so narrow that both bound-tolerance masks are true,
retain its raw residual conservatively. Only exact equality of the lower and
upper bounds removes all feasible directions.

`soft_penalty_equations` remains an explicit alternative: it uses the full raw
free phase norm instead of the box norm. It is a diagnostic/control, not the
primary target. Requiring raw zero at a hard lower bound is generally wrong:
for pristine AT1 `d=d_old=0`, `psi+=0`, the fracture term produces positive
`Rd=(3/8)(Gc/ell) integral(N)` and hence a valid lower-bound reaction. The
MATLAB pure-callback selftest includes this case and wrong-sign reactions.

`fresh_strict_e011` separately offers the prior E011 numerical scales
`joint_tol=4e-6`, `u_tol=1e-8`. It is not enabled by default and changing to it is
a distinct accuracy policy. None of these numbers establishes physical or
teacher validity, and none should be transferred across meshes or residual
normalizations without a new rationale.

## Assembly, material and history interfaces

`e036_native_candidate` directly calls the existing native equilibrium and
phase assembly functions. It passes final projected `d`, current `u`, the
original substep `d_old`, and original substep history. Fresh equilibrium
returns `psi+`; fresh phase assembly uses it and computes the current-trial
fatigue coefficient. No derivative through the fatigue coefficient is added.

The native material binding is checked and saved: `E=1`, `nu=.3`, `Gc=.01`,
`ell=.01`, `eta=0`, `alpha_T=.5`, `p=2`, `penalty_irrev=421875`,
`penalty_recov=13781.25`. These are native assembled nodal energy derivatives,
including thickness, shape functions, determinant and quadrature weights;
they are not network-parameter gradients or mass-normalized fields.

The original kernel includes the negative-d recovery contribution:

```text
penalty_recov = (Gc/ell)*9*(Lmax/ell - 2)/(64*tol_AT1_recovery)
              = 13781.25 for Lmax=1, ell=.01, tol=1e-3.
E_recovery = 0.5 * penalty_recov * integral(min(d_GP,0)^2)
```

It is zero at a feasible final state with nonnegative old damage. It can still
affect unconstrained inner trials. A PIDL objective intended to match those
trial equations must include the same opt-in term and coefficient, not only
add it to a separate endpoint checker.

For an accepted candidate the adapter computes a second *pure* phase mapping
with new lower `d_old_new=d_final` and the **same old incoming history**.
History channels 2–4 must agree with the fresh solve mapping within `1e-10`.
The FEM proposal records `f_solve` as the coefficient rebuilt by the **final
fresh assembly**, `f_commit` as the pure commit mapping, and
`f_last_inner_return` as the coefficient returned by the last original inner
assembly. The PIDL controller's `f_solve` instead means the coefficient frozen
for the last optimizer call; compare it with FEM `f_last_inner_return` when
investigating inner-solve lag, not by matching field names alone.
No trial history is used as input to the commit mapping, so
there is no duplicated accumulation. The wrapper assigns accepted history
only after the new joint check and proposal persistence succeed.

Each accepted receipt is labelled
`validated_proposal_before_native_assignment`. It is not on its own proof
that assignment/checkpointing completed: the subsequent existing native step
checkpoint remains the committed-state record. On outer-iteration exhaustion,
a rejection receipt stores the last fresh audit and compact iteration trace,
and history is not committed. Inner solver failures retain the native error
path and cannot reach the commit branch.

## Local preparation and validation

```sh
python tools/s04_e036_fem/build_overlay.py \
  --audited-source-dir /absolute/path/to/audit/fem_live \
  --output /absolute/new/local/overlay
python -m pytest -q tools/s04_e036_fem/test_overlay.py
```

The output contains patched copies under `Scripts/fatigue_fracture/` and three
helpers under `Sources/+phase_field/+audit/`. Applying that overlay to a future
isolated producer snapshot is a separate deployment action; this utility
does not perform it.

Completed locally: five Python source/overlay safety tests; generation against
the actual two pinned live-source copies. MATLAB and Octave are unavailable on
this Mac, so `e036_selftest` and MATLAB `checkcode` are **not yet run**. The
selftest uses tiny callbacks only and has seventeen semantic guard cases; it does
not call a native kernel, linear solver or training code. Native same-state
assembly admission, disabled-mode identity and a producer preflight still
remain before any scientific use. This is prepared code, not a reproduced
trajectory or an executed repair.
