# D14：数值耦合与机械成本修复 v6

2026-10-20，继续同owner D12/D13，不改网络、材料、mesh、目标载荷或训练方案。用户新许可原文：“同意，请按这个优先顺序推进数值求解器修复，复用现有代码，先完成实现、相关测试和必要的独立复审。保持物理接受精度和历史更新规则不变，无误后重跑”。这授权一次条件重跑，不复用R2已消费许可，不授权重跑失败后的自动第二次科学尝试。

依据：R2原trace记录第2子步9次QP、8次fresh联合检查，机械75.48秒内含LU52.81秒；Anderson候选merit9.885→6.811，31%改善因旧50%保护被拒绝，后续只用普通map。末fresh KKT_inf4.217e-7未达1e-7，Ru_L2约4.7e-15已达标。原日志、图和CSV保留在 `local_archive/research/fem_surrogate_comparison_preparation_20261020/execution_v1/timeout_diagnosis_20261020/`，旧120秒失败不改写。

## 联动实现

1. 新显式mode `projected_anderson_monotone` 使用同一fresh联合merit的严格下降保护；物理passed优先接受，未passed的trial只有merit严格小于保存的baseline才保留。原feasible projection/stable-free/trust/condition保护不变。真实proposal总数最多3，rejection上限3；reject恢复完整baseline d/u/LU/domain并清空窗口，但一次reject不会永久禁用，需重新积累两次map才再提议。不是将31%候选直接视为物理接受，也不承诺此策略实测更快。
2. 同一个完整当前K/rhs，旧LU仅为GMRES预条件器。restart20、maxiter4、callback_type=pr_norm，最多80次inner迭代；检查真实未预条件残差和非有限值。atol为原force tolerance×0.1×min(force_scale,||rhs||)，同时覆盖原绝对/相对精度。未收敛或真实残差不达标仅在该机械调用内重新分解当前K一次；坏pivot/非有限值/期限/证据写入失败仍停止，不当作可救的trial rejection。
3. GMRES成功不得将old LU标为当前精确因子；mesh/material由workspace固定，free-DOF域/矩阵完整字节参与exact key和预条件器域检查。Anderson snapshot/restore包含factor_domain。所有新调用记录迭代/当前K矩阵乘/预条件器次数、factor/refactor及耗时。
4. 中间迭代pivot资格可延后，但最终接受态仍必须对当前u/d的K做fresh装配并核真实LU/pivot≥1e-14；仅完全相同current CSC/free key才复用已有精确因子。不能用旧P的pivot证明新K健康。原独立legacy force审查、节点KKT/投影、Ru/联合L2/界/疲劳fixed-point全部保留，历史与D13 f_solve/f_commit证据和CAS一次提交不变。

## 工程时限与预算

新revision `coupled-recycle-v6` 将单物理子步工程保护前瞻设为300秒，而非把120秒当物理标准。此值只给修复后内层/外层的有界运行余量，不是已测收敛时间，不以单纯延时声称修复。所有三臂共用同策略/时限；原120秒的R2源、卡、终态与负结果保留。card validator仅在本revision允许300，所有物理settings精确保持原值；worker/guardian从同卡取限时，日志、回退不能重置起点。

原全局136hosth/2176分配coreh、≤16核、12GPUh（fit6/hybrid6）、120hosth数值工作总上限、各标签/参考/经典phase20hosth、共享回放/分析4h、RAM64GiB、VRAM上限24GiB及128+128GiB存储不增。CPU轨迹仍需平均≤120秒、hybrid需平均≤36秒。旧R2成本/接受和失败尝试全部单列，fit尚未开始；本次新许可明确授予一次完整3600子步重跑计划，不把既往失败步数从历史删除或声称累计只有3600步。若本次首个科学失败即停，不自动再次运行。

前置只读/零启动机械检查最多2轮、合计≤120秒，计原预算；已知资源未准备好属于not ready，未知spawn先查收据/进程，不能重编号绕过。producer固定GPUServer8/drtao/GPU5原UUID，不换机不改系统环境。复用已留存输入和OSQP；新fresh runroot，不热换R2或D13其他卡。

## 测试与科学边界

已先跑140项人工回归（含新修复测试）通过3.72秒，随后新增300秒/物理阈值不变两项定向检查：12项v6检查通过0.69秒。此前一项旧RSS故障测试隐含sandbox可读RSS而失败；已改成受控已观测RSS替身以验证失败保留峰值，生产缺测仍为None，不写假零。没有项目数组/FEM/训练测试。

重点覆盖：31%候选strict-progress/相等拒绝与拒绝后再积累、stale精确key不冒用、新free域拒复用、GMRES info0但真实残差错/不收敛refactor、非有限直接停、奇异一致矩阵不能借旧健康pivot、最终证书失败不输出proposal、人工f<1从同old态构造并一次提交D13字段证据、300秒deadline不因日志重置及新卡不得放宽物理精度。必要独立复审以准确源/卡为准。通过测试和代码复审不证明真实大网格收敛或在线收益；实际完整比较仍按原判据与自身历史评分。
