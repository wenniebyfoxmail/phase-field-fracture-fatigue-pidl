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
