# E019-D03-U01 B002 — 最终执行包 v1（待用户批准）

2026-10-18，Europe/London。本轮仅准备和源码/文档/路径元数据核对，未执行。
本包替代旧 underflow_execution_package.md 中的 B002 草案命令；旧文档和
A001/B001 失败均保留。批准范围拟为下述命令一次，不自动进入验收或 C/D。

## 目的与已有依据

最小问题：A002 已验证的参考算术与 Q 一致实现，能否在同尺寸纯人工输入上，
按原判据完成一次 SVD、两次薄 QR、数值证书及出图，并通过 60 秒软完成检查？
这只检查人工资源可行性，不确定真实 B001 根因，不证明真实 DIC 或相场反演。

- A002：65/65（41 新用例+24 原 stub 回归），exit0，零实际 QR/SVD，
  无非预期异常或重试；见 underflow_a002_results.md。小测试耗时不能外推本包。
- 原实现独立静态代码审查：underflow_code_review.md，clean d478b2d5；
  后续三个人工 fixture 修正焦点复审：underflow_fixture_revision.md，
  clean 2b425376。A001 暴露的静态审查遗漏保留，不改写历史结论。
- 代码基线：`ab6f123a0174c7009b5427c0db0b98901ca1e2d3`。
  本轮准备起点 HEAD：`77385406352f18714632aea9e7aa2370e78d7d0f`，clean；
  基线之后仅 docs 改动。A002 运行 HEAD 为 c024bfac309f460a700467d349c2853ab4b525b0。
  本轮不改源码、不重复已通过的测试或未变算法审查。

五源码 SHA256 与 A002 记录逐项一致：

| scripts/ 下的文件 | SHA256 |
|---|---|
| aa2024_q_recheck.py | 0a7ebbd60d778b8e0cf2171891b68ab928ff73e0092c244f7958174ac9d49acd |
| aa2024_q_verify.py | 90755956092e16cb84c0ebedd9907c21a79ea523d1819dc8fb657ec10ae7d873 |
| test_aa2024_q_recheck.py | a5b7fc3c1e97132c45df5118d06015baff3a3caf101e66a22137d941f014cedf |
| aa2024_dyadic_reference.py | a492c822d7e06d82ff0c43306b7fdb004e2cb5b987b28bb5fd1646bcb8fd1c36 |
| test_aa2024_underflow.py | faec84e6e98c2063f9010e97028eebee52a8c782684640ed0c7e0b1bc124b87f |

## 唯一拟执行命令

工作目录固定为：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/aa2024_q_recheck.py synthetic --source-commit ab6f123a0174c7009b5427c0db0b98901ca1e2d3 --output /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B002
```

单线程 CPU，CUDA 空；只启动一次 producer，不附带 verifier、测试或第二命令。
不使用 `--allow-two-opaque-hashes`，不切换 real 模式。C/D 不在本执行包中。

## 人工资产与读写范围

- 由源码生成 41×21 网格：861 节点、1600 三角形、120 边界节点，
  741 内部节点/1482 自由位移分量；648 个规则内部人工点/1296 观测分量。
  A 为 1296×1482。人工权重为 1，边界值为 0，观测与三臂场为源码正弦/余弦。
- old/proxy/intact 仅人工臂标签，不读取同名真实冻结预测；人工 rank 不强制
  等于真实方案的 1203。不改变真实 stage13/14 的 648 点、权重或资产。
- 允许读取源码、Git 身份及依赖运行所需的标准库/配置/字体；只在新 B002
  下保存本次人工结果、图和隔离的 `.mplconfig`、`.cache`。
  旧 B001、真实 NPZ/report、训练数组、stage15 响应和其他留出均不读取。
- 不导入旧 producer、不组装刚度或 FEM 求解、不拟合 q、不训练或调参。
  仅一次固定 gesvd SVD、两次 economic 无 pivot QR；计数是受控 API 记录，
  不包装成全进程追踪。失败时可能尚未完成全部三次分解，保留实际计数。

## 原数值判据与停止规则

rtol=1e-12；matrix atol=1e-12、vector atol=1e-15 mm、square atol=1e-18 mm²。
保留五个固定列缩放参考调用点及原派发、全分量比较和首失败见证，不扩大到
一般乘法；不改变 L/s/A/H/U/p/r、操作数或容差来救结果。
保留 tau=1e-12*smax、s>tau、[tau/10,10*tau] 谱带首停与 eta<=0.5 硬界。
保留 binary64/舍入模型、有限性、双侧奇异对、Q/Gram/QR、候选子空间和
平方账本检查；不要求 legacy 必须失败，不将 legacy 通过当修复因果证据。

`-W error`、logging WARNING 首停与 `np.errstate(all='raise')` 不变。
本包没有字体缓存初始化日志豁免；历史 D02 的单次例外不继承。
首个非预期异常、警告、模型不支持、数值判据失败、身份/路径变化或预算超时
立即判本次未完成并停止；不自动重试、换目录续跑、改线程、扩时或调参。
不得把局部通过或部分文件当作完整证书。失败记录定位到阶段/检查/计数，
不由资源阻断直接否定真实 DIC 反演路线。

## 60 秒预算的确切口径

本源码的 Budget 在导入、参数/线程检查、初始 Git/源码身份、路径检查、
新目录创建及初始收据元数据之后开始；从 check_model 前计时。
涵盖人工资产生成、算子构造、1 SVD/2 QR、原数值检查与参考证书、NPZ/JSON、
绘图及 sidecar、产物哈希、末次身份核对、执行收据和 completion 写入后检查。
检查值 >=60 秒即 TimeoutError，整次不接纳。初始导入/元数据、最终 stdout
及异常后的取证写盘不属于该计时区间，另记录进程外工具 wall，不能混称。

这是软完成预算，不是 60 秒硬杀进程：正在进行的 SVD/QR/BLAS/绘图不能由
检查点中断，返回后的下一检查若超时即失败；实际进程时长可能超过 60 秒。
不因软超时接受已出图结果，也不自动增加预算。当前没有 B002 耗时实测。

## 预期产物与完成边界

仅新目录 `S03-E019-D03-B002`：

- certificate.npz、report.json（schema E019-D03-U01-v1）；
- q_residuals.png/pdf/md：U/V 两行×Q retained、old、proxy、intact 四列，
  同一人工坐标、全 648 点、统一对称色标；D^-1 仅显示，不改数值权重；
- q_square_ledger.png/pdf/md：三臂 J_Q+gap² 与原 J_k，单位 mm²，不加 RMS；
- execution_receipt.json（源码/版本/主机/PID/命令/耗时/分解计数/八产物哈希）
  和 completion.json（收据哈希）；另有新目录中的绘图缓存。

原图器标题中的 stages13/14 是沿用任务上下文，synthetic 模式必须与标题
一起解读：全部数据人工生成，不代表已读取真实训练场。
这轮按实验门控限制信息集，按图形规范绑定同目录证书/说明与共享色标，
不在准备阶段生成或查看图。未来图形出现并不等于独立图形验收通过。

成功仅表示命令 exit0、末次预算与身份检查完成、受控计数 1 SVD/2 QR，
匹配的完整执行收据/完成标记且无失败收据；状态仍为
`producer_completed_not_independently_accepted`。独立算术/图形验收另议，
不隐含启动 verifier 的额外算术成本或新权限。
失败只保留本次 failure_receipt.json 和可能的局部取证文件；若已写 completion
则源码只撤掉本次无效标记，不删除旧文件。初始化早于 try 的失败可能没有
失败收据，此时原终端输出也是失败依据，不因缺收据重试。

## 本轮预检与审批后检查

本轮只读 stat：B002 路径不存在（含 symlink 检查），既有祖先均目录且
无 symlink；未新建目录、未列读旧数值内容。所在卷 df 可用约 494 GiB，
只是本轮快照，不是内存/峰值资源可行性认证。
普通 Codex 窗口 used16%/remaining84%，未触发既定 80% 停止线。

获批后启动前重新核对 clean Git、基线祖先/后继仅 docs、五 SHA、目录新鲜、
无 symlink、磁盘可用状态和普通额度；任一异常先停止报告，不执行或改命令。
运行前后 HEAD/源码身份一致，保存完整终端/exit/工具 wall；只做本次运行
完整性核对，不借此读真实数组或开启独立数值验收。批准不继承到任何重试。

本轮尚未启动 Python/测试/QR/SVD、出图、B002、C/D 或真实/留出读取；
仅新增本包与轻量方案索引。待用户对以上确切命令及软预算口径批准。
