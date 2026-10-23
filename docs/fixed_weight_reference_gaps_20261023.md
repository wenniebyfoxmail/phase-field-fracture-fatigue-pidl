# 独立测试与 FEM 参考资格：现有证据及最小补齐方案

日期：2026-10-23，Europe/London。Owner：fixed-weight-learning。
模式：C1 只读证据盘点与方案；继续已完成的原生状态适配，不启动训练、FEM 求解、旧基准重跑或新增审核。检查现有源码／记录，以及 CITPC12 目录、已暴露数据的索引和资格回执。U0.1175 仅查身份／封存／字段／既有终态完整性元数据和访问脚本，未打开其目标数组或事件值。本轮不改变保护数据用途或解除封存。

**结论：有现成的独立测试候选，优先复用 U0.1175 fresh-v10；但独立性和当前接口资格尚未补齐。物理资格的主要缺口是最终接受状态的数值收敛证据、离散误差证据和匹配的独立实验观测。已有接口通过与采集一致性证据可直接复用，不必重新求解五条已暴露工况。**

## 1. 两处需要更新的旧判断

1. **U0.1175 已经生成。** 10-21 清单引用的共享 outbox 停在 v7/v8。实际资产 owner 的 10-12 记录及本轮远端元数据确认，fresh-v10 从 c0 完成、封存；不是 v9i partial 续跑，也不依赖尚未执行的 v12 恢复探针。因此不应继续把“未生成”作为补跑理由。
2. **旧三个幅值有后来生成的完整 native Stage0b 索引。** 旧 `psi_fields` 确为峰值能量＋圈末 d/history 的混时 carrier，但该限制不能外推到 Windows 的另一套 `hard5_native_q4_existing_u011_u012_u013_20260827_v1` 包。本轮索引元数据分别为 626／431／311 个独立 payload，s00–s05 齐全；当前只核元数据，不据此宣称已通过新 Torch adapter。

上述为 10-23 的增补；原先日期的失败、检查范围与结果保留。

## 2. 可复用工况与独立性

下表角色指本 fixed-weight 任务；原 S04-E016 的保护与允许信息约定继续适用于其封存资产，不由这张候选表改写。

| 工况／资产 | 现有证据 | 当前可以承担的角色 | 尚缺什么 |
|---|---|---|---|
| U0.115／0.125 | 已通过 516／366 状态及 515／365 转移的新接口；两者已有开发暴露 | 保留训练池／开发验证池；复用全部现有准入记录 | 不能恢复为未触碰测试；数值 teacher／实验资格另见下表 |
| U0.11／0.12／0.13 native Stage0b | 本轮远端完整索引 626／431／311 payload，sealed；旧模型已使用三个幅值。native producer `53ce560…` | 三个额外开发候选；可以降低重新生成数据的需要 | 绑定各自 static/material/actual schedule 与新接口，检查完整原生字段及逐步约束；现有两-run adapter 只允许 `862992…`，不能直接改标签加入。metadata 完整不等于新契约准入 |
| **U0.1175 fresh-v10** | 完整封存记录、原生 u/d/GP history/energy 字段清单；本轮远端 identity/health 与原 owner 一致，parent `862992…`；overlay 只替换 text logger | **最强的现成 confirmation/test 候选，继续封存** | 同条件 partial 的允许信息／访问用途核对；当前任务的测试协议；受控的完整新接口准入；相应数值参考资格 |
| Ferrite 2×2×2 pilot | 原 6/1/1 split 保留，`u012_tsoft_mwet` 为 protected；未保护代表包保留初态和各圈 peak/unload，reduced export 是抽样 cell means | 保留原研究用途；若已有完整 checkpoint，可考虑重导出 | 当前全子步 nodal/GP 状态未建立；不能打开 protected 包来修接口。更换 solver/state semantics 的成本高于优先复用现有 native 包 |
| Ferrite revised geometry、SYNMEM、MOOSE | 不同 geometry/BC/状态或原有否定结论 | 原范围的诊断／控制 | 不能作为同固定网格模型的即插即用独立工况 |

精确旧到新 producer 的 `git diff --name-status 53ce560… 862992…` 已保存。本次变化限 case/config/queue/seal/tests 和 capture 中 run_id 元数据，未列出 AMOR、AT1、solve 或材料内核修改；这是进一步复用的正证据，仍须绑定每个包实际的配置和数组身份。

### U0.1175 为什么仍不能直接贴上“未触碰”标签

- exact root：`C:\q4runs\request31_u01175_confirmation_20261011_v2\hard5_u01175_stage0b`。
- run：`hard5_u01175_stage0b_839c82fc5eaf4f37bee7f70aca268ce0`；完整封存身份见原 `TERMINAL_AUDIT.json`。
- 原 S04-E016 明确将 .1175 指定为 final interpolation confirmation，只允许 metadata／validity booleans／封存身份，不 fit/tuning；后续开发记录继续写 confirmation closed。
- 同幅值旧 v9i partial 曾载入 c63/c64 checkpoint 做恢复诊断。只读审计脚本不输出 u/d/history 场值，但会输出 `penetration_detected`、confirmation counter、`native_q4_event_state` 中的 first-hit/confirmed/censor 字段。因此它**不只是结构检查**。本轮只读了脚本，未读取这些事件值。未找到其用于固定权重模型拟合或调参的证据；这也不能证明整个条件从未暴露目标信息。
- v10 的完整文件保持 sealed，并不使同条件旧 partial 成为独立样本。partial、fresh repeat、切片和所有衍生导出应同组。

**决定性补件**是访问用途记录与当前允许信息约定：谁见过哪些字段，它们是否进入特征、normalizer、模型／超参／预测起点／评估窗口选择。若原保护政策和当前确认性定义允许这种工程诊断信息，可将其作为有披露的独立确认条件；若要求目标完全未知，就不能把历史访问“清零”。后一情形才需要另一个无开发暴露的条件。

## 3. 哪些“物理基准”证据已有，哪些仍缺

| 资格层次 | 可直接复用的现有证据 | 决定性缺口及最小补件 |
|---|---|---|
| 数据接口／来源 | 两条轨迹 882 状态／880 转移已通过实际 Torch；材料、mesh、初态、实际载荷和 history 语义已绑定 | 此层已完成，直接复用；不再重跑 120 项回归或完整适配来增加信心 |
| capture／重放一致性 | **同精确 `862992…` 的 U0.12 c1 v5 已通过**：6 states，s00 d 差0，s05 d/u 最大差约 5.0e-16／1.4e-17，c1 文本和五子步 convergence anchors 差0 | 复用为同版本 hook／重放证据。U0.115/.125 自己的 receipts 中 `reference_checked=false`、`capture_neutrality_passed=false` 仍保持原值；不能把 v5 外推成两条全程平衡证据 |
| **最终保存状态的数值一致性** | 原生 u/d/GP histories、前一接受状态、source、mesh/BC；原 CONV/stdout、reaction/crack 文本可定位复用 | 缺最终 clipping／history refresh 后的自由位移残差、相场离散残差及适用的约束检查。需绑定原 penalty/active DOF/recovery 和旧 history，先从现有 fem_archive/checkpoint 抽取；模型 material8 本身不包含这些求解参数 |
| **耦合固定点稳定性** | 原日志有残差与 energy；历史 U0.13 c5 有明确反例：小 residual/KKT 可伴随 Δd∞=0.0742（GRIPHFiTH）或0.0256（Ferrite） | 当前两条轨迹未有相同范围的连续 stagger Δd 证据。先查原 checkpoint 是否保存所需前后迭代；若没有，仅靠文件检查补不出。只有目标要求“收敛 teacher”时才提出一个明确范围的原位固定-history 验证；不自动重跑全部轨迹 |
| **网格／加载离散误差** | 旧 mesh/cadence 比较存在，但不是这两条精确设置的合格对照；不同幅值也不是离散收敛对照 | 缺同物理设置下可追溯的 h、载荷子步／solver tolerance 敏感性与输出误差。优先查已有匹配对照；缺失时保留“固定网格五步档案参考”范围，后续只为需要的更强主张设计一套固定开发工况对照 |
| **实验／物理有效性** | 目前查到的 Hard5 证据是合成参数、代码／数值比较 | 缺与材料、试件、预裂纹、边界、载荷历史匹配的独立反力／位移及裂缝演化观测，含参数标定来源、测量映射与误差。不同 solver 一致或稳定残差均不补足这条证据链 |

这里“数值参考”指复现声明的离散求解器输出；“数值 teacher”进一步要求受监督输出在其使用范围内具有足够的数值可信度；“物理资格”还要求独立观测。H/alpha/q 是模型内部状态，反力或裂缝观测吻合也不使它们自动成为直接测得的物理真值。资格必须按输出和使用范围给出。

### 为什么不能直接读取 metadata 的 residual 就结案

Exact source 在 Newton 后还执行 d clipping、力学重算及最后 history refresh。`producer_metadata/res_displ,res_pf` 可能仍是较早 Newton 值。`provenance/convergence/<state>.log` 又只是 `jsonencode(row)`，不是内部 stagger 轨迹。

原 CONV 表应按物理 state key 对齐复用，但它也未输出逐 stagger Δd。计算 phase 残差需取**前一个物理状态**的 d_old/alpha/q，再用当前 u/d 与正确源离散算子构造；不能把已经提交的 history 再当成旧 history 累积一次。Penalty 残差也不能直接改称 bound-aware KKT。初态须检查 recovery 最后 clipping 后的状态。

旧 U0.13 c5 的否定结果限定其版本和状态；它说明 Convergedflag 不充分，**不直接判定新 U0.115/.125 失败**。当前 `physics_diagnostics` 只覆盖部分力学／history 诊断，明确跳过 phase KKT，也未在此次接口准入中执行；其代码存在不是物理资格结果。

## 4. 最小补齐方案

### 首选：零新增 FEM 轨迹

1. **沿用已通过记录，整理现有六幅值的候选角色。** 当前正式 admitted 仍只有 U0.115 train、U0.125 development validation。若三条旧 native 包适配后通过且 U0.1175 独立性成立，可沿用原来六工况方案：train={.11,.115,.12,.13}、validation={.125}、test={.1175}。这是候选，不修改现有 manifest，也不以字段数/窗口数凑工况。
2. **先补独立性与测试协议。** 核清 .1175 partial 访问用途；冻结 whole-condition membership、允许输入、完整载荷动作、评估起点／horizon、训练侧 normalization，以及 persistence／同分支 secant 比较。起点和窗口不得依赖测试 FEM future event。保持原封存，只有用途明确且原保护政策允许后才做受控准入／一次性评分；本轮不解除封存。
3. **用未保护开发档案补一套固定数值资格证据。** 复用 v5、原 source/CONV/stdout，抽取实际 penalty/DOF/recovery；准备对所声明范围内最终状态的原离散残差、初态 post-clip 和 history 因果一致性的一次完整分析。任何新计算的范围／判据先在原 owner 记录固定，完成即交付；不追加 smoke 阶梯或反复回测。现有残差／固定点阈值只对原锁定任务有效，不能无说明照搬或按观察值放宽。

此路径的新 FEM 完整轨迹数为 **0**，训练次数为 **0**。缺失内部迭代或实验真值时明确保留相应资格未建立；不能用更多接口测试替代。

### 仅当仍有决定性缺口时

- **严格未触碰测试不能复用 .1175：**先查是否还有已封存、未开发的同族档案；没有才提出**一条**新幅值完整轨迹。可沿原 metadata-only 后备顺序核对 .1225，再考虑 .1275，不能依据新测试结果择优。新 seed／重复跑 .1175 不增加独立工况。既有五个暴露条件全部复用。
- **要升级为收敛数值 teacher，但缺迭代证据：**仅在已暴露开发工况，固定原始旧 history/载荷及接受状态，设计能检验 source stagger 稳定性的有界验证。若只覆盖局部状态，其通过范围就限定该局部；不以一次额外迭代替代全程资格。U0.1175 不承担开发调试。
- **要升级为物理验证：**先选择已有匹配实验资料及可观测输出，固定单位、参数标定／验证分离、观测映射与比较误差。无匹配资料时，该缺口无法靠 FEM 复算补齐；需要另行确定实验来源与使用范围。

这些是后续方案，不是新求解、训练、保护数据访问或费用许可。本轮只保存证据盘点与最小方案。

## 5. 证据定位

- 本轮 case：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/fixed_weight_reference_gap_audit_20261023/`。`remote_metadata_inventory.jsonl`、`remote_qualification_receipts.jsonl` 和 `producer_source_delta.txt` 对应上述 live metadata 与 source 比较；脚本均留存。
- 当前接口结果：[fixed_weight_native_adaptation_20261022.md](fixed_weight_native_adaptation_20261022.md)；当前实际划分：[fixed_weight_native_development_manifest_20261022.json](fixed_weight_native_development_manifest_20261022.json)。
- S04-E016 authoritative owner：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-e016-request31-storage-block-20261009/`。相对于该根：`docs/handovers/windows_fem_outbox.md:29–51`（v10完成与保护）；`docs/research/S04/S04-E016/g5_contract_role_input_audit_20261012.md:45–67`（角色／允许信息）；`experiment.md:93–112,183–204,373–384`（fresh-v10、partial、开发仍closed）；`local_archive/experiments/S04-E016/request31_v10_terminal_audit_20261012/windows_audit/{TERMINAL_AUDIT.json,field_inventory.csv}`（终态／字段）。
- partial 访问审计脚本：上述 owner 下 `local_archive/experiments/S04-E016/request31_u01175_failure_freeze_20261011_v1/run_request31_checkpoint_matlab_audit.m:24–42,73–85`。本轮只读脚本，未读其事件值。
- 物理 source 根：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s09-e007-fixed-damage-holdout-20261012/local_archive/experiments/S09-E008/producer_provenance_20261016/source/`。其下 `Scripts/fatigue_fracture/solve_fatigue_fracture.m:115–148,182–194,235–261`，`run_SENS_hard_recovery_native_q4_capture.m:164–199`，`Sources/+phase_field/+mex/Modules/fem/assembly/pf/at1_penalty_fatigue.f90:85–119`。
- 旧固定点反例：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/handoffs/ferrite_hard5_locked_handoff_20260801_staging/docs/u013_c5_teacher_decision.md:40–50`；旧离散／实验资格缺口：`.../local_archive/after_strict_setting_alignment/fem/pidl_griphfith_hardsoft_step_audit_20260819/confirmation_report.md:45–52`。
- Ferrite 原 split、代表文件与 reduced carrier 的路径详见 [10-21 数据清单](fixed_weight_data_audit_20261021.md)。原保护 split 不变，本轮未打开其 payload。
