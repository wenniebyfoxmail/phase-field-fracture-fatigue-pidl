# G01-R65-A001 — 原65项人工回归执行包 v1（待静态审查及用户批准）

2026-10-18（Europe/London）。本轮仅准备和独立只读审查，不运行Python、
导入、语法/AST检查、测试或求解。本包不修改任何源码或冻结数值产物。

## 问题、依据与结论边界

在G01修订后的代码身份下，原来的41项人工算术边界测试及24项stub回归是否
仍按原判据一次完成？成功只支持该人工回归的兼容性，不证明真实DIC反演。

- A002曾在旧基线ab6f123a下65/65通过，见underflow_a002_results.md；
  历史结果保持原样，不能当本次新代码下已通过。
- G01-A001在当前数值代码基线下26子进程/两类源码断言已通过，见
  thread_stop_test_results.md；那次不运行原65项，不能代替本回归。
- 本轮比照A002运行HEAD c024bfac，两个原测试文件与参考算术文件字节未变；
  rg文本计数41+24。仅文本/Git/hash检查，不执行test discovery或AST。
- 原65 runner导入candidate/verifier而非执行其CLI，candidate._RUNTIME_GUARD
  为None，新guard helper只被import，不安装进程退出机制。原日志/异常单元
  的assertRaises行为保留；本回归不是重测G01跨线程os._exit路径。

## 固定身份

代码基线：`ecb8b9a9238b035f9a87bf7d4a85deb2455b95e0`。
准备起点HEAD：`bea9acf7259928f6bd9b4d3d3092e1f10d4e39c2`，clean。
基线之后只有docs；与G01-A001运行时七源码SHA一致。执行前/后再次核对
实际HEAD、clean、基线祖先关系及仅docs后继，不用旧五文件身份替代七文件。

| scripts/文件 | SHA256 |
|---|---|
| aa2024_q_recheck.py | fc35d2c2a85780228468417613eb194ac95e6ca8b77d37f76f4ac1eba3bb8fcf |
| aa2024_q_verify.py | db48c03ccd5b4972663e10b31f54cbbc3562b9d78d994852f10b69190c85af09 |
| test_aa2024_q_recheck.py | a5b7fc3c1e97132c45df5118d06015baff3a3caf101e66a22137d941f014cedf |
| aa2024_dyadic_reference.py | a492c822d7e06d82ff0c43306b7fdb004e2cb5b987b28bb5fd1646bcb8fd1c36 |
| test_aa2024_underflow.py | faec84e6e98c2063f9010e97028eebee52a8c782684640ed0c7e0b1bc124b87f |
| aa2024_runtime_guard.py | e7bf15a9a46fa60dcc1ef41cbd3f86c2d41fb44bcda6de1ba9300df8cd76874c |
| test_aa2024_runtime_guard.py | 2eb8663fea0a31a9bf88802dc9ac9bdd609934f8ab415a557a8ed6b6d6922e54 |

## 唯一拟执行命令（暂不执行）

工作目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/test_aa2024_underflow.py --source-commit ecb8b9a9238b035f9a87bf7d4a85deb2455b95e0
```

仅本命令一次，不附加另一24项runner、G01子进程包、producer/verifier CLI、
B002/B003、出图或C/D，不使用管道包装改变退出码。静态通过后仍须用户审批。
用户已明确撤销额度停止线，本包不沿用旧80%门槛；60秒运行预算不变。

## 测试与信息集

| 组 | 固定内容 | 禁止的外推 |
|---|---|---|
| 41人工边界 | 原位型/舍入证书、Fraction独立oracle、派发与原三类容差、错误保护 | 未测输入无条件正确或B001实际下溢根因 |
| 24原stub单元 | Q一致投影小数组、stub QR/SVD与计数、CST采样、权限/身份/预算 | 实际分解、完整producer或新真实场证书 |

与G01标准库-only测试不同，本命令**允许导入NumPy/SciPy**和参考算术，
但以下受控入口均禁止真实执行：candidate.linalg及np.linalg的qr/svd/
solve/lstsq/pinv/eig/eigh，np.load，candidate.artificial；load_real(True)
直接拒绝，False只验证原opaque权限负控在读文件之前失败。
原QR/SVD测试使用显式stub，可能增加模拟Factors计数，不是实际分解。

数据只来自源码内人工数值、小数组/位型及运行所需依赖；CST仿射单元会
在内存构造原固定网格定义和少数人工观测，不读取真实网格/648点或训练资产。
Fake NPZ测试局部覆盖np.load为内存假容器，路径只是未打开的人工字符串，
不打开NPZ/report或读取真实成员。不得把这种fake调用说成真实文件读取。
仅读源码原字节/Git及标准依赖，不读local_archive、旧数值report、真实数组
或留出，不写数值产物、新图、运行缓存目录或覆盖冻结资产。保留终端原文。

原rtol=1e-12；matrix atol=1e-12、vector atol=1e-15 mm、square atol=1e-18 mm²。
五个参考乘积站点、派发阈值、原操作数/预期、eta硬界、原负控均保持。
命令-W error、runner警告错误策略及np.errstate(all='raise')不变。
预登记assertRaises（含原下溢/警告/权限负控）须按原类型通过，不是忽略
新异常的许可，更不是字体缓存日志豁免。无Matplotlib/真实字体扫描。

## 60秒软预算与首停

父runner从首个time导入后START计时，涵盖其他导入、初始Git/七源码身份、
模型检查、两组测试、最终身份核对及stdout后末次检查。继承24项的局部
tearDown还有自己的60秒检查，但不替代或重置顶层整包时钟；Budget单元的
人工fake clock仅测试阈值，不是扩时。elapsed>=60即停止，不接受部分通过。

unittest failfast=True；首个非预期失败/错误/警告、模型不支持、守卫或身份
不符、预算超时立即停止，不跳项、不补跑、不重试、不修改容差/操作数救结果。
检查点不能强行中断在途导入/系统调用，故不是60秒硬杀进程保证；不扩预算。

## 成功、保存与下一步

只有实际exit0、65项全部运行并通过（无跳过/失败/错误）、最终身份/预算
检查通过，才记录这次人工回归成功。核对unittest输出与最终JSON tests=65，
以及actual_svd=0/actual_qr=0的受控代码路径/守卫口径，不当作系统调用追踪。
elapsed_before_print只代表stdout前取样，另记录工具wall，不混为精确总时长。
若exit0但项数/终端异常不符，仍为本次未完成，不能补跑或自动认定通过。

获批执行时，最小资产是G01-R65-A001完整stdout/stderr、exit与身份/预算
记录，写到本任务docs结果及S03 storyline。纯人工回归无物理结果图，不出图。
失败保留通过组件和首个阻断，不等于否定DIC路线；任何修订/新执行另批。

本轮独立审查仅源码/文档/Git/hash，重点是当前import模式、7源码绑定、
65项原判据、零实际分解/数据读取守卫、原60秒及命令一致性。复用G01/U01
不变审查，不重开科学设计或Pro审查；只读通过不是本回归实际通过。
若未来通过，仍不解除B002隔离或开启新资源检验/真实读取/验收/C/D；
下一项资源方案和确切新Run命令须另行准备审查批准，本轮不包含。
