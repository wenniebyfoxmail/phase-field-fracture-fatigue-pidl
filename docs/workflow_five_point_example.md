# Existing-task continuation example

Illustration only: this is not an owner card, a run permission or a new template.
Reuse the existing task's record and values; none of the times below renews an
old experiment. This governance task leaves HQ paused.

**Question / evidence gap.** Can the already-authorised paired comparison
resolve the current discrepancy? If addressing a mechanism, state the proposed
intervention and competing outcome; a theory/calibration/synthesis task uses
its own appropriate argument instead.

**Owner and current record.** The project's existing Experiment/owner card is
the one detailed record. The latest direct human instruction overrides a stale
card. HQ stores its path and a short next-decision summary, not copied limits.

**Same-contract repair.** Correcting log paths/exception propagation can stay
inside the envelope. Changing the solver, data or convergence criterion does
not become a mechanical fix because it makes a run succeed. A wrapper error
does not prove zero progress. Inspect the attributable process, output and
receipt first; unknown state retains the reservation. Explicit one-start and
first-stop instructions still prevail.

**Accumulated budget, only when applicable.** In the original task, record the
start once, total wall allowance, resource allowance if any, waiting treatment,
science end and cleanup reserve. For example, a declared 60-second elapsed
clock with 10 seconds for cleanup leaves 30 execution seconds at t=20 and 10
at t=40. A repair does not restart t=0. Unknown measured CPU/GPU use is unknown,
not zero or the elapsed supervisor wall time. The E036 supervisor's legacy
`charged_gpu_seconds` is a wall-reservation convention, not a GPU utilisation
measurement; the new explicit fields say so.

**Code and benchmark.** Bind actual worktree, entrypoint, commit/snapshot and
input/output paths in the existing receipt. Reuse this fixed offline control
benchmark for changes to the E036 captured-execution path:

```sh
python3 tests/test_workflow_execution_benchmark.py --output /absolute/result.json
# If one item fails, fix it and rerun only that named item:
python3 tests/test_workflow_execution_benchmark.py \
  --case test_real_child_to_saved_result --output /absolute/failed-item-rerun.json
```

It executes local Python children, log capture and saved-result readback.
Ambiguous spawn, observer/ownership loss and clock timestamps are injected.
It does not execute Windows, GPU admission, MATLAB, MEX, recovery, mechanics or
loaded phase-field assembly. No such result is inferred from a control pass.
On this Mac those native runtimes are unavailable; that boundary stays open
without adding SSH, a new FEM job, training or a historical rerun.

**Delivery / result entrypoint.** State actual saved paths, source version and
whether a file was updated in place, versioned separately or not yet applied.
Keep running producers' pinned scripts stable. One result entrypoint links
small plotting inputs, code, rendered figures when useful and interpretation;
large data/frozen code may remain at stable versioned paths. A label/caption
change only checks affected output. A figure is not compulsory for every task.

For this implementation, canonical installed rules/templates are updated in
place. The E036 executor source update is isolated on this task branch, using
the original relative entrypoint `tools/s04_e036/gpu_watchdog.py`; it is not
written over the original owner's checkout or deployed to any producer.
Original source: `worktrees/s04-gap-attribution-20261022/`, commit
`ce0f8a3d07bc93725b886f3a38eda217de62fdcc`. Producer admission, explicit
one-attempt-per-phase restriction and ownership-aware cleanup are preserved.
