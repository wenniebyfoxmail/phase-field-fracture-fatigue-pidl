# S09-E008 P1 Code Ready review round 1

- reviewer: Haofan ChatGPT Pro via OpenCLI
- reviewed exact commit: `f4f0d2eabbd3e6caa79105eddfe0b3bebf37cf2f`
- conversation: `https://chatgpt.com/c/6ad21ed5-b38c-8330-a463-aeee98191c9b`
- UI duration: 14m 56s
- no producer access, real packet export, training or optimiser step

REVISE\_AND\_REREVIEW

审核对象：f4f0d2eabbd3e6caa79105eddfe0b3bebf37cf2f。

**存在必须在真实 packet export 或训练前修复的问题，因此本次不通过 Code Ready。** 最直接的阻断是：**near-stagnant 判据错误地使用 damage increment RMS scale 代替协议中的 DD**。此外，配置与代码身份绑定、loader 的固定 schema 校验、非有限值检查，以及失败后的证据保存尚未闭合。以下结论属于实现审核，不涉及模型能力或科学有效性。

## 一、实际核验范围

我读取了附件全文，并恢复、核对了 manifest 中的 **16 个文件：字节数和 SHA256 全部一致**；所附 **12 个 Python 文件均通过 py\_compile**。这里确认的是附件内容与 manifest 自洽；commit 归属依据附件的 git show 声明，没有访问仓库或 producer 进行外部认证。附件所报告的 49 passed 与禁止训练等边界见审核请求。

**未能独立复跑完整 49-test suite。** 附件缺少三个被导入的项目模块和四个列入测试命令的复用测试文件；实际执行 pytest --collect-only 在导入阶段即因缺少 s09\_stage0a\_packet 停止。另行完成的核验是：从附件源码原样抽取函数，使用 tiny CPU 张量、合成数组和隔离 guard mocks 做反例检查；没有补写缺失依赖来冒充完整实现。

本轮没有访问 producer、SSH 或 GPU，没有调用真实 exporter、resolver 或训练入口，**optimizer steps 为零**。

## 二、按八项审核问题逐项结论

审核项

结论

核验结果

1\. 完整 qualification、packet identity、loader

**不通过**

存在完整资格重算调用路径，但依赖源码未齐；重算结果与冻结 scales/groups/DD 的绑定不足；loader 主要核对 manifest 自述内容，没有完整执行固定 schema 与 canonical 校验。

2\. resolution order、equilibrium normaliser、授权

**部分成立，不通过**

normaliser 确实在模型构造前计算，并要求有限、严格正；未授权配置会拒绝执行。但配置不变量、已审 commit、实际执行字节及 producer environment 未形成完整绑定。

3\. Stage-0A 映射、输入边界、float64/native supports

**所给调用路径静态核验一致**

输入限于 s00 的 damage/history、已知 prescribed path 和静态几何；没有把 s04 target 送入模型，没有 s05 输出头或 rollout。scale buffers 直接以 float64 构造，raw history 三通道与 derived f 的接口一致。

4\. 三目标 full-vector gradients 与更新代数

**代数成立，缺失记录 guard 不通过**

三目标齐全时，零块补齐、lower median、immutable-reference cyclic projection、三方向平均、单次 clip 和赋值顺序一致；但缺失第三目标没有被拒绝。

5\. projected-output 与 teacher/prestate 检查

**不通过**

已实现的有限值条件下约束公式基本一致，raw clipping 没有误算成 violation；但 NaN 可以穿过检查，evaluate() 仍返回 finite=True，部分 prestate 检查晚于模型构造。

6\. 每步日志

**不通过**

有参数名称顺序、unconnected names、norms、raw pairwise cosines 和 merged-vector hash；但“raw increment”不是未缩放 objective，部分承诺的诊断缺失，而且日志直到训练全部结束才落盘。

7\. schedule、verdict、输出、producer guards、failure receipt

**不通过**

1,000 次循环、固定 cycle 顺序及末次 cycle 46 一致；但 DD 判据错误，路径/environment guard 不闭合，失败 receipt 缺少关键身份与更新计数。

8\. 49 tests 是否足够支撑首次运行

**不通过**

完整 suite 无法由附件重现；本地反例还证明现有校验存在实质遗漏，不能仅以提交方的 49-pass 报告放行。

## 三、阻断发现与最小修复

### F1．near-stagnant verdict 使用了错误的量

**位置：** source/s09\_stage0a\_p1\_trainer.py::run\_training，以及 exporter/config 中冻结判据的传递接口。

协议中的 DD 是全部 eligible cycles 的 gkg\_k 上四分位组中位数；near-stagnant clause 是：

false\_growth⁡≤0.25D.\\operatorname{false\\\_growth}\\leq 0.25D.

代码却使用：

Python

`stagnant = final["near_stagnant_false_growth"] <= ( 0.25 * runtime.config["normalisers"]["damage_increment"] )`

damage\_increment 是另一个量——selected-set damage increment RMS scale，不能替代 DD。当前代码实际上使用阈值 0.001724003346706521。附件没有给出可用于此处的真实 DD 数值，因此不能判断该错误使真实判据变严还是变松；但可以确定它**改变了冻结 verdict 的定义**。

**触发与影响：** 正常完成 1,000 updates 就会使用这个错误阈值；不需要任何异常输入。它可能改变最终 P1 verdict。

**最小修复：** 将 qualification 重算得到的真实 DD 作为独立字段写入并绑定 packet/frozen contract，再由 decision 使用；不能把现有 RMS 字段改名当作修复。同时在模型构造前核验 growth group 非空、persistence baseline 严格正，并记录所有判据使用的实际阈值。增加 **D≠D\\neq RMS** 的边界测试，不改变原选择规则、分组或阈值。

### F2．配置与已审代码身份没有 fail-closed 地锁住

**位置：** s09\_stage0a\_p1\_packet.py::\_validate\_config/export\_s09\_e008\_p1\_packet；s09\_stage0a\_p1\_trainer.py::\_validate\_reviewed\_config/current\_commit/resolve\_execution\_config。

exporter 将 config\_sha256、normalisers 等写入 metadata，但后续 validator 没有据此锁定原配置。重算 qualification 后，明确比较的主要是 selected cycles 和 static identity；没有把重算 verdict、groups、scales、DD 完整核对到冻结包。trainer 的 validator 也没有固定 width/rank、学习率、完整 scales、分组和 gradient epsilon 等方法不变量。

**实际本地反例：** 单独改变 width 32→64、学习率、damage scale、growth group 或 gradient epsilon，validator 均接受；在构造的 executable config 中，width 与 scale 漂移也仍被接受。相反，execution\_authorized=False 被 executable validator 拒绝，这一项 guard 成立。

代码身份方面，current\_commit() 只读 git rev-parse HEAD；resolver 将当前 HEAD 写入配置，却没有核对它是否为已审批准的 commit，也没有检查相关工作树或执行文件字节是否漂移。因而“HEAD 相同”不等于“实际执行的是本次审过的代码”。

**最小修复：** 以已审 base-config identity 为锚，只允许 resolution 明确列出的字段变化，其余方法字段精确比较；核对 packet 内的 config identity 和冻结资格结果。export、resolve、run 都应核对**外部给定的已审 commit**及相关执行文件身份。无需把 commit 自引用硬编码进它自身，但不能自动把任意当前 HEAD 当成已批准版本。

### F3．loader 校验的是自述一致性，不是完整固定 schema

**位置：** source/s09\_stage0a\_p1\_packet.py::load\_verified\_packet。

loader 检查数组字节 hash、数组与 record 的 shape/dtype 是否相同，以及数值有限性；但没有重新调用固定的 \_validate\_arrays，也没有验证 manifest 字节是否等于 canonical\_json(manifest)。manifest\_bytes、array\_count 等 identity 字段也未形成完整校验。

**实际本地反例：** 将 tiny synthetic packet 的 d\_peak 改为 float32，同时更新自述 manifest/identity，loader 接受；将 manifest 改成非 canonical 排版并更新 identity，也被接受。未更新 hash 的普通字节篡改则正确被拒绝。

这**不是**绕过已经从外部固定的原 packet hash；反例证明的是：在首次 resolution 接受一个新 packet identity 时，loader 自身并不能证明它满足所声称的固定 dtype/schema/canonical contract。

**最小修复：** 在 loader 中执行完整固定 array membership、native shape、精确 dtype、数值语义检查；验证 canonical bytes、长度及计数，并在 resolution/run 核对外部绑定的 packet identity。schema 校验不能只相信同一份 manifest 的自述。

### F4．非有限输出能穿过 validity 检查；部分输入资格检查过晚

**位置：** s09\_stage0a\_p1\_trainer.py::hard\_constraint\_report/evaluate/\_verify\_packet\_states\_before\_model。

hard\_constraint\_report() 使用违反不等式的数量判错，但没有先检查全部输出有限性；evaluate() 最后直接写入 "finite": True，也没有先验证 judgement 和各项 metric 有限。

**实际本地反例：** 在合成输出的内部位移 DOF 放入 NaN，得到：

纯文本

`L_judge = NaN hard_constraint_violations = 0 finite = True`

这不等于完整 runner 一定会把 NaN run 判为 PASS：后面的 canonical\_json(allow\_nan=False) 可能再拒绝它。问题是**检查阶段和 validity 标志已经错误**，而诊断 evaluation 的失败还可能被延迟发现。

另一个反例是 negative prestate alpha：当 f=1 且前后满足现有比较时，pre-model checker 接受；真正的 alpha 非负检查位于模型 forward 的 \_validate()，晚于构造。

**最小修复：** 在模型构造前完成已有输入资格谓词；每次 loss/metric 使用前检查所需 projected outputs、raw proposals 和权重有限；metric 产生后再次检查有限性。finite 应来自实际检查而非字面常量。保留现有区别：**合法 projected output 对应的 raw clipping/saturation 仍只是诊断，不增加 hard-constraint violation。**

### F5．Taobo roots、设备与 environment 的锁定不完整

**位置：** s09\_stage0a\_p1\_trainer.py::resolve\_execution\_config/\_execution\_preflight。

现有 preflight 使用字符串前缀检查 root，没有规范化后的 containment 检查；archive\_root 未纳入校验。Linux、CUDA 可用及单个 CUDA\_VISIBLE\_DEVICES 字符串，也不足以核对 Taobo 主机身份、实际设备身份和预先锁定的 environment。完整 environment 信息是在训练结束后才生成的。

**实际本地反例：** 仅用虚拟路径和 guard mocks，以下配置/输出路径被接受：

纯文本

`/mnt/data2/drtao/wennie/../escaped/R001`

它规范化后已位于 wennie 根目录之外。没有访问或创建这个实际路径。

代码没有自动 CSD3 fallback 分支；这里的缺口是**缺少正向 producer 身份绑定**，不能据此宣称 no-CSD3 guard 已闭合。

**最小修复：** 对 approved roots 做规范化、containment、父路径链接和 freshness 校验；明确 resolved config 的 staging 位置，避免 resolver 先创建未来 run root 后又触发 freshness failure。将 read-only preflight 得到的主机、实际 GPU 和 environment identity 写入 resolution receipt，并在执行前比较；保留单 GPU 与既定磁盘门槛。

### F6．失败证据与日志输出不闭合

**位置：** s09\_stage0a\_p1\_trainer.py::run\_training/gradient\_record。

每步 train\_rows 和 gradient\_rows 只保存在内存中，全部更新结束后才写文件；diagnostic steps 的结果保存在 diagnostics 字典，却没有输出。build\_runtime 和 \_execution\_preflight 在 try 之外，因此这些阶段失败不走 failure receipt；进入 except 后的 receipt 又只有错误类型、信息和耗时，没有 run/code/config/packet identity 或已完成更新数。

**触发与影响：** 例如第 600 次更新附近异常终止，会丢失此前逐步 loss/gradient 记录，也无法仅凭 failure receipt 准确判断已有多少 optimizer mutation。这会直接损害首次 producer run 的可解释性。

日志语义也需补齐：raw\_increment\_objectives 中的 “raw” 指未投影 proposal，其 target 已除以冻结 scales，**不是未缩放的原始 objective**；现有日志没有完整覆盖承诺的 raw/scaled 对照，以及 post-projection alignment/effective ratios。

**最小修复：** 增量写入逐步日志，明确记录已完成 optimizer step 与已验证 successful update 的计数；持久化 diagnostic schedule 的结果。开始执行前保存身份与环境，所有可捕获失败都生成带阶段、身份、计数及最后有效日志位置的 receipt；无效 root 的失败应写到事先批准的安全审计位置，不能为留痕越权创建目录。补齐未缩放分项、scaled objectives 和所承诺的梯度诊断，不需要保存巨大的完整梯度 JSON。

### F7．缺失整个 objective 不会触发 stop

**位置：** s09\_stage0a\_p1\_trainer.py::full\_objective\_gradients。

函数使用 zip(OBJECTIVE\_ORDER, objectives)，只检查返回 vectors 长度一致，没有要求恰好三项及完整 objective membership。传入两个 objectives 时，返回两个 vectors；merge 函数同样接受两个输入。

**实际本地反例：** 两个 objectives 被接受，返回 vector count 为 2。当前 \_objectives() 的正常路径确实返回三项，因此这不是声称正常路径已经少算了一个目标；它说明协议要求的“missing record 必须 stop”没有实现。

三目标齐全时，本地核验确认了 unconnected parameter 的同形状零块、flatten/assignment，并且 merge 通过六组独立 NumPy 代数对照，包括 lower median、零方向平均、微小正 norm、冲突投影和 global clipping。合并主公式本身没有发现需要修改的问题。

**最小修复：** autograd 前严格检查目标数与目标身份；将每次产生的 parameter order/layout 对照已冻结记录，而不是只与本次刚生成的 layout 自洽。增加 missing/extra objective、顺序漂移、缺块和长度漂移的拒绝测试。

### F8．审核附件未包含可复现完整候选的依赖闭包

**位置：** bundle manifest、源码 imports、所列测试命令。

缺失的源码为 source/s09\_stage0a\_packet.py、source/s09\_stage0a\_p1\_freeze.py、source/s09\_operator.py。它们分别承载 payload/transition decode、P1 selection/freeze 和实际 IntegralBlock/mlp 实现，并非无关文件。

测试命令还引用四个未附文件：test\_s09\_stage0a\_capability.py、test\_s09\_stage0a\_packet.py、test\_s09\_stage0a\_transition.py、test\_s09\_stage0a\_p1\_freeze.py；实际所附 runner 文件包含七个 test functions。

**影响：** 无法完整核验 decoder、资格重算、骨干实现及 49 tests 覆盖范围。**这是附件证据缺失，不是认定这些文件在你的仓库中不存在。**

**最小修复：** 从修复后的同一个 exact commit 补齐依赖源码、四个测试文件和对应 hashes，再提交完整 no-training 测试结果。回归测试必须覆盖上述反例，尤其是 D≠D\\neq RMS、配置漂移、固定 schema、NaN、missing objective 和失败留痕；无需为此导出真实 scientific packet 或运行 optimizer。

## 四、允许的下一 gate

**本次只允许：本地有界修复与 synthetic/no-training 回归 → 冻结新的 exact candidate commit → 再次独立 Code Ready 审核。**

本次 **不放行真实 packet export、Taobo resolution 或训练**。后续只有在 Code Ready 通过后，才进入已审 exporter 的真实 packet binding、read-only Taobo environment/GPU resolution、模型构造前 equilibrium normaliser 冻结，以及独立的 final execution gate；Code Ready 本身仍不授权 optimizer training，也不构成任何科学结论。

本地审核证据包：逐文件 hash 核验、隔离反例脚本与实际结果

ChatGPT 可能会出错。请核查重要信息。
