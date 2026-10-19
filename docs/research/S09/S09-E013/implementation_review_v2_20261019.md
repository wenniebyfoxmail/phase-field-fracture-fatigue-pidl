# S09-E013 implementation review v2 (ChatGPT Pro, Haofan)

- Reviewed commit: `70f802cb51b4fe411c31073dd939fd6ae8c62fa3`
- Conversation: https://chatgpt.com/c/6ad49578-9328-832b-b4ee-bfe121ff38eb
- Account: Haofan
- Verdict: `REVISE_AND_REREVIEW`

## Review transcript

REVISE_AND_REREVIEW

本轮结论绑定你声明的 candidate 70f802cb51b4fe411c31073dd939fd6ae8c62fa3。

R1、R2 已闭合；R3 的逐项 deadline 与部分 progress 保留也已闭合。仍有两处最小修复：最终状态哈希之后缺少 publication deadline 检查，以及新增 standalone identity gate 没有覆盖 standalone 脚本本身。 未发现需要重开 E009–E012 generic producer/core 的问题。

1. 已独立确认的闭合项
R1：准入条件已闭合

我重放了上一轮使用一致 per-cycle Jacobians 的反例，并检查了边界：

检查	v2 observed
六个 zero contrasts、两个 helpful；L25 helpful=2、G25=0、保护集合17、crossings=3	STOP，usable count=2
八个 contrasts 全部 usable，但 global protected count=12	STOP
八个 usable、冻结的17个 protected identities、directional gain 成立	READY
gradient norm 为 NORM_EPSILON/2 或恰好 NORM_EPSILON	STOP
gradient norm 为 nextafter(NORM_EPSILON, +inf)	READY
缺失、重复、增加、未知 cycle、替换 cohort identity	全部拒绝
protected crossings=3 / 4	分别通过 / STOP
非有限 local gradient 或 wrong-local margin change	拒绝

这里使用的是 v2 明确冻结的 finite 且 norm 严格大于 NORM_EPSILON，没有引入 E012 的其他相对敏感性阈值。

虽然 classifier 没有额外单写一个 all-pair set comparison，但“25条记录 + 精确八成员 wrong set + 精确互补十七成员 protected set”的约束已经足以排除遗漏和重复；生成顺序仍由 PAIR_ORDER 固定。

R2：保存端点与 local primary 已闭合

上一轮的空间重分配反例现在通过正确的保存端点计算结果：

扰动 live L25 fields，可使 live local score 从28变为50，同时保持 global amplitude 最大差仅 2.168404344971009e-19。
保存的两臂 checkpoint 对应 local score 均为28。
v2 在 local metrics 之前严格 reload checkpoint，并将同一份重建 fields 交给 metrics、classification、NPZ 和 figures。

独立复现结果为：

纯文本
decision delta_pair_score = 0
NPZ-recomputed delta_pair_score = 0
scientific_status = NO_REALISED_LOCAL_SIGNAL

上一轮错误的 delta=22 / ROBUST_LOCAL_OBJECTIVE_REPAIR 不再出现。新增的 initially-correct-local losses 也已接入相同的初始身份和重建端点结果。

R3：原始循环超时反例已闭合

模拟 deadline=3600，首项工作在3599开始、3601结束：

Audit 只完成一个 pair/arm；先写入并 flush 一条完整 progress record，随后抛出超时，没有进入第二项。
Endpoint field replay 只进入一个 cycle。
Endpoint local-metric calculation 只进入一个 cycle。

因此，上一轮“超时后继续启动49项/31项工作”的反例已经关闭。

新增 G25 replay gate：连接正确

我独立重哈希并以受限解码方式读取了归档 E011 ranking checkpoint 的实际 tensor/storage 内容，核对了：

SHA256：a3f2f83bd2c86f8bc3a455c899ddc5ea0d5e394b8b6f5930950d4e5dbb024c8d
53个 model entries，包含 buffers；
50个 AdamW parameter states，1个 parameter group。

当前递归 comparator 接受匹配状态，并拒绝 model value、exp_avg 的单 ULP 改动，以及 step、dtype、optimizer epsilon 改动。

实际 dispatch-loop AST 的故障注入顺序也正确：

纯文本
匹配：G25 result → verify → 写 replay evidence → L25
失配：G25 result → verify 抛错；保留 G25 result；不进入 L25

冻结 E011 decision 的 8 repairs / 5 losses 与 0 repairs / 0 losses 也已正确解析。以上是实现检查，不表示 E013 的真实 G25 执行已经完成。

2. 剩余 blocker A：最终状态哈希跨过 deadline 后仍发布 READY

目标：

source/s09_e013_producer.py，zero_step_audit()，约第544–551行；
同文件 run_producer()，约第1320–1321行。

当前顺序是：

Python
_check_deadline(deadline, "zero_step:before_admission_publication")
summary = _classify_zero_step_records(records)
_require(parameter_state_sha256(runtime.model) == before_hash, ...)
_require(_optimizer_state_sha256(optimizer) == optimizer_hash, ...)
return {"status": ..., ...}

调用者随后先写 audit，再检查 deadline：

Python
_write_json(output_dir / "zero_step_audit.json", audit)
_check_deadline(deadline, "zero_step_after")
已执行反例

所有50项 audit collection 在 deadline 前完成；最后一次 deadline check 在3599通过。仅让最终 optimizer-state serialization/hash 耗时2秒，返回的 hash 保持不变。

执行当前 audit 和实际调用片段后：

纯文本
50 progress records retained
zero_step_audit.json written at 3601
written status = ZERO_STEP_DIRECTION_READY
then: WALL_TIME_CAP_REACHED:zero_step_after

Expected： 状态验证完成时已经超时，不发布 READY；保留 progress，进入失败收尾。
Observed： 超时后先发布 READY，随后才拒绝。

现有 producer 外层检查仍阻止训练开始，所以这不是 deadline 后 optimizer step 的反例。问题是明确可耗时的状态验证被放到了最后一次检查之后。Standalone 的新增 receipt 写入段也没有补上返回后的最后检查。

可执行回归

以下测试可追加到本轮 E013 测试文件，复用其中已有的 producer、_audit_fixture、SimpleNamespace 和 pytest。它抽取实际 audit 的全部 post-loop closure，不执行 forward、autograd 或 optimizer：

Python
def test_audit_close_rejects_deadline_crossed_by_final_hash(monkeypatch):
    import ast
    import inspect

    node = ast.parse(inspect.getsource(producer.zero_step_audit)).body[0]
    last_loop = max(
        i for i, statement in enumerate(node.body)
        if isinstance(statement, ast.For)
    )
    node.body = node.body[last_loop + 1:]
    node.name = "_review_audit_close"
    node.args = ast.arguments(
        posonlyargs=[], args=[], vararg=None,
        kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[],
    )
    node.returns = None

    clock = [3599.0]
    monkeypatch.setattr(producer.time, "time", lambda: clock[0])

    def final_optimizer_hash(_):
        clock[0] += 2.0
        return "same-optimizer"

    namespace = dict(vars(producer))
    namespace.update(
        records=_audit_fixture(),
        runtime=SimpleNamespace(model=object()),
        optimizer=object(),
        before_hash="same-model",
        optimizer_hash="same-optimizer",
        deadline=3600.0,
        parameter_state_sha256=lambda _: "same-model",
        _optimizer_state_sha256=final_optimizer_hash,
    )
    module = ast.fix_missing_locations(
        ast.Module(body=[node], type_ignores=[])
    )
    exec(compile(module, "<actual-audit-close>", "exec"), namespace)

    with pytest.raises(TimeoutError):
        namespace["_review_audit_close"]()

当前候选会返回 READY，因此最后的 pytest.raises 失败。

最小修复：

将 final deadline check 放在 summary 和两项状态哈希验证之后。
在 producer 写 zero_step_audit.json 之前再次检查同一个 deadline。
Standalone 保存该绝对 deadline，并在最终 receipt 发布前检查；不要为发布阶段重置计时。
3. 剩余 blocker B：standalone 的 clean gate 漏掉正在执行的入口文件

目标：

scripts/check_s09_e013_zero_step.py :: main()，patch中的第45–46行；
source/s09_e013_producer.py :: PRODUCER_FILES，第90行附近；
_execution_files_clean()，第248行附近。

新增 standalone 入口要求：

Python
current_commit(ROOT) == args.expected_commit
and _execution_files_clean(ROOT)

但被检查的 paths 只有：

Python
"source"
"scripts/run_s09_e013_producer.py"
"docs/research/S09/S09-E013/experiment.md"
"docs/research/S09/S09-E013/run_config.json"

没有 scripts/check_s09_e013_zero_step.py。

已执行反例

使用实际 _execution_files_clean() 和临时 Git repository：

Commit source 与 standalone entry。
记录真实 HEAD。
仅修改已 tracked 的 standalone entry。
重做新入口采用的 commit + clean 检查。

结果：

纯文本
HEAD == expected_commit                         True
_execution_files_clean(repo)                    True
standalone entry differs from committed version True

修改 source 文件则会正确拒绝，说明缺口确实是 pathspec 漏项。

Expected： 正在执行的 standalone 脚本有未提交改动，在 runtime/audit 前拒绝。
Observed： exact-commit 与 clean predicates 同时通过。

可执行回归
Python
def test_standalone_entry_drift_is_rejected(tmp_path):
    import subprocess

    repo = tmp_path / "repo"
    entry = repo / "scripts/check_s09_e013_zero_step.py"
    dependency = repo / "source/dependency.py"
    entry.parent.mkdir(parents=True)
    dependency.parent.mkdir(parents=True)
    entry.write_text("pass\n")
    dependency.write_text("pass\n")

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=repo, check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    git("init", "-q")
    git("add", ".")
    git(
        "-c", "user.name=Review Fixture",
        "-c", "user.email=review@example.invalid",
        "commit", "-qm", "fixture",
    )
    expected_commit = git("rev-parse", "HEAD")
    assert producer._execution_files_clean(repo)

    entry.write_text("pass\n# unreviewed entry change\n")
    assert git("rev-parse", "HEAD") == expected_commit
    assert not producer._execution_files_clean(repo)

当前候选在最后一行失败。

最小修复： 将 standalone entry 加入 clean set，或为 standalone 建立包含自身及相同依赖的专用集合。无需改变任何 numerical objective、预算或执行设计。

4. 身份与复现边界

我从 inline patch 重建并核对了以下六个文件的 Git blob hash，与 patch 中的目标前缀一致：

文件	匹配的 blob 前缀
Protocol	3f8c9d00
Run config	03b9573d
Producer CLI	e11951c4
Core	57a17cf9
Producer	5d62e568
Tests	c081daf1

另外，protocol 与 canonical run config 的 SHA256 均与新绑定常量一致。Producer CLI 保留了 --execute-reviewed-run guard，并正确传入新增 ranking-checkpoint 参数。

Standalone 未提供的旧文件内容不能完整认证；本次对它的 finding 只依赖明确贴出的新增 gate 和已完整核对的 PRODUCER_FILES。Archive SHA256、完整 Git commit object 未独立核验。 这与没有 GPU 执行一样，都不是本轮阻断原因。

本环境未安装 PyTorch/pytest，没有重跑提交方的30 tests。独立执行采用实际函数 AST、NumPy 替身、归档字段、模拟时钟及临时 Git 仓库；没有真实模型 forward/autograd、optimizer step、producer execution、FEM 或 holdout access。

Optional

Standalone 的 open("xb") 确实拒绝覆盖已有 receipt/progress。可在构建 runtime 前同时检查两个输出路径，避免“receipt 已存在但 progress 不存在”时，完成 audit 后才发现无法写 receipt。这是减少无用计算的改进，不列为第三个 blocker。

下一轮只需复核上述 publication deadline 顺序与 standalone self-file identity coverage 两项及其直接回归；R1、R2和本轮已验证的 replay gate 保持关闭。
