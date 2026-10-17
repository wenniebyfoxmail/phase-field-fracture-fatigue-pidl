# S04-E021-LATE-DIAG-R001：四源只读接入单次运行卡 v2（待执行审批）

2026-10-17 Europe/London。**仅准备最终命令／运行卡，未执行、未读取真实metadata／内容、未拟合或重复mock。**
本卡绑定已实现源码及独立静态认可，补齐ea9cafb范围卡的启动身份；不改变四源、预算、停止规则或科学协议。
当前用户仅批准准备本卡，**尚未批准这一次真实读取**。不得据命令文本、批准索引或静态认可自行启动。

## 1. 精确版本、审核和申请的单次行动

- Storyline／Experiment：S04／S04-E021；类别C0/C1，证据域仍为已见合成开发归档。
- 唯一拟Run：`S04-E021-LATE-DIAG-R001`。仅四源接入／snapshot身份和覆盖核对，DIAG名称不授予归因分析。
- 完整源码：`33feec6813347177649cffbcc0ba39297937a09e`。
- 范围合同：`ea9cafbc907cb683544aca75a58480b51c7487bd`，
  `late_real_readonly_access_scope_and_run_card_v1_20261017.md`；9984226归因方案和原E021结论不变。
- 独立审核：初审fd4700f仅发现计时起点偏晚，33feec6修正后静态差异复审通过、无新增必改。
  记录`late_real_access_code_review_result_33feec6_20261017.md`，存于32d010a。
- 审核对话：「多目标优化学习 FEM–PINN Delta」`01a12d15-9b60-7280-8248-18386d6ef741`；
  通过turn `01a14aa8-180a-7d93-b7ea-f252e25e86e0`，最终message
  `msg_015d0a19570ed14a016ad39fd210048191a8f8c550d8c5caab`。
- 已有语法／差异检查和独立静态审核；**新链未做动态、资源或OS行为验证**，旧mock不能代替本版运行证据。
  若批准本卡，就是在此限制已知的前提下，批准一次受限真实接入；不夹带另一次mock或隐含试跑。

## 2. 批准引用：当前无执行许可，获准后才有效

本卡唯一申请的批准索引：
`S04-E021-LATE-DIAG-R001-CARD-v2-33feec6`。

最终命令中的完整approval-ref固定为：
`codex-thread:01a1131d-017c-7b03-a95a-ad73ba8fcc9c/approval:S04-E021-LATE-DIAG-R001-CARD-v2-33feec6`。
这是**本卡专属、预先约定的批准定位索引，不是已存在的批准消息或人方身份认证**。
只有在本卡展示之后，用户明确批准本卡最终Git版本、33feec6及这一个Run的真实读取时，索引才成立。
单纯“同意准备”、先前实现／mock许可、代理消息或文件内的批准示例均不成立。

启动前主对话必须读回该真实用户批准，核对对象／卡版本／代码／四源／预算／不重试范围，
保留其原文和时间（可取得时加message ID），并在后续共享Run结果记录中将该实际批准与此索引对应。
不能因为命令里已有approval-ref或--allow-real-read就跳过核对；未找到、歧义、被撤回或版本不符则停止。
review-ref固定指向上节实际存在的独立认可消息；两个引用都写入worker及guard的控制记录。
若代码、命令、范围或承诺改变，重新审核／请求相应版本批准，不沿用本卡许可。

## 3. 四源白名单：未来获批后才可读取

下列绝对路径及顺序固定，与源码SOURCES一致；不得跟随源JSON里的其他路径、换根、猜名或递归扫描。

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/runs/S04-E021-R001/percycle.csv
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/replay_runs/S04-E021-REPLAY-R001/summary.json
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/control/S04-E021-REPLAY-R001_verification.json
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/control/S04-E021-R001_saved_output_verification.json
```

| 源 | 仅允许的核对 |
|---|---|
| percycle.csv | 只保留六列holdout／cycle／stratum／cycle_weight／V0_physical_mse／V1_physical_mse；核对357唯一键、四完整前缀、原层权重、有限非负MSE |
| replay summary | 核对自身Run／code／状态／原结论／无拟合，四fold三层结构和有限非负保存量；不输出背景MSE或重算其他case均值 |
| replay verification | 显式五selector绑定；保存RMSE百分数仅按1+p/100转比值并按原1e-12容差核对，不从CSV重新证明晚期比值 |
| saved-output verification | 原审计身份及唯一CSV路径／bytes／mtime；不跟随清单的其他文件，不hash原归档 |

每份是非空≤1MiB UTF-8常规文件，以O_RDONLY|O_NOFOLLOW及path／fd前后token核对读取。
这是有界全文读取：额外CSV列／JSON键可能随整文件进入内存，只提取声明字段，不分析或输出其他字段。
原CSV须已只读，不主动chmod源文件；metadata漂移检测不是内容hash认证或Python安全沙箱。
保持拟合runtime6aa21e3、重放runtime08242ea、rows357、counts={u011:121,u0115:99,u012:82,u013:55}。

禁止读取models／selection、NPZ／MAT／PT／checkpoint、C20数组、完整trajectory、场／梯度／process-zone、
新导出或U0.1175／U0.125确认数据。禁止describe／report、D_i／S／k50／harm归因、R/G/Q重算、拟合、重放或画图。

## 4. 唯一启动命令（供本卡审批，当前不得调用）

仅本Mac CPU、数值线程1、无GPU／SSH。工作目录固定：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-late-regression-plan-20261016`。
分支codex/s04-late-regression-plan-20261016；本卡准备基线32d010a，文档提交可晚于源码。
本次没有改源码／入口／配置。已有受限真实入口、默认开关False，不得笼统称读取完全不可达。

**仅当第2节实际用户执行批准成立、下节预检全部满足时，从上述工作目录调用以下命令一次：**

```bash
PYTHONOPTIMIZE=0 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 SENS_tensile/s04_late_access_guard.py --out /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/late_attribution_runs/S04-E021-LATE-DIAG-R001 --expected-commit 33feec6813347177649cffbcc0ba39297937a09e --approval-ref 'codex-thread:01a1131d-017c-7b03-a95a-ad73ba8fcc9c/approval:S04-E021-LATE-DIAG-R001-CARD-v2-33feec6' --review-ref 'codex-thread:01a12d15-9b60-7280-8248-18386d6ef741/message:msg_015d0a19570ed14a016ad39fd210048191a8f8c550d8c5caab' --allow-real-read
```

不是“先试一下”或--help命令；不先直启worker、构造假授权、临时开关、改参数或另跑mock。
主对话人工核对的启动命令／cwd也须保存在后续结果记录，guard.command字段只记录其实际worker命令。

## 5. 获执行批准后才做的预检与交接

本轮只检查Git文档和源码等价性，**未检查四源当前存在／内容／metadata、新输出占用或实时进程**。
获准后先读回真实批准及独立审核，再核对主机／cwd、五运行依赖tracked／clean且与33feec6等价：
s04_late_attribution.py、s04_late_attribution_guard.py、s04_late_adapter.py、s04_late_access.py、
s04_late_access_guard.py（均在SENS_tensile），冻结9984226方案及ea9cafb范围卡不变。
只检查同Run／同guard-worker进程和固定输出目录未占用，不扫描旧归档或直接打开四源；
有冲突就报告，不删除／覆盖、改名、等待后擅自重试或干预其他用户进程。

真正启动后父guard独占新输出，计时从execute前两条语句开始；核对源码后才生成本Run授权文件，
覆盖S04_LATE_AUTH／OUTPUT／PARENT／ATTEMPT／CODE和两个引用的子环境，固定非优化解释器。
子进程先核对绝对路径／实际父PID／代码／引用，≤64KiB只读读取authorization.json并严格校验grant，
再取得调用级permit。授权是本Run控制输入，不是第五份科学源，禁止将其其他路径交给科学reader。
四源访问顺序保持metadata → inventory → verification → summary → CSV → metadata复核。
不因授权bool／APPROVED字符串或默认开关False而省略人工许可核对。

## 6. 预算、首次停止和不重试

单次60秒／512MiB聚合采样RSS／5MiB新增输出；包含授权、日志、worker核验与guard回执。
沿用58秒工作余量、20ms采样、16KiB回执余量及post-receipt检查；execute入口后预检／交接／读取／核验／
清理计入，同一started贯穿后续时限；解释器／import启动不计入。不是OS硬峰值或采样间资源保证。
真实新链尚未动态测量，不能用旧mock的0.112秒／52MiB作本次保证。

| 首个停止条件 | 处置 |
|---|---|
| 人方批准／审核／源码／身份／父子交接／非优化配置不符，或输出已占用 | 拒绝科学访问；不自补许可、不换版本或目录；报告缺口 |
| 四源路径／链接／常规文件／大小／UTF-8／fd／metadata异常或漂移 | 立即停，不扩读、换副本、修数据或更改原文件 |
| Run／code／schema／counts／覆盖／原权重／有限非负值／保存比值核对失败 | 不放宽容差或补字段，不拟合／重放；本次接入不能登记通过，原科学结论不变 |
| 58秒工作余量、任一预算阈值、异常、非零或未知退出、部分产物／回执失败 | 保留首因和terminal_caps；停止且不重试／resume／扩预算／换机器或身份补跑 |
| 接入核对完成 | 写控制结果并退出，不继续归因、计算或打开确认数据 |

唯一启动命令一经发出即视为本次尝试；即使失败在创建目录前，也不得自动再调用一次。
工具失联仅代表可见性丢失，先查本Run进程链／自有产物，不盲目重发。只清理本guard创建的进程组，
信号成功不等于退出；无有效终态要保留null／unknown，不能把已发生或未知真实读取写成false。

## 7. 四输出、冻结和结论边界

唯一输出目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/late_attribution_runs/S04-E021-LATE-DIAG-R001`。
预计仅authorization.json、access_verification.json、access.log、guard_receipt.json；不复制源CSV、rows、
完整JSON、背景数值或模型，不新增图／缓存／授权副本或常规hash。

未来完成后仅核对本Run四文件、字节总量、身份／两个引用、实际访问记录、scope／domain、完整退出和预算；
成功须guard COMPLETED且无首因／terminal caps／错误、worker退出0、READONLY_ACCESS_VERIFIED、
357行／原counts／保存标量核对成功、非优化模式、attribution／fit／confirmation均false，四源确实有读取记录。
这意味着**本次会在获批后读取四份实际文件**，不能沿用旧mock的real_data_read=false作为成功条件。
metadata标记按尝试保守记录，不能当成完成认证；没有worker终态则实际读取状态保持未知。
确认进程退出后，仅移除本Run文件和目录写权限，冻结已有完整或部分结果；不改原四源或旧现场。

通过仅支持接入／保存记录的有界核对，不支持完整晚期归因、物理机制、teacher、梯度冲突或泛化。
失败／不完整是接入结果，不自动否定原V0/V1方法，也不授权补算。本C0/C1卡用上表表达决策，无新结果图。

## 8. 本轮交付和审批用语

本卡、Experiment索引及原Obsidian主题／Roadmap状态为全部交付；未改Python、创建授权／输出或Run，
未导入／执行模块、检查真实路径、拟合或重复mock。方法对话只读、未发新计算／写入任务。
U0.1175／U0.125继续关闭，S04-E017／NN／多目标训练暂缓，本对话唯一执行／记录方。

可供用户明确批准的用语（**这段示例不是实际批准**）：
“批准按本卡最终Git版本和33feec6代码，执行唯一一次S04-E021-LATE-DIAG-R001四源真实只读接入；
批准索引S04-E021-LATE-DIAG-R001-CARD-v2-33feec6，60秒／512MiB／5MiB，失败或触限不重试。
仅接入，不归因、不拟合、不打开确认数据；完成后冻结核验并由本对话更新Obsidian。”

当前只等待用户批准或拒绝上述一次真实接入，不执行，也不把普通方案同意解释成单次执行批准。
本轮仅对文档命令作shlex静态分词，核对固定解释器／参数／40位源码／两个引用及长度；未调用该命令。
五源码及原方案／范围卡与33feec6一致、tracked且clean；这不等于对真实输入或实时运行条件完成预检。
