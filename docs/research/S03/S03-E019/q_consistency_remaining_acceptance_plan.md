# E019-D02 — 新说明映射下的剩余独立只读验收 v1

2026-10-17；仅准备并静态审查，未执行验收、导入、语法检查或测试。
承接 D02 已冻结的合成数值标准和首轮暂停，不开新诊断或改变阈值。
当前不读取合成 report/CSV 数值或图形；仅阅读冻结源码/协议/已有记录，
并为执行包绑定新说明收据的字节 SHA，未据此宣称其独立验收通过。

## 1. 问题、依据和结论上限

问题：已有 D02-R001 的三例操作数是否支持原定五维 Q 一致投影，且
保存表、图、运行身份和新说明映射是否一致？不是重新生产任何结果。
来源：[原实现契约](q_consistency_test_design.md)、[原停验](q_consistency_evidence_review.md)、
[生成记录](q_consistency_results.md)、[说明静态审查](q_consistency_sidecar_static_review.md)。

说明派生已按用户批准的确切命令一次生成，工具 chunk b988e0、exit0、
收据写前约0.003955584秒/60秒；这只作为既有执行事实，不等于验收。
新说明 SHA b4ad866d79174d72fbecefad051092ea6ebb8e1f964a7bd2c2a1532474fd9246；
新收据 SHA 631afb1ca7c204fe85225853d1b252c5c1e931c66289f0eea48f7dad8e209c37。

通过最多支持三个固定人工控制上的保存证据一致性及投影必要条件。
不改变旧 E019 暂停状态，不认证真实根因、真实 DIC 反演或预测有效性。
没有 C0 原 C/A 或原 Qr 的新核验；不重新打开 D01 报告或真实数据。
本次是原验收的剩余实现，不增设算法、主要标准或跨路径 ratio 相等门槛，
不触发新的研究方案外发；仅安排独立只读 Codex 静态审查。

## 2. 输入白名单与说明映射

合成根目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D02/S03-E019-D02-R001`

仅该目录的8文件：report.json、summary.csv、q_identity_ratio.png、
q_identity_ratio.pdf、原q_identity_ratio.md、execution_receipt.json、
q_identity_ratio.sidecar_v01.md、q_identity_ratio.sidecar_v01.receipt.json。
每文件 SHA 在新脚本中固定；不按收据任意路径扩大读取范围、不递归扫描。
另只读 D02-T001 的 test_receipt.json/tests.log、原10项源码/协议/测试设计
及 Pro 记录（字节与固定0fb6bfe快照核对，不打开外部会话）、说明派生
脚本、原说明检查器源码和本次验收脚本。均为明确路径，拒绝输入软链。

冻结映射：

| 既有图 | 本次采用的已生成说明 |
|---|---|
| q_identity_ratio.png | q_identity_ratio.sidecar_v01.md |
| q_identity_ratio.pdf | q_identity_ratio.sidecar_v01.md |

核新说明严格等于原说明的两处已批替换：How to read 标题、五探针明细
只在 report 而不在七列 CSV；其余字节不变。核派生收据映射/前后来源 SHA/
代码 SHA/新说明 SHA/未验收身份。核原检查器规定的长度≥400及三个短语，
不修改/导入/运行原目录 validator，不声称其 same-stem 检查通过。
原同名说明保留；本协议只验收显式映射的新 companion，不伪造新图或
空目录运行成功。未来若需发行目录整体达标，仍须单独组织，当前不做。

禁读真实648点、训练 prepared/solved/四组预测、stage15/R003、新留出、
旧E019或D01数值报告、NPZ/ZIP/节点映射和其他 Run。

## 3. 固定顺序与已保存数值核验

由未参与本验收实现的独立 Codex 按确切命令执行一次：

1. 核本脚本 SHA、clean HEAD、固定文件 SHA、10项源码与0fb6bfe快照、
   A/B收据与A日志身份、CPU/预算/历史受控计数、唯一获批的历史字体日志。
   计数字段只认证保存来源一致，不冒充独立历史进程审计。
2. 核新说明严格派生和上述映射；核内容/数值行与保存报告/CSV相符。
3. 核三例schema/顺序、五模式、原容差、CSV七列与保存值、输入机制标签。
4. 只用已保存操作数的标准库 Decimal80 / math.fsum 参考算术核对：
   - 保存的 dyadic H/clean/V/g、s及c/a/t常量、y/Lr/A人工定义；
   - H Gram、B=QLr、UT=B、U Gram、T正对角/三角形式及eta行和≤1/2；
   - 保存p/r与实际U的完整Decimal参考、残差定义、Uᵀr、解析p*/r*；
   - 输入y、新U/p/r及原r的保存Q逐分量float/Decimal/fsum路径与状态；
   - C1原p/r按原容差保持，C2/C3原路径仍为预登记Q负控；
   - 每例五探针的b/image/d/total、像内条件、加法、交叉项、Pythagoras、
     解析gap/total和残差floor；
   - C2/C3的A不同、Lr/y及原p/r相同，不冒称两个独立压力输入。
5. 原PNG的签名、逐chunk CRC、IEND和1836×986像素；原PDF用现有
   `/opt/homebrew/bin/pdfinfo -isodates` 只读解析，要求单页、未加密、
   页尺寸777.6×417.6pts，对应原10.8×5.8英寸定义。捕获stderr，任意
   警告/解析失败即停。不生成PDF渲染文件或其他图片。
6. 末次固定文件/源码/脚本/HEAD/clean状态与预算核对，stdout输出报告。
7. 仅在命令exit0、没有迟发异常且结果明确为PENDING_PNG时，独立Codex
   只读查看原已保存PNG一次，核对下节视觉清单。命令失败绝不进入此步。

“不重算”在此指不重跑producer、诊断、投影候选、fixture生产或新分解。
上述内存参考乘积/标量核验是剩余验收的内容，不写入或替换任何数组。
禁止导入NumPy/SciPy/Matplotlib/producer，零QR/SVD/eig/找秩/FEM/训练/
测试/绘图。只用已存U/T，不重新分解B；不回写Qp/Qr或改变任何输入。

## 4. 原容差与路径语义不变

保持 abs(x−ref)≤atol+1e-12|ref|：matrix/无量纲1e-12，vector1e-15mm，
square1e-18mm²。eta≤1/2仍是原硬保护，不加isclose；保留五个模式。

独立 Decimal80 精确导入已保存binary64；fsum先完成float乘积再求和。
核保存Q逐分量与参考向量接近；直接用保存producer Qz_float/z核其原ratio
定义，用独立Decimal Q/z核Decimal80_ratio定义。**不要求producer ratio
与参考ratio彼此相等**，不从向量接近推导归一化标量接近；两者分别输出。
Q评估或Q通过状态在路径间不一致时分流
STOP_REFERENCE_PATH_DIFFERENCE_UNRESOLVED，不直接判原report损坏。
缺失的未保存中间einsum积不重造历史；部分保存product/probe ratio字段
只核原范围及其对应已存恒等式，不声称所有末位/每个历史ratio逐bit重现。
C1原0变新小非零仍按原容差判断，不宣称每例ratio均改善。

## 5. PNG目视清单与PDF范围

只读调用（不是终端命令，不生成新图）：

```json
{"path":"/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D02/S03-E019-D02-R001/q_identity_ratio.png","detail":"original"}
```

使用view_image一次，由独立执行者检查：一张面板、C1/C2/C3固定顺序、
旧橙叉/新蓝圆、symlog/阈值1、旧0不加epsilon、C2/C3旧负控明显高于1、
所有新值低于1、数值标签与命令输出对应、标题/图例/标记无误导遮挡或
裁切。零标记越轴但不越画布是原设计，不当作新异常。
不调整字体/布局，不渲染PDF或另出缩略图，不以主代理先前看图代替独立验收。

PDF本次仅解析/页数/尺寸与冻结SHA完整性，**不认证PDF目视质量或PNG/PDF
像素等价**。遵守“不重绘”限制，不采用PDF技能默认渲染步骤，不运行
pdftoppm。缺少PDF独立目视作为范围限制保留，不隐藏成“全部视觉通过”。

## 6. 预算、输出与首异常停止

自动命令单线程CPU、CUDA空、Python -I -B -W error、60秒，覆盖标准库
加载后的START、所有来源/读取/内存算术、pdfinfo、末次复核与stdout后检查。
所有子进程共享剩余时间；SIGALRM不是系统级硬杀保证。PNG工具读取/人工
判断与计算预算分开记录，不声称人工审阅也在这60秒内完成。

本轮与未来命令全程不写文件、不创建目录、缓存或收据，结果仅在stdout；
没有日志重定向。stdout中的elapsed_before_stdout_seconds只是输出前取样；
必须工具exit0且最终预算检查无异常才采纳。未来报告留在对话，不写回产物。
历史B字体日志只读核身份，不是本次新警告许可；任何新warning/error、
非有限值、schema/身份/预算/数值/视觉异常首个立即停止，不补查、不修复、
不重试、不改阈值/路径或换验收算法。失败stdout列已完成项后非零退出；
当前仅准备，没有运行任何上述检查或提前拿结果适配代码。

输出分层：

- 自动项通过：PASS_SAVED_SYNTHETIC_ARITHMETIC_AND_MAPPED_SIDECAR_PENDING_PNG。
- 命令或视觉异常：STOP及准确层级，原结论不变，不把参考路径差异直接
  归为report错误，也不把说明/PDF工具问题归为数值修复失败。
- PNG亦通过：独立执行者报告“保存合成算术、新说明映射及PNG目视通过；
  PDF只读解析/元信息通过”。必须保留上文范围限制，不称原目录validator通过。

## 7. 确切命令（待静态审查与用户执行审批）

脚本：scripts/aa2024_d02_remaining_readonly.py；SHA256
`93b048c9948475ca7c9cfd357c13c4e12b963c9ee258708c0f010af258bcecd3`。
不导入producer或旧验收器；不自动重新执行说明修订。命令只批准一次，
后续条件式PNG查看也须包含在该次明确授权范围内。

```bash
set -euo pipefail
cd '/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013'
export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
unset PYTHONPATH PYTHONSTARTUP PYTHONHOME PYTEST_ADDOPTS PYTEST_PLUGINS MATPLOTLIBRC
'/Users/wenxiaofang/miniconda3/bin/python3' -I -B -W error scripts/aa2024_d02_remaining_readonly.py --expected-script-sha256 93b048c9948475ca7c9cfd357c13c4e12b963c9ee258708c0f010af258bcecd3
```

无导入/语法/测试执行。静态审查若发现必须修改问题，先记录并修订/复审，
不边验收边改；审查通过后只展示命令，等待用户批准。
