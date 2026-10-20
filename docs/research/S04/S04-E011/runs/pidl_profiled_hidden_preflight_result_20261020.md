# PIDL c20：5449d5a9真实首检的遥测竞态停止

目的：按用户对显存修订和旧首次停止的明确授权，执行冻结c20s4的300秒真实首检，通过后继续原3000秒完整比较。实际Phi、FEM damage、原UV、B0/约束Q4路线和1e-10保持不变。

本轮：精确5449d5a9包实际在Taobo GPUServer8/GPU5启动一次worker2909415。总链8.052633秒、controller7.431278秒后因storage sampler的临时JSON竞态停止；没有OOM，也没有进入candidate、局部见证或结果读数。旧5a01757e显存配置停止与本轮真实启动后的停止分开保留。

## 已完成什么，未完成什么

| 对象／环节 | 本轮证据 | 可以说明什么 |
|---|---|---|
| Taobo GPU5准入 |总24564MiB，初始空闲24077MiB，正确UUID、无外来计算进程|修订12GiB准入可达；不是完整新图容量证明|
| 原6份输入／权重／Phi／T |完整bytes/SHA验证，actualPhi复制SHA相同；初始SVD0|原源身份及实际Phi字节复用保留|
| 冻结FEM参考的共同原生算子回放 |自由位移残差L2=3.799534726e-15，force maxabs8.430857737e-17|这是FEM参考的算子一致性，不是PIDL求解残差|
| 实际PIDL首检早期 |energy/field与raw-feature的Guard计数各5（含保守记账）；CUDA活跃|真实模型/字段路径已运行，不是纯人工测试|
| 真reprofile导数／候选优化 |JVP/VJP/C/CT/K/head/SVD计数均0，accepted hidden0|首检未通过；无新预条件／场误差／容量结果|
| 早期资源峰值 |RSS1432457216bytes、allocated2085410304bytes、reserved2099249152bytes|仅停止前早期观测；不能外推到完整二阶图|

完整三次source读数、actualPhi移动图一致性／真reprofile FD及最终3GiB余量检查均未完成。没有新PIDL终点能量、Ru或active场误差可与A或FEM比较；原方向审计与此前FEM/PIDL场结果不变。

## 为何停止

worker遥测线程每次统计run/archive文件大小；controller以`write_json`写monitor.json：先写`monitor.json.2909412.tmp`，再`os.replace`为正式文件。`os.walk`捕获该临时名字之后、sampler调用stat之前，controller已完成替换，stat抛FileNotFound。旧sampler把这类正常竞态记成永久telemetry error；worker Guard与controller随后都读到错误，按原策略停止自己的worker。

两份guard的`incomplete authorised phase chain`是上面早停的后果，不是300秒超时，更不是数学导数检查失败。worker以SIGTERM退出(-15)，最后只读监测无任务自有live进程；没有杀其他进程，也没有修改远端原包或清理claim。没有发生候选步、FEM求解或历史提交。原3000秒不是供失败后自动重启使用的余额。

## 传输与执行身份

源5449d5a99884b48d404d0c7c3bb5a616c8afdada，branch codex/hard5-q4-t3-2x2-20261005，clean Mac snapshot；manifest SHA `df8189160deb20bffeec3ba225003de4b073a43cb3194578e43abb46becf0525`。worker命令、GPU UUID、PID、root、archive、日志及authority SHA见[receipt](pidl_profiled_hidden_preflight_result_20261020/receipt.json)。

第一次传输60秒超时后，只读核对确认根目录/archive/claim皆未创建、无producer，才继续同一字节包的传输；没有重复启动。按精确字节接收完成后，传输校验器因自身未禁bytecode而生成两份pyc，原包校验正确拒绝；在尚无worker/claim时仅移除这两份自有缓存，以`-B`再次校验全部原文件后才真正启动一次bootstrap2909400/worker2909415。所有传输/只读/清理命令与前后状态保存在本地，不改写原失败记录或包源码。

## 证据取回与局部修复

对远端373个payload/postexit条目、573190469bytes及完整覆盖已逐项bytes/SHA核验。实际网络取回compact213966bytes；其余37247050bytes从已有完全同SHA的本地原输入/已批准包复制，逐项重验。两个相同的267902656byte实际Phi文件留远端；因此**本地镜像明确不完整**，不能把远端hash通过写成full-local download完成。所有失败栈、终端、源身份、原生contract、Phi元数据和工作/峰值计数均已在本地核验。

[局部storage扫描修复](../profiled_hidden_execution_20261020/storage_scan_repair/README.md)仅对确认为`*.json.<十进制PID>.tmp`的、已原子替换消失文件允许继续；存在的临时文件仍计入存储。其他缺失payload、未知临时类型、符号链接和权限错误仍失败；目录遍历错误也显式抛出，不静默漏算。42项纯人工检查（原37+5个竞态/权限/计数边界）及独立差量审查见修复目录。没有对远端源码应用此修复或重新运行。

结论：当前预条件比较**不可判定**，绑定瓶颈是执行封装的文件扫描竞态，不能归因于PIDL参数化、方向方法、OOM或Phi/AD失败。局部修复可继续准备下一次真实验证，但当前已消耗的claim/原始证据保留；没有自动重启或用新RunID绕过首次停止。保持同一科学目标和原容差，下一执行需明确的新尝试/精确包及首停修订。
