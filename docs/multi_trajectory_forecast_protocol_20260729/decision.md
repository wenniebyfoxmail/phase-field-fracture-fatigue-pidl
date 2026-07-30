# Decision: completed factorial LOCO forecast matrix

## Verdict

The sealed within-Hard5 forecast experiment is complete. Taobo executed all
36 fixed jobs (4 held-out trajectories x 3 model families x 3 seeds) for 3000
steps. The downloaded archive preserved all 36 run directories and passed
254/254 SHA-256 checks against the remote manifest.

Neither TCN nor Transformer is promoted over the matched Markov graph control.
The held-out evaluation is complete, but the forecast task gate fails.

## FEM-centred result

Values below are means over 12 independent fold-seed units. The full tables
also report 95% intervals and paired same-fold, same-seed differences.

| Task | Family | Active log-MAE | FEM-p99 IoU | Absolute support ratio |
|---|---|---:|---:|---:|
| observed-state h1-h3 | Markov | 0.0586 | 0.6301 | 0.698 |
| observed-state h1-h3 | TCN | 0.0546 | 0.6024 | 0.677 |
| observed-state h1-h3 | Transformer | 0.0530 | 0.6023 | 0.672 |
| transition warning | Markov | 1.0559 | 0.4833 | 32.84 |
| transition warning | TCN | 1.0553 | 0.4860 | 32.87 |
| transition warning | Transformer | 1.0586 | 0.4844 | 32.89 |
| first-hit reset h1-h3 | Markov | 2.6136 | 0.01045 | 94.51 |
| first-hit reset h1-h3 | TCN | 2.6430 | 0.01041 | 94.77 |
| first-hit reset h1-h3 | Transformer | 2.6493 | 0.01041 | 94.76 |

In same-regime propagation, the temporal models reduce average active-field
amplitude error slightly but worsen FEM-p99 localization. None of the primary
paired 95% intervals excludes zero favorably for both active log-MAE and IoU.

All 36 runs miss every one of the six transition-positive warning states in
their held-out trajectory. The event-state reset indexing was audited: the
forecast history includes the true FEM first-hit state. Nevertheless, the next
three predicted states spread absolute active support to about 95 times the FEM
area. The earlier single-trajectory reset-recovery result therefore does not
generalize to this four-trajectory factorial.

## Cost

Mean training time was 304 s for Markov, 346 s for TCN and 363 s for
Transformer. Parameter counts remain within the frozen 1% matching gate.

## Evidence

Formal result package:

`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/pidl_result/factorial_loco_matrix_20260729`

The analysis directory contains model/task and horizon summaries, paired
intervals, runtime, transition-warning counts, the all-fold scatter plot, and
FEM-centred transition/reset active-support montages. The remote result manifest
SHA-256 is
`6b292aeaed15f2d3beda482382bf884cb48eb12d90a5f19c5706f5540a085b33`.

## Claim boundary

This is a synthetic, shared-geometry, within-Hard5 initial-tip/loading-history
factorial. It is not road-like LOTO and provides no geometry, material, road or
calibrated hazard/RUL generalization. A negative promotion result is still a
completed experiment; it must not be relabelled as missing producer access.
