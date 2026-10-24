
**2026-10-24纠正：本文件仅核R2子集；后续R3–R008已纳入[真正当前owner](/Users/wenxiaofang/phase-field-fracture-with-pidl/worktrees/fem-surrogate-solver-repair-v6-20261020/docs/research/S04/hybrid_constrained_design_20261019/training_readiness_20261024.md)。旧600秒候选已撤回、未部署；不要用135.773h作为当前全链余额。**

# R2终态、复用与最快训练安排（2026-10-24）

目的：沿原owner核清已提交R2，结清费用，尽快获得可训练标签。工作模式为已有证据核查＋本地控制准备，不新建科学尝试；本轮只有一次20秒上限的远端只读查询，未解码科学数组、求解或训练。原D13接受态与字段契约继续使用。

## 已核实的终态与产出

R2准确源d703e3c8／artifact7c150a68／card f3cc0463，在 **2026-10-20T19:07:25.839732+01:00** 首停；本轮 **2026-10-24T20:07:17.834714+01:00** 核实terminal.status=failed，原3个PID均不存在，指定run路径也无匹配进程。78份原源文件SHA、精确卡、事件、state0/state1/features与latest快照字节一致。旧终态与20日后续只读材料相符；上轮19:06快照已经过时，本轮纠正原owner入口。

| 阶段 | 实际产出 | 墙钟秒 | 结果 |
|---|---|---:|---|
| 绘图依赖 | Agg/PNG/PDF通过 | 3.154383 | 执行环境证据 |
| 原生回放 | 已见5态通过 | 9.430831 | 原算子证据 |
| train_A | 接受1/600；step2未接受 | 157.477526 | physical-substep120s deadline，SIGTERM |
| 其余5条轨迹 | 0 | — | 未启动 |
| fit / checkpoint | 0 / 0 | 0 GPU秒 | 未启动 |

第一步34.249059秒只是一接受子步，不是phase总耗时。完整周期0、完整标签轨迹0、新字段契约合格标签0。当前训练入口缺1200训练＋600验证；**无需等1800测试步，标签齐备就应fit。** 未对输出场重新求解，所述物理通过来自原封存证书，非本轮独立残差重算。

## 停在哪里，以及下一次该改变什么

已存在的诊断日志与远端当前SHA逐一吻合，直接复用，不再重做诊断。step2完成9QP、8次fresh检查；最后机械Ru L2=4.71125e-15，fresh damage KKT∞=4.21680e-7，仍高于1e-7。f<1点数0、fatigue residual0，不能归因于尚未发生的NN或疲劳反馈。机械工作75.48秒、damage QP26.41秒（嵌套LU不重复加）；联合残差仍下降，记录没有证明数学不收敛或近奇异。

![原R2残差与120秒截止](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/fem_surrogate_comparison_preparation_20261020/execution_v1/timeout_diagnosis_20261020/step2_residual.png)

此处正式图直接复用原归档：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/fem_surrogate_comparison_preparation_20261020/execution_v1/timeout_diagnosis_20261020/step2_residual.png`。看到：残差下降但在120秒仍高于物理阈值；31%改善的候选未满足原50%保护而回退。说明：首停是计算保护与外层成本的瓶颈，不能靠放宽KKT或提前fit解决；更长时间不保证全轨迹能完成。

最短前瞻候选是 **保留原求解算法和Anderson规则，只把单子步计算保护120秒改为600秒**；phase20h、总136h/12GPUh、max_outer100、force/KKT/历史精度全部不变。现有末段约0.87收缩若持续，约还需11个map；根据已完成map成本，旧step2可能需约4–5分钟。这只解释600秒的工程余量，绝不是收敛预测或已测性能。即使更久接受，也只证明新计算额度下的可达性，不能把收益归于未改的Anderson或NN。

不在这轮同时上Krylov/新预条件器、重写Anderson或扫保护参数，以免把“能否给够计算工作”与新算法收益混成一个问题。如果600秒/phase总额仍不足，先按新尝试首停，利用已保存fresh分量选择真正的算子/联合求解改造，不继续自动加时。

## 已结清预算

- R2之前已计费：625.698780406秒。
- R2 producer本次：171.379771518秒；phase合计170.062740269秒，另有supervisor overhead1.317031249秒。cost_ledger.wall_seconds只是旧费用＋phase，**必须使用total_job_wall_seconds=797.078551924**，不能把两个字段再相加。
- dispatch本地：5.258660625秒；已记录的两次20日状态查询（含未连通sandbox本地耗时）、一次日志查询、本轮查询，合计13.517316375秒，仅计一次。
- 可追溯累计主机墙钟：**815.854528924秒，余135.773374小时**。GPU实际消耗0，余12小时；实测producer CPU含旧费用833.543593秒，metadata/dispatch CPU未测，账本对其按16核墙钟上界保守计费，不冒充实测CPU。
- 原120数值小时账本余119.861812小时；原3600步是完整比较设计，不能由已接受1步推导出可直接续跑3599个新合同目标。R2尝试2、接受1、未访问3598；新合同的3600目标均未满足。首停后可用新科学尝试数仍为0，fit容量未用1次也不等于当前执行许可。
- 当前主目录90.561MiB，归档43.709MiB；全新契约payload＋20GiB余量估算106.51GiB/份，仍在原128GiB/份上限内。实际启动时另查可用256GiB，不把硬上限当已证空闲。

机器可读账本：[r2_reconciliation_20261024.json](r2_reconciliation_20261024.json)；逐项复用/缺口：[r2_reuse_and_gaps_20261024.csv](r2_reuse_and_gaps_20261024.csv)。所有原始snapshot、查询收据及SHA在`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/fem_surrogate_comparison_preparation_20261020/execution_v1/reconciliation_20261024`。本轮下载的是metadata/NPZ头与证书，不是完整数值数组镜像；原始状态和features仍留在原archive，不重复镜像无用的大文件。

## 复用和必须补做

直接复用原mesh/material/state0/载荷、已有算子回放与环境证据、D13代码、4×64网络、loss/seed/split，以及R2完整失败诊断；不重做全文回归或独立审核。执行时只做必要身份/漂移机械核查。

R2第一步只保留回归和溯源作用。它的原K约束接受证书存在，f_min=1且fatigue residual0也可作局部描述；但没有D13原生f_solve/raw分存，且没有连续轨迹，**不为节省一个约34秒点而新增旧标签升级机制**。step2所有trial不作接受标签，不从旧R2续写或热换源码。

必须重新从共同state0生成train_A600，再完成未启动的train_B600和validation600。三条每条120周期、自身历史、完整新字段契约。测试三臂各600在冻结模型之后才生产，不作为进入训练的前置条件。

## 下一步的一次完整执行安排（当前禁用）

| 顺序 | 实施 | 原阶段上限 |
|---|---|---|
| 本地准备 | 同owner接入600秒明确修订；固定metadata基准、准确manifest/卡实例化 | 机械工作计入总账，不再前置独审或一串smoke |
| teacher生产 | A(.8)/B(1.2)/validation(1.0)，原NN-off受约束校正，新字段合同，各600 | ≤20h/条，合计≤60hosth |
| **自动进入fit** | 1800条完整核验后立即一次训练；1200训练＋600验证 | ≤6GPUh；原20000更新/early-stop |
| 冻结后测试 | reference/classical/hybrid，各.9、各600、自身历史 | 20hosth＋20hosth＋6GPUh |
| 统一分析 | 原质量、f<1覆盖、反力/历史与相对两强基线10%在线收益判据 | 准入/回放/分析共用原4hosth |

phase合计最大116hosth，早期费用保留，从当前135.77hosth余量扣除；原总预算不扩大。600秒是局部上限，不能用3600×600再追加费用，也不能用总预算补超单phase。hybrid6h/600仍要求平均≤36秒；这里没有保证加速或完成时间。

准备卡：[training_entry_preparation_card_v6.json](training_entry_preparation_card_v6.json)，execution_enabled=false、null RunID。600秒支持只作本地可审阅控制准备；拟用源文件与签过的R2旧码分开。将来一次边界授权须明确包含：**首停后的一个fresh科学尝试、120→600秒计算保护、新3600设计目标、1800齐备立即一次fit及冻结后测试，沿用原总预算与首停不重试。** 这不是辅助库/路径元数据审批；当前用户要求的是核查与下一步安排，没有启动新FEM或训练。

若获这一次完整授权，agent在该包络内自动完成必要机械绑定与部署；不逐字段再问、不自动追加独立审核。若teacher未全且不合格，不训练；若标签齐备，直接进入唯一fit；若算子或任一阶段首停，保留结果，不创建绕过预算/次数的新RunID。

## 本轮唯一固定基准（实现前登记）

模式：既有证据C1核查＋本地控制准备。无新科学验证。代表输入为本次真实R2对账收据及禁用v6卡（原生state0/数据身份不变）；对照为未改的120秒卡。只检查明确600秒修订的识别、未授权启动拒绝、准确预算扣减和原物理精度/phase设置不变。

固定命令：`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=source:tools:.:tests <原owner venv>/bin/python -m pytest -q -p no:cacheprovider tests/test_hybrid_training_entry_preparation.py`；之后用原打包器指定v6卡/manifest构建本地禁用包，原supervisor `--check`核准确包/卡/inputs。预期：控制准备通过、两类卡均不能启动、无数组解码/求解/训练。通过即交付，不加全套回归、其它smoke或独审。

本轮结果：唯一固定元数据基准1项通过（0.33秒）。原owner现已支持明确标识的600秒卡及按真实上限写guard原因；打包器可选择本次卡/源清单。原v5/已用R2科学卡及收据保留，未重跑130项或新增独审。新准备包保持禁用，尚无600秒实际收敛/成本证据。
