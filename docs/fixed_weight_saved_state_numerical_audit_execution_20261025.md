# U0.115 / U0.125 保存态数值审计执行记录

日期：2026-10-25，Europe/London。Owner：`fixed-weight-learning`。

## 范围与边界

本记录覆盖既有 U0.115（训练）和 U0.125（开发验证）档案的一次
**保存态重组审计**。工作只读取已封存的原始档案，以同一已锁定 MEX
接口重组每一个相邻物理转移；没有启动训练、FEM 求解或新工况生成，也
没有改动原始档案、修剪 H/q，或放宽任何验收阈值。

审计使用的是 `862992a60edc7f59335365beacb5c71fc8592a7a` 源快照和
`47cb9c41fa8d4cec03d9088e4aba720365f987bde82204d4d30b27b51373e051`
审计包。它审计最终保存状态，不能回溯原求解器的 Newton 或 stagger
迭代历史。

## 写入回执的修复与证据保全

R004、R005、R006、R007 的结果目录均保留。它们分别记录了 CSV 显示值
再解析、五个物理转移与六位置日程混淆、计算完成但 JSON 回执损坏，以及
Windows 参数传输失败；没有删除或覆盖其中任何一个结果。

R006 的计算本身已经完成，但 MATLAB 的 `jsonencode(...) + newline` 将
字符做了逐元素数值加法，写出的字节不是 JSON。审计写入器现以
`sprintf('%s\\n', jsonencode(...))` 生成文本，并以 UTF-8、无 BOM 的
`fprintf` 写入。R007 的独立编码 smoke 验证了这个写入器；其完整控制器
在 Windows/Python 双引号传输层失败，未接触档案。R008 是修复后新的、
单独命名的执行根，未把后验修复的产物混入 R006。

## R008 可复核执行

远端根：`C:\\q4runs\\FW-SAVED-STATE-NUMERICAL-AUDIT-20261025-R008`。
完整控制器 `FW-SavedState-Audit-R008-20261025` 于
2026-10-25T19:58:31Z 至 20:15:42Z 以退出码 0 完成，stdout 仅报告
`completed_saved_state_audit`，stderr 为空。

| 产物 | SHA-256 |
|---|---|
| `preflight.json` | `bf72a9daf9de4a903946f56e6771a380c7bc8438c3ed5437d8273ed349bbd4f5` |
| `saved_state_audit_receipt.json` | `da1b8a4ba3a86d55c756a4b409566e173b6310aac4d86661962ddd3851b8c174` |
| `saved_state_transition_metrics.csv` | `c18c4f1c9151c55b341b2d0f0525e5116cd6cb1322671f3105697b7edd2ae271` |

随后以独立的 Python 后验验证器（包清单
`21eb4251f42869fa5343659e03f6674ddab2ea7e79357a2b407a40067a098df5`）在
远端完成一次只读核验，退出码 0。以上三个文件还被下载为字节相同的本地
证据副本，在迁移位置再次通过该验证器。审计包 6/6、验证器 3/3 文件哈希
检查均通过；验证器的 canonical worktree 单元测试为 11/11 通过。临时迁移
副本中有一项单测依赖相邻的 canonical 审计包路径，因此单测套件本身还不是
完全自包含的 relocation 测试；实际 relocation 验证器已对 R008 证据成功
运行，此观察不改变本记录的证据结论。

## 契约结果

- 物理转移总数为 **880 = 515（U0.115）+ 365（U0.125）**；两档案的
  sealed、source、mesh/material 绑定、清单与 payload 唯一性均通过。
- 初态均匹配受约束的
  `post_clip_zero_load_recovery_pre_cycle_committed`：`u=0`、`H/alpha/q=0`、
  `f=1`、损伤位于单位区间、退化能量为零，且零载荷元数据精确一致。这是
  档案契约初态，不是一次新求解的全局平衡证明。
- 所有 880 个转移均有 `history_exact=true`；用前一接受状态和当前保存
  `u,d` 重建的 AMOR 能量、AT1 相场/历史更新与第二次 history commit 的
  最大分量误差均为零。载荷日程以五个物理增量对齐六位置表的 `s01..s05`，
  保留二进制实际 `effective_uy` 值；未以格式化的 `.25` 替换实际值。
- 原始 H 和 q 不做截断。共保留 5 个 H 与 5 个 q 的极微小负值，最小为
  `-3.52410948526606e-72`：U0.115 的 `c0058_s04→s05`（1 个）与
  `c0087_s04→s05`（2 个），以及 U0.125 的 `c0058_s04→s05`（2 个）。
  它们沿实际 MEX 重组路径可复现；现有静态证书把它们解释为刚体平移下的
  binary64 舍入残留。该结果不把静态解释升级为源代码到运行时 MEX 二进制
  等价证明。
- 记录的自由残差和投影 KKT 数值仅是审计观测，未建立新的接受阈值，也不以
  它们作数值收敛结论。

## 准入结论与未建立的资格

U0.115 与 U0.125 **准入“开发保存态数值审计证据层”**：它们可作为当前
固定网格、五子步、既有档案的原始状态/历史一致性证据。回执明确保留
`numerical_admission_decision=not_evaluated` 和
`physical_conclusion=not_established`，因此这个结论不升级为数值 teacher
资格、严格独立测试或物理基准资格。

仍缺的决定性证据是：原始 Newton 残差历史、stagger 固定点和 `Δd` 历史、
源代码到实际 MEX 二进制的等价性、同设置的网格/载荷离散敏感性，以及材料、
试件、预裂纹、边界和载荷历史都匹配的独立反力/位移和裂缝演化实验观测。

独立测试也尚未建立：U0.1175 因历史 partial/result 元数据暴露，不能作为
严格盲测；U0.1225 仍只有未激活的 custody 准备包，缺独立 custodian、ACL
与 scorer-only 释放证据。最小补齐方案及其边界见
[`fixed_weight_reference_gaps_20261023.md`](fixed_weight_reference_gaps_20261023.md)。
