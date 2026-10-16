# E019-D01-R001-V01 — 待审批执行包（未执行）

2026-10-16；已确认显示方案v1.1。当前仅代码/测试设计/确切命令与独立静态
审查；不运行测试、导入/语法检查或出图，不读取report内容或真实/留出。
静态审查记录见subspace_display_code_review.md；未获审查通过不请求执行。

## 版本、来源与边界

代码/测试/设计快照：fe190c9260d3a97421606ba96dcfb4df151a7680。
方案SHA256：fa0a408e2b78c54b1160b83b4ece5cad91d698550e671f55fc5f9eea984737bb。
新图器scripts/aa2024_qsubspace_report_view.py；测试tests/test_aa2024_qsubspace_report_view.py；
设计subspace_display_test_design.md。原producer、测试、阈值及冻结输出不改。

唯一绘图数值来源是已存合成R001/analysis/report.json，固定SHA256
f6276a7d474cde6675d99649d8256027edea16902e7c259af2fab24c3535a689。
新图器只复制C1–C3保存ratio/状态，无QR/SVD/eig、Q/投影重算、拟合或FEM。
不读取真实数组、stage15/R003或新留出，无SSH/联网/发送/push。
9.6×5.4in、170dpi、固定布局、symlog/原阈值线1/精确0与负控原义保持。

本轮没有任何运行结果、导入成功、实际预算或布局通过依据。
下列A与B各单线程CPU、CUDA禁用、warnings=error、各自60秒；互不自动串联。
建议先仅审批A人工测试；通过后再单独审批B一次渲染。任何非预期异常即停，
保留取证，不自动重试、修正后重跑、换目录或另开V02；原数值验收仍暂停。

## A — 仅人工单元测试，尚未执行

11个test方法含subtests，不导入Matplotlib/producer，不打开已有report。
新目录固定S03-E019-D01-V01-T001，存在即停；只写新测试日志/收据及人工
临时文件，不覆盖旧T001。unittest failfast，无pytest/conftest/第三方插件。
启动后60秒覆盖身份核对、测试子进程和收据；只终止自身启动的测试进程。

```bash
set -euo pipefail
cd '/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013'
export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export E019_VIEW_TEST_ROOT='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/code_checks/S03-E019-D01-V01-T001'
unset PYTHONPATH PYTHONSTARTUP PYTHONHOME PYTEST_ADDOPTS PYTEST_PLUGINS MATPLOTLIBRC
'/Users/wenxiaofang/miniconda3/bin/python3' -I -B -W error -u - <<'PY'
import time
start=time.monotonic()
import signal
def deadline(signum,frame): raise TimeoutError('A reached 60-second process budget')
signal.signal(signal.SIGALRM,deadline)
signal.setitimer(signal.ITIMER_REAL,max(.001,60-(time.monotonic()-start)))
import hashlib,json,os,socket,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
snapshot='fe190c9260d3a97421606ba96dcfb4df151a7680'
names=['docs/research/S03/S03-E019/subspace_display_plan.md',
       'scripts/aa2024_qsubspace_report_view.py','tests/test_aa2024_qsubspace_report_view.py',
       'docs/research/S03/S03-E019/subspace_display_test_design.md']
threads=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS')
root=Path(os.environ['E019_VIEW_TEST_ROOT'])
if Path.cwd()!=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013'):
    raise ValueError('wrong worktree')
if root.resolve()!=root or root.exists(): raise ValueError('test directory exists or ancestor symlink')
if any(os.environ.get(k)!='1' for k in threads) or os.environ.get('CUDA_VISIBLE_DEVICES')!='':
    raise ValueError('not single-thread CPU')
def bindings():
    out={}
    for name in names:
        path=Path(name)
        if path.is_symlink():raise ValueError('symlink source: '+name)
        data=path.read_bytes()
        if data!=subprocess.check_output(['git','show',snapshot+':'+name]):
            raise ValueError('reviewed source changed: '+name)
        out[name]=hashlib.sha256(data).hexdigest()
    return out
before=bindings()
root.mkdir(exist_ok=False)
receipt=dict(status='running',operation='artificial_view_unit_tests_only',source_commit=snapshot,
             budget_seconds=60,thread_environment={k:os.environ[k] for k in threads},
             sources_before_sha256=before,start_utc=datetime.now(timezone.utc).isoformat(),
             pid=os.getpid(),hostname=socket.gethostname(),cwd=str(Path.cwd()),
             head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
             dirty=subprocess.check_output(['git','status','--porcelain'],text=True),
             command=[sys.executable,'-I','-B','-W','error','tests/test_aa2024_qsubspace_report_view.py'])
try:
    with (root/'tests.log').open('x',encoding='utf-8') as log:
        subprocess.run(receipt['command'],stdout=log,stderr=subprocess.STDOUT,
                       check=True,timeout=max(.001,60-(time.monotonic()-start)))
    after=bindings()
    if before!=after:raise ValueError('source changed during A')
    receipt.update(status='passed',sources_after_sha256=after,
                   tests_log_sha256=hashlib.sha256((root/'tests.log').read_bytes()).hexdigest(),
                   elapsed_seconds=time.monotonic()-start,end_utc=datetime.now(timezone.utc).isoformat())
    if receipt['elapsed_seconds']>=60:raise TimeoutError('A exceeded60s')
    with (root/'test_receipt.json').open('x',encoding='utf-8') as h:json.dump(receipt,h,indent=2,allow_nan=False)
    with (root/'test_receipt.json').open(encoding='utf-8') as h:
        if json.load(h)!=receipt:raise ValueError('receipt readback differs')
    if time.monotonic()-start>=60:raise TimeoutError('A final receipt exceeded60s')
except BaseException as exc:
    receipt.update(status='failed',error=repr(exc),outputs_role='forensic_only',elapsed_seconds=time.monotonic()-start)
    with (root/'test_receipt.json').open('w',encoding='utf-8') as h:json.dump(receipt,h,indent=2,allow_nan=False)
    raise
finally:
    signal.setitimer(signal.ITIMER_REAL,0)
PY
```

## B — A通过后仍单独审批的一次report渲染（尚未执行）

读取新A收据/日志仅核对代码测试身份，不作为绘图数值。固定四源码清单，
不接受收据提供任意路径。B源report只读；独占新目录：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D01/S03-E019-D01-R001-V01/`。
保存PNG/PDF/同名说明、plot_values.json、render_receipt.json、render.log，
仅目录内另有字体缓存。目录存在或任何哈希/schema/布局/预算/新警告异常即停。
新收据rendered只是导出结束，不表示独立图形/原数值验收通过。
实际出图后只读PNG/sidecar/PDF验收另安排，不把该步骤混进原数值验收。

```bash
set -euo pipefail
cd '/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013'
export CUDA_VISIBLE_DEVICES='' PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export MPLCONFIGDIR='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D01/S03-E019-D01-R001-V01/.mplconfig'
export XDG_CACHE_HOME='/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D01/S03-E019-D01-R001-V01/.cache'
unset PYTHONPATH PYTHONSTARTUP PYTHONHOME PYTEST_ADDOPTS PYTEST_PLUGINS MATPLOTLIBRC
'/Users/wenxiaofang/miniconda3/bin/python3' -I -B -W error -u - <<'PY'
import time
start=time.monotonic()
import signal
def deadline(signum,frame): raise TimeoutError('B reached 60-second process budget')
signal.signal(signal.SIGALRM,deadline)
signal.setitimer(signal.ITIMER_REAL,max(.001,60-(time.monotonic()-start)))
import hashlib,json,os,runpy,subprocess
from pathlib import Path
snapshot='fe190c9260d3a97421606ba96dcfb4df151a7680'
names=['docs/research/S03/S03-E019/subspace_display_plan.md',
       'scripts/aa2024_qsubspace_report_view.py','tests/test_aa2024_qsubspace_report_view.py',
       'docs/research/S03/S03-E019/subspace_display_test_design.md']
test=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/code_checks/S03-E019-D01-V01-T001')
if test.resolve()!=test or (test/'test_receipt.json').is_symlink() or (test/'tests.log').is_symlink():
    raise ValueError('test record path is symlink')
with (test/'test_receipt.json').open(encoding='utf-8') as h:r=json.load(h)
threads=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS')
before=r.get('sources_before_sha256',{})
after=r.get('sources_after_sha256',{})
if (not isinstance(before,dict) or not isinstance(after,dict) or set(before)!=set(names) or
    set(after)!=set(names) or before!=after or r.get('source_commit')!=snapshot or
    r.get('status')!='passed' or r.get('operation')!='artificial_view_unit_tests_only' or
    r.get('budget_seconds')!=60 or not 0<=r.get('elapsed_seconds',60)<60 or
    r.get('thread_environment')!={k:'1' for k in threads}):
    raise ValueError('matching A unit tests not passed')
if hashlib.sha256((test/'tests.log').read_bytes()).hexdigest()!=r['tests_log_sha256']:
    raise ValueError('A log changed')
bindings={}
for name in names:
    p=Path(name)
    if p.is_symlink():raise ValueError('symlink source: '+name)
    data=p.read_bytes()
    if data!=subprocess.check_output(['git','show',snapshot+':'+name]):
        raise ValueError('reviewed source changed: '+name)
    bindings[name]=hashlib.sha256(data).hexdigest()
if bindings!=after:raise ValueError('tested source changed')
module=runpy.run_path('scripts/aa2024_qsubspace_report_view.py',run_name='reviewed_view')
try:
    module['render_once'](start,bindings)
finally:
    signal.setitimer(signal.ITIMER_REAL,0)
PY
```

## 执行后的报告范围

报告实际耗时/异常、来源字节、原产物保留、新view路径及独立显示验收状态。
不以渲染成功追认D01算术、真实A/SVD根因或任何反演/预测结论。
无实际测试结果前，建议审批仅A，不同时启动B。
