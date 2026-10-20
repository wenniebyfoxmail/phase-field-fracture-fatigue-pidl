# V002-L01 独立只读验收：V1通过，UI工具阻断后停止

2026-10-20（Europe/London）。独立结论：`NOT_REVIEWABLE`，限尚未完成的
实际图形及最终身份验收；不是布局或科学失败。V1身份／允许差异／说明审阅
进展保留。原结构和S01已通过范围、原首停及G运行记录均不改写。

## 渠道、权限与实际步骤

- 人方本轮批准确切执行包V1→目视→V3，独立本地只读Codex
  `/root/e019_d02_review`；复用既有配置，未切到Pro／云端，不虚报不可见的
  后端型号。该独立者未参与本次layout_release.py或V002-L01生成。
- 协议 `preparation/f01_v002_layout/execution_package.md`，SHA256
  `8b74abfd0f047a02801a84b81f4c9966e9c037e1d9d55ae867bd2203f6c52d55`。
  开始clean HEAD `c8e064f1703d0a5c54d84ddcc0d6c8ff9d9b4763`，CLI和manifest
  SHA匹配授权值。主代理审查期间不改工作区、不先看图、不补跑。
- 权限仍为单线程CPU、同一60秒软窗口、零SVD/QR；只读派生资产及固定
  代码／清单／协议／Git。首个非预期异常／警告即停，不重试、不换通道。

| 步骤 | 独立者实际结果 |
|---|---|
| V1 `--mode verify` | 一次，chunk `d7b860`，同步exit0，无警告；`PENDING_REAL_VISUAL_QA` |
| 新说明 | 两份stdout全文读完，未见阻断：来源／布局身份区分，S01语义保持，NEW同目录及OLD绝对路径引用正确 |
| V2 `open -a Safari` | 一次，chunk `812c15`，exit0，终端为空；两张NEW原SVG各请求打开一次，不等于已目视 |
| 原生UI | 第一次缩放按键报错；未取得任何NEW截图，不签视觉通过 |
| V3 `--mode finish` | 未执行；无跨目视最终七SHA／HEAD／clean复核 |

V1执行的是协议原命令，无改参数或另跑旧结构检查。它确认来源十件、NEW
七件、代码／manifest、映射及仅允许的布局／说明变化；原结构／S01通过
内容按相同来源身份继承。这里不把V1当实际显示通过。

## 首停与连续预算

独立者开始记录 `2026-10-20T21:51:40.872Z`（伦敦22:51:40.872 BST），
用持续的 `performance.now()` 单调计时，不重置。UI失败调用前最后可核实
经过 `11940.338041000068 ms`；停止记录 `2026-10-20T21:52:14.022Z`
（伦敦22:52:14.022 BST），距开始墙钟33.150秒，期间未继续验收。墙钟
停止记录不冒充精确的报错单调时刻；本次首停不是预算到限。

原始UI返回：

```text
Computer Use server error -10005: keyNotFound("-")
{ elapsed_ms: 11940.338041000068 }
```

独立者报告：失败调用第一条 `safari.pressKey("super+-")` 未完成；第二次
按键和截图均未执行。未改键名／重试／切通道／补查。准备时Safari只给出
旧V001标签的AX状态，不作为NEW视觉证据。

因此NEW两行、底注、右侧完整色标及单位／极值、三条J_Q标签和柱高呈现
均未实际审阅，窗口尺寸／新图缩放也未核实。不能由XML匹配、打开退出码
或旧图状态推断它们通过，也不能说再次发现了布局缺陷。

## 独立者V1原始结果

同一chunk先完整打印两份新说明，随后：

```json
{"status": "PENDING_REAL_VISUAL_QA", "sha256": {"layout_completion.json": "f4cb18bd510c769b078eafbdeb344a0b377ef6e5be6719bcab0aaf4711802d27", "layout_receipt.json": "748c1f636b31828fb7e080f5205279d5964f62f2bcc8ec0fa722a1d711480376", "residuals.md": "54ffcaba86a88db114f5e548988a217f49b79d0bf290398482ed3be63aba6641", "residuals.svg": "f4051470027642281a5e6f9f5f9bd41afefae6f9eb8ff1d8d970bf6d095fec0c", "runtime_guard_events.log": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "square_ledger.md": "a830f23bbe5b388193736032038dd1cc0afdec4c62fc984922889ba643b48edd", "square_ledger.svg": "018d607c9ccb19af36ae343fc8a4df2249d727682f7c4b322779957ded3222c6"}, "runtime_head": "c8e064f1703d0a5c54d84ddcc0d6c8ff9d9b4763", "elapsed_before_print": 0.25950104207731783}
```

新说明新增关键段原文（实际stdout已全文审阅，不另读或改产物）：

> V002-L01 layout-only derivative of the source V001 SVG. The inherited provenance block remains source provenance, not a new numerical run. V row moved down 70 SVG units; canvas height 820. All saved point attributes and colour-scale content unchanged.

> V002-L01 layout-only derivative of the source V001 SVG. The inherited provenance block remains source provenance, not a new numerical run. Canvas height 720. Blue J_Q bars retain original height; added labels copy the literal saved data-value strings, without scaling or rounding.

## 主代理采纳、限制与停点

采纳 `NOT_REVIEWABLE` 的范围：V1及说明审阅通过，V2打开请求执行过，
实际目视与V3未完成。只归档已返回结果，不执行第二次open／按键／截图／
verify／finish或任何补验，不把归档Git操作误写成V3终检。无须因这个工具
错误改图、重绘或重做数值计算；后续恢复查看／终检需要新的明确授权。

独立者实际科学资产访问仅V1授权OLD十件和NEW七件；未读/hash B003数值、
真实数组、stage15或新留出；无测试、生成、重绘、转码、科学重算、SVD/QR、
写截图、改产物或Git，不启动C/D、不外发。原容差、权重及冻结预测不变。
主代理亦未自行查看或复算。B003仍incomplete/unaccepted，这次验收不能
追认它，也不认证真实DIC反演／预测。
