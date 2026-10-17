# External review — cross-Umax short-horizon forecast

**Decision:** freeze as development-only, conditional on one mandatory leakage
lock.

The reviewer accepted whole-Umax folds, trajectory-equal weighting, fixed ridge
`lambda=1`, causal features, recursive h2, persistence/secant controls,
first-detect used only as a post-prediction stress label, confirmed-cycle
exclusion, and descriptive-only uncertainty.

The mandatory correction was to state explicitly that every feature and target
standardization statistic must be fitted inside the two training trajectories
of each outer fold and then frozen before application to the held-out Umax.
This includes stiffness normalization and any data-derived constants. The
stiffness ablation must remain secondary and cannot replace a failed base ridge.

The implemented runner satisfies this condition: `fit_map()` receives only the
two training `Case` objects for the pooled point model; its mean, variance,
normal equations, and target scaling never access the challenge object. The two
single-trajectory fits used only for descriptive ensemble spread are similarly
isolated. Fixed physical clipping bounds and log floors are declared constants,
not data-derived holdout statistics.

Permissible positive claim would have been development-only evidence within the
three examined Hard5 Umax trajectories. Independent validation, early warning,
first-detect timing, deployment, and generalization claims remain forbidden.

