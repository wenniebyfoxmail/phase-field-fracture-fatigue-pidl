# Experiment Inventory — Purpose-Organized

**Last updated**: 2026-05-05  
**Scope**: All PIDL + FEM experiments across Mac / Windows-PIDL / Windows-FEM / Taobo  
**Format**: purpose → experiments → [机器] result / verdict

---

## 1. Baseline & Reproducibility
> **目标**: 确认 PIDL 在训练 Umax=0.12 能复现 Carrara N_f；建立参考基准。

| 实验 | 机器 | 关键结果 | 状态 |
|---|---|---|---|
| hl_6 小网络探索（100 neurons，fatigue on/off，aT=0.167/0.5） | Mac | 概念可行；网络太小 | done |
| hl_8 baseline coeff=1.0，u=0.12，seed=1 | Mac | N_f=82（FEM=82）✅ | valid |
| hl_8 baseline coeff=1.0，u=0.12，seed=2/3 | Mac+Taobo | N_f=82 bit-exact × 3 | valid，零方差 |
| hl_8 baseline coeff=1.0，u=0.08–0.11（legacy 5-Umax sweep） | Mac | N_f trend 单调 | 历史参考 |
| hl_8 baseline coeff=3.0，u=0.08–0.12（敏感性检验） | Windows | N_f对 init_coeff 不敏感；ᾱ_max 低 Umax 有影响 | done |
| Golahmar 模型 spAlphaT b=0.8（替换 Carrara 模型验证框架可换） | Mac | N_f=154（模型不同，仅框架测试）| done |

---

## 2. ᾱ_max Gap — 输入/表示层干预
> **目标**: 通过改变 NN 输入特征/ansatz，让 ψ⁺ 峰值在裂纹尖端更集中，突破 ᾱ_max 天花板。  
> **背景**: ψ⁺_active_driver 比 FEM 低 5.8×（~3 orders 在极端情况），怀疑 NN 表示能力是瓶颈。

| 实验 | 机器 | 关键结果 | 判决 |
|---|---|---|---|
| **Williams Ansatz** v1（K_I × r^{-1/2} 解析） | Mac | v1 crash，v2 cycle 12 failed | — |
| **Williams Ansatz** v3（fallback false stop） | Mac | cycle 69 停止，no fracture | — |
| **Williams Ansatz** v4 | Mac | N_f=77，E_el 非单调 → V1 BC 残差 FAIL | ❌ NEGATIVE |
| **Fourier Feature** nf=16 σ=1.0 | Mac | N_f=84，ᾱ_max 无改善 | ❌ NEGATIVE |
| **Enriched Ansatz Mode-I** v1 | Mac(smoke)+Windows(prod) | N_f=84，D1a传播率=0.42≈baseline→Claim 1 不变量跨 Umax | ❌ ᾱ_max NEGATIVE；✅ 发现 Claim 1 低 Umax 泛化 |
| **Enriched Ansatz** v1 @ u=0.08（低 Umax 泛化验证） | Windows | N_f=345，D1a=0.42（baseline=0.40）→ Claim 1 invariance confirmed | ✅ 发现 |
| **Enriched Ansatz** v2 cinit=0.1 rcut=0.05 | Mac | smoke done，未完整产跑 | — |
| **tip-weighted loss** b=2.0 p=1.0 | Mac | done，ᾱ_max 无显著改善 | ❌ NEGATIVE |

---

## 3. ᾱ_max Gap — 疲劳模型/损失层干预
> **目标**: 通过修改 Carrara 疲劳参数（α_T、f-shape、监督信号），直接放大疲劳驱动。

| 实验 | 机器 | 关键结果 | 判决 |
|---|---|---|---|
| **spAlphaT** b=0.5 r=0.1（空间非均匀 α_T） | Mac | N_f=76，Kt 无改善，A1 K_I 一致 | ❌ NEGATIVE |
| **spAlphaT** b=0.8 r=0.03 | Mac | N_f=80，Kt_PIDL 无改善 | ❌ NEGATIVE |
| **MIT-8** K=1/2/3（监督 ψ⁺ 1-3 cycles） | Mac | smoke done | — |
| **MIT-8** K=5 amortized（监督 5 个周期的平均） | Mac | N_f=81，ᾱ=8.45（≈baseline 9.09）→ peak-drift 机制第3次确认 | ❌ NEGATIVE |
| **MIT-8** K=40（强监督，未摊销） | Mac | done | — |
| **Dir 6.3 logf** @ u=0.12（对数 f-shape） | Windows | N_f=121（+46%），ᾱ_max=10.83（+16%）→ f-shape 对高 Umax 效果微弱 | ❌ ᾱ_max 无突破 |
| **Dir 6.3 logf** @ u=0.08/0.09（低 Umax） | Windows | NO fracture in 300 cycles！低 Umax 传播彻底停止 | ❌❌ 使情况更糟；但发现 f-shape 控制低 Umax 传播运动学 |

---

## 4. ᾱ_max Gap — 架构干预
> **目标**: 改变 NN 架构（多头、网格自适应、跳跃增益），直接解决尖端 α 表示限制。

| 实验 | 机器 | 关键结果 | 判决 |
|---|---|---|---|
| **α-1** 自适应网格（153k三角，PZ h=0.001） smoke N10 | Mac | smoke ✅，50 min/cycle Mac（远超预期 22 min/cycle）| — |
| **α-1** 生产跑 u=0.12 N=300 | Windows | N_f=79，ᾱ_max=11.94（+28%）→ 有小幅改善但不是 closure | ❌ NEGATIVE（不闭合）|
| **α-2** multi-head（主头+尖端门控头，default gate r_g=0.02） | Mac(dev)+Windows(prod) | T4 modal=0.30 FAIL（需≥0.70）| ❌ FAIL |
| **α-2** tighter gate r_g=0.005 power=4 | Windows | T4 modal=0.30 FAIL → α-2 架构宣告无效 | ❌ DEAD |
| **α-3** XFEM 跳跃增益（Heaviside 型连续+跳跃双头） | Windows | T4 modal=0.500 MARGINAL（最优 stationarity）；ᾱ_max@c9=3.04 | ⚠ MARGINAL → **CLOSED OUT 2026-05-06**：not pursued for Phase 1，Path C 给了更好 trajectory metrics |
| **Path C** supervised-α @ u=0.12 λ=0 seed=1 | Taobo | N_f=82 EXACT，ᾱ_max=12.08 | ✅ 确认 N_f match seed-robust |
| **Path C** supervised-α @ u=0.12 λ=0 seed=2 (multi-seed) | Taobo | N_f=82 BIT-EXACT，ᾱ_max=10.17 | ✅ 框架级 N_f match 不依赖 seed |
| **Path C** supervised-α @ u=0.12 λ=1 (R2) | Taobo | N_f=89，ᾱ_max=**108.9**（vs FEM 270 = 0.40×） | ✅ **最强 ᾱ_max 改善**（4× α-1/α-2/α-3 at c9=9.66）|
| **Path C** supervised-α @ u=0.12 λ=10 | Taobo | N_f=89，ᾱ_max=27.46 | 过 supervised → λ=1 sweet spot |
| **Path C** supervised-α @ u=0.08 λ=1 (cross-Umax) | Taobo | N_f=375 (FEM 396, −5%)，ᾱ_max=128.8 (FEM 390, 0.33×) | ✅ 跨 Umax transfer |

> **Path C 不继续的原因**（v3.16, 2026-05-06 决策）: 
> 1. cross-Umax 显示 ᾱ_max 在 c200 进入 **plateau ≈ 128.8**，结构性 ceiling（zone-internal f(ᾱ) 进入 asymptotic 极低退化 regime，accumulator Δᾱ → 接近 0）；不是 cycle 不够
> 2. ᾱ_max gap 可能不是正确闭合目标：domain-level proxy α_bar_domain ratio 仅 1.08-1.78×（vs ᾱ_max 9-94×），积分量已经接近，只是空间峰值不同
> 3. N_f 与 ᾱ_max 解耦：Path C 闭合 ᾱ_max 不改 N_f match 的 paper claim
> 4. Path C 是 supervised（非 pure-physics），适合 §5 supervised extension 而非 §4 closure 主线
> 5. 资源 ROI：继续 Path C+α-3 combine = 3-4 周 engineering vs Phase 2 PCC concrete 转向更高 impact

---

## 5. 机制诊断（为什么 ᾱ_max 差距存在？）
> **目标**: 通过受控实验，区分"NN能力上限"、"疲劳模型结构"、"训练动力学"三类原因。

| 实验 | 机器 | 关键发现 | 意义 |
|---|---|---|---|
| **E2 psiHack**（冻结累积器 = 假注入 FEM ψ⁺）@ u=0.12 | Mac | N_f=81 → 证明 accum 机制健全，ψ⁺ amplitude 是唯一瓶颈 | ✅ 诊断 |
| **α-0**（FEM ψ⁺投影到 PIDL mesh） @ u=0.08/0.12，coeff=1/3 | Mac | ψ⁺_active_driver ~ 5，gap to FEM ~ 2000×（3个 OOM）| ✅ 量化差距基线 |
| **Oracle** movingzone smoke @ u=0.12 N10 | Mac | smoke ✅ | — |
| **Oracle** Variant-A @ u=0.12（注入 FEM ψ⁺ zone=0.02） | Mac+Windows | N_f=83（FEM=82，+1%）✅，ᾱ_max=极高 → N_f match 可达 | ✅ N_f ceiling 可破；ᾱ_max 是 field-level 非 framework-level |
| **Oracle** Variant-B @ u=0.12 zone=0.005（仅5元素） | Windows | N_f=84（稳定），ᾱ_max 崩塌 82× → **N_f 与 ᾱ_max 两效应解耦** | ✅ 重要机制发现 |
| **Oracle fresh vs resumed** @ u=0.10 | Windows | bit-identical → Hyp F（resume artifact）refuted | ✅ 排除假说 |
| **α-field 直接对比**（PIDL α vs FEM α in oracle zone） | Windows | PIDL α mean=0.485 vs FEM mean=0.159（PIDL 高3×）→ Hyp B/E 全 refuted | ✅ 推翻5个假说 |
| **Oracle** 5-Umax sweep（0.08–0.14）| Windows | N_f 全部在 FEM ±10% 内（0.14: −15% Pattern A）；ᾱ_max 11 个量级差异 | ✅ framework vs field level 核心证据 |
| **Oracle** u=0.11 seed=1/2/3（三种初始化） | Windows | N_f={117,116,114}（Δ=3 cycles），ᾱ_max={11253,1140,3511}（10× 扩散）→ **3 distinct basins** | ✅ multimodal loss landscape 确认 |
| **posthoc 5-metric 多档案分析**（Mac 分析脚本） | Mac（分析）| 3 新发现：(4) energy budget 守恒（ᾱ_bar_domain ratio=1.08-1.78×）；(5) Pattern A 是高 Umax 专属；(6) Path C a-N 跟踪 FEM 精度比纯物理高 3.4× | ✅ 重构 Ch2 §4 叙事 |

---

## 6. OOD 泛化 — N_f 跨 Umax 验证（§4.6）
> **目标**: 在训练 Umax 之外（0.08–0.14）验证 PIDL 预测 N_f 的准确性和鲁棒性（seed 方差、cross-method 一致性）。

### 6a. Pure-physics baseline（无 FEM 监督）

| Umax | Method | Seed | N_f_PIDL | N_f_FEM | 误差 | 机器 | 状态 |
|---|---|---|---|---|---|---|---|
| 0.08 | baseline | 1 | ~340 | 396 | −14% | Mac | legacy |
| 0.09 | baseline | 1 | ~225 | 254 | −11% | Mac | legacy |
| 0.10 | baseline | 1 | ~170 | 170 | 0% | Mac | legacy |
| 0.11 | baseline | 1 | 116/126 | 117 | −1% / +8% | Taobo | ✅ clean |
| 0.11 | baseline | 2 | 🏃 running | 117 | — | Taobo | ⏳ |
| 0.11 | baseline | 3 | 113 | 117 | −3% | Windows | ✅ |
| 0.12 | baseline | 1 | 82 | 82 | 0% | Mac+Taobo | ✅ valid |
| 0.12 | baseline | 2 | 82 | 82 | 0% | Taobo | ✅ |
| 0.12 | baseline | 3 | 82 | 82 | 0% | Taobo | ✅ 零方差 |
| 0.13 | baseline | 1 | 61/71 | 57 | +7% / +25% | Taobo | ✅ clean |
| 0.13 | baseline | 2 | 60 | 57 | +5% | Windows | ✅ |
| 0.13 | baseline | 3 | 62 | 57 | +9% | Windows | ✅ |
| 0.14 | baseline | 1 | 33 | 39 | −15% | Taobo | ✅ |
| 0.14 | baseline | 2 | 36 | 39 | −8% | Taobo | ✅ |
| 0.14 | baseline | 3 | 26 | 39 | −33% | Taobo | ✅ |
| 0.14 | baseline | 4 | 33 | 39 | −15% | Taobo | ✅ |
| 0.14 | baseline | 5 | 25 | 39 | −36% | Taobo | ✅ |
| **0.14 mean** | — | — | **29.6 (std=4.2)** | 39 | **−24%** | — | **OOD boundary** |

### 6b. Oracle（注入 FEM ψ⁺，cross-method 一致性验证）

| Umax | Seed | N_f_Oracle | N_f_FEM | 误差 | 机器 |
|---|---|---|---|---|---|
| 0.08 | 1 | 359 | 396 | −9% | Windows |
| 0.09 | 1 | 235 | 254 | −7% | Windows |
| 0.10 | 1 | 156 | 170 | −8% | Windows |
| 0.11 | 1 | 117 | 117 | 0% | Windows |
| 0.11 | 2 | 116 | 117 | −1% | Windows |
| 0.11 | 3 | 114 | 117 | −3% | Windows |
| 0.12 | 1 | 83 | 82 | +1% | Windows |
| 0.13 | 1 | 61 | 57 | +7% | Windows |
| 0.14 | 1 | 33 | 39 | −15% | Windows |

**结论**：Oracle 7/8 Umax 在 ±10% 内；u=0.14 偏出（Pattern A）。  
u=0.11 三 seed N_f spread=3 cycles，但 ᾱ_max 相差 10×（multimodal loss landscape）。

### 6c. 关键 cross-method 一致性点

| Umax | pure-physics seeds | Oracle seeds | FEM | 结论 |
|---|---|---|---|---|
| 0.12 | 82/82/82 | 83 | 82 | 完全一致，零方差 |
| 0.11 | 113/116/🏃 | 117/116/114 | 117 | N_f 一致（Δ≤4），ᾱ_max 仅 Oracle 多峰 → multimodality 是 Oracle-specific |
| 0.13 | 61/60/62 | 61 | 57 | 4种方法/seed 聚集在 60-62（+5%–+9%），最强 OOD 证据 |

---

## 7. FEM Reference Quality（网格收敛）
> **目标**: 验证 PIDL-series FEM 参考数据（ℓ/h≈1）是否网格收敛；为 paper 提供"convergence verified"陈述。

### 7a. PIDL-series 参考数据（ℓ/h≈1，Abaqus mesh，77,730 quads）

| Umax | N_f_FEM | 机器 |
|---|---|---|
| 0.08 | 396 | Windows-FEM |
| 0.09 | 254 | Windows-FEM |
| 0.10 | 170 | Windows-FEM |
| 0.11 | 117 | Windows-FEM |
| 0.12 | 82 | Windows-FEM |
| 0.13 | 57 | Windows-FEM |
| 0.14 | 39 | Windows-FEM |

### 7b. 网格收敛实验

| 实验 | Mesh | ℓ/h_tip | N_f | 工具 | 状态 |
|---|---|---|---|---|---|
| FEM-1：ℓ/h=5 对比 | gmsh graded h_tip=0.002 | 5 | 77 | gmsh vs Abaqus（混合工具）| ✅，Δ=−6.1%，混合工具噪声内 |
| FEM-2 mesh_C | gmsh h_tip=0.002 | 5 | 77 | 同工具 | ✅ |
| FEM-2 mesh_M | gmsh h_tip=0.001 | 10 | 79 | 同工具 | ✅ |
| FEM-2 mesh_F | gmsh h_tip=0.0005 | 15 | 86 | 同工具 | ✅，M→F +8.9%，**未收敛** |
| FEM-3 mesh_XF | gmsh h_tip=0.00025 | 20 | — | — | ⏳ requested |

**当前状态**：ℓ/h=15 仍未收敛（+8.9%），FEM-3 ℓ/h=20 结果待收。

---

## 8. Phase 2 Groundwork（混凝土方向准备）
> **目标**: 确认 GRIPHFiTH + PIDL 框架能在 PCC 混凝土参数下运行；识别 gating 项。

| 实验 | 机器 | 关键结果 | 状态 |
|---|---|---|---|
| PCC concrete smoke（E=30GPa，ν=0.18，α_T=0.094 占位符） | Windows-FEM | N_f≫10⁵（ψ_tip vs α_T 差 5 OOM）→ α_T 标定是 gating 项 | ✅ smoke done，blocked on Holmen 1982 SP-75 |
| Holmen 1982 α_T digitization | — | 需要 SP-75 PDF，Cambridge VPN 下载 | ❌ blocked |

---

## Summary — 按目的判决

| 目的 | 主要发现 | 判决 |
|---|---|---|
| **1. Baseline** | PIDL u=0.12 精确复现 FEM，零 seed 方差 | ✅ 建立 |
| **2. 输入/表示层干预** | Williams/Fourier/Enriched 均无法突破 ᾱ_max 天花板 | ❌ 全 NEGATIVE |
| **3. 疲劳模型/损失干预** | spAlphaT/MIT-8/logf 均无法闭合差距；logf 在低 Umax 破坏传播 | ❌ 全 NEGATIVE |
| **4. 架构干预** | α-1 微弱改善；α-2 dead；α-3 marginal；Path C 未完成 | ❌/⏳ 未闭合 |
| **5. 机制诊断** | ᾱ_max = field-level；N_f = framework-level；两效应解耦；multimodality = Oracle-specific | ✅ 重大发现，重构 Ch2 |
| **6. OOD 泛化** | ≤0.13 可靠（±10%）；0.14 系统性低估 −24%；OOD 边界确定 | ✅ §4.6 结论完整 |
| **7. FEM 收敛** | ℓ/h=15 未收敛，ℓ/h=20 结果 pending | ⏳ FEM-3 待 |
| **8. Phase 2** | α_T 标定是 gating 项，SP-75 PDF 阻塞 | ❌ blocked |
