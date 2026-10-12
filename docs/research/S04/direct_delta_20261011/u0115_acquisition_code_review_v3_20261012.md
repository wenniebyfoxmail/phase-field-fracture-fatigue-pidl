---
review_scope: U0115_PINN_ACQUISITION_CODE_READY_ONLY
status: PASS
date: 2026-10-12
run_id: pf_u0115_acquire_39f8108fe96d406385e4011700cb47f9
source_commit: b6d56102daa7d45a6c196b72055010170e5f39fb
code_manifest_sha256: 2ad7b6a3a6001e4f9d4d6d4bddd3650352a04d43d8a1f7a4044cbfd302301f6c
supervisor_sha256: fccba7a4ccf204c28a55c3482932b15fe154b0d73b71a372279864972a682e7b
---

# U0.115 acquisition Code Ready最终只读审核 v3

**PASS — 限这条用户已授权的唯一acquisition。** 独立审核只释放Code Ready；唯一owner
`01a1131d-017c-7b03-a95a-ad73ba8fcc9c`须在launch前完成live GPU/storage/runtime与远程
snapshot身份核对。本review不启动任务；G5/data lock、完成状态、PINN/FEM physics、teacher
qualification、D0/Delta NN仍不由此获得PASS或授权。旧v1/v2 FAIL保留，不能改写。

Machine-readable review envelope见同目录
`u0115_acquisition_CODE_REVIEW_v3_20261012.json`；只绑定以上两个最终hash与Run ID。
任何源/command/supervisor变更均使本PASS失效。

## 核查对象与exact scope

主worktree package：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-e016-request31-storage-block-20261009/local_archive/experiments/S04-E016/u0115_pinn_acquisition_20261012/`。

fixed commit `b6d56102...`、manifest200files包含必要field_computation，source/core没有改动。
Umax.115、seed1、8×400/init1/TrainableReLU、RPROP10000、LBFGS config0、tol5e-7、
tri3 history-driver/irreversibility、hard-alpha recovery、[.25,.5,.75,1,0]；上限120physical
cycles/601training steps，保留原PINN自身fracture confirmation停止。逐cycle s4/s5输出和
weights/history保存能力继承v1/v2的fixed-core检查，无FEMoracle/.1175/.125输入。

scope为fresh Run，无retry/resume/额外seed；单GPU、48h/50GiB task-owned资源监管。
配置的LBFGS0在frozen pretraining仍有至少1个LBFGS epoch；pretrain tol被CLI设为5e-7；
fracture confirmation的3按training steps递减，非3physical cycles。owner在实际receipt记录
这些语义、last state与own-event/censor，不把601steps当作已完成状态。

## v2阻断项的闭合

| 项 | 最终源码/验证 | 结论 |
|---|---|---|
| R1启动/receipt失败 | execute置于main外层failure receipt边界；Popen/log/初receipt在protected scope；SIGTERM/INT转SystemExit；TERM/KILL错误单列、child_stopped与FAILED_CLEANUP | 关闭 |
| R2资源cap | monotonic elapsed；ROOT+ARCHIVE periodic和final计数；final超限或计数失败不能变成成功；cutoff提前30s留poll/TERM grace；实际elapsed/bytes写入receipt | 关闭，属于periodic supervisory cap，非filesystem硬quota |
| R3fresh-only | spawn前manifest exact file-set、code-side symlink拒绝（pycache允许）；archive不存在；LAUNCH_CONSUMED exclusive；重复invocation在main顶部拒绝，不能改写先前receipt | 关闭 |

cleanup无法停止child时明确FAILED_CLEANUP，不能当作合格完成。SIGKILL/host failure无法保证
Python finally执行，属于infra failure与后续live状态核对，不应伪称成功。执行owner不干预
其它GPU小服务，只能监管由该Popen创建的任务组；没有全用户pkill行为。

## 实际完成的no-training验证

- manifest200/200 SHA与fixed Git bytes验证（v2）通过；最终再次核200/200 SHA、exact
  file set、0extra/0missing/0symlink，supervisor AST与最终两hash匹配。
- supplied `test_supervisor.py` 的6/6 mocked-child tests实跑PASS：walltime、workspace
  budget、initial receipt cleanup、spawn failure terminal、final budget、TERM handler。
- 独立verify-only fixtures3/3 PASS：clean staged code通过；code-side成对old.pt拒绝；
  code-side symlink拒绝。fixture没有反序列化tensor。
- 独立protected-cleanup fixtures3/3 PASS：monitor内TERM异常→signal status且child_stopped；
  TERM wait timeout→KILL且stopped；两次cleanup failure→FAILED_CLEANUP且stopped=false。
  所有kill调用都被mock并指向同一fake child PID，无真实Popen/GPU/进程终止。
- 测试fixture仅写本地temporary test目录，未改被审source、Windows/G5记录或共享Obsidian。

供重放的provided tests SHA256：
`a9e7336d0b5752aaeda77465235141e11f7dc00bbfee5ec3a90ced1f33dec438`。
独立fixture结果均于最终hash `fccba7a4...`下检查；没有使用training循环作测试。

## Run Ready前唯一owner仍需做的检查

远程两hash+200-file身份及干净staging、single-use nonce未消费、fresh ARCHIVE、已选唯一
CUDA_VISIBLE_DEVICES、GPU余量与storage、Python/torch依赖、detached supervisor运行方式。
使用普通未优化Python运行hash guards（不启用-O/PYTHONOPTIMIZE）；不要编辑通过后的包。
这些是已约定launch前检查，不是需要新增科学授权的步骤。Start成功只记录RUNNING；
completed/partial/event/checkpoint coverage须另审，U0.1175仍sealed，U0.125仍excluded。

当前blocking corrections：**无**。本方法review结束，交回唯一owner执行授权范围内launch。
