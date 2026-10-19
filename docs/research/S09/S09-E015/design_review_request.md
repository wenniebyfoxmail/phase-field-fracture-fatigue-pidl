# S09-E015 design review request

Please review the frozen `experiment.md` before any implementation or producer
execution.

The preceding E014 run is valid Level 3 evidence: its common local secondary is
finite, distinct and orthogonal, but both actual step-1 checkpoints made all 16
predicted damage-increment fields exactly zero. S09-E015 therefore defines each
finite path by the actual checkpoint difference `theta_arm,1 - theta_0` and
evaluates the output map along a fixed logarithmic fraction grid. Exact source
and endpoint checkpoints define lambda 0 and 1; only interior states use direct
float64 interpolation. The earlier analytic next-AdamW displacement archive is
retained as a provenance/tolerance check and is not called byte-identical to
the actual difference. The assay performs no gradient collection, autograd,
optimizer construction or optimizer step.

Check specifically:

1. whether direct parameter interpolation isolates the stated output-space
   geometry question without being misrepresented as an AdamW learning-rate
   study;
2. whether the fixed lambda grid, 13-state accounting and no-adaptive-search
   rule prevent result-dependent route selection;
3. whether `NONCOLLAPSED` and Levels 2-5 preserve useful partial evidence while
   preventing an all-zero field or undefined protected ratio from being called
   a balanced signal;
4. whether same-lambda CG-versus-CL comparison answers the local-secondary
   question without weakening the original global/physics protections;
5. whether source binding, complete-grid evidence, zero-step/no-autograd audit,
   900-second/10-GiB limits and success closure are sufficient for one exact
   implementation review and one later authorised execution.

This revision also asks whether the endpoint replay rule closes the first
review's only blocker: lambda 0 must reproduce E014 baseline evidence, and each
lambda 1 must reproduce its actual E014 endpoint. Continuous evaluator values
use the predeclared inherited tolerance; strict-zero status, positive-node
counts, collapse status, pair outcomes and integer counts must match exactly or
the assay is `EXECUTION_INVALID`.

Return first line `E015_DESIGN_READY_PASS` or `REVISE_AND_REREVIEW`. If revising,
identify the exact clause, counterexample, expected/observed interpretation and
smallest repair. Keep optional refinements separate. A PASS authorises local
implementation and no-training tests only; it does not authorise GPU execution.

