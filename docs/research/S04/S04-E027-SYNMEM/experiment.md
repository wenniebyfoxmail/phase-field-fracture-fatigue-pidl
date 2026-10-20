# S04-E027-SYNMEM — 最小合法历史合成机制验证

2026-10-20 · protocol 1.0 · 以下保留原冻结准备方案。

**当前结果（2026-10-21）：**另获HQ前瞻v2单次权限后，R003完整完成并得到负结果：三配置内当前两臂严格相同，H20两臂差均0；1846接受转换及200未来重放逐步核验。停止扩库/训练，授权已关闭；见[v2结果与路线判断](results_v2_20261021.md)及[v2修订](protocol_v2.md)。原v1的R001/R002控制故障、跨网格8像素必要条件反例与未完成结论保留于[原记录](results_20261020.md)。下文仍为v1冻结准备方案，不是当前运行指令。

目标锚点：observation → state → evolution → prediction；延续 BRIDGE-PS 的 D4。上一轮真实数据没有已证严格匹配组，旧c1/c11标量近似掩盖局部场差。本次用户选择先准备最小synthetic机制验证，补生成器、独立审查，确认后再跑。保留原B探索结果及原求解器失败记录，不继承其数据、运行、重试或预算许可。

主owner为本Experiment，主Storyline S04，C3 transition信息机制，domain=synthetic。数值生成器角色为**机制诊断候选**，非合格物理teacher。只检验Q1；不训练、不评估Q2响应历史预测收益，也不宣称道路/材料迁移。

## 决策与复用

D1已完成：复用上一轮数据/源码核查及受约束AT1–Amor–Carrara实现。新工作树 `codex/synthetic-memory-mechanism-20261020` 从明确提交 `62cf787f8ad1d8ffd9b91b4bec4566714e6e510e` 分出；未复制其他owner的未提交文件。复用 `hybrid_incremental/history/transaction/state_contract`、v6接受态检查和绘图基础；新增输入、观测、编排与专属监督器，原生产runner与原same-problem比较合同不改。

Active D4：实现并审查此参数/观测/共同续载设计 → 用户一次确认具体producer/预算后运行 → 按冻结判据决定是否值得加更强观测。小网格用于解决可达历史与观测非充分性的实际阻塞，不以均匀patch的已知本构现象替代裂纹几何问题。

## 固定试件、材料与前史

全部数值为归一化模型量，不对应一份已标定实物材料。

| 项目 | 冻结值 |
|---|---|
| 域/预裂 | [-0.5,0.5]²；y=0、x≤0的左边缘预裂，tip=(0,0) |
| 主网格 | 16×16 Q4，256单元/289节点，2×2原生积分 |
| 空间敏感性 | 32×32 Q4，1024单元/1089节点；域、预裂、材料、ell均不变 |
| 材料 | E=1、ν=0.3、Gc=0.01、ell=0.125、alphaT=0.005、p=2、thickness=1、eta=0 |
| 位移边界 | top uy=+U/2，bottom uy=−U/2，bottom-left ux=0，其余ux自由 |
| 原始初态 | 预裂节点d=1，其余d=0；u/A/r/opaque=0，f=1；这仅为可行初始化 |
| 接受初态 | 每臂先合法zero-load settle；两臂完整数值字段必须相同；不把原始尖锐seed冒充平衡态 |
| low前史 | 20cycles，峰值总开口U=0.005 |
| high前史 | 20cycles，峰值总开口U=0.010 |
| 共同探测 | 1cycle，U=0.005；卸载末端为原点，探测引起的演化照常提交 |
| 共同未来 | 20cycles，U=0.030；H20为唯一主终点，H5/H10只解释过程 |
| 基础cycle | [0.25,0.5,0.75,1,0]×峰值U |
| 加载步长敏感性 | 每段二等分：[0.125,0.25,0.375,0.5,0.625,0.75,0.875,1,0.5,0]；包括卸载 |

alphaT相对Gc/ell是本人工模型的预设选择，不能沿用旧大网格teacher身份。远场线弹性尺度下两个前史的累计驱动小于alphaT，而共同未来可跨过alphaT；裂尖集中、损伤反馈、实际激活和mask匹配均未验证。没有阳性承诺，也不按输出改幅值、alphaT、循环数或选原点。

两条前史从同一解析几何/材料/初态定义推进；A_new=A_old+max(r_new−r_old,0)仍由已接受旧态及最终场单次计算。内层迭代不重复累计，不手改A/f/d、不拼场。每个数值版本两臂各自zero-settle，保留原transaction完整schedule与parent链；以完整字段比较相同settle，不把不同load_id导致的fingerprint差误判为物理差。

## 当前观测匹配

本次I0仅为**固定数字几何观测**，加共同材料、几何、年龄、原点相位与未来计划。过去载荷有意不同，不是I0的匹配量。结果不能证明已知全部加载的强基线仍缺信息，不能证明响应历史能恢复状态，也不能单独归因于A：隐藏d等字段可同时不同。

固定64×64全域像素中心，按原生Q4双线性插值得到d_sample，主mask为d_sample≥0.5。它是合成传感定义，不是真实裂缝mask。容差来源是这一明确的离散观测精度，**不使用任意3%或10%全场阈值**。

主匹配要求：两臂×三数值版本的**全部六张当前mask逐像素完全一致**。预先指定anchor为rows31:33、cols8:24（Python半开区间），32像素位于预裂后方；必须实际可见，不硬填mask。合法d下fine mesh的这些像素插值至少0.75，故anchor不会靠运行结果选择。若anchor缺失，属于状态/renderer无效；若六图不一致，报告无匹配，停止在原点，不计算未来来挑正例。

完整d/A/r/f、积分量和共同probe的全场u差仅作诊断，不参与匹配。起点统一在第21循环卸载后，不按终寿命、未来裂长或分歧选择。阈值0.45/0.55仅固定敏感性读数，不能挽救主0.5判据。

## 共同续载、数值对照与主判据

三个版本：base、space（只改网格）、load_step（只改每段细分）。各版本都重放完整前史、probe、未来，不只从主网格origin换步长。以物理cycle和phase对齐，不能按load_index错配。固定ell，16/32网格分别有h/ell=0.5/0.25；这是两分辨率敏感性，非完整网格收敛证明。

base两臂各增加一次完整state origin存盘重载，并从全新backend继续相同suffix。保留u/d/A/r/f/opaque、索引、load_id及合同，所有100个未来子步的完整AcceptedState fingerprint都须与原base一致。使用direct mechanics，避免近似旧LU预条件器改变重放轨迹；仍保留受保护Anderson及所有最终接受检查。若确定性重放不一致，先视为实现/数值敏感性阻塞，不能据此断言隐藏历史机制成立或不存在；运行后不放松null要求。

主量D_robust(H20)：在每个arm内部，H20像素值在三数值版本都一致；两arm的值彼此不同。报告其像素数与面积，并同时保留全域不稳定像素图、各版本完整arm XOR计数。预声明条件：

> 当前匹配成立、数值接受与完整state重放有效，且D_robust(H20)>0。

这是特定数字观测的存在性反例标准，所以至少1像素即可支持此**很窄**的Q1结论；1像素面积=1/4096模型面积，不代表实用预测改善。三版一致是已检验的敏感性，不是全局误差上界。H5/H10、0.45/0.55、隐藏A对比、平均场和图片都不能投票救主结果。

结果映射：

- 无当前匹配：inconclusive，保留六图与距离；调整观测或前史须新修订和复核。
- 数值/资源/anchor/restart失败：未完成或不可解释，保留已接受状态与失败，不自动重试。
- 有效匹配、H20稳健差像素为0：此设计negative；不能声称不存在隐藏状态；不扩大合成库。
- 主条件成立：supports这一数字几何观测非充分；下一检验更强当前响应是否能区分，再考虑Q2。不是疲劳A的独立因果证明。

## 预算、生产机与一次性执行边界

**本卡当前禁用；无新producer执行权限。** 用户本次要求先具体定案、实现、审查，“确认后再跑”。下一次只需要确认下列整体方案；版本/路径/资源检查由执行器自动完成，不逐字段索取许可。

建议producer为 `gpu-server` / hostname `GPUServer8` 的CPU，0GPU；不使用Mac做FEM，不换机。fresh root固定为 `/mnt/data2/drtao/wennie/S04-E027-SYNMEM-R001`，代码从精确审阅提交部署，不热换其他任务的输入或runner。

| 限额 | 数值 |
|---|---|
| 整次墙钟 | 4hosth=14,400s，含编排、求解、重放、作图和监督；末20s留清理 |
| CPU/GPU | 最多4 CPU线程（最多16分配coreh）；0GPUh |
| 内存/存储 | 8GiB进程地址空间硬限；本run全部数据8GiB监测上限（内部预留64KiB终态收据空间），至少另留1GiB空闲 |
| 单物理子步 | solver和独立监督均120s，不因日志或重放重置 |
| 尝试总量 | 最多1846步：base412＋space412＋load_step822＋base两次suffix重放200；含6个settle |
| 失败/重试 | 首个科学、数值、资源或IO失败即停；0自动重试、0自动resume |
| 资源未就绪 | 启动前一次只读检查；不启动、不等待轮询、不改run root绕过旧尝试；结果未知先核验 |

1846×120s=61.53hosth仅是逐步上限之和，不是所需时间或授权。4h完成要求含开销平均约7.8s/步，尚未实测。预算达到就保留部分数据并停止，不自动扩时。存储检查间隔0.5s，可能超出最后一次写入大小；任何超额导致停止，不能称精确文件系统配额。RLIMIT_AS会令超额分配失败；不是实测峰值RSS。

## 代码、轻量检查与独立审阅

- `source/synthetic_history_inputs.py`：mesh、原始初态、合法日程与新pair合同；不修改旧same-problem合同。
- `source/synthetic_history_observation.py`：固定相机、anchor、当前匹配与未来稳健像素。
- `source/synthetic_history_experiment.py`：完整接受态前史、原点匹配、共同续载、fresh-backend restart与结论。
- `tools/run_synthetic_history.py`：默认仅校验，显式确认＋准确代码审阅后方可执行；Linux/hostname/新目录/进程组/parent-death与资源监督。
- `tools/plot_synthetic_history.py`：固定全域图、主终点与不稳定像素，nomatch也保留全套当前图。
- 单测仅人工mesh/arrays、元数据、故障模拟和已有代数合同，不跑本试件FEM或训练。首个插值测试误把浮点容差设为2e−16，实差为1 machine epsilon，已改为4eps；这不是科学容差变化。

独立review绑定本次实际commit、spec及只读检查；通过仅说明准备范围可接受。确认前 `authority.json.enabled=false`，不产生run receipt或科学结果。

准备检查命令：

```sh
PYTHONPATH=source:tools python tools/run_synthetic_history.py --spec docs/research/S04/S04-E027-SYNMEM/spec.json
```

确认后执行命令模板（Linux，准确运行卡与review部署后，外层nohup保持SSH断线独立）：

```sh
PYTHONPATH=source:tools nohup python -u tools/run_synthetic_history.py --execute --spec docs/research/S04/S04-E027-SYNMEM/spec.json --authority docs/research/S04/S04-E027-SYNMEM/authority.json --review docs/research/S04/S04-E027-SYNMEM/review.json --output /mnt/data2/drtao/wennie/S04-E027-SYNMEM-R001 > /mnt/data2/drtao/wennie/S04-E027-SYNMEM-R001-dispatch.log 2>&1 < /dev/null &
```

该模板当前不能执行：authority禁用、未获本具体预算确认。正式dispatch日志及部署/回传开销也须记在同一run记录，0.5s监督开销已计墙钟；不能把git成功或准备测试称作FEM成功。

## 最低证据与回传

完整spec/authority/review、host/code/runtime/command与进程收据；逐臂mesh/schedule/pair合同；state0、每步接受态、最终联合证书、原点/未来数字观测、restart逐步对照和停止理由。raw留本run及本地 `local_archive/experiments/S04-E027-SYNMEM/runs/S04-E027-SYNMEM-R001/`，Git只保留紧凑收据和结果。独立结果审阅后才作科学结论。

图至少包括六张当前mask；有未来时包含H20两臂/稳健与不稳定像素，以及H5/H10/H20计数。`README_analysis.md`明确来源、主终点、观测定义、实际结果与限制。检视图后仅选决策PNG进入原Obsidian owner note，继续其唯一Roadmap链接，不创建重复研究路线。

上一轮依据：[数据能力与合成方案](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/cross-track-predictive-state-20261019/docs/research/bridges/BRIDGE-PS-20261019/matched_history_feasibility_20261020/feasibility_and_decision_protocol.md)。
