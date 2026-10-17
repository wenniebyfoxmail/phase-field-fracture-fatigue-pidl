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
49 passed in 1.28s
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

No optimiser step or training was executed. A full E009 producer runner,
resolved configuration, evidence packet, and launch path do not yet exist.
Therefore this is a core-implementation candidate for exact-commit review, not
a full `CODE_READY_PASS` and not an execution authorisation.
