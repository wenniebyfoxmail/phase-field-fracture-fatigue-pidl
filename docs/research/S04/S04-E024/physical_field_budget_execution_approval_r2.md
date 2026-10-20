# D013 生产机角色修订审批卡 r2 — 静态提案，暂不可批准启动

2026-10-20；接总部的机器角色核查委派，仅查本地记录。**没有SSH、资源探针、真实预检、solve、train或真实Torch操作。委派不是执行批准。** 本卡集中给出完整拟运行范围与缺项，避免再让人方单独回答“本地是哪台机器”。不重复科学设计或Code Ready审查。

## 发现及依据

v1不是代码上未指定机器：原审批卡第14行明确“当前Mac”；冻结execution_plan.json指定same local Mac；启动器第25–29行把PROJECT和解释器硬绑到Mac路径。故问题是**生产机角色与许可未说明充分**，不能把“CPU-only／不训练”自动等同于“允许在Mac运行这一科学比较批次”。

- [项目AGENTS.md第7–9行](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-sampling-multiscale-20261012/AGENTS.md)：Mac-PIDL is Dev only，lightweight import/unit；Taobo/CSD3/Windows为Producers。
- [Taobo协议第24–35行](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-sampling-multiscale-20261012/docs/taobo_gpu_submission_protocol.md)允许Mac非训练analysis/plotting，也把production cases放生产机。D013有12profiles／最多36次数值求解／真实场及完整重放，采用生产机路由以避免利用条文差异自行扩大Mac角色。这里不推断用户已经给出Mac生产计算例外。
- [E024既有部署记录](/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-sampling-multiscale-20261012/docs/research/S04/S04-E024/producer_execution.md)和本地launch_receipt.json给出`drtao@172.16.100.2 / GPUServer8`；[已回收baseline_preflight.json](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/producer_execution_v1/raw/baseline_preflight.json)第25–33行给出历史Torch2.7.0+cu126、NumPy1.24.4、hostname GPUServer8和**/usr/bin/python3**；logs/python_executable.txt第1行独立记录同一路径。它们是2026-10-17的历史证据，不是今天的服务器可达性／可用资源／依赖现状证明。
- 未改的18d0e7cb runner第136行`threadpool_limits(2)`；field_physics第183行`torch.set_num_threads(2)`，第189行要求CPU模型。CPU2是本次串行数值worker的计算库线程上限，**不是已经预留两个空闲核**。

## 完整拟执行范围（不因本卡获准）

|字段|唯一拟定值及权限边界|
|---|---|
|研究负责人／准备机|Winnie，CRSid xw436；Mac用户wenxiaofang，仅开发、静态包装与轻量人工检查|
|实际生产机／账号|Taobo，`drtao@172.16.100.2`，必须核对hostname `GPUServer8`；共享drtao不等于独占|
|生产解释器|**/usr/bin/python3**；依据既有回收记录；最终v2锁定其实际版本／依赖后才可申请启动，不偷换为PATH中的python3或Mac Conda|
|CPU／GPU|CPU2计算线程，三态与profiles串行；OMP/BLAS/Torch/threadpoolctl均2；CUDA_VISIBLE_DEVICES为空，0GPU，无GPU0显存占用或旧GPU训练授权继承|
|新生产根|`/mnt/data2/drtao/wennie/S04-E024-D013-CPU2-18d0e7cb-20261020-v2`；今天未创建／未远端检查，不能宣称不存在|
|科学源码|精确18d0e7cb1153dc969c1ee0c21c77ada1297b2d89；树14f6ba5d4b0107e0655f711622ef51268222221e18666f65426bc11e42813c23；科学文件零修改|
|三态／比较|c20s4→c60s4→c83s4，各自E023 joint10000 seed7；strict η=.1/.3/1＋中央旧七消融，共12比较；88文件身份沿用v1内容|
|保护／累计中心|原13实际保护、producer D／BC／窗口／features／damage／history／fatigue冻结；永久各自原E023累计Q和原误差尺度，不重置、不加slack、不改零分母处理|
|计算预算|仍1800秒数值＋900重放/汇总＋300累计非训练/预检＋120绘图≤3120；原检查已记账71.937549秒，换包装不清零；RSS每进程3GiB，legacy loader2GiB不改，归档合计1GiB|
|共享机与存储|挂载/mnt/data2；代码／缓存／日志／原始证据均在新生产根，不写home或根盘，不干预他人PID／GPU；线程限制不冒充已核验CPU可用性|
|首停／单次性|保留原profile首停与整体身份／非有限／映射／资源首停；原子一次性领取目录；未知状态先核验，SSH断开仅丢失可见性，不重试、换机、加预算或自动装环境|
|后续输出|完整已访问头/实际场重放，三态齐全才汇总；UV／应变／弱残差／瞬时driver收益、背景代价和成本分开；.001历史，history/裂纹/疲劳应用未获资格|

## 现有证据不足的确切缺项（一次收束，不追加零碎人方审批）

|缺项|现状／为何不能复用v1的通过|补齐后同一审批卡必须显示|
|---|---|---|
|生产启动包装|v1硬绑Darwin、Mac用户、Conda、所有本地路径，不能原样发Taobo；其PACKAGE_READY_PASS只覆盖原v1|仅部署层的Linux／GPUServer8／/usr/bin/python3启动器、target/argv、CPU线程与合并资源监督、一次性claim；只审部署差异，沿用未改科学Code Ready|
|解释器与依赖锁|只有2026-10-17历史/usr/bin/python3和Torch/NumPy记录；当前Python、SciPy、Matplotlib、psutil、threadpoolctl及具体CPU兼容性未知；Mac依赖锁不是Linux锁|最终静态依赖来源／版本要求、真实环境核验的明文动作及失败即停；未获准前不连接／import真实Torch，不能写“已经通过Linux数值准入”|
|输入／D012来源和地址|v1的88条路径是Mac local_archive布局；既有Taobo E019/E022/E023根有历史来源，但D012历史头和manifest不能假定已在Taobo|每份输入的唯一源／目标／bytes/SHA与复制方式；D012三态已保存比较头不重求；需要上传的准确payload清单和SHA，不能从旧E024120份资产批准继承|
|最终可发送包／授权|目前只有Mac v1 manifest，**没有Taobo v2最终artifact、manifest/hash或账号/动作批准**|一张最终卡同时给sender/recipient、精确文件及hash、全量命令、fresh根、资源／环境预检、单次条件启动、禁止项；哈希未齐前不向人方索要运行批准|

机器角色与历史解释器已从现有证据确定，无需再做一次“同意使用Taobo吗”的碎片确认。当前只允许继续本地补上述部署材料；待全部精确绑定后，合并成**一次**最终人方审批：是否向该账号发送所列版本、执行明文预检并条件单次运行。这里没有批准远端探针、数据传输、真实预检或科学计算。

## v1保留与来源差异

- v1完整zip：SHA `e6e11df3ef2e86676dcafa06a648a7d3a19e1253a07ee21781a7dffdcbdd91d1`；manifest `7c77c4db5448d64d8d9e3f647ce7210615df9506d276a7b86740d46ef866f91a`；source tar `4682bf96f178c4ca6dc9faf56a9f591cb687077e554240d77a997b818681d7b1`，均原样保留。
- 原v1审批原件与包状态收据另存machine_role_alignment/v1_original_*，保持逐字节；原v1批准模板仍false，没有生成授权文件。
- 科学Code Ready、18非训练启动器检查和FINAL_BINDING_PASS仍是原范围内的历史事实；它们没有审核Mac生产角色，也没有审核Linux包装或Taobo当前环境，不能改写为科学代码失败，也不能扩成Taobo READY。
- r2是**静态路由与审批卡修订，不是v2可执行包**；差异仅拟部署机／解释器／路径／来源／权限／部署核验。数值方案、三态配对、12比较、13保护、原预算和首停均不改。
- 当前状态：v1 `ON_HOLD_MACHINE_ROLE_ALIGNMENT`；r2 `STATIC_PRODUCER_ROUTE_SPECIFIED_NOT_RUN_READY`。不要运行原v1 Mac命令，也不要将原v1 manifest当Taobo新版批准对象。
