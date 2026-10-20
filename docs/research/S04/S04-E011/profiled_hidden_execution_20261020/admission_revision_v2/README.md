# 显存准入修订 v2（关闭；未执行）

目的：修复5a01757e包的硬件准入配置错误，继续原c20 PIDL方向/预条件比较。原包、数学方法、科学输入/容差、主读数、工作上限及300/1800/600/300=3000秒预算保留。

本轮只本地准备。原授权单次只读SSH已到达GPUServer8，GPU5/UUID正确、无计算进程、无重复wrapper/根目录/family claim；但其总24564MiB和空闲24077MiB都小于旧准入28672MiB。原包在上传/真实模型/真实首检前停止，没有OOM或新模型结果。停止后没有重新连接服务器。

## 精确修订

- `launch.gpu_snapshot`同时记录物理total并拒绝非有限／越界读数；先确认所需显存不超过总容量。v2卡把初始空闲要求恢复为旧E011真实启动器的12288MiB；原卡和旧包仍是28GiB，不回写旧证据。
- 新图的真实300秒首检完成全部source/Phi/AD/reprofile检查后，再查CUDA free≥3GiB；不满足先保存free/total/required/判定，再首停，不进入candidate。累计峰值RSS/CUDA allocated/reserved/目录大小、外部guard和工作计数不变。
- 旧probe峰值allocated5375645696bytes只证明旧图曾可运行，不能证明新二阶图可运行。原24GiB allocated/26GiB reserved是预算上限，不代表这张约24GiB卡拥有该可用容量；真实OOM或新峰值/余量失败仍停止，不能借预算或切换GPU。
- 修订后authority必须同时绑定新包manifest SHA、旧停止包SHA和精确停止收据SHA。原conditional_full批准不能自动启动本版本。RunID/family保持原值；不是换ID绕过首次停止。
- builder增加显式、仓库内已跟踪的`--execution-card`选择，默认仍使用旧卡。新关闭包不包含启用的authority。

其余保持：同一实际Phi/初始权重、FEM c20s4条件damage、原UV边界、B0/约束Q4路线、1e-10、原候选/见证/对照和工作/时限/资源上限。没有新FEM/history/训练/holdout或实测预条件性能。

下一执行必须是对本修订包及旧首次停止的明确授权；本地构建/检查不会触发SSH。首检通过才允许原预算内完整比较。

资产：本目录关闭卡/独立差量审查；本地包`local_archive/experiments/S04-E011/pidl_profiled_hidden_execution_preparation_20261020_v2_admission`，精确代码commit/manifest SHA见其build_receipt.json。旧停止收据见上级目录admission_stop_receipt.json。

人工检查：37项mock测试（原29＋8项准入修订）通过；不启动child/GPU/真实图。独立精确差量审查见review.json。
