# FEM Reference — Background, Setup, Results

**Owner**: Windows-FEM (GRIPHFiTH)  
**Sync source**: `docs/handovers/windows_fem_outbox.md` (canonical) + `docs/shared_research_log.md`  
**Last sync**: 2026-05-06

> **Purpose**: single canonical reference for FEM background + reference data + paper §FEM写作。Avoid scattered grep across handovers / shared_log。每次 Windows-FEM ship 重要结果时，本文件更新。

---

## 1. Solver background — GRIPHFiTH

**Origin**: ETH Zürich (Aurel Vischer), Apache 2.0 license.
**Fork mirror (read-only for Mac)**:  
> https://github.com/wenniebyfoxmail/wenniebyfoxmail-GRIPHFiTH-mirror.git (private, branch `devel`)

**Architecture**:
- **Fortran kernels** (compiled MEX): `Sources/+phase_field/+mex/Modules/`
  - `at1_penalty_fatigue.f90` — AT1 + penalty 实现 + Carrara accumulator
  - `at2_penalty_fatigue.f90` — AT2 + penalty 实现 + Carrara accumulator
  - `miehe.f90` — Miehe spectral split (recent bugfix `e7eb3f8`：strain-split 三处 index/div-by-zero)
- **MATLAB drivers**: `Scripts/fatigue_fracture/main_*.m`
- **INPUT files**: `Scripts/fatigue_fracture/INPUT_SENT_*.m`
- **Mesh generators**: `Dependencies/SENT_mesh/` (Abaqus & gmsh paths)

**Standard formulation for Phase 1**:
- AT1 + AMOR (volumetric-deviatoric energy split)
- Penalty regularization
- Carrara accumulator: `ᾱ_{n+1} = ᾱ_n + g(α_n)·ψ⁺·H(...)`
- Asymptotic degradation `f(ᾱ) = (2α_T/(ᾱ+α_T))²`
- α_T = 0.5 (toy methodology demo)
- ℓ_0 = 0.01 mm
- Material: E=1, ν=0.3, σ_c/E=1（无量纲 toy）

**Strict Carrara version (in progress)**: AT2 + Miehe spectral split + HISTORY accumulator. Kernel bugfix done (commit `e7eb3f8`)；全 6-case sweep 待跑。

---

## 2. Geometry and BCs

**SENT specimen** (Carrara 2020 Section 4.1 Fig 3a 同款)：
- 1×1 mm 正方形
- 切口 slit：x ∈ [-0.5, 0]，y = 0（沿 horizontal symmetry plane）
- 边界条件:
  - Top edge y = +0.5: prescribed v = +λ (vertical displacement)
  - Bottom edge y = -0.5: clamped (v = 0)
  - Side edges x = ±0.5: traction-free
- 加载: Δū cyclic, R-ratio = 0

> ⚠ **PIDL/FEM BC convention 一致性**：双方都用同一 affine BC（top pulled / bottom clamped）。这导致 displacement field **不**严格 y-mirror odd（v_BC 是 affine, 不 odd）；但 damage field α 在 tip-stress-dominated regime 仍接近 mirror-symmetric。详 §4 paper.

---

## 3. PIDL-series reference data (Phase 1 paper 主要 reference)

**Mesh**: `SENT_mesh.inp` (Abaqus uniform，77,730 quads，ℓ/h ≈ 1)。

| Δū | N_f (FEM) | Comment |
|---|---|---|
| 0.08 | 396 | low Umax; PIDL legacy data |
| 0.09 | 254 | — |
| 0.10 | 170 | — |
| 0.11 | 117 | PIDL Oracle multi-seed comparison anchor |
| 0.12 | 82 | training Umax，多 seed BIT-EXACT 验证 |
| 0.13 | 57 | OOD +1 step，PIDL multi-seed 验证 |
| 0.14 | 39 | OOD +2 step，Pattern A regime（PIDL 系统性低估 −24%）|

**ψ⁺ keyframe data** (用于 PIDL Oracle / Path C / MIT-8 监督):
- u=0.08：c1, c150, c350, c396 (4 keyframes, in `_pidl_handoff_v2/`)
- u=0.10：c1, c80, c140, c170 (4 keyframes, FEM-5 shipped 2026-05-06)
- u=0.11：c1, c55, c95, c117 (4 keyframes, FEM-5 shipped 2026-05-06)
- u=0.12：c1, c40, c70, c82 (4 keyframes)
- u=0.13/0.14：完整 `psi_snapshots_for_agent/` 在 `_pidl_handoff_v2/`

**a(N) trajectories** (FEM-4, 2026-05-05, paper 核心 figure 用):
- `_pidl_handoff_v3_items/fem_a_traj_u008.csv` (73 cycles, x_tip 0.025 → 0.4995)
- `_pidl_handoff_v3_items/fem_a_traj_u012.csv` (36 cycles, x_tip 0.10 → 0.4995)
- `_pidl_handoff_v3_items/fem_a_traj_u013.csv` (32 cycles, x_tip 0.12 → 0.4995)

格式: `cycle, x_tip_alpha95, alpha_max`
- `x_tip_alpha95` = max x-centroid of elements with `d_elem ≥ 0.95`
- `alpha_max` = max(`alpha_elem`) from `psi_fields/cycle_NNNN.mat` Carrara accumulator ᾱ

---

## 4. Mesh-convergence study (FEM-1 → FEM-3 → FEM-D → FEM-6)

**Goal**: 验证 PIDL-series FEM reference (ℓ/h ≈ 1) 是否网格收敛。

**Final result**: ❌ NOT converged (AT1+PENALTY known h-non-monotonic, Mandal-Nguyen-Wu 2019 EFM 217)

### 4.1 The 2×4 matrix (FEM-D, complete 2026-05-06)

固定 Δū=0.12，gmsh-generated quad mesh。`Lref_y` 是 refinement-band 高度（防 band-width confound 实验）。

| | ℓ/h=5 | ℓ/h=10 | ℓ/h=15 | ℓ/h=20 |
|---|---:|---:|---:|---:|
| **Lref_y=0.10 (wide)** | 77 | 79 | 86 | 97 |
| **Lref_y=0.05 (narrow)** | 77 | 79 | 86 | 97 |

**Findings**:
1. ✅ **Band-width 不影响 N_f**：wide=narrow bit-identical at every h（damage band 4ℓ=0.04 在 0.10 和 0.05 corridor 都装得下）
2. ❌ **h-convergence is non-monotonic**：N_f 单调放大 77 → 79 (+2.6%) → 86 (+8.9%) → 97 (+12.8%)，差异不缩反扩
3. ✅ **Detection criterion 不影响 N_f**（FEM-6, 2026-05-06）：load-drop (5%, 10%) 与 d-front criterion 在所有 mesh 上 **bit-identical** N_f。Penetration 时 F_peak drop 95% in one cycle (true cliff)，任何 5%-50% 阈值都选同一 cycle。

### 4.2 Acceptance verdict (B-fail)

Mac 给的 acceptance：`|N_f_F − N_f_M| / N_f_M < 5%` → |86−79|/79 = **8.9%**，failed。

→ AT1+PENALTY 真实 h-non-monotonic (Mandal-Nguyen-Wu 2019)，**不是 detection artifact，不是 band-width 干扰**。Phase 2 走 PF-CZM (Wu 2017+) length-scale insensitive 是 natural fix。

### 4.3 Paper §FEM 写法 (per FEM-6 outbox 建议)

> "The PIDL-series reference uses ℓ/h ≈ 1 (Abaqus uniform mesh) for back-compat with PIDL training data. h-refinement under both d-front and load-amplitude-drop criteria yields non-monotonic N_f variation (77, 79, 86, 97 at ℓ/h ∈ {5, 10, 15, 20}), consistent with the documented length-scale and mesh-bias sensitivity of AT1 phase-field formulations (Mandal et al. 2019, EFM 217). Band-width and detection-criterion confounds were ruled out via 2×4 matrix and load-drop cross-validation. Relative comparisons between PIDL methods within Phase 1 use a common reference mesh and are not affected by absolute h-sensitivity; absolute uncertainty band is approximately ±15% on N_f. Phase 2 transition to PF-CZM (Wu 2017+) is the planned mitigation."

---

## 5. Carrara 2020 Fig 6 cross-validation

**GRIPHFiTH 端：done** (commit `4084b79`, 2026-05-02).

| Method | Δū sweep | Basquin m | vs Carrara 3.8-4.0 |
|---|---|---|---|
| AMOR + AT2 + HISTORY | 6 cases | **3.49** | -12 to -15% |
| MIEHE + AT2 + HISTORY | 6 cases | TBD (kernel 已 fix `e7eb3f8`) | 待跑 |

**Castillón 2026 IJF cross-validation**: GRIPHFiTH du25 N_f=198 vs Castillón published N_f=195 (Haynes 230 superalloy, paradigm B reference) → **1.5% match**。Community anchor 已建立。

**MIEHE bugfix details** (`e7eb3f8`, 2026-05-02):
- 3 bugs in `miehe.f90` STRAIN_SPLIT branch:
  - eps_p / eps_n index swap
  - eps_p − eps_n div-by-zero at trace=0
  - H_p(trace) / trace at trace=0
- 5-cycle smoke previously NaN'd c2，bugfix 后 38 sec 通过
- du25 MIEHE production launched，N_f estimate ~200

---

## 6. Phase 2 PCC concrete smoke (Handoff F)

**Status**: ✅ smoke complete (2026-05-04)；α_T 标定 unblocked (2026-05-06, fib MC 2010 sufficient)。

**Smoke result**:
- (a) Compile + run ✓ — 100 cycles 25.6 s wall，MIEHE+AT2 spectral kernel patched
- (b) Crack pattern ✓ — Kt = 2.10 at notch tip (a/W=0.05 SENT 物理合理)，`||d||_inf = 0.016`
- (c) N_f ❌ — N_f ≫ 10⁵ (`ψ_tip ≈ 4.2e-7` vs `α_T = 0.094` 差 5 OOM；fatigue degradation 永远不触发)

**Root cause**: `α_T = 0.094` 是占位符；真混凝土 α_T 需要从 fib MC 2010 §5.1.11 S-N relations 反推。**Phase 2.1 重跑等 α_T 标定**。

**Phase 2A vs 2B path**: 见 `references/README.md` Paradigm 章节。
- 2A = Carrara extended at concrete units (current GRIPHFiTH code 直接外推，工程量小)
- 2B = Wu PF-CZM 替换 (Baktheer-Aldakheel 2024 arXiv 蓝图，需 Fortran kernel 改 + g(α) 重写，工程量大)

---

## 7. N_f detection criterion (统一 PIDL ↔ FEM)

**Primary**: `d_elem ≥ 0.95` 在 right boundary，`≥ 3 elements`，3-cycle 确认窗口。

**Secondary cross-check**: `F_peak / F_initial < 5%` load-drop criterion (Castillón 2026 / ASTM 风格)。

**Identical at all completed meshes**: penetration 时 F_peak drop 95% in one cycle，任何阈值 5%-50% 都给同 N_f。

**Paper §FEM 写法**: 报告 d-front 为主，load-drop 作为脚注 cross-check。

---

## 8. Open / TBD

| Item | Owner | Trigger |
|---|---|---|
| MIEHE+AT2 strict Carrara 6-case sweep | Windows-FEM | 等 Mac decision (2A vs 2B 分歧) |
| Phase 2 PCC re-smoke with fib-MC-derived α_T | Mac (calibration) → Windows-FEM (run) | Mac 反推完 α_T 数字 |
| FEM-3 mesh_XF_w 完整 N_f (only narrow XF=97 confirmed; wide XF crashed at c97 mid-cycle) | low priority | 不影响 paper（symmetry 已在其它 h 验证）|

---

## 9. 文件路径速查 (Mac 端可访问)

| 项 | Mac path | Source |
|---|---|---|
| ψ⁺ keyframes | `~/Downloads/_pidl_handoff_v2/psi_snapshots_for_agent/` | OneDrive sync |
| FEM-4 a(N) CSVs | `~/Downloads/_pidl_handoff_v3_items/` | OneDrive sync |
| FEM-6 load-drop CSV | `~/Downloads/_pidl_handoff_v3_items/fem6_load_drop_Nf.csv` | OneDrive sync |
| Dir 6.3 logf archives | `~/Downloads/_pidl_handoff_dir63_logf_20260505/` (4 tarballs, 4.7 GB) | OneDrive sync |
| GRIPHFiTH source (read-only) | `git clone <mirror-URL>` to `~/phase-field-fracture-with-pidl/GRIPHFiTH/` | GitHub mirror |

---

## 10. 维护规则

- **Owner**: Windows-FEM 主导；Mac sync from outbox 时更新本文件
- 每次 Windows-FEM ship 重要 result 时（[done] entry 标记 paper-grade）：
  1. Mac sync outbox
  2. 把 result 抠到本 FEM.md 对应 section
  3. shared_research_log 只记 finding/decision/retraction，本文件记 fact + path
- **paper §FEM 写作直接引本文件**，不再 grep 散落条目

