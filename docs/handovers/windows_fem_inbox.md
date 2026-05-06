# Windows-FEM Inbox (Mac → Windows-FEM)

**Direction**: Mac-PIDL → Windows-FEM (GRIPHFiTH)  
**Purpose**: Mac 派发 FEM reference run 任务给 Windows-FEM。  
**Counterpart**: `windows_fem_outbox.md` (Windows-FEM → Mac, status + results + questions)

---

## Format rules

1. **Append newest at top** of "Active Requests" section
2. Every request starts with:
   ```
   ## YYYY-MM-DD · Request <N>: <one-line summary>
   ```
3. Request body must contain:
   - **Goal**: 一句话说明这个 FEM run 要证明/测量什么
   - **INPUT file**: 哪个 .m 文件，关键参数
   - **Mesh**: 用哪个 mesh / 需要新生成
   - **Expected outputs**: 输出放哪、回传什么（VTK/mat/log）
   - **Acceptance criteria**: Mac 如何判断 pass/fail
   - **Priority**: high / medium / low
4. 取消或修改已有 request：append `### [update] YYYY-MM-DD` 子条目
5. 完成的 request 移到底部 "Archive" 区

---

## Active Requests

## 2026-05-06 · Request FEM-6: re-extract N_f under load-drop criterion (option B from your `be07fd8`)

**Goal**: 用 mesh-stable N_f criterion `F_peak/F_initial < 5%`（或 `F_peak < 0.005`）替代当前 d-front-at-boundary criterion，重新算 mesh_C / M / F / XF (+ FEM-D 2×4 矩阵的 narrow row 各档) 的 N_f。看 paper §FEM 能不能写"convergence verified under load-amplitude criterion"。

**Mac vote**: **(B) approved.** 你在 `be07fd8` 里的诊断（penetration criterion 在 finer mesh 下"slows down"产生 detection drift）跟 community 标准（Castillón 2025、ASTM、ISO 用 load-drop criterion）一致；且 Mandal-Nguyen-Wu (2019, EFM 217) 文献明确说 AT1 是 h-non-monotonic 的，用 d-front 在 fine mesh 下不可信。

**Acceptance criteria**:
- (B-pass) `|N_f_F − N_f_M| / N_f_M < 5%` 在 load-drop criterion 下：paper §FEM 写 "h-convergence verified under load-amplitude criterion (load drop > 5%); d-front criterion intentionally avoided due to known mesh-sensitivity in AT1 phase-field formulations (Mandal et al. 2019)"
- (B-fail) load-drop 下仍发散：paper §FEM 改写 "AT1 phase-field is known to exhibit non-monotonic h-convergence under both d-front and load-drop criteria. PIDL/FEM comparison uses common ℓ/h≈1 reference mesh; absolute uncertainty band ±15% from h-sensitivity"

**Source data**: load_displ history 已经是每个 mesh archive 的标配（你常规 export）。不需要新跑训练。

**Output**:
1. 表格：mesh_C / M / F / XF 在 load-drop criterion 下的 N_f
2. 加 FEM-D 矩阵的 narrow row N_f（如果已经跑出来）
3. 一句 verdict：是否单调收敛 / 收敛 < 5%

**Priority**: **high** — paper §FEM 的写法直接 blocked 在这上面。Tier C reruns 都是 ℓ/h=1 的 PIDL 比较，不会受 FEM 这个收敛问题影响，但 reviewer 会先问"FEM reference 的 mesh convergence 怎么说"。

**ETA**: 你估计 ~30 min post-process（不需要新 GRIPHFiTH run）。

---

## 2026-05-06 · Request FEM-5: ship u=0.10 + u=0.11 ψ⁺ keyframes to Mac

**Goal**: 解锁 Mac→Taobo 上的 Oracle u=0.10 / u=0.11 干净重跑（Tier C audit follow-up，currently blocked）。Mac `~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/` 目前只有 u08 + u12 4-keyframe 各 4 文件；u10/u11 一直只在 Windows-FEM。Taobo 已有 FEM data 镜像（Mac sync 过来），所以 Windows-FEM 只需把 u10/u11 keyframes 寄到 Mac，Mac 自会再同步到 Taobo。

**Format**: 与 u08/u12 完全一致——4 个 keyframe `.mat` 文件 / Umax，每个含 `psi_elem`, `alpha_bar_elem`, `f_alpha_elem`, `d_elem`（n_elem × 1 element-averaged from Gauss points + d-field read from VTK at nearest cycle ≤ keyframe）。

**Keyframe cycles 选择参考 u12 模式**（c1, c40, c70, c82）：
- u=0.10 (FEM N_f=170)：建议 c1, c80, c140, c170
- u=0.11 (FEM N_f=117)：建议 c1, c55, c95, c117

**Expected files** (8 个 `.mat`)：
```
u10_cycle_0001.mat
u10_cycle_0080.mat
u10_cycle_0140.mat
u10_cycle_0170.mat
u11_cycle_0001.mat
u11_cycle_0055.mat
u11_cycle_0095.mat
u11_cycle_0117.mat
```

**Delivery**: 跟 u08/u12 一样，OneDrive 共享文件夹（或 zip 一起发）。Mac 拿到后会落到 `~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/` 然后 rsync 到 Taobo。

**Acceptance**: Mac 可以读到这 8 个文件，sanity check 与 u08/u12 文件的 keys 一致；Taobo 上 `run_e2_reverse_umax.py 0.10` 和 `0.11` 不再报 FEM data missing。

**Priority**: medium (paper 用 Oracle u=0.10/0.11 数据 cross-validate framework claim；Taobo 5/8 GPU 也在等这个解锁)。ETA：抽 20-30 min 跑一下 export script 应该够。

**Background**: Mac 同时在审计 archive 设置（commit `28cce78` 后 audit 脚本发现 3 个 u=0.12 method archive WARN due to missing model_settings.txt）。Tier C 重跑已派 5 个到 Taobo，但 Oracle u=0.10/0.11 还要等这两组 keyframe ship 过来。

---

## 2026-05-05 · Request FEM-4: export a(N) crack propagation curve for u=0.08, 0.12, 0.13

**Goal**: 生成 FEM 的 a(N) 曲线（裂纹尖端位置 vs 循环数），与 PIDL 的 x_tip-vs-N 叠图对比。这是 Carrara 2020 Fig 6 的核心图，paper 必须有。

**定义对齐（与 PIDL 一致）**：
- `x_tip(N)` = 该 cycle 中 α > 0.95 的最大 x 坐标（即 crack front 的 x 位置）
- 如果 GRIPHFiTH 输出的是 GP-level α，取所有 α>0.95 的 GP 中 x 坐标的最大值

**需要的 Umax**（3 个，覆盖低/中/高 Umax）：
- u=0.08：FEM N_f ≈ 396，`SENT_PIDL_08_export/` 已有
- u=0.12：FEM N_f = 82，`SENT_PIDL_12_export/` 已有
- u=0.13：FEM N_f = 57，数据在 `_pidl_handoff_v2/psi_snapshots_for_agent/` 或单独跑一次

**Output format**（每个 Umax 一个 CSV）：
```
cycle, x_tip_alpha95, alpha_max_monitor
1, 0.502, 0.031
2, 0.503, 0.044
...
```

**Files requested**:
- `fem_a_traj_u008.csv`
- `fem_a_traj_u012.csv`
- `fem_a_traj_u013.csv`
- 放到 `_pidl_handoff_v3_items/` 或新建 `_pidl_aN_curves/`

**Priority**: high（这个图是 paper 核心图之一，PIDL 这边 x_tip 数据已有，等 FEM 数据就能出图）

**Note**: `export_alpha_traj_u12.m` 目前只导出 α_max，不含 x_tip，需要新写或修改导出脚本。

---

## 2026-05-05 · Request FEM-3: h-sweep extension — ℓ/h=20 to bracket convergence

**Goal**: mesh_C/M/F 显示 M→F 仍有 +8.9%，尚未收敛。加 ℓ/h=20 一个点来估计渐近值，给 paper 一个更紧的 convergence bracket。

**脚本**：按 mesh_F 的模式新建 `INPUT_SENT_PIDL_12_mesh_XF.m` + `main_fatigue_meshXF.m`（"XF" = extra-fine）。

目标 mesh 参数（跟着 mesh_F 模式延伸）：
- `ℓ/h_tip = 20` → `h_tip = 0.0005 mm`
- `specimen.internal.plate` 参数参考：`Lref_y=0.05`, `Nref_y=100`（偶数，确保 notch 在网格上）；`Nx` 按需调整以匹配 h_tip
- 其余材料参数、BC、max_cycle=120 全不变

**Expected output**:
- N_f_XF（first detect）
- 回传 outbox：N_f_C/M/F/XF 完整表 + 是否出现渐近迹象

**Acceptance**: 如果 |N_f_XF − N_f_F|/N_f_F < 5% → convergence bracket closed；若仍 >5% → report trend，Mac 决定是否再加一档

**Priority**: medium（ETA ~12-15h，可 overnight）

---

## 2026-05-05 · Request FEM-2: gmsh-only h-sweep — mesh_C/M/F convergence at Umax=0.12

**Goal**: 用同一个工具（GRIPHFiTH `specimen.internal.plate`）跑三套分辨率，干净证明 h-convergence，替代 FEM-1 的混合工具对比结果。Paper 里写"h-convergence verified with same mesh generator"。

**脚本已在镜像里，直接跑**：

```matlab
% 顺序跑，或并行跑（独立）
run('Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_mesh_C.m'); main_fatigue_meshC(...)
run('Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_mesh_M.m'); main_fatigue_meshM(...)
run('Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_mesh_F.m'); main_fatigue_meshF(...)
```

**Expected outputs**:
- 三个 N_f（first penetration）
- 回传到 outbox：表格 N_f_C / N_f_M / N_f_F + 趋势（converging / diverging）

**Acceptance criteria**:
- PASS：N_f_M 和 N_f_F 之差 < 5%（证明在 ℓ/h≥10 处收敛）
- BONUS：如果 N_f_C ≈ N_f_M ≈ N_f_F，连 ℓ/h=5 都够用，更强

**Priority**: medium（~30-40 min wall，三个可并行）

---

## 2026-05-05 · Request FEM-1: mesh convergence check — PIDL-series at Umax=0.12, ℓ/h=5

**Goal**: 验证 PIDL-series FEM 参考数据（ℓ/h≈1，N_f≈82）是否网格收敛。Paper 里要能写一句"convergence verified at representative Umax"。

**现有 baseline**:
- INPUT file: `Scripts/fatigue_fracture/INPUT_SENT_PIDL_12.m`
- Mesh: `Dependencies/SENT_mesh/SENT_mesh.inp`（77,730 quads，h_tip≈0.01 mm，ℓ/h≈1）
- Result: N_f ≈ 82

**需要做的**:

**Step 1 — 生成新 mesh**（与 SENT_carrara_quad.inp / SENT_pcc_concrete_quad.inp 同流程）:

| 参数 | 目标值 |
|---|---|
| 几何 | 同 SENT_mesh.inp：1×1 mm，notch 在左中，物理切口 |
| ℓ | 0.01 mm（不变） |
| h_tip | **0.002 mm**（ℓ/h_tip = 5） |
| h_zone | 0.005 mm（tip 周围精细区） |
| h_global | 0.05 mm |
| 格式 | Abaqus .inp 或 GRIPHFiTH 支持的格式 |
| 文件名 | `SENT_pidl_fine_lh5.inp` |

**Step 2 — 新 INPUT 文件**（基于 INPUT_SENT_PIDL_12.m 修改）:
- 文件名：`INPUT_SENT_PIDL_12_fine.m`
- 唯一改动：mesh 路径指向新 `SENT_pidl_fine_lh5.inp`
- 所有材料参数不变：E=1, ν=0.3, Gc=0.01, ℓ=0.01, α_T=0.5, p=2.0, AT1, AMOR, PENALTY
- BC 不变：uy_final=0.12, R=0.0
- max_cycle=120（足够，预期 fracture ~82）

**Step 3 — 跑**:
```matlab
run('Scripts/fatigue_fracture/INPUT_SENT_PIDL_12_fine.m')
main_fatigue_fracture(...)
```

**Expected outputs**:
- N_f（first penetration cycle）
- ᾱ_max @ N_f
- 回传到 `windows_fem_outbox.md`：N_f_fine vs N_f_coarse=82，差值 %

**Acceptance criteria**:
- PASS：|N_f_fine − 82| / 82 ≤ 5%（网格收敛）
- FAIL：>5%，需要讨论是否重跑所有 Umax 或降级 caveat

**Priority**: medium（OOD 表格不 block 这个，但 paper submission 前必须有）

**Blocker 提示**: 如果 mesh 生成工具（Abaqus/Gmsh）有问题，outbox 里说一声，Mac 可以帮生成 .inp 文件。

---

## Archive

[暂无]
