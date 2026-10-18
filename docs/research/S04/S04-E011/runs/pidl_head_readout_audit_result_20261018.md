# E011 c20 冻结端点：基底与梯度读数判别

**目的**：补齐旧失败断言前缺失的记录，保持1e-10不变，区分基底重建与梯度计算的数值影响。

**执行**：同一已接受PIDL c20s4端点（来源pf_s04e011_learnednewton_e2dc61d_20261018T125034Z_production的accepted_network.pt）／源档99／双精度，固定FEM conditional c20s4 outer18 damage、原UV边界及Smooth B0损伤参数化（本轮力学目标固定FEM damage）、全部权重和历史输入。原生Q4/2×2GP，86756节点／86408单元，U=.11999988、E1、ν.3、η0。3次完整网络、5次固定场力读数；旧保存T重建Phi＋3份同缓存输入重建Phi；32份GPU投影向量完整保存，另有独立NumPy Q4回放。0参数／历史／FEM更新。

| 计算路径（同一PIDL字段、同一力） | 旧T在本轮重建Phi | fresh0/fresh1/fresh2 |
|---|---:|---:|
| GPU实际PhiᵀR：主判据 | 3.3665696099e-11 | 1.1159427375e-10 |
| NumPy相同Phi/R | 3.3665509333e-11 | 1.1159448290e-10 |
| NumPy独立Q4力再投影 | 3.3664548982e-11 | 1.1159467382e-10 |
| Tᵀ原始参数梯度：仅辅助 | 2.0540230630e-10 | 2.0540230630e-10 |

**结论**：本轮固定基底的8次力读数与5次固定投影重复均完全一致；3份fresh T/Phi也逐字节一致。因此本轮不是SVD同输入重复的随机波动。仅切换数值基底，就能使直接PhiᵀR的1e-10标签翻转；同Phi/R的GPU／NumPy向量差≤1.245e-15，独立Q4力最大差4.135e-17，均不翻转标签。辅助参数梯度变换路径另有约2e-10差异，不能据此替代主判据。

两种Phi最大差3.8184e-8、rank均386；当前保留设计条件数5.2533e8、T最大幅值7.3659e7，支持数值放大的解释，但未唯一定位其底层来源。固定R的q=Phi(PhiᵀR)在同CPU质量L2下差1.4152e-10；q不是已独立证明的严格正交投影，其变化不是u/v/d变化。GPU质量重复略有差异，但所有freshSVD使用mass0，未作质量因素臂，不将质量装配定为原因。

PIDL字段／能量未变：Eel=.005268400005223913，自由位移残差≈.01348894，对同FEM的UV质量相对L2=.0754865、active相对L2=6.12090。26个保存网络张量前后与源完全相同。每层参数梯度范数与完整2×401 UV头梯度已记录；隐藏原始梯度∞=.0440131，UV头原始梯度∞=1.286e-13，与保留坐标梯度不同，不能混作全网络收敛判据。历史无提交，未单独导出before/after历史张量；冻结输入与已审无变更代码及producer flags作为该部分证据。

旧通过Run未保存完整Phi；本轮source列是本轮缓存design乘旧T，不能当旧Phi逐元素存档。旧失败Run具体g/Phi仍未知，不得回填本轮数值或唯一追溯旧失败，也不撤销旧原坐标结果。无优化效果、全网络容量、物理teacher或疲劳演化结论。

D1冻结状态与记录完整性通过；D2分离本轮基底切换与力／归约影响；D3选中**持久化实际Phi并与权重绑定，同端点复用，特征变化后才重建／校正输出头**。仍用直接PhiᵀR和1e-10。确定性质量权重可作下一因素，未执行修复或继续训练。

生产commit a698ec7b3c4ff98c1df50dacf7fc5adbdf8faa94，branch codex/hard5-q4-t3-2x2-20261005；Run pf_s04e011_readoutaudit_a698ec7_20261018T203915Z，GPUServer8/GPU5 UUID GPU-5622bd47-1050-3003-246d-3cabe2b4791b，PID3703382已正常退出。10calls／24.77167运行状态秒（上限32／600），0优化、0重试。暂存资源等待与JSON格式归一化均在Popen之前，未改数值参数。

原始53文件／1,400,670,192bytes已远端SHA核对；本地32份完整raw文件逐个SHA核对，19份分析交付2,580,245bytes逐个SHA/大小核对。本地全量镜像因600秒传输上限中断；大Phi／features与84MB分析physical_arrays仍远端留存、路径和SHA已记录，不能称已全量下载。独立NumPy分析在Taobo单线程CPU、CUDA隐藏，0新增网络前向／SVD／求解。

本地资产：`local_archive/experiments/S04-E011/runs/pf_s04e011_readoutaudit_a698ec7_20261018T203915Z`；分析README、完整投影向量／CSV、4图／sidecar、原始SHA清单、独立保存状态核对均在该目录。主图readout_decision.png来自已存summary的展示修订，未新增数值回放；其余3图保留并已检查。Git只存本摘要、绘图代码和[紧凑证据](pidl_head_readout_audit_evidence_20261018/compact_result.json)。用户状态与图：[mesh对齐.md](/Users/wenxiaofang/obsidian/mesh对齐.md)。
