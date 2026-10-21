# S04-E035 — Standard Umax 0.12 main-solve network L2 removal

Purpose / evidence stage: bounded synthetic numerical exploration, C1/C2 diagnostic.
Question: does removing only `1e-5 sum(weight²)` change finite RPROP optimization,
fields and one-step history consequences at representative standard states?
No accuracy or physical-validation claim; neither comparator is qualified truth.

Goal anchor: user requested a new chat to try a solve without regularization.
Continue the standard hard_d1_u0_recovery seed1 8x400 family; this is separate
from the source chat's archived-gradient analysis and from native-Q4 S04-E011.
Owner chat: 01a15fbd-8618-77b1-a90a-bbac583fe35a.

D1 reuse: inspected standard raw model_settings, original archive, historical
`fit_with_early_stopping`, `get_optimizer`, energy, field and fatigue helpers;
no existing matched L2 solve found. Reuse those unchanged functions.
Base b6d56102daa7d45a6c196b72055010170e5f39fb is remote-preserved and its
relevant source/config/field/mesh files equal the original producer e9dc263.
Task branch `codex/s04-l2-ablation-20261021`, dedicated clean worktree.
Scope: new runner, analysis, S04-E035 records only; no shared defaults/core edits.

## Protocol r1 — fixed before producer results

Active D2: paired frozen-history solves; D3: compare, visualize and record.
Mechanism: even small L2 can change total-gradient coordinate signs after
physical-term cancellation; RPROP sign history can amplify finite-path changes.
Alternative: L2 does not materially affect these finite solves despite scalar loss change.

Six states fixed by coverage: c1/c40/c83 peak and unload: raw steps
4,5,199,200,414,415. Recovery step0 adds an offset: peak=1+5(c-1)+3.
All six are before the archived c89 event, with early/middle/late load/unload coverage.
For target j, both arms load network trained_1NN_(j-1) and checkpoint_step_(j-1).
History tensors are postcommit at j-1, detached and held fixed throughout j.
Same fine mesh, material, nonsmooth damage map, standard BC, current_active,
fem_gp_tri3_g_mean history reduction, fem_gp_tri3 irreversibility; no oracle.
Arms use fresh standard RPROP lr1e-5/step_sizes1e-10..50, up to10000 epochs,
relative loss tolerance5e-7 for10 consecutive epochs; LBFGS0 for these nonzero steps.
Only main-solve weight_decay switches1e-5 ->0; biases/activation coefficients
remain excluded from L2. Pretraining/recovery and preceding trajectory are shared.
Original stopping uses each arm's own loss definition, which itself may affect
termination; endpoint and iteration histories will distinguish that effect.

Primary descriptive observable: within-pair nodal damage RMS/max difference
and common log10 energy, per state, without a scientific pass threshold.
Secondary: u/v differences, total physical network gradient and canonical
regularized gradient, L2 gradient, same-vector sign-change fraction, iterations,
time, damage bounds, nodal and tri3 retreat, one-step trial history/fatigue fields.
Parameter-gradient norm is not a FEM equilibrium residual or KKT certificate.
Trial history is computed once for diagnostics; it is NOT fed into a next solve.
No local result will be called a full-trajectory or initialization ablation result.
One trajectory/seed; six correlated states are coverage, not six independent samples.

Authority: delegated direct user request covers necessary preparation/checks/review
and one bounded exploration; gpu-taobo or gpu-server, single GPU, cumulative
at most1 GPU-hour. This is the task implementation ceiling, not a historical
user budget. Choose Taobo GPU5 after fresh resource/process recheck.
Per-arm240s cap, whole runner3300s cap, plus outer3550s timeout includes setup/export.
12 sequential arm executions receive Run IDs S04-E035-R001..R012 in state/arm order;
one dispatcher, fresh case paths, no retries after scientific failure.
Zero-start recheck cap: two connection/resource checks before actual launch;
initial sandbox connection errors are environment checks, not scientific attempts.
Stop on invalid input/nonfinite failure; diagnose without scientific retry.
No extra seed, full trajectory, changed initialization, new FEM or irreversibility ablation.

Minimum evidence: exact commit/review, environment/command/process receipt,
per-arm input/final metrics and fields, loss/gradient traces, complete/partial
retrieval status, exact-output comparison plot and README_analysis.
Planned figures: all six damage/control/intervention/difference maps with common
scales, common-energy/gradient convergence and sign/retreat diagnostics.
Interpretation: detectable effects establish local finite-path sensitivity only;
small effects do not prove global redundancy. Capped arms remain capped, not converged.

Status: prepared; review and producer execution pending. No scientific result yet.
