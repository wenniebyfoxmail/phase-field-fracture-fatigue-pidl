
<!-- HYBRID_TRAINING_READINESS_20261024 -->
**2026-10-24当前入口：** [R2终态、R3–R008全链费用与训练安排](../training_readiness_20261024.md)。R2已首停，后续至R008仍0完整teacher/0fit；D21禁用且旧时钟过期。复用现成D21，不回退旧600秒候选；先补labels出口，再1800标签→一次fit→测试。

> 当前任务管理条款见 [current_entry.md](current_entry.md)（2026-10-20前瞻修订）。下文为已有运行快照；本次迁移未查询生产状态，未修改已用执行卡或签名记录。

# Complete hybrid comparison — submitted and running

Run `pf_hybrid_complete_20261020_r2` on GPUServer8/drtao, source d703e3c8, exact card f3cc0463, original3600 steps/onefit/12GPUh/136hosth envelope. User's conditional authority and exact independent review were satisfied before this single dispatch. No material/property extension launched.

At 2026-10-20T19:05:11.699238+01:00, actual supervisorPID3210955 and train_A workerPID3211535 were running with verified cwd/cmdline/etime. Outer GNUtimeout PID3210954 is distinct from the supervisor. Started 2026-10-20T19:04:35.768586+01:00. Real six imports matched, including torch2.7.0+cu126; Matplotlib3.10.3 guarded Agg PNG/PDF passed. Known five-state operator replay passed original1e-10. train_A has0accepted substeps at this snapshot; no complete trajectory/fit/acceleration result yet.

Known prior wall625.6987804058008s is charged once. Finaldispatch measured local5.258660624967888s is recorded separately; the outer deadline already subtracts45s unspent dispatch plus45s cleanup reserve (not actual costs). Actual per-case elapsed comes from `cost_ledger.json → phases[case].wall_seconds`; ongoing monitor elapsed is partial only. Run/attempts and failure elapsed are retained. No automatic retry/rebind/install. Runtime success is not numerical/physical success.

[Exact independent review](execution_review.md) / [tracked run receipt](run_receipt.json). Remote primary `/mnt/data2/drtao/wennie/pf_hybrid_complete_20261020_r2`, archive `/mnt/data2/drtao/pidl_archives/pf_hybrid_complete_20261020_r2`, log `supervisor.log`. Local packet and source/read-only monitor snapshots: `/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/research/fem_surrogate_comparison_preparation_20261020/execution_v1`. Scientific archive retrieval is not yet complete; local snapshots are partial evidence only. Future inspection must use this exact run/ownedPID identity and preserve stopped receipts; timeout exit124/137 or missingterminal with absentprocess cannot be called successful.

Latest read-only check 2026-10-20T19:06:47.862089+01:00: supervisor/worker still alive, train_A accepted1/600, first accepted substep including recorded IO/features34.249059395864606s. Ongoing case monitor elapsed118.861561675556s, not finalcaseelapsed. No terminal/failure. No scientific speedup inference from this one step.
