# S09-E009 producer package Round-2 exact-commit review request

Please review exact commit `6861a1c8260e158269da2738176a62d612f5a2a2`
against the Round-1 producer candidate `3a3296d63370babda8ad7063fdfcff306a18bedb`.

Return exactly one of these tokens on the first line:

- `PRODUCER_PACKAGE_READY_PASS`
- `REVISE_AND_REREVIEW`

This rereview is limited to whether the Round-1 findings F1–F5 are closed.
The previously passed numerical core `8b6a2e49b241ae73f433645cb30a69291f7aee53`
and runner integration `efeffbfae4395f95228c56e3f530e323f1ab8f6a`
remain inherited trust anchors.

The repair candidate now:

1. restores `ARM_ORDER` after canonical JSON reread and tests the real
   resolver-write-reread-executable-validation path;
2. binds public entry points to the loaded module root, hard-binds the approved
   packet manifest, rechecks `base_runtime.packet_identity` before optimizer
   construction, and records that consumed identity;
3. fails before autograd on nonfinite combined replay objectives, checks merger
   diagnostics, and separates numeric replay validity from the new-stream hash
   diagnostic in both code and the final run card;
4. treats exact constant fields as spatial NA, retains all 120 pairwise values
   including NA, and recomputes/validates the nested AUC, amplitude ratio,
   amplitude correlations, spatial support, losses and constraint counts from
   the fixed 16 per-cycle rows;
5. preserves failed-forward hard counts, reports confirmed gradient-log prefix
   separately from an unconfirmed tail, and emits a checkpoint-bound failed
   receipt when evidence hashing fails after checkpoint commit.

Local evidence on the exact commit:

- producer-specific suite: `22 passed in 1.02s`;
- frozen five-file selected suite: `98 passed in 2.24s`;
- `py_compile` and `git diff --check`: pass;
- every producer test installs a fail-if-called `torch.optim.AdamW.step`
  sentinel; zero real optimizer steps, no SSH, producer access, packet export,
  or training occurred.

Please reproduce the focused no-training checks and try counterexamples at the
same F1–F5 boundaries. A PASS means code-ready for a separate final execution
approval only. It is not execution authorization or a scientific result.
