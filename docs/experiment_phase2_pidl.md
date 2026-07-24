# Phase 2 PIDL Experiment Log

**Period**: 2026-05-15 起
**Scope**: PIDL retrain at PCC concrete physical units (E=30 GPa)。Phase 1 PIDL log frozen at `experiment_results.md`（toy units, AT1, u=0.12）。
**Sibling docs**:
- `memory/experiment_results_phase2.md` — FEM lane + Phase 2 strategic decisions (May 10 起的全部 PCC FEM 数据)
- `memory/finding_alpha_T_PCC_may10.md` — α_T calibration 全部依据
- `memory/finding_wu_pfczm_kernel_sign_fix_may13.md` — Wu PF-CZM kernel 状态
- `memory/finding_carrara_structural_asymmetry_may12.md` — §5 motivation 机制

---

## 0. 锁定的前置事实（不再讨论）

### 0.1 §5 paper plan（5/14 retraction 后）

- §5 plot：**PIDL_PCC vs Wu 2017 + Baktheer 2024 出版引用**（不是 in-house FEM N_f）
- 原计划 "PIDL_PCC vs Wu_FEM_PCC_Nf" 因 Wu PF-CZM monolithic Newton d-localization fail → BFGS port 推到 post-paper future work
- "N_f ≈ 1500-2500" 数字**已正式 retract**（inbox `4124444`），任何 §5 wording 不引

### 0.2 PCC 物理参数（locked，May 10）

| 参数 | 值 | 备注 |
|---|---|---|
| E_0 | 30,000 MPa | fib MC 2010 §5.1.7 typical PCC C30 |
| ν | 0.18 | typical PCC |
| f_t | 3.0 MPa | C30 grade |
| G_f | 0.10 N/mm | fib MC 2010 §5.1.5.2 |
| ℓ | 2.0 mm | regularization length |
| h_tip | 0.4 mm = ℓ/5 | Carrara rec |
| k_f | 0.01 | Baktheer 2024 |
| α_T = α_N | 5.0 N/mm² | = G_f / (k_f · ℓ) |

### 0.3 可用的 FEM 监督数据（Wu PF-CZM PCC v3 3000-cycle）

虽然这次 run **没有裂**（d_max=0.0037, ᾱ=1.14·α_T at c3000），但 trajectory 已 re-exported（outbox `b2d8432`）：

| 文件 | 路径（Windows-FEM 仓库） | 内容 |
|---|---|---|
| Bulk trajectory | `SENT_pf_czm_PCC_v3_fullNf/PCC_v3_trajectory_3000c.mat` | 4 tensors 2391 elem × 3000 cycle: `d_elem_traj`, `psi_elem_traj`, `alpha_elem_traj`, `f_alpha_traj` |
| Mesh | `SENT_pf_czm_PCC_v3_fullNf/mesh_geometry.mat` | `element_centroids` 2391×2, `connectivity` 2391×4, `node_coords` 2443×2 |
| Per-cycle snapshots | `SENT_pf_czm_PCC_v3_fullNf/psi_fields/cycle_NNNN.mat` × 3000 | 单 cycle .mat |

**用途限制**：可以作 PIDL 的 ψ⁺ / α / d 监督目标（MIT-8 family on PCC data），**不能**作 N_f oracle（没有 N_f）。

---

## 1. PIDL Phase 2 retrain — 计划

### 1.1 架构选择（待 discuss）

| 选项 | 描述 | 风险 |
|---|---|---|
| (i) AT1 + Carrara（Phase 1 同架构） | 改动最小，复用 Phase 1 经验 | 结构次临界，可能不裂（VHCF）|
| (ii) AT2 + Miehe + Carrara | 跟 FEM AT2 reference 对齐 | 跟 (i) 同病；需重写 PFF kernel |
| (iii) Wu PF-CZM PIDL | 跟 §5 plot line 对齐 | 工作量大，原计划 Phase 3 |

**当前决定**：先 (i) 探探水（见 §1.2）。

### 1.2 (i) AT1 + Carrara 探探水 — pilot run spec (LOCKED 2026-05-15)

**Runner**: `SENS_tensile/run_pcc_baseline_umax.py` (exists, commit `fd4d944` + `8134163`)
**Scaling 基础设施**: `source/scaling.py` — Buckingham π non-dim (L_char=W_phys, σ_char=Griffith)

**Pilot 命令**:
```bash
CUDA_VISIBLE_DEVICES=5 python3 -u run_pcc_baseline_umax.py 0.75 --n-cycles 50 --seed 1 --pff-model AT1
```
- `disp_ratio_intact=0.75` = **intact-bar displacement-equivalent**（不是 calibrated cracked-SENT S^max=0.75·f_t；裂纹存在时 realized nominal stress LESS than 0.75·f_t）

**Non-dim values applied (AT1 PCC)**:

| 量 | toy (Phase 1) | PCC (Phase 2A) |
|---|---|---|
| mat_E_norm | 1.0 | 1.0 |
| mat_nu_norm | 0.3 | 0.18 |
| w1_norm | 1.0 | **1.0** (`w1_phys=G_c/ell`; `c_w` already appears in the energy functional) |
| l0_norm | 0.01 | **0.02** (= 2 mm / 100 mm) |
| α_T_norm | 0.5 | **100** (vs toy 0.5, ratio 200×) |
| u_norm @ disp_ratio=0.75 | 0.12 | **0.0581** |
| ψ_per_cycle_norm | ~7e-3 | **~1.7e-3** (deep subcritical) |

**Pre-registered acceptance**（**只看 infra 稳定 + magnitude 预期**，不看 N_f）:

| 指标 | PASS 范围 | FAIL 即调查 |
|---|---|---|
| NaN / inf in any tensor | 无 | 有 → infra bug |
| loss trajectory | 单调下降（cycle 内）| 发散 / 震荡 |
| ψ⁺ magnitude @ cycle 1 | O(10⁻³) ~ O(10⁻⁴) norm（≈ 1.7e-3 上下 1 OOM） | >> 1.7e-2 或 << 1.7e-5 = scaling 仍有错 |
| ᾱ @ c50 | linear cum: ~ 0.085 = 0.085%·α_T | >> 1%·α_T → 裂纹活化太快，违 VHCF 预期 |
| f(ᾱ) @ c50 | ≈ 1.0 (未活化) | <0.99 = ᾱ 累得太快 |
| d_max @ c50 | < 0.005 | > 0.01 = 假裂 / localization 过早 |
| no_fracture stop @ c50 | yes（正常停在 c50）| 提前裂 = 几何/loading 严重失配 |

**三重 confound（写 §5 时必须 hedge）**:
1. **Loading label**：intact-bar 等效，不是 SENT cracked 标定（P1）
2. **Geometry**：a₀/W=0.5 (toy mesh reuse)，不是 FEM PCC v3 的 0.05（P2）
3. **Null-result 归因**：若 N=50 no fracture，机制无法唯一归因于 (a) Carrara 结构次临界 / (b) loading under-load / (c) toy-vs-PCC 几何差异（P4）→ 不写 "Phase 2A confirms framework insufficiency"

### 1.3 几何决策（已锁）

- 计算域保持 toy `[-0.5, 0.5]²`（normalized W_norm=1）
- 物理域映射 100×100 mm via `scaling.py` 的 L_char=W_phys=100 mm
- a₀ 沿用 toy mesh `meshed_geom1.msh` 的 a₀/W=0.5 （即 a₀_phys=50 mm）
- **不同于 FEM PCC v3 的 a₀=5 mm (a₀/W=0.05)** → 几何不等价，**不能直接 N_f 对标 FEM 这条线**

---

## 2. Pilot Run Inventory

待 §1.2 决定后填表。

| Run | Umax | n_cycles | architecture | seed | machine | GPU | log | archive | status |
|---|---|---|---|---|---|---|---|---|---|

---

## 3. Cross-comparison with FEM data

PIDL Phase 2 出 trajectory 后，跟 Wu PF-CZM PCC v3 3000-cycle data 对位：

| 比较项 | PIDL Phase 2 | Wu PF-CZM FEM PCC v3 |
|---|---|---|
| ᾱ_max @ c3000 | ? | 5.71e-3 (= 1.14·α_T) |
| d_max @ c3000 | ? | 0.0037 |
| f_min @ c3000 | ? | 0.78 (per-elem) |
| ψ⁺_tip trajectory | ? | trajectory available |
| N_f | ? | N/A (no fracture in 3000) |

§5 plot 主体仍由 Wu 2017 / Baktheer 2024 出版数据撑起，PIDL Phase 2 数据作为 "PIDL 在 PCC 单位下的行为" 单独呈现。

---

## 4. Open questions / Parking lot

- 是否需要 Phase 2 自己的 V1-V7 validator？（Phase 1 的 V4/V7 阈值是 toy 单位下的，PCC 单位下需重新校）
- §5 vs §6 章节归属：PIDL Phase 2 retrain 数据放 §5 还是另起 §6？
- Phase 3 是否仍是 "PIDL Wu PF-CZM 架构升级"？（5/14 retraction 后此目标地位变化）
