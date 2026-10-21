# D20 R008：可表示域认证修复奏效，但有限盒约束LS改进尚未达到原物理精度

目的：延续同原方程、加载、不可逆边界和真实自身历史的train_A600连续轨迹，最终支持同精度前态／经典／神经初猜比较。本轮为原HQ有界R008的唯一尝试与收尾，**首步8个外层子问题耗尽，0/600，已停止，无重试**。相对于R007，保守可行性认证不再提前中断；八轮Cauchy证书及候选比较都完成。但工作目标下降没有达到原物理精度，完整轨迹可行性和NN收益均未建立。当前处置是保存负结果并提出下一路线设计；不实施或启动R009。

## 身份、完整取回及退出

- Run `pf_hybrid_solver_v11_20261021_r8`，原GPUServer8 `drtao@172.16.100.2`，4CPU/0GPU；源`a21785a9d6c62cf034ea0fa063e417b88c4dc089`，37文件artifact`560e701e37005de5879ff342eee0a80a8bd648b67b6c576012561e4e9c4b9188`。
- 卡SHA`b487e76cc7ac6679ba42f08747ed8ccd15ba63dde916e2aba6f7ddeef7f67851`，最终静态复审SHA`5a348151bd59f00e9140fd4770113859ed3faeb697ddd9d546c1de1abe609ce7`。旧716e阶段桥接关键字冲突的临时复审已撤回，原件保存在`superseded_716e/`，不追认为最终执行版本。最终73项给定数组／控制检查通过，6项native/controller检查按范围排除，未在Mac进行新FEM装配／分解／科学试跑。
- 原R3输入只读；同机复制98个公共OSQP文件980049B；上传审核源码控制包118185B。两次机械动作共7.21932287409436秒，额度已消费。此次没有新private input、其他case、训练或GPU探针。
- 终态清单共**169文件147540936B**，逐文件size/SHA全部核验；37份返回科学源与冻结清单／当前源一致。完整保存在`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v11_20261021/recovered_verified/`，没有重复下载已核件。
- 自有PID123141／123142／123149／123150在终态清单中均absent。终态为`failed`；worker的真实原因是`joint coupled block direction budget exhausted`。guardian的“incomplete step completion at worker exit”是其后退出检查，**不是300秒超时**。
- `state0000.npz`与`latest.npz`均version0、fingerprint`fdedddadeb403e3e4316ca8132e4edc87ac22b6755da4af19419d8d428a6c4e1`；只有原初态，0次CAS/history commit。9次fresh检查均无真实QP操作，`m_accept`和fatigue操作分量为NA；不能写成零残差或完整物理认证通过。

取回原清单、返回验证、状态与源绑定见本地`full_remote_inventory.json`、`complete_return_verification.json`及`recovered_verified/runroot/terminal.json`；[analysis_manifest.json](analysis_manifest.json)绑定本次分析／图表原件；[case_elapsed_times.csv](case_elapsed_times.csv)给唯一实际case，其他case未启动，不填零。

## 真实时间及物理末态

| 范围 | 实测值 | 解释 |
|---|---:|---|
| train_A phase/case wall | 170.495091159秒 | 唯一失败case，接受0/600 |
| producer wall | 170.496567417秒 | 包含phase，不能相加 |
| worker+guardian CPU | 202.596635 CPU秒 | 仅运行进程树，不是整个准备包CPU |
| GPU | 0 | 未训练／未用GPU |
| owned-tree峰RSS | 4498243584B，约4.19GiB | 运行采样；全生命周期Mac峰值UNKNOWN |
| 第1步marker→末trace | 167.209553769秒 | 完成／失败闭合root工作160.040077024秒，差7.169476745秒未分摊 |
| 首停计数事件elapsed | 167.208404692秒 | 与trace范围不同，分别保留 |
| 全量只读取回stream | 51.784270167秒 | 已含在整包calendar，不额外叠加 |

末次fresh（outer9）原读数：Ru_L2 **1.7322971102619295e-6**，门1e-8，**173.229711倍**；damage KKT_inf **1.5686503205259705e-6**，门1e-7，**15.686503倍**；damage KKT_L2 **2.3012768014034866e-6**，原联合L2比**1.00839348**。边界／primal检查为0，但这些不能代替力／KKT门。没有最终真实QP、最终机械认证或接受态。全部9个完整fresh的f均1，没有卸载／f<1覆盖。

## 哪些修复奏效

1. **可表示状态区间认证跨过R007的首停点。** R008八轮都有Cauchy、PG1、PG2、optional比较，共136条stage JSON。每轮数字证书／ID均保留；向量文件按stage覆盖为最新outer8，并非八轮全向量留存。生产中exact Fraction比较数均0：本次靠inner interval／有效上界完成资格，不能声称精确比较分支已在生产执行。
2. **可选候选没有破坏已有合格best。** outer1选合格Newton比较，rho0.966384；outer2–8的optional模型pred_upper全部为负，未替换PG best，也没有额外非线性fresh试算。这次不是抓住typed exception的fallback；候选可行但模型变坏。数值／域／IO真错误继续首停。
3. **模型证书和实际下降相容。** 8个工作候选均keep、0reject；每轮4/16更新、action upper28–35/100（含原块保守12动作，不等同于同数量J乘积）。Cauchy充分下降证书全通过；后7轮rho近1。原块八轮通过既有effective行残差与绝对目标；第一轮极小机械RHS使用原roundoff条款，严格relative0.0076679>.001，不能写成八轮严格relative均通过。其余轮没有相同例外。

![R008全局化与成本](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v11_20261021/analysis/r8_globalization_trace.png)

看见什么：加权Phi单调下降，模型/实际比接近1；原力与damage容差比仍远大于1，选中步远小于半径。
说明什么：表示认证与候选选择的修复有效，但还缺足够有效的可行耦合步。不能把0/600改写为数值成功。

## 为什么可靠的局部LS模型仍未达原精度

Phi从**4.833261034356823e-7→1.3139338387247479e-8**，降36.78466倍；其中首Newton比较已贡献主要下降，后7次为较小投影梯度改进。原m_work却从初始30.2718升到首Newton后的218.1846，再缓慢降到173.2297。**只有Phi全程下降，不能声称原m_work单调下降。**

冻结工作目标为`Phi=.5||w_u Ru||²+.5||w_d F||²`，权重来自初始原算子对角，和原容差归一化最大残差不同。末Phi中damage占99.958%，mechanics约0.042%，但原力门仍超173倍。这实证了这条路径上的目标／接受指标脱节；尚不能断言换权重即能解原方程。

半径始终R=.1。选中步的`||D p_actual||inf`从3.6487291e-4降到后7轮1.0878291e-5→3.86598085e-6，最后只占半径0.003866%。rho高却不扩半径，是因为原扩张条件还要求步接近边界；并非拒绝反复缩半径。因此，仅放大R没有直接依据，R008也未做半径扫。

最后outer8同parent／load／r0的保存量经独立代数核对（[saved_algebra_review.json](saved_algebra_review.json)）：

| 已存点 | 模型下降pred | D尺度步范数 | 解释 |
|---|---:|---:|---|
| Cauchy | 7.67493356e-11 | 1.34486469e-6 | 通过充分下降，required1.94405395e-11 |
| PG1 | 1.49611458e-10 | 2.63227003e-6 | 比Cauchy进一步改善 |
| PG2，最终选中 | 2.18892710e-10 | 3.86598085e-6 | 实际下降2.18892709556e-10，rho.999999996986 |
| 可行optional Newton | **−1.16169138e-8** | .1 | 模型变坏，未选／未做非线性评价 |

四个使用原saved J与high+tail的模型数值均在原保存区间内。已保存原块方向在线性模型q约3.9270e-27，但其`||D p||inf=.94722569>R`，不能作为合法候选；经过当前盒／TR可行化后，optional的q为2.497514487e-8，高于base1.335823110e-8。1264是**第二层representable-inner状态投影**相对已经缩放／裁剪提议改变的分量数，不是完整原Newton方向总clipping数。

由此支持的机制是：精确求解原非活动块方向，不保证逐分量投影后还保持完整耦合模型下降；现有子问题只做Cauchy＋两次PG＋一次optional比较，后7轮实际退回了小PG。它没有证明盒约束LS已近最优，8轮耗尽也没有证明原方程无根。是否存在更好的可行子空间方向、尺度谱性或active-set几何限制，以及不同工作权重的贡献，仍是竞争解释；没有新谱估计／条件数／方向扫或非线性试算来判死其中某一项。

## 成本瓶颈与可用数据

非嵌套root共160.040077秒：块LU46.056591秒；box-LS35.685884秒，**已包含stage写入27.869177秒**；model写入28.263554秒；其他50.034048秒。stage/model/方向/工作点/候选等必要证据写入开销显著，但它们不是本次首停的直接原因。不能再把stage27.869秒加到LS父块上，或把所有IO都当可删。

每个后续外层约20秒，却只执行4次更新和28–34 charged actions，未用尽每子问题16更新／100动作包络；重复块LU与全量model覆盖成本已支付，但可行LS改进仍浅。这支持下一设计优先提高**每个既有模型内的可行方向效率**，并保留最少阶段证书；不能从中直接许诺更快完整轨迹。

![最后实际工作场](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v11_20261021/analysis/r8_last_joint_fields.png)

同一首步载荷下fresh8基点→fresh9已评价候选，u/v/d使用共同色标与有符号差值；它们均未接受，不能拿场变化当裂纹演化真值。四图及CSV有同stem说明，PNG已视觉核查，原网格Q4均值绘制，无场插值或新FEM重建。

![接受场只有初态](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v11_20261021/analysis/r8_accepted_prefix_fields.png)

![可用演化只有初态](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/hybrid_solver_repair_v11_20261021/analysis/r8_available_prefix_evolution.png)

没有新接受场、反力序列、疲劳退化或完整轨迹；没有step2，故不能评价R3第2步反弹是否被解决。R007/R008 policy_id不同，首候选标量相同不等于完整state-contract相同，不拼接轨迹、不作隔离因素速度结论。

## 下一路线设计，仅前瞻方案，不执行

保留原方程、d_n下界、边界、真实f_solve/f_commit、最终QP／机械／当前K／单次CAS和原接受精度。下一若另获授权，针对一个机制做**盒约束子问题内的可行耦合方向求解**：从现有合格Cauchy点起，用自由变量子空间的有界Krylov最小二乘改进，遇到边界时截断／更新活动集，避免将一个不受盒约束的精确块方向直接逐分量裁剪后当作主要耦合修复。保留当前模型定义及原证书作第一比较，以区分求解器质量与换目标收益；不同时改权重并宣称因果。

未来判别路线应在同原状态／同总资源内，将现有“两次PG”与上述约束内改进比较：至少记录可行模型下降／Cauchy比、投影梯度或子问题最优性缺口、实际步／半径、原Ru和damage门比、每次J/JT及内外费用。判别重点是能否用已支付的模型获得更有效的可行耦合步，并经真实QP最终认证推进连续原轨迹；不是仅把8改大或把Phi继续压低。该路线需要先说明活动释放、表示域证书和有限JJT包络，尚未实现／审核／执行，也不承诺全局收敛。

目前最少未决量是：现有可行盒子问题距离最优还有多少、自由子空间方向能否同时改善原Ru/KKT、以及固定工作尺度的影响。它们不能由本次9个fresh标量和末次四向量全部分离；本轮不补新J动作／优化／FEM。若未来在同预算内无法取得更有效可行下降或原物理门仍停滞，应据新证据转向目标／尺度设计，而非继续逐次加步数或训练。

## 费用与收尾边界

共享R007/R008时钟仍自**01:04:27Z**起；R008新动作自**02:24:52Z**起，较严绝对结束**04:54:52Z**，没有重置。终态共享calendar6329.999787秒，R008自身1504.999785秒；R007保守4825秒已包含其中，不能再加。R4/R5/R006分别4390／3056／2445秒与旧已知1232.462627637秒保留；到终态已知／保守累计17453.462415008秒。phase、producer、机械动作、取回、分析／审核／图／Obsidian均是calendar的包含项，不逐项重复相加。

[completion_cost.json](completion_cost.json)记录结果复核／归档后的日期费用，[closure_cost.json](closure_cost.json)记录最终Git／正文收尾及保守余量。全包CPU、准备与Mac分析RSS/AS峰、若干块间耗时未知，明确UNKNOWN；保留已有workerCPU、测试CPU等部分测量，不能填零。存储以终态169文件147540936B为准，monitor149.38MB包括采样时临时／覆盖文件，不能当最终归档大小。单独记录本地镜像／分析／缓存／Vault的已识别逻辑字节及未测范围。

本报告和四图的同一既定独立结果复核见[evidence_review.json](evidence_review.json)，只覆盖保存证据及方案边界，不授予新科学尝试；费用后续日期收尾单列，不冒充静态审核已覆盖。原唯一attempt消费完毕，**无自动重试、无新模型、无R009**。
