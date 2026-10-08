# S04 — PIDL/FEM mechanism closure

## 2026-10-05 claim impact: S04-E002-R003

The FEM c83 peak is nonstationary for the frozen projected PIDL413 objective (UV .04133148; box-damage .17479701; frozen screen1e-3). This narrows the interpretation of future supervised-to-physics departure; it cannot establish optimizer failure alone. History incompatibility is present, but cannot uniquely explain the total mismatch, especially the history-independent fixed-field UV residual. This supports a one-state counterfactual diagnostic only, not FEM invalidity, PINN incapacity, trajectory closure or a manuscript-level reproduction claim. Next gate: same-field weak-form/energy-gradient consistency and qualified FEM predecessor. Evidence: [S04-E002 decision](S04-E002/cross_residual_result.md).

## 2026-10-05 claim impact: S04-E003-R001

Original archived FEM free-UV weak residual and PIDL energy derivative agree (scaled vector difference1.108e-11, gate1e-9). The same rho_u .04133148 is present in both. Qualified FEM prior damage eliminates the cross-trajectory healing penalty; with both FEM histories, common-free damage box residual remains .058074. Frozen trial-coefficient damage gradient also agrees with the original weak residual at this inactive-penalty state (diagnostic). This excludes a same-field UV operator mismatch and narrows, but does not close, history attribution. Correct E002 predecessor unavailability: v1/native_q4 was missed, not absent. Next gate is teacher accuracy under a common residual/field contract; no training or trajectory claim. [Decision](S04-E003/decision.md).

## 2026-10-05 claim impact: S04-E006 teacher UV precision

FEM-seeded fixed-FEM-damage equilibrium reduces rho_u .04133148 to4.396e-11 with RMS UV correction/Us9.659e-6 and active relativeL2 correction0.06357%. Thus screen failure alone did not require large corrections in these norms for c83. Common-free damage stays .05807453; full coupled teacher remains unqualified. Next gate is phase/clipping/fatigue endpoint damage certification, not more UV precision or immediate training. Scoped evidence reviewPASS. [Decision](S04-E006/decision.md). Cross-cycle E005 is independently running.

## 2026-10-05 — hard-irreversibility interpretation corrected (S04-E007)

c76/c82/c83 native FEM endpoints pass the pre-frozen4e-4 nodal hard-KKT migration screen; their box-screen failures remain valid for the different feasible set. Original UV screens still fail and full teacher remains NOT_QUALIFIED. Follow-up E008 measures c76/c82 fixed-damage UV corrections; early/mid and within-cycle missing prior/oracle cannot be substituted by late peaks. See S04-E007/decision.md.

### 2026-10-05 — S04-E008 conditional UV precision, late peaks

Condor65 exit0, numerical a741da7,29tests PASS; c76/c82 fixed-damage UV solves4iterations each, rho_u≈4.7e-11. Active-driver relativeL2 corrections7.86%/18.56%, original-p99 9.33%/19.64%; c83 existing E006 much smaller. Only these three peaks show increase then decrease; no early-stage trend or causality claim. Hard KKT migration passes before/after, box fails, damage residuals increase slightly. Full teacher NOT_QUALIFIED. Evidence review PASS on supplied results; archived-array norm checks agree. [Decision](S04-E008/decision.md). Missing early/internal assets remain next gate, no new training.

### 2026-10-05 — S04-E009 restored early peaks

Original c20/c40 accepted fields fail the unchanged free-UV screen (rho_u0.7175/1.1879). Fixed-damage re-equilibration gives4.95e-11/4.87e-11, with active-driver corrections3.14%/9.02%. This excludes an exclusively late origin in sampled states, but does not locate onset or establish monotonicity. Own FEM priors and original MATLAB vectors admitted; separate replay lineage preserved. Hard-KKT passes, box fails; full teacher NOT_QUALIFIED. Evidence PASS on supplied records. [Decision](S04-E009/decision.md).

### 2026-10-05 — S04-E010 phase-resolved teacher residuals

One sealedStage0b trajectory, sixcycles20/40/60/76/82/83 ×s2/s4/s5, eachownacceptedprior. All18identity/operator/strictfeasibility pass;5archivedMATLAB bridges and13reconstructed-only labels retained. Original loading/peakUV fails alreadyatc20, allunloadUV passes, peakUVnonmonotonic. AllhardKKTmigration screensPASS versus allboxFAIL; different constraints/scales, no teacherpromotion. Condor67exit0,33testsPASS,archivednormsreproduced. EvidencePASS. [Decision](S04-E010/decision.md). Nextread-only gate: accepted-endpoint stopping semantics, no longrerun/training.

### 2026-10-06 — S04-E011 native stopping contract versus teacher gate

Hash-matched original Stage0b source reassembles UV equilibrium after the damage update and accepts on raw free-UV L2 plus the returned phase-Newton scalar at `4e-4`. Reusing the18E010 accepted-state vectors, all18 pass that reconstructed native expression, while all12 loading/peak states fail the later mass-dual `rho_u<=1e-3` teacher gate. Earlyc20, middlec60, latec82, and transitionc83 show the same contract mismatch; `rho_u/raw_uv_l2` is about4.17e3–4.44e3 for these sampled directions, not a universal conversion. The phase scalar precedes damage bounds and is not the E010 hard-KKT residual; the final native sum is posterior-reconstructed rather than separately archived. This resolves the apparent `converged=true` contradiction without granting teacher qualification. Quantitative attribution to the last damage change remains unavailable. Future mechanism checks default to early–middle–late plus within-cycle phase coverage. Independent evidence reviewPASS. Next: primary fixed-damage/frozen-fatigue UV-rebalanced derived-reference pilot at c82s4/c83s4 with read-only c82s5 control; keep native-fidelity as a separate secondary baseline. [Decision](S04-E011/decision.md), [review](S04-E011/evidence_review.md).

### 2026-10-08 — S04-E012 conditional UV-derived-reference adoption

The reviewed read-only runner independently reassembled the locked original and existing UV-rebalanced c82s4/c83s4 fields. Original `rho_u` values `1.3533453` and `0.04133148` fail; polished values `4.58098e-11` and `4.39641e-11` pass. All 596 essential UV values have zero error, fixed damage passes, and c83 prior/target/fatigue/strict-feasibility identity passes. c82 hard-KKT remains parent-reported, c83 hard-KKT is recomputed from locked inputs, and c82s5 remains a parent-JSON-only unloading control. Active-driver changes differ strongly: `18.5616%` at c82s4 versus `0.063566%` at c83s4, so the correction is state dependent and is not a universal late-stage escalation rule. Code Ready and Evidence review both PASS. Register c82s4/c83s4 only as fixed-damage/frozen-fatigue UV-rebalanced derived references; polished native phase/joint acceptance is not evaluated and `full_teacher=NOT_QUALIFIED`. Future checks retain the early–middle–late plus s2/s4/s5 default; E012 itself samples only two late states and one unloading control. [Decision](S04-E012/decision.md), [metrics](S04-E012/metrics.csv), [review](S04-E012/evidence_review.md).
