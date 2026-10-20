# PIDL c20：5a01757e实际准入停止（2026-10-20）

目的：按用户本轮明确授权，执行300秒真实首检，通过后直接进入原3000秒预算内完整比较；保持实际Phi、FEM damage、原UV及1e-10。

本轮：精确原包manifest `ec63104508dd741623ce337cf3a45094b12e43bcf23680bff940aa76d8eccbe9`及原29项人工检查证据保留。执行前本地原包静态检查通过；一次SSH只读检查耗时7.71545秒，确认GPUServer8/drtao及GPU5 UUID匹配，无selected-GPU计算进程、无重复wrapper、无原run/archive目录或远端family claim。新科学worker没有启动，没有上传/权重或数组读取/CUDA首检/优化/FEM/history更新。

| 2026-10-20同一次真实只读快照 | 数值 | 含义 |
|---|---:|---|
| GPU5物理总显存 |24564MiB =23.9883GiB|RTX4090硬件上限|
| GPU5当时空闲显存 |24077MiB =23.5127GiB|无selected compute进程，utilization0%|
| 5a01757e包要求的初始空闲 |28672MiB =28GiB|超过物理总容量，不可能通过|
| 新worker/真实首检/accepted hidden更新 |0/0/0|没有新数值性能结果|

结论：`STOPPED_NO_RETRY_GPU_ADMISSION_CONFIGURATION_ERROR`。这是准备方写入的显存条件错误，非PIDL方法/AD/Phi失败，也非Taobo未启动或GPU被占；不能把未运行当作负向科学结果。原3000秒科学计算预算消耗0，SSH耗时另记；本轮停止不自动释放为重试授权。远端family claim未消耗，但本地尝试已终止，不能据此自重试。

## 来源纠正与可审阅修订

[原复用记录](profiled_hidden_execution_20261020/reuse_receipt.json)曾把28GiB误归为旧producer准入；核对本地原tight-coupling execute.py43–44/102–103行，真实旧阈值是12288MiB。旧probe_pass.json记录peak_allocated5375645696bytes/free16065953792bytes，支持旧图可行，不证明本次新二阶AD图资源可行。旧原始文件和5a01757e包均不修改；这里追加勘误。

[关闭显存修订v2](profiled_hidden_execution_20261020/admission_revision_v2/README.md)只恢复12GiB初始准入、先核硬件total、在新真实300秒首检后要求≥3GiB自由显存，并显式绑定旧停止的授权。数学核心、源Phi/FEMd/UV/1e-10、工作量/时限和原资源上限不变。原上限大于物理卡容量不是可用性承诺，OOM/新图不合格仍首停。代码、人工边界测试及关闭卡已本地准备；独立差量审查/最终包hash见修订目录及本地build receipt。没有启动修订版。

证据：[紧凑停止收据](profiled_hidden_execution_20261020/admission_stop_receipt.json)，[最初修订提案](profiled_hidden_execution_20261020/admission_correction_proposal.json)，[本地完整记录](/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs/pf_s04e011_profiled_hidden_c20_r1_20261020/execution_receipt.json)。原方向回放结论不变；没有新的FEM/PIDL场比较图可报告。
