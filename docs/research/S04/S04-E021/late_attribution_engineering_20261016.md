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
