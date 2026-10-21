# Stage A frozen-state comparison

`compare_frozen_states.py` reads one `e036_frozen_native_v1` MATLAB v7.3
export from `e036_stage_a_export_frozen.m`. It does not optimize fields,
construct a network, call MATLAB/MEX, accept a physical state or commit history.
The production CLI is restricted to the common ordered mesh and the four
predeclared c1/c20/c60/c83 step-4 states with their own step-3 predecessors.
Full-mesh execution on macOS is refused. Run each state in a fresh Python
process on the authorized producer, serially with the native work.

```text
python tools/s04_e036_fem/compare_frozen_states.py
  --input /absolute/frozen_c0001_s04.mat
  --input-sha256 <export-receipt-sha256>
  --common-problem /absolute/common_problem_q4.json
  --common-problem-sha256 <reviewed-common-problem-sha256>
  --output /absolute/new-comparison-directory
  --threads 1
```

The command is shown across lines for readability; use the appropriate shell
continuation syntax or one line. Threads must be 1–4. The entry sets numerical
library and Torch thread limits before assembly. It checks elapsed time between
assemblies and after output, with a fixed 600-second limit; the Stage A wrapper
must also enforce the external wall-clock limit because an individual native
library operation cannot be interrupted by those Python checks.

Two CPU float64 implementations are compared separately to the native arrays:
the existing `compute_energy` derivative with detached fresh trial f, and the
existing independent NumPy weak-form equations. Both use unchanged incoming
history and the exact exported geometry. Compared channels are full/free Ru,
full/free Rd, the current nodal-box projected free Rd, and full-GP raw/P/A/f.
The fixed per-channel rule is `maxabsdiff <= 1e-10 + 1e-8*maxabsref`.
No tolerance override is available. Old history slot 1 is preserved but unused;
new slot 1 must agree with fresh raw energy. The legacy audit's doubly-active
projection is not used: current E036 narrow-interval semantics apply.

The export uses MATLAB one-based cells/DOFs and blocked displacement `[X;Y]`.
Numeric HDF5 axes are reversed on read. Schema and the four `*_json` metadata
fields must be MATLAB `char`, not opaque string objects. Native quadrature,
material/unit thickness, BCs, physical keys and common policy are checked before
assembly. Source, input and output hashes are recorded in `comparison.json`;
full Python arrays are retained in `python_fields.npz`.

Every output directory must be new. A channel miss or input/assembly error is
saved as a failure and returns exit code 1; an existing directory is never
reused. Matching is software equivalence at these supplied fields, not an
equilibrium, reference-accuracy or physical-validity result. Keep failed exports
and reports, and do not loosen thresholds after inspecting them.

Deploy the relative source files listed in `SOURCE_PATHS` along with the common
problem JSON, preserving their paths. Dependencies are Python, NumPy, SciPy,
h5py, PyTorch and Matplotlib. Imported analysis modules have guarded mains;
their solve, trajectory and plotting entrypoints are never invoked.
