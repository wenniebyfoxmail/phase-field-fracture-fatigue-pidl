# G5 PINN input bounds diagnostic — 2026-10-13

G5 HOLD. Native64 mapping review PASS does not release D0. The unique PINN field export terminated exit1 on its first c1/s4 damage >=0 assertion, before any trajectory NPZ or export receipt was produced. No FEM full export, solve, training, clipping or retry was started.

Run pf_g5_u0115_s4_export_20261013_v4; CPU only (CUDA_VISIBLE_DEVICES empty), four threads, timeout300s. Mac snapshot base commit 5b1eec29d2bed37d42baab5850ceb9c57ae16249; task branch codex/s04-e016-request31-storage-block-20261009 is dirty; immutable Python SHA334196924ef89ba59256d591686a54f9c0e41256102a7be298e58f2ae424eb1c, approved mapping SHAeb8791f7958c9999b2c2c83058e3542ec3cb25b272d2f9e4a018a313be5ba10f. Remote /mnt/data2/drtao/wennie/pf_g5_u0115_s4_export_20261013_v4. Wrapper launch reported1989195; it is not assumed to be the numerical child PID. Start11:27:37UTC, end11:27:39UTC. Control log/exit/start/end retrieved to local_archive/experiments/S04-E016/g5_export_20261013. Empty partial output retained; raw acquisition untouched.

| First c1/s4 native triangle field | Observed |
|---|---|
| current alpha min | -0.0001325765624642372 |
| current alpha max | 0.9993140697479248 |
| negative triangle count | 78780 / 90000 |
| saved diagnostic definition | mean of current three nodal alpha values, not hist_alpha |

Frozen source SENS_tensile/field_computation.py lines112–115 selects NonsmoothSigmoid(2,1e-3). Its forward implementation lines400–424 has nonzero-slope tails below0/above1. Therefore strict [0,1] output bounds are not guaranteed by this native PINN coordinate. This is not float32 roundoff; the source comment claiming bounds is contradicted by the actual formula. Existing posthoc returns current alpha_elem without clipping too.

Proposed single semantic repair, NOT approved/executed here: retain the failed strict-input-bound audit; label PINN current alpha as signed surrogate phase-field coordinate, require finite identity-correct inputs and report out-of-bound diagnostics rather than clip or falsely claim physical bounds. FEM supervised target bounds remain strict; corrected physical output must be separately validated. Delta remains native FEM target minus actual PINN output, not a new clipped baseline. Independent method review must decide whether this is admissible only for bounded archive-imitation D0, followed by an exact code review for any amended exporter. No producer retraining is implied or authorised. Actual history equality result currently covers only the first attempted s4; full100 remain pending.

Top-level lesson: candidate-input defects, target-reference qualification, export capability and scientific model validation are separate gates. A bounded target does not imply the uncorrected input is bounded; installing the target constraint on the input can reject precisely the discrepancy being studied. No threshold change can promote this failed physical-bound observation to a physical PASS.
