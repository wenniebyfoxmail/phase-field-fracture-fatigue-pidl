# E019-D01-R001-V01 — 新图器测试设计（未运行）

2026-10-16；对应已确认显示方案v1.1。只准备实现与静态审查，不测试/导入/
py_compile/AST执行/bash-n或出图，也不读取已有report内容。

## 边界与对象

scripts/aa2024_qsubspace_report_view.py独立于原producer，只有标准库及延迟
导入的Matplotlib Agg。主入口拒绝直接运行，只允许已审预算/身份launcher。
不读取真实/留出，也不导入原producer或调用QR/SVD/任何诊断算术。
source report固定字节SHA，C1–C3保存ratio和状态直接复制；C0不作0处理。
允许layout所需坐标/marker几何计算、标量schema/range验证和哈希，不算Q、
残差、范数或任何新数值诊断。JSON会解析整份合成report，不使用evidence。

新view目录R001-V01，任何已存在目录均停止；源R001不写。
新增基础设施仅限新view目录内Matplotlib字体缓存.mplconfig、.cache，
不作为科学产物。PNG/PDF/说明/plot_values/render_receipt/render.log按方案保存。
rendered收据仅表示导出成功，实际独立图形/sidecar/PDF验收另行只读完成；
不能称D01数值验收通过。失败产物只作取证，禁止重试/换目录救图。

## A — 人工单元测试，未来另批

tests/test_aa2024_qsubspace_report_view.py使用unittest，不用pytest/plugin/
conftest；11个test方法含subtests，不预报通过数量或实际执行时间。
人工report只含比值0和2，不调用真实report/旧诊断或Matplotlib/canvas。
验证仅schema/copy、原状态/阈值不变、非有限/类型/范围拒绝、C0非零处理、
evidence访问哨兵、人工矩形边界/重叠/零点跨轴边、人工临时文件的哈希/
排除软链/独占写入和sidecar内容。只在新的代码检查目录内创建临时玩具文件。

单线程CPU，隔离Python -I -B -Werror，单独60秒预算，failfast。
新目录local_archive/code_checks/S03-E019-D01-V01-T001；存在即停。
launcher前后核对固定源码清单与已审git快照，收据记录日志SHA、身份和预算。
任一非预期失败立即停止，不修正后自动重跑，不进入B。
这些单元测试不覆盖真实Matplotlib导入/渲染/字体/实际布局或预算可行性。

## B — 仅保存report的一次渲染，A通过后仍另批

先核对新A成功收据/固定源码清单/测试日志，不接受收据自报的任意路径。
新目录由图器在来源与schema通过后独占创建，不向原目录输出。
所有五线程为1、CUDA为空、warnings=error；Python启动后即激活60秒signal，
覆盖launcher/source检查、stdlib与Matplotlib导入、source读取、layout、导出、
哈希和新收据最终读回。超时/新警告/任何异常立即结束，保留新目录，不重试。
每次只一次显式canvas.draw；savefig内部正常绘制不视作重算，不自动试排。

布局固定按v1.1：9.6×5.4、170dpi、预设留白/字体/颜色、symlog、阈值线1、
精确0/C1完整marker、C2/C3向下18pt标注。完整marker含线宽检查画布安全距，
C2/C3还须全在axes内；文本范围/数值在轴内及标题/数值互不交叠均检查。
任何布局不满足停止，不调整字体、轴限、值、epsilon或自动另开V02。

## 后续独立验收（本轮不执行）

1. 固定source前后SHA、代码/方案字节与新receipt一致；原产物不覆盖。
2. 新plot_values与源report允许字段直接一致，保存角色/状态保持；不验算旧Q。
3. 实际PNG目视标签/数值/marker/阈值与图说明，官方sidecar检查。
4. PDF头/EOF/pdfinfo，不重新绘制；没有PDF视觉检查时明确其限度。
5. 先异常即停，不继续补查，不把显示就绪写成原数值/真实根因结论。

本轮只执行源码/文档字节检查及独立静态审查；A/B均待批准。
