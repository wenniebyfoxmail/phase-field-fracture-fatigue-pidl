# F01-V001 独立只读验收 — 结构命令通过，说明语义阻断后停止

2026-10-19（Europe/London）。结论：`MODIFY_AND_REREVIEW`，不是科学失败。
命令1成功，但说明人工审阅发现首个问题；遵守首停，没有打开两张SVG或继续
命令3。派生图导出成功与本次结构检查的进展保留，不声称整体显示验收通过。

## 身份、权限与实际执行

- 用户明确批准最终方案确切命令的一次独立只读验收；仅V001七份派生产物，
  单线程CPU、60秒软预算、零SVD/QR，不重绘/重算/改冻结产物，不读B003
  数值/真实/留出、不启动C/D，首个非预期异常或警告停止、不重试。
- 独立本地Codex：`/root/e019_d02_review`，沿用既有配置；不是Pro或云端。
  未参与V001生成，既有代码审查不替代本次实际验收。
- 方案：[font_svg_display_acceptance_plan.md](font_svg_display_acceptance_plan.md)。
  SHA256：`c7f0c205c55e20c584cfe804f188868c854b68639824a864bc897cfe5e1b2657`。
- 预检clean HEAD：`426f9de9b4c64ec2a9f6a619eac387f4af85128d`。
  固定代码基线为祖先，后继仅docs。主代理在独立者运行时未改工作区、未看图。
- 独立者完整读取并核对原命令，原样提取方案第85–209行交`/bin/bash`，
  命令1只执行一次；chunk `63a0b9`，同步exit0，无session，无重试。
- 最终stdout状态`PENDING_VISUAL_QA`，stdout前取样`0.03947737504495308`秒；
  stdout后60秒检查通过。工具wall `0.00000575`秒为另一个工具口径，不能
  混成精确脚本总时长或回写原出图预算。

## 已完成与未完成

| 项目 | 实际范围 |
|---|---|
| 独立静态/启动预检 | 方案SHA、clean HEAD、代码基线祖先、仅docs后继 |
| 命令1 | 七派生资产冻结哈希、receipt/completion绑定、空guard、JSON/XML结构、8×648保存点ID/坐标属性、9账本标记与说明保存行直接对照、说明全文打印；末次命令内身份/哈希及预算检查完成 |
| 说明人工审阅 | 发现首个阻断并停止，不能签全文语义验收完成 |
| 命令2/两图目视 | 未执行；Safari打开0次、截图0次，两图均未目视 |
| 命令3/目视后末检 | 未执行；不补查、不声称完整验收结束身份复核 |

命令1中的点属性/保存标量直接比较不是源数组、颜色数值映射、坐标变换、
投影或Pythagoras恒等式的独立数值验证。零SVD/QR和guard字段不构成历史
系统调用审计。命令没有出现warning或traceback；停止理由是说明语义问题，
不是运行失败、预算超限或数值条件不满足。

## 独立者首个问题与原文

问题文件：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001/residuals.md`

读图说明含：`Shared symmetric eleven-stop RdBu_r-style RGB interpolation; deweighting is display only.`

限制段却写：`No caching, interpolation or smoothing.`

独立者结论原文：

> MODIFY_AND_REREVIEW — 命令1通过，但说明审阅发现阻断，已立即停止。
>
> 首个问题位于 residuals.md：读图说明写明 RGB interpolation，限制段却笼统写
> No caching, interpolation or smoothing.，未区分色标 RGB 插值与空间插值／平滑。
> 按方案第238–240行，必须澄清后复审；本次未修改原文。

这是验收方案预先明确要求检查的说明歧义。不能把RGB色标插值误写成数据
空间插值，也不能为使验收继续而将本问题事后忽略；没有证据表明已进行了
错误的空间插值或数值重算。当前也没有实际目视结果来判断图形布局好坏。

## 命令1最终stdout JSON（原样）

完整工具终端先打印了两份已冻结说明全文，随后输出以下JSON；说明全文仍
在原派生产物，独立工具chunk见上，当前不另行打开或修改原文件。

```json
{"actual_qr": 0, "actual_svd": 0, "elapsed_before_print": 0.03947737504495308, "sha256": {"derived_completion.json": "f4c649e1c18b9d08ce7d279e26d46b59e876ed019350ba9eaff0929f8c3dc0c2", "derived_receipt.json": "22a84024dd011230e0a89790c6d8681ffeebb2684b257978a6a8cee63892cc5a", "residuals.md": "33632165d5cf01b8b8e8b8ffc46a3ba9953e8d3af61608118e1bc0f5a9c7fed1", "residuals.svg": "8228c9b7b8e2f247f0ce9fb764c5ea9863be2b96a4eb3cbf8add39803b07893f", "runtime_guard_events.log": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "square_ledger.md": "cf14301c56c61853ad19a0ca5e5b58bf3ea906d81409501e4a19e31d0deeae6a", "square_ledger.svg": "210aeb0aaa3ea03a51c6cd6a0575ed223f62828044e212ec69a5c8cd6a7772a5"}, "status": "PENDING_VISUAL_QA"}
```

## 主代理采纳、边界与下一选择

采纳独立者停止及限定结论。只新增本证据记录与现有owner/index里程碑，
不改源码、方案、SVG/说明/收据或任何冻结产物，不补运行命令2/3。
未打开/hash B003原文件、真实数组/stage15/新留出；终端来源指纹只是派生
说明的已有文本。未导入NumPy/SciPy/Matplotlib/producer/verifier，未分解、
重算、重绘、转码或启动C/D。B003继续incomplete/unaccepted；本次既不证明
也不否定真实DIC反演或预测能力。主代理未以自己看图替代独立者缺失范围。

建议下一项仅准备“不改图、另存澄清说明及映射收据”的方案供用户选择，
明确允许的是RGB色标插值，未做数据空间插值或平滑；原图/说明/数值/收据
全部保留。修订和剩余验收均需另行批准，本轮未准备执行器、未修订或续验。
不能因为该文字阻断反复重做SVD/QR、旧B或真实计算。后续若继续验收，须
明确新说明映射、保留已完成检查，并如实完成两图目视及末次身份复核。
