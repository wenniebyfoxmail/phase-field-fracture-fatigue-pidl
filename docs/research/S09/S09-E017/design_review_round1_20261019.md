# S09-E017 design review round 1

Reviewer: ChatGPT Pro, Haofan account
Reviewed commit: `43077940e9cdd512697f9730896cc64844527667`
Verdict: `E017_DESIGN_REVISE`

The reviewer accepted the three-arm route, frozen-trunk P0 scope, the limited
`beta=0.25` equilibrium interpretation and the 64-update-per-arm budget. It
identified five design-contract gaps that could change the experiment's
meaning without changing its apparent configuration:

1. distinguish latent head amplitude from the common effective hazard
   amplitude recomputed from each decoded field, including zero-capacity and
   saturation behavior;
2. freeze the active-loss matrix so `D_DIRECT` and `F_AMP_SHAPE` receive the
   same common amplitude/shape/reconstruction/equilibrium supervision, and
   derive each hazard-pair target direction from FEM hazard ordering;
3. replace the optional at-most-`1e-6` exploratory component with a strictly
   positive target-independent capacity-supported seed and require nonzero
   mass-reallocation sensitivity;
4. specify normalization, beta weighting, zero-norm behavior, PCGrad reference
   gradients/order/seed, active-group aggregation, clipping and exact optimizer
   settings;
5. give the result profiles executable predicates at the fixed final update
   and narrow causal claims: gradient conflicts are observations, and a short
   negative result does not prove trunk/state insufficiency.

The review explicitly said no fourth arm or larger budget was needed. It
performed no model forward, autograd, optimiser step, training, SSH/GPU work,
FEM, holdout or rollout and did not authorise execution.
