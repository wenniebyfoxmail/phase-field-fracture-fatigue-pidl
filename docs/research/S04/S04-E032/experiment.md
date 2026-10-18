---
storyline_id: S04
experiment_id: S04-E032
protocol_revision: v1-fixed-damage-joint-head-plane-20261018
status: preparation
---
# E032：保留E031终态，在冻结七梯度空间内联合选择一次UV头增量

目的：E031沿单一共同方向的raw收益仅.009366%，是否主要受该方向的UV曲率限制，并可在不牺牲既有七指标与damage收益下获得更大的有限改进？
当前D7，复用D1/E030/E031及E024小系数受保护选择方法。C2/synthetic单暴露c20s4/horizon0/seed1，无新状态、数据、FEM、history/holdout/泛化。不是在相同起点对两种算法作因果优劣比较。

## 运行前保存证据与方法选择

E031唯一已访问步，raw-global平方指标实际相对变化−.000187311744，线性预期−.000187300980，非线性剩余只占线性变化的−.00005747；不是raw自身曲率吃掉了主要收益。Z UV线性预期−.124965185，实际−.062482593：正曲率抵消一半，原half-crossing起步由Z UV约束。raw-global与active-global的单位原头梯度余弦−.9696461545，局部取舍强。七行单位梯度的奇异值为1.98566/1.38094/.86666/.44388/.30182/.29505/.15457，保存空间rank7；这些证据只说明该点/该方向与小空间，不能把一次小步当成802维头的容量上限。

[saved_gradient_diagnosis.json](saved_gradient_diagnosis.json)及本地preparation_20261018保留纯保存数组诊断，Mac无模型/PT、真实head拟合或新有限候选。复用E024 two_coordinate/background_plane的“小空间一次SLSQP+精确UV二次式+真实有限检查”模式，只移植选择结构，不移植其AMOR/区域/driver/状态或结论。接口/原生Q4物理及七指标完全沿用E031；[reuse.json](reuse.json)保存文件hash。旧E031和全部旧实验不改判据或结果。

## 唯一方法与起点

起点是实际E031已接受终态：物理damage继续为E030 R，逐位固定；原S1500隐藏层/activation/第三输出头不变，两个UV输出行+bias取E031 head_endpoint.npz 的实际theta，不加载E030变过的hidden weights。原S1500和四MAT身份不变，E031 fields/scores/head_geometry/head_endpoint/receipt逐文件大小/SHA。新零步完整物理场/指标复放E031 1e−10，实际模型前向核验；无新种子、损失权重或优化器扫描。

用E031已存7×802单位梯度的SVD行空间作为**冻结最多7维**的原UV头正交basis，relative cutoff1e−10，不增加/重算其他方向。z为此basis中的无量纲系数，theta=theta31+R B^T z，R=.02||theta31||F。原模型全部参数冻结，只有最后接受时写入两个UV W/b行，最多1次接受，0optimizer.step。真实producer在当前E031物理起点重新计算七指标对z的autograd梯度；这是冻结空间内当前梯度，不能沿用旧点梯度冒称当前。

七指标沿用E031：global/Z质量加权UV RMS/Us平方；global/Z原生GP4 raw/active相对L2平方；free-force L2平方/当前自身零步force平方。d/lower/fatigue/history冻结。当前七行单位平面梯度凸包若无可解析严格共同方向(margin<=1e−8或有限zero-row)，交付精确零校正；不是全头或新表示容量否定。输入非有限/证书数值失败仍首停。

## 联合系数选择与固定终点

每个basis方向用原模型features及真实lift形成包含R的物理UV速度，得到global/Z**精确**误差比二次式 U(z)=1+2b·z+z^TQz，Gram Q自然半正定，不切换物理力学定义。当前平面共同方向配合原half-crossing规则只用于给联合proxy一个非零可行初始系数，不另行实际评价该seed或作备用方法。

一次小空间SLSQP：min t，约束
- ||z||<=1；
- 精确U_global(z)<=1、U_Z(z)<=1；
- t>=U_global(z)，t>=1+(g_raw_global/M_raw_global)·z；
- 所有七个单位平面梯度 a_i 满足 a_i·z+kappa||z||<=0，kappa=.5*当前凸包margin，固定不调。

它联合考虑UV曲率与raw一阶代理，并留严格切线共降余量；不是全非线性物理优化或完整头最优性证明。一次调用、最多100 proxy迭代、ftol1e−12；所有proxy系数迭代/目标/最小约束保存。仅success且有限、primal约束>=−1e−10作为数值求解可用；这是proxy容差，**真实物理指标无slack**。数值失败/不收敛即整次首停、不重试、不换solver。若可用proxy无可解析改善，按协议输出自身起点，不转其他法。

对唯一联合proposal，只检查fraction=2^-k,k=0..8的最多9个真实有限候选；同一proposal、首个七指标均不增加且global UV/raw均有解析下降(max两RMS比值<1−1e−8)的候选为固定终点。没有bestpoint选择或新方向；全拒绝则精确复用E031缓存场和theta31，同时保留实际NN前向一致性检查。未接受不返回最小误差候选。候选拒绝是声明的单次内部line-search，输入/非有限/物理界/资源故障则整个attempt首停，不能靠下一个候选救援。

最终真实NN与线性features头前向差<=1e−10，非UV参数逐位不变，damage/历史/疲劳与物理界保持。保存basis、当前7×k梯度、UV速度矩阵/二次式、共同方向/seed、一次联合proposal/所有proxy迭代、所有已访问有限候选、theta31/终theta、实际场/分量/原模型+物理d checkpoint。总计100代理迭代+最多9真实候选，低于允许200有限更新；代理迭代不冒充NN optimizer.step或实际场评价。

## 事前标准与结果分层

唯一探索主标准：**相对实际E031，全域raw RMSE至少下降.1%（比值<=.999）**；同时global UV解析改善、七项真实指标不增、d逐位不变是接受前提。目标幅度约为E031 .009366%增益的10.7倍，用于分辨更有用的方向/曲率进展，并非参考不确定性已支持的物理准确性或显著性阈值。当前保存方向/梯度不足以保证可达，不据此预报成功；E031既有数值方向标准不倒改。

若主标准通过，只支持冻结七维空间内一次较大组件改进；若仅小幅共降，保留真实组件结果但本轮raw幅度目标negative；无接受则本配方零校正，不外推完整头容量。科学主目标未达不自动加更小步、换basis/优化器/权重。完整报告相对E031、E030与其d0的global/Z u/v/UV/d/raw/active、force/reaction/物理界及同色标实际场；反力等次要读数不覆盖主标准。相对更早对照若有真实取舍单列，不隐藏旧全域active代价。FEM UV代数替换不混入实际方法，也不称网络oracle。

下一决定由证据选：若raw仍很小/无接受，收口当前冻结小空间配方，准备一个最小表示或物理分布限制的选择给HQ；不无限改优化器/权重。不在本次协议内执行下一方案。

## 资源、授权与首停

HQ直接人方夜间继续托管userMessage01a15126-2cc8-7f22-a54b-4054bb54aa65已现场核读，原最小有判别力试验连续到真实场/数值授权及本次D7具体派发有效。旧五Run receipt共1.07992943710646GPU小时；本次一次最多.5，最坏1.57992944<原2GPU小时总限。单GPU实际UUID，启动空闲>=20GiB/SM0/无计算进程，allocator<=free−1GiB、余量>=1GiB，RSS32GiB、输出2GiB。预计与E031梯度/评估/图约34秒同量级外加7方向UV及小空间系数求解；保守<=1800s，外层1790s TERM+5s KILL。缓存/tmp/output均fresh /mnt/data2路径，独立clean exact Git snapshot。

Mac仅保存数组诊断与synthetic轻量fixture；真实模型/当前梯度/头校正仅producer。必要独立焦点review绑定精确源码后才启动。输入/来源/主机/GPU/零步身份不符、非有限、联合求解数值失败、物理d/历史/非UV参数变化、界/预裂纹>1e−10、前向不符、时间/内存/输出超限均首停不重试；不换权重、不接触封存、新状态或别人的进程。
