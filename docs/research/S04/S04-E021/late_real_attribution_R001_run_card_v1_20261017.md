# S04-E021-LATE-ATTR-R001：最终命令／单次运行卡 v1（待执行审批）

2026-10-17 Europe/London。**仅准备本卡；未执行、探测真实数据路径、读取真实metadata／内容、拟合或重复mock。**
本卡将2f0ff22范围绑定到ab48965源码和实际独立审核消息，不修改9984226的问题、指标、容差或分支。
“真实”指实际保存文件，仍是已见合成开发归档；“归因”是周期误差贡献定位，不是物理因果识别。
当前只获准备本卡的授权，尚无本Run的真实读取／归因／报告执行许可；命令文本不构成许可。

## 1. 固定身份及独立审核

- Storyline／Experiment：S04／S04-E021，描述性C0/C1补充；原科学判定不变。
- 唯一拟Run：`S04-E021-LATE-ATTR-R001`，新用途，不是旧DIAG接入的重试／续跑。
- 完整受审源码：`ab489652d4b4bb55c166782c8b9de9645a5f569b`。
- 原方案：`9984226de5eb659b9ed6f82803a22c91a92e5f82`；范围合同：
  `2f0ff22d26818ece7aa02f509451301c0cefb7d2`、`late_attribution_real_plan_and_run_card_v1_20261017.md`。
- 独立审核对话：「多目标优化学习 FEM–PINN Delta」，`01a12d15-9b60-7280-8248-18386d6ef741`。
  复审turn `01a14b70-fb6b-7643-b408-66045fe4a09a`，completed／error=null；最终message
  `msg_015d0a19570ed14a016ad3d35251548191b22c1d021d6e269a`。
  结论：ab48965静态差异复审通过，两项必改闭合，无新增必改。详见
  `late_real_attribution_code_review_result_ab48965_20261017.md`（38b5a57记录）。
- 修正限于活跃worker缓存消失竞态和已知归因失败白名单原因码。原数学核心、工程报告、旧接入入口和两份合同未改。
  新真实报告直接消费同次describe结果；不通过generated报告改标签来伪装真实结果。
- 本卡准备基线`38b5a57f24804d41b3844a2e57657fd7ec354dce`；文档提交可以晚于源码。
  既有AST／diff和静态审核不等于动态、资源、OS或视觉验证。若批准本卡，是在这些限制已知下准许一次受限运行，
  不包含隐含试跑或新增mock；不承诺本次一定完成或预算一定不触限。

## 2. 本卡专属批准引用（尚未生效）

批准索引：`S04-E021-LATE-ATTR-R001-CARD-v1-ab48965`。

固定approval-ref：
`codex-thread:01a1131d-017c-7b03-a95a-ad73ba8fcc9c/approval:S04-E021-LATE-ATTR-R001-CARD-v1-ab48965`。

这是本卡预先约定的定位索引，**不是已经存在的用户批准消息，也不是人方身份认证**。
只有本卡展示后，用户明确批准本卡最终Git版本、ab48965源码和这一个Run的四源读取／晚期归因及报告，索引才生效。
“同意准备”、以前的实现／mock／DIAG批准、代理回复和文档中的批准示例均不成立。

主对话启动前须读回实际人方批准与上节实际审核，核对完整版本／对象／命令／范围／预算／不重试；
保留批准原文与时间（可取得时加message ID），在后续Run结果记录中把实际批准映射到此索引。
未找到、含糊、撤回或版本不符即停止。源码／命令／范围改变须重新审核或取得相应版本批准。
review-ref固定指向上节审核消息；两个引用写入version-2归因grant及worker／guard结果。
`--allow-real-attribution`、grant布尔值／APPROVED字符串和默认总开关False都不能替代这一步。

## 3. 四源科学白名单及计算边界

仅以下四个绝对路径，与源码SOURCES顺序一致；不得换根、猜名、递归扫描或跟随源内其他路径：

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/runs/S04-E021-R001/percycle.csv
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/replay_runs/S04-E021-REPLAY-R001/summary.json
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/control/S04-E021-REPLAY-R001_verification.json
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/control/S04-E021-R001_saved_output_verification.json
```

| 源 | 允许用途 |
|---|---|
| percycle.csv | 六列holdout／cycle／stratum／cycle_weight／V0_physical_mse／V1_physical_mse；357行仅验证唯一键、完整前缀、权重及有限非负性；只分解U0.11 C41–C121的81周期 |
| replay summary | 自身身份／状态／原结论及四fold三层结构；仅引用其余三case已存late MSE为背景，不重算它们的均值或归因 |
| replay verification | 显式五selector；RMSE增幅百分数按1+p/100换算，核对原保存参考 |
| saved-output verification | 原审计身份、唯一CSV路径／bytes／mtime；不读取清单其他文件，不hash原归档 |

每份非空≤1MiB UTF-8常规文件，O_RDONLY|O_NOFOLLOW，path／fd前后token核对，CSV须已只读，禁止更改源权限。
是有界全文读取，额外列／键可能进入内存，但只提取声明字段，不分析或输出完整JSON、其他列或原357行副本。
保留原fit runtime6aa21e3、replay runtime08242ea、rows357、counts={u011:121,u0115:99,u012:82,u013:55}。
metadata漂移核验不是内容hash认证、物理有效性证明或OS沙箱。新authorization.json是本Run控制输入，不是第五科学源。

原describe只处理nominal-peak s4 post-history、horizon0、U0.11 C41–C121：
`D=m1-m0`，`S_plus=Σmax(D,0)`，`S_minus=Σmax(-D,0)`，`S_net=S_plus-S_minus`，晚期均差`S_net/81`。
保留k50／k50/81／对应cycle、最大正贡献、harm／improve／tie计数与比例；正贡献降序、同值cycle升序。
`tau=1e-10+1e-10*abs(m0)`；闭合差≤Σtau；基线均值>1e-24，RMSE比值与1.0160831289564436差≤1e-12。
不混用整体权重1/(3×81)，不线性分摊RMSE百分数，不加floor／换容差／删cycle／择窗。

原分支顺序不变：无效或不可识别先停；k50=1先提单状态来源核查；否则harm>=41提阶段目标／表示问题；
其余提主要贡献状态的来源需求。C121仅能提示来源核查，所有分支只产出提案，不自动计算或认定物理原因。

禁止读取models／selection、NPZ／MAT／PT／checkpoint、C20数组、场／梯度／process-zone、完整trajectory、
新导出、额外变量或U0.1175／U0.125确认数据。禁止拟合、训练、重放runner、R/G/Q重算、其他case分解、
独立cycle推断、参数搜索或重做顶层设计；DIAG控制文件不作为第五科学输入，也不重复旧mock。

## 4. 唯一启动命令（仅供审批；当前不得调用）

机器：本Mac CPU、数值线程1，无GPU／SSH。cwd固定：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016`；
分支`codex/s04-late-regression-plan-20261016`。仅在第2节实际批准成立及版本／归属核对后，从该cwd发出一次：

```bash
PYTHONOPTIMIZE=0 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -B /Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016/SENS_tensile/s04_late_real_attribution_guard.py --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/late_attribution_runs/S04-E021-LATE-ATTR-R001 --expected-commit ab489652d4b4bb55c166782c8b9de9645a5f569b --approval-ref 'codex-thread:01a1131d-017c-7b03-a95a-ad73ba8fcc9c/approval:S04-E021-LATE-ATTR-R001-CARD-v1-ab48965' --review-ref 'codex-thread:01a12d15-9b60-7280-8248-18386d6ef741/message:msg_015d0a19570ed14a016ad3d35251548191b22c1d021d6e269a' --allow-real-attribution
```

不先直启worker、--help、导入验证、制造假grant、临时改总开关、换参数、另跑mock或用其他解释器试跑。
启动命令／cwd及实际批准须由主对话记入后续结果；guard.command只记录其实际worker命令。

## 5. 获批后才进行的身份检查和交接

本轮未检查四源当前存在／metadata／内容、新输出占用或实时进程，不声称已完成运行现场预检。
获准后只核对本机／cwd及同Run guard-worker是否已有作业、固定新输出是否未占用，不扫旧归档或额外打开四源；
冲突即报告，不删除／覆盖、换名、换身份或干预其他用户进程。五运行依赖在SENS_tensile：
`s04_late_attribution.py`、`s04_late_attribution_guard.py`、`s04_late_adapter.py`、
`s04_late_real_attribution.py`、`s04_late_real_attribution_guard.py`，须tracked／clean且与ab48965逐字等价；
两份冻结合同不变。文档后续提交不改变源码身份；不为本卡改代码或复用旧DIAG授权。

实际调用后父guard独占新输出、从execute入口计时，核对源码／合同才生成version-2
`four_source_readonly_attribution` grant；绑定新Run、代码、scope、四源、预算和两个引用，fit=false／confirmation=false。
父子绝对路径、实际父PID、非优化解释器及环境须一致；子进程读取≤64KiB的只读授权后核对grant，
取得本次调用permit才可访问科学源。科学读取仍按原snapshot：metadata → inventory → verification → summary → CSV → metadata复核。
然后只调用一次原describe及本Run报告；不更改原源文件或旧结果。执行期间不派发另一计算或记录任务。

## 6. 一次总预算和停止规则

60秒／guard＋worker子树聚合采样RSS 512MiB（536870912字节）／新增输出5MiB（5242880字节）。
授权、读取、归因、表图、README、日志、全部缓存／临时文件及终态回执共用一次预算，不拆分或追加阶段预算。
计时从execute前两条语句开始，涵盖函数内预检／交接／读取／报告／清理；父解释器／import启动不计。
58秒工作留2秒清理余量、20ms采样、16KiB回执余量及post检查；字体初始化／绘图在受监督worker内。
这不是OS硬峰值或采样间保证；新链尚无动态／资源核验，旧接入或mock耗时不能作为本次保证。

| 首个条件 | 固定处置 |
|---|---|
| 批准／审核／版本／归因用途／交接／非优化配置不符或输出占用 | 拒绝科学访问，不自补许可、不换目录／身份／版本 |
| 四源路径／链接／常规文件／大小／UTF-8／fd／metadata、身份／schema／357覆盖／原权重／有限非负性失败 | 停止、保留缺口，不扩读／换副本／补字段／修源 |
| 基线≤1e-24、已知比值不符、分解闭合失败、非有限／溢出 | 报不可识别／数值无效和安全原因码，不加floor／改容差或作分支解释；未知错误只留阶段／类型 |
| S_plus<=Σtau | k50=null，保留可计算描述，图B说明不可识别、不画归一化曲线；停止分支归因，不改窗口补算 |
| 58秒工作余量、任一预算阈值、异常、非零／未知退出、缺产物或回执失败 | 留首因、terminal_caps及实际／未知活动状态，失败或触限不重试／resume／扩预算／换机器／补跑 |
| 原表图已回答问题，或下一解释需要更多字段／物理因果／梯度 | 收尾，只提出下一补证需求，不启动后续计算或打开确认数据 |

活跃worker下仅容忍cache/临时项消失，扫描有1024项上限；核心文件、链接／硬链接、其他异常及终态清单严格。
MPLCONFIGDIR／XDG_CACHE_HOME／TMPDIR分别固定在本Run的cache/matplotlib、cache/xdg、cache/tmp，全部计入预算；
不清缓存来隐藏输出，不写home缓存。不把正常缓存变化当作重启或重试理由。
仅清理本guard创建且能确认归属的进程组；信号成功不等于退出。读取／describe／绘图已发生就如实记录，
缺有效worker终态则保留unknown，不能因为失败写成false。

命令一经发出即消耗一次，即使创建目录前失败也不自动再发；工具失联只代表失去可见性，先查本Run自有进程／产物。
任何未获批准的修复、复算、重试／新Run或追加拟合均不在本卡内。

## 7. 产物、冻结、验收与结论边界

唯一输出：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/late_attribution_runs/S04-E021-LATE-ATTR-R001`。
七核心产物：authorization.json、diagnostic.csv（81行）、summary.json、diagnostic.png、README_analysis.md、analysis.log、guard_receipt.json；
必要cache另列入实际清单，不假称只有七个文件。不复制原357行／完整源JSON／模型，不新增常规hash。
原两面板来自同次结果：A为全部81周期有符号D及零线；B为原排序累计正贡献、50%和k50，或不可识别说明。
标签／README保留已见合成开发、s4／horizon0、raw archive units²、新Run及“描述性、非物理因果”。

未来终态后主对话只核对本Run产物与引用、实际读取／归因／绘图标志、已保存算术结果／表图一致性、实际退出、清单与预算；
查看本次PNG，不重绘、不重跑describe、不再读原四源作复算。若需额外分析另行申请，不以核验名义另起计算。
确认自有进程退出后，移除本Run已有文件和目录的写权限，冻结完整或部分输出；不改原四源或旧现场。
Obsidian只记录简明结果，并复用同次决策PNG，不另起作业或让方法对话双写。

运行完成须guard COMPLETED、无首因／terminal_caps／错误、worker退出0及READONLY_ATTRIBUTION_REPORTED，
引用／身份一致、四源有实际读取、357覆盖、非优化、attribution／plotting=true、fit／confirmation=false、核心产物齐全。
这些是执行与完整性条件，不是物理有效性或方法成功判定。analysis=INCONCLUSIVE也可正常收尾，不能包装成归因明确。
缺图是报告不完整，不自动否定原V0/V1；失败也不授权补算。数表权威，图不新增阈值，原E021结论不变。
若结果需独立审核，仅用本次冻结产物；不自动重新访问科学源。

## 8. 当前交付与审批用语

本轮仅本卡／Experiment记录和原Obsidian主题／Roadmap更新；未改Python或合同，未创建Run、grant、图或缓存，
未检查真实输入／旧控制文件／输出占用、未执行／拟合／重复mock。方法对话本轮未接收新任务；本对话唯一准备／未来记录方。
U0.1175／U0.125保持关闭，S04-E017／NN／多目标拟合仍暂缓。

可用批准用语（**仅示例，不是实际批准**）：

“批准按本卡最终Git版本、使用ab48965源码执行唯一一次S04-E021-LATE-ATTR-R001四源真实只读归因及报告，
批准索引S04-E021-LATE-ATTR-R001-CARD-v1-ab48965；保持60秒／512MiB／5MiB，失败或触限不重试。
完成后冻结核验并由本对话更新Obsidian；不拟合、不打开确认数据，避免双写和重复计算。”

只有明确批准此版本后才能启动。当前等待用户审批，不调用上述命令。

本轮检查：仅用标准库shlex静态分词本卡命令，并对guard的AST核对CLI参数名、固定解释器／入口／输出、
完整SHA、两个引用及其长度；没有调用命令、执行guard或导入项目。五源码及两份合同与ab48965的Git diff为空。
这不等于对真实输入、输出占用或实时条件完成运行预检。
