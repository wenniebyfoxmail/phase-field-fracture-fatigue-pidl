# D0 streaming implementation amendment — no scientific-design change

Owner S04-E016. Previous R001 remains RSS_CAP / scientific INCONCLUSIVE.
User2026-10-14 approves one fresh B0/B1 after equivalence, memory and independent
exact-code review. Fresh Run S04-E016-D0-R002; Mac CPU4/noGPU, combined fit and
renderer300s/2GiB/100MiB, stop without retry. Sources/feature SHA and paired lock
cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c unchanged.

Preserved: four whole-Umax outer/inner grouping, all357 admitted cycles,
2048 geometry-only fit cells/cycle, full85112-cell heldout scoring, native area
weights, equal case/three fixed cycle strata, training-PIN-only h/r weighted
means, training-only X/Delta standardizers/std<1e-12=>1, alpha .01/1/100,
unpenalized intercept, inner minimax-MSE-ratio selection/exact tie=>larger alpha,
float64 target/error arithmetic, no clipping. Same targets, metrics, examples
and figures. No foreground/background q99 weighting, Q4-edge graph, new history,
active/f output, NN, physics claim or confirmation access.

Engineering-only change: regenerate one cycle's sampled X/Y/weights per pass.
First pass uses stable centered weighted batch moments + Welford/merge, not
E[x²]-mean²; second pass accumulates normalized33x33 Gram /33x3 cross matrix.
No all-cycle feature/label/weight concatenation in production. Old dense code is
available only as frozen-commit test oracle. Run IDs/receipt/figure labels advance
toR002; original R001 artifacts remain unchanged.

Pre-result numerical check tolerances: statistics/Gram rtol1e-9,atol1e-11;
coefficients rtol1e-7,atol1e-9; toy predictions/errors rtol1e-8,atol1e-9.
All three alpha coefficients, signed values, constant/near-floor columns,
unequal weights/strata and full toy nested selection must agree. Non-tied toy
selection must match; exact-tie larger-alpha rule tested separately. This is
floating-point equivalence, not bitwise identity or scientific success.

Memory check: independent bounded process reads approved input files and builds
one current full-field feature matrix, plus synthetic max2048x32 cycle blocks
for streamed numerical accumulation. No actual model/scoring in that check.
Record sampled RSS and analytic owned-array sizes; neither guarantees allocator
behavior of the whole real pipeline, which remains guarded at the original cap.
Engineering checks are not experimental arms and do not consume/produce scientific
fit results. Stop if checks disagree or memory evidence is inadequate.

Documentation authority: archive split verdict supersedes old pairing-HOLD only
for imitation; terminal receipt supersedes historical NOT STARTED. The frozen
lock's candidate/pending strings are historical and must not be edited to change
its identity. Teacher/physics/Contract A remain HOLD. S03 optical and S04 simulation
states remain separate. No finite-rotation, mesh-independence or feedback closure.

## Interface corrections (not new options)

| Item | Actual admitted D0 | Old-method candidate, NOT activated |
|---|---|---|
| locality | current geometry9NN including self, equal neighbor mean | Q4 edge graph/two-hop halo |
| global PIN summary | area mean of each transformed current channel | std/q90/q99 |
| h/r | training PIN weighted mean | median raw scale / fixed history0.5 |
| conditions | x,y,log area,Umax,physical integer cycle | separate load-factor,c/100 |
| local weighting | admitted-domain area weights | q99 foreground/background balancing |
| outputs | d/alpha_bar/direct raw only | f/active auxiliary output,H |

All input fields are current/c-1/c-2 s4 post-history; alpha_bar is accumulated
fatigue history, not H. damage is current signed coordinate, not hist_alpha.
Missing C0 remains absent with lag masks. active_proxy is PIN-only mean-parent
auxiliary, not native joint active or physical degradation closure. FEM reductions
are mean four nodal d /native GP history and raw; source values are float32,
target/error arithmetic float64. No SI unit mapping is asserted. Original source
geometry/native-support, nominal-amplitude difference and signed-input caveats
remain. Frozen lock pending-status strings are not current execution status.
