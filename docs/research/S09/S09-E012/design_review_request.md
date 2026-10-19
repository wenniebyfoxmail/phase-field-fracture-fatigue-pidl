# S09-E012 focused diagnostic design review request

Review only the new no-training diagnostic in `experiment.md`.  E010/E011 core,
their frozen results and the existing global-amplitude Jacobian are unchanged
and need not be re-reviewed.

Please check:

1. whether reusing the exact E010 target support mask at `1e-15` is a valid
   local-versus-background oracle diagnostic while remaining clearly
   non-deployable;
2. whether `s_local = mean_support(Delta d_pred) -
   mean_background(Delta d_pred)` distinguishes local crack support from a
   diffuse positive field without an unstable ratio;
3. whether unique-cycle autograd followed by algebraic pair assembly is
   equivalent to repeated pair autograd for all declared directions;
4. whether the decomposition cleanly separates raw ranking gradient, conflict
   projection, merge, positive-scalar clipping, exact AdamW preconditioning and
   realised endpoint displacement;
5. whether the frozen `r >= 1e-4` usability and `rho >= 1e-3` helpfulness
   predicates support honest multi-label mechanism evidence, while the separate
   minimum-change priority selects one bounded exploratory probe without
   treating that action as an exclusive causal verdict or treating low rank
   alone as proof that the head must change;
6. whether the eight wrong and 17 correct pairs, state identities, zero-update
   constraint and 15-minute wall cap are sufficient validity protections.

Return `E012_DIAGNOSTIC_DESIGN_PASS` or `REVISE_AND_REREVIEW` on the first line.
For revisions, give the smallest blocking counterexample and exact repair.
Separate optional improvements.  A PASS authorises implementation and one
read-only producer diagnostic only; it does not authorise training, retry,
holdout access or a new architecture.
