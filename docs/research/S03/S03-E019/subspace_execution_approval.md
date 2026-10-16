# E019-D01 v1.1 — 未执行代码/测试包与确切待审批命令

2026-10-16。用户已确认v1.1，授权代码、测试设计和命令准备及本地独立
只读代码审查；明确暂不运行诊断或测试。本文件中的所有命令尚未执行。
本轮不做导入检查、py_compile/AST测试、bash-n、pytest、合成算术或绘图。
普通源码/文档阅读、字节哈希和Git差异检查不运行诊断或测试。

## 确切版本与状态

数值/测试/设计快照：8471002db09cd1cb072552b00f3fd736a607b11a。
方案v1.1 SHA256：adbe5d5c9dafbdef0f9db99c231dda5e25840401fd98cac6021b24b320f11be4。
新增scripts/aa2024_qsubspace_diagnostic.py、tests/test_aa2024_qsubspace_diagnostic.py，
测试设计见subspace_test_design.md。旧runner、依赖和E019协议不改。
独立静态审查结论另见subspace_code_review.md；未完成审查不请求执行。

当前没有测试运行数、测试通过率、语法/导入成功、实际预算或图形QA依据。
静态审查通过不等于测试或完整Code Ready。请先只批准A；A通过后，B仍须
人方另行批准，不能在同一shell自动接着运行B。若A失败立即停止、报告，
不自动修复/重试。若B失败，同样不自动重试或换RunID。

## 不变的边界

四固定纯合成用例；零SVD/eig/pinv/lstsq/数值秩，C0仅一次小型薄QR。
单线程CPU、CUDA禁用、warnings=error；A和B各自60秒，非共享预算或自动延长。
B软60秒含模块导入/源码核对/全部参考算术/图/保存/最终成功收据后的检查。
阈值rtol1e-12；matrix/vector/square atol分别1e-12/1e-15/1e-18，原值不变。
C2/C3注入机制的预定负控Qr=r未通过原阈值如实记录；其他异常立即停止。
没有真实字段输入参数，不读取任何真实数组、stage15/R003或新留出；
没有FEM/q/调参/真实A重构/旧结果补投影或修写，不恢复E019真实验收。
不发送文件、联网、SSH或push；原冻结产物不读不写。仅本机新测试/合成目录。

## A — 仅待审批的测试命令（尚未执行）

作用：仅运行新测试文件，不跑包含SVD的旧E019测试；不调用完整diagnostic/run。
输出全新local_archive/code_checks/S03-E019-D01-T001的日志、测试收据和审批副本。
pytest插件自动加载关闭，清除PYTEST_ADDOPTS/PYTEST_PLUGINS，不读conftest、
不写pytest缓存或pyc；-x遇首个非预期测试失败立即停止。
Python wrapper使用60秒剩余时限；超时终止它自己启动的pytest子进程，不重试。
收据与日志均限定代码检查，不混为正式诊断的结果。

```bash
set -euo pipefail
task_repo='/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013'
task_py='/Users/wenxiaofang/miniconda3/bin/python3'
task_check='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/code_checks/S03-E019-D01-T001'
cd "$task_repo"
export PYTHONDONTWRITEBYTECODE=1 PYTHONWARNINGS=error CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 E019_D01_TEST_ROOT="$task_check"
unset PYTEST_ADDOPTS PYTEST_PLUGINS
mkdir -p '/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/code_checks'
mkdir "$task_check"
cp docs/research/S03/S03-E019/subspace_execution_approval.md "$task_check/00_intent_approved.md"
"$task_py" -u - <<'PY' > "$task_check/tests.log" 2>&1
import hashlib,json,os,socket,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
start=time.monotonic()
root=Path(os.environ['E019_D01_TEST_ROOT'])
snapshot='8471002db09cd1cb072552b00f3fd736a607b11a'
names=['docs/research/S03/S03-E019/subspace_localisation_plan.md',
       'docs/research/S03/S03-E019/experiment.md',
       'scripts/aa2024_kinematic_capacity.py','scripts/aa2024_geometry_prior.py',
       'scripts/aa2024_boundary_basis.py','scripts/aa2024_triplet_structure.py',
       'scripts/aa2024_patch_mechanics.py','scripts/aa2024_rigid_observable.py',
       'scripts/aa2024_qsubspace_diagnostic.py','tests/test_aa2024_qsubspace_diagnostic.py',
       'docs/research/S03/S03-E019/subspace_test_design.md']
def bindings():
    out={}
    for name in names:
        data=Path(name).read_bytes()
        if data!=subprocess.check_output(['git','show',snapshot+':'+name]):
            raise ValueError('reviewed source changed: '+name)
        out[name]=hashlib.sha256(data).hexdigest()
    return out
def save(receipt):
    with (root/'test_receipt.json').open('w') as handle:
        json.dump(receipt,handle,indent=2,allow_nan=False)
        handle.write('\n')
receipt=dict(status='running',source_commit=snapshot,budget_seconds=60.,
             start_utc=datetime.now(timezone.utc).isoformat(),
             role='synthetic unit tests only, not diagnostic/E019 acceptance',
             pid=os.getpid(),hostname=socket.gethostname(),cwd=str(Path.cwd()),
             thread_environment={k:os.environ.get(k) for k in
                                 ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
                                  'VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS')},
             pytest_environment={k:os.environ.get(k) for k in
                                 ('PYTEST_DISABLE_PLUGIN_AUTOLOAD','PYTEST_ADDOPTS','PYTEST_PLUGINS')},
             command=[sys.executable,'-m','pytest','-x','--noconftest','-c','/dev/null',
                                    '-p','no:cacheprovider','-W','error','-q',
                                    'tests/test_aa2024_qsubspace_diagnostic.py'])
try:
    before=bindings()
    receipt['sources_before_sha256']=before
    remaining=60.-(time.monotonic()-start)
    if remaining<=0:raise TimeoutError('test preparation exhausted60s')
    subprocess.run(receipt['command'],check=True,timeout=remaining)
    after=bindings()
    if before!=after:raise ValueError('test source changed')
    receipt.update(status='passed',sources_after_sha256=after,
                   elapsed_seconds=time.monotonic()-start,end_utc=datetime.now(timezone.utc).isoformat(),
                   tests_log_sha256=hashlib.sha256((root/'tests.log').read_bytes()).hexdigest())
    if receipt['elapsed_seconds']>=60.:raise TimeoutError('tests exceeded60s')
    save(receipt)
    if time.monotonic()-start>=60.:raise TimeoutError('final test receipt exceeded60s')
except Exception as exc:
    receipt.update(status='failed',error=repr(exc),outputs_role='forensic_only',
                   elapsed_seconds=time.monotonic()-start,end_utc=datetime.now(timezone.utc).isoformat())
    save(receipt)
    raise
PY
```

## B — 测试通过后仍需单独审批的一次合成诊断（尚未执行）

本段不是A的继续命令。本轮不运行。未来先核对同一快照的T001成功收据、
源码前后哈希及日志字节，再创建唯一新S03-E019-D01-R001；任何缺失/不符即停。
完整6产物与成功/失败收据见测试设计。B执行之后另做独立只读数值/图形
验收，不自动再运行任何分析。原E019-R001继续保留原失败记录。

```bash
set -euo pipefail
task_repo='/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013'
task_py='/Users/wenxiaofang/miniconda3/bin/python3'
task_run='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D01/S03-E019-D01-R001'
cd "$task_repo"
export PYTHONDONTWRITEBYTECODE=1 PYTHONWARNINGS=error CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
"$task_py" - <<'PY'
import hashlib,json,subprocess
from pathlib import Path
root=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/code_checks/S03-E019-D01-T001')
r=json.loads((root/'test_receipt.json').read_text())
snapshot='8471002db09cd1cb072552b00f3fd736a607b11a'
names=['docs/research/S03/S03-E019/subspace_localisation_plan.md',
       'docs/research/S03/S03-E019/experiment.md',
       'scripts/aa2024_kinematic_capacity.py','scripts/aa2024_geometry_prior.py',
       'scripts/aa2024_boundary_basis.py','scripts/aa2024_triplet_structure.py',
       'scripts/aa2024_patch_mechanics.py','scripts/aa2024_rigid_observable.py',
       'scripts/aa2024_qsubspace_diagnostic.py','tests/test_aa2024_qsubspace_diagnostic.py',
       'docs/research/S03/S03-E019/subspace_test_design.md']
before=r.get('sources_before_sha256',{})
after=r.get('sources_after_sha256',{})
if not isinstance(before,dict) or not isinstance(after,dict) or set(before)!=set(names) or set(after)!=set(names):
    raise ValueError('test receipt source keys differ from fixed allowlist')
if (r.get('status')!='passed' or r.get('source_commit')!=snapshot or
    r.get('budget_seconds')!=60. or not 0<=r.get('elapsed_seconds',60.)<60. or
    before!=after or
    r.get('thread_environment')!={k:'1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
                                               'VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS')} or
    r.get('pytest_environment')!={'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTEST_ADDOPTS':None,'PYTEST_PLUGINS':None}):
    raise ValueError('reviewed synthetic unit tests not qualified')
if hashlib.sha256((root/'tests.log').read_bytes()).hexdigest()!=r['tests_log_sha256']:
    raise ValueError('test log changed')
for name in names:
    digest=after[name]
    data=Path(name).read_bytes()
    if hashlib.sha256(data).hexdigest()!=digest or data!=subprocess.check_output(['git','show',snapshot+':'+name]):
        raise ValueError('tested source changed: '+name)
PY
mkdir -p '/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D01'
mkdir "$task_run"
cp docs/research/S03/S03-E019/subspace_execution_approval.md "$task_run/00_intent_approved.md"
"$task_py" -u scripts/aa2024_qsubspace_diagnostic.py \
  --output "$task_run/analysis" \
  --source-commit 8471002db09cd1cb072552b00f3fd736a607b11a \
  > "$task_run/run.log" 2>&1
```

## 当前请求与禁止扩大

当前先完成独立静态代码/命令审查并向用户展示，尚不请求自动执行B。
如获批执行A且全部通过，另报告实测结果，再请求B的单独一次权限。
没有对外发件账号、收件人、附件或承诺；不涉及任何文件发送。
