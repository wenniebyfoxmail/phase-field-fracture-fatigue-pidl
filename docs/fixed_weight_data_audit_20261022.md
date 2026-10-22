# U0.115／U0.125 完整原始档案与当前状态契约核验

日期：2026-10-22。Owner：`fixed-weight-learning`，继续 10-21 的数据清单。
目的：确认已有两条轨迹是否完整、其原生状态可否直接进入当前固定权重接口。
范围：C1／synthetic；既有档案只读核验，不是模型训练或 FEM 物理资格验证。

## 结论

**两条完整原始档案均在 CITPC12，文件与全部逐子步字段齐全；材料、
原生网格／GP 顺序和恢复后初态能够绑定。当前接口仍不能原样接收两条
完整轨迹，剩余问题是初始化类型和严格数值比较，不是缺少 FEM 解。**

本轮不需要生成新的 FEM 数据。用户允许必要时在 FEM 端生成数据的指示已
记录；现有核验没有发现需要重跑整条 FEM 才能补出的字段。未启动新求解、
训练或旧失败任务重试，未改原始文件，未调整当前契约或放宽其阈值。

## 远端完整性：由历史记录升级为本轮实查

完整源根均在 `citpc12-ssh` / `CITPC12`：

```text
C:\q4runs\hard5_new_runs_u0115_u0125_20260827_v1\hard5_u0115_stage0b
C:\q4runs\hard5_new_runs_u0115_u0125_20260827_v1\hard5_u0125_stage0b
```

| 核查项 | U0.115 | U0.125 |
|---|---:|---:|
| 物理循环 | 103 | 73 |
| 完整 s00–s05 逻辑索引 | 618 | 438 |
| 独立原生状态文件，含一个初态 | 516 | 366 |
| 原生 post-history 状态 | 515 | 365 |
| 后续 s00→前一 s05 别名 | 102 | 72 |
| 逐状态 SHA256 与已绑定索引一致 | 516／516 | 366／366 |
| 原生字段解码完成 | 516／516 | 366／366 |
| 状态文件总字节 | 7,644,978,713 | 5,341,579,398 |
| 原 SHA256SUMS 清单成员存在性 | 1,206／1,206 | 872／872 |

每周期子步集合、顺序、别名源、别名载荷／路径／哈希均检查；不是只数文件。
SHA256SUMS 中非状态成员只检查存在性，未把它们全部重新散列。状态文件、
static 和 config 身份单独核对。U0.115 的 206 个状态需要下面明确记录的
载荷小数序列化诊断路径，不能把“完成解码”写成旧严格 decoder 全部通过。

核验代码为 `201287a9` 的 `scripts/audit_fixed_weight_fem_archive.py`，
依赖复用原 `s09_stage0a_packet`／`s09_stage0a_capability` 底层函数，
没有套用仅支持 U0.125 的 73-cycle wrapper。脚本经独立只读审查后，通过
stdin 在 Python 3.12.3、NumPy 2.4.4、h5py 3.16.0 上执行；无远端脚本或
结果写入，单进程，数值库最多两线程，两个档案合计约 116 秒，exit 0。

所有大数组保留在远端。本地新增的是来源记录、逐状态 JSONL 和诊断摘要，
不能据此声称本地已保存全部原始档案。

## 已确认可复用的绑定与字段

| 项目 | 本轮结果 | 适配方式 |
|---|---|---|
| 材料八参数 | 两者均 `(E,nu,Gc,ell,alpha_t,p,eta,t)=(1,.3,.01,.01,.5,2,0,1)`；元素 material ID 全为 1 | `nu←ni`、`alpha_t←alpha_T`、厚度取 `geometry.t`；绑定各自 static/config |
| 网格 | 两者均 86,756 节点、86,408 Q4；坐标、连接、GP 权重及形函数数组哈希分别一致 | 可以共用同一 mesh identity；不能用不同 static 容器哈希判成不同网格 |
| Q4／GP | 原生顺序 `(+,+),(-,+),(+,-),(-,-)`；正积分权重；无重复单元节点或未使用节点 | 保持节点、元素和 GP 顺序；相对当前公式 N 最大绝对差 `1.11e-16`、dN `5.55e-17` |
| 边界 | fix_X 为上下边界共 298 节点；fix_Y 为底部 271；disp_Y 为顶部 27；与当前规则一致 | 全状态位移边界检查无超差，最大残差 `6.94e-18`；卸载零载边界也通过 |
| `u,d` | 全部原生 float64、有限；所有 d∈[0,1]；全相邻物理状态 d 无下降 | 保持原生节点；按精确 producer 提交规则显式派生 `d_lower=d` |
| `H,alpha_bar,q_prev,f` | 每个状态都有 `[E,4GP,4]`；alpha 全程非负、无下降；H 与导出的当前未退化能量逐点相同 | 保留 `[H,alpha_bar,q_prev]`；f 是待校验的冗余导出量，见下表 |
| 时序与动作 | 原生 s01–s05 为 post-history-commit；加载／卸载序列完整 | 用真实 imposed displacement，创建连续 ordinal／branch，去除别名重复 |

两份 static 容器 SHA 不同，因为它们还包含各自 case configuration；不能
用“整个 MAT 不同”代替内部 mesh/material 内容比较。对应的数组身份和每个
run 的索引、config、static hash 均保留在同名 JSON 摘要。

## 初态确实存在，但当前类型不接收

两个 `c0001_s00` 的 u、d 和四历史通道分别逐位相同；实测 u=0，H=0，
alpha_bar=0，q_prev=0，f=1，d 有界。精确 producer `862992a...` 的顺序是：
零能量相场 recovery → 收敛检查 → d 截到 [0,1] → `p_field_old=d` → 疲劳
历史重置 → 捕获 `pre_cycle_committed`。

因此它是恢复并重置后的初态，不是未求解的 hard-crack 初猜，也不是正常
加载子步的 post-history-refresh。当前 `StateKey`／adapter 只接受
`post_history_commit`，不能通过换标签接入。可选的明确适配工作是：

- 为这一精确 producer 增加独立的 recovered-initial 类型／入口，保留原始
  timing 和 recovery/reset 来源；不改变普通 post-state adapter 的拒绝规则。
- 若接口保持不变，只能从 c1s01 开始 continuation：515／365 states、
  514／364 transitions，明确省略初始加载转移。这仍需解决下面数值条件，
  并不因为省略 s00 就成为已准入完整轨迹。

源码的 recovery 收敛检查位于最后 d clipping 之前；本轮没有额外验证
clipping 后初态的相场残差，不把“初态存在且相同”提升为平衡资格。

## 当前严格接口仍拒绝的部分

| 项目 | U0.115 | U0.125 | 性质／下一项适配工作 |
|---|---|---|---|
| CSV 与 MAT imposed displacement 精确相等 | s01、s02 各 103 状态，共 206 次失败；最大差 `6.94e-18` | 无失败 | MAT 真实值与 config 的 effective_uy 全部精确一致；需明确完整精度载荷映射和 CSV 序列化比较，不能默改原 CSV |
| H／q 严格非负 | c58s05、c87s05，共 3 个 GP 点；最低 `−3.5241e-72` | c58s05，2 个 GP 点；最低 `−1.5666e-72` | H 与原始能量相同，q 继承同一微负值；alpha 无负值。需有来源依据的数值零处理方案，尚未重建 AMOR 应变来证明负值产生机制 |
| 冗余 f 与当前 Carrara 式的 8eps 相对一致性 | 305 个状态，1,229 个 GP-时点超差；最大相对差 `9.8099e-15` | 150 个状态，301 个 GP-时点超差；最大 `5.2597e-15` | 当前阈值约 `1.7764e-15`；生产者与接口的浮点运算表达式不同，见下文 |

这张表的全量计数来自 **NumPy float64 谓词扫描，不是完整 PyTorch loader
执行**。另用当前实际 Torch `carrara_f` 核对了六个定点诊断样本；两个最大
差异点均重现当前 8eps 拒绝，负历史值也不满足实际非负谓词。没有安装远端
Torch、修改契约、投影原始状态或丢弃失败步骤。

全量扫描中，同时满足旧严格 decoder 和数值谓词的 post-state 只有
U0.115 的 129／515、U0.125 的 215／365；这些是散布于轨迹的状态，
**不是可删掉其余步骤后拼出的完整训练轨迹或有效 split**。

### 疲劳因子的已定位差异

Producer 精确源码使用：

```text
f = min(1, (1 - (alpha-alpha_T)/(alpha+alpha_T))**p)
```

当前接口使用代数等价的稳定表达式：

```text
f = min(1, (2*alpha_T/(alpha+alpha_T))**p)
```

U0.115 最大差异点 c100s04 / element 47853 / GP 3（零基）：
alpha=`31.74907345088553`，export f=`0.0009615359297028576`；
producer 式给出相同值，当前 Torch 式为 `0.0009615359297028481`。
U0.125 最大点 c68s01 也逐位匹配 producer 表达式。六个复核状态的所有
GP 按 producer 式检查均未超 8eps，最大相对误差不超过 `2.18e-16`。
这支持所查状态存在算术路径差异，不是该处缺少疲劳历史。

目前未对全部超差点重建 producer 表达式，也未据六个状态扩张为全量来源
等价证明。后续可设计来源感知的 f 校验／派生规则，保留原始 f 和稳定表达式
的差异；不能把本次观察到的最大差直接改成新的通过阈值。

## 适配清单与数据生成决定

**可以直接复用的内容：**完整原生文件、节点 u/d、四 GP 历史、已绑定的
material8、共同 mesh、完整子步索引和实际载荷元数据；普通 post-state
映射、别名解析和 `d_lower=d` 均有明确来源。这里“复用”不等于两条完整
轨迹已经通过当前 loader。

**仍需完成的适配：**独立初态入口；完整精度载荷来源；保留原值的 f 运算
路径核对；微负 H/q 的来源诊断及数值零规则。完成后才可建立新的有明确
范围的 qualification_ref 和执行用轨迹 manifest。当前不生成这些通过声明。

**目前无需 FEM 重算或补导出。**重新求解并不能自动解决接口对初态类型、
CSV 精度和不同浮点公式的要求。若后续的负能量来源诊断发现实质数值问题，
或要取得新的独立工况，再以相应目的明确限定 FEM 生成工作；不复活旧
U0.1175 失败启动的重试，也不把新的重复计算当作全新物理条件。

训练／验证／测试结论仍与 10-21 一致：两工况都已有开发暴露；U0.115 训练、
U0.125 开发验证仅是完成适配后的候选；当前无已准入三分集合，也无匹配的
未触碰测试条件。完整性核验不改变既有 reference/capture-neutrality 限制。

## 证据与复核

- 可机读摘要：[fixed_weight_data_audit_20261022.json](fixed_weight_data_audit_20261022.json)。
- 本地完整回执目录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/after_strict_setting_alignment/fem/fixed_weight_u0115_u0125_audit_20261022/`。
- 该目录的 `full_audit.jsonl` 保留全部状态检查；`execution_receipt.json` 记录实际执行；`audit_code_manifest.json`／`audit_stdin_payload.py` 记录精确代码；`formula_diagnostic.jsonl` 和 `torch_scalar_diagnostic.json` 记录定点复核；`00_intent.md` 记录授权与边界。
- `analysis/contract_inventory.{png,pdf,csv}` 将文件完整性与接口标记分别展示；同目录 `README_analysis.md` 说明含义，绘图直接读取 JSON 摘要，渲染与 Obsidian 图像链接均已核对。
- 精确 producer 源目录：`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s09-e007-fixed-damage-holdout-20261012/local_archive/experiments/S09-E008/producer_provenance_20261016/source/`。本轮独立审查确认所用 16 份本地 source blob 与来源 manifest 匹配。
- 该源目录下：`Scripts/fatigue_fracture/run_SENS_hard_recovery_native_q4_capture.m:164–199`（初态）；`solve_fatigue_fracture.m:182–226`（提交／刷新／捕获）；`Sources/+phase_field/+mex/Modules/fem/assembly/pf/at1_penalty_fatigue.f90:89–99`（H/alpha/q/f）；`Sources/+phase_field/+audit/write_stage0b_static.m:24–88`（静态绑定）。
- 独立结果审查重新聚合 JSONL，确认全部 882 状态、两组 manifest 存在性、共同 mesh/material/initial 与上述失败计数；最终报告审查无阻塞意见，指出的索引哈希指针已补入 JSON。没有把扫描完成解释为契约全部通过。
