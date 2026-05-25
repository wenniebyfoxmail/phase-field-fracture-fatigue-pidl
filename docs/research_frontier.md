# Research Frontier

**规则**：此文件是"一屏决策前线"，不是历史日志。
- 总长度 ≤ 50 行（不含本 header）
- Active Branches ≤ 3 个
- Current Question 只能 1 个
- 关闭的分支移到 `shared_research_log.md`，不留在这里
- 如果本 session 改变了主问题，重写前两节

**Owner**: Mac-PIDL | **Update**: 每个 Mac research session 结束时

---

## Current Question

**Moving tip-local net: local correction window 跟随上一圈 alpha-tip 后，是否能恢复 FEM-like crack-tip fatigue-history / phase-field localization，而不改物理 loss？**

## Active Branches

1. **Moving tip-local correction network** — Global NN + compact local head whose window is moved to the previous cycle's alpha-tip before the next fit. Integrated at raw field output before existing BC/alpha constraints. Physical loss unchanged. Branch: `codex/exp/tip-local-net`.
2. **S1 static process-zone oversampling baseline** — Use fixed S1 mesh (`r_tip=0.05`, `n_refine_passes=1`) as the comparator/isolation mesh. The first moving-window test still keeps S1 fixed to isolate representation from remeshing.
3. **FEM field reference** — Treat FEM `psi` sanity checks as reference-quality for field localization, but do not overclaim exact crack-tip peak values.

## Current Best Bet

The static local head was centered at `(0,0)` while the crack tip moved to `x≈0.16` by cycle 40 and `x≈0.36` by cycle 70, so the local branch saw tiny gradients. Move the window first; only combine with S2/v4 if the moving head helps but mesh density becomes the next limiter.

## Best Next Discriminator

Run `Umax=0.12`, seed 1, S1 fixed mesh, moving window, `N=20` smoke. If stable, extend to `N=40`. Compare `tip_net` vs `global_net` gradient split, alpha line profile, process-zone `psi/alpha_bar`, localization width, crack-tip trajectory, far-field `psi`, and absence of far-side spurious damage.

## Switch Condition

If tip-local net is stable but does not improve localization metrics over S1, the failure is likely not just global spectral/representation capacity; return to mesh/history/conditioning diagnostics. If it destabilizes Kt or creates far-side damage, constrain or shrink the local head/window before broadening experiments.

## Parking Lot

- Dynamic S2/v4 remesh with local net (only after fixed S1 representation test)
- Adaptive `lambda_hist` as diagnostic only, not main method
- Wider local window / multi-head local net
- PCC Phase 2 calibration thread (separate from this branch)

## Recently Closed / Triggered

- **2026-05-23 handoff**: FEM `psi` sanity checks passed; S1/S2/v3.2/v4/adaptive-`lambda_hist` reviewed. Decision: try local crack-tip correction network first on fixed S1 mesh.
- **2026-05-25 diagnostic**: Static window was off-tip after early propagation; code now defaults `run_tip_local_net_S1_umax.py` to moving-window mode with `_followTip` archive tag and logs `tip_local_window_{x,y}_vs_cycle.npy`.
- **S1 static oversampling**: Early `alpha_bar_max` lifted but long-horizon field localization remained modest/seed-sensitive.
- **S2/v4 dynamic/add-only refinement**: Mesh-side fixes reduce transport disturbance but do not change NN approximation space.
