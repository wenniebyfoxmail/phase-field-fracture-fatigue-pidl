# S04-E011 decision

Status: complete; independent evidence review PASS.

All 18 accepted states pass the reconstructed original Stage0b staggered stopping expression. The largest reconstructed stopping sum is `3.78799e-4` at `c40s4`, or 94.70% of the native `4e-4` tolerance. Yet all 12 nonzero loading/peak states fail the later teacher `rho_u <= 1e-3` screen; all six unload states pass it.

The early–middle–late checkpoints tell the same qualitative story. At the peak, the native stopping sums are `3.19299e-4` at c20, `3.61986e-4` at c60, `3.64307e-4` at c82, and `6.43088e-5` at c83. The corresponding teacher `rho_u` values are `0.71750`, `1.28578`, `1.35335`, and `0.04133`. Thus the disagreement is already present in the early state, persists in the middle and late states, and decreases sharply at the transition state without passing the teacher gate.

For these 18 residual directions, the accepted-pair raw UV norm is amplified by approximately 4.17e3–4.44e3 when expressed as the frozen mass-dual teacher metric. The sampled factor is similar across early, middle, and late states, so the large teacher numbers are primarily a consequence of the evaluation norm and scale, while the cycle-to-cycle variation still reflects the accepted residual vector. This factor depends on the residual's spatial distribution over nodal masses and is not a universal conversion.

Verdict: the apparent contradiction is a criterion mismatch, not evidence that Stage0b skipped its post-damage UV residual check. The native solver certifies `raw UV L2 + phase residual <= 4e-4`; the later audit asks a substantially stricter and spatially weighted question. Consequently:

- the Stage0b fields pass the reconstructed original acceptance expression for the 18 audited states;
- they are not equilibrium-qualified teachers under the later mass-dual `rho_u <= 1e-3` contract;
- neither statement is a true-solution or mesh-convergence claim;
- the remaining residual cannot yet be attributed quantitatively to the last damage update because genuine last-iteration intermediate fields were not archived.

The external review also fixed the remaining field semantics. `producer_metadata.equilibrium_residual` is the preceding UV Newton scalar, not the accepted-pair residual. `native_phase_residual` is the scalar returned by the phase-field Newton solve before the producer applies nodal damage bounds; it is neither a projected accepted-pair residual nor the E010 hard-KKT L2. `native_stagger_sum` is therefore a posterior reconstruction of the source-level expression, not an independently archived final scalar.

For the PINN/FEM reproduction objective, freeze two separate routes before model comparison:

1. Primary strict-physics route: create a **fixed accepted damage / frozen fatigue UV-rebalanced derived reference field**. Do not label it a qualified FEM teacher unless all other gates pass.
2. Secondary native-fidelity baseline: test whether PIDL reaches the original FEM output accuracy using the native acceptance contract plus preregistered displacement and damage field metrics.

The two routes answer different questions; “either route passes” is not a valid success rule. The minimum next pilot is UV-only polish at `c82s4` and `c83s4`, with a read-only `c82s5` passing control, under the frozen contract recorded in [the evidence review](evidence_review.md).
