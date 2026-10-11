# S04-E014 R001 offline repair-selection result

Result date: 2026-10-11
Source: S04-E013 Attempt B, R016--R027
Execution: read-only local analysis; no optimiser step or producer mutation
Disposition: `REPAIR_SELECTED_UNBIASED_DAMAGE_STRATIFIED_SAMPLING_SCREEN`

## What the completed runs show

The final full-field displacement RMS is stable across seeds, but the logged
minibatch loss is not. Over steps 8,000--10,000, the sampled-loss p90/p10 ratio
ranges from `9.94` to `37.09`. At the final step, the logged minibatch loss is
only `0.19` to `3.02` times the exact full-field loss. Loss traces using the
same seed across different physical states have correlation `0.48--0.82`
(mean `0.708`), consistent with a substantial shared sampling pattern.

The seed decomposition is more decisive. The ensemble-mean bias accounts for
`96.07--96.46%` of the mean weighted displacement MSE; between-seed variance
accounts for only `3.54--3.93%`. A seed sweep is therefore not the first repair.

## Where the remaining error lives

For every state and seed, `99.47--99.84%` of displacement squared error lies on
nodes with reference `damage>0.1`, even though those nodes contain only
`1.60--2.85%` of nodal mass. The worst 1% of nodes alone contain
`99.55--99.79%` of displacement error. Original active-p99 nodes contain
`75.35--99.80%` of displacement error while accounting for about
`1.41--1.60%` of mass.

The network is not globally inert: it reduces the exact-BC affine comparator's
displacement RMS by about `43--54` times. The unresolved error is a highly
localised correction around the damaged/process-zone region.

## Smallest selected repair

The current mass sampler assigns only the stratum's physical mass probability
to that region. A fixed two-stratum estimator can preserve the exact same
full-field mass-weighted objective while guaranteeing adequate local coverage:

```text
A = nodes with fixed reference damage > 0.1
B = remaining nodes
loss = P(A) * mean_A(squared error / Us^2)
     + P(B) * mean_B(squared error / Us^2)
```

Using 90% of the fixed batch in A and 10% in B, the final-error loss-estimator
variance proxy is `1.78--3.16%` of simple mass sampling, a projected reduction
of roughly `32--56` times. This is a loss-estimator proxy, not a measured
gradient-variance reduction, so it selects a controlled producer screen rather
than establishes a solution.

The next test should keep the architecture, initialisation, optimizer, budget,
reference and full-field estimand unchanged and change only to this unbiased
stratified sampler. It should screen c20 early and c83 transition at seed 7,
then stop. The frozen proposal is in [sampling_repair_plan.md](sampling_repair_plan.md).

## Boundary

This result does not prove that stochastic sampling is the sole cause, that the
architecture can represent the local correction, or that mechanics residuals
will pass after displacement fitting. It rules out another blind seed sweep and
selects the cheapest measured lever. S04-E013 remains a valid fixed-procedure
negative.

Compact evidence: [convergence.csv](convergence.csv),
[state_decomposition.csv](state_decomposition.csv),
[localisation.csv](localisation.csv),
[sampling_variance_proxy.csv](sampling_variance_proxy.csv), and
[summary.json](summary.json).
