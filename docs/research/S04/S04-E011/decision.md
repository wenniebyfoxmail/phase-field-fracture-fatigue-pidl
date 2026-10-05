# S04-E011 decision

Status: read-only numerical/source audit complete; evidence review pending.

All 18 accepted states pass the original Stage0b staggered stopping expression. The largest reconstructed stopping sum is `3.78799e-4` at `c40s4`, or 94.70% of the native `4e-4` tolerance. Yet all 12 nonzero loading/peak states fail the later teacher `rho_u <= 1e-3` screen; all six unload states pass it.

The early–middle–late checkpoints tell the same qualitative story. At the peak, the native stopping sums are `3.19299e-4` at c20, `3.61986e-4` at c60, `3.64307e-4` at c82, and `6.43088e-5` at c83. The corresponding teacher `rho_u` values are `0.71750`, `1.28578`, `1.35335`, and `0.04133`. Thus the disagreement is already present in the early state, persists in the middle and late states, and decreases sharply at the transition state without passing the teacher gate.

The accepted-pair raw UV norm is amplified by approximately 4.17e3–4.44e3 when expressed as the frozen mass-dual teacher metric. This factor is stable across early, middle, and late states, so the large teacher numbers are primarily a consequence of the evaluation norm and scale, while the cycle-to-cycle variation still reflects the accepted residual vector.

Verdict: the apparent contradiction is a criterion mismatch, not evidence that Stage0b skipped its post-damage UV residual check. The native solver certifies `raw UV L2 + phase residual <= 4e-4`; the later audit asks a substantially stricter and spatially weighted question. Consequently:

- the Stage0b fields are valid outputs under their original solver contract;
- they are not equilibrium-qualified teachers under the later mass-dual `rho_u <= 1e-3` contract;
- neither statement is a true-solution or mesh-convergence claim;
- the remaining residual cannot yet be attributed quantitatively to the last damage update because genuine last-iteration intermediate fields were not archived.

For the PINN/FEM reproduction objective, the next decision is methodological: either polish FEM UV at fixed accepted damage before using physics-residual evaluation, or evaluate reproduction first against the FEM solver's native acceptance norm and report the mass-dual screen as a stricter secondary qualification. This choice must be frozen before model comparison; it cannot be selected after seeing PIDL results.

