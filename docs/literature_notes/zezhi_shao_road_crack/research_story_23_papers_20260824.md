# 邵泽志 23 篇论文的研究路径、逻辑关系与道路裂缝迁移判断

更新时间：2026-08-24  
材料范围：`/Users/wenxiaofang/Downloads/pidl_papers/Shao_Zezhi/` 中 23 篇 PDF 全文。

## 结论先行

这组论文讲的并不是“不断把网络做复杂”的故事，而是一条逐渐转向**问题诊断、数据异质性和可部署性**的路线：

1. 早期从轨迹、异质图的表示学习出发，研究如何保留序列或多视图语义。
2. 2022 年进入空间—时间预测主线，同时给出三种不同答案：分解生成机制（D²STGNN）、利用更长上下文（STEP）、以及质疑复杂图网络必要性（STID）。
3. 之后把问题扩展到长预测、多尺度、大空间规模、变量缺失和公平 benchmark。
4. BasicTS+ 之后研究重心明显从“哪种架构最好”转向“什么数据上、为什么有效”：数据异质性、分布漂移、噪声、样本可学习性和预训练语料构成。
5. 最近进一步进入通用时间序列模型，但仍坚持两个母题：**合适的归纳偏置比裸模型容量重要，数据构成和任务定义比模型榜单更重要。**

对我们的道路裂缝预测，最值得借鉴的不是直接复现某个 Transformer/GNN，而是四件事：

- 先用 BasicTS+ 式协议判断数据异质性和模型适用条件；
- 用 STID/STELLA 式简单模型检验物理位置、季节、环境和结构状态是否提供增量信息；
- 用 D²STGNN/PULSE 的“生成机制分解”思想定义状态转移，但不把其交通扩散或相位假设当作裂缝物理；
- 用 GinAR、APT、BLAST 的思路分别管理缺失、分布漂移和样本构成。

当前 LTPP 冻结数据不支持 STEP、D²STGNN、PatchSTG、HUTFormer、Zeus 等深模型训练。可立即执行的是 benchmark/异质性审计、missingness-aware 数据表示，以及简单的 persistence、trend、正则化统计模型和物理属性条件模型。

## 一、逐篇文章的研究路径

### 1. TULAR：Trajectory-User Link with Attention Recurrent Networks（2021）

- **问题**：长且碎片化的签到轨迹难以链接到用户；同一用户在不同时间的轨迹甚至可能比同行用户更不相似。
- **诊断**：普通 RNN 难以压缩长序列，地理坐标空间中的相似性也不等于行为语义相似性。
- **方法**：先学习位置语义表示，再用 RNN 生成轨迹语义向量，以三种 attention score 选择轨迹中更有辨识力的片段，完成用户分类。
- **验证**：在真实轨迹数据上与距离法和深度 TUL 方法比较，并分析 embedding、attention 和序列长度。
- **研究位置**：早期“序列中哪些片段真正有辨识力”的工作。它与后来的时间序列预测主线不是直接继承关系，但“不要平均使用所有时间点”在 Selective Learning 中重新出现。
- **对裂缝的启发**：调查序列中的养护前后、首次出现、快速扩展期可能比平稳期更有辨识力；但不能用 attention 权重替代事件标签或物理解释。

### 2. STID：Spatial-Temporal Identity（2022）

- **问题**：STGNN 越来越复杂，但性能增益有限。
- **诊断**：许多短历史窗口在空间或时间上数值近似、未来却不同；关键瓶颈是样本不可区分，而不一定是缺少复杂图卷积。
- **方法**：给每个变量加入空间 ID，并加入 time-of-day、day-of-week ID，再用残差 MLP 预测。
- **验证**：在交通和电力数据上与 STGNN 比性能和效率，并可视化学到的身份 embedding。
- **研究位置**：这是整个研究故事的转折点——先找“复杂模型究竟解决了什么”，再构造最简单的反例基线。
- **对裂缝的启发**：优先测试位置、季节、资产属性能否消除不可区分性；但 LOSO 未见道路不能使用训练过的道路 ID，应改用可泛化的坐标、结构、气候和交通属性。

### 3. STEP：Pre-training Enhanced STGNN（2022）

- **问题**：STGNN 通常只看约一小时的短窗口，无法利用周尺度上下文，也难以从短窗口可靠学习变量依赖图。
- **诊断**：短窗口既有上下文歧义，又使图结构估计对噪声敏感；直接扩大 STGNN 输入计算代价过高。
- **方法**：用 masked autoencoding 预训练 TSFormer，从很长历史中获得 segment representation；再把表示注入下游 STGNN，并用长期表示形成的 kNN 图约束可学习图。
- **验证**：三套交通数据、多个下游 STGNN、预训练与图学习消融。
- **研究位置**：开启“长历史预训练—下游预测”的 foundation 路线，后续延伸到 BLAST 和 Zeus。
- **对裂缝的启发**：多年环境/荷载史可作为状态上下文，但前提是有足够长、密集、同语义的轨迹；当前稀疏 LTPP 不满足。

### 4. MV-HetGNN：Heterogeneous Graph Neural Network with Multi-View Representation Learning（2022）

- **问题**：异质图既有不同节点/关系类型，又有由不同 metapath 表达的多种语义；简单 attention 或 concatenation 会丢结构或保留冗余。
- **诊断**：每个语义视图应保留完整 ego graph，并显式建模异质节点间映射；多视图融合还需避免冗余。
- **方法**：把异质 ego graph 按 metapath 分成 view-specific ego graphs，用关系表示处理异质映射，再以分层 autoencoder 和正交约束融合多视图。
- **验证**：三类异质图、节点分类/聚类/链接预测，以及视图编码和融合消融。
- **研究位置**：图表示学习支线，不是 MTS 预测主线；其“共享信息与视图特有信息分开”后来在 SMARTraj2 中更直接体现。
- **对裂缝的启发**：图像、裂缝几何、交通、天气、结构层信息可以视为多视图，但在各视图时间/空间配准合格前，不应直接做融合。

### 5. D²STGNN：Decoupled Dynamic STGNN（2022）

- **问题**：交通信号被粗略地全部解释为网络扩散，而且静态道路图不能描述时变依赖。
- **诊断**：观测是“来自邻近节点的扩散部分 + 本地点自身的 inherent 部分”的叠加。
- **方法**：用 estimation gate 和 residual decomposition 逐层分离两类信号；分别用局部扩散模块和 RNN/self-attention 建模，并学习动态图。
- **验证**：四个交通数据集，和静态/自适应 STGNN 比较，并对分解和动态图做消融。
- **研究位置**：代表“先提出生成机制，再按机制拆模型”的路线；与 STID 的简化路线互补而非前后替代。
- **对裂缝的启发**：可把未来变化分为局部已有裂缝延续、环境/荷载驱动的新变化和观测误差；但裂缝不是交通扩散，分解必须由可观测量和物理假设重新定义。

### 6. DSFormer：Double Sampling Transformer（2023）

- **问题**：长预测需要同时保留全局趋势、局部细节和变量相关性。
- **诊断**：单一采样尺度或单一 attention 维度不能兼顾三者。
- **方法**：down-sampling 提取全局信息，piecewise sampling 保留局部信息；temporal-variable attention 分别建模时间和变量维度，再并行融合。
- **验证**：九套真实数据，并做采样、注意力和效率分析。
- **研究位置**：从 STEP 的“长上下文”进一步转向“多尺度如何组织”，与 HUTFormer 和 Zeus 形成多尺度支线。
- **对裂缝的启发**：道路劣化同时有多年慢趋势和局部裂缝事件；先做多时间尺度统计特征，比直接搬 Transformer 更现实。

### 7. STELLA：Lightweight Atmospheric Forecasting with Spatial-Temporal Knowledge（2024/2025 版本）

- **问题**：大规模站点预测中 Transformer 昂贵，复杂度与收益不匹配。
- **诊断**：大气 PDE 表明时间和经纬高程直接参与状态演化；很多模型忽略这些已知坐标，却用复杂 attention 间接拟合。
- **方法**：将地理坐标和时间特征编码为 STPE，只配合 MLP；参数量约 10k，复杂度随站点数线性增长。
- **验证**：五套天气数据、17 个基线、效率和 embedding 分析。
- **边界**：作者明确指出 channel-independent、MLP 表达力和极端事件过平滑问题，未来需协变量和物理约束。
- **研究位置**：把 STID 的“身份即可解决一部分依赖”推进为“有理论来源的空间—时间知识比复杂架构更重要”。
- **对裂缝的启发**：使用真实坐标、层结构、气候和时间间隔做条件变量；这是比 learned section ID 更适合未见道路的迁移版本。

### 8. AI for Geoscience Review（2024）

- **问题**：AI4Geo 研究跨大气圈、水圈、岩石圈等领域，但范式、数据和验证要求高度分散。
- **路径**：组织观察—假设、过程模型、数据驱动、模型—数据混合等研究范式，梳理数据、可靠性、解释性、安全和算力挑战。
- **研究位置**：宏观综述/合作论文，不能视为某一算法论文的直接延续；它提供的是“混合模型必须在观测上校准和验证”的科学位置。
- **对裂缝的启发**：PIDL/FEM 只应提供状态约束、先验或候选机制；真实道路预测 claim 必须由独立观测验证。

### 9. GinAR：MTS Forecasting with Variable Missing（2024）

- **问题**：某些变量整段历史缺失时，传统 STGNN 无法构图；先插补再预测会积累误差。
- **诊断**：长期缺失变量没有可学时间模式，固定邻接也未必能找到足够的正常变量作为参照。
- **方法**：在递归单元内以 interpolation attention 恢复缺失变量表示，以 adaptive graph convolution 重建空间关系，实现端到端恢复和预测。
- **验证**：五套真实数据，在高变量缺失率下与 11 个基线比较；论文展示仅 10% 变量正常时仍可预测全部变量。
- **研究位置**：从“完整规则传感器面板”走向现实数据质量问题。
- **对裂缝的启发**：显式记录缺失机制和可用性 mask，联合状态估计与预测，避免把预插补结果当真值；但不可用图像和配准失败不是普通数值缺失，仍需 fail-closed。

### 10. BasicTS+：Benchmarking and Heterogeneity Analysis（2024）

- **问题**：不同论文对同一模型报告互相矛盾的结果，模型优劣无法可靠判断。
- **诊断**：训练管线、归一化和指标不统一只是第一层；更深层原因是数据在稳定性、漂移和空间不可区分性上异质，结论只在特定数据类型成立。
- **方法**：统一训练/评估管线；用时间稳定性/漂移和空间不可区分性分类数据；在 20 个数据集、30 多个模型上重评。
- **验证结果的含义**：复杂网络并非普遍优于线性模型，GCN 也只在空间不可区分性明显时更有价值。
- **研究位置**：最重要的第二次转折——从模型发明转向 benchmark、数据诊断和条件化结论，后续 BLAST、SSTD tutorial、APT、Selective Learning 都沿这条路发展。
- **对裂缝的启发**：这是当前最可直接使用的工作：冻结数据、统一 pipeline、按资产/时间/气候/养护分层、物理 holdout、persistence control 和完整误差报告。

### 11. STGNN Survey for Urban Predictive Learning（2024）

- **问题**：城市预测中图构造、时间建模、空间建模和融合方法繁多，应用边界不清。
- **路径**：从先验/相似/动态图构造出发，对 temporal learning、spatial learning、fusion 和高级学习框架建立 taxonomy，再总结效率、泛化、鲁棒性、可解释性等挑战。
- **研究位置**：领域综述，不是独立算法链；它为 D²STGNN、STEP、STID 所在的技术空间提供地图。
- **对裂缝的启发**：图首先是数据结构假设。只有存在同步位置、可解释边和可验证的信息传播时，才应引入 GNN。

### 12. BLAST：Balanced Sampling Time Series Corpus（2025）

- **问题**：通用预测模型追求更多数据，但少数超大数据集/长序列主导训练，导致模式分布失衡。
- **诊断**：按 dataset 或 domain 分层仍不能保证模式多样，因为同域数据可能差异很大，同一数据集内部也可能异质。
- **方法**：用多个统计量表征时间序列模式，在低维网格中做 grid sampling 与 grid mixup，构造 3210 亿观测的平衡语料。
- **验证**：用更少 token 和 GPU 训练通用模型，同时改善零样本性能。
- **研究位置**：STEP 的预训练路线与 BasicTS+ 的异质性路线汇合：重点从“预训练模型”转到“预训练数据如何组成”。
- **对裂缝的启发**：按裂缝演化模式、气候、养护和调查质量平衡采样，而不是让图片最多的道路主导；但小数据阶段更适合做分层权重/审计，不适合 foundation pretraining。

### 13. APT：Affine Prototype-Timestamps（PDF 为 AAAI 2026 版本）

- **问题**：分布漂移下，局部 mean/variance normalization 对缺失和噪声敏感，还会抹掉有用的全局分布信息；静态 affine 参数帮助有限。
- **诊断**：相同 time-of-day/day-of-week 的片段常有相似分布，时间戳可作为全局 regime 的低成本语义。
- **方法**：把时间戳匹配到 prototypes，生成样本条件化 affine 参数；以自监督、正交和负载平衡损失训练，作为冻结 backbone/normalization 的插件。
- **验证**：跨多个 backbone 和 normalization 比较分布漂移下的改进。
- **边界**：依赖人工选择确有信息增益的时间标签；无关标签会降性能，且需要额外预训练和参数调节。
- **研究位置**：STID 的离散时间身份被推进为“时间条件化的分布调制”。
- **对裂缝的启发**：可把冻融季、养护 phase、调查协议或气候 regime 作为条件，但不规则年度调查不能照搬日/周 timestamp prototypes。

### 14. HUTFormer：Hierarchical U-Net Transformer（2025）

- **问题**：交通 STGNN 因复杂度主要做 1 小时预测，而日尺度预测需要同时表示周期和尖峰细节。
- **诊断**：固定尺度全局 attention 难以同时保留全局周期与局部拥堵变化；历史与未来不对齐，普通 U-Net skip connection 不能直接套用。
- **方法**：window attention + segment merging 形成层级编码；先生成粗预测，再以 cross-scale attention 检索各尺度特征进行修正；采用 STID 式时空位置编码降低复杂度。
- **验证**：四个交通数据集，长预测基线、多尺度和位置编码消融。
- **边界**：论文明确承认 learned sensor embedding 难以泛化到新传感器。
- **研究位置**：DSFormer 多尺度思想、STID 位置身份和长交通预测汇合。
- **对裂缝的启发**：适合未来密集面板中的慢趋势/局部事件融合；当前几次年度调查不足以支撑层级 Transformer。

### 15. Foundation Models and Intelligent Decision-Making Review（2025）

- **问题**：决策智能从规则、优化、RL 发展到 foundation models，需统一感知、推理、行动，同时管理安全、隐私和人机伦理。
- **路径**：以环境—agent—reward—工具和 OODA 为框架，综述 FM 如何支持复杂决策和跨域应用。
- **研究位置**：宏观合作综述，与 MTS 预测论文没有直接算法继承；它把预测放进“observe—orient—decide—act”的决策闭环。
- **对裂缝的启发**：模型输出应服务于巡检/养护决策，并给出风险和不确定性；目前我们只做观察与预测，不能越过证据直接给自动养护策略。

### 16. Spatial-Temporal Large Models Commentary（2025）

- **问题**：各科学领域重复构建碎片化时空分析管线，要求同时具备 AI 与领域知识。
- **主张**：时空大模型可统一数据格式、任务和工具，成为跨学科“super hub”；但仍面临速度、内存、隐私、非欧/欧式数据统一和领域知识注入问题。
- **研究位置**：STEP—BLAST—Zeus 路线的愿景性表达，不是实证证明。
- **对裂缝的启发**：可长期建设统一道路劣化数据接口和多任务表示，但领域知识、可解释性和独立验证不能被大模型取代。

### 17. PatchSTG：Large-Scale Traffic Forecasting via Spatial Data Management（2025）

- **问题**：动态图 attention 在成千上万交通点上是二次复杂度；线性/低秩近似又损失可解释性或信息。
- **诊断**：规则图像 patch 不适合道路上不规则分布的传感器。
- **方法**：用 KD-tree 递归划分并回溯合并，形成均衡、非重叠的不规则空间 patch；patch 内 depth attention、跨 patch 同索引 breadth attention。
- **验证**：大规模交通数据上报告性能、约 4 倍显存降低和约 10 倍训练加速，并做 patching/attention 消融。
- **研究位置**：D²STGNN 动态空间建模的规模化工程支线。
- **对裂缝的启发**：如果未来有大规模连续路面网格，可用物理空间分区减少计算；当前 6 条 section 完全不需要。

### 18. SMARTraj2（2025）

- **问题**：多视图轨迹模型在不同城市的道路、网格和规则下难泛化，优化某城市/视图/任务会伤害其他目标。
- **诊断**：需要同时保留跨城市共享表示和城市特有表示，并动态控制二者贡献。
- **方法**：正交约束的 feature disentanglement 分离 domain-invariant/domain-specific 表示；城市级与轨迹级 personalized gate 平衡视图和任务。
- **验证**：成都和西安、多下游任务；作者同时承认仅两城、依赖多视图完整性和数据质量。
- **研究位置**：回到 TULAR/MV-HetGNN 的轨迹与多视图支线，但问题从单数据集表示转为跨域泛化。
- **对裂缝的启发**：共享劣化规律与 road/site-specific effect 应分层建模；两城结果提醒我们不能把少数道路的跨域表现称为普适。

### 19. Selective Learning（2025）

- **问题**：MSE/MAE 对所有时间点一视同仁，深模型会拟合噪声和异常，导致过拟合。
- **诊断**：可由多个滑窗对同一目标时刻的 residual entropy 识别不确定点，由 residual lower bound 识别难以再改善的异常点。
- **方法**：用 uncertainty mask 和 anomaly mask，只在“可泛化”的时间点计算训练损失；方法与 backbone 无关。
- **验证**：八套数据、六种深模型，并展示过拟合曲线改善。
- **关键边界**：作者明确警告可能过滤稀有极端事件，建议极端场景用在线适配或部署后微调。
- **研究位置**：把 TULAR 的“选择有用片段”从表示层推进到训练目标；DropoutTS 随后直接批评其 hard selection 的信息损失。
- **对裂缝的启发**：不能把裂缝快速增长/首次出现当异常删掉；可用于降低明显测量故障权重，但需保留单独的 extreme-event loss 与审计。

### 20. Heterogeneity in MTS Tutorial（SSTD 2025）

- **问题**：MTS 研究结论冲突且跨域泛化差，核心是数据异质性没有被量化。
- **路径**：用 BasicTS 公平 benchmark；以 stationarity、trend、periodicity、volatility、homoscedasticity、memory、anomaly 等统计属性描述数据；提出两条适配路线：BLAST 式通用模型和 ARIES 式 pattern-to-model 推荐。
- **研究位置**：不是新算法，而是对 BasicTS+—BLAST 主线的明确总结，也公开表明其当前研究重点是 foundation models 与跨域分布分析。
- **对裂缝的启发**：先做道路轨迹“统计画像—模型适配”表，而不是在所有道路上使用同一个深模型。

### 21. DropoutTS（ICML 2026）

- **问题**：hard pruning 会丢掉有效稀有事件，概率先验又昂贵；统一 dropout 假定所有样本难度相同。
- **诊断**：样本噪声/可预测性不同，应调节每个样本获得的模型容量，而不是简单保留或删除。
- **方法**：用频谱稀疏性和可学习 mask 的重构残差估计噪声；噪声越高，dropout 越强。
- **验证**：七套真实数据、可控合成噪声、多 backbone，且与 Selective Learning 组合比较。
- **边界**：假定有效信号能量集中在稀疏主频；随机游走、混沌或宽谱有效信号不满足。
- **研究位置**：对 Selective Learning 的软化修正——从“学不学”转为“给多少容量”。
- **对裂缝的启发**：比删除异常样本更安全，但裂缝事件常是非周期宽谱变化，频谱噪声假设必须先用合成/真实故障对照验证。

### 22. PULSE（ICML 2026）

- **问题**：非平稳预测既需稳定表示，又需生成未来分布变化；归一化和固定周期方法会发生所谓 Phase Amnesia。
- **诊断/假设**：时间序列可分为确定结构与随机残差；结构的相位和幅值随时间演化；残差分布也随时间异方差变化。
- **方法**：Phase-Anchored Disentanglement 分开结构/残差，Phase Router 主动生成未来结构轨迹，Statistic-Aware Mixup 模拟未见残差分布；可作为轻量 MLP 插件。
- **验证**：12 套真实 benchmark，并分析组件和效率。
- **研究位置**：D²STGNN 的“机制分解”与 APT/BasicTS 的“分布变化”在非平稳预测问题上汇合。
- **对裂缝的启发**：可借用“状态基线 + 事件残差 + regime shift”的建模语言，但 phase/Wold 假设不是相场断裂物理；必须先由裂缝数据验证可辨识性。

### 23. Zeus（ICML 2026）

- **问题**：时间序列 foundation model 在 patch 粒度上丢点级细节，在 point 粒度上计算昂贵；预测、插补、异常检测和分类又有不同归纳偏置。
- **方法**：point-wise tokenization + U 形多尺度 Transformer，在高分辨率保留细节、低分辨率捕捉长依赖；MOTM 用预测式、点式和块式 masking 联合训练外推、插值和全局抽象。
- **验证**：五类下游任务，强调无需任务专属 tuning 的表现。
- **边界**：当前以 univariate/channel-independent 为主，多变量相关、结构性缺失、分割和因果发现仍是未来工作；极短高维分类也较弱。
- **研究位置**：STEP 的预训练、DSFormer/HUTFormer 的多尺度和 STFM 愿景最终汇入通用多任务模型。
- **对裂缝的启发**：长期可统一预测、缺失恢复、异常和裂缝状态分类；当前数据量、变量关系和结构性缺失条件均不支持投入复现。

## 二、论文之间的真实逻辑关系

### 主线 A：从复杂 STGNN 到“先找瓶颈”

`D²STGNN（机制分解） / STEP（长上下文） / STID（不可区分性）`

这三篇不是单线升级，而是对 2022 年同一类问题的三种解释。后续事实更支持将 STID 的研究方法视为核心：先诊断复杂模型的有效因素，再决定是否需要图、attention 或预训练。

### 主线 B：长历史与多尺度

`STEP → DSFormer → HUTFormer → Zeus`

- STEP：长历史先预训练，再服务短预测；
- DSFormer：显式拆全局/局部采样尺度；
- HUTFormer：为长交通预测建立层级编码—解码；
- Zeus：把多尺度进一步用于多任务 foundation model。

### 主线 C：身份/知识注入的简化路线

`STID → HUTFormer 的 ST-PE → STELLA → APT`

- STID 用空间/时间身份解决样本歧义；
- HUTFormer 直接继承这种位置编码以避免昂贵图卷积；
- STELLA 用领域方程解释为何真实空间—时间坐标本身有预测力；
- APT 不再只把时间戳当 embedding，而用它调制分布。

### 主线 D：数据异质性成为中心问题

`BasicTS+ → SSTD Heterogeneity Tutorial → BLAST / ARIES 路线`

BasicTS+ 先说明模型排名依赖数据类型；SSTD tutorial 将其总结为统计画像；BLAST 面向通用模型平衡预训练模式，ARIES（本文件夹没有独立 PDF）面向单域任务做 pattern-to-model 推荐。

### 主线 E：现实数据质量与鲁棒性

`GinAR（结构性变量缺失）`、`APT（分布漂移）`、`Selective Learning（难点筛除） → DropoutTS（软容量调节）`、`PULSE（生成分布演化）`

它们处理的是不同失效模式，不能互相替代。尤其 Selective Learning 与 DropoutTS 有明确逻辑关系：后者把前者的二元删除改成样本自适应容量，意图保留稀有有效信息。

### 支线：图/轨迹多视图

`TULAR → MV-HetGNN → SMARTraj2`

这是从轨迹辨识、异质多视图表示到跨城市多视图泛化的支线。它与 MTS 预测主线共享“辨识性、异质性和共享/特有信息分解”，但任务和数据结构不同。

### 规模化支线

`D²STGNN 的动态图 → PatchSTG 的大规模空间计算`

PatchSTG 解决的是动态图在海量不规则交通点上的计算问题，不是提高小样本统计有效性的工具。

### 宏观综述/愿景

AI4Geo Review、STGNN Survey、IDM Review、STFM Commentary 提供领域地图和研究定位，但不能当作算法链中的实证节点。

## 三、邵泽志的研究故事

如果把这 23 篇看成一个 publication portfolio，而不把每篇合著论文都强行解释为个人单线推进，可以概括为：

1. **从表示开始**：先研究轨迹和异质图如何提取有辨识力的序列/多视图信息。
2. **进入空间—时间预测**：同时探索动态图分解、长历史预训练和极简身份基线。
3. **开始质疑架构中心主义**：STID 提出“复杂模型可能只是在解决不可区分性”；BasicTS+ 进一步证明模型结论依赖 benchmark 和数据异质性。
4. **把现实失效模式逐一显式化**：变量长期缺失、长预测、多尺度、大规模点集、跨城市、噪声、异常和分布漂移。
5. **走向数据中心和通用模型**：BLAST 关注语料构成，Zeus 关注跨任务统一；同时 STELLA、APT、PULSE 继续强调知识/分布归纳偏置，而不是单纯扩大模型。

因此，他最值得我们借鉴的不是某一层网络，而是一种研究套路：

> 先指出一个可复现的失败模式，给出比“换更大模型”更具体的诊断，再设计只针对该失效模式的模块，并在异质数据和简单基线上验证。

## 四、对我们道路裂缝预测的借鉴优先级

### A. 现在就可用：研究协议与数据表示

1. **BasicTS+ 式异质性审计**
   - 每条轨迹标注资产、位置、时间间隔、季节/气候、交通、结构、养护和观测协议。
   - 按 asset/site/environment 做 holdout；不能随机拆同一道路的相邻年份。
   - persistence、trend、正则化线性/状态空间模型必须先跑。
   - 报告每个资产和每类 regime，不只给全局平均。

2. **GinAR 式 missingness-aware 表示**
   - 区分“真实为零”“未调查”“图像不可用”“配准失败”“养护后语义重置”。
   - 把 availability mask 和 missing reason 作为输入/审计变量。
   - 配准失败不能插补成二维裂缝真值；只能降级为可证明的标量任务或 `NOT_COMPUTABLE`。

3. **STID/STELLA 式简单知识条件基线**
   - 输入使用可泛化属性：坐标、车道/方向、结构层、气候、交通、距上次调查时间、养护 phase。
   - 不使用未见 section 的 learned ID，也不允许 timestamp/asset shortcut 泄漏。

### B. 新 panel 冻结后值得测试：低成本 challenger

1. **D²STGNN/PULSE 启发的状态分解**
   - 候选分解：已有损伤 persistence/trend + 环境/荷载条件增量 + observation noise。
   - 先用线性混合效应或状态空间模型验证各部分是否可辨识，再考虑神经模块。

2. **APT 式 regime conditioning**
   - 只有在重复季节、明确养护事件和足够多 regime 实例存在时测试。
   - 条件标签必须预先定义并做信息增益审计；无关时间标签应作为负对照。

3. **BLAST 式 pattern balancing**
   - 按增长率、间隔、裂缝状态、气候和养护平衡训练/抽样；每一资产设置上限，防止帧多的道路支配模型。

4. **Selective Learning/DropoutTS 的谨慎版本**
   - 只降低确认的测量故障权重，不删除首次开裂和快速增长事件。
   - 单独报告 extreme-event recall、new-geometry error、calibration 和 worst-asset error。

### C. 暂不投入：数据条件尚未满足

- STEP：需要长、密集、同语义历史；
- D²STGNN/PatchSTG：需要同步物理图和足够节点；
- DSFormer/HUTFormer：需要密集、多尺度长序列；
- SMARTraj2：需要多个城市/道路群和稳定的多视图；
- Zeus/STFM：需要大规模多域语料，且 Zeus 的多变量相关仍是限制。

## 五、建议的下一决定（不是立即训练）

### Gate 1：数据是否达到预测资格

先冻结一个新的 asset-time panel，并检查：

- 至少有多个独立道路/环境；
- 每个测试资产有真实 future-time observation；
- 养护事件和调查间隔明确；
- 裂缝几何/标量 target 的定义跨年份一致；
- availability 与 missing reason 可审计；
- 不依赖跨年份失败的二维配准来制造标签。

### Gate 2：最小模型是否有增量价值

按预注册顺序比较：

1. persistence；
2. linear trend；
3. 正则化统计/状态空间模型；
4. 加入 STELLA 式物理属性和时间条件的简单模型；
5. 只有前四步显示稳定的 out-of-asset 增量，才测试 APT 或更复杂模型。

### Gate 3：复杂方法的专属进入条件

- 图模型：必须证明物理邻接/交通/排水边在 held-out asset 上有增量信息；
- 长历史预训练：必须证明长历史不是 asset identity 或调查 cadence shortcut；
- 多尺度模型：必须有足够时间密度使局部与全局尺度可辨识；
- 样本筛除/降权：必须不降低首次开裂和极端增长召回；
- foundation model：必须先证明零样本/少样本表示在我们的单位、缺失和非规则时间上可用。

## 证据边界

- 这 23 篇主要是交通、天气、通用时间序列、轨迹和综述论文，不是道路裂缝预测验证。
- 论文中的“physics-informed”通常是时间序列结构或领域方程启发，不等同于相场断裂物理，也不证明 PIDL 的现实预测能力。
- 下载和阅读论文不构成启动训练授权；本报告没有运行任何预测实验。
- 对 2025/2026 预印本的结论按本地 PDF 版本陈述，后续版本可能变化。
