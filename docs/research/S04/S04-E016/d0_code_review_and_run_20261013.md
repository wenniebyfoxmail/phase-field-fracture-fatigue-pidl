# D0 exact Code Ready and Run record

Main chat 01a1131d-017c-7b03-a95a-ad73ba8fcc9c is sole executor;
method chat 01a12d15-9b60-7280-8248-18386d6ef741 is independent read-only reviewer.
Review first held c1bb217 for float32 physical error arithmetic, missing
authoritative guard checks and startup/cleanup races. Those verdicts remain HOLD.
After repair, reviewer final message msg_015d0a19570ed14a016ace7b36b5c08191af0e3c3061ca50b8:
**Code Ready PASS**, exact commit cb86a118aa06b0cbe532b5c63a94c07a84587dc9,
protocol d0_runner_protocol_v1_20261013.md, data lock cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c.

Tests: causal feature checks, weighted strata/transforms/ridge algebra, toy
heldout perturbation leaving all fitted statistics unchanged, four-outer/twelve-
inner toy execution, float64 target dtype, mock combined guard normal/startup/
visibility/race/final-wall paths. No actual archive fit occurred before PASS.
NumPy2.2.6 Accelerate emits matmul warnings even on finite toy arithmetic;
warnings retained, with explicit finite gates at statistics/predictions/scores.

Prepared Run S04-E016-D0-R001, Wennies-MacBook-Pro-14.local, CPU4/no GPU.
Command: /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_d0_guard.py
--out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E016/runs/S04-E016-D0-R001
Output is fresh. Reviewed source paths clean; unrelated task documentation/raw
assets remain dirty and are preserved. The guard records exact commit, dirty
status, UTC start, both child PIDs/commands, elapsed/peak RSS/output and exits.
Budget includes fit+renderer and outputs/log/receipts:300s/2GiB/100MiB, no retry.
Final authoritative receipt is adjacent *_guard_receipt.json; fit-stage success
is not pipeline success. Result/QA still pending at this prelaunch entry.

Only retrospective horizon0 synthetic archive imitation; no teacher, physical,
Contract A, NN, confirmation or rollout authorization. .1175/.125 remain closed.

## Terminal: RSS_CAP, no complete method result

Actual UTC start18:41:32.616508, elapsed56.532636s, sampled peak RSS
2,436,546,560 bytes (2.269 GiB), exceeding2GiB. Guard terminated its own
fit child43887 (exit-15); subsequent ps showed no such process. Six inner-pair
completion messages exist, but no complete outer holdout, selection/models,
percycle metrics, C20 snapshot, runner receipt or figures were persisted.
At terminal the output directory was empty (only a post-run README added later).
Only original guard log and final failed pipeline
receipt remain; no fit-stage success receipt or renderer process. No retry.

Execution failed by budget; scientific verdict INCONCLUSIVE, not negative for
Delta, ridge, multiobjective learning, or teacher qualification. G5 archive data
admission unchanged; physical/teacher/Contract A HOLD, confirmation still sealed.
The required comparator visualization cannot be made without scored outputs;
Evidence Ready for a method comparison is NOT achieved. Do not invent a ratio.

Next smallest repair (prepared only, NOT authorized to execute): replace
whole-fit X/Y/weight concatenation with two-pass cycle-streamed weighted moments
and normalized Gram accumulation; release each cycle buffer. Keep all scientific
inputs, labels, splits, weights, alpha rules, data lock and budgets unchanged.
Require toy equivalence against the dense implementation and working-set audit,
then exact renewed Code Ready and explicit authority for fresh R002. Raw archives
and the failed R001 remain unchanged. Dense allocation/allocator retention is a
plausible bottleneck, not proved by a sampled RSS trace alone.

Independent terminal review: method chat final
msg_015d0a19570ed14a016ace7c8007008191ab3d17c37fc7e73e confirmed no C20
or scored outputs, only guard log/final receipt/post-run README, INCONCLUSIVE.
It remains read-only and will review stable weighted Welford/merge moments,
second-pass normalized Gram and unchanged constant-column/std-floor behavior;
no actual repair execution approved or started.
