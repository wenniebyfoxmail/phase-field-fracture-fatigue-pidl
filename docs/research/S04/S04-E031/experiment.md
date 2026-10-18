---
storyline_id: S04
experiment_id: S04-E031
protocol_revision: v1-fixed-damage-UV-head-common-step-20261018
status: preparation
---
# E031：固定E030物理damage，核查UV输出头的可达方向并实现一次有限校正

当前D6，复用既有D1与E030结果。先有代数归因，后决定最小干预；所有旧Run/判据不改。本轮是已暴露synthetic c20s4/horizon0/seed1的C2组件探索，无新状态/留出/FEM/history/泛化。

## 代数归因与已有路线复用

同一原生Q4保存场，UVown/FEM × d0/dE030四组合：ownUV+d0的global active RMSE .05274395，ownUV+d30为.08028759；FEMUV+d0为.00277216、FEMUV+d30为.00266322。原Z对应.772727/.738755/.743167/.716707。FEMUV+d30 free force .00080877，而actual E030为.02503289。FEM UV组合只是代数替换，不是平衡解、可训练oracle或本试验结果。

精确GP4分区中，E030 d替换的active积分平方误差变化：原Z −6.89613e-7、左裂纹窄带(x<0,|y|<=.03) +.00366486263、带外 +4.63942e-10。全域代价几乎全在左窄带。恒定own raw下DeltaA=raw*Delta((1-d)^2)，DeltaSE=积分(2e0DeltaA+DeltaA²)，数值逐项核对；不能把RMS或交叉抵消项当可相加因果百分比。parent_substitution.json及本地preparation含图/CSV/所有组合。

已核读其他owner最新结果：PC16 c1同能量头检验预算内阴性，不能据此否认当前头容量；E024完整头存在共同下降方向、三维有限步可行但收益很小。只复用其通用共同下降/UV曲率助手，不复制三态物理场、AMOR driver语义、窗口、basis或结论，不重跑他们的计算。reuse.json保存确切路径/代码hash。当前86756节点坐标均唯一，未发现同坐标多标签的直接表示冲突；这不是当前头可达性的证明。

## 唯一方法和准确起点

物理起点必须完整复放E030 R：UV来自原S1500的物理预测，d为E030实际fields.npz R[:,2]不可变buffer。**UV网络使用精确原S1500，不能加载E030已被damage训练改变的hidden weights**；后者配合固定UVbuffer才是E030的物理场，不可无声解除buffer。原S1500大小/SHA及四MAT保持，前态c20s3/fatigue/history冻结。新零步全部指标匹配E030终态1e-10。

固定全部hidden/activation及模型第三输出头，仅在原UV输出W+b的802个坐标内改变两个UV行；物理d单独固定，不通过NN第三输出或可变映射计算。最后实际NN前向必须与固定feature的线性头计算一致<=1e-10；全部非UV头状态逐位不变。E030 d误差/增长域收益因此完整保持，目标FEM d不作为输入或lower。

不是再跑200步Adam：选择**一次共同下降有限头校正**，最多9个前瞻候选、最多1个接受的真实UV头写入，0optimizer.step，总量远少于允许200更新。没有lambda/优化器扫描、无约束联合训练或新head容量。

在起点计算七个平方指标对802坐标的真实autograd：global/Z UV RMS/Us²，global/Z raw与active的原生GP4参考相对L2²，以及free-force L2²/自身初值²。复用单位梯度凸包最小范数算法，允许梯度数由5扩至7；非零证书给严格共同下降方向。证书检查原单位梯度斜率、凸包KKT与margin，<=1e-8不称可解析方向。无方向/数值证书不成立则停止为零校正，不转其他目标或方法，不称一般容量不足。

头增量半径固定为原UV头Frobenius范数2%。沿同一单位方向计算该半径的物理UV速度；global/Z的精确MSE(t)=c+2bt+at²给正零交叉−2b/a，取t0=min(1,.5*min交叉)。这复用已验证的曲率起步，防止把2%上限直接走满。只按t0*2^-k,k=0..8取**首个**实际七指标都不增加、且主读数解析改善的候选。候选拒绝是已声明单次line-search内部，不是Run重试；候选全拒绝则实际模型/字段精确退回起点。不得追加更小步或另选方向。若输入/数值/物理界/资源故障，整次首停，不能走下一个候选救援。

## 终点标准与读数

唯一探索主读数为max(R_global_UV_RMS, R_global_raw_RMSE)<1−1e-8，两比值均相对本次完整E030物理起点。两项同时改善是本轮UV/raw目标的必要条件；这是数值方向信号，不是实用幅度或统计显著性门槛。七项真实有限指标均须不高于起点，保护原Z UV/raw与local/global active、force。头参数半径仅允许1e-12相对浮点预算容差，物理指标无额外slack；方向证书不替代实际有限检查。

报告所有global/Z u/v/UV/d/raw/active、force/reaction、节点/GP lower/upper/healing/precrack、d逐位不变、原S/模型头身份、原E030零步作对照并保留更早的全域代价。每个已访问候选的七指标、原相对头增量、步fraction、拒绝原因均保存；不择最好。即便接受，微小收益也必须按真实量级报告，原UV/raw未全面修好、damage固定并非演化成功。若无接受，只支持本方法/预算未实现共降，不推广为UV头容量不足。

输出实际原生u/v/d/raw/active与有符号误差，FEM/E030原零步/E030终态/新UV头同色标；代数FEMUV替换图另存preparation并明确标注，绝不混入真实方法。保存802梯度/方向/原头/候选、UV速度/曲率、实际NN+物理d checkpoint及所有身份/资源收据。完整取回hash、CPU已存字段重算与必要独立图/数值核对后交HQ。

## 成本与停止

直接人方持续最小修复授权及HQ本轮D6具体派发有效。四次旧运行receipt累计约1.07054GPU小时，本次最多.5后<=1.57054，低于原2GPU小时总限。一张允许GPU/实际UUID，空闲>=20GiB、allocator<=free−1GiB/至少1GiB余量，RSS32GiB、输出2GiB。预计显著小于此前200步+绘图的410.8秒量级，但执行硬上限仍1800秒含身份/可达性/候选/评估/保存；外层1790秒TERM+5秒KILL。

Mac只做保存数组分析和轻量fixture，真实模型/梯度/头参数校正均在producer。本次一个fresh Run，输入/schema/clean source/host/UUID/零步身份不合、非有限值/证书计算失败、物理d/历史/非UV参数改变、物理界/预裂纹>1e-10、实际头前向不符，或时间/内存/输出超限，整次立即停止、不重试/恢复/替代权重。无新增云资源或共享进程动作。
