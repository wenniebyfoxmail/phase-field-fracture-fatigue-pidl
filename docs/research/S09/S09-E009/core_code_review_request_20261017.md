# S09-E009 exact-commit core implementation review request

Date: 2026-10-17
Reviewer: Haofan / ChatGPT Pro
Exact implementation commit: `53b9bf9ab12c6fa3bc333b9287483735414ec3ba`

Please review only the local four-arm **core numerical contract** against the
frozen protocol v3. This candidate deliberately contains no producer runner and
must not be judged as a full training package.

Return one first-line verdict:

- `CORE_CODE_READY_PASS`, if these primitives are faithful and safe to integrate
  into a separately reviewed runner; or
- `REVISE_AND_REREVIEW`, followed by concrete blocking defects.

Please check:

1. exact E008 replay objective coefficients and absence of double clipping;
2. S/A0/A25 causal differences, pre-projection equalisation, projection sign,
   beta placement, stationary/zero behavior, and one global clip;
3. six atomic loss reductions and whether predicted `u` and `d` both remain in
   the equilibrium autograd graph;
4. byte-identical but object-independent model copies and empty independent
   AdamW states;
5. gradient flattening/layout, disconnected-block handling, actual parameter
   displacement diagnostic, and finite checks;
6. zero denominator, AUC ties, fixed-support spatial NA, movement tolerance and
   decision precedence;
7. whether the tests are meaningful enough for this core-only scope.

Do not request training, producer access, a larger budget, or threshold changes.
A PASS authorises only integration into a future runner and further no-training
verification. It does not authorise optimiser execution or make a scientific
claim.
