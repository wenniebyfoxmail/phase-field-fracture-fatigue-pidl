# Windows GRIPHFiTH Request 27: U0.13 c5 GP/stagger probe

请把这份说明交给 Windows-FEM / GRIPHFiTH agent。该任务是一个最小诊断
导出，不是新的参数扫描，也不授权 PIDL 训练。

## 一句话目标

在不改变 Hard5 U0.13 物理设置的前提下，fresh replay 到 cycle 5，导出
c5 每个载荷子步以及 peak 子步每个 stagger iteration 的 Gauss-point
driver/history/residual 状态，从而定位为什么 GRIPHFiTH c5 active raw-`psi`
峰值为 `1.2301`，而 Mac Ferrite adapter 只有约 `0.45--0.47`。

## 背景与现有结论

Mac 端已经完成以下检查：

- U0.13 c1--c4 raw-`psi` field 通过锁定门槛；只在 c5 失败。
- c5 damage、`alpha_bar`、fatigue `f` 和高值 support 仍接近。
- GRIPHFiTH 与 Ferrite 都在 load-step stagger convergence 后更新 cycle
  peak，并对每个 Q4 单元的四个 GP 取平均；不是 peak/unload label swap。
- AMOR、AT1 history fatigue、`R=0` 五步 schedule、plane strain、`eta=0`
  和疲劳更新公式已经源码核对。
- 把 Ferrite displacement Newton tolerance 从 `4e-4` 收紧到 GRIPHFiTH
  的 `1e-6` 后仍失败：c5 relative L2 `0.3731`，correlation `0.8931`，
  peak `0.4494`，参考 peak `1.2301`。

因此现在只需要检查 c5 nonlinear branch / tangent / state coupling，不要
再改 tolerance、参数、mesh 或 acceptance gate。

## 五问 experiment gate

1. **Mechanism question**：两套实现从 c5 的哪一个 substep/stagger 开始在
   converged `u,d,psi_raw,H,alpha_bar` 或 residual 上分叉？
2. **Claim consequence**：找到第一个分叉状态后，才能设计一个单因素代码
   修复；如果 GRIPHFiTH fresh replay 不能复现原 c5 field，则先判定 reference
   provenance/reproducibility blocker。无论结果如何，本任务不直接通过 Q1。
3. **Cheaper diagnostic**：Mac 已完成现有 cycle field、peak/unload、源码顺序
   和 tolerance 检查；现有 archive 没有 per-stagger GP fields，因此需要这次
   Windows state export。
4. **Minimal asset**：一个小型 c5 state package、两个 index CSV、一个
   reproduction-audit CSV 和 README；不要导出完整长轨迹。
5. **Registry path**：完成后在 `docs/handovers/windows_fem_outbox.md` 回复
   Request 27，Mac 再更新主 experiment inventory。

GPT Pro 在当前 Mac 会话不可用；本请求沿用已经锁定的 Q1 门槛，只做状态
instrumentation，不设计新阈值或新物理分支。

## 固定输入：不得改变

以现有 U0.13 canonical Hard5 case 为唯一 reference：

```text
OneDrive/.../griphfith/Hard5_eta0_5step_Umax_011_012_013_20260729/
  u013/SENS_hard5_u013_eta0_canonical_v1/
```

如 Windows 路径不同，请按文件夹名搜索。应保持：

```text
fresh hard-recovery state0 from the same canonical driver
same 86,408-cell native Q4 mesh and node/element ordering
E=1, nu=0.3, Gc=0.01, ell=0.01
alpha_T=0.5, p=2, res_stiff/eta=0
plane strain, AMOR, AT1_HISTORY_FATIGUE
Umax=0.13, R=0
retained load factors approximately [0.25, 0.50, 0.75, 1.00, 0.00]
tol_displ=1e-6, tol_p_field=4e-4, staggered tol=4e-4
line_search=false, regularize_pf_newton=true
```

将 `max_cycle` 临时限制为 5，只用于缩短 fresh diagnostic replay。不要从
现有 cycle-62 checkpoint 倒退，不要覆盖 canonical directory，不要重编译或
修改 AMOR/AT1 MEX physics。

## Fresh output identity

建议输出到：

```text
C:/Users/xw436/Downloads/_pidl_handoff_v2/
  hard5_u013_c5_gp_stagger_probe_20260730/
```

并同步一份到 OneDrive 的同名文件夹。运行目录名称必须是新的，例如：

```text
SENS_hard5_u013_eta0_c5_gp_stagger_probe_v1
```

## 必须导出的状态

### A. 一次性 mesh/quadrature 信息

写入 `mesh_and_quadrature.mat`：

```text
node_coords
connectivity                 # exact Q4 element order
element_material_id
quadrature.Nxi
quadrature.dNdxi
quadrature.gauss_W
num_elem, num_node, num_gauss_pts
```

### B. committed anchors

至少导出：

```text
c4_unload_post_commit
c5_step1_post_commit
c5_step2_post_commit
c5_step3_post_commit
c5_peak_step4_post_commit
c5_unload_step5_post_commit
```

每个状态保存：

```text
cycle, substep, load_factor, imposed_uy
displ                         # full nodal vector, preserve GRIPHFiTH ordering
p_field                       # nodal damage
psi_raw_gp                    # num_elem x 4; converged post-phase recomputation
psi_cyclemax_gp               # running max over committed substeps in this cycle
history_H_gp                  # history_vars_old(:,:,1) after commit
alpha_bar_gp                  # history_vars_old(:,:,2) after commit
psi_eff_prev_gp               # history_vars_old(:,:,3) after commit
f_alpha_gp                    # history_vars_old(:,:,4) after commit
d_gp                          # Nxi interpolation of p_field, num_elem x 4
g_gp                          # (1-d_gp)^2 + res_stiff
stagger_iterations
final_residual_u_post_phase
final_residual_phi
final_residual_sum
```

如果方便，请同时保存 `strain_gp` 或至少 `trace_strain_gp`；这可直接检查
AMOR positive/negative branch。若需要修改 MEX 才能导出 strain，请不要为了
它改 MEX，`displ + mesh/quadrature + psi_raw_gp` 已是最低充分集合。

### C. c5 peak step 4 的 stagger trace

只对 `cycle=5, substep=4`，每个 stagger iteration 分三个时刻记录：

1. `after_u_before_phase`
2. `after_phase_before_post_iter`
3. `after_post_iter_recompute`

每个 stagger 至少保存：

```text
stagger_index
displ
p_field_before_phase
p_field_after_phase
psi_raw_gp_after_u
psi_raw_gp_after_post_iter_recompute
history_vars_old_pre_step     # frozen committed input, save once or reference it
history_vars_new_after_phase  # H, alpha_bar, psi_eff, f at every GP
residual_u_after_u_newton
residual_phi_after_phase_newton
residual_u_after_post_iter
residual_sum_after_post_iter
stagger_converged
```

不要只导出 element means；本请求的关键就是保留 `num_elem x 4` GP 差异。
如果数组较大，可以每个 stagger 一个 `-v7.3` MAT，并用
`stagger_index.csv` 索引。

## 建议 package 结构

```text
hard5_u013_c5_gp_stagger_probe_20260730/
  README.md
  RUN_PROVENANCE.txt
  state_index.csv
  stagger_index.csv
  cycle_level_reproduction_audit.csv
  mesh_and_quadrature.mat
  anchors/
    c4_unload_post_commit.mat
    c5_step1_post_commit.mat
    ...
    c5_unload_step5_post_commit.mat
  c5_peak_stagger/
    stagger_001.mat
    ...
  source/
    main_*.m
    instrumented_solve_fatigue_fracture.m
    export/helper scripts
  run.log
  SHA256SUMS.txt
```

## Instrumentation 不得改变解

优先复制 `solve_fatigue_fracture.m` 为 run-local instrumented 版本，只增加
只读保存语句。不要把 probe 计算结果写回 `displ`、`p_field`、
`history_vars_old/new`、stiffness 或 residual。

必须保留未 instrumented canonical 文件的 hash，并在 README 写明新增 probe
插入在哪几个原有语句之间。

## 验收标准

1. Fresh run 完成 c1--c5，25 个 retained substeps 均收敛；没有继续跑 c6+。
2. Mesh/node/element ordering 与 canonical U0.13 完全一致。
3. 所有导出尺寸正确、有限、state label 唯一；GP 数必须为 4。
4. Instrumented run 的 cycle-level c1--c5 `d_elem/alpha_elem/f_elem/psi_elem`
   与现有 canonical `psi_fields/cycle_0001.mat` ... `cycle_0005.mat` 比较，并
   写入 `cycle_level_reproduction_audit.csv`。
5. 最关键的 non-perturbation gate：

   ```text
   mean(psi_raw_gp_c5_cyclemax, 2)
   ```

   必须与 canonical `cycle_0005.mat::psi_elem` 一致；目标 max-abs `<=1e-12`。
   如果不能达到，报告实测误差并停止机制解释，先排查 fresh-run provenance。
6. c5 peak post-commit 的 `mean(psi_raw_gp,2)`、cycle-maximum GP mean 和
   canonical `psi_elem` 必须分别命名，不能混为一个字段。
7. `RUN_PROVENANCE.txt` 记录 Windows commit/dirty status、MATLAB version、
   loaded MEX paths/hashes、driver/source hashes、command、开始/结束时间和
   runtime。
8. `SHA256SUMS.txt` 覆盖所有 MAT/CSV/source/log/README 文件。

## Stop rules

- 不修改 acceptance thresholds。
- 不跑 U0.11/U0.12，不跑长轨迹或 Request 26 sweep。
- 不启动 PIDL/network training。
- 如果 fresh U0.13 在 c5 之前不收敛，或 c1--c5 cycle fields 不能复现
  canonical reference，立即作为 blocker 回报，不要通过调 tolerance/physics
  强迫一致。

## 回传时请回答

1. Fresh instrumented run 是否复现 canonical c1--c5？
2. c5 的高 `psi_raw` 第一次出现在哪个 substep/stagger/timing point？
3. 峰值是来自 converged displacement、phase update 后的重分配，还是
   cycle-max accumulation？
4. 对应位置的 `d_gp, g_gp, H_gp, alpha_bar_gp, f_gp` 是什么？
5. 文件路径、总大小、SHA256 和是否已同步 OneDrive。
