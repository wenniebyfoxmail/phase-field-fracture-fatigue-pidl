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

**Tip-local net: 在固定 S1 crack-tip refined mesh 上，local correction head 是否能恢复 FEM-like crack-tip fatigue-history / phase-field localization，而不改物理 loss？**

## Active Branches

1. **Tip-local correction network** — Global NN + compact local head near current initial tip `(0,0)`, integrated at raw field output before existing BC/alpha constraints. Physical loss unchanged. First branch: `codex/exp/tip-local-net`.
2. **S1 static process-zone oversampling baseline** — Use fixed S1 mesh (`r_tip=0.05`, `n_refine_passes=1`) as the comparator/isolation mesh. Do not use dynamic S2/v4 during the first test.
3. **FEM field reference** — Treat FEM `psi` sanity checks as reference-quality for field localization, but do not overclaim exact crack-tip peak values.

## Current Best Bet

Representation, not remeshing, is now the main bottleneck. Keep the Carrara/PIDL loss fixed and add a small tip-local approximation space so the global net can remain smooth while the local head carries the sharp process zone.

## Best Next Discriminator

Run `Umax=0.12`, seed 1, S1 fixed mesh, `N=20` smoke. If stable, extend to `N=40`. Compare alpha line profile, process-zone `psi/alpha_bar`, localization width, crack-tip trajectory, far-field `psi`, and absence of far-side spurious damage.

## Switch Condition

If tip-local net is stable but does not improve localization metrics over S1, the failure is likely not just global spectral/representation capacity; return to mesh/history/conditioning diagnostics. If it destabilizes Kt or creates far-side damage, constrain or shrink the local head/window before broadening experiments.

## Parking Lot

- Dynamic S2/v4 remesh with local net (only after fixed S1 representation test)
- Adaptive `lambda_hist` as diagnostic only, not main method
- Wider local window / multi-head local net
- PCC Phase 2 calibration thread (separate from this branch)

## Recently Closed / Triggered

- **2026-05-23 handoff**: FEM `psi` sanity checks passed; S1/S2/v3.2/v4/adaptive-`lambda_hist` reviewed. Decision: try local crack-tip correction network first on fixed S1 mesh.
- **S1 static oversampling**: Early `alpha_bar_max` lifted but long-horizon field localization remained modest/seed-sensitive.
- **S2/v4 dynamic/add-only refinement**: Mesh-side fixes reduce transport disturbance but do not change NN approximation space.
