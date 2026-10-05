# A1 stop result — 2026-10-05

S04-E004 did not enter solver qualification or the Hard-5 direct-Q4 path. Its mandatory S04-E003 cheaper diagnostic passed the implementation-equivalence gate but failed the frozen endpoint-stationarity gate.

- Native MATLAB, independent NumPy-Q4, and Torch/PIDL free-UV residual vectors agree: scaled difference `1.10760485e-11` versus threshold `1e-9`.
- The damage-gradient comparison on the common diagnostic field has scaled difference `1.28459609e-13`.
- On the lineage-qualified FEM c83 s4 state with trial fatigue rebuilt from the immutable accepted predecessor: `rho_u=0.04133148` and all-node constrained `rho_d=0.06534478`; both exceed the frozen `1e-3` stationarity screen.

Verdict: `A1_TRIAL_F_REJECTED`. The direct sparse Q4 solve is therefore not an admissible optimizer discriminator for this endpoint definition. No producer solve was launched and no accepted state was committed. The remaining difference is now localized beyond mesh/GP/gradient implementation, at endpoint state timing, outer-stagger closure, or formulation semantics. This does not by itself invalidate FEM or prove PINN incapacity.

Local evidence:

- `local_archive/experiments/S04-E003/runs/S04-E003-R001/retrieved/output/audit/summary.json`, SHA-256 `d0da8ffc42c08bc18bfeebd57f20294332de14335438193164b3e23f1bfbf8ba`.
- `local_archive/experiments/S04-E003/runs/S04-E003-R001/retrieved/output/audit/history_controls.csv`, SHA-256 `b4be7bd5f6702965ae19ae269cd1b79d742ed031fab2f931c58def4ca1348e1f`.
- `local_archive/experiments/S04-E004/a1_negative_receipt.json`, SHA-256 `da75aa587b731b3f42d49993cf49212123c0a39323742372dcd595323ad58193`.

The independent exact-commit review of `14112e5` also blocked producer staging because endpoint `rho_d` was not re-certified after the final `(u,f)` refresh, canonical A0 input identities and separate FEM/PIDL seed arms were incomplete, and partial accepted-state/run-receipt output was insufficient. These tooling blockers remain recorded, but A1 already stops scientific execution.
