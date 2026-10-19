# 完整混合求解 producer 执行方案（当前卡v2）

日期2026-10-19。延续同一S04场一致性目标；本轮按用户“完成独立复审后给我看可执行的完整方案，无误后开始运行”的条件指令准备。当前科学工作是完整方法探索性比较，不是逐个开关或最小验证。只有精确代码/卡独立复审及实时准入通过才执行；不把开发库复审当作producer复审。

## 已完成的原生算子与状态对齐

复用已见c1 v4/r1的网格、zero-load恢复二维damage、251预裂纹节点、原生自由DOF、A/r/f及opaque channel1；不新增初始化FEM。native位移/力blocked存储经显式排列转为canonical interleaved；history从HDF5转为(element,GP,channel)，native四GP顺序不再二次排列。重新从geometry生成的固定DOF与导出自由DOF经排列后完全吻合；五态的固定边界均核对。

`native_operator_replay_v1.json`在五个已见保存场上核对raw、Ru、Rd、A/r/f：5/5通过原1e-10阈值，最大Ru差1.863e-16、Rd差5.903e-18、raw/history差1.584e-12；Mac纯后处理耗时2.808秒，无新状态求解。producer在正式轨迹前再次回放自己的运行时，失败即停。该结果不覆盖f<1反馈，也不要求把固定f的Picard矩阵当作整个history map的全Jacobian。

归档AT1源码SHA70b01f0b...与native manifest一致；live ff6c9ddb...仅CRLF/LF不同，文本内容完全相同，见native_source_identity_v1.json。保存的MEX和source identities继续入输入manifest；不声称在Linux重编了同一Windows MEX。

初态是明确给定的、可行的已恢复state0：u0=0、完整d0、lower=d0、A0/r0=0、f0=1，原生channel1原样保留；其作用是共同预设初始条件，不是新后端已训练标签。初态与所有输入资产SHA在inputs.json及执行卡绑定。

## 标签复用与真实缺口

已有5个repaired c1状态可做算子回放，但0个已认证新合同标签、0个合格完整轨迹。四个加载态的保存可行梯度高于1e-7工程目标，且全部接受f=1；不放宽旧标准，不把它们投影成teacher，也不读取关闭的旧完整轨迹来凑标签。原生已恢复初场与operator证据的复用避免重做recovery/原生FEM对照。

新合同标签需由同节点K和trial-map下的直接数值参考产生：训练0.8/1.2倍幅值各600子步、验证1.0倍600，合计1200训练+600验证；测试0.9倍600仅在模型冻结后产生/开放。这个数据缺口实质需要最多2400个新的完整接受子步，不能用已有欠闭合端点免掉成本。本轮执行条件满足后才开始这些计算。

## 一次成套流程与防泄漏

1. native_replay：读取已见五态作同场算子复核，0新FEM。
2. train_A、train_B、validation：各120cycle×5，以同state0、相同材料/网格、既定幅值生成完整参考轨迹。每个物理子步保存接受态/前态ID、fresh证书、工作账本及common u_pred/psi_pred派生的输入特征。
3. training：仅访问1200训练/600验证标签；训练集统计归一化，四块64宽图网络、单d初值头、Adam1e-3、seed20261019、最多20000updates/8GPUh/1fit。每1000updates全验证，3次未改善早停。无架构或loss权重扫描；test不参与选模。图网络默认head weight0/bias.05避免clip死初始化。
4. test_reference：模型冻结后按0.9幅值产生600步同问题NN-off参考。
5. test_classical、test_hybrid：各600步，从同state0出发但分别推进自身接受态；只改变初值来源。经典可行secant规则预先固定；NN每步一次，随后完整空间u/d/f校正。候选构造阶段不读取reference状态。
6. analysis：全部输出冻结后统一计算u/v/d、A/r/f、反力误差和方法成本，单独计研究评分成本，不混入某个候选的在线时间来造提速或惩罚。

若任何轨迹提前数值失败，整个包停止，保留接受态和失败账本；不拿局部标签直接凑一次fit，也不改成另一条最小研究路线。完整120cycle并非收敛保证；eta0临界/退化风险如实暴露。若已接受路径不含f<1，则疲劳反馈结论覆盖不足，不自动延长。

## 固定数值条件与评价

保持AT1/Amor平面应变、E1/nu.3/Gc.01/ell.01、eta0、alphaT.5/p2、native86756节点/86408Q4/四GP，原预裂纹线d1。节点d_n≤d≤1，lower不随inner滚动，所有活跃集可释放。w1=Gc/ell，thickness1；无新对称/参数正则/gamma项。

执行卡加强现库接受合同并保留旧严格联合条件：Ru自由DOF L2≤1e-8，同时Ru_L2+Rd_feasible_L2≤4e-6；另要求final KKT_Linf/固定梯度尺度≤1e-7、投影≤1e-7、界≤1e-10、f fixed-point≤1e-8、QP eps1e-10。force/gradient尺度固定为1，对应本无量纲E=t=L=1的全域标度；卸载不除近零载荷。数值核对仍1e-10，不放宽原raw或严格链检查容差。每步100outer/50mechanics/200000QP、求解器120秒合作式deadline及外部watchdog触发；不是120.0秒精确OS终止保证。watchdog约1秒轮询，GPU查询超时2秒，TERM grace10秒；阶段、replay+analysis合计、总host/GPU预算的停止触发提前45秒预留清理。慢文件系统或OS调度可能延迟监督，实际超时与终止费用如实记账。

探索性联合主判断：完整路径物理条件合格，NN相对同问题参考mean J≤.001/worst J≤.01（u/v除固定.108位移尺度，d原值），A/r相对GP RMS最坏≤5%（近零范数用1e-8固定floor）、f RMS最坏≤.01、反力相对L2最坏≤1%（1e-8floor），且完整在线wall至少比直接FEM和经典外推两者更快10%。这些是本新方法预先选择的实用目标，不是旧实验标准替换或统计置信界。单条匹配轨迹/1seed的结果只支持本合成家族探索，不声称可重复性或材料/几何泛化。质量与反力/历史任一回退不得仅凭raw或loss好看判成功。

## 预算与实际计费

沿用v2总上限：3600数值子步，单worker≤16cores；CPU最多136墙钟/2176核小时；单GPU训练≤8h、完整混合推理/数值校正阶段占卡≤4h，共≤12GPUh；RAM64GiB、VRAM24GiB；主目录128GiB+archive128GiB，启动需data2至少256GiB可用。replay+共同分析预算≤4CPUh；GPU主机CPU也计入总host上限，不另开并行CPU池。

2026-10-19 12:41UTC只读容量快照：GPUServer8，64逻辑CPU、available RAM约380GiB；data2约615GiB可用、data3约939GiB。GPU5 UUID5622bd47...当时仅4MiB/0%；这些不是未来预留，GPU阶段前重新核查，若占用即停止且只管理自身子进程。实际运行时NumPy1.24.4/SciPy1.15.3/Torch2.7.0+cu126/h5py3.13/psutil7；缺失OSQP1.0.4将安装到本Run专属deps，不改共享环境。

已测实际成本目前只有Mac纯原生回放2.808秒及输入资产大小；新标签生产、训练与在线校正尚无实测值，不能将预算上限当耗时预测。执行后cost_ledger记录每阶段wall/实际CPU秒/占卡秒/采样RAM与VRAM，events记录每步机械装配/因子次数、QP次数、history/fresh audit、feature/NN/传输及IO。失败/kill也入账。CF/CC/CH统一包含worker启动、setup、物理校正、保存和fallback，评分单列；离线标签与训练为C0，CH<CF才报N>C0/(CF−CH)，冷启动总成本另列。

## 运行与恢复

唯一Run ID `pf_hybrid_full_20261019_r1`；code/inputs/deps/tmp/cache/log在`/mnt/data2/drtao/wennie/<RunID>`，原始接受态/标签/模型在`/mnt/data2/drtao/pidl_archives/<RunID>`。源包仅来自本Mac冻结commit及source manifest，远端禁止改核。精确执行CLI、输入hash和card source manifest与独立producer复审一起交付。

外层supervisor独立于worker，检查物理子步/phase/总wall、RAM、存储、GPU身份/占用；仅终止自己创建且PGID核对的worker group。SSH掉线不视作停止；detached launch并保存PID/命令/log。原子CAS保存接受态，写入后未知结果/崩溃锁由inspect_hybrid_run.py只读核实，禁止盲重试/自动删锁/重复提交。任何工作不能因Mac工具超时而重复启动。

旧设计、开发复审、结果与预算v1/v2保留。本次producer review需绑定新core接受增强、inputs adapter、worker、supervisor、执行卡、原生回放与依赖合同；通过前没有科学任务启动。

## 精确启动与只读恢复

最终source manifest包含detached launcher、完整worker及依赖、卡片和测试；独立复审回执绑定artifact_id与card SHA。远端code来自冻结Mac commit的字节包，安装仅本Run依赖OSQP1.0.4。先执行同包`run_hybrid_producer.py --check`及纯算子回放并记录Linux身份；不得将Mac回放冒充Linux验收。

从producer的code目录，用本Run deps/source/tools组成PYTHONPATH，唯一启动命令为`python3 tools/launch_hybrid_detached.py --card docs/research/S04/hybrid_constrained_design_20261019/execution_card_v2.json --package ../producer_source_manifest.json --inputs ../inputs --review ../producer_review.json`。launcher在spawn之前独占创建launch_reservation.json，任何未知结果都先读reservation、PID/cmdline、launch/terminal/cost receipts，绝不再次执行该命令。Linux worker在数值模块导入前安装parent-death信号，supervisor异常退出时不遗留计算worker。

恢复只读命令为`python3 tools/inspect_hybrid_run.py --archive /mnt/data2/drtao/pidl_archives/pf_hybrid_full_20261019_r1`。日志截断仅承认完整有效前缀，明确标出坏行及reconciliation_needed；损坏store单独列错，不掩盖其他phase。没有自动解锁、续算或重新提交入口。

Python兼容修复阶段的静态复审源为e4f5215e、artifact e96e3c0e，见producer_review_v3；下述跨平台修复形成当前43af56d4/manifest_v4/card_v2新包，另用producer_review_v4，不将旧收据用于新包。Linux实际Python3.10.12已通过全部依赖导入/源包校验，OSQP仅本Run deps，实际worker-prefix父进程死亡保护测试通过。phase墙钟上限与replay+analysis合计4h相加为116h；136h仍为含监督开销的全作业独立总上限，2176coreh为16核占用保守上界，均非预测。初始Mac回放2.808秒为已测成本；正式全输入Linux回放/数值标签/训练/在线成本以各阶段真实收据更新。

## 跨平台身份修复（实机发现，保留旧回执）

首轮Linux源包导入通过后，严格state/backend身份拒绝执行。逐项SHA定位：points/cells/N/DOF/assembly/physics完全相同，只有LAPACK派生B/det不同，Mac旧mesh be91...、Linux旧5053...。没有放宽逐字节身份或仅编辑预期hash绕过；新增hybrid-only固定float64运算次序、显式2×2逆/行列式的Q4 kernel，原PIDL/native函数不改。新backend仍逐字节重建B/det并将完整系数纳入mesh hash。

canonicalize_hybrid_inputs.py先核对全部旧输入字节，u/d/A/r/f/opaque逐字节保持，仅用新确定性几何显式重绑定派生mesh/state身份；原inputs/state/meshID保留于新manifest。mesh及五态NPZ原字节复用，不投影、不生产标签。当前卡v2绑定inputs SHA51776e2e...；新mesh f5c36127...、state0 fdedddad...。本变更使平台间同一严格身份可复现，不降低任何数值容差。Mac新五态回放5/5通过原1e-10，最大raw/history1.584e-12、Ru1.753e-16、Rd5.205e-18，纯后处理2.530秒，46项人工/kernel检查通过。科学运行仍需新精确复审和Linux全输入/回放准入。

当前唯一执行版本：source43af56d4，manifest_v4 artifact6b0ef3bf36ffbedf3c33170b2f641c06873684276a18be3f6726537e4d7c4585；card_v2 SHA da119752c2ee81443dcee43b31cbe1fe2942ae70b39acf115dc1712005d8a125。producer_review_v4独立复审通过，29文件核验/46项测试及人工身份迁移检查通过。Linux初始严格身份已完全一致；最终全资产、--check、五态回放另由实际执行收据确认。

输入分片首批实际传输917.624秒（仅该批网络阶段，不含此前断连、准备/复审或后续补齐），171数据分片中1个需按远端hash证实损坏后补齐；另一客户端超时片已实际完整，不重传。传输不计GPU数值工作；仍单独列准备开销，不冒充标签/训练时间。

正式启动已核验：pf_hybrid_full_20261019_r1，监督PID1054983，原生回放阶段8.29667墙钟秒/9.82828实际CPU秒通过后进入train_A。完整Linux预启动回放8.21175秒5/5通过，source/input/state/运行时/实时容量准入通过。执行回执producer_delivery_v4.json记录实时快照与确切身份；后续成本以远端cost_ledger/terminal为准。启动不是数值收敛或改善结论。

启动后首个实际接受子步：train_A/c1s1，总墙钟56.952秒，求解55.184秒、2outer；fresh Ru_L2=2.202e-15、KKT_Linf=1.480e-8、KKT_L2=1.480e-7、界违例0、fatigue residual0，接受态/特征/来源hash已持久保存，f_min1。这里展示实现真实接受和单步成本，不等于已形成完整训练集或证实场改善。三个机械块各约15.3–15.5秒，是首步主要成本；它还不能给出整轨迹预测。尤其混合阶段固定4小时/600步能否完成仍需实际检验，预算到限即停，不增加占卡或自动重跑。
