# S04-E014 proposed unbiased stratified-sampling repair screen

Status: PLAN PASS; implementation and local non-training checks authorized;
producer execution requires exact-commit Code Ready PASS

## Bounded question

Can unbiased fixed-damage stratification recover the frozen supervised
displacement gate at one early and one transition state without changing the
architecture, full-field objective or 10,000-step budget?

## Frozen screen

- Units: `c20s4 seed 7` and `c83s4 seed 7`, two fresh independent networks.
- Comparator: the completed S04-E013 seed-7 result at the same state and all
  original field gates.
- Inputs, reference SHAs, float64 architecture, Xavier initialisation, exact
  boundary ansatz, AdamW, cosine schedule, 10,000 steps and final-only decision
  remain identical to S04-E013.
- Strata are fixed before training from admitted reference damage:
  `A = damage>0.1`, `B = complement`.
- Batch size remains 16,384. Each step draws exactly 14,746 nodes from A and
  1,638 from B, with replacement and conditional probability proportional to
  the original nodal mass inside each stratum.
- The loss is `P(A)*mean_A(f_i) + P(B)*mean_B(f_i)`, where
  `f_i=||u_theta-u_ref||^2/|Us|^2`. This is an unbiased estimator of the same
  frozen full-field mass-weighted loss. Samples are not weighted by mass again.
- NumPy PCG64 seed remains `S+1000003`; the exact draw order and concatenation
  order are implementation constants.
- Exact full-field displacement RMS and the two stratum contributions are
  monitored at steps 0, 1000, ..., 10000, but only step 10000 votes. No early
  stopping or checkpoint selection.
- No damage solve, history update, target mutation, architecture change,
  warm-start or budget extension.

## Outcome and repair triggers

Primary screen criterion:

```text
both final displacement mass RMS / |Us| <= 1e-3
```

- Primary pass: `STRATIFIED_SAMPLING_REPAIRS_SUPERVISED_FIT_SCREEN`. If strain
  or `rho_u` still fails, the next bounded lever is a mechanics/derivative-aware
  objective; if all gates pass, request a separately authorised 12-run
  validation.
- Primary fail, but both states reduce displacement RMS by at least 50% versus
  their frozen S04-E013 seed-7 comparator: sampling is useful but insufficient;
  test one deterministic full-field polish under a new gate.
- Otherwise: `SAMPLING_ONLY_REPAIR_REJECTED`; move to one local/multiscale
  representation screen. Do not extend this run.
- Missing, corrupted or nonfinite evidence: `INCONCLUSIVE` or `INADMISSIBLE`
  under the same fail-closed precedence as S04-E013.

Strain and `rho_u` are reported as secondary repair selectors and cannot rescue
a displacement failure. This two-run screen cannot grant
`SUPERVISED_CAPACITY_PASS` for the original four-state, three-seed matrix.

## Minimum evidence and next gates

Required: two final checkpoints and predictions, final metrics, 11-point exact
full-field monitoring traces, sampler identities, run receipts, verified
archive copies, comparison table and decision figure.

Implementation and Mac non-training tests require planning PASS. Taobo launch
then requires exact-commit Code Ready PASS, fresh Run IDs and fresh output,
archive and log roots.
