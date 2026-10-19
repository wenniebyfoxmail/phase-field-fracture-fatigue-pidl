# F01 命令B最终执行包 v1 — 待用户批准，仅一次派生SVG

2026-10-19（Europe/London）。本轮仅准备，不执行B、不读B003数值或哈希、
不出图、不启动独立验收或C/D。原执行包、审查记录和冻结产物原字节保留。

## 目的与当前决定

目标仍是从真实DIC观测桥接到可验证的状态反演；F01只解决显示环节被字体
初始化阻断的问题，不替代真实训练侧数值复核或物理验证。
沿用font_plot_separation_plan.md的D1及既有独立审查，不重开路线或复跑测试。
D2人工接口已完成（F01-A001，40/40、exit0）；当前D3是已有未接纳合成值的
派生显示准备，owner为本聊天S03-E019-D03-F01。待批准后一次B只回答：
不导入字体管理器、不重新分解，能否把保存值独立导出为可追溯SVG？
成功只支持该显示能力；任何非预期异常/警告停止并报告，不自动修补或重试。
后续视觉/数值独立验收和真实DIC动作均不由此自动开放。

## 代码身份与既有验证

- 准备起点clean HEAD：`c58a56600966069e292d4c0ed08dad884fc83214`。
- 固定代码基线：`6514160302be3f654d96bf19ba8d2d747c6bfd26`。
- A实际运行HEAD：`8920759fd8716c648b488356758161bd78874435`；完整证据见
  [font_svg_a_results.md](font_svg_a_results.md)。40项全部通过，无skip、
  非预期警告或重试，零实际SVD/QR；本轮未重跑。
- 原独立只读代码审查见[font_svg_code_review.md](font_svg_code_review.md)，
  原确切B命令见[font_svg_execution_package.md](font_svg_execution_package.md)。
  本包不改代码、命令、输入/输出路径或停止规则，沿用该审查；不新开验收。
- 基线到当前HEAD只改变docs；`git diff --exit-code 基线 HEAD -- scripts`
  为0。三源码SHA与A和独立审查逐项相同。

| scripts/文件 | SHA256 |
|---|---|
| aa2024_saved_svg.py | 625e312c760a9f1685fe9afd4aaeea0cadcf772556eab87999a27e5bec4bdf99 |
| test_aa2024_saved_svg.py | 6b7a3f4a5fc9588f39f9e034571ee5ec30a12a620d0cb133aa757bf91aaa1d7b |
| aa2024_runtime_guard.py | e7bf15a9a46fa60dcc1ef41cbd3f86c2d41fb44bcda6de1ba9300df8cd76874c |

本包提交后允许仅docs后继；启动时记录实际clean HEAD，核对基线祖先、
后继仅docs、上述三SHA。运行前后HEAD及三SHA必须相同；不以旧记录代替重查。

## 确切命令B（本轮不执行）

固定工作目录：

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013
```

在该目录中仅执行以下命令一次，不附带测试、预热、转换器或verifier：

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/aa2024_saved_svg.py --source-commit 6514160302be3f654d96bf19ba8d2d747c6bfd26 --input /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B003 --output /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001 --allow-unaccepted-synthetic
```

## 允许输入与新输出

若用户批准B，除源码/Git/依赖外，仅读取固定B003目录中的certificate.npz和
report.json及其当前SHA256。NPZ只解码source_xy、scale、r、old_r、proxy_r、
intact_r六成员；report整体严格解析，仅消费schema/rows。
整文件哈希会读取文件字节，不等于解码其他NPZ成员；此读取权限尚未执行。
仅做D^-1 r显示映射、坐标/色标/保存标量排布，不复算Q、p、r、Gram、投影、
平方账本或误差分解，不做SVD/QR/FEM/拟合，不改原容差、权重或预测。

新输出固定为：

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001
```

计划仅新增residuals.svg、residuals.md、square_ledger.svg、square_ledger.md、
runtime_guard_events.log、derived_receipt.json、derived_completion.json。
普通失败可能新增display_failure.json；G01/预算失败不保证有失败收据。
不生成PNG/PDF，不打开或渲染查看器，不启动独立数值/图形验收。

本轮仅元数据预检：上述V001及其F01父目录均不存在；从根到两个输入及新
输出的现有路径未见符号链接。两个输入为普通非符号链接文件，大小分别为
78,468,281与116,470字节；未读取内容或哈希，不能据此声称内容有效。
所在卷当时可用477GiB。未来启动前须重新检查目录仍新鲜、祖先无符号链接、
输入为普通文件和磁盘可用；任何不符停止，不删除、覆盖或自动换目录。

## 预算、保护和停止规则

- 单线程CPU，CUDA空，六个线程变量均1；原60秒软完成预算不变。
  脚本START在首次time导入后取样，之后的导入、Git/hash、读写、生成、收据和
  最终stdout后检查均计入。另记录外部运行墙钟，不能拿某个内部局部耗时冒充
  全进程耗时；任何可见预算超限不得判完成。无硬实时/阻塞I/O强杀保证。
- 不导入Matplotlib/SciPy/旧producer/verifier；不预热、复制或初始化字体缓存，
  不豁免字体日志。SVG字体由后续查看器选择，当前无字体等价或布局验收结论。
- 沿用G01、`-W error`、`np.errstate(all='raise')`及数值入口禁止保护；实际
  SVD/QR均须0。受控计数字段不是全进程系统调用审计。
- 首个非预期失败、警告、日志事件、权限/身份/输入变化、输出冲突或预算失败
  立即停止；不跳项、续跑、补图、修改阈值或自动重试。失败后保留新目录部分
  产物，不清理重用。未知退出先查原进程状态，绝不因此重新启动。
- 外部非零退出或异常事件优先于任何completion标记；首停后不继续内容核验
  或独立验收，只保留并报告当时退出/终端/必要停止证据，不借故重读数值。
- 若exit0且终端无异常，仅核对本次执行的基本完整性：输入指纹及源码前后一致，
  五个资产哈希与派生receipt匹配，completion绑定receipt、guard健康且事件为空，
  无failure文件，最终预算检查通过。该基本记录不调用verifier、不重新计算，
  不是独立数值/视觉验收。记录实际命令、HEAD、主机/PID、终端和时间口径。

## 结论与批准范围

这次申请只含前置身份/新鲜性重查、确切B一次及上述基本运行记录；不含
独立验收、打开SVG、真实数组/stage15/新留出、C/D、文件发送或后续计算。
B003仍未完成且数值未接纳，B002仍隔离。当前hash只绑定本次读取，不证明
历史生成正确；派生图不能补认证B003、真实DIC反演或后续预测。
本轮无Python执行、测试、数值读取/hash、出图、冻结产物修改或外部发送。
