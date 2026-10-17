# S09-E009 producer package Round-3 narrow review request

Please review exact commit `bc1309c75a2309e8b5e0fa00d474605a333d0379`
against the Round-2 candidate `6861a1c8260e158269da2738176a62d612f5a2a2`.

Return exactly one of these tokens on the first line:

- `PRODUCER_PACKAGE_READY_PASS`
- `REVISE_AND_REREVIEW`

This rereview is limited to the two Round-2 F5 residuals. F1-F4, the numerical
core `8b6a2e49b241ae73f433645cb30a69291f7aee53`, and runner integration
`efeffbfae4395f95228c56e3f530e323f1ab8f6a` remain closed.

The exact candidate now:

1. bridges the inherited fail-fast hard-constraint exception into structured
   adapter counts without a second forward; the strict internal payload is
   parsed and schema-checked before re-raising the original exception;
2. covers both initial-evaluation and first-update real-forward boundary
   violations with the unmodified inherited predicate, and checks matching
   reason/count, zero optimizer calls, and unchanged parameters/buffers;
3. catches persistent per-artifact fallback read failures, omits any fabricated
   hash, records the unavailable artifact in the failure reason, preserves the
   real checkpoint hash, and still writes a valid EXECUTION_FAILED receipt.

Local exact-commit evidence:

- focused two-residual suite: `4 passed`;
- selected five-file no-training suite: `101 passed in 2.27s`;
- `py_compile` and `git diff --check`: pass;
- autouse `torch.optim.AdamW.step` fail-if-called sentinel remained silent;
- no SSH, producer access, packet export, or training occurred.

Please reproduce only these two F5 counterexamples. A PASS means code-ready for
a separate final execution approval; it is not execution authorization or a
scientific result.
