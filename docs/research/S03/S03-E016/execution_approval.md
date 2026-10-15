# E016 三次静态求解执行审批 — v1

2026-10-15。本文件仅供审批；文件尚未发送，未连接Taobo，未启动求解。

## 账号、目标和发送内容

发送端：Wennie的本机工作区（macOS用户wenxiaofang）。
接收端：Taobo的共享账号drtao，经本机SSH别名gpu-taobo，目标172.16.100.2:22，
要求实际主机名GPUServer8。不是haofan/Pro审查会话，不向ChatGPT、邮件或GitHub发送。

仅拟发送一个已生成的本地压缩包：
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E016/execution_approval_v1/S03-E016-R002_fit_only_v1.tar.gz

大小2445698bytes；SHA256：
7d1bb9248788260eefcf3c77e55ce497d02b03ce2c4abd5db535e60a4ddda9e6

接收及工作目录拟为：/mnt/data2/drtao/wennie/S03-E016-R002/
该目录目前是否存在、当前环境/资源是否可用尚未远程检查。若已有该目录，停止报告，
不覆盖、不清理，也不自行换RunID。压缩包先在此目录核对身份，再解出以下11个文件：

```text
code/scripts/aa2024_geometry_prior.py
code/scripts/aa2024_boundary_basis.py
code/scripts/aa2024_triplet_structure.py
code/scripts/aa2024_patch_mechanics.py
code/scripts/aa2024_rigid_observable.py
prepare/preparation.json
prepare/prepared.npz
prepare/geometry_audit.json
prepare/training_geometry.npz
prepare/execution_receipt.json
transfer_manifest.json
```

transfer_manifest.json列出10项代码/数据文件的大小与SHA256、来源版本、目标、三臂、
q=0、单线程配置、600秒整组预算、禁止自动重试。整个包的SHA256同时绑定该清单本身。
本地已检查精确成员白名单、逐文件身份、无符号链接，以及完整准备回执与runner/依赖绑定。
未打包原ZIP、stage15响应数组/成员、其他实验、审查聊天、图片或验证输入。
prepare元数据含此前允许的stage15标识/力值/字节摘要；不含其响应值。

## 代码和已验收输入

来源提交d0c2bbee1ccf0072e7e776bde6fdf8faa788a0fc，打包前工作树clean。
数值代码独立复审绑定35fd968b8393cbea50125025d1b2daf044b6456c；
二者数值runner和四依赖字节完全相同，之后仅有图器/记录变化。
本次不修改数值代码，不需要推送整个仓库；采用绑定Mac提交的最小文件快照。

Runner SHA256：0bb5c1c0689bca78021ba6cfbe0ed8979141bca665eabf68e7790f82da363fe5
R001准备回执SHA256：8655d49b30e341d488eeb8c15db9a7d347f236634a22adbbf39fcb7b4bbd3ccf
prepared.npz SHA256：d62c4648d029fff636984f214cb8673539cf56de195f4bc31fc5b278c3b0144b

cycle292018.5，stage13/14训练资产已独立验收：861节点、1600CST、120边界节点，
648共同评分点，权重面积和426.022805635mm²；主带106查询均有支持。
旧先验水平线段[-9,6]mm，新先验[-8.286708688,6.921424233]mm。
二者弥散宽度1.5mm，E=1、nu=0.30，qR=qL=0；第三臂完好。
几何、BC、权重和支撑不重算、不换主带、不搜索参数。
完整验收及局限见training_assets.md；1.8mm辅助带病态、2.7mm源增量不一致、
W位移不小都保留，不解释为已经恢复真实裂尖或验证了二维模型。

## 审批后的操作范围

本次若获批准，仅允许以下操作：

1. 对同一Taobo目标做只读预检：账号/主机名，df -h / /mnt/data2 /mnt/data3，
   CPU/内存/现有进程负载、Python及NumPy/SciPy/线程池环境。不修改其他用户作业。
2. 确认目标目录未存在后，创建专属R002目录，传输上述唯一包；核对压缩包身份和成员，
   解包后再次核对清单及完整准备回执。创建本Run的logs/tmp/.jitcache/cache/archive目录。
3. 仅启动下述一次fit，记录PID、主机、起始时间、命令和环境，单线程CPU、不占GPU。
4. 只读监测该Run；结束后取回完整fit目录、日志和环境记录，核对回执及全部产物，
   保存至本机local_archive/experiments/S03-E016/S03-E016-R002/。不自动进入validate。

环境拟采用此前Taobo运行的/usr/bin/python3，要求Python3.10.12、NumPy1.24.4、
SciPy1.15.3；这些仅为已知基准，当前版本尚未确认。预检若不一致或依赖不可用则报告，
不安装、不升级、不替换解释器。使用threadpoolctl读取实际已加载线程池，确认均为1线程；
该检查必须在import numpy和scipy.sparse.linalg之后进行，不能只看环境变量。
若threadpoolctl不可用、线程数不为1、资源有冲突或/mnt/data2不可用，停止启动。
单线程不表示独占整颗CPU；不申请GPU，不改变共享机器配置。

### 单线程CPU启动命令（仅预检和审批后运行）

```bash
cd /mnt/data2/drtao/wennie/S03-E016-R002 || exit 1
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/mnt/data2/drtao/wennie/S03-E016-R002/tmp
export JIT_CACHE_DIR=/mnt/data2/drtao/wennie/S03-E016-R002/.jitcache
export XDG_CACHE_HOME=/mnt/data2/drtao/wennie/S03-E016-R002/cache
export PIDL_ARCHIVE_DIR=/mnt/data2/drtao/wennie/S03-E016-R002/archive
nohup /usr/bin/python3 -u code/scripts/aa2024_geometry_prior.py fit \
  --input /mnt/data2/drtao/wennie/S03-E016-R002/prepare \
  --output /mnt/data2/drtao/wennie/S03-E016-R002/fit \
  --source-commit d0c2bbee1ccf0072e7e776bde6fdf8faa788a0fc \
  --run-id S03-E016-R002 \
  > /mnt/data2/drtao/wennie/S03-E016-R002/logs/fit.log 2>&1 < /dev/null &
```

启动前须确认cwd正确且fit尚不存在。执行时记录后台PID；此命令不含验证、调参或重试。
线程变量同时适用于环境预检。不使用timeout强制杀进程，不使用pkill，不触碰其他会话。

## 600秒预算、停止规则与输出

- 按old、proxy、intact顺序各求解一次，最多三次；secant由观测训练增量线性计算，无第四次求解。
- 600秒是整个fit的软完成预算，含三解、采样、保存、哈希；不包含审批、网络传输和环境预检。
  每次解前/后、保存后、最终哈希之后且成功回执之前检查。运行中的解可以结束；
  一旦观察到耗时>=600秒，整组不接纳，不能从完成的前缀挑选结果。
- 非有限alpha/解/采样/预测，残差>1e-8，准备回执/来源/文件身份不符，或输出目录冲突，
  都停止。保留失败回执和已有文件用于查因，不作部分科学比较，不自动重试。
- 若连接断开或无完整成功回执，状态为未知/未完成；先核对实际PID和回执，绝不盲目再启动。
  对长时间未返回的在途求解也不自动杀进程或重启，先报告。
- 成功应保留solved_fields.npz（三组完整场/采样/先验）、frozen_predictions.npz
  （old/proxy/intact/secant四预测）、fit.json及execution_receipt.json。
- 仅在三解均完成、预测有限、产物及成功回执完整且预算合格时，称为“完成预测冻结”。
  这不是留出验证，也不是损伤相场或材料参数恢复。

stage15响应仍留在本机原始归档中，不传输、不转换、不评分。本次审批即使通过，
也不包含stage15验证；待取回核验冻结结果，再单独申请该步骤。
不发送任何额外邮件、审查消息或文件；若包内容、目标、账号、命令或承诺改变，重新展示审批。

## 本次需要你批准的事项

是否批准将上述SHA256的唯一包发送至指定drtao/GPUServer8新R002目录，
在上述只读预检满足后，按原命令仅运行一次三臂q=0静态fit并取回冻结结果？
未获得该次明确批准前，继续保持本地准备状态。
