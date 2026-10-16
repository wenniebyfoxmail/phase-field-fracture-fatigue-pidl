# 9984226：晚期误差定位核心及生成表核验（部分完成）

2026-10-16 Europe/London。唯一执行／记录方：原残差主对话
01a1131d-017c-7b03-a95a-ad73ba8fcc9c。没有向方法对话发消息或启动第二项工作。
其他对话、E022、旧拟合／重放代码和记录保留。未读取真实CSV、真实控制JSON、
模型、轨迹、数组或确认数据；未真实分析、拟合、重放、SSH或GPU计算。

## 实现范围与尚未完成项

沿用9984226方案，不改原公式、分层、容差或决策顺序。专用工作树
`codex/s04-late-regression-plan-20261016`，base46ca50c；原方案9984226保持不动。
工作树没有local_archive链接或科学payload。

| 文件 | 范围 |
|---|---|
| SENS_tensile/s04_late_attribution.py | 纯标量CSV文本解析、357前缀验证、u011晚期81行分解、k50／计数／固定分支、生成表报告 |
| SENS_tensile/s04_late_attribution_guard.py | 固定生成核验入口；CPU1、60秒／512MiB／5MiB采样监督，独占新目录，无重试／任意命令入口 |
| SENS_tensile/s04_late_attribution_checks.py | 生成CSV及无真实进程的触限mock；禁止科学文件open及旧runner导入 |

核心不读取路径或加载模型，只接收调用者已提供的六列标量；只分解u011 C41–121。
原cycle_weight仅校验，晚期均值按1/81，不重算其他三case或整体R/G/Q。
真实已知ratio在代码中保留常量，生成测试用自己的解析期望值，不用真实数值冒充验证。
有符号误差、改善抵消、tau持平带、并列按cycle、k50=1优先及多数退化计数均保留。
S_plus不可识别时不制造比例或进一步归因；C121仅标记拟核查来源，不剔除。

**这不是完整真实runner交付，也未达到真实分析可运行状态。** 本轮未获准打开四份真实
白名单源，因此未猜测replay verification的未公开JSON结构；真实四源／metadata绑定、
背景均值摘录、执行批准交接和精确运行卡尚未实现／核验。真实CLI无入口，报告函数也拒绝
real模式。将来须先明确并独立审核这些绑定，再另行审批真实分析；不能仅换路径运行。
生成mock仅测工程监督器，不代替真实来源／授权交接测试。独立代码审核应明确此范围缺口，
不能把核心审核认可写成整条真实链已就绪。

## 唯一一次生成核验及停止

runtime：65f416e022744711362a01c2dd6ae136e89de585，启动时三源码干净。
cwd：本专用工作树；Python `/Users/wenxiaofang/miniconda3/bin/python3`。
精确调用：

```bash
PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_late_attribution_guard.py --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering/late-attribution-20261016-9984226
```

唯一工程输出位置为命令中的目录，不是新科学Run或执行授权。guard78452 → worker78470，
UTC2026-10-16T12:11:22.171715+00:00启动；worker退出1，终态后两PID均不在。
没有第二次调用、重试或扩大预算。

| 项 | 实际记录 | 说明 |
|---|---:|---|
| 终态 | CHILD_FAILED | 核验未全部完成，不能写全部通过 |
| 计时 | 8.683296209秒 | 上限60秒，未触限 |
| 聚合采样RSS | 265830400 bytes，253.516MiB | 上限512MiB；不是OS硬峰值保证 |
| receipt前输出 | 247778 bytes | 含生成CSV／图／字体缓存／日志 |
| receipt后输出 | 248926 bytes，约0.237MiB | 共8文件，含1148-byte receipt，低于5MiB |

回溯停在checks的原line255：`source.read_text() == text`。
生成CSV由csv.DictWriter默认写CRLF；read_text默认通用换行转换为LF，原始字符串仍含CRLF，
因此此文本比较不等，并不证明文件被改。紧邻前一条size／mtime／mode断言已经通过。
已将其修正为 `source.read_bytes() == text.encode('utf-8')`，直接比较字节，不再混用换行口径。
**修正后只做AST语法与git diff空白检查，未重跑生成核验。** 原receipt／失败记录不改。

按源代码控制流及回溯，异常前已走过生成数值分支、输入错误拒绝、C121标记及报告生成；
但没有最终checks.json，不能把它们升级为一套已完成且有完整回执的核验。
尤其后置六类mock监督路径、精确预算边界和复用拒绝断言没有执行，应明确标为未核验，
不能以测试已编写代替测试通过。没有做真实资源压力测试。

## 生成图及只读留存

现有部分输出8文件与目录已移除写权限，保留失败现场；未改旧科学输入／输出权限，未新增数据哈希。
主对话仅查看本次生成PNG、工程日志、receipt及元数据，没有查看科学归档内容。
图为generated_report/diagnostic.png；CSV与summary同时保留，但只能作为未完成核验的生成例子。
已目检：两面板非空、81周期／正负差额／零线／50%／k50清楚，标签无遮挡；醒目标为
GENERATED ENGINEERING ONLY与非物理归因。图内k50=21不是U0.11真实数据的结果。
README说明MSE可加、RMSE百分比不可线性分摊、来源和禁止结论。
research-figure-workflow只影响本生成示例标注与目检；PIDL闸门使工程完成度、真实链就绪与科学结论分开。

## 下一步及协作

本轮停止核验，不自动补跑。仅准备精确提交的独立代码审核请求，待人方批准发送；
由方法对话只读审核心、未重测的换行修正和监督器，指出尚缺的源绑定／核验，不启动作业。
审核之后再由用户决定是否批准一次新的生成核验与真实适配准备；不是直接批准真实分析。
本对话唯一更新Obsidian／Roadmap，避免双写。确认数据关闭，S04-E017／多目标／NN暂缓。
原U0.11晚期+1.6083%、整体Q和E021科学结论均保持，不因生成表或代码审核改变。

## 2026-10-16 后追加：监督器修订候选，仅静态检查

用户批准13db6f2审核结果所列局部修订与新生成核验卡准备；未批准执行。
原65f416e工程失败与0f10c6a换行修正的未重测状态保持，旧目录及8文件不改。
本轮在同一干净专用工作树修改guard／checks，不改core、9984226方案或旧科学结论。

- Git身份调用、输出预留、日志打开和worker启动纳入异常处理；Git子调用最多2秒，
  三源码必须已跟踪、干净且与显式expected-commit一致，冻结方案也不得偏移。
  允许后续仅文档提交，记录reviewed code与checkout两个身份；这是代码互锁，不替代人方批准。
- 新候选身份S04-E021-LATE-ENG-R002，只接受固定新目录late-attribution-20261016-R002，
  禁止旧目录、任意路径、已存在目录或错误attempt；未创建新输出、授权或Run receipt。
- 以primary_reason保存首次失败；terminal_caps单列，不把CHILD_FAILED覆盖成笼统终态触限。
  worker退出0之外还需完整生成checks标记，而不是只检查文件存在。
- 只清理本次Popen(start_new_session=True)产生的进程组：TERM等待0.25秒，超时／异常
  后KILL再等待0.25秒，最后poll仍不能确认则EXIT_UNCONFIRMED且worker_exit=null。
  信号成功不等于进程退出；poll、signal、wait错误保留，不误报清理成功。
- 日志关闭与回执写入异常另记；输出预留失败不向未取得所有权的目录写回执。
  可写时尽力写终态JSON；若磁盘完全不可写，只能控制台报告receipt_persisted=false并非零退出，
  不保证这种情况下有落盘回执。判断须结合启动工具退出码／stdout，不能只看可能残留的旧内容。
- 预算仍60秒／512MiB聚合采样RSS／5MiB全部新增输出，预留16KiB回执空间；
  工作阶段在58秒停止，为有界清理与回执留2秒。是采样监督，不是OS硬资源保证。
  清理仍未知时不能冻结为完成；不得启动另一项计算、扩大预算或自动重试。

checks补写虚拟Git失败／超时、源码不符、脏源码、日志开关／spawn／poll异常、
回执写失败、终态测量失败、首次失败与终态触限并存，以及TERM超时→KILL退出、
两次等待均超时／仍未知、等待异常和信号失败；全部只mock，不真正发送信号或加压。
保留原六类路径、预算等号、已存在目录复用拒绝；补S_plus==sum_tau与harm40／41边界。
原换行字节比较不变，生成报告CSV句柄现用with关闭。

**验证状态：仅AST语法解析、git diff空白检查与静态逐行对照；没有导入／运行这三模块，
没有执行新旧mock、生成表、资源核验、真实分析、绘图或拟合。** 新增用例不记为已通过。
核心与9984226保持不变，独立复审与新运行卡仍待审批；代码修改使旧监督器审核不能直接沿用。
主对话单写Obsidian，方法对话未触发新任务。确认数据／S04-E017／NN继续关闭或暂缓。
