# ChatGPT Pro 外部设计审核：采纳决定

日期：2026-10-08（Europe/London）。用户明确授权使用 Haofan 账户。
渠道：OpenCLI Browser Bridge；发送前 UI 显示 Pro，完整 prompt 按忽略空白的文本一致性核对。
[外部会话](https://chatgpt.com/c/6ac78d26-b514-8332-b98e-a7638ca59f3b)。

## 审核范围与结论

外部判定：**READY_WITH_CHANGES**。仅设计审核，不是 code/run/science PASS。Pro 未访问本地源码/数据，未训练、未做数值验证。最终答复已完整取得；停止生成按钮消失，A–G 各节均存在。

`design_submitted.md` 为提交前设计；`review_prompt.txt` 为完整请求；`review_raw.html` 为原始最终答复 DOM；`review_raw.md` 为从同一 DOM 提取的正文（公式保留 TeX，表格采用简单文本）。`review_capture.json` 保留正文/HTML/引用链接；`submission_receipt.json` 记录身份与状态。不将外部引用视为本地独立全文验核。

## 逐项采纳

| 意见 | 决定 | 为什么与实际修改 |
|---|---|---|
| 完整 peak→peak 路径和 accepted/commit 时序 | 采纳 | 疲劳正增量不等于峰值净差；固定模板可以编码完整处方，但不能抹去卸载/恢复。 |
| 非线性与空间平均不交换 | 采纳并纠正原稿 | 禁止从平均 alpha_bar 直接重建平均 f；尊重原生支持，A 可继续用现存均值。 |
| 投影前增量监督 | 采纳并扩展 | raw 监督用于 teacher-forced 一步分支，覆盖 d/alpha/z 截断头；滚动监督累计状态，检查梯度。 |
| P2 有效增长与假增长护栏 | 采纳为候选工程合同 | R3<=0.95、增长量比>=0.25、停滞上界0.25G_ref+2tau；实际 tau/库存未核实，不标 frozen/ready。 |
| 完整开发轨迹不参与梯度训练 | 采纳 | 3输入+3目标不跨划分；重导出/重启属于同组；旧已看过轨迹仅开发。 |
| 首版宽度64、2局部+1粗层、秩8 | 采纳为 profile 前默认值 | 减少容量和逐边内存；半径2ell与粗层256不是最优值，实际边数/连通性需检查。 |
| 首个 PINO 只加 R_u | 采纳 | 将平衡项收益与复杂相场/历史语义分开；保留完整 PINO 路线，不以偏概全。 |
| 无需复刻 staggered 次数 | 采纳 | 先学 accepted-state 映射；若引入内部试算则保证历史幂等。 |
| “最近邻反例证明缺状态” | 限定解释 | 必须匹配全部输入及路径；近邻未来差异仅是告警，可能来自裂尖敏感性。 |
| 跨分辨率、完整物理、三种子、长滚动 | 延期 | 不作为 A 的 P0/P1 阻塞条件；正式泛化阶段另行冻结。 |

没有采纳“Pro 已证明方法有效”的表述。文档修改落实了审核建议，但不是修订代码/结果的独立复核。旧 Hard5 negative / FAIL 保持。

## 下一步

`../../S09-E001/experiment.md` 保持 draft：先核实字段空间支持、peak时序、完整处方、训练/开发分组、tau/G_ref与库存；之后实现小型 GNO 的 P0/P1。当前未创建 producer Run、未运行训练。
