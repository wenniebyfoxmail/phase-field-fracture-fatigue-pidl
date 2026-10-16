# S09-E008 P1 package review round 1 — revise and re-review

- reviewer: ChatGPT Pro, Haofan account;
- submitted package commit: `785129c` (short identity stated in request);
- verdict: `REVISE_AND_REREVIEW`;
- review type: package-level design/executability review, not Code Ready;
- scope: seven submitted files; no model construction, backward, optimiser,
  FEM, remote execution, packet export or training.

## Findings retained

The mapping, development-only boundary, 16-cycle membership, 1,000-update
budget/order, three objective pairing, judgement metrics, diagnostic buckets,
stop rules, output list and Taobo-only producer boundary were accepted. The
review returned three implementation-contract gaps:

1. A002 normalisers were declared float64/verbatim but the model constructed
   scale buffers through float32. The package also needed to state explicitly
   that three history scales feed raw heads while all four feed evaluation.
2. Per-objective gradients needed a full common parameter order with zero blocks
   for legally unconnected parameters. The projection denominator compared a
   squared norm with a norm epsilon, creating scale-dependent projection.
3. “Zero hard-constraint violations” needed fixed predicates, tolerances, check
   times and a distinction between projected-output validity and raw-proposal
   clipping diagnostics.

The review also required an unambiguous order for resolving the trainer commit,
packet identity, GPU/environment and equilibrium normaliser. These are allowed
later values, but none may be chosen after seeing initial metrics.

## Response

Round 2 changes construct model scale buffers directly in float64; freeze the
three-scale raw-head/four-scale evaluation interface; define full-vector gradient
assembly and logging; use `eps**2` for squared-norm projection eligibility;
freeze the lower-median, averaging and clip semantics; define every hard-
constraint predicate/tolerance/check time; and state the placeholder resolution
order. The cycle set, budget, architecture and scientific thresholds are
unchanged. No training or real packet export was performed.
