# E019-D01-R001 — 一次合成诊断成功，图形问题使验收暂停

最新状态（2026-10-17）：V01显示验收已通过；v1.1一次独立只读算术验收
exit0，保存C1–C3账本和C0已存H/Gram核验通过，但保留C0原C/A及原Qr
未保存限制。下文旧暂停记录保留，当前结论见末节及subspace_arithmetic_evidence_review.md。

2026-10-16。用户单独批准确切命令B一次及独立只读验收；主代理原样执行
审批正文B段一次，exit0，无重试。当前是“运行成功、产物已生成、验收
未完成”，不是完整PASS_EVIDENCE，也不是将预定负控误判成运行失败。

## 执行、来源与停止位置

执行时cleanHEAD15b6e31e1bdd892fe19f8139aae8d58e74357f81；数值/测试/设计
快照8471002db09cd1cb072552b00f3fd736a607b11a。审批正文与Run副本SHA256：
ee408ccee63a9509e889421134a25bdd215ac764f473d57110dffb821096345e。
命令B先核对T001成功收据、固定11来源、线程/隔离环境及测试日志，再创建
全新Run。没有重跑测试或原E019、运行新SVD、访问真实数组/留出或修改旧产物。

本机PID89045，Wennies-MacBook-Pro-14.local；五项线程环境均1，CUDA禁用，
warnings=error。收据execution_status=succeeded、elapsed_seconds=
1.0695549999945797/60秒；软预算从模块导入前计时，不只计run函数内UTC区间。
run函数收据UTC为2026-10-16T13:09:39.678650Z–13:09:40.255668Z。
日志为空；报告记录svd_calls/eig_calls/fem_solves/array_file_inputs均0。
只使用人工常量和源码；C0一次人工薄QR，不是SVD或真实FEM求解。

主代理核对11项来源前后/当前哈希及6项产物哈希全部一致，审批副本字节
一致。随后实际PNG目视发现纵轴长标签被画布裁切，C2/C3顶部数值标注
与标题区域重叠。它是未预期的图形QA问题；发现后即停止后续验收、通知
独立审查者中止。没有修码、重绘、换图、改变阈值或重新执行B。
本次目视、说明读取及哈希检查在同一批工具返回后被主代理接收；发现问题
后未追加数值/图形检查。原分析成功收据不改为运行失败。

## 保存的数值结果（尚未独立算术验收）

这些是producer保存的合成数据，不是实测DIC或实际gesvd输出，也没有用
真实E019的4.05e-15mm去拟合扰动幅值。

| 用例 | 保存结果 | 限定解释 |
|---|---|---|
| C0人工采样A | max|HᵀA|约2.667e-17；基项4.236e-17、求值项1.707e-17 | 标量最大值不可相加作因果份额，需保留有符号账本 |
| C1解析干净基线 | Qr=r最大差0mm，原容差误差比0 | 本人工基线通过，不代表真实数据已通过 |
| C2输入扰动 | 因子重构最大差0，Qr=r最大差1.862645149230957e-9mm | 预定负控，按原向量阈值不通过 |
| C3近似因子扰动 | 因子重构最大差2.7755575615628914e-17，Qr=r差与C2相同 | 重构可过原矩阵容差而Q保持不过；仍是人为控制 |

C2/C3的原向量判据误差比均1755501.1331537713，保存p/r相同而输入A不同。
两者已有子空间分量约7.45058e-9mm，p新增求值项与r新增减法项各约
6.77626e-21mm；均来自固定人工机制。预先登记的负控不通过不是新异常，
也没有因此放宽阈值。当前停止原因是图形布局，不是这两个负控。

保存结果提示：小的输入/因子重构误差不必保证保留子空间严格保持Q；
不同上游机制可有相同p/r。但未独立完成账本复核，不能把这段自报数值
当作验收已通过，更不能据此确定真实E019的A/SVD/定义根因或修好物理模型。
原E019真实验收暂停、原阈值/失败/预测结论全部保留。

## 固定产物与完整性

Run根：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D01/S03-E019-D01-R001/`。

- analysis/execution_receipt.json SHA256：3677f36fdce41c61fd0173ae16dfecdc90ff5e0eeef61cef4acaaf220d43f48a。
- analysis/report.json：f6276a7d474cde6675d99649d8256027edea16902e7c259af2fab24c3535a689。
- analysis/summary.csv：25ae87fcb284e55ae5d8a8c452ba6dca4c0673064eef07cc24ecb9d0c49a2101。
- analysis/q_identity_ratio.png：5f37dabce7b123943e050caa554dbf61c366b365801ae9e0d40cf3a4fc500df5。
- analysis/q_identity_ratio.pdf：364777ef3964be14349658a16b5edbf4fb3355467ba3e1af3e68d790ec87b685。
- analysis/q_identity_ratio.md：3800503ad56e823dd8bf7334d47519bed47697d859754d6bccd8cd2906bc6612。
- analysis/README_analysis.md：bb61eee883229babf83d38e017cb30dfb5a82d90b955fa28ce31e525c7df733b。

原图与全部数值/收据均冻结保留，不覆盖。未运行官方sidecar/PDF检查或
为修图重算任何数据；没有外发、联网、SSH或push。

## 独立验收的实际完成范围

完整停止回复见subspace_evidence_review.md。独立Codex读取cleanHEAD、
本次receipt/report及目录清单；尚未独立算术重构或哈希核验，也未目视
原图。它按主代理发现的布局问题通知立即停止，不把主代理目视冒充自己
已检查。停止后未补查结束HEAD或追加哈希/数值/图形检查。
因此无完整独立验收结论，不能把主代理哈希核查替代该缺项。

## 下一步（尚未实施）

只建议另行准备显示布局修订与独立新图输出方案：改短/换行纵轴标签、
给标题/标注留足空间；从已有合成report读取绘图，不重算数值、重复诊断
或运行SVD。旧代码快照、数值、原图和收据不覆盖；新图器/输出另审另批。
获批后再补剩余独立只读数值与图形验收；当前不自动修图或继续验收。

### 2026-10-16：显示方案已准备，尚未实施

subspace_display_plan.md v1.1仅直读已存report的三个ratio/状态，拟独立
同级R001-V01目录出图；短换行标签、标题分区、向下数值标注、零点marker
完整性检查，不重算/重SVD或改原轴语义/阈值。独立方案审查要求补充
零点标记防裁切，修订后REVIEW_PASS；完整记录见subspace_display_review.md。
未读report数值/真实数组/留出、未改代码/测试/出图或新建输出目录。
等待用户确认方案；代码准备/静态审查与最终渲染审批仍未完成。
本条不改变前述原数值/图形验收未完成状态。

### 2026-10-16：新图器静态审查通过，尚未测试/渲染

显示方案v1.1获确认后，新增独立图器、人工单元测试与确切A/B命令。
代码/测试/设计fe190c9，命令7b8cc1e，独立只读静态REVIEW_PASS，无必改。
完整范围见subspace_display_code_review.md，待审批命令见
subspace_display_execution_approval.md。不运行任何代码/测试/出图，不读
report内容/真实数组/留出，不建T/V01目录；原图/数值/收据保持。
本轮仅静态就绪，没有运行或布局结论；下一步仅建议审批A人工测试，B另批。

### 2026-10-16：获批仅显示A人工测试一次通过

11 tests/0.001s全部通过、exit0，收据约0.2003秒/60秒（写前取样，最终预算
检查也完成），五线程1，四来源身份不变。完整subspace_display_test_results.md。
B及预检未启动、V01目录不存在；没有report/真实/留出读取或原产物修改。
此结果仅人工逻辑测试，未验证实际绘图布局，原独立数值验收仍暂停。
下一步B一次report渲染仍须单独批准，不自动推进。

### 2026-10-16：显示B另批一次出图完成，独立显示验收部分完成后暂停

新V01一次exit0、收据约8.31秒/60秒、单线程；独立核保存值/角色状态和
身份哈希，复核布局并亲看PNG：原裁切/重叠已修复，精确零点完整。
终端缓存初始化消息后核实为logging WARNING；原规则无例外，主代理
纠正此前分类并立即要求独立停验收。剩余说明/官方sidecar、PDF完整性和
结束哈希未做，无完整PASS_DISPLAY；原数值验收暂停不变。
详见subspace_display_results.md/subspace_display_evidence_review.md。
已生成图和有效检查保留，不重绘/重算/重SVD或改原产物；候选仅另批这条
确切缓存日志的预期分类及剩余只读验收，不自动执行。

### 2026-10-16：V01限定获批后独立显示验收完成

仅字体缓存这条确切logging WARNING按用户批准作为预期初始化保留。
剩余说明/官方sidecar（2图/1说明/0错误）、PDF完整性及末次哈希均通过，
无其他新异常，独立PASS_DISPLAY仅限V01。PDF未渲染或目视。
来源/产物/收据/源码保持，未重绘或重算、读取真实/留出/evidence数组。
详见subspace_display_evidence_review.md/subspace_display_results.md末节。
原D01独立算术、真实E019失败/暂停仍保持，不能用显示通过替代。

### 2026-10-16：剩余独立算术只读方案待确认

subspace_arithmetic_acceptance_plan.md v1准备了完整只读命令，未执行或
读取report数值。拟核C1–C3保存账本/原负控、来源与CSV，保留原容差；
不导入producer、不生成fixture、不分解/重绘或写冻结产物。
按保存契约C0原C/A缺失、逐分量Qr未存；不会补构造来追认全D01通过。
即便可核部分通过，也单列C0限度。方案/标量核验映射和命令待用户确认，
尚无独立静态审查或算术结果；原真实E019验收状态不变。

### 2026-10-16：算术命令v1静态审查需明确ratio路径语义

独立静态MODIFY_AND_REREVIEW仅一项必改：保存einsum ratio与fsum参考
ratio的标量比较不能当成由原mm容差直接推出，需声明额外跨路径检查及
特定失败分流，不直接判report/producer错误。没有实际验算，不能说
当前用例已失败。详见subspace_arithmetic_command_review.md。
按用户要求先报告，不改v1/阈值/操作数或C0/原Qr限制；无数值产物读取、
导入/测试/执行/真实/留出访问。原D01及真实E019数值状态均不变。

### 2026-10-17：算术命令v1.1静态复审通过，尚未执行

获批仅修订ratio跨路径语义/来源标注/专属停止分类，未改阈值、操作数、
fsum/Decimal公式或C0/原Qr限制。快照f805eab，独立REVIEW_PASS，无必改。
完整subspace_arithmetic_command_review.md；确切命令在
subspace_arithmetic_acceptance_plan.md v1.1（SHA95ce2969…）。
未运行算术/导入/测试或读数值产物，未改冻结产物；当前仅展示执行审批，
不是保存账本/真实根因已验收通过，不自动启动。

### 2026-10-17：v1.1一次独立只读算术验收完成，有限通过

用户另批确切命令，仅独立Codex执行一次；主代理未重复或复算。exit0、
无STOP/警告/traceback/重试。结果PASS_SAVED_C1_C3_ARITHMETIC_WITH_C0_LIMITATION。
输出前取样0.37604833295335993秒/60秒，stdout后预算检查亦通过；不是
最终stdout结束后的精确总耗时。五线程1，CUDA禁用，标准库/只读stdout。

已核来源/CSV、C0 H/Gram、C1–C3因子及p/r分层账本、独立Q参考及同p/r
不同A对照。三例ratio保存einsum与参考fsum比较一致，未触发专属停止；
C2/C3原Q未通过仍属负控，不误判成整次验收异常。两个因子重构最大值
与Decimal参考不是逐位相等但满足原容差，保留差值/exact_match=false。

末次固定产物/11来源/HEAD和dirty不变由同一脚本完成，没有追加补查。
实际cleanHEAD e75d3a8，已审命令f805eab / SHA95ce2969…；完整stdout与
执行范围见subspace_arithmetic_evidence_review.md。
没有重构C0原C/A、补原Qr、重跑诊断/测试/QR/SVD/求解/绘图或真实/留出
访问；原Run/V01数值和收据均未变。本次只关闭保存C1–C3可核账本，
不将D01全部原算术或真实E019根因/反演/预测判为通过，也不自动另开计算。
