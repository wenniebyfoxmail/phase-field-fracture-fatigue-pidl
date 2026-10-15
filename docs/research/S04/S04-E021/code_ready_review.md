# E021 Code Ready 审查（2026-10-15）

结论：**CODE READY PASS**，仅绑定科学源码 `98c620637b2b2ef06ec86983220a4e7f9f1053b7`，协议 `20261015-r1-coordinate-preconditioning`。由用户指定的独立 Codex subagent 审查；不是外部 Pro 评审，也不是生产启动批准。

首轮源码 `9b627979d2f30f196e54d011c0afaeef93bc1bfa` 为 NO-GO：候选 strain、ρ_u、BC 未独立重算，错误指标配合一致布尔值及有效文件哈希仍能被接受。修复仅涉及 E021；从 checkpoint 重载核验后的 UV 重算全部最终指标，要求同一字段集合、严格布尔值及既有 `rel_tol=1e-12 / abs_tol=1e-14` 数值容差。原 E019/E020 源码和历史结论不变。

独立复审重跑 **162 项非训练检查，全部通过，无跳过，212.99 秒**；首轮相同多字段篡改被明确拒绝，错误为 `candidate metric mismatch: strain_error_norm`。另有开发者针对性 49 项检查通过（147.94 秒）。临时合成完成记录仅用于解码器测试，未执行候选训练或参数 optimizer 更新。三态真实初始资产、完整采样流、坐标映射及原生 LR 元数据回放的准备记录见 [implementation.md](implementation.md)。

审查确认实际更新 LR 的索引与原 E019 原生调度一致；10000 次新更新与历史 backbone 预算分列，E019 对照不重训。配对身份、冻结模型、物理窗口、预更新文件、数值停止及禁止自动重试规则均有检查。主目标与损伤改善／背景保留分别汇总，缺失和无效行不能当成完成结果。

原始记录位于项目根 `local_archive/experiments/S04-E021/codex_subagent_review_v1/` 与 `codex_subagent_review_v2/`；全文、独立测试和篡改复现的 SHA-256／大小见 [review_evidence_manifest.json](review_evidence_manifest.json)。首次 NO-GO 保留。

尚未验证正式 Taobo Torch2.7/CUDA 环境、实际训练更新、生产归档和最终科学效果。Mac Torch2.11 的元数据回放不替代生产预检，严格跨平台 ρ_u 例外未放宽。下一步可准备绑定上述源码的三态生产方案与启动脚本；传输、预检及启动须对具体方案取得用户批准。本轮未 SSH、上传、push、外发或训练。
