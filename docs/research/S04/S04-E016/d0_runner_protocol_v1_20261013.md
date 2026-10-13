# D0 runner protocol v1 — frozen before fit

Owner S04-E016, synthetic C1/C2 current-state archive-imitation diagnostic only;
Run S04-E016-D0-R001, main chat sole executor. Admission is the separate G5
archive verdict, not physical teacher PASS. Data lock cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c.

Reuse search found scalar lifetime ridge in run_m2s_next_stage_feasibility.py;
its target/splits are unsuitable. Reuse approved s04_g5_features.py unchanged.
Only B0 zero correction vs B1 closed-form three-output ridge; no NN/POD/retry.

Four whole-Umax outer folds; three whole-Umax inner validations within each
outer training set. Identical inner training pairs may reuse their fitted model,
but each model's statistics are independently training-only. No holdout enters
scales, normalizers, Gram matrix or alpha selection. Each trajectory has equal
weight, each C1–20/C21–40/C41+ stratum equal weight, each cycle within its stratum
equal weight. Fit 2048 systematic linspace indices of sorted contained geometry
per cycle, with sampled native area weights normalized per cycle; score all85112
cells with full native areas. Not random cell CV or independent physical replicas.

History/raw scale = full-domain training-PIN weighted mean with the same
case/stratum/cycle weights; fail if <=1e-12. Targets are [d,log1p(ab/h),log1p(raw/r)].
Label = transformed FEM minus transformed PIN. Features/labels standardized
using fit-row weighted means/std; std<1e-12 replaced by1 (not scale amplification).
Training weighted Gram normalized sum1, intercept unpenalized; alpha .01/1/100.
Inner selection: for each channel average the three inner-validation balanced
MSE ratios B1/B0; minimize the maximum of these three averages. Exact ties pick
larger alpha. B0 MSE<=1e-24 is unidentified: stop, never denominator rescue.
Final B1 = transformed PIN + predicted standardized delta inverted by d identity
and expm1 for history/raw. No output clipping. Finite inverse required.

Report per-cycle, per-stratum and per-fold transformed/physical RMSE ratios,
full-area bound violations, signed ranges, selected alpha, cost. These are
diagnostics, no scientifically justified acceptance margin and no scientific
PASS. A transformed gain with physical regression remains regression. Ridge
failure is not proof that NN/multiobjective methods cannot work.

Preregistered figures: all4 outer folds vs B0=1, three channels, transformed and
physical ratios; fixed u0115 C20 target/PIN/B1 and B1-minus-FEM on native Q4
polygons, shared symmetric asinh scale per channel (display only, no clipping).
Must visibly inspect; pair with CSV, README_analysis and decision. No seed bars.

Execution: Mac closed-form analysis ONLY, /Users/wenxiaofang/miniconda3/bin/python3
SENS_tensile/s04_d0_guard.py --out <fresh local archive>/S04-E016-D0-R001.
External monitor covers fit AND renderer jointly within300s/2GiB/100MiB,
including payload, figures, log and receipts. It polls child RSS/output and elapsed
time and kills only its own process group; inner fit checks295s. A completed
authoritative fit-stage guard receipt admits rendering (matched run/code/PID/path);
the final pipeline guard receipt is authoritative for full completion. All target
and physical error arithmetic is float64. Startup failures/cleanup races retain
failed receipts; no retry/budget expansion on cap.
Minimum evidence includes exact reviewed commit, guard receipt, selection/models,
percycle metrics, fixed C20 predictions, figures and scoped verdict. Confirmation
and .1175/.125 remain sealed. Code Ready still required before invocation.
