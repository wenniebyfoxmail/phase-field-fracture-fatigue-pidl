# S09 claim impact — 2026-10-08

Experiment S09-E001 / frozen v0.2 / code f58df2d. R002 execution succeeded; independent Evidence Ready PASS; P1 bounded 16-window fit criterion FAIL (best0.997986 vs <=0.80,1000 updates). R001 failed before training and has no scientific result.

Claim added: the reduced continuous-kernel graph operator executes on86408 elements under the measured GPU budget. No evidence yet of useful crack-growth learning. Existing historical Hard5 verdicts unchanged; P2/PINO pending. Full experiment remains open for diagnosis, not closed as prediction validation.

Decision and evidence: [P1 decision](S09-E001/P1_decision_20261008.md). Next is fixed-checkpoint forward diagnosis, then a separately frozen minimal intervention if warranted.

R003 update: fixed-checkpoint diagnosis verified. Aggregate undergrowth plus broader weak activation, not a metric implementation mismatch; P1 negative unchanged. No causal loss/projection conclusion. Next damage-only loss ablation planned, unexecuted.

S09-E002: frozen damage-only single-factor ablation completed and closed, independent evidence PASS; fit target FAIL(best0.9900616 vs<=0.8). Auxiliary supervision removal alone insufficient in this setup. No inference of zero auxiliary effect or method-class failure. Mapping/name boundary recorded in operator_mapping_20261008.md; current model remains data-only graph operator, not PINO.


## 2026-10-09 — S09-E003 FEM physics / PINN diagnostic

Implemented and independently checked native AMOR equilibrium, AT1 penalty partial residual and immutable trial fatigue. U012c76s4 native kinematics/energy reproduced at float64 precision. Ran500-step fixed-damage equilibrium-only displacement PINN on Taobo; final residual/affine=.280859 (C0 PASS), but nodal displacement relative difference1.00909 and force15.6times native preclude accuracy claims. All13files retrieved; independent Evidence Ready PASS; exact run commit2bfa5d3. See S09-E003/decision.md. No damage forecast, physics-informed operator training or generalization established.

## 2026-10-11/12 — S09-E005 multi-objective gradient audit

At E004's exact common checkpoint, zero-update audit found a global
physics/data gradient norm ratio of 10,165–57,338 with positive cosine on all
16 states.  Decoder conflict occurred on 6/16 states, but the observed FEM
target residual was small (median 0.0199 times affine).  The nominal E004
weight therefore remained strongly physics-dominant in gradient space.  This
supports a fresh gradient-balanced, data-anchored S09-E006 test; it does not
rescue E004 or establish successful PINO training.

## 2026-10-12 — S09-E006 gradient-balanced Pareto rescue

The exact data-only replay passed.  From the common E004 checkpoint and frozen
700-state sequence, the `beta=0.25` projected gradient-balanced arm reduced the
mean development force residual to 39.68% of data-only while every state's
displacement error remained within 109.70% of data-only, passing the frozen
50%/110% conjunction.  `beta=1.0` reduced residual farther but failed the
displacement guard.  Independent Evidence Ready review passed after raw-row
recomputation.  This is a positive fixed-damage development optimisation
result; it is not exact equilibrium, damage evolution, independent
generalisation or road evidence.
