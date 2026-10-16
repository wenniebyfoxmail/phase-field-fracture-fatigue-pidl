# E019-D01-R001-V01 — 仅已有report的显示布局修订方案 v1.1

2026-10-16；view_id=S03-E019-D01-R001-V01；revision=v1.1。
当前仅方案与独立只读审查，不改代码、不测试、不绘图、不创建输出目录。
这是C0显示能力修复，源证据域synthetic，不是新的数值诊断或物理实验。
原R001运行成功/原图布局问题/独立验收暂停三个事实分别保留。

## 1. 唯一目的和不变项

修复原图纵轴长标签裁切、C2/C3数值标注与标题重叠，让既有三个误差比值
及原判据线完整可读。只改显示，不重新定位Q差异、不计算任何新诊断指标。
原report/CSV/PNG/PDF/说明/数值代码/测试/协议/执行收据全部保持。
新图通过只表示绘图派生物可读，不代替D01尚未完成的独立数值验收，也不
恢复真实E019验收或确认A/SVD/材料根因。不得把原有失败或预定负控改判。

## 2. 唯一数值来源与最小访问清单

唯一输入固定为：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D01/S03-E019-D01-R001/analysis/report.json`。

源report SHA256锚点（既有运行记录）：
f6276a7d474cde6675d99649d8256027edea16902e7c259af2fab24c3535a689。
未来渲染先以原字节核对锚点，再解析；写图后再核同一文件字节，不写回。

仅访问report根部domain/protocol_revision/tolerances等身份字段和cases的
case、Q_identity_ratio、Q_identity_pass、Q_identity_role、Q_identity_outcome。
要求cases顺序正好C0/C1/C2/C3；C0为not_applicable且ratio为null；C1为
clean_baseline/passed；C2/C3为预登记negative control且原判据未通过。
数值直接读取C1–C3保存的Q_identity_ratio；验证为有限非负数，不重新算
max、Qr、分子、分母、残差、分类、范数、Gram或任何分层账本。
JSON解析会读取整份合成report，但不使用evidence中的H/L/A/V/s/y/p/r，
不把它们转成数组或进行运算。精度显示格式不改变保存的原始比值。

禁止读summary.csv、旧真实E019投影/残差、prepared/solved/预测NPZ、
stage15/R003、新留出、ZIP/nodemap。数值来源绝不改成CSV或重新计算的值。
渲染只读原report；不打开原图/原收据来驱动新图，来源锚点已在本方案给出。
代码/本方案的普通字节身份可记入新渲染收据，不视作第二个数值来源。
源Run完整数值/执行链的独立验收仍属另一步，不借出图补做或扩展访问。

## 3. 独立新图器与新目录（将来另批，当前不实现）

拟另建轻量图器scripts/aa2024_qsubspace_report_view.py；不改原
aa2024_qsubspace_diagnostic.py，也不导入它或原数值runner/依赖。
未来只需标准库与Matplotlib Agg；不调用原render/run/diagnostic、pytest、
QR/SVD/eig/pinv/lstsq、FEM、拟合或任何数据生产入口。零SVD，零数值重算。
不额外生成合成数据、补投影、修正原p/r或继续原停止的算术验收。

唯一新输出根拟为独立同级派生目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D01/S03-E019-D01-R001-V01/`。

它是view派生物，不是第二次R001、R002或新的数值求解。目录存在即停，
不覆盖/清空/复用；不得向源R001目录写文件或修改原冻结产物/收据。
输出文件：q_identity_ratio.png/pdf/md、plot_values.json、render_receipt.json、
render.log（具体命令在代码准备后另审）。plot_values只复制三个保存值和
原状态/角色，不生成新指标或修正值。新receipt明确operation=
render_saved_report_only，记录源report前后SHA、view/代码身份、预算、
新图/说明/复制值哈希及布局检查结果；绝不把原运行时间或原收据重写。

## 4. 冻结的显示设计

单面板，仍只画全部C1–C3；C0标注不适用，不画成误差0。

| 项目 | 修订后定义 |
|---|---|
| 画布 | 9.6×5.4英寸；PNG170dpi、PDF同版；不用bbox_inches=tight掩盖裁切 |
| 留白 | 显式left=0.16/right=0.97/bottom=0.22/top=0.78，不做自适应多轮试排 |
| 标题 | 图级短标题置于y=0.965；短副标题置于y=0.905，与坐标区分开 |
| 标题文案 | `E019-D01 | R001 saved report | synthetic`；副标题`C2/C3: prescribed negative controls; zero SVD` |
| 纵轴标签 | `Q-identity error ratio`换行`(dimensionless)`，10pt；完整公式保留在说明中 |
| 纵轴映射 | 保留symlog、linthresh=1；显示范围固定[0,1e8]，不得负值显示或截去实际点 |
| 横轴 | C1 clean / C2 input perturbation / C3 factor perturbation，固定顺序，长标签换行 |
| 标记 | 保留C1蓝圆点#0072B2、C2/C3橙叉#D55E00；不用颜色暗示实际求解器有错 |
| 零点完整性 | C1使用clip_on=False、zorder=4（高于轴线），保持圆心在精确0；完整标记外接范围纳入画布安全检查 |
| 原判据线 | 黑虚线y=1；线内右侧直接标注`Original tolerance = 1`，不放遮挡数据的长图例 |
| 数值标注 | C1精确0仍标`0 (exact)`，点上方10pt；C2/C3按保存值.5g格式标在点下方18pt，留在轴内 |

横轴范围固定[-0.4,2.4]，字体/marker使用可读常量；标题/副标题11/10pt。
所有比值保持原值和同一映射，阈值线仍为1；仅去掉旧图自动范围产生的
无意义负值显示并增加顶部空间。源值若超出固定显示范围则停止，禁止
截点、裁值、改轴救图或自动换布局。精确0不加epsilon，不作平滑/插值。
图题和说明明确它是同一个R001保存结果的布局派生物，不是新计算结果。
允许C1圆点的图形笔画越过轴边，但不得越出画布；这不表示存在负比值，
不移动点、不加epsilon，也不改变固定轴范围。

## 5. 一次布局检查和验收标准

未来一次渲染流程内先canvas.draw取得文本及完整标记边界，再输出PNG/PDF；这只是
绘图库求布局，不是数值诊断，不调用旧图器。单次draw/save内部正常绘制
不是重跑分析；禁止循环调字体/边距、自动重绘试到通过或另开V02救结果。

输出前检查全部标题、副标题、纵轴标签、刻度/横轴标签、三个数值标注和
判据线文字及三个完整marker外接范围（包括笔画线宽）在画布内，至少2px显示安全边距；数值标注在轴内，且不与标题/
副标题或其他数值标注相交。记录检查对象、边界及是否通过到新receipt。
2px仅为新显示QA标准，不是修改E019向量/矩阵容差或原数值判据。
任何布局检查不通过、新警告、非有限/身份/字段/哈希/保存异常均立即
停止，保留新目录取证，不自动调整或重试，不改源report或旧图。

后续独立只读显示验收核对：复制值/角色/原状态与源report逐项一致，
阈值线1及symlog/精确0显示未变；实际PNG的标签和数字完整不重叠；
同名说明符合项目模板/官方sidecar检查；PDF头/EOF/pdfinfo完整性及必要
只读检查。不得为PDF检查重绘，不将PNG通过冒充PDF全部视觉已核验。
源report前后字节必须同锚点，新产物与receipt哈希一致，原目录无写入。
没有原数值独立账本验收，因此最多得出“V01显示派生物通过”，不能出具
D01整体验收通过或真实E019数值/物理结论。

## 6. 预算、审查与下一步

未来只拟一次本地单线程CPU显示操作、软60秒，覆盖导入/输入核对/布局/
导出/新文件哈希/源report再核及最终成功收据写后检查；CUDA禁用，
warnings=error，所有文件/图句柄显式关闭。未实测预算，不保证成功。
无SVD、求解、真实数组/留出、外发、联网、SSH或push。

本轮只读原布局源码、既有停止记录和规范，准备本方案；没有读取源report
数值、执行代码、导入、测试、canvas.draw、出图或创建V01。原停止记录
不删除，已有数值和图形均未改。此为排版修订，不新开数值方案或放宽门槛。

请本地独立只读Codex审查：report唯一来源/不重算、明确的新目录隔离、
显示设计/布局失败即停、原判据和负控语义不变、显示与数值验收分离。
审查同样只读方案/必要旧源码/停止记录，不读数组、不计算/试排或编辑。
审查通过后先展示给用户确认；之后才准备新图器、测试设计/确切命令和
独立静态代码审查，实际出图仍需对最终包单独批准。本轮不实施或执行。
