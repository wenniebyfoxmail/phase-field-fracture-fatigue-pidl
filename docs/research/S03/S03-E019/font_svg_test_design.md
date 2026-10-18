# F01独立SVG图器：纯人工测试设计 v1

2026-10-18，Europe/London。用户仅批准准备代码/测试设计/命令与只读代码审查。
本轮未运行Python、导入、语法/AST执行检查、test discovery、测试、数组读取或
图器。下述40项为源码rg计数，不是40/40通过。

## 一个问题与边界

D2：独立显示能否只消费已有值，不再依赖Matplotlib/字体初始化或数值分解？
只支持synthetic显示接口和工具能力，不支持数值正确、物理反演或未来预测。
原F01方案、G01停止审查与旧65回归不变结论复用；这40项不是重跑旧包。

新增scripts/aa2024_saved_svg.py、test_aa2024_saved_svg.py；共享G01 guard不改。
旧七源码逐字节不变。SVG标准库ElementTree生成，NumPy仅精选读取/显示映射；
不导入Matplotlib/SciPy/旧producer或verifier，不出PNG/PDF或调用外部转换器。

## 40个人工用例（按源码顺序列组）

| 组／数目 | 人工输入与检查 | 不能代替 |
|---|---|---|
| 1–9，9项 | 三点小数组的显示除法；生产默认648形状；键/shape/dtype/有限性/scale正性/坐标范围 | B003六成员实际可读性或数据身份 |
| 10–17，8项 | schema、三臂顺序/数量、保存标量有限非负且非bool、共同J_Q、显示堆叠溢出 | 原平方账本复算或数值容差验收 |
| 18–22，5项 | 显示除法下溢负控；输入不改写；零值/端点/越界色标 | 一般数值模型及完整浮点证书 |
| 23–26，4项 | 内存SVG树所有点/面板、共享色标、等比例且y向上、全零显示范围 | 浏览器字体与实际视觉布局验收 |
| 27–30，4项 | 已保存J_k直接呈现而非由其他值重算、全零轴、XML转义、同stem说明边界 | 原论文/原图像素等价或B003完成 |
| 31–40，10项 | JSON重复键/NaN、原定60s阈值、内存Fake NPZ只访问六成员、分解禁止入口、import fence、精确权限/路径及源AST检查 | 恶意任意运行时篡改/系统调用全进程追踪 |

人工fixture只在内存：3点、四个6维残差、三臂保存标量。故意不满足J_k=J_Q+gap²
也可作显示输入，以证明图器未暗中重算或接纳账本。SVG只在内存解析，不写出、
显示或打开SVG，不创建输出/缓存/临时目录。Fake NPZ为自建内存容器，
字符串memory-only-fake.npz从不打开；np.load在整个人工套件禁止真实读取。
AST检查仅在未来获批A中读取新图器源文件；本轮不执行AST。

命令A启用G01（CLI启动、第三方依赖前），禁止Matplotlib/SciPy/旧producer/
verifier的导入；真实NumPy.linalg分解/求解入口均patch为Stop，测试只断言
守卫拒绝，不实际分解。np.errstate(all='raise')和-W error保持。
命名assertRaises负控不是新警告豁免；未复跑G01子进程包或旧65项。

整个人工命令从首个time导入后START计时，含其余导入、Git/三源码身份、40项、
末次身份/stdout后检查；>=60即不完成。unittest failfast=True，任何非预期
失败/警告即停、不skip/补跑或重试，额外检查实际testsRun=40、无skipped、exit0。
只允许源码/标准依赖/Git读取；无B003哈希或数组/report/真实/留出访问。

## 未来B接口（本轮不读）

独立synthetic-only白名单固定：
input=/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03/S03-E019-D03-B003；
output=/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001。
必须显式--allow-unaccepted-synthetic。仅certificate.npz及report.json；
NPZ消费source_xy、scale、r、old_r、proxy_r、intact_r，不枚举或解码其余成员。
JSON必须整体解析，但只消费schema/rows，拒绝非有限常数和重复键。
两文件运行前后sha256/大小/设备/inode/mtime_ns核对只建立当前读取一致性，
不认证历史生成。无B003执行/完成收据不能通过后续hash弥补。

显示只做r/scale、共享颜色范围、坐标/颜色线性映射及柱图的显示几何。
不用新的Q/p/r/Gram/范数或参考乘积，不比较或重算平方账本，不评原容差。
显示的+/-1e-15mm与1e-18mm²全零范围仅轴/色标，不是阈值更改。

生成独立新目录的residuals.svg/md、square_ledger.svg/md，九/三臂等原物理
判据不放进图器验收。四派生文件与空runtime_guard_events.log哈希写入
derived_receipt.json，derived_completion.json只绑定派生收据。所有标签明确
B003 INCOMPLETE/UNACCEPTED、synthetic-only。新时钟60秒不回填旧B003预算。
普通异常可能留下display_failure.json；软超时、初始化或G01 fatal可能无
失败收据，缺收据不重试，任何外部非零退出或事件均优先于派生completion。

SVG采用11-stop RdBu_r-style RGB线性显示配色，与原图同色系/同量纲，非
Matplotlib像素复刻。SVG文字仍由查看器字体呈现；代码/内存XML检查不能宣称
布局无重叠、字体等价或图形独立验收通过，渲染/PNG/PDF转换均另批。

## 执行顺序

本轮静态代码审查通过→展示A与后续B的分立确切命令→用户先批A一次。
A若成功才另行准备/复核B输入权限、新鲜目录与执行批准；A不自动启动B。
本轮不运行预检Python/AST/import、测试、B、SVD/QR或独立验收，不读产物。
任何科学判据、数据或旧结果不因该显示代码改变。
