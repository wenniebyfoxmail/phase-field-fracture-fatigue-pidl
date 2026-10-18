# E019-D03-G01 B003 — 新同尺寸纯合成资源检查执行包 v1

2026-10-18（Europe/London）。本轮仅源码/文档/Git/hash和路径元数据检查、
独立只读静态审查；不运行Python、导入、AST、测试、QR/SVD或出图。
本文件不替代旧B002包或结果，旧产物继续隔离。只有用户批准本包唯一命令后
才可执行一次；不自动接入verifier、独立验收或C/D。

## 目的与已有依据

问题：G01已验证的停止保护与原65项回归兼容性，能否支持新的同尺寸人工
资源路径，在原数值判据及60秒软完成预算内完成1 SVD、2薄QR、证书和图？
结论仅为synthetic C0资源/工具可行性，非真实DIC数值复核或物理反演。
最便宜的前置证据已完成，不重复运行：

- G01-A001：26人工子进程及两类源码断言通过，代码基线ecb8b9a9；
  见thread_stop_test_results.md，不能据此宣称完整producer已通过。
- G01-R65-A001：clean runtime4486d51d，65/65，exit0，零实际QR/SVD；
  见thread_stop_regression_results.md。结果记录commit065a20ae。
- G01独立代码审查及焦点复审见thread_stop_code_review.md；数值与图器未变
  部分复用已有审查，不新增科学方案、判据或Pro提交。

## 必要的最小路径差异与身份

准备起点clean HEAD：`065a20ae1efa128b8141e3bdcf0789a69f32bb45`。
G01原基线：`ecb8b9a9238b035f9a87bf7d4a85deb2455b95e0`。
源码原来只允许synthetic写B002，不能直接换命令输出目录。为保留旧冻结结果，
新代码commit `87bc592d9c0828d0c698058702edca840e7e151d` **仅改两行字面量**：

| 文件/位置 | 变化 | 不变项 |
|---|---|---|
| producer main合成路径 | B002→B003 | real路径、fresh/无symlink检查、数值/图器/预算/G01 |
| verifier main合成路径 | B002→B003（未来acceptance目录同步） | 独立数值逻辑、外部退出声明、guard元数据要求 |

未来verifier未获执行许可；同步路径不触发任何验收。本轮不重测，新路径版本
没有新的动态65/65证据；已通过结果严格属于改路径前ecb8b9a9代码，不能改写。
两份原测试、参考算术、G01 guard及guard测试字节未变；只有producer/verifier
两个SHA改变。独立静态审查需确认这个差异没有扩大读取或运行权限。

拟运行source-commit：`87bc592d9c0828d0c698058702edca840e7e151d`。
后续仅docs记录审查，执行前后必须clean、该基线祖先成立且后继仅docs，
运行HEAD和以下七SHA始终一致：

| scripts/文件 | SHA256 |
|---|---|
| aa2024_q_recheck.py | 50a44d40e363cd7023ad988cabe15d4661343a8c45d9d35621470682690fcbca |
| aa2024_q_verify.py | fa1482cf4fd369c6bc6336a62d31a2973e90ab642047a0658334490947869d4f |
| test_aa2024_q_recheck.py | a5b7fc3c1e97132c45df5118d06015baff3a3caf101e66a22137d941f014cedf |
| aa2024_dyadic_reference.py | a492c822d7e06d82ff0c43306b7fdb004e2cb5b987b28bb5fd1646bcb8fd1c36 |
| test_aa2024_underflow.py | faec84e6e98c2063f9010e97028eebee52a8c782684640ed0c7e0b1bc124b87f |
| aa2024_runtime_guard.py | e7bf15a9a46fa60dcc1ef41cbd3f86c2d41fb44bcda6de1ba9300df8cd76874c |
| test_aa2024_runtime_guard.py | 2eb8663fea0a31a9bf88802dc9ac9bdd609934f8ab415a557a8ed6b6d6922e54 |

## 唯一拟执行命令（本轮不执行）

工作目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/aa2024_q_recheck.py synthetic --source-commit 87bc592d9c0828d0c698058702edca840e7e151d --output /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B003
```

仅一次本地轻量资源检查，单线程CPU、CUDA空。不附带测试/验收/第二命令，
不使用管道丢失退出码，不传--allow-two-opaque-hashes、不切real。
用户已取消旧额度停止线，不沿用80%门槛；原60秒预算未放宽。

## 人工资产、分解与读写界限

完全由源码确定性生成：41×21网格、861节点、1600三角形、120边界节点、
741内部节点/1482自由位移分量；27×24=648人工规则点/1296观测分量，
A为1296×1482。人工权重1、边界0，观测和old/proxy/intact三臂均为源码
正弦/余弦。三标签不读取同名真实冻结预测；人工rank不强制真实1203。
不改变stage13/14原648点、权重、网格、边界或任何冻结预测。

仅一次gesvd SVD（full_matrices=False），两次economic无pivot薄QR：
刚体H一次，Q Lr的修复U一次。计数为受控API记录而非全进程追踪。
若故障提前停止，可能少于1/2，须保留实际计数，不补做分解。
无刚度组装、FEM求解、q拟合、训练或调参，不导入旧producer。

允许源码/Git和运行依赖/系统配置/字体读取；不读local_archive旧内容、
旧NPZ/report、真实训练数组、stage15响应或任何新留出。不为避开警告
预热字体、复制旧缓存、禁用Timer或压低日志级别。绘图仍由原代码在新B003
内创建全新.mplconfig/.cache，不借用B002缓存。只写新B003人工产物和缓存；
旧B002及其他冻结产物完全不动，不创建目录或产物于本次准备阶段。

## 原数值判据与60秒口径

rtol=1e-12，matrix/vector/square atol=1e-12/1e-15 mm/1e-18 mm²；
五参考乘积站点、操作数、派发/舍入证书、全分量比较和首失败见证不变。
tau=1e-12*smax，s>tau，[tau/10,10*tau]未决谱带首停，eta<=0.5；
binary64模型、有限性、双侧奇异对、Q/Gram/QR、保留子空间与平方账本全保留。
不要求legacy必须失败，也不由其通过声称修复因果有效。

Budget起点保持原代码：导入、参数/线程检查、初始Git/七SHA、路径检查、
目录创建和初始receipt元数据后，check_model之前。此后人工资产、构造、
1SVD/2QR、数值检查/参考证书、写NPZ/JSON、图/sidecar/缓存、哈希、
末次身份、receipt/completion后检查都计入同一60秒软预算。值>=60即停止。
初始导入/元数据、最终stdout及异常取证不在此时钟内；另留工具wall，不混称。
G01接线没有重置时钟或额外宽限；不是硬杀保证，在途BLAS/SVD/系统调用
可能先返回才检查超时。旧B002或小测试耗时不是本新运行耗时保证。

## 首停与字体日志：没有豁免

- -W error、warnings error和np.errstate(all='raise')保持。
- CLI在NumPy/SciPy导入前安装G01；标准logging factory的WARNING及以上、
  threading.Thread未处理异常升级为exit70，守卫身份/事件检查同样失败即停。
  主线程普通异常走既有非零失败路径；故障后不启动下一阶段。
- **字体缓存日志也必须首停**。即使属于首次初始化、在后台、最后有图或
  completion，也不按成功接纳。新缓存仍可能触发该日志；本包不保证完成，
  不根据结果事后豁免，也不触发自动修订/重试。
- 第一个非预期异常/警告、模型/数值检查失败、身份/路径不符或软预算超时，
  本次即未完成。不要扩时、改线程/容差、换目录续算或重跑B002。
- os._exit可能只留下event/终端和部分文件，无failure_receipt或清理保证。
  非零退出/事件优先于任何completion；保留局部产物，仅作取证。G01不承诺
  标准logging/Thread之外的全部native故障或OS阻塞瞬时停止。

## 新产物、结果图与完成规则

仅新B003，预期九项被哈希资产：certificate.npz、report.json、
q_residuals.png/pdf/md、q_square_ledger.png/pdf/md、runtime_guard_events.log；
另有execution_receipt.json、completion.json及两个新缓存目录。

| 图 | 来源与显示 | 边界 |
|---|---|---|
| q_residuals | 本次证书/报告，全648人工点，U/V两行×Q retained及三臂四列；共享对称RdBu_r，D^-1显示mm | 不改权重、不平滑；synthetic标签必须与stages13/14上下文同读 |
| q_square_ledger | 同批rows，三臂J_Q+gap²和J_k黑点，mm² | 平方可加，RMS不相加，不作真实力学误差归因 |

图器原样复用，同stem说明绑定同目录证书；本轮不出图或视觉验收。
图存在不代表已验收；独立数值/图形验收需后续另行准备、审查与批准。

未来本命令“producer完成”必须同时：外部exit0、完整终端无非预期事件；
G01事件文件可读且空，guard版本E019-D03-G01-v0.2/healthy=true/fatal_seen=false；
七源码及运行HEAD不变；原身份/数值/预算检查完成，受控计数1SVD/2QR；
receipt/completion哈希匹配、九资产清单与哈希一致、inputs={}、没有failure_receipt。
初步完整性只读本次元数据/事件及文件哈希，不解码certificate/report或查看图；
这不是独立算术/图形验收。不因仅有exit0或completion即放行。
状态仍为producer_completed_not_independently_accepted；不能升级物理或DIC结论。

启动后若工具仅返回session，继续只读监测本命令至真实退出，保存全部输出；
看到异常先停后报告，只检查该精确进程，不盲目重发或杀其他进程。单次运行
若失败保留首阻断、阶段及可取得计数，缺取证不重试，不强制继续读取产物。

## 预检、审查与审批边界

本轮仅路径元数据：B003不存在（含symlink检查）；所有既有祖先为目录且
无symlink；所在卷df约486GiB可用。未创建新目录、未读取旧数值内容；
磁盘快照不是峰值内存认证。获批启动前须重核上述路径/磁盘及clean/七SHA。

独立只读Codex聚焦：两行路径差异、七SHA/新基线、确切synthetic命令、
1/2受控分解及信息集、G01覆盖/例外/事件优先、原预算口径、九资产和完成规则；
复用不变代码审查。不得运行Python/导入/AST/测试/计算，不读archive内容/
真实/留出，不写文件或联系其他代理。审查通过仅代表可交用户审批。

本轮最小资产为本包和静态审查收据，回到S03 storyline；未来执行后保存
外部终端/退出/身份和完成或首阻断结果。B002仍隔离，C/D、真实读取、验收、
新字体日志豁免与后续重试均不在本次批准范围。
