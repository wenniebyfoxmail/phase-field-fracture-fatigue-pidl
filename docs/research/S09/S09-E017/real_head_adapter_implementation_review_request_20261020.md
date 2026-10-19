# S09-E017 real-head-adapter implementation review request

Review the exact disabled candidate against the design at
`06bf5fef693be5321ce7daf9d2384b8fa3953fde` and final-package blockers B1-B5.

Please independently verify archive/manifest/commit identities and inspect the
actual source rather than relying on this summary. Return one verdict:

- `E017_REAL_ADAPTER_CODE_READY_PASS`; or
- `E017_REAL_ADAPTER_REVISE`, with minimal blocking counterexamples.

Check specifically:

1. checkpoint membership, shapes, dtypes, finiteness and storage aliasing;
   update-0 bitwise preservation through the original one-call three-output
   linear arithmetic and max/clamp boundary cases;
2. exact arm partitions and counts, common frozen `h_i`, pristine starts,
   frozen anchors, deliberate F_AMP_SHAPE seed offset and cross-arm isolation;
3. real decoded A/S/R/P loss -> raw gradient -> frozen scaling -> reviewed
   PCGrad -> exactly one AdamW step, including withheld F_AMP S gradient;
4. evaluation non-mutation, operation/step/commit counters, first-stop
   preservation, complete evidence, non-self-referential inventory and
   retrieval verification;
5. authority-before-import ordering, resource checks, fixed 64/192 budget,
   no retry/resume/transfer and complete internal dependency closure;
6. field/evaluator/figure output and the bounded interpretation of positive or
   negative results.

This review may establish implementation Code Ready only. It cannot authorise
execution or establish a scientific result.
