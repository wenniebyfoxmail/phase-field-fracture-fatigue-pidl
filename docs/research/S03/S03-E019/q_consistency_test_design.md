# E019-D02 v0.1 — 实现约定与合成测试设计（未运行）

2026-10-17；用户确认v0.1方向，Pro PASS_PLAN与本地PASS_STATIC_PLAN后准备。
本文件落实审查明确化，不修改原方案、旧源码或冻结产物。当前不运行
Python导入、AST/py_compile、bash-n、测试、诊断、QR/SVD或绘图，不读数值归档。

## 代码及唯一数据流

- scripts/aa2024_qconsistent_repair.py：独立新实现，只导入NumPy/SciPy及标准库，
  不导入旧producer。fixture仅构造原C1–C3人工常量；不得有文件型数值入口。
- repair(H,Lr,y)：固定16×3、16×5、16×1；仅这些输入，无A/s/V/clean/oracle。
  H/y接纳检查只读；候选流B=QLr一次，scipy.linalg.qr(mode=economic,
  pivoting=False,check_finite=True)一次；正对角规范、零/非有限拒绝；
  eta=max行和|I−T|≤1/2硬保护，不套isclose；p=U(Uᵀy)，r=p−y。
- 其余Q调用只作检查，不回写任何候选数组；不重复QR、改目标、归一化输入
  Lt、删除/旋转选模式或把U拼成原A的新SVD。
- audit_case另接收clean作参考，存五个b_j=2^-8 clean[:,j]的UUᵀb_j=b_j、
  加法/交叉项/平方分解。p*=2^-8(l1+l5)、r*=−2^-12g；解析平方参考为
  floor=2^-24、gap=(j=1/5时1，否则3)*2^-16、total=gap+2^-24，单位mm²。
  这些是预定义公式，不是当前测得值，不替换候选输出。
- 原路径C1 Q通过、C2/C3 Q未通过的预声明负控继续记录；C2/C3 A不同、
  Lr/y与原p/r相同检查保留，不作为两套独立数值压力输入。

## 单位、参考、分类

原rtol1e-12、matrix/vector/square atol1e-12/1e-15mm/1e-18mm²不变。
矩阵QU=U用matrix，Qy/Qp/Qr、Uᵀr、五探针像内差和残差加法用vector，
欧氏和平方/交叉项/勾股用square。新eta规则不是原tau或原A条件数。
C1新旧结果按容差比较，不要求经QR后逐字节相同。

检查ratio统一为max逐分量 abs(a−ref)/(atol+rtol*abs(ref))，图取r的
producer-einsum路径，不换成全局归一化ratio。Q检查同时保存实际Qr与
同一实际float输入精确导入Decimal80的参考Qr、fsum参考Qr；fsum的输入
项为先完成float乘积的值。路径不同，不强加“原向量接近蕴含ratio标量
接近”的推论。对实际U的完整Decimal投影、分步float投影及解析p*分开。
参考只能核对，不能修正候选或作为重试路径。

主要标准为三例新p/r符合解析参考，此外必须满足原负控、五维秩保护、
重构/正交/Q一致性、五方向像内检查及平方分解，不能只展示Q改善。
Q求值路径接近/通不过不一致或p/r求值路径超原容差，按
STOP_REFERENCE_PATH_DIFFERENCE_UNRESOLVED停，不自动判旧报告错误，也
不宣告修复成功；新候选Q、解析投影、eta/模式或原负控异常分别明确分类。

## A — 人工单元测试（待单独批准）

tests/test_aa2024_qconsistent_repair.py：17个unittest test方法，含subtests。
此数是静态方法数，不是通过数；当前没有语法、导入、运行或预算实测。
测试不导入Matplotlib、不读原report/资产，不调用完整diagnose/render/launcher。
仅从标准库启动器模块导入WarningStop类，不调用其main；在数值模块导入前
为测试子进程安装同一logging.WARNING及以上即异常的处理器，字体初始化
许可窗口始终关闭。人工LogRecord仅核对处理器拒绝行为，不发布真实警告。
真实QR全部禁用；候选数据流测试用预先给定U/T作为QR返回stub，不冒充
SciPy分解已通过。零实际QR、零SVD/eig/pinv/lstsq/cond/数值秩；算法不调用逆。

覆盖人工定义/机制区别/旧负控；候选不改输入且QR接收单次QLr；符号规范；
零对角、四列、非有限、非法case拒绝；eta行和vs最大元素、1/2严格边界；
原三类容差；五探针/分解；一个y仍投对但未激发方向被替换时探针拒绝；
非Q目标先拒绝不修写；Decimal精确导入与fsum乘积语义；禁止API哨兵已布置。
不调用被禁止API“测试拦截”，保持实际调用计数0。failfast首个非预期失败即停。

独占新目录local_archive/code_checks/S03-E019-D02-T001，存在或软链即停。
仅写tests.log和test_receipt.json，固定源码清单前后与已审commit逐字节比较；
隔离Python -I -B -W error、CPU五线程变量均1、CUDA空、单独60秒。
launcher的超时只作用于自己启动的测试子进程，不重试、不自动进入B。

## B — 三例主诊断（A通过后仍待单独批准）

先核对同一快照A成功收据、固定源码清单前后SHA、测试日志SHA及CPU/预算身份，
不从收据接受任意来源路径。新目录固定：
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D02/S03-E019-D02-R001。
目录存在或祖先软链即停，不换RunID、覆盖或自动重试。

仅C1–C3固定顺序，每例一次16×5真实薄QR，共3次；0次SVD/其他谱分解、
pinv/lstsq/数值秩/cond/FEM/训练；数值算法不调用逆，绘图内部正常二维仿射
坐标变换不属于数值修复或分解。NumPy/SciPy禁止API及数组读入口
运行时设拒绝哨兵，并保存实际受控API计数；这些不是全进程独立行为认证。
旧producer不导入，只核源码字节。绝不读取旧数值report、真实数组或留出。

成功产物：report.json（人工A/s/V/c/a、H/Lr/y、B/U/T、新旧p/r、解析参考、
实际U的Decimal投影、各Q求值及五探针完整操作数和检查），summary.csv，
q_identity_ratio.png/.pdf/.md，execution_receipt.json。每文件独占创建；
本次自己新建的收据允许在迟发失败时改为failed，不修改任何旧收据。

图固定10.8×5.8英寸/170dpi、所有3例、同一尺度symlog线性区≤1、[0,1e8]，
旧橙叉/新蓝圆、阈值1、精确零不加epsilon、标题与数值分开；同名说明保存
完整数值与来源/局限。绘图只使用本次已评分report。画布文本越界即停，
不试排/调字体或轴限；重叠及marker可读性仍需之后独立目视验收。

B独立60秒从launcher START覆盖源码/测试身份核对、导入、数值/参考、绘图、
保存/哈希/成功收据读回及最终检查；信号异常停止，原生调用未返回时仍可能
稍后才能处理信号，不保证精确硬杀墙钟上限，返回后超时不能接纳成功。
其他警告/异常立即停；部分新文件只作取证，不作部分通过或自动重试。

运行时Python warnings均error。唯一拟预声明的非失败初始化日志是：
logger matplotlib.font_manager、level WARNING、完整正文恰为
`Matplotlib is building the font cache; this may take a moment.`
仅首次导入绘图栈窗口内最多一次，完整存入新收据；无数值阈值豁免。
它是logging记录而非Python warning；第二次、其他正文/级别/来源/时段均停。
此操作约定随B执行包供用户审批，不继承旧V01的事后许可；当前不触发缓存。
所有字体/.cache写入本次新R001目录，不写旧显示目录。

## 后续只读验收及结果用途（本轮不执行）

独立验收只用新保存操作数，不再QR/SVD，核身份/五模式/原容差/参考路径、
五方向与平方关系、原负控/来源区别，并目视PNG/核同名说明及PDF完整性。
保存足够中间量，不重现原C0缺失C/A问题。不得因图形或算术不通过而自动
重算。静态代码通过不等于测试通过、实际QR可用或数值证据通过。

若合成通过，仅准备另批的训练侧真实数值复核。真实A/Lr缺失、不确认根因；
本分支不能直接恢复旧E019，不能读取stage15或将其当未见验证，不增加q。
