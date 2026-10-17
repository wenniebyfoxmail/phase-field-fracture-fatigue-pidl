# E024 v1 三态生产传输与启动审批版本

状态：仅本地准备，未SSH、传输或启动。发起：Mac用户wenxiaofang；对象：drtao@172.16.100.2 / GPUServer8，现有Tunnelblick client通道。SSH统一`-F /dev/null -o BatchMode=yes -o ConnectTimeout=15`。

仅发送以下两个文件原样至新目录`/mnt/data2/drtao/wennie/S04-E024-head-tail-231fe4b-20261017-v1`。科学源码精确`231fe4be83e26ef4054a2a6a567da51229185837`，已获独立Code Ready；部署脚本单独审查，不能修改该科学checkout。包基于现有E023 `c4ceb5d27fa8d408be1b9f02dcd6b10308f301a2`增量重建；没有Mac D、原始数据或checkpoint外传。

| 文件 | 字节 | SHA256 |
|---|---:|---|
| E024_231fe4b.bundle | 138885 | `a4e108f4034779801949a69a7e4fe9be6383b5e51773a8d1a5b0a76671fad6ee` |
| prepare_and_dispatch.sh | 21011 | `6a35eb158194b1ebed43ebb2950a1baafa6527dddc5069e5dd8ed653a9bddb13` |

本地路径：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/producer_submission_v1`。三态生产使用自己的新运行目录和独立归档`/mnt/data2/drtao/pidl_archives/<run_id>/`，不复用历史目录。批准后先查远端状态；存在目标或结果未知则停止查证，不盲目重发/重复启动。

## 最终传输与单次启动命令（尚未执行）

```bash
ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=15 drtao@172.16.100.2 'umask 077
[ "$(id -un)" = drtao ] || exit 1
[ "$(hostname)" = GPUServer8 ] || exit 1
mountpoint -q /mnt/data2 || exit 1
mkdir /mnt/data2/drtao/wennie/S04-E024-head-tail-231fe4b-20261017-v1'

scp -F /dev/null -o BatchMode=yes -o ConnectTimeout=15 /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/producer_submission_v1/E024_231fe4b.bundle /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E024/producer_submission_v1/prepare_and_dispatch.sh drtao@172.16.100.2:/mnt/data2/drtao/wennie/S04-E024-head-tail-231fe4b-20261017-v1/

ssh -F /dev/null -o BatchMode=yes -o ConnectTimeout=15 drtao@172.16.100.2 'cd /mnt/data2/drtao/wennie/S04-E024-head-tail-231fe4b-20261017-v1 || exit 1
[ "$(sha256sum E024_231fe4b.bundle | cut -d " " -f 1)" = a4e108f4034779801949a69a7e4fe9be6383b5e51773a8d1a5b0a76671fad6ee ] || exit 1
[ "$(sha256sum prepare_and_dispatch.sh | cut -d " " -f 1)" = 6a35eb158194b1ebed43ebb2950a1baafa6527dddc5069e5dd8ed653a9bddb13 ] || exit 1
mkdir -p logs || exit 1
nohup bash /mnt/data2/drtao/wennie/S04-E024-head-tail-231fe4b-20261017-v1/prepare_and_dispatch.sh > /mnt/data2/drtao/wennie/S04-E024-head-tail-231fe4b-20261017-v1/logs/dispatcher.log 2>&1 < /dev/null &
printf '"'"'dispatcher_pid=%s\n'"'"' "$!"'
```

单次nohup先执行全部准备/预检，只有三个状态预检全部通过后才进入第一行训练。记录PID后独立核对实际cwd、commit、状态和日志。SSH掉线仅表示可见性丢失，不表示任务停止。

## 资源、身份与预检

GPU0允许共享，仅初始及每行前空闲显存严格>8192MiB；mounted `/mnt/data2`空闲严格>8GiB。保留GPU UUID、占用/进程/磁盘记录，UUID改变、查询失败或空间不足即停；这不是资源预留。不杀其它进程、不换GPU、不等待重排、不安装环境、不改全局配置。

从旧远端只读复制120份文件（3参考、15backbone、15E019、27E021、27E022、33E023），拒绝symlink/已用目标，核对复制前后字节摘要。克隆旧E023提交对象、验证bundle、detach `231fe4be83e26ef4054a2a6a567da51229185837`且git干净。正式Torch/NumPy/CUDA/GPU/hostname/CUBLAS须与原三态记录一致，保持原严格尺度和门槛，Mac可移植性例外不得当作预检通过。

训练前一次性完成三态native10000LR、FEM参考/自身backbone、E019/E021/E022/E023身份、坐标map、BC/物理窗口、leak及零输出/CUDA缓存核对。fresh初始CPUfloat64/two-thread/1024chunk全质量RMS D和梯度审计须与自身原E023文件逐字节相等；不上传Mac D。每行前重新算D/梯度与sampler前8000/全10000摘要并复核正式文件，不能跳过。

## 三状态与实际更新

串行c20s4早期、c60s4中期、c83s4转变期；各自配对同状态E023，E022/E021/E019只作历史比较，不重训、不拼赢家。完整run IDs/argv见production_plan.json。全部localized、alpha=.7、seed7，从原E017backbone加共同零输出初始化开始，不resume E023终态；history/fatigue/damage/backbone/目标/map/窗口/BC/D/leak冻结。

每态新增10000更新：1..8000联合；8001..10000隐藏与activation.coeff冻结，只更新output_layer.weight/bias。使用同一AdamW/参数组/原输出头动量，隐藏grad必须None，后2000无隐藏梯度或decoupled decay。最终head步数10000、hidden8000。没有额外头部拟合或第10001步。

原生CosineAnnealingLR(T_max=10000,eta_min=.00001)，optimizer前读实际LR、optimizer后scheduler.step：第1次`.001`，第8000次`0.00010462801334558331`，第8001次`0.00010453658778440045`，末次`1.0000024427270673e-05`，post-final才`.00001`。完整actual向量必须与自身E023/E022/E021和正式native预检一致；阶段转换不重置LR。

## 阶段收据、输出与停止

PRE_UPDATE.json只记录update1前并保持不变；完成8000后在8001前保存step_8000.pt（真实model、optimizer、参数名与计数）和HEAD_ONLY_STAGE_ENTRY.json（原PRE_UPDATE/快照/D/gradient/source/state/run摘要、冻结前后摘要、sampler前8000摘要、8000实际与8001将用LR、时间）。最终CP包含真实optimizer状态和阶段引用。严格冻结源码解码独立核对8000→10000隐藏权重/动量精确不变、头计数8000→10000及全部mask/身份/采样/LR；核对前0..8000轨迹与自身E023。每态13份输出+13份真实producer归档副本，三态39份；每行有效并归档核验后才进入下一行。

任一源码、runtime、身份、D、采样、LR、阶段/计数/冻结、finite、BC、支持外或归档错误立即停止并保留日志，不自动修复、重试、加预算、换seed/GPU或改切点。完整三态及冻结汇总器的48项区域比较有效才记执行完成；缺失INCONCLUSIVE、完整性错误INADMISSIBLE。

后续比较每态全场/损伤/背景/窗口内背景相对自身E023及E022/E021/E019，同时报告冻结backbone、窗口外不变和计算成本。`.001`仅历史诊断，不作为本轮路线淘汰线；背景接受预算、应用容差与route_acceptance未定义。UV拟合不证明损伤/裂纹/疲劳可用，需要另行耦合与历史验证。不自动启动下一实验。

## 本次请求审批的动作

批准这两个固定文件、上述新目录、GPU0共享且空闲>8GiB政策，以及所有预检通过后单次串行启动这三行。此次授权不包含自动重试、GPU替换、源代码修改或新实验。
