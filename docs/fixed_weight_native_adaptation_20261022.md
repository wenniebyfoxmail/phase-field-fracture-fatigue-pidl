# 两条完整原生 FEM 轨迹的显式适配（2026-10-22）

目的：解决已查明的四项接口差异，判定 U0.115 / U0.125 的完整轨迹能否用于固定权重模型的数据接口。继续 10-22 的原始档案核验；原来的严格接口失败结论保留，不改写为原数据本来已通过。

本轮范围：两份既有、已开发暴露的档案；代码、来源诊断、CPU 全量验证和独立复核。原始 MAT、CSV、config、static 均只读；没有训练或新 FEM 求解。用户已授权完成这条适配链，无需为机械依赖或回归检查逐项再审批。

**结论：两条完整轨迹已通过显式适配后的数据接口准入，独立代码、数学实现和全量结果复核均无阻塞问题。** 准入限已暴露开发条件的 synthetic interface；不是旧v1直接通过，也没有启动训练。

## 适配规则

| 问题 | 实现 | 保留的约束 |
|---|---|---|
| recovered 初态 | 新 `RecoveredInitialKey/State` 和 `explicit_recovered_initial_and_post_commit_v2`，保留 `pre_cycle_committed`；仅 c1s00，u/H/alpha/q 必须精确为零 | 旧 v1/普通 adapter 继续拒绝 pre-cycle；新轨迹保留首次 s00→s01 |
| 载荷精度 | immutable index 下的原 CSV token 显式映射到同档案 config 的 binary64 schedule；原 decoder 用这个独立派生 row 对 MAT scalar 做精确核对 | 无 load tolerance 放宽；原 token、index hash、config hash和派生完整精度值均保留；错 schedule/token/scalar 拒绝 |
| 疲劳公式 | 先用生产者 `min(1,(1-(alpha-alpha_T)/(alpha+alpha_T))**p)` 核对所有原 f，再由当前稳定 Carrara 式派生模型 f | 原来的 float64 8eps 相对容差、零绝对容差不变；错误 f 不能被先重算覆盖；alpha 不改 |
| 微负 H/q | 只对原索引绑定的五个已知异常点执行来源证明，派生为精确刚体平移对应的 H=q=0，逐点保存原值与证明 | 不增加负值容差，不通用 clip；任意新异常位置/非刚体位移/非零 d/不满足误差界都拒绝；u/d/alpha和其余 GP 不变 |

CSV 精度解释以实际档案绑定为准。精确 producer `finalize_stage0b_package.m:45` 调用默认 `writetable`，没有显式格式参数；本实现不声称源码指定了 `%.15g`。写出前，原 producer 在 :140–145 精确检查 row 和 MAT scalar；当前原 MAT 又与 config 完全一致。

## 微负值的来源

精确 producer commit `862992a60edc7f59335365beacb5c71fc8592a7a` 的 AMOR 代码先算 `Bᵀ C⁺ B`，再算 `0.5 u_eᵀ (Bᵀ C⁺ B) u_e`。它没有通过先计算局部应变来求能量。因此矩阵乘法与最终点积中的相消会影响接近刚体平移的能量符号。

针对三个状态文件的五个异常 GP，已重新核对 payload/static/index hash，并抽取完整单元节点坐标、位移、损伤、native shape/derivative 及相邻历史：每个单元四节点的 ux、uy 分别逐位相同；d 全零。因此，对满足分割恒等式的 Q4，其局部梯度严格为零，理论 H=q=0。H 与导出的 undegraded energy 相同，q 在 d=0、eta=0 时原样继承它。疲劳正部算子 `H_p(a)=0.5*(a+abs(a))` 不是这些负 H/q 的来源。

新规则必须同时有身份绑定、精确刚体平移和源运算误差包络，不能只凭 `1e-72` 的数值大小判定。验证器还要求每个相邻对的 raw 与 canonical `max(q_new-q_old,0)` 在 float64 下逐位一致；这排除修正改变后续疲劳累积增量。

## 验证状态

完整运行已结束，exit 0，268.305 秒；实际 CPU Torch 2.4.1+cpu，CITPC12，2线程，PID 36184。代码精确版本 `5a3b5d8c87b3ba804460dd52c2096c218aafe8e1`。执行前独立代码复核通过，120项回归通过；另有18项数学实现回归及独立推导复核。最终独立结果复核状态见下方回执。

| 全量结果 | U0.115 | U0.125 |
|---|---:|---:|
| 实际适配且完成契约验证的状态 | 516 | 366 |
| 实际相邻转移验证 | 515 | 365 |
| 完整范围 | c1s00 → c103s05 | c1s00 → c73s05 |
| 保留原 token 的载荷精度映射差异 | 206 | 0 |
| 刚体平移证明后派生 H/q=0 的 GP-时点 | 3 | 2 |
| canonical/raw 疲劳正增量逐位不变的转移 | 515 | 365 |
| 原 f 对 source 公式最大相对误差 | 2.219876e-16 | 2.219566e-16 |
| 原 f 对稳定式仍有差异的状态（原 8eps） | 305 | 150 |

source f 检查涵盖所有882个状态的所有原生GP，均在原8eps（1.776357e-15）相对阈值内，绝对容差仍为0。稳定式的最大相对差仍为9.809887e-15／5.259734e-15，没有藏掉或改变旧接口失败。两条轨迹含恢复初态、首次加载与最后卸载，去除174个别名重复；没有删掉任何物理步骤。材料、网格、初态数组身份再次相同。

新接口的H/alpha/q严格非负、d上下界、BC、d_lower、每对d/alpha单调和身份／时序检查全部通过。u/d/alpha未改，其余历史GP未改；raw数组适配前后摘要一致，原始文件只读。

完整检查走实际 Torch adapter、State.validate、TransitionRequest 和逐相邻 d/alpha 单调约束。采用 `iter_trajectory` 流式运行以避免保留整条大数组；必须耗尽后才发 admitted。原 load_trajectory 仍通过完全耗尽返回 list。独立预审发现 persistence 从初态出发会保留 source 子类，已改为显式构造普通 post-state，并增加完整 evaluator 的初态→加载→卸载回归。

### 数学检查的边界

证书用精确Fraction区间覆盖源几何重建、两种C⁺分支和四级矩阵／向量乘法，γ44来自6+6+16+16的运算预算，另有绝对下溢项和逐层溢出检查。五点负值绝对量为该推导界的0.000413–0.002596。其结论基于声明的IEEE binary64基本运算模型及精确source-family绑定；NumPy重算原二次式可正可负，不声称逐位复现原MEX。canonical零值来自刚体平移的精确零应变证明，而非观察到的负值尺度。

## 使用范围

已生成 [开发集划分与准入 manifest](fixed_weight_native_development_manifest_20261022.json)：U0.115 train、U0.125 development validation；没有未触碰 test condition。manifest记录接口资格，不启动或授权训练。两者共享 mesh/material/初态，只改变载荷幅值。接口准入不证明模型效果、相场平衡、capture-neutrality、状态充分性或真实道路外推。

初态原源代码的 recovery 收敛检查早于最终 d clipping，本次不追加求解或宣称 post-clip 平衡资格。历史中已有失败/不确定结论维持原范围。

代码入口：`source/fixed_weight_native_adapter.py`、`source/fixed_weight_roundoff.py`、`scripts/validate_fixed_weight_native_archives.py`。原始核验：[fixed_weight_data_audit_20261022.md](fixed_weight_data_audit_20261022.md)。本轮原始回执根：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/fixed_weight_adapter_20261022/`。


## 证据与独立复核

- [机器可读全量结果](fixed_weight_native_adaptation_20261022.json)：原始绑定、计数、五点原值／派生值／误差界、实际运行环境及代码身份。
- 本地case的 `validation.jsonl` 是全882状态的逐条记录；`execution_receipt.json` 和 `code_manifest.json` 记录精确代码及实际268.305秒运行；`code_review.md`、`mathematical_review.md` 为独立审查记录。`negative_energy_diagnostic/` 保存五点原字段、相邻历史、十份精确producer源码及抽取／分析脚本。
- 独立结果复核：通过。审查者将bundle的12个模块及runner逐字比较到精确提交；重新解析888条JSONL，核对882状态／880转移、初态／载荷／五点修正／摘要／exit0和complete。记录位于case的 `evidence_review.md`。原运行绑定中的 `validation-in-progress` 文字保持不变，完成后的资格写入独立development manifest。
- 非state的原SHA256SUMS成员仅检查存在性；state payload与index/static/config则按原身份核验。本报告不扩大为所有非state附件都重新做了内容hash。
