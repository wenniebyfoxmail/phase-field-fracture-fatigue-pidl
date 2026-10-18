---
storyline_id: S04
experiment_id: S04-E033
protocol_revision: v1-full-head-eleven-guards-one-axis-20261019
status: preparation
---
# E033：完整UV头只读诊断；有证书才作唯一单轴增广校正

D8，沿用D1与E032结论。E032 raw .0460%未达.1%，u全域/Z误差回退15.25%/8.30%；旧结果与七维配方冻结。本轮不重跑它的候选或调共同margin/权重/优化器。C1当前可达性诊断→条件性C2单暴露synthetic c20s4/horizon0/seed1校正，不作因果算法优劣、完整NN容量、物理演化、teacher或泛化结论。

## 两阶段问题与硬边界

1. 在**实际E032终态**，当前原802个UV W+b坐标内，raw/active/force与分开的u/v全域/Z指标是否有可解析的严格共同下降方向？当前完整梯度在冻结七维B内/外的范数是多少？
2. 仅当完整方向确在B外且可精确重构时，只增加它的一条正交轴，能否实现一项不再牺牲单独u/v的实际有限校正，并使raw至少下降.1%？

原S1500的hidden/activation/第三输出头冻结，UV头取实际E032 head_endpoint theta，物理d继续为E030 R并从E032字段逐位继承；不得误载E030训练过的hidden，也不以FEM target替代d/lower。原四MAT、c20s3前态/fatigue/history及S1500大小/SHA不变。E032 fields/scores/head_geometry/head_endpoint/receipt大小/SHA全部绑定，[data_lock](data_lock.json)。新零步完整物理场/分量复放E032 1e−10，最终NN前向与affine head一致<=1e−10。

## 复用与诊断：无optimizer update、无FEM求解

复用E024 full-head cone的最小范数单位梯度凸包，以及enrich_basis的精确单轴重构；E031有限零行处理和E032实际原生Q4/力学/曲率/proxy保护保持。仅把凸包行数扩到11、旧轴数扩到7、候选空间最多8；不移植E024 AMOR/driver语义、状态/字段或结论，也不重复其他owner现有状态计算。[reuse](reuse.json)保存确切助手hash。

十一项平方指标，前七项顺序沿用E032：
- 全域/Z UV质量加权RMS/Us平方；
- 全域/Z raw、active的原生GP4参考相对L2平方；
- free-force L2平方/本次自身零步平方；
- 分开的u_global、u_Z、v_global、v_Z质量加权RMS/Us平方。

直接对原theta的802坐标计算全部真实autograd，force保留create_graph二阶链；每一行梯度先保存再做有限性检查。保存11×802矩阵、原B、投影与正交残量、每行full/inside/outside范数和比例。分别保存完整头与旧平面的凸包KKT/方向证书；检查实际单位梯度斜率，margin>1e−8且斜率<=−.5margin才称解析严格方向。有限zero-row或无严格方向是诊断结果，不调用备用方法；非有限/数值证书不成立首停。若旧平面的实现方向明确支持完整头下降而完整证书矛盾，按数值故障停止，不转用另一方向救援。

完整方向v与B的正交余量norm<=1e−8则不强行增加轴；不能因有剩余半径而造增广。无完整证书/无可解析B外方向则保存精确E032字段/头作为零校正终点，optimizer/history/FEM计数均0。该结论只限定当前点/严格一阶问题和本配方，不否定真实非线性或全网络能力。

诊断从本次起始计时<=900秒，Linux独立SIGALRM与循环/梯度guard保护；任何首停不重试。输出诊断后才解除此阶段alarm，记录diagnostic_seconds；总Run仍受1800秒/.5GPUh和外层1790s TERM+5s KILL约束。

## 唯一条件性增广和有限校正

仅有支持时，保持旧B七轴逐位不变，加一条e8=(v−B^TBv)/||v−B^TBv||；v必须由八个坐标精确重构<=1e−12，新basis正交<=1e−12。模型head容量仍为802，未增hidden。当前full梯度投影到新八维并乘R=.02||theta32||F，验证重构方向对**十一项**都严格下降；kappa=.5*该方向最小单位下降margin，固定不调。

原features/lift给八轴包括R的物理UV速度；得到六个精确相对误差二次式：全域/Z的UV、u、v。以重构方向的六项最小正零交叉的一半作唯一proxy可行seed，不实际评价它、不作fallback。

复用一次E032小空间SLSQP，最多100 proxy迭代、ftol1e−12，min t，约束：
- ||z||<=1；
- 六个精确UV/u/v二次式均<=1；
- t>=全域UV精确二次式，t>=raw_global归一一阶代理；
- 十一项单位平面梯度均满足a_i·z+kappa||z||<=0。

保存全部proxy迭代/目标/约束；有限、success且primal>=−1e−10只承认代理数值可用，不保证非线性物理或全头最优。非收敛/数值故障首停，不换solver。只有一个联合proposal，fraction=2^-k,k=0..8，至多9个实际有限候选，首个十一项实际值都不增、global UV/raw解析下降(max两RMS比值<1−1e−8)的候选为固定终点。实际值无slack；u或v单通道增加也拒绝。全拒绝则精确E032头/字段，不选bestpoint/seed或另方向。

总计<=100代理迭代+9真实候选/最多1个接受头写入，0NN optimizer.step/history/FEM，低于200有限更新/声明候选额度。凸包枚举是诊断线性代数，不是NN更新或额外有限候选。最终非UV参数、物理d/前态/history/fatigue逐位不变，物理界/预裂纹<=1e−10，实际NN前向及UV速度关系核对。

## 事前判读与证据

诊断与校正分开：完整/旧平面证书、B外方向有无先报告。没有支持就诊断-only收口，不能说增广或修复已执行。有支持才执行的校正唯一探索主标准：**raw_global RMSE相对E032至少再降.1%（<=.999）**；十一项不增、globalUV解析下降和d身份是接受必要条件。该幅度沿用E032阶段目标，不是参考不确定性支持的物理/统计准确性界。

校正若仅小幅共降，主幅度目标negative但保留实际组件；没有接受则零校正，不为科学primary miss制造重试。所有结果与E032、E031及旧E030 d0同列，尤其u/v分量回退是否被停止、旧global active代价和反力过冲是否仍在。字段、五场同色标/有符号误差、实际候选、完整802梯度/投影/证书、单轴重构、参数/UV速度、identity/resource/下载hash及必要独立复核是交付。FEM代数UV替换不混入实际方法。

## 资源与授权

HQ直接人方夜间继续托管与既有最小试验授权有效，本次D8明确授权<=15分钟诊断+有支持才作一条轴的有限校正，合计<=.5GPUh，不另待普通预算批准。旧六Run累计1.09177619513718GPUh，最坏加本次.5后1.5917762<原2总限。单GPU实际UUID、空闲>=20GiB/SM0/无计算进程，allocator<=free−1GiB且保持1GiB余量，RSS32GiB，输出2GiB，所有缓存/临时/输出在fresh /mnt/data2目录；clean exact Git snapshot与必要独立焦点review后才执行。

Mac仅合成fixture和保存数组分析，不加载真实PT/模型、真实梯度或头拟合。来源/shape/零步/主机/GPU身份不符、非有限/证书矛盾、物理界或非UV/d/历史改变、前向不符、联合求解故障、时间/内存/输出超限均首停、不重试、不替换权重、不触及共享进程或封存数据。下一方法不包含在本Run；本次结束保留全部证据交HQ。
