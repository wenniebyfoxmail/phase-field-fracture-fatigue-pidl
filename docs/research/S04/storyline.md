# S04 — PIDL/FEM mechanism closure

## 2026-10-05 claim impact: S04-E002-R003

The FEM c83 peak is nonstationary for the frozen projected PIDL413 objective (UV .04133148; box-damage .17479701; frozen screen1e-3). This narrows the interpretation of future supervised-to-physics departure; it cannot establish optimizer failure alone. History incompatibility is present, but cannot uniquely explain the total mismatch, especially the history-independent fixed-field UV residual. This supports a one-state counterfactual diagnostic only, not FEM invalidity, PINN incapacity, trajectory closure or a manuscript-level reproduction claim. Next gate: same-field weak-form/energy-gradient consistency and qualified FEM predecessor. Evidence: [S04-E002 decision](S04-E002/cross_residual_result.md).

## 2026-10-05 claim impact: S04-E003-R001

Original archived FEM free-UV weak residual and PIDL energy derivative agree (scaled vector difference1.108e-11, gate1e-9). The same rho_u .04133148 is present in both. Qualified FEM prior damage eliminates the cross-trajectory healing penalty; with both FEM histories, common-free damage box residual remains .058074. Frozen trial-coefficient damage gradient also agrees with the original weak residual at this inactive-penalty state (diagnostic). This excludes a same-field UV operator mismatch and narrows, but does not close, history attribution. Correct E002 predecessor unavailability: v1/native_q4 was missed, not absent. Next gate is teacher accuracy under a common residual/field contract; no training or trajectory claim. [Decision](S04-E003/decision.md).
