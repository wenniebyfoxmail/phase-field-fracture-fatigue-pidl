# U0.12 saved-state gradient-vector diagnostic

Owner: chat01a15f55-6b92-7cd2-9122-de9ae13176d7; continuation of the standard
loss-component question, separate from running L2 solve pairs in chat01a15fbd.
Question: cancellation of dissipation/irreversibility gradients, net gradient,
same-point L2 coordinate sign changes, and unpenalized energy direction.
Stage: retrospective diagnostic, one existing synthetic trajectory; no optimizer,
history or FEM updates. Eleven archived final states, preceding-step histories.

Executed reviewed code d03bd4e026467fd8021135bd01a03c9533a21d7d on gpu-taobo,
GPUServer8 GPU0 RTX4090, torch2.7.0+cu126; dispatcher1427282,
2026-10-21T18:52:02Z, exit0, worker19.398s. Two preceding zero-start failures
(metadata binding, device placement) are preserved, neither produced gradients.
All11 energy triplets exactly reproduce the original archive.

c82 peak: cos(gd,gh)=-.999945698; pair norm9.97239, direct net4.90366;
L2 norm.00121365,2592 nonzero coordinates reverse (.23036% of1125211),
115333 zero coordinates activate (10.24990%). c88 peak: pair norm4.09124,
net3.18092; cos(unpenalized physical gradient,total)=-.921253.
The local negative-total-gradient direction at c88 raises unpenalized
elastic-plus-fracture energy while lowering penalty. This is a constraint/
energy competition diagnostic, not proof of physical error or finite-step bias.
Actual archived adaptive RPROP steps cannot be reconstructed without optimizer
state. Independent code review and two-state raw-vector evidence recomputation
completed; no claim of equilibrium, teacher validity or full-trajectory effect.

Local analysis, CSV, figure, reviews and receipts:
`/Users/wenxiaofang/.codex/visualizations/2026/10/21/01a15f55-6b92-7cd2-9122-de9ae13176d7/pidl_u012_gradient_vectors/`.
Complete compact metrics retrieved for11 states; raw seven-vector arrays for
steps409/439 retrieved and size/finite checked. Nine others remain remote:
`/mnt/data2/drtao/pidl_archives/pf_u012_gradient_cancellation_d03bd4e0_20261021/results`.
Decision: retain the distinction between scalar loss, vector balance and RPROP
updates; use the separately authorised matched L2 solves to assess finite-path
influence, rather than discarding regularization or irreversibility from norms.
