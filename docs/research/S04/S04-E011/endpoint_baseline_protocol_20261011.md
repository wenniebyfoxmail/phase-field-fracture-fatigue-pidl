# C83 single-step baseline reproduction — 2026-10-11

This is a C0/C1 baseline-admission run for the supplemental endpoint diagnostic,
not a changed E011 physical trajectory. It answers whether a restored accepted
c83s3 state reproduces the original native-Q4 c83s4 endpoint.

Inputs: frozen E011 production source, Q4 mesh, accepted c83s3 postcommit
snapshot, and c83s4 native capture. The latter is used solely for a fixed
reproduction gate. Coordinate/connectivity, predecessor damage/history and
source hashes must match before the first Newton solve.

System initialization is copied from the frozen driver without recovery. The
s3 fields replace c0 fields. The s3 native AMOR tangent is reassembled before
the original step-4 load predictor. The original displacement/phase/clamp/post-
update outer block is copied verbatim. Histories and accepted damage remain
immutable; no history commit or subsequent substep occurs.

Frozen controls: eta=0, E=1, nu=.3, AT1 Gc=.01 ell=.01, native Q4 GP4,
U=.11999988; displacement tolerance1e-6, phase/outer4e-4; caps250/250/1000.
A single computation thread limits resource competition with the existing
Windows run. Runtime roundoff differences must pass the gate or stop admission.

Primary reproduction gate: exact iter20 and endpoint u/v/d maxabs<=1e-10,
relative displacement/damage<=1e-8, and native free ru/rd maxerr<=1e-10.
These tolerances test tight same-code floating-point reproduction, not physics.
Any nonfinite value, source/state mismatch, cap or baseline mismatch stops the
run. There is no retry or modified-arm automatic launch.

Minimum evidence: start/PID/commit/command receipt, stdout/stderr and MATLAB log,
progress.mat, baseline_endpoint.mat and result.json. Execution admission is
separate from the scientific stationarity or FEM/PIDL field comparison.

The next solver-control variant may be implemented only after this baseline
reproduces. Its design must consider inner phase accuracy and reassembled
projected residual monitoring, with a budget of at most ten additional outer
iterations and no further load step. It is a separate reviewed variant.
