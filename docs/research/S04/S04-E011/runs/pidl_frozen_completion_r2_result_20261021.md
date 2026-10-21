# PIDL c20冻结控制补齐：四臂均未消除导数失配

**目的：** 在同一冻结FEM c20第4子步峰值damage、原PIDL源历史、B0 Smooth Boundary、原UV边界、实际Phi/T0与头梯度1e-10下，分清近似头驻点和弹性分支变化是否解释PIDL导数失配。这里比较PIDL诊断场映射，不是新FEM求解或新的PIDL优化端点。

**本轮：** 新前瞻授权`HQ-MESH-FROZEN-STDIN-R002-20261021`只补`frozen_constant/frozen_zero`，原native R1两臂不重算。两冻结臂31.532576秒完成，无OOM／非有限／状态错误；worker/controller/guard均正常退出，自有live=[]。与不可变native原量合并后，四臂均未过原FD判据，3000秒隐藏优化未启动。

## 同状态四臂读数

固定方向seed173、h=1e-6，范数为共同自由UV顺序的未加权L2。原FD阈值为`1e-10 + 1e-4 max(||Qv||,||FD||)`，约0.00130574；它与物理输出头梯度阈值1e-10是两种不同条件。

|PIDL控制映射|源物理头梯度∞范数|‖Qv−FD‖₂|失配／原FD阈值|数据来源|
|---|---:|---:|---:|---|
|native，保持g=g0|3.36656e-11|0.009444733263|7.233244|旧fa9ce259/R1原量|
|native，零根重锚g=0|1.46638e-15|0.009444733342|7.233244|旧fa9ce259/R1原量|
|冻结源弹性分支，保持g=g0|3.36657e-11|0.009506254089|7.280360|本轮f5972efd/R002|
|冻结源弹性分支，零根重锚g=0|1.74210e-15|0.009506254020|7.280360|本轮f5972efd/R002|

![四臂PIDL导数检查](/Users/wenxiaofang/obsidian/attachments/S04-E011/2026-10-21/pidl_frozen_completion_r2_FD_four_arm.png)

四根柱都高于原阈值，零根和冻结分支均未消除共同失配。这不是FEM/PIDL场误差增减比例，也不是网络容量结论。

- 冻结臂重锚前后误差向量差1.64e-9，源场差7.46e-12；源头残差更小，没有对应的FD改善。
- native与frozen的Qv差仅6.17e-11／7.20e-11；FD及误差向量差约4.7667e-4，约旧native失配范数的5.05%。这是向量差的大小，**不是失配降低5.05%**；冻结臂总失配略高。
- constant源的Jv、H及Cholesky factor逐值相同，Cv/KJv/U/头响应差值很小，详见逐项表；例如constant臂Cv相对差约5.9e-12，不等同于已证明舍入地板。共同Jv范数约53032.7，而校正后Qv约13.06，提示大项抵消的数值敏感性，尚不是原因证明。完整逐项差见[derivative_terms.csv](pidl_frozen_completion_r2_result_20261021/derivative_terms.csv)。

## 误差位置与数值边界

![共同色标的四臂导数误差场](/Users/wenxiaofang/obsidian/attachments/S04-E011/2026-10-21/pidl_frozen_completion_r2_FD_four_arm_fields.png)

四臂最大误差均在节点(x,y)=(0.35098756,-0.03927073)，top1%节点贡献约77.4%–78.2%的误差平方和，场分布接近。图是Q4单元内节点向量误差的RMS，共同symlog色标；不是damage／active误差或新的裂缝场。每臂解场trace在±侧仍有5个GP换号；冻结臂能量始终使用源mask，这个几何换号统计不表示冻结控制失效。

线性日志15次调用均有开始/结束及H/factor/RHS/solution/residual，无中断，包含11次向量求解和4次逆列求解。向量相对残差约4.85e-16–1.61e-15；逆列残差∞范数约1.96e-13–1.97e-13。这些只评价已存线性系统，不是完整原生非线性或场前向误差证书，也不补造旧R1缺失日志。

**关键缺项仍在：** 条件线性FD上界约6.03，约原门4619倍，且力／矩阵装配的算术误差界不完整。它远未低于原门的1/10（约1.31e-4），不能据此排除共有数值误差。当前有限方向/h证据削弱“仅源残差”或“仅trace跨支”的解释，但未证明唯一原因，也未区分优化不足与参数化上限。

## 身份、执行与资源

源`f5972efd9b9bb8bba9ba42b13fc0af7174c980f4`，分支`codex/hard5-q4-t3-2x2-20261005`，Mac干净快照。包SHA `cbc2986100e206576a3e229f08094c9620227f0c3f5980e0b1019d515d317bb1`；authority SHA `f1306ecd2f7967fc733ddebeafc35bd25478c9d87a3c5d32e991dbc95bf7f108`。

Run `pf_s04e011_frozen_completion_r2_hq_20261021`；GPUServer8/drtao、GPU5 UUID`GPU-5622bd47-1050-3003-246d-3cabe2b4791b`，worker3997835、bootstrap3997764。root `/mnt/data2/drtao/wennie/<Run>`，archive `/mnt/data2/drtao/pidl_archives/<Run>`，日志`<root>/worker.log`。完整命令、PID、准入和终态见[receipt.json](pidl_frozen_completion_r2_result_20261021/receipt.json)。授权来自已核实的人方夜间托管，原HQ线程01a14bb9-6cd1-7ee2-9647-5190d786f7ba；这不是5449d5a9旧许可重用。

首次GPU空闲24077MiB，无冲突；六原输入＋371复用项SHA/bytes全过。source/±三处派生Phi和qraw分别与旧缓存逐值相同，方向／尺度／自由DOF／T0／源trace／原始输入与物理算子身份通过。旧features本体未存，**不声称旧原始features逐位一致或整个邻域等价**。冻结源E/R与旧native参考差约8.67e-19／1.73e-18，同坐标g0差约1.18e-16；source AD primal与源场maxabs=0，边界与源场不变；最终物理/网络/B0检查通过。torch2.7.0+cu126、NumPy1.24.4、4CPU affinity0–3、继承RLIMIT_AS=[-1,-1]不改。

工作：field25＋frozenK2=27/250，Qv2，JVP4/VJP0，H装配11／factor11／三角求解记账30，raw-feature forward9，SVD0，native重算0。三处值重建不等于总NN前向只有三次。峰值自有进程树RSS1,710,415,872bytes、CUDA allocated11,298,841,600／reserved12,108,955,648bytes，任务存储约1.163GB，均在原限额内。

## 输送修复、取回与成本

相同身份清单改走stdin；新card因Run/时间/授权字段变化为149910bytes，原371项完整保留。实际probe最大参数2526bytes、stage4516bytes（含NUL），每项≤16KiB且总argv≤64KiB；bootstrap及双watchdog命令逐次执行前也检查。仅机械计时改为明确授权的两批90秒。独立差量审查通过；同一个stdin往返夹具因审查修正启动确认路径共执行两次，约0.0380秒，无SSH/模型。旧失败包未覆盖。

机械保守远端计时43.4928秒；本地stage响应落盘相对客户端开始约41.0002秒，两者均含连接/核查/部署/启动确认，≤90秒。科学31.5326秒，GPU kernel/完整CPU和货币成本UNKNOWN，不能用科学墙钟冒充kernel时间。

远端599项1,162,558,770bytes全hash/覆盖核验；本地选集241项354,238,769bytes逐项核验，3份大sharedPhi仍留远端，**不是完整本地镜像**。网络gzip260,211,402bytes，取回272.1565秒，远端hash0.96995秒；manifest SHA `964c92eec66a5edce6da3d87623db5a04c67864711dbc8b2317f91d2105dee8b`，outer-return SHA `b725c8426d8f548ee666eff63e5d857b815e17408b0040225bb2b6f7e0ada4a0`。

原112.405科学／1555.63整包、27.862862科学／1368.323整包、178.813saved-only墙钟、8.052633旧首检总链、79.918925旧R2总链及所有UNKNOWN保留。整包从00:02:23UTC开始，上限1800秒，截止00:32:23UTC；当前最终收口墙钟与本地分析成本见本目录cost.json／analysis_cost.json。第一次本地分析命中缺NumPy的python3，未加载数组；随后用已有miniconda解释器完成保存量分析，无新模型/物理/AD/SVD/求解。两图已人工查看，sidecar格式检查修正后通过，没有因此重算图中数值。

## 对PIDL复现FEM目标的影响

冻结FEM基准仍E=0.0043205760、自由Ru≈3.78e-15；原PIDL端点仍E=0.0052684000、Ru=0.01348894、UV mass误差7.5487%、active加权relL2=6.120899／相关0.102518。本轮没有更好的PIDL端点、历史提交、演化或新FEM结果。

**结论／下一项：** 四臂比较已补齐，原FD自洽目标均未达标；共有误差机制仍未定量闭合。保留实际Phi、共同Q4算子、B0 Smooth Boundary与约束Q4 damage路线。最小缺项是能覆盖共同场／force／装配／求根链的可信误差控制，而不是更多优化时间。原3000秒优化继续保持未启动；本次不加方向/h/精度或Gram扫描，不创建R003救正，也不以小头残差或本次完成宣称数值原因已排尽。独立结果复核另存本目录review_result.json。

全流程的原边界继续保留：空间算子与Carrara提交状态对齐，并未消除PIDL固定committed-f与FEM trial-f、联合Deep-Ritz与staggered/Picard的差别；本轮冻结控制也不提供完整演化对齐证明。
