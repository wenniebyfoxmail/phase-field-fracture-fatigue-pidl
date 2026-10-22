# S04-E038 — RPROP cap without network L2

2026-10-22 prospective protocol r1. User directly authorizes smaller RPROP maximum,
zero L2, all other settings unchanged, focusing c1/c40 unloading. Owner: current
chat. Reuses E035 frozen-state runner and archived comparators; no default solver
change or trajectory run. Parent baseline/source provenance is in E035.

Hypothesis: coupled L2 partly masks sign-driven excessive coordinate movement;
a smaller maximum may suppress weight growth and added unloading damage. Competing
explanation: accumulated sign steps/nonconvex representation/termination remain
problematic even with a smaller maximum. Stability alone is not convergence.

One candidate maximum 0.001 (100 times initial 1e-5), replacing50; L2=0.
Minimum1e-10, etas(.5,1.2), fresh optimizer, 10000epochs, relative-loss tolerance
5e-7 for10 epochs, 240s per arm. Frozen c1 step5 and c40 step200 from ORIGINAL
regularized step4/199 networks and postcommit histories. U=0, standard fine mesh,
seed1, 8x400 TrainableReLU; physics, histories, recovery unchanged. No pretraining.
2 new arms, R001/R002. Reuse E035 matching L2=1e-5/max50 and zero/max50 outputs;
regularized E035 arms had exact original replay. Shared initialization must match.
No c83 claim, full rollout, cap sweep, or post-result adjustment is authorized here.

Operational ceiling: single GPU, <=1 GPUh; runner total780s, outer900s. Admission
zero-start failure may be diagnosed within2 attempts; scientific failure stops.
GPU rechecked before launch. Mac import/configuration only; GPU does solver work.

Report common physical energy Eel+Ed+Eirr, d/u/v, committed-history trial max(h,d),
new damage support, bounds/GP retreat, weight norm/max, iterations/time and ACTUAL
RPROP step sizes/cap fraction. Sample weights/step sizes first/every50/final by
read-only optimizer post-hook; retain existing same-vector gradient diagnostics.
No hypothesis is accepted solely from raw weight size or early-stop flag.
