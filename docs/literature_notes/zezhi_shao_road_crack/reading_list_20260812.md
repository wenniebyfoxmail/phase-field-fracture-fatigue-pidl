# 邵泽志时间序列方向：道路裂缝预测阅读清单

更新时间：2026-08-12

## 结论先行

与当前道路裂缝预测最相关的不是“交通流预测”这个应用标签，而是四个可迁移问题：

1. **STID：提醒我们检查路段/位置身份和时间身份是否构成 shortcut；当前数据不足以训练该模型。**
2. **APT：提示未来应显式处理跨年份、气候和养护 regime shift；当前稀疏调查不满足其 timestamp 假设。**
3. **BasicTS+：借用异质性分析和公平 benchmark 设计，避免在不同资产、路段和采样频率混在一起时误判模型。**
4. **STEP：只有在真实轨迹足够长、密集且语义一致时，才值得测试长历史预训练表示。**

**2026-08-12 可行性复审结论：文献阅读有价值，但在当前六路段 LTPP 冻结包上复现 STID、APT、STEP、D²STGNN 或 Zeus 均不获准，也不具备可靠统计可行性。** 当前可行的是采用 BasicTS+ 的公平比较和异质性审计原则；新的模型实验必须等待独立的新数据包或 prospective pilot。D²STGNN 只有在拥有**同步、相邻、可定义物理图边的多位置状态**时才有意义。Zeus 只作观察材料。

## 下载文件

文件位于：`references/zezhi_shao_time_series/`

| 优先级 | 论文 | 本地 PDF | 官方入口 | 当前迁移判断 |
|---|---|---|---|---|
| A / protocol only | Spatial-Temporal Identity (STID), CIKM 2022 | [2208.05233_STID.pdf](../../../references/zezhi_shao_time_series/2208.05233_STID.pdf) | [arXiv:2208.05233](https://arxiv.org/abs/2208.05233) · [代码](https://github.com/zezhishao/STID) | 用于识别 identity shortcut；当前不训练 |
| A / future method | APT: Affine Prototype-Timestamp under Distribution Shift, AAAI 2026 | [2511.12945_APT.pdf](../../../references/zezhi_shao_time_series/2511.12945_APT.pdf) | [arXiv:2511.12945](https://arxiv.org/abs/2511.12945) · [代码](https://github.com/blisky-li/APT) | 对 future prospective panel 有意义；当前不训练 |
| A / immediately usable | Exploring Progress in MTS Forecasting: Benchmarking and Heterogeneity Analysis | [2310.06119_BasicTS_plus_heterogeneity.pdf](../../../references/zezhi_shao_time_series/2310.06119_BasicTS_plus_heterogeneity.pdf) | [arXiv:2310.06119](https://arxiv.org/abs/2310.06119) · [BasicTS](https://github.com/GestaltCogTeam/BasicTS) | 采用 protocol 和 heterogeneity 原则，不搬 45+ 模型 |
| B / data-gated | STEP: Pre-training Enhanced STGNN for MTS Forecasting | [2206.09113_STEP.pdf](../../../references/zezhi_shao_time_series/2206.09113_STEP.pdf) | [arXiv:2206.09113](https://arxiv.org/abs/2206.09113) · [代码](https://github.com/zezhishao/STEP) | 当前没有长、密集、同语义历史 |
| B / data-gated | D²STGNN: Decoupled Dynamic STGNN for Traffic Forecasting | [2206.09112_D2STGNN.pdf](../../../references/zezhi_shao_time_series/2206.09112_D2STGNN.pdf) | [arXiv:2206.09112](https://arxiv.org/abs/2206.09112) · [代码](https://github.com/zezhishao/D2STGNN) | 当前六 section 不是同步物理邻接图 |
| C / watch | Zeus: Tuning-Free Foundation Model for Time Series Analysis | [2607.01918_Zeus_watch_only.pdf](../../../references/zezhi_shao_time_series/2607.01918_Zeus_watch_only.pdf) | [arXiv:2607.01918](https://arxiv.org/abs/2607.01918) · [代码](https://github.com/GestaltCogTeam/Zeus) | 多变量建模仍是论文未来方向；不进入实验 |

## 2026-08-12 独立可行性复审

### 当前数据是否足够

不够。冻结包只有 37 个 states、31 个 transitions，其中 25 个 development transitions 和 6 个 future-time tests。每个 section 只有 3--6 个开发转移。31 个转移中裂缝长度变化有 15 个正值、9 个负值和 7 个零值，反映识别/调查波动与真实非单调观测共同存在。已有一次性层级状态空间 challenger 在 LOSO 下相对 persistence 的长度误差恶化 15.63%，new-geometry error 恶化 6.31%，联合胜出为 0/6；完整 enriched-input 模型也相对 persistence 恶化 4.13%。

这些结果不证明神经网络一定失败，但证明当前数据不能支持把更复杂模型作为同一冻结 track 的 rescue。

### 各候选的可行性判定

| 候选 | 当前判定 | 决定性原因 |
|---|---|---|
| BasicTS+ protocol | `FEASIBLE_ALREADY_ADOPTED` | LOSO、future-time freeze、persistence control、分层报告等原则与现有协议一致 |
| STID 训练 | `NOT_FEASIBLE_CURRENT_PACKET` | LOSO held-out section 没有可学习的 section embedding；25 条训练转移不足以估计 identity + MLP，且会违反禁止 architecture rescue 的冻结决定 |
| APT 训练 | `NOT_FEASIBLE_CURRENT_PACKET` | APT 的 Time-in-Day/Day-in-Week 假设不适用于 1--4.5 年不规则 survey；只有 22 个 source year-month 组合，prototype/affine 参数不可可靠识别 |
| STEP | `NOT_FEASIBLE_CURRENT_PACKET` | 没有论文要求的长且密集历史；每 section 只有 4--7 个 transition |
| D²STGNN | `NOT_FEASIBLE_CURRENT_PACKET` | 六条 section 不构成同步邻接网络，无法定义无泄漏、可解释的动态传播图 |
| Zeus | `NOT_FEASIBLE_CURRENT_PACKET` | 约 100M 参数与 25 条 development transitions 不匹配，且论文自身尚未完成 multivariate extension |

### 五问实验门

1. **机制问题**：identity 或 timestamp-conditioned shift 是否对未见道路的裂缝增长提供稳定增量信息？问题成立。
2. **改变的 claim**：成功可支持 observation-conditioned scalar baseline；失败只否定该数据包中的增量价值。边界可定义。
3. **更便宜诊断**：现有 state-space、enriched-input 和 load-only 负结果已经完成了更便宜诊断；无需再用复杂神经网络重复询问。
4. **最小输出资产**：本次可行性决策说明已经足够；当前没有获准的新训练输出。
5. **registry handoff**：研究前线已经把六路段 benchmark 标记为 terminal，并要求新表示或更大 panel 作为新 preregistered experiment。

因此当前 gate verdict 是：`NO_GO_CURRENT_LTPP_PACKET__ACQUISITION_OR_NEW_PANEL_REQUIRED`。

## 每篇文章对我们能提供什么

### 1. STID：一个必须先打败/至少公平比较的简单基线

论文的核心不是复杂 GNN，而是给每个变量/空间位置和时间位置加 identity embedding，再用小型 MLP 做预测。迁移到裂缝问题时，可以把：

- spatial identity：路段、固定采样位置、车道/方向或资产 ID；
- temporal identity：季节、月份、调查周期、降雨/冻融季或 maintenance phase；
- target：未来裂缝长度、面积、tip 位移、new-geometry indicator 或风险。

**当前用途**：把 STID 当作 shortcut 警告和未来 baseline 设计参考。不能在现有六路段包上学习 section identity，因为 LOSO 的未见 section 没有已训练 embedding；也不应通过 transductive embedding 暗中使用 held-out identity。

### 2. APT：目前最有现实意义的算法候选

APT 用 timestamp-conditioned prototypes 生成输入/输出 affine parameters，目标是让 forecasting backbone 感知全局分布漂移，而不只依赖局部 normalization。对道路裂缝，合理对应的是：

- 年份/季节/气候带造成的裂缝增长分布变化；
- resurfacing、排水改变或养护造成的 regime break；
- 不同 survey protocol、传感器或资产群造成的 channel/section shift。

**但不能直接照搬**：论文的 timestamp 语义来自高频规则时间序列；我们的调查时间稀疏、维护可能截断轨迹、不同 section 不等价。APT 只能进入一个未来的新数据包：至少要有足够的重复季节/年份、明确 maintenance regime、预先冻结的 asset holdout，并与相同 backbone 的无 APT 版本及 persistence 比较。

### 3. BasicTS+ / heterogeneity：对研究设计的价值高于对模型的价值

这篇工作强调：不同 MTS 数据的 temporal/spatial characteristics 会改变模型排名；不应默认 spatial dependency 必须被建模。对我们尤其重要，因为当前项目已经看到真实道路轨迹的 section、气候和 survey cadence 差异很大。

**可直接采用的 protocol**：按物理 asset/site/environment 分组 holdout；分层报告长裂缝/短裂缝、稀疏/密集调查、气候/结构类别；每个模型都与 persistence 和简单 trend control 比较。它支持 benchmark 设计，不等于证明其 45+ 模型中的某个模型适合裂缝。

### 4. STEP：长历史表示学习的条件性候选

STEP 用 scalable pre-training 从很长历史中学习 segment-level representation，再辅助短期 STGNN。它提示我们：若未来获得多年、多资产、同语义的道路轨迹，可以把“长期环境/荷载 regime”作为表示输入。

**当前限制**：现有 LTPP 主序列仍是小样本、稀疏 survey、跨 section 语义不完全同质；直接预训练容易把 asset identity、cadence 或标签制度学成 shortcut。因此先不训练 STEP，除非 acquisition gate 证明有足够的同语义长序列。

### 5. D²STGNN：动态图不是默认答案

D²STGNN 将信号拆成 diffusion 和 inherent 两部分，并学习动态空间关系。它对裂缝的潜在启发是区分：

- 邻近位置/相邻路段传播或共同荷载影响；
- 某一位置自身的局部劣化、材料和历史状态。

**进入条件**：必须先有同步的多路段或道路网络观测，并明确图边来自物理邻接、交通/排水联系还是数据学习；否则“动态邻接”很容易只是 section ID 或时间泄漏的替代品。

### 6. Zeus：值得关注，但现在不应投入复现成本

Zeus 的多尺度 Transformer + multi-objective temporal masking 对“预测、插值、异常检测、分类”统一建模有启发，但当前论文的限制与我们的任务正好冲突：它把 multivariate modeling 和更广泛扩展列为未来工作，而且其训练数据/任务与道路裂缝的稀疏、事件驱动观测差异很大。先保存原文，不进入当前实验队列。

## 推荐阅读顺序与下一决策

1. **读 BasicTS+ 的 benchmark/heterogeneity 部分**，用于审查下一批数据，而不是重跑当前 terminal benchmark。
2. **不在当前六路段包复现 STID/APT**；保留代码和论文作为 future-panel 候选。
3. **下一步应是 acquisition gate**：寻找或建立更多独立道路、重复季节、明确养护事件、同步图像/几何/荷载/天气的 asset-time panel。
4. 新 panel 冻结后，先做 persistence、trend、正则化线性/状态空间模型；只有简单 challenger 通过预设 gate，才进入 STID/APT。STEP/D²STGNN 还需额外满足长历史或物理图条件；Zeus 继续观察。

## 证据边界

- 这些论文是多变量时间序列/交通预测论文，不是道路裂缝预测验证；方法可迁移性需要在我们的冻结、分组 holdout 协议中重新证明。
- 下载原文不等于授权开始训练。当前项目的 LTPP 二维空间配准路线仍关闭；本清单优先支持标量/观察条件的诊断。
- 六个 PDF 的 SHA-256 收据见同目录旁的下载命令输出；若需要提交到共享仓库，下一步再单独决定是否纳入大文件追踪。
