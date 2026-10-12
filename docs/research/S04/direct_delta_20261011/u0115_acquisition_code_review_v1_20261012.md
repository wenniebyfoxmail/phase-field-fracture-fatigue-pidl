---
review_scope: U0115_PINN_ACQUISITION_CODE_READY_ONLY
status: FAIL
date: 2026-10-12
run_id: pf_u0115_acquire_39f8108fe96d406385e4011700cb47f9
source_commit: b6d56102daa7d45a6c196b72055010170e5f39fb
code_manifest_sha256: a9047ac85a60a7be8dd100446eb6fecda8704714470a117423d7eb77e4b195d8
supervisor_sha256: 9ac0da9ee3e161d3628818db607cee3fea9316eef778b86953d50385b298f0cc
approval_for_launch: false
---

# U0.115 acquisition独立只读Code Ready审核 v1

Verdict：**FAIL — 不释放launch**。本review严格绑定上述两个hash与Run ID。用户对唯一
acquisition的授权保留，代码须修复并取得新hash的re-review；不要求重复科学授权、不改变
acquisition设计。本review不代表G5、PINN physics、FEM teacher或Delta learnability verdict。

唯一执行owner为主对话 `01a1131d-017c-7b03-a95a-ad73ba8fcc9c`。未启动supervisor或训练，
未访问GPU/Windows、未读取科学payload/checkpoint tensors、未编辑被审代码或共享Obsidian。

## 被审包与检查

Package root：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s04-e016-request31-storage-block-20261009/local_archive/experiments/S04-E016/u0115_pinn_acquisition_20261012/`。

- 两个hash与请求一致。
- manifest列出的26文件：26/26 SHA验证PASS，26/26与 `git show b6d56102...:<relative>`
  byte-identical；包内24个Python源码全部AST解析通过。
- 检查exact supervisor command、runner CLI/recovery/cadence、main/config/model_train、
  history更新与保存、archive解析、恢复路径、监督器failure/resource/receipt路径。
- 未import config/main/model_train/runner（config import会创建outputs）；仅AST/源码检查。
  提供的py_compile PASS是syntax evidence，不能证明dependency completeness或进程监管正确。

## Blocking corrections

### B1 [P1] 缺少必需的 field_computation.py

`code/SENS_tensile/main.py:6`：`from field_computation import FieldComputation`。
被审26-file包在 `code/SENS_tensile/` 和 `code/source/` 都没有该module；manifest也没它。
原commit存在 `SENS_tensile/field_computation.py`，其imports的williams_features/enriched_ansatz/
network已在包中，但它本身漏装。

隔离snapshot在main import阶段不能构建model；若依赖环境偶然提供同名module，则反而加载
manifest未绑定的外部实现。不能靠py_compile或producer PYTHONPATH来承认本包完整。

修复：把exact commit的 `SENS_tensile/field_computation.py`纳入archive+manifest，静态核完
local import dependency closure；运行不进入training loop的import/model-construction sanity
需要明确控制main/__main__、config副作用和临时输出。新manifest hash需re-review。

### B2 [P1] 首次receipt失败可留下无监管训练，launch失败无terminal receipt

`supervise.py:72--77`：Popen成功后，第一次 `write('RUN_RECEIPT.json', receipt)` 在
`try/finally`之外。write/rename发生I/O exception会直接退出，child已通过
`start_new_session=True`脱离supervisor；没有kill/wait、没有48h/50GiB监管或terminal failure。
Popen/log创建失败和nonce后的preflight失败也没有统一failure receipt。

`87--102`虽覆盖monitor-loop异常，但不覆盖这些startup边界；SIGTERM也未注册成可控
termination路径。finally内kill/wait再次抛错时同样会跳过terminal write。

修复：从消费nonce前后开始建立统一失败记录边界，尤其Popen至initial receipt必须在
child cleanup guard内；保存original failure、停止/确认自己的child/group，再独立尝试
terminal receipt。处理正常SIGTERM/KeyboardInterrupt；不可依赖SIGKILL的finally。提供
mock child的no-training fault tests：Popen失败、initial receipt write失败、heartbeat失败、
TERM→KILL timeout与kill错误。禁止借此在review期间运行真实PINN。

### B3 [P2] 50GiB只计ARCHIVE，未覆盖全部task-owned outputs或终态

`supervise.py:47--51,71,81--85`：tmp/cache/jitcache、training.log位于ROOT，预算只累计
ARCHIVE。ROOT日志/缓存可以增长但不触发limit；child在两个poll之间写完退出时，也没有
final byte tally检查，可能给出 `EXITED_ZERO_PENDING_AUDIT` 而实际超预算。

48h使用wall clock `time.time()`，不是monotonic elapsed deadline；系统时钟回拨可延长
已授权walltime。10秒poll本来就是soft sampling，不能宣称严格0-byte overshoot。

修复：冻结50GiB计数域为ROOT+ARCHIVE实际task-owned文件，symlink去重且不跟随到无关
路径；bounded periodic tally+final tally，receipt记录overshoot/observed size。用monotonic
elapsed作deadline（UTC timestamps仍可保留）；资源cap命中即stopped/partial，不能当PASS。
no-training fixtures检查ROOT日志/缓存超限、child立即退出后的final超限、clock变化。

### B4 [P1] “fresh ARCHIVE”不足以禁止existing code-side archive自动resume

`supervise.py:29--32`只验证manifest文件，未拒绝unlisted旧output/checkpoints。
`supervise.py:41`只要求ARCHIVE不存在。
`code/SENS_tensile/config.py:453--459` 的 `resolve_archive_dir` 对已经存在的real
`code/SENS_tensile/<dir_name>`直接返回该目录，不使用新的ARCHIVE。
`code/source/model_train.py:1155--1184` 又会自动glob checkpoint并恢复weights/histories；
`1322--1328`在resume时跳过hard-alpha recovery。

当前本地被审snapshot未发现这种旧output，但启动时的代码没有fail-closed控制：向staged
code中放旧目录/成对.pt，不改任何manifest文件，仍可通过verify_code并变成旧状态resume。
这违反本次fresh-only acquisition，不应靠“通常目录是干净的”来通过。

修复可只改supervisor：producer启动前拒绝unlisted源码/已有result directories/old.pt，
验证唯一archive resolved destination处于此次ARCHIVE且不存在；明确记录fresh baseline。
不要删除旧文件来通过guard。no-training contamination test必须证明有old paired .pt时
拒绝spawn。若要改科学runner禁resume则新code hash/physics-source change需重审。

## 其余源码检查结论（不能救上述FAIL）

- command在runner中合法：Umax .115，seed1，8×400、TrainableReLU/init1、RPROP10000、
  LBFGS0、main tol5e-7；两个mesh确属fixed commit；AT1/volumetric、eta0、E1/nu.3/w1=1/l0=.01、
  Carrara/asymptotic、alphaT.5；history current_active与tri3 reduction/irr都显式启用。
- [0,.02875,.0575,.08625,.115,0,...]按120个physical cycles构成601个training steps；
  recovery offset1，s4=5c−1、s5=5c正确。diag cycles1..120使已实际执行的每cycle s4/s5
  被列入diagnostics；601是上限而不是已完成状态数。
- `model_train.py:1814` damage-history max commit、`2103--2202`fatigue更新、`2219--2222`
  previous-driver更新在 `2399--2426`保存之前；weight与history文件都每training step保存。
  s4/s5的checkpoint可用于same-state post-commit export，完整性仍要执行后验证。
- `pre_step0_baseline_diagnostics.npz`与step0 recovery是不同状态，不能用后者代替前者。
  本包baseline diagnostics在hard-current-alpha preset之后被保存；它含alpha_pretrain字段名
  但不应被误解为unmodified pre-preset NN state。G5应保留该精确timing。
- oracle/supervision hooks默认未开启，runner/main没有传入FEM targets；未使用FEM103作为
  stopping signal，也不读取.1175/.125。内置FEMSupervision代码存在不等于启用。
- `fracture_confirm_cycles=3`在此frozen源码中按training-loop j递减，实际是3个后续
  load steps，未乘五。保持历史PINN规则可以，但run card/receipt应写清“3 training steps”，
  不称3个physical cycles；own-event可在s4/s5之外终止，须记录last step/partial final cycle。
- `--optim-rel-tol 5e-7`同时改main与pretrain tol；fixed config pretrain默认1e-6。
  receipt应明确实际pretrain5e-7，不能仅凭参考settings的main tol宣称所有pretrain设置相同。
- 单次 `open('x')`、declared root和child的新session/group是合理机制，但未覆盖fresh/receipt
  failure边界。live GPU/VRAM、其它服务不干预、storage和runtime依赖由唯一owner launch前核对，
  本review未代做这些checks。

## Re-review boundary

修复B1--B4后更新包/manifest/supervisor hash，提供no-training边界tests与fresh preflight。
审核固定新版本再生成PASS review envelope。当前两个hash对应的审批status只能FAIL，
不能把本文改成PASS或将其复用于新hash。用户已授权此唯一acquisition，scope和48h上限保留；
不扩展至D0/NN、额外seed、resume/retry或新FEM。
