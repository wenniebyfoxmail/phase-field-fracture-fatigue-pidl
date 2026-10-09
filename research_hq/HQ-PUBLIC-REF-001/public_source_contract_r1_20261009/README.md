# HQ公开来源代码合同 r1

2026-10-09。本目录是可审阅的设计/辅助代码交付，不是训练runner，也不是科学资格认证。

| 角色 | 候选组 | 原图数 | 允许用途 |
|---|---:|---:|---|
| METU train | 274 | 316 | 拟训练 |
| METU validation | 59 | 62 | 仅checkpoint选择 |
| METU internal_test | 59 | 80 | 最终内部诊断 |
| BuildCrack external_diagnostic | 90候选采集族 | 358 | 最终来源外诊断 |

候选组/采集族不代表独立现场。只有角色分配，没有训练动作。未修改原始数据或上游UNASSIGNED清单，角色存于新manifest。

阅读顺序：CODE_CONTRACT_R1.md → metu_group_split_r1.csv / buildcrack_external_role_r1.csv → split_receipt.json → reconstruction_reference.py → local_check_receipt.json。

训练与推理的实现选择已写明：U-Net随机初始化、固定crop与loss、仅验证集选checkpoint、原尺寸滑窗概率平均、各来源单独评分。训练/验证上限6 GPU小时，最终推理另1小时；总7小时是合同草案的前瞻上限，不代表获准算力。r0原文保留，本r1明确细化预算。

本地实际检查：六种合成尺寸的恒定输出和逐像素恒等重建通过；NaN、越界概率、错误shape三类拒绝；458行唯一且同组不跨角色，7对已知近重复约束全部保留。不调用torch、不构建模型、不训练。这些检查不证明真实分割模型有效或生产runner正确。

仍缺完整训练/评价runner、环境与数据内容锁、正式实验归属和域映射、全代码独立审查、生产资源与执行授权。因此NOT_RUN_READY；下一步是按合同实现离线可检查runner，不能直接启动训练。

辅助代码独立审查已完成：仅上述三个Python文件获得bounded helper PASS，绑定SHA见INDEPENDENT_REVIEW_RECEIPT.md；完整合同/训练runner未获得Code Ready。
