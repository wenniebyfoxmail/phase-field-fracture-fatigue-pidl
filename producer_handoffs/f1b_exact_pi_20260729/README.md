# F1b Exact-Pi Fresh FEM Producer Handoff

This handoff runs one new GRIPHFiTH dimensional solve. It is a solver-invariance
control, not PIDL training and not road validation.

## Producer Requirements

- Windows-FEM with MATLAB, GRIPHFiTH MEX binaries, and SuiteSparse available.
- Clean checkout of the pushed `codex/road-rescaling-bridge` commit.
- A writable output parent outside both the reference archive and GRIPHFiTH
  source tree.

Do not run this on Mac-PIDL. Do not reuse or resume an existing output folder.

## Locked Transformation

The candidate changes the formal eta0 SENS realization from

```text
E=1, Gc=0.01, ell=0.01, L=H=t=1, Umax=0.12, alpha_T=0.5
```

to

```text
E=3, Gc=0.3, ell=0.1, L=H=t=10, Umax=1.2, alpha_T=1.5
```

while retaining the same topology, plane strain, AT1/AMOR law, eta0, R=0,
reverse BC, hard recovery, explicit eight-step loading/unloading path, and event
rule. The mesh coordinates are multiplied by ten rather than remeshed, so the
element ordering and the full `h/ell` distribution remain paired.

The nonlinear numerical contract is also transformed. Force residuals scale by
`300`, energy/phase residuals and phase tangents by `3000`, and the staggered
criterion is evaluated only after separately normalizing those two residuals.
See `TOLERANCE_AUDIT.md`; retaining the original absolute tolerances is
prohibited because it changes the dimensionless numerical problem.

## Launch

From PowerShell:

```powershell
& "<shared-repo>\producer_handoffs\f1b_exact_pi_20260729\launch_F1b_exact_pi.ps1" `
  -SharedRepo "<shared-repo>" `
  -GripfithRoot "C:\Users\xw436\GRIPHFiTH" `
  -OutputParent "C:\Users\xw436\GRIPHFiTH_F1b_outputs"
```

The launcher verifies `SHA256SUMS.txt`, refuses a dirty shared checkout, derives
the case name from the source commit, and refuses an existing output root.

## Return Contract

Return the complete new output directory without renaming files. At minimum it
must contain the files listed in `INPUT_LOCK.json`, including provenance,
event metadata, mesh geometry, c20/c40/c60 fields, and the reported first-hit
and confirmed own-event fields. Mac analysis:

```bash
python SENS_tensile/analyze_f1b_exact_pi_solver.py \
  --candidate-root '<downloaded-output-root>' \
  --output docs/f1b_exact_pi_solver_invariance_20260729
```

F1b passes only if both event-cycle errors are at most one cycle and every
predeclared normalized field and active-support gate passes at c20/c40/c60 and
the two own-event states. These are solver/mesh-level tolerances, not replay
identity tolerances, and they are frozen before launch. A completed solve that
misses a gate is `FAIL`, not `BLOCKED`; `BLOCKED` is reserved for lack of an
approved producer or a producer environment failure before a valid solve is
produced.
