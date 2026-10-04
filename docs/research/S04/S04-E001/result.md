# S04-E001-R001 decision

Verdict: supports deterministic reproduction; insufficient for FEM field or trajectory reproduction.
Purpose: reproduce unchanged native-Q4 spatial replay, region attribution, GP cross-swaps, bounded-alpha counterfactual, and fixed-damage equilibrium on Windows.
Gate: existing operator thresholds, unchanged; finite diagnostics; verified archive. No retrospective field-performance threshold added.

## Observed results
- 12 kernel/history tests passed on Windows (5.68 s); all three FEM replays passed. Damage max absolute error <=3.34e-16; strain <=1.60e-12; active-driver relative L2 <=4.45e-11 versus existing 1e-9 limit.
- Fixed clipped PIDL damage, matching essential BC, displacement-only AMOR solve: c76 normalized free residual 0.00343654 -> 6.81557e-15; active-field relative L2 0.4193147 -> 0.4104324 (2.1183% reduction). c82 residual 0.00343608 -> 6.60526e-15; field relative L2 0.4089570 -> 0.4075472 (0.34473% reduction). Active sets stable, 14/12 iterations. Both meet existing solver residual tolerance 1e-8.
- Across four production states, negative nodal damage fraction 86.34--87.58%, damage maximum >1. Frozen clipping reduces active elastic integral by 1.47--2.19%. This is a counterfactual, not a bounded optimization or fatigue-history repair.
- Original un-clipped GP fields: same-cycle c83 active relative L2 3.5543; own-event FEM c83 / PIDL c85 relative L2 1.0702 and correlation 0.01068. These are different estimands, neither establishes spatial reproduction.
- Region metrics use archived element reductions, distinct from GP metrics. At c76/c82 the common-intact active relative L2 is about 0.130/0.099; heavily damaged regions can dominate raw strain/energy discrepancies. Region masks and element-vs-GP support must remain explicit.
- 7 tables / 1516 finite numeric cells compared with prior archive. Among cells whose prior absolute magnitude exceeds 1e-10, excluding residual_reduction_factor, maximum relative drift is 1.06002e-11. This descriptive filter is not a new gate. Tiny residuals and their amplification factors differ more in relative terms but remain around 1e-14 absolute force / 1e-15 normalized residual.
- Float64 network reconstruction differs from original float32 active-driver exports by relative L2 1.62e-4--3.47e-4; not bit-exact. Separate reconstruction_validation.json preserves this limit.

## Decision and stage implications
A spatial replay closes for these three states only. B neural expression remains untested. In C, displacement equilibration alone gives limited field improvement under the two frozen clipped damage states; this cannot prove that all remaining error is damage/history, nor exclude another optimizer path. Strict damage feasibility and the existing minimal one-step discriminator are the next justified tests. Supervised FEM projection followed by physics polish remains the separate expression/objective discriminator. D/E autonomous rollout and transition reproduction are not tested here. No speedup claim is made.

The earlier signed-AT1 energy contamination and six-arm matrix remain historical evidence in the production archive; this run did not rerun that optimization matrix. Exact accepted step-412 checkpoint and trained network were recovered read-only from Taobo and their hashes match remotely; they were not inputs to the present calculations.

## Provenance and execution
- Source: ff42cb9; production networks: aaf13fd native-Q4 archive. Mathematical diagnostic scripts copied unchanged.
- Successful launcher: 47ed14f. Condor cluster 54, PID 51632, D-26-09, 2026-10-04 16:38:26--16:41:05 UTC. Numerical section 159 s; scheduler RemoteWallClockTime 246 s. ExitCode 0. Runtime: Python 3.12.14, torch 2.5.1+cpu, numpy 2.1.3, scipy 1.14.1, h5py 3.12.1.
- Allocation: 8 CPUs /32GB /1 GPU required by host START. Actual numerical threads: 1; no GPU computation, no training. No system services or ACLs modified.
- Earlier infrastructure attempts are retained separately: private-runtime access, batch launch, interrupted transfer, missing Windows environment/configuration. Attempt 53 passed tests but parallel replay exited 0xC000070A without metrics; single-thread attempt 54 completed. This does not identify the exact underlying runtime fault. Microsoft documents the code as STATUS_THREADPOOL_HANDLE_EXCEPTION: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55 .
- Download: 57 files verified by SHA-256 and byte count. results.zip SHA-256 bb006df7ce8ebdac7cf5c1d7ce1ebb0a64e3e571c956c9ce226cd84d6c2252b6.

## Evidence and limits
Tables: operator_replay_summary.csv; cross_platform_numeric_drift.csv; ../retrieved/output/{region,gp_crossswap_equilibrium}/. Figure: figures/fixed_damage_equilibrium.{png,pdf}. Caption: normalized free-DOF residual and common-Q4 active-driver field error before/after displacement equilibration at c76/c82, with the same clipped PIDL damage. Residual convergence does not coincide with comparable field-error reduction in these two frozen states. Curves overlap on the residual log scale. No new damage/fatigue evolution or network fitting.

Figure inspected: axes readable, field-error axis begins at zero, final labels separated, no field rescaling or smoothing. Scientific claim promotion and independent review remain pending; mechanical reproduction is not Evidence Ready.
Next: existing bounded B0 and minimal one-step protocol using recovered exact restart; separately register projection -> physics-polish diagnostic. No new long trajectory sweep yet.
