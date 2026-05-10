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

## 2026-05-10 · [reply to fd2a113]: Answers to 3 scope questions before FEM-9 kickoff

**Re**: Windows-FEM ack fd2a113 — 3 questions answered, proceed with A→B→F→D→E→C sequence.

### Q1: Doc location
`docs/FEM.md` 已存在，路径正确（`upload code/docs/FEM.md`，last sync 2026-05-06）。
Task A 要做的：把 FEM-7（V4 mirror RMS = 2.98e-5，integrated damage = 4.39e-2）和 FEM-8（V7_FEM = 0.12%）追加进 FEM.md 对应 section，更新 Last sync 为今日。

### Q2: Task D 6-case selection
**用同样的 6 个 amplitude（du25/30/35/40/45/50），在 MIEHE+AT2+HISTORY 下重跑，与 AMOR 结果直接对比。**
- MIEHE 的 ψ⁺ 数值与 AMOR 不同（spectral vs volumetric-deviatoric），N_f 会变，必须重跑才能得到 MIEHE 的 Basquin m
- 保留 du40/50（即使是 LCF 端）：Basquin log-log 拟合需要宽幅值范围，截掉高端会让斜率不稳
- 不延伸到更低幅值（N_f >> 10³，代价大，Carrara 2020 也没做超高周）
- 目标：MIEHE 这条线的 m 是否从 3.49 往 3.8–4.0 移动

### Q3: Task F cycle selection
**用 cycle 40（~49% 寿命，u=0.12 N_f=82）代替 cycle 82。**
- Cycle 82 穿透态裂缝带 σ ≈ 0，归一化分母受损伤区扭曲，FEM 自己也会给出不合理的 V7 值
- Cycle 40 在传播阶段（裂缝已启动），归一化分母（体内 σ_yy_max）在清晰的裂缝前端，定义明确
- Cycle 40 有现成 `psi_fields/cycle_0040.mat`（FEM-5 keyframe set 已包含），读 VTK 即可，~10 min 额外计算

**→ 可以按 A→B→F→D→E→C 顺序开始，无其他 blocker。**

---

## 2026-05-09 · Request FEM-9: Windows-FEM 1-week plan (external expert recommendation)

**Goal**: 把外部专家给的 1 周 FEM 工作排期同步过来。专家把任务分成"必须做 / 值得做 / 暂缓"三档。整体方向：**收口 Phase 1 evidence、启动 strict Carrara、准备 PCC Phase 2** —— 不再用 Windows-FEM 资源补 AT1+penalty 细枝末节。

### 必须做（直接服务当前 paper + 主线判断）

**Task A — 把 Phase 1 FEM 证据包整理进 [docs/FEM.md](upload code/docs/FEM.md)**

不是新计算，是**已经到位的证据收口**。必须明确包含：
- `V7_FEM = 0.12%` (FEM-8 result)
- exact-pair symmetry 的好结果（FEM-7: alpha_bar rel 2.98e-5）
- `∫ ᾱ·(1-f) dV` integrated damage budget（FEM-7: 4.39e-2）
- AT1+penalty 的 h-non-monotonic verdict（即"AT1+penalty 在 SENT 上不收敛"的结论文档化）

**Task B — 确认 strict Carrara 线的 runner 能稳定跑**

公式: `AT2 + Miehe spectral split + HISTORY` (这是 Carrara 2020 community-anchor 公式)。
要求：
- 至少 1 个 smoke + 1 个代表性载荷点（比如 u=0.12）
- 目标不是立刻出完整论文图，而是确认 kernel bugfix 后这条线**真的可用**，不再是 "理论上想跑"

**Task C — 把 PCC Phase 2 的输入参数接口准备好**

等 Mac 给定 `α_T` (PCC concrete-specific) 后，Windows-FEM 能直接重跑：
- PCC 材料参数（E~30GPa, ν~0.18 vs 当前 toy E=1, ν=0.3）
- AT2 + Miehe spectral
- FEM-only smoke (PIDL 暂不动)

这一步**先做"脚本 ready"**，不必跑实际计算 — 等 Mac 给参数。

### 值得做（高价值增强，但不该阻塞写作）

**Task D — strict Carrara 6-case sweep**

最值得的增强实验。目的：
- 对齐 Carrara community anchor (Carrara 2020 CMAME)
- 看 Basquin slope `m` 能不能从当前 `3.49` 更接近 community range `3.8–4.0`

**Task E — strict Carrara 最小 mesh check**

只选 1 个中间载荷点（比如 u=0.12 量级），跑两档 mesh：
- ℓ/h = 5
- ℓ/h = 10

不追完美收敛，**确认 strict formulation 的 mesh sensitivity 是不是比当前 AT1+penalty 更可控**。

**Task F — V7_FEM 再补 1 个 fracture-near cycle**

现有 `V7_FEM = 0.12%` 是 peak elastic / cycle 0 状态。如果时间允许，再补 fracture 附近 cycle 的同口径 V7。这样后续能回答："FEM 边界质量在早期 vs 临破坏时是否都稳定"。

### 暂缓（不优先）

- AT1+penalty h-sweep 继续细化（已经够得出"不收敛"verdict）
- wide/narrow XF 尾巴
- 为 PIDL 每个新想法立刻配 FEM rerun（不应该让 Windows-FEM 被 PIDL 微调牵着走）

### 1 周顺序建议

| Day | 任务 |
|---:|---|
| 1 | Task A: 更新 docs/FEM.md，固定 Phase 1 evidence pack |
| 2 | Task B: strict Carrara 1-case smoke，确认 runner / kernel / export 全通 |
| 3-4 | Task D: strict Carrara 6-case sweep |
| 5 | Task E: strict Carrara 1-point mesh check |
| 6-7 | Task C: PCC Phase 2 脚本 ready + 等 α_T 后 smoke |

### Acceptance / Reply

每完成一个 Task 就 append 一个 `[done]` entry 到 `windows_fem_outbox.md`，含：
- 关键数字（如 strict Carrara N_f 或 Basquin m）
- 任何 blocker（如 kernel bug、参数未定）
- 下一步打算

### Priority

**Task A: HIGH** — paper §4 evidence consolidation 直接 depends on this  
**Task B/C: HIGH** — 解锁 Phase 2 主线  
**Task D/E/F: MEDIUM** — 增强但非阻塞

---

## 2026-05-07 · Request FEM-7: FEM-side symmetry + integrated damage budget @ u=0.12

**Goal**: 给 paper §4 reframe 提供 FEM 端的对照数字。Mac 这边 PIDL 完成了 soft symmetry penalty 实验（commit 90f2297）+ Layer 3 red-team 反馈，现需 FEM 侧的：
1. **V4 对称性 ground truth**：FEM α-field 在 SENT 几何下的 mirror RMS 数字（公认应 ≈ 0 at machine precision，但需要数字进 paper §4.2）
2. **真实 integrated damage budget**：∫ ᾱ·(1-f(ᾱ))·dV at fracture cycle，替代 Mac 当前的 f_mean-based 'domain-mean proxy'（red-team 指出后者是 wrong quantity）
3. **α field snapshot @ fracture cycle**：用于 F4.5a side-by-side mirror visualization (PIDL baseline vs PIDL soft sym vs FEM)

**Specific deliverables** (3 个 numbers + 1 个 .mat)：

### (a) FEM V4 mirror RMS @ Umax=0.12 fracture cycle (cycle 82)

```python
# From SENT_PIDL_12/psi_fields/cycle_0082.mat or similar
import numpy as np
from scipy.spatial import cKDTree
import scipy.io as sio

m = sio.loadmat("path/to/cycle_0082.mat")
centroids = m["centroids"]      # (N_elem, 2)
alpha = m["alpha_bar_elem"]      # or "d_elem"
x, y = centroids[:,0], centroids[:,1]
mu = y > 1e-6; ml = y < -1e-6
tree = cKDTree(np.stack([x[ml], -y[ml]], axis=1))
d, idx = tree.query(np.stack([x[mu], y[mu]], axis=1), k=1)
exact = d < 1e-7    # exact mirror pairs (for FEM mesh likely ~thousands)
diff = alpha[mu][exact].flatten() - alpha[ml][idx[exact]].flatten()
print(f"FEM V4 mirror RMS (exact pairs): {np.sqrt((diff**2).mean()):.4e}")
print(f"n_exact_pairs: {exact.sum()}")
```
→ 期望 RMS < 1e-4（per `Mandal-Nguyen-Wu 2019 EFM 217` 标 ≤ 2e-4 PASS）

### (b) Integrated ∫ ᾱ·(1-f(ᾱ))·dV @ fracture cycle 82

```python
alpha_T = 0.5        # match PIDL's setting
f_alpha = (2*alpha_T / (alpha + alpha_T))**2
# area_per_elem = element area (from mesh; you have it from FEM solver)
integrated = (alpha.flatten() * (1 - f_alpha).flatten() * area_per_elem.flatten()).sum()
print(f"FEM ∫ᾱ(1-f)dV @ c82 = {integrated:.4e}")
```

→ 这个数字对照 PIDL 的同公式（Mac 端在算 baseline + soft sym 两个 archive 的同 quantity），决定 paper §4.4 是 'energy budget 1.5-2× near-equivalence' 还是要砍掉

### (c) α field snapshot @ fracture cycle

期望 1 个 .mat 文件 `u12_cycle_0082_FEM7.mat`，含：
- `centroids`: (N_elem, 2)
- `alpha_bar_elem`: (N_elem, 1) — Carrara accumulator at c82
- `d_elem`: (N_elem, 1) — phase-field damage at c82

放 `_pidl_handoff_v3_items/` 同步到 OneDrive。

### (d) Paper-grade caveat

如果你有 FEM 的 V4 RMS、integrated damage、α field 的 ready 现成 dump，直接给 numbers + .mat 即可。如果需要新跑 post-processing，约 30 min-1h（不需要新 GRIPHFiTH run）。

**Priority**: high — 这三个 number 是 §4 核心 claim 的 FEM 对照 baseline，写 LaTeX 之前必须有。

**ETA**: 你估计 30 min-1h post-process。

---

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
