---
review_scope: U0115_PINN_ACQUISITION_CODE_READY_ONLY
status: FAIL
date: 2026-10-12
run_id: pf_u0115_acquire_39f8108fe96d406385e4011700cb47f9
source_commit: b6d56102daa7d45a6c196b72055010170e5f39fb
code_manifest_sha256: 2ad7b6a3a6001e4f9d4d6d4bddd3650352a04d43d8a1f7a4044cbfd302301f6c
supervisor_sha256: 08f2f5b9a94392d7888493e5fef602d1f2a56029db465fefd794504aa4940895
approval_for_launch: false
---

# U0.115 acquisition Code Ready v2只读复审

**FAIL，不能生成PASS envelope。** 旧v1 FAIL保留；本判决绑定以上新hash，科学授权保留，
主对话仍为唯一执行owner。本review没有运行真实training或修改被审包/Obsidian。

## 已修复并实核通过

- 新manifest200文件：200/200 SHA验证、200/200 byte-identical到fixed Git commit；
  `field_computation.py`已纳入，v1 B1关闭。源码package当前没有.pt文件。
- exactcommand未变。逐cycle s4/s5、weights+history保存、causal post-commit timing、无FEM
  oracle的源码判断继承v1；此项仍只是code capability，不是acquisition/G5 scientific PASS。
- 首RUN_RECEIPT write已移至Popen后的try/finally，首receipt失败时子组cleanup测试通过。
- ROOT+ARCHIVE已纳入periodic预算计数；ROOT日志/缓存遗漏修复。
- 实际重跑 `test_supervisor.py`，3/3 mocked-child tests PASS（walltime、workspace超预算、
  first receipt failure cleanup）。没有training Popen，GPU未使用。

## 仍阻断的边界

### R1 [P1] Startup失败没有terminal receipt；TERM/cleanup error边界仍未保护

`supervise.py:39--74` nonce/preflight/log创建/Popen仍在统一failure receipt范围之外。
我独立做的no-training mock：Popen抛OSError，结果为

```json
{"mock_spawn_failure":true,"launch_consumed_exists":true,"terminal_receipt_exists":false,"real_training_launched":false,"popen_mock_calls":1,"kill_mock_calls":0}
```

即single-use launch已经被消费，但没有RUN_RECEIPT告知startup失败。补做Popen失败路径
的terminal failure记录；日志/nonce/preflight异常也需可追溯status。
`supervise.py:94--105` kill/wait出错仍可跳过terminal receipt；无SIGTERM handler，给supervisor
正常TERM不会进入finally，而child在独立session中，可失去48h监管。将终态写入与cleanup
错误独立处理，记录group是否已停止；提供TERM、kill-error的mock tests。

### R2 [P2] Final预算与monotonic deadline仍缺少

`79--89`只在child poll返回None时计数，child在两次poll间结束不会做final byte tally。
`102--105`也没有final资源检查，可以给出EXITED_ZERO_PENDING_AUDIT但实际已超过50GiB。
当前3个tests未覆盖“退出时超限”。补final ROOT+ARCHIVE计数和明确cap outcome。
`64,80`仍用time.time进行48h判断；elapsed预算应改monotonic，UTC timestamp单独保留。
10秒周期检查是soft sampling，receipt需记录实际size/elapsed与可能overshoot，不称绝对硬限。

### R3 [P1] Runtime fresh-only仍没有封住code-side旧archive绕路

“旧恢复只可能在fresh ARCHIVE内部”与fixed source不符：

- `config.py:453--459`发现已有real `code/SENS_tensile/<dir_name>`便直接返回它，绕过ARCHIVE。
- `model_train.py:770--775`可读旧initTraining weights，`1155--1184`可自动恢复旧step+history；
  recovery guard随后会skip hard-alpha initialization。
- `supervise.py:29--32`验证listed files，41只检查ARCHIVE不存在；不拒绝code里的旧result
  directory或.pt。现有本地snapshot干净是一次inspection，并非运行时的fresh-only guard。

修复无需改frozenphysics源码：在supervisor检查code tree只含manifest源码与允许的compile
artifacts、拒绝所有已有result directories/.pt/外部symlink，并核result resolved destination。
或者提供同等强度、hash-bound的launch-sidefresh检查及不可变staging合同。禁止删除旧文件
来让检查通过。添加污染fixture，证明code-side成对old.pt会在spawn前拒绝。

## 边界说明与下一步

已有3/3测试是必要的局部修复证据，不覆盖R1--R3。v1所述pretrain tolerance和fracture
confirmation按training-step j递减应写入run receipt。源码另确认 `model_train.py:793`
以 `max(n_epochs_LBFGS,1)`让pretraining至少执行1个LBFGS epoch，即config的LBFGS0
不等于全程零LBFGS；这是frozenfamily行为，也须如实记录。
无需为了改这些历史family行为重新设计physics，只需如实记录实际执行语义。

补齐上述supervisor边界并提供新hash/no-training tests后re-review。本轮结束交回唯一owner；
没有launch、restart、export、D0或NN。被审包目录同v1，review只保存在独立方法worktree。
