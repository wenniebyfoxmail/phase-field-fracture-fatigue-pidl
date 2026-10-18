# F01 SVG执行包 v1 — 仅准备，A/B分立审批

2026-10-18（Europe/London）。本轮不执行任何命令A/B、Python/import/AST/测试、
读取B003数值或哈希、真实/留出、出图、验收或C/D。
按font_plot_separation_plan.md及其独立审查落实D2，问题是显示能否隔离
字体依赖/数值求解；只支持工具能力。尚无新脚本动态通过或视觉结果。

## 固定身份与不变项

准备起点clean HEAD：22cb6179f2f44cc4d3c85cc15757d00f3e6358e8。
新增代码基线：`6514160302be3f654d96bf19ba8d2d747c6bfd26`。
执行前后要求clean、基线祖先成立、后继仅docs、实际HEAD与以下三源码不变。

| scripts/文件 | SHA256 |
|---|---|
| aa2024_saved_svg.py | 625e312c760a9f1685fe9afd4aaeea0cadcf772556eab87999a27e5bec4bdf99 |
| test_aa2024_saved_svg.py | 6b7a3f4a5fc9588f39f9e034571ee5ec30a12a620d0cb133aa757bf91aaa1d7b |
| aa2024_runtime_guard.py | e7bf15a9a46fa60dcc1ef41cbd3f86c2d41fb44bcda6de1ba9300df8cd76874c |

旧七源码与准备起点逐字节一致（git diff --exit-code已核），不复跑旧26/65包，
不改producer/verifier/G01、数值容差、权重或冻结预测。B002仍隔离、B003仍
未完成，不回填其收据、计数、耗时或接受结论。

工作目录，两命令均固定：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`

## 命令A：40项纯人工内存测试（下一项申请审批）

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/test_aa2024_saved_svg.py --source-commit 6514160302be3f654d96bf19ba8d2d747c6bfd26
```

只运行本命令一次，单线程CPU、整包60秒软预算、零实际QR/SVD。不创建/写出
SVG或缓存，不打开/查看图，所有SVG/XML与小数组只在内存测试。
只读源码/Git/标准依赖；不读取B003/report/真实/留出，不启动B或旧测试包。
初始导入即启用G01/导入禁止，真实np.load被守卫拒绝；Fake NPZ只用内存替身。
详细40项、首停和原阈值边界见font_svg_test_design.md。源码计数40不是已通过。

成功须实际40/40、无skip/error/failure、exit0且无非预期终端事件，末次身份与
60秒（含stdout后）检查通过。计数零分解是受控入口口径，不是系统调用追踪。
记录完整终端/退出/运行身份/计时；不由A通过自动开B。

## 命令B：已有未接纳合成值的派生SVG（本轮不申请执行）

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/aa2024_saved_svg.py --source-commit 6514160302be3f654d96bf19ba8d2d747c6bfd26 --input /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B003 --output /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001 --allow-unaccepted-synthetic
```

此命令列出供静态核对，不是当前A审批范围。A通过后仍要用户单独批准B。
本轮不对B003或新输出做内容/hash读取，不创建目录。未来B启动前重查新目录
不存在且全部祖先无symlink，源文件为常规文件，磁盘/clean/三SHA满足才运行。
仅允许读取B003两个合成文件及当前哈希；NPZ精选六成员，JSON整体解析但仅
消费schema/rows。不消费其他输入、旧缓存、真实数组或留出。
运行只显示保存值，无投影/平方账本重算、无新分解/求解、无Matplotlib/SciPy，
不转换PNG/PDF；SVG文本的字体与布局由查看器决定，未视觉验收。

新输出：residuals.svg/md、square_ledger.svg/md、runtime_guard_events.log、
derived_receipt.json、derived_completion.json；普通失败可能有display_failure.json。
收据为“派生显示完成、未视觉或数值验收”，当前hash只绑定本次读取，不追认
输入的历史生成。B003及所有冻结产物、缓存不覆盖、不删除或修改。

未来B成功需外部exit0、干净终端、空guard事件、guard健康、前后输入和源码
身份不变、五资产哈希与派生收据/完成标记相符、无失败文件，原整包软60秒
（含导入、读写、最终stdout后）通过。不能仅凭图或completion认成功。
这是初步完整性，绝不自动调用verifier或数值/图形独立验收。

## 共同停止规则与审查

原数值容差不改或重新评价；显示全零范围不是更改容差。CLI均启用已验证
G01，-W error与np.errstate(all='raise')保持，不豁免字体日志，不预热/复制
字体缓存，不因声称“初始化”而继续。标准logging/Thread之外及OS阻塞仍非
硬实时保证。60秒为软预算，检查点不能强杀在途I/O；>=60就未完成。
首个非预期异常/警告/预算/身份/权限失败即停止，不跳项、续跑或自动重试。
失败写盘也不增加预算；G01或超时可能没有失败收据，外部非零退出覆盖标记。
用户已取消旧80%额度停止线，不因此修改运行预算或要求重新授权额度。

本轮只读审查源码/方案/测试设计/确切命令及Git/hash，不执行代码/测试/
导入/AST或读取数组。审查重点：不变旧代码、白名单/信息集、零分解与导入
禁止、纯显示、不复算/改写来源、SVG转义/面板/共享色标/单位和命名、原预算
及G01路径、40项人工fixture不读真文件。通过后再交用户审批A一次。
