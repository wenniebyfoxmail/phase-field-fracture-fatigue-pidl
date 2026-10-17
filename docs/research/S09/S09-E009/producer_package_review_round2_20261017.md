# S09-E009 producer package Round-2 review — 2026-10-17

REVISE_AND_REREVIEW

审核对象：`6861a1c8260e158269da2738176a62d612f5a2a2`。

F1–F4 可关闭；F5 的 confirmed-prefix/unconfirmed-tail 修复通过，但 failed-forward hard counts 和 evidence-close fallback 各剩一处可复现遗漏。本轮不回退已通过的 core `8b6a2e49` 与 integration `efeffbfa`，也不要求训练。

## 一、实际核验结果

| 核验内容 | 独立结果 |
|---|---|
| 附件指定五文件 selected no-training suite | 98 passed |
| F1–F5 补充边界检查 | 63 passed、3 failed；三个失败归并为下文两个 F5 残余 |
| 本地 Git 身份探针 | clean A、dirty B 检查 A、dirty B 检查 B 三种行为均符合修复预期 |
| Exact repair diff | 所附三文件 diff 应用到 Round-1 文件后，与本轮 producer 源码、测试、final run card 逐字节一致；Git blob 前缀匹配 |
| 编译与 CLI | 29 个 Python 文件通过编译；两个 CLI `--help` 返回 0 |
| 测试后身份 | 重建目录内 33 个文件字节未改变 |

未重复附带的依赖从前轮附件恢复，并对 32 个基线文件与原始附件内容进行了核对，没有补写实现。这里验证的是附件、差分及继承依赖的一致性，没有外部认证完整 Git commit 对象。

原始 suite 的既有隔离测试构造了 16 个空 AdamW 对象；补充检查未构造 AdamW。真实 `AdamW.step` 调用尝试和 optimizer updates 均为零。所有 500 次状态机循环均使用 MockAdapter，不是训练；没有 SSH、producer 访问、真实 packet export 或真实科学数组读取。

## 二、F1–F5 逐项结论

| Finding | 本轮结论 | 核验说明 |
|---|---|---|
| F1：resolver 文件往返与 arm order | 关闭 | 实际 resolver → canonical 写文件 → 重新读取 → executable validation 已通过。投影先检查 arm membership，再恢复 ARM_ORDER；缺臂、额外臂、规则/beta 和其他冻结字段漂移仍被拒绝。 |
| F2：module root 与实际消费 packet 身份 | 关闭 | 公开入口拒绝不同于实际 module root 的仓库；resolver 绑定独立批准的 packet hash；实际 runtime identity 在 optimizer 初始化边界前再次检查，输出记录使用 consumed identity。 |
| F3：replay 非有限边界及 numeric/hash 分离 | 关闭 | 非有限组合 objective 被拒绝，六项通常应有限的 merger diagnostics 的 NaN/Inf 注入均停止，合法 zero-cosine NA 保留。普通方向、同-forward g_D 和 legacy bytes 与继承实现一致；新 hash mismatch 不再单独否决 numeric replay。 |
| F4：16-cycle 嵌套 scorecard 与 120 对分布 | 关闭本轮所列问题 | 精确常数场返回 NA；实际 evaluator 保留全部 120 对位置及 null。AUC/ties、幅值比、空间支持集、相关性、loss/count 汇总及 pairwise 统计的漂移检查通过。 |
| F5：失败观察与条件性 evidence | 部分关闭 | 确认前缀与未确认尾部已经正确分开；单次 artifact-hash helper failure 后也能保留 checkpoint-bound receipt。但实际失败 forward 的计数仍丢失，fallback 遇到持续的单文件读取错误仍会再次中断。 |

F1 的修复位于新增 producer 投影层，没有修改已审 integration validator；F2 的 runtime 身份核对确实位于 `initialise_arm_states()` 之前。F3 的数值 gate 与新输出 hash diagnostic 已在代码及唯一 final run card 中一致分离，没有新增 replay 接受阈值。

## 三、F5 残余一：实际失败 forward 在新计数赋值之前已抛出

位置：`TorchArmAdapter.step()`、`TorchArmAdapter.evaluate()` 与继承的 `atomic_losses()` 的连接边界。

当前新增顺序是：

```python
losses, context = atomic_losses(self.runtime, index)
step_hard_counts = hard_constraint_report(...)
self.hard_constraint_counts = dict(step_hard_counts)
```

但是继承的 `atomic_losses()` 在返回之前，已经调用实际的 fail-fast `hard_constraint_report()`。真正的 hard-constraint violation 会在那里抛出，因此不会到达新增的 `self.hard_constraint_counts` 赋值。这是新增 adapter 对已审接口的使用问题，不是 core 谓词需要修改。

### 实际复现

使用 tiny synthetic runtime，仅通过 forward hook 给一个 prescribed-boundary displacement DOF 增加 0.1，没有 mock 约束谓词或 atomic losses，分别检查：

| 失败位置 | 实际结果 |
|---|---|
| 初始 evaluation 的第一个 forward | 正确停止为 EXECUTION_FAILED，但结构化 hard count 为零 |
| 完成初始 16-example evaluation 后，首次待更新 forward | 同样正确停止，但结构化 hard count 仍为零 |

两份 receipt 都出现以下矛盾：

```text
reason 中：peak_boundary_lifting = 1
hard_constraint_counts 中：peak_boundary_lifting = 0
```

两项检查的 optimizer 调用均为零，模型 parameters/buffers 未改变。没有错误放行训练，但失败证据仍错误地报告零违反计数。

现有新增测试将 producer 层的 `hard_constraint_report` mock 成“返回非零 counts”，因而能执行后面的赋值；它没有覆盖实际 inherited validator 提前抛出的路径。另一个 MockAdapter 主动设置 counts 的测试，也不能替代真实 adapter 的这一连接检查。

### 最小修复

在 producer 层增加同一 forward 的失败观察桥接：在异常传播前保存该实际输出对应的 hard counts，并同时覆盖 evaluation 与待更新 forward。不能等待 `atomic_losses()` 成功返回后才记录。

保留已审 core 的 fail-fast 谓词和 loss 数学；不通过第二次 forward 重新生成诊断。新增回归应使用未修改的实际谓词，覆盖上述两个失败位置，并要求 reason 与结构化 counts 一致、optimizer 调用为零。

## 四、F5 残余二：hash fallback 仍依赖失败文件能够再次读取

位置：`run_arm_state_machine()` 的 evidence-close exception 分支。

当前 catch 到 artifact hashing failure 后，会逐文件执行：

```python
artifacts[name] = hashlib.sha256(path.read_bytes()).hexdigest()
```

这些 fallback reads 没有逐项异常保护。若第一次 hashing failure 正是因为某个 common artifact 无法读取，fallback 会对同一文件再次失败，仍到不了 termination receipt 写入。

### 实际复现

纯 MockAdapter 完成 500 次逻辑更新并保存 mock checkpoint 后，在读取边界对 `gradient_diagnostics.jsonl` 单个文件注入可重复的 `PermissionError`。其余路径正常。

实际结果：

```text
checkpoint_update500.pt：存在且可读取、可计算 SHA256
receipt 所在目录：独立写入/删除探针通过
termination_receipt.json：不存在
返回：PermissionError
```

这不是“整个文件系统不可写”的情形，也没有运行或保存真实训练 checkpoint。它复现的是：一个 common file 的读取故障，阻止了在仍可写目录中记录该故障和已经存在的 checkpoint。

### 最小修复

Fallback 应逐 artifact 捕获读取失败：保留可读文件及已提交 checkpoint 的真实 hash；无法读取的项明确记录为不可用，不能伪造 hash，也不能让它阻止整个失败回执生成。

可利用现有失败 reason 或可写的诊断文件记录不可用项，继续写出 EXECUTION_FAILED receipt，保留真实 step/log count 和 checkpoint presence/identity。不需要修改已审 termination validator，也不要求在不可写文件系统上保证落盘。

## 五、F5 已通过的部分保持关闭

实际注入第 17 行写入后的 gradient flush failure，并检查合法 JSON 尾行与截断 JSON 尾行两种情况。当前实现均保留：

```text
optimizer_steps_completed = 17
fully_logged_updates = 16
confirmed prefix = 16 行
unconfirmed tail = 1 行
```

它不会把尾行升级成已确认更新，也不删除尾部证据；失败臂进入 shared writer 后能够生成 EXECUTION_INVALID，且没有 A25 性能分类。confirmed-prefix/unconfirmed-tail 这部分无需继续修改。

## 六、允许的下一 gate

只需修复上述两个 F5 残余，补充实际函数路径及 I/O 边界的 no-training 回归，再冻结新 exact commit 窄复审。F1–F4、core 和 runner integration 保持关闭，不重新设计 loss、beta、阈值或 protocol。

当前不放行最终执行门。后续 PRODUCER_PACKAGE_READY_PASS 也仅表示代码可进入单独的最终执行审批，不授权 SSH、传输、optimizer training、Taobo launch 或科学结论。
