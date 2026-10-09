# S09-E003 physics probe decision — 2026-10-09

## Purpose and completed action

Check the actual FEM physics and execute the smallest physics-only PINN diagnostic before adding residual losses to S09's element-mean graph operator. Implemented native AMOR equilibrium, AT1 penalty and immutable trial fatigue; only equilibrium enters this run. Source/GP identity and derivative checks passed independent review.

## Producer results (retrieval verified; independent Evidence Ready PASS)

S09-E003-R001 on Taobo GPUServer8 GPU7, commit2bfa5d3, seed1,500 Adam updates, about14s, peak torch allocation383MB, exit0. Native input hash verified; clean release. Small snapshot release omitted unrelated Git blobs; preparation printed a missing excluded-blob warning, then all materialized release files were verified against HEAD and clean status confirmed before launch. This was not a failed training run.

Final free-force RMS9.05643900099e-6 / affine3.22454705270e-5 = **.280859260323**; <=.8 operational gate PASS,71.914% reduction. Native reference force RMS5.80416587456e-7, so final PINN remains15.603343 times the native residual. Final unweighted nodal-vector displacement relativeL2 to native **1.0090928467**. Best equals final; no best-checkpoint rescue.

## Interpretation

The FEM-aligned differentiable equilibrium loss and neural optimization path run successfully and lower the chosen residual. That is the declared C0 capability conclusion only. The high displacement discrepancy and remaining force imbalance do NOT support accurate reconstruction or equilibrium convergence. Residual reduction relative to an easy affine initial condition cannot stand in for field accuracy. Eta0 and localized damage imply a demanding conditioning problem, but this experiment does not identify the unique cause of the discrepancy.

No damage transition was learned. Damage is fixed; there is no phase/fatigue solve, no heldout trajectory, no autonomous rollout, no PINO superiority. Native FEM itself remains an unqualified full teacher. Existing E001/E002 negative decisions remain unchanged.

## Next useful move

Use this verified AMOR/Q4 residual as a reusable physics module. For the actual operator comparison, first provide native nodal u,d outputs and FE mappings; jointly supervise fields and add equilibrium as a controlled loss term with matched data-only baseline. The next comparison should evaluate both declared field accuracy and physics diagnostics on a complete development trajectory. AT1/fatigue terms require an accurately bound old substep state and trial/commit contract. Do not solve the present discrepancy by declaring the20% optimization gate a physical tolerance or by silently changing S09 fields.


## Visual inspection

All13 producer output/log/receipt files retrieved and sizes match; remote archive copies verified. Final field force RMS exactly reproduces the reported metric. Full-domain plots show a smooth PINN displacement transition versus a sharply localized native opening; this is descriptive evidence of field mismatch, not proof of a unique optimization/architecture cause. Raw assembled force RMS depends on this mesh/discretization; no mesh-invariant physical tolerance is claimed.


## Independent evidence review and Storyline impact

2026-10-09 Evidence Ready PASS: reassembled force max difference2.10e-17, checkpoint/final-u max difference2.78e-17, hard-BC error0, fixed damage unchanged,21 finite evaluations, all13 files verified. S09 gains a source-checked differentiable AMOR/Q4 physics module and a completed single-state PINN capability probe. It does not yet gain a trained physics-informed operator or damage-prediction evidence.
