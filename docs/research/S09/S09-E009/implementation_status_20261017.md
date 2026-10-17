# S09-E009 local implementation status — 2026-10-17

## Scope implemented

The local core implements the frozen four-arm numerical contract without a
producer launch path:

- exact E008 replay objectives and merger;
- scalar data-only aggregation;
- damage-anchor beta 0 and beta 0.25 directions;
- one complete-direction global L2 clip per arm;
- six atomic losses on the E008-compatible runtime;
- byte-identical, object-independent arm initialisation with empty AdamW state;
- actual parameter-displacement alignment diagnostics;
- deterministic replay ratios, amplitude ratios/AUC, fixed-support spatial
  medians, and the four-level A25 performance classification.

## Verification

Using `/Users/wenxiaofang/miniconda3/bin/python3`:

```text
51 passed in 1.15s
```

The selected suite covers the new core, the frozen E008 update contract, and
the E008 no-training runtime. `py_compile` and `git diff --check` also pass.

After the first exact-commit review, the core also fails closed on nonfinite
derived norms/dots/ratios, emits native JSON scalar types for valid NumPy
inputs, and distinguishes an exactly zero projected vector from a retained
near-zero residue. These fixes do not change the frozen four-arm formulas.
The frozen replay merger boundary is checked separately because that inherited
implementation uses an overflow-prone ordinary norm internally; nonfinite
input norms now stop before the merger, without adding a second clip.

## Boundary

No optimiser step or training was executed. Exact commit
`8b6a2e49b241ae73f433645cb30a69291f7aee53` received
`CORE_CODE_READY_PASS`.

The first local integration candidate at exact commit
`77ab15254e8b444a37ae9f11c9a91791f2e1d906` now freezes the four-arm schedule,
copies and isolates the arm models/optimisers, binds the reviewed E008 runtime,
preserves the same-forward `g_D` needed by the later AdamW displacement
diagnostic, and declares the future evidence manifest. Its 59-test selected
suite passed with `AdamW.step` replaced by a fail-if-called sentinel.

ChatGPT Pro returned `REVISE_AND_REREVIEW`: the numerical runner connection,
same-forward damage gradient, arm isolation and fixed schedule passed, while
the base-config identity check and terminal evidence declaration required
repair. The production path now binds the reviewed E008 config and protocol by
independent hashes. Its synthetic adapter permits only the 9-node/4-Q4 size
substitution and rejects every other base-runtime change. The evidence contract
now distinguishes completed, execution-failed and method-inapplicable arms,
including conditional update-500 checkpoints and cross-arm comparison gates.

Round-2 reproduced 69 tests and confirmed those major repairs, but found one
remaining trust-anchor edge and five receipt-consistency edges. The synthetic
adapter now verifies the trusted reference file's own frozen hash before using
it. Terminal receipts now require valid nonnegative constraint counts, zero
violations for completed/applicable states, evaluation and stop locations
consistent with completed steps, and a checkpoint identity whenever a real
update-500 checkpoint is present. A late evidence-writer failure may retain
that checkpoint while remaining `EXECUTION_FAILED`.

The further repaired selected no-training suite reports 75 passed, including
all 64 arm/cycle direction comparisons and every Round-1/Round-2 counterexample.

This layer still exposes no producer loop or optimiser-step route. A resolved
producer configuration, full evaluator/evidence writer and launch path do not
yet exist. The repaired exact integration commit still requires a narrow
ChatGPT Pro rereview; neither its local pass nor the prior core PASS is an
execution authorisation.
