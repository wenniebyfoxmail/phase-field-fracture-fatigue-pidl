# F01-V001 — 命令B一次派生SVG完成，未打开或独立验收

2026-10-19（Europe/London）。用户批准最终执行包后，只执行确切B一次。
外部exit0、终端无非预期警告/异常，guard事件为空；派生显示基本完整性
已核对，不是独立数值或图形验收。无重试，未打开SVG。

## 目的 / 本轮 / 结论

- 目的：沿用F01 D3，检验已保存的未接纳合成值可否不经过字体管理器、
  不重复分解而导出SVG，服务后续DIC反演诊断的显示能力。
- 本轮：两张SVG、同名说明及派生收据正常写入全新V001；源代码不变，
  零实际SVD/QR，单线程CPU、原60秒软预算内完成。
- 结论：该合成派生显示路径已运行成功；未观察图形，不能评价布局、
  可读性或场机制，更不能据此判断B003数值、真实DIC反演或预测有效。

## 运行身份与完整终端

- Run ID：`S03-E019-D03-F01-V001`。
- 主机：`Wennies-MacBook-Pro-14.local`；PID `79373`（运行收据）。
- 固定代码基线：`6514160302be3f654d96bf19ba8d2d747c6bfd26`。
- 前后clean运行HEAD：`30bc4b4cd29542ca8d6749f2df156e3d17b665f8`。
  祖先关系满足、后继仅docs、三源码SHA与A001/既有审查/最终执行包相同。
- 最终执行包SHA256：`1992269f2d1de10c4de9fd9cc779c20045a4821d1301ef6425189050c44019e0`。
- Python 3.12.2，NumPy 2.2.6；运行日志未报告警告或异常。
- 工具chunk `0d9710`，同步exit0，无运行中session；只发起一次命令。
- 脚本stdout前取样 `0.33283079200191423` 秒；收据前取样
  `0.2636857079924084` 秒。stdout后最终预算检查通过才exit0。
  工具wall为 `0.2491935` 秒，口径不同，不混同或相加为精确全程时间。
- 围绕启动前检查及退出后核对的UTC观察窗口12:15:29–12:15:45，
  即BST13:15:29–13:15:45；不是精确进程起止记录或硬实时承诺。

工作目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`

实际确切命令（一次）：

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -W error -B scripts/aa2024_saved_svg.py --source-commit 6514160302be3f654d96bf19ba8d2d747c6bfd26 --input /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B003 --output /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001 --allow-unaccepted-synthetic
```

完整工具合并stdout/stderr：

```text
{"status": "derived_display_completed_not_visual_or_numerical_acceptance", "elapsed_before_print": 0.33283079200191423}
```

## 前置检查、输入边界与基本完整性

启动前V001及其F01父目录不存在；祖先和两个输入无符号链接，输入为普通
文件，磁盘可用477GiB。未预建输出、预热/复制字体缓存或启动旧测试/producer。
运行只解码固定B003的六个NPZ成员，整体严格解析report但仅消费schema/rows；
整文件SHA读取不等于解码其它成员。基本收据核对不消费report数值或SVG内容。

输入当前SHA与脚本开始/过程/完成前指纹相同，外部退出后SHA复核也相同：

| B003输入 | SHA256 |
|---|---|
| certificate.npz | 9148f89493c076b1833aa29f92cbc92502be282350b325767fff739adc6cbe94 |
| report.json | 9c950fe4c529f9bda52fd6eb68c8b3b19c90e01297a861e54aea8ef662e4673f |

新输出根：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001`

| 资产 | 字节 | 外部SHA256（与receipt一致） |
|---|---:|---|
| residuals.svg | 965937 | 8228c9b7b8e2f247f0ce9fb764c5ea9863be2b96a4eb3cbf8add39803b07893f |
| residuals.md | 2657 | 33632165d5cf01b8b8e8b8ffc46a3ba9953e8d3af61608118e1bc0f5a9c7fed1 |
| square_ledger.svg | 4210 | 210aeb0aaa3ea03a51c6cd6a0575ed223f62828044e212ec69a5c8cd6a7772a5 |
| square_ledger.md | 2571 | cf14301c56c61853ad19a0ca5e5b58bf3ea906d81409501e4a19e31d0deeae6a |
| runtime_guard_events.log | 0 | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |

另有derived_receipt.json（3095字节）与derived_completion.json（94字节）。
receipt SHA为 `22a84024dd011230e0a89790c6d8681ffeebb2684b257978a6a8cee63892cc5a`，
与completion绑定值相同；无display_failure.json、无额外缓存/图片/转换输出。
G01 v0.2记录healthy=true、fatal_seen=false；事件文件为空，外部exit0。
源码三个SHA前后不变，详见最终包及receipt。仅完成批准范围内的哈希/收据/
目录基本核对，不调用verifier、不开展独立验收，不重算投影或平方账本。

## 保留的限制与下一步

不导入Matplotlib/SciPy/旧producer或verifier，未预热缓存、未豁免字体日志；
沿用G01、warnings-as-errors、浮点首停和分解入口禁止保护。收据零SVD/QR为
受控路径口径，不冒称全进程系统调用追踪。原容差、预测、权重和冻结产物不变。
B003的incomplete_unaccepted_synthetic标签保留：本次当前hash不能证明其
历史生成有效；未重跑B003/B002、未修复原收据、未读取真实数组/stage15或新留出。

遵照用户限制，未打开/渲染SVG，未运行sidecar validator或独立数值/视觉验收，
未调用子代理、C/D或外部发送；因此不嵌图、不作视觉解释，也不复制转码至Obsidian。
本轮到此停止；若后续希望据图作判断，需要另行授权只读图形/说明验收，
不应为展示而重做SVD/QR。真实训练侧Q一致性复核的科学结论仍未由本轮回答。
