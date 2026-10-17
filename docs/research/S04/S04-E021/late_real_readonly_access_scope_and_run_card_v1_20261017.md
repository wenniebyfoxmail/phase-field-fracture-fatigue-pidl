# 受限真实只读接入：范围与运行卡 v1（供审批，不可执行）

2026-10-17 Europe/London。**本轮仅准备文档；未实现、未读真实文件、未拟合，未重复mock。**
本卡是待审批的接入合同，不是已实现的launcher或真实执行许可。REAL_ACQUISITION_ENABLED仍False。
这里“真实”仅指实际保存文件；证据域仍是已见合成开发归档，不是真实道路或独立确认数据。

## 1. 唯一问题与批准边界

唯一问题：受审launcher能否在明确授权后，仅以只读方式接入四份既有标量文件，
完成已声明的身份／元数据／字段／覆盖检查，并保留可核对的控制回执？类别C0/C1接入能力。
最小比较是既有Git生产schema、冻结身份、原校验规则与实际文件的对应，不新增方法性能判据。

本卡**只覆盖接入／snapshot完整性**：不调用describe或report，不计算晚期D_i、S_plus／minus／net、
k50或harm比例，不从CSV重算晚期RMSE、其他case均值或R/G/Q，不画归因图或导出新逐周期表。
9984226归因方案、旧E021科学结论／数据角色／容差保持不变；真实归因分析须另批范围，不能借此自动开展。

| 阶段 | 当前／所需权限 |
|---|---|
| 本轮 | 仅编写本卡及Obsidian，已获准；不实现、不运行、不stat／打开四源 |
| 用户审批本卡范围后 | 下一步才可按批准范围准备／实现受限授权reader与launcher，取得绑定精确代码的独立审核；不继承真实读取许可 |
| 真实单次执行前 | 必须补齐精确源码提交、审核结论、最终命令／版本，向用户另行请求这一次执行批准；任一缺失即不启动 |

本次只解决接入合同；人工mock成功或grant中的布尔值均不能代替人方批准。

## 2. 四源科学输入白名单（固定顺序，未来获批才读）

共同绝对根：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/`。
下表相对项与该根逐字拼接才是允许的绝对路径；顺序与现有adapter.SOURCES完全一致。
不允许CLI传入替代数据根、通配符、递归猜文件名、其他别名或链接路径。

| 顺序／固定相对路径 | 仅允许用途／字段 |
|---|---|
| 1. `runs/S04-E021-R001/percycle.csv` | 保留holdout、cycle、stratum、cycle_weight、V0_physical_mse、V1_physical_mse六列；核对357个唯一键、完整四前缀、原层权重、有限非负MSE，不做误差分解 |
| 2. `replay_runs/S04-E021-REPLAY-R001/summary.json` | run_id、code_commit、status、original_verdict、fitting_invoked及四fold／三stratum结构和有限非负性；其他三case已存late背景只在原snapshot内提取，不新增计算或复制数值到本次输出 |
| 3. `control/S04-E021-REPLAY-R001_verification.json` | 显式路径run_id、code_commit、ordered_unique_rows、exact_cycle_counts、u011_C41_plus_RMSE_increase_percent；百分数仅以1+p/100换算并核对保存比值，不平方／开方或递归猜selector |
| 4. `control/S04-E021-R001_saved_output_verification.json` | 原审计status／run_id／code_commit及唯一匹配CSV的frozen_files.path／bytes／mtime_ns；不跟随清单里的其他文件路径 |

这是**四文件有界全文读取**，不是字节级列过滤：CSV其他列和JSON其他键可能随文件进入内存，
仅提取声明字段，不分析、打印或保存其他字段；不能声称文件中其余内容从未被读取。
单份科学输入仍须为非空、≤1MiB的UTF-8常规文件；超限／解码失败即停，不截断、扩限或改用其他副本。

冻结对应：拟合runtime `6aa21e3c469d53c92240c9689d07a3ffb316d67c`；
重放runtime `08242ea1c7a2cf09e4d211c51b946b8ed16cd1ab`；rows357，
counts={u011:121,u0115:99,u012:82,u013:55}；原保存late ratio参考与1e-12绝对容差不变。
百分数绑定只核对已存标量，**不等于用CSV重新证明该标量**。summary仍须自带正确Run／commit、
REPLAY_ARITHMETIC_MATCH、DIRECTIONAL_DEVELOPMENT_GAIN及fitting_invoked=false。
这些是既有声明，当前未读取文件确认其存在、当前值、大小、权限或mtime。

禁止所有其他科学输入：models／selection、NPZ／MAT／PT／checkpoint、C20数组、完整trajectory、
场／梯度／process-zone、新导出、U0.1175／U0.125确认数据；不遍历、hash或修复原归档。

## 3. 授权交接合同（仅设计，当前无授权文件）

未来顺序固定为：人方批准最终执行版本 → 父guard核对代码／审核／范围并独占新输出 →
生成本次授权 → 子worker核对绝对路径／父PID／代码 → 有界读取授权并校验全部字段 →
进入获准真实接入路径 → 四源metadata与内容 → 写本次控制结果并退出。
任何科学输入的stat／open必须晚于授权完整验证；授权缺失／错配不能通过“先检查数据”补救。

- 父guard只接受本卡固定Run／输出／四源；核对真实执行的人方批准记录和独立审核精确版本，
  再构造grant。用户批准引用／审核引用写控制回执，不靠自填true或字符串APPROVED证明人方许可。
- 父进程调用现有prepare_handoff一次，在父cwd解析授权和输出的绝对路径；
  显式覆盖S04_LATE_AUTH、S04_LATE_OUTPUT、S04_LATE_PARENT、S04_LATE_ATTEMPT、S04_LATE_CODE。
  子进程按实际os.getppid及完整40位审核源码SHA核对，任一不符先拒绝，不读授权或四源。
- 授权文件固定为本次新输出内的`authorization.json`，只在获准执行时创建；≤64KiB UTF-8、
  常规非链接文件，有界O_RDONLY读取，路径／fd及前后metadata对应，关闭fd，严格JSON拒绝重复键／非有限常量。
  这是本Run自有控制输入，不是第五份科学源；不得把授权内任意其他路径交给科学reader。
- grant沿用现有check_grant的**精确字段集合**：version=1、action=four_source_readonly_handoff、
  domain=REAL_SAVED_SCALARS、精确code_commit、plan_commit=9984226de5eb659b9ed6f82803a22c91a92e5f82、
  attempt／output、按第2节顺序的sources、固定budget、fit=false、confirmation=false，另含
  user_approved_real_execution=true及independent_code_review=APPROVED；不加被schema拒绝的额外键。
  MOCK_ONLY／engineering_only不能用于真实读取。授权机器联锁不是密码学或人方身份认证。
- 父／子启动均固定非优化Python：PYTHONOPTIMIZE=0、不用-O／-OO；两端以不可移除的if／raise拒绝优化解释器。
  默认真实入口继续关闭；未来解封路径须独立受审且只在上述许可完整时可达，不靠环境变量单独解锁或绕过现有检查。

科学reader只用精确四源，O_RDONLY|O_NOFOLLOW及path／fd前后token核对；无目录扫描／额外源名探测。
保留现有顺序：四源metadata → inventory → verification → summary → CSV → 四源metadata复核。
原CSV必须已只读；不主动chmod源文件。JSON按现有常规／大小检查，不额外假定其当前写权限已关闭。
token为dev／ino／mode／size／mtime_ns；这是替换／漂移检测，不是内容hash认证或任意Python的OS沙箱。

## 4. 拟单次运行身份和输出（尚未创建／核查）

- 沿用adapter中尚未获执行许可的拟定标识`S04-E021-LATE-DIAG-R001`；本卡仅接入，不因DIAG命名扩大为归因分析。
- 固定输出：`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/late_attribution_runs/S04-E021-LATE-DIAG-R001`。
- 制作方仅本Mac CPU、线程1，无GPU／SSH。主对话01a1131d-017c-7b03-a95a-ad73ba8fcc9c唯一执行／记录。
- 准备基线d275dd1b66be1bbe4abd79c1ed059880bff03b3b；现有核心／adapter基线e7bce63，**不是可执行真实runner身份**。
  未来真实reader／launcher、终态监督器、精确源码SHA和命令均未形成。本卡不提供可运行命令或虚构审核SHA。
- 获准执行前才核对主机、受控源码tracked／clean／等价、无重复worker、新输出未占用及必要运行环境。
  当前不扫描归档或探测新目录；不宣称该路径现在fresh。目录存在即拒绝，不删除／覆盖或换名重试。

最小未来输出固定四文件：authorization.json、access_verification.json、access.log、guard_receipt.json。
授权文件独占创建，交接后只读；其字节计入总预算。access结果只留输入路径／token、身份／字段／覆盖
核对状态、读取计数和限制，不复制源CSV、其他case的数值、数组或完整源JSON，也不序列化snapshot.rows。
父回执保留人方批准／独立审核引用、最终命令／runtime／host／PID／源码／checkout／dirty／预算／终态。
不得把真实完成写成GENERATED_ENGINEERING_ONLY、real_data_read=false或旧mock完成标记。
成功应明确是REAL_SAVED_SCALARS接入核验，不是归因完成；失败也须如实区分metadata访问、部分内容读取和未访问，
不能因为最后失败就把已经发生的真实读取标为false。

现有工程guard只准engineering目录并要求生成mock完成标记，**不能原样当作真实launcher使用**。
未来仅复用已审资源／异常回执／清理原则，真实目标路径、授权／完成判据及控制输出必须另外实现并独立审查。

## 5. 60秒／512MiB／5MiB及停止规则

拟单次总预算固定：60秒、guard＋worker子树聚合采样RSS≤512MiB、全部新增输出≤5MiB。
授权、日志、核验JSON和终态回执全部计入；不把授权准备／输出或子进程排除计量。
沿用58秒工作／2秒清理余量、20ms采样、16KiB回执余量及post-receipt检查口径；
从guard execute开始含预检／交接／读取／核验／清理，不含Python解释器／import启动。
它们是采样监督，不是OS硬峰值保证；人工R001的资源结果不证明真实接入也能在预算内完成。

| 首个停止条件 | 必须处置 |
|---|---|
| 许可／审核／源码／父子交接／非优化检查不符，真实入口未具备 | 在任何科学metadata／内容访问前拒绝；不自补授权或开关 |
| 路径不在四源、链接／别名、非常规文件、大小／UTF-8／fd／metadata异常或漂移 | 立即停，记录发生阶段和实际访问；不扩读、找替代副本或改源文件 |
| Run／commit／字段／类型／counts／唯一键／完整前缀／原权重／有限非负值／已存ratio核对失败 | 不修值、放宽容差、补字段或重做模型；报告本次接入不可接受，保留原科学判定 |
| 58秒工作余量、任一总资源阈值、异常、非零／未知退出、缺输出或回执失败 | 停止本次、保留部分产物与首因；失败或触限不重试、不resume、不扩预算、不换机器／身份补跑 |
| 完整snapshot检查已经结束 | 写控制结果、退出并冻结；不继续describe／report／拟合／重放／归因或打开确认数据 |

只清理本guard创建并能确认归属的进程组，不碰其他用户；信号成功不代表已退出。
首因与terminal_caps分列，回执缺失／退出不明不能包装为成功；冻结前核对真实进程终态。
未来主对话仅核对本Run四输出、总字节、身份／访问范围／退出和预算，然后移除自身产物写权限；
不额外hash或改原四源，源只读／metadata证据不扩大为内容认证。

## 6. 本轮交付与待用户决定

本卡和既有主题笔记／Roadmap更新是全部交付；未改任何Python、开关、原方案、科学协议或结果。
未导入项目模块，未执行实验命令／mock／真实核验，未创建Run、授权、输出或副本，也未读取四源metadata／内容。
本卡用范围表及授权顺序表达非数值C0/C1决策；当前无结果图，不生成装饰图。

请审批的仅是**四源接入范围、授权交接设计、上述预算／停止规则及最小输出**。
批准后下一步仅准备／实现受限reader与launcher并独立代码审核，随后补齐最终代码／命令版卡再申请单次真实执行。
既有mock及已消耗Run不重复。若新代码审核确需新增交接验证，先说明新增差异与授权范围，不擅自补跑旧mock。

方法对话只读分工不变；本轮compact状态读取为idle、revision62未变，未发送执行／写入任务。
本对话统一更新Obsidian。U0.1175／U0.125继续关闭，E017／NN／多目标训练暂缓；原科学结论不变。
