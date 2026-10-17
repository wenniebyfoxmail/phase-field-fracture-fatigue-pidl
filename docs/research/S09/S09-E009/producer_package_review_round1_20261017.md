# S09-E009 producer package review — Round 1

Reviewer: Haofan account / ChatGPT Pro  
Reviewed exact commit: `3a3296d63370babda8ad7063fdfcff306a18bedb`  
Returned: 2026-10-17  
Verdict: `REVISE_AND_REREVIEW`

## Reviewer response

**附件中的 selected suite 已独立复现为 84 passed，但新增 producer package 尚不能进入最终执行门。** 最直接的阻断发生在正常接口路径：**resolver 写出的 canonical JSON，重新读取后会被 executable validator 以 `arm order drift` 拒绝。** 此外，新层的执行身份绑定、R replay 桥接、scorecard 校验和失败证据收尾仍有必须修复的问题。

本轮不回退或重新评审已通过的 core `8b6a2e49` 和 integration `efeffbfa`；下述发现均针对新增层及其对已审接口的使用。

### 一、实际核验范围与结果

| 核验内容 | 独立结果 |
|---|---|
| 附件指定的五文件 no-training suite | **84 passed** |
| 新 producer 层补充契约检查 | **24 passed、13 failed**，归并为下述五组 finding |
| 独立本地 Git 身份探针 | 完成 clean A / dirty executing B 的三种对照 |
| Python 编译、两个新 CLI | **29 个 Python 文件通过编译；两个 `--help` 均返回 0** |
| 测试后文件身份 | 候选基线文件字节未改变 |

本次恢复了附件中的六个快照：五个新增受审文件及继承的 integration config。未重复附带的依赖从前轮附件恢复，并对其中 16 个源码、测试或配置记录进行了来源核对。附件提供 diff-stat 和文件快照，不是完整 parent tree 或 Git 对象；本轮没有外部认证该 Git 对象。

原始 suite 的既有隔离测试构造了 **16 个空 AdamW 对象**；独立检查未构造 AdamW。**真实 `AdamW.step` 调用尝试和 updates 均为零**。部分状态机检查使用只增加计数的 MockAdapter，另有四臂 adapter 检查使用完全不修改参数的 inert optimizer，均不是训练。没有 SSH、producer 访问、真实 packet export 或真实科学数组读取；附件报告的真实 packet update-0 复现值，本轮未再次认证。

### 二、按 request 七项结论

| 请求项 | 结论 |
|---|---|
| **1. Resolver 的 exact identity、staging/GPU 与授权绑定** | **部分成立，未关闭。** 配置快照及冻结字段检查有实质保护，但落盘后消费失败，且公开函数的代码根与实际载入 packet 身份仍有缺口。 |
| **2. 500×4、真实 step/log count、termination** | **固定调度及普通计数路径通过；失败证据未闭合。** Mock post-step failure 能保留 steps=17、logged=16，但部分后续证据处理会丢失观察或再次失败。 |
| **3. R exact replay、legacy stream、single clip** | **普通有限路径通过；新边界及 gate 语义未闭合。** 四个 tiny-Q4 cycle 的方向、同-forward `g_D` 和 canonical legacy record 与继承实现一致，无第二次 clip。 |
| **4. 固定 16-example evaluator 与完整 scorecard** | **部分成立，未关闭。** 同一 checkpoint 遍历完整支持集成立，但 constant-field NA 和嵌套指标一致性校验存在缺陷。 |
| **5. Conditional evidence、失效后禁止性能解释** | **成功路径有覆盖；失败路径未关闭。** 具体见 F5。 |
| **6. Mock tests 是否确实零 AdamW.step** | **零真实 step 已验证。** 但现有测试未覆盖实际 resolver 文件往返、部分嵌套 scorecard 和 evidence-close failure。 |
| **7. 两个显式 CLI 与单一 final run card** | **入口结构基本成立，但暂不足以放行。** CLI 均有显式动作开关并使用自身 `ROOT`；run card 仍受 F1–F3 的接口或契约冲突影响。 |

### 三、必须修复的发现

#### F1．正常 resolver 输出在落盘后无法通过自己的执行校验

**位置：** `validate_resolved_config()`、`_unresolved_projection()` 与 resolver 写文件路径。

Resolver 的内存对象中，arms 顺序是 `R → S → A0 → A25`，但 `_write_new_json()` 使用的 `canonical_json()` 会排序字典键。实际写入并重新解析后，顺序变为 `A0 → A25 → R → S`。Producer 随后把该对象投影回 integration config，却没有恢复冻结顺序，直接交给已审 integration validator。实际结果是 `ValueError: arm order drift`。

**这个反例使用了实际 resolver、实际文件写入、实际重新读取和实际 validator。** 仅 GPU/environment、Git 检查结果和 packet loader 使用显式 mocks；没有修改候选代码。返回对象与落盘对象的字典内容相等，但插入顺序不同。现有 resolver 测试只验证返回的 `resolved`，没有验证文件往返后的对象。

这是正常路径阻断，不需要异常数据。排序行为也由继承 serializer 明确定义。

**最小修复：** 在新增 producer 的投影/序列化适配层，先严格核对 arm membership 和各臂内容，再显式按 `ARM_ORDER` 构造传给 integration validator 的对象；执行顺序继续使用冻结常量。增加“实际 resolver → 实际写文件 → 重新读取 → executable validation”的正向回归。**不要修改已审 integration validator，也不要改变四臂顺序或方法。**

#### F2．新层尚未把“检查的身份”完整绑定到“实际执行与消费的对象”

##### 2.1 实际载入的 packet 没有再次对照授权身份

当前执行路径先读取 `packet_identity.json` 并与 resolved config 比较，之后 `build_runtime()` 又独立加载 packet。**返回的 `base_runtime.packet_identity` 没有再与预期身份比较，就进入 `initialise_arm_states()`。**

独立 mock 检查中，前置 identity/config 均为 A，`build_runtime()` 返回的已载入 identity 为 B，程序仍到达了被监测的 optimizer-construction 边界；该边界立即抛出测试异常，**没有实际构造 optimizer**。

这一检查刻意保留可通过当前 validator 的 arm 顺序，以隔离 F1；没有靠修改 validator 绕过检查。它证明的是新消费边界缺少身份比较，不是声称本轮读取或替换了真实 packet。

另外，final run card 已给出具体 packet manifest SHA，但 resolver 只是把它观察到的 packet identity 写入配置，未与独立批准的 expected packet identity 比较。

**最小修复：** 绑定独立批准的 expected packet hash，并在实际 runtime/数组进入四臂 optimizer 构造前再次核对；不能只验证更早读到的 sidecar。随后保存的 packet identity必须描述实际消费对象。

##### 2.2 CLI 固定了 ROOT，但公开 Python 入口仍允许检查另一目录

两个 CLI 自身没有 caller-controlled `--repo-root`，这一点成立。但 `resolve_producer_config(..., repo_root=...)` 等公开函数仍检查传入的仓库，而不是要求其对应实际载入模块的代码树。

使用真实本地 Git fixture、真实 commit/cleanliness 检查得到：

| 实际执行模块 | 被检查目录 | 结果 |
|---|---|---|
| Clean A | A | 通过身份检查，到达预设的 packet-read 哨兵 |
| Dirty B | A | **同样通过身份检查** |
| Dirty B | B | 正确拒绝 dirty execution files |

仅环境查询及 packet-read 停止点使用 mocks；fixture commit 不是用户的真实 commit。

**最小修复：** 在新增模块的公开入口从自身 `__file__` 确定代码根，或拒绝 `repo_root` 与实际模块根不一致。这里修复的是**函数入口**，不是宣称当前 CLI 支持传入另一 root。

#### F3．R 的普通数值桥接正确，但新增边界遗漏检查，并改变了 hash 的 gate 含义

##### 3.1 派生 objective 非有限时，新桥接仍会产生方向

`_replay_direction_with_legacy()` 检查梯度块和 raw gradient norm，却没有像继承接口一样，在 autograd 前检查各个组合 objective 是否为有限 scalar。

实际合成反例中，六个原子 loss 都是有限的 `l_i = 10^308 + sum(p)`。组合后的 `J_N/J_H` 已溢出为非有限值，但新桥接仍调用 merger 并返回方向，没有停止。若继续正常 producer 路径，训练行中的非有限组合量要到**optimizer step 之后的序列化**才可能被发现。该先 step、后生成日志的顺序由新增 adapter 明确定义；本轮没有实际执行该 optimizer step。

**最小修复：** 在新桥接边界恢复组合 objective 的有限性检查，以及已审路径中通常应有限的 merger diagnostics 检查；保留合法 zero-cosine NA。正常 replay 算术、legacy 格式和那一次 clipping 均不改变。

##### 3.2 新输出 hash 被升级成了额外硬门槛

冻结 protocol 规定：归档前 500 行 hash 用于参考身份；新的 direction hashes 是 identity diagnostics，在数值容差全部通过时不是额外科学接受条件。

但新 `replay_validity()` 把**新生成的完整 legacy stream hash**纳入 `all(clauses.values())`；run card 也要求其不匹配时停止后续 arms。独立字典级检查中，0/500 全部数值参考完全一致、terminal completed，仅新 hash 不同，仍返回 `pass=False`。

**这是一处冻结 protocol 与新增代码/run card 的契约冲突，不是声称真实 R 已经出现 hash mismatch。**

**最小修复：** 保持原 protocol，区分 archived-reference hash qualification、numeric replay gate 和 new-stream hash diagnostic；不要静默增加新的接受条件。实际 legacy 字节流仍应可保存或确定性重建以供审计。

#### F4．Evaluator 的 constant-field NA 与完整 scorecard 校验尚未闭合

##### 4.1 精确常数场可能被报成 correlation 1

对 float64 常数向量 `left=[0.1,0.1,0.1]`、`right=[0.2,0.2,0.2]`、`weight=[1,2,3]`，实际 `_weighted_correlation()` 返回 **1.0**，而不是 NA。原因是加权均值的舍入使中心化残余不完全为零，当前代码只检查计算后的平方和是否为零。

**最小修复：** 在 covariance 运算前识别精确常数输入，返回既定 NA；不要新加一个“near-constant epsilon”或改变空间阈值。

##### 4.2 嵌套 scorecard 可以缺失或与同一 16 行证据矛盾

在实际 update-0 synthetic evaluation 上，分别进行以下修改，当前 `_validate_evaluation_record()` 均未拒绝：

| 修改 | 当前行为 |
|---|---|
| `amplitude_auc={}`，缺少 value 和 win/tie/loss | 接受 |
| 16 行预测幅值全部相同，却把 aggregate AUC 改成 1、25 wins | 接受 |
| 某 cycle correlation 为 NA，aggregate 仍声明完整支持集 median 为 DEFINED | 接受 |
| 两组预测幅值均为零，却声明组间比值为 `1 / DEFINED` | 接受 |

Validator 对 G/F/persistence、loss 均值和 hard-count 做了较实质的重算，但对上述嵌套对象主要检查顶层字段存在，没有完成其内部 schema 和跨层一致性检查。

**最小修复：** 从同一固定 16-cycle rows 重算/核对 AUC、ties、组间幅值比及 fixed-support spatial median；严格检查嵌套对象的字段、类型、NA 状态和 membership。用于 pairwise distribution 的固定 120 对值及其 NA 也应保留，不能把现有 count/min/max/median 称为完整 distribution。

这些是实现冻结 scorecard，不是新增科学指标。现有 mocks 自身也存在 AUC/count 不一致，修复测试时应构造一致证据，不能放宽 validator 以维持测试通过。

#### F5．失败状态被识别，但其观察值和 evidence-close 不能可靠保留下来

这里有三个不同的新增层缺口。

**第一，真实 hard-count 丢失。** Pro 让实际 tiny 模型完成初始 16-example evaluation，再在首次待更新 forward 注入一个 prescribed-boundary violation。程序正确在 optimizer 前停止，reason 包含 `'peak_boundary_lifting': 1`，但 termination receipt 的所有 `hard_constraint_counts` 仍为零。新状态机保留的是最后一次成功 evaluation 的 counts，没有接收失败 forward 已发现的 counts。

**第二，合法部分日志导致共享失败 writer 再次失败。** 模拟第 17 行写入后的 gradient flush failure，状态机正确保留 mock `steps=17`、`fully_logged=16`，文件中则有第 17 行。随后 `_read_gradient_summary()` 对 failed arm 仍强制“可解析行数等于 fully_logged”，抛出异常，阻止共享失败证据生成。

不能把第 17 行擅自升级成完整更新，也不能删除它；应报告**已确认前缀与未确认尾部**。

**第三，checkpoint 已保存后的 evidence-close failure 没有 arm receipt。** 在纯 MockAdapter 完成 500 个逻辑更新并提交 mock checkpoint 后，注入一次 artifact-hashing failure。实际结果是 checkpoint 文件存在，但 `run_arm_state_machine()` 抛出，未生成该 arm 的 termination receipt；相关 hashing/receipt-writing位于 catch 区域之外。

**最小修复：** 在新增 adapter/状态机中传递失败观察的实际 counts；failed-arm 日志汇总应保留验证过的前缀和尾部状态；将 evidence close 纳入终止及安全 fallback 路径，保留已完成计数、已提交 checkpoint 的 presence/identity。不要修改已审 hard-constraint 谓词、termination validator 或科学分级。

### 四、测试覆盖与单一 final run card 的收束

现有测试确实完成了 mock 完成/失败/不适用路径、普通 evaluator、普通 replay bridge 和成功 writer 的检查，**84 passed 不是虚报**。但 resolver 测试验证的是内存对象；writer 测试使用了未被充分交叉核对的 mock scorecard；post-step failure 测试没有覆盖实际文件留下部分尾行及 checkpoint 后 evidence-close failure。新增失败检查正好落在这些交界。

修复后，final run card 应与代码保留**唯一的一套**解析、授权、启动和 fail-stop 规则，尤其要消除新 hash 硬门槛与冻结 protocol 的冲突，并明确同一 `CUDA_VISIBLE_DEVICES` 对 resolver 和 launch 都生效。无需增加 arm、seed、预算或性能阈值。

### 五、允许的下一 gate

**先完成 F1–F5 的新增层修复，补充 mock/synthetic no-training 回归，再冻结新的 exact producer commit 复审。** 已通过的 core 和 runner-integration gate 保持关闭，不要求重新训练或重新设计 protocol。

后续 `PRODUCER_PACKAGE_READY_PASS` 也只表示可以进入**单独的最终执行门**，不授权 SSH、传输、optimizer training、Taobo launch、P1 通过或科学结论。
