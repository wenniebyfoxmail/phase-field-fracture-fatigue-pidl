# S09-E007 independent design review request

Please review `experiment.md` as a fail-closed pre-unsealing protocol. No U0.125
scientific field has been read for this experiment and no inference has run.

Return exactly one verdict: `DESIGN_READY`, `MODIFY_AND_REREVIEW`, or
`REJECT_REDIRECT`.

Check especially:

1. whether the existing U0.125 archive can honestly serve as a post-selection
   holdout despite `exposure_unknown_not_cleared`, with the stated claim limit;
2. whether the evaluation unit and no-update information set are unambiguous;
3. whether `Q_f<=0.50 AND Q_u<=1.10` is a coherent, attainable, smallest joint
   criterion and whether aggregate displacement is justified for a full trajectory;
4. whether the data-only checkpoint is the honest comparator;
5. whether the validity gates prevent partial-state cherry-picking or leakage;
6. whether the outcome/repair map advances toward a causal transition PINO
   without promoting fixed-damage reconstruction to evolution evidence.

List every blocking ambiguity and the smallest exact repair. A pass authorises
read-only U0.125 acquisition and evaluator implementation; it does not authorise
Taobo inference before exact-commit Code Ready review.
