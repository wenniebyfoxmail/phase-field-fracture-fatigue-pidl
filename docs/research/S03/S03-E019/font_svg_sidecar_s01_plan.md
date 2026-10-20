# F01-V001-S01 新说明及映射收据方案 v1 — 仅准备，未执行

2026-10-20（Europe/London）。本轮只准备此方案/内嵌命令及现有owner里程碑，
不执行修订、测试或继续验收，不打开图。不另读V001原图/说明内容或哈希，
不读取B003数值、真实数组或留出。文字与身份依据既有独立验收记录。

## 目的与复用决定

目标仍为真实DIC到状态反演；本项仅澄清显示说明，不能代替数值/物理验证。
沿用F01 D3与[独立停验记录](font_svg_display_evidence_review.md)：命令1结构
与保存值映射已通过，说明语义未通过，两图未目视。复用既有D1，不重开实验。
owner为本聊天S03-E019-D03-F01。本项既不重跑原B，也不恢复原验收。

参考既有D02 companion修订方法，只做一条确切句子的字节替换；不修改其旧
脚本或拿旧静态通过替新命令背书。本命令仅做文字/哈希/映射，不增加测试
台阶；当前未独立静态复审、未导入/编译或动态测试，不声称执行已通过。

## 唯一文字修订（每份一次，其他字节不变）

在原residuals.md和square_ledger.md中，各仅替换一次：

原文：

```text
No caching, interpolation or smoothing.
```

新文（完整一行）：

```text
No caching. RGB interpolation is used only for the residual colour scale. It does not interpolate point data in space; no spatial interpolation or smoothing of point data is performed.
```

含义：只在已有残差值到颜色的映射中做RGB色标插值，不在空间中补点或平滑。
“No caching”原意保留，不在此项增加缓存行为解释或新声明。两份说明统一
这一个术语，账本说明中的澄清明确指残差色标，并非声称账本柱图做了RGB插值。
不改标题、面板、色标、数据、数值解释、来源或限制，不给图补充优劣判断。

## 来源、仅新增文件和映射

固定目录：

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001
```

若另行获批，仅新增以下三份文件，全部使用xb独占创建：

| 已有图（不改） | 原同名说明（不改） | 新companion |
|---|---|---|
| residuals.svg | residuals.md | residuals.sidecar_s01.md |
| square_ledger.svg | square_ledger.md | square_ledger.sidecar_s01.md |

新收据：`sidecar_mapping_s01.receipt.json`，记录原七件SHA前后不变、
每图绝对路径/SHA、原说明路径/SHA、新说明路径/SHA、唯一old/new替换及次数、
环境/时间口径和“只生成文本、未验收”身份。不改derived_receipt/completion。

选择原目录新增companion，而非迁移说明到新目录，是为保留说明中
`Same-directory derived_receipt.json`的真实指向。原七件字节全部保留，
但目录成员将从7变为10，这属于本次明确申请的新增范围。未来验收必须
前瞻性采用“原七件＋新三件”和显式SVG→companion映射；原方案的恰好七件
条件不再直接适用，不能改旧方案或冒称旧命令已通过。普通same-stem检查
仍会找到旧说明；本修订不运行validator，也不宣称目录/说明已独立验收。

本轮仅用路径元数据确认三个新文件均不存在，未据此声明其可用性或源内容
当前有效。启动前须重新核对；任何目标已存在（含坏软链）即停止，不覆盖、
删除、改名换号或重试。不会创建前期考虑过的另一个S01目录。

## 执行范围与停止规则

拟批准后一次执行：单线程CPU、60秒软预算、零SVD/QR；标准库字节替换、
哈希/JSON及新增三文件读回自检。七原件仅为身份完整性读字节/hash，SVG不
解析或显示，说明不解析/重算其科学量，原收据/完成标记只hash、不随其路径
扩大读取范围。不读B003 certificate/report或其他Run/真实/stage15/新留出。

不导入NumPy/SciPy/Matplotlib/producer/verifier，不生成或转换图片、不启动
字体缓存，不预热、不豁免字体日志；不运行原验收命令、测试或C/D。
warnings-as-errors和标准logging WARNING及以上首停；无预登记日志例外。
计时从首次time导入后开始，包含后续标准库加载/读写/哈希及stdout后检查；
这是检查点式软预算，不是阻塞I/O的硬实时强杀。外部退出状态优先于收据。

首个非预期异常/警告、预算/身份/权限错误、非唯一替换、输出冲突或源变化
立即停止；不补写、修复、重试或清理部分产物。即使收据已写也须exit0和
最终预算检查才算本次文本生成完成；失败可能只留下新文件的一部分。
收据耗时是写前取样，不当作最终全程时间。只记录原容差未动，不重新评价。

## 确切命令（尚未执行）

工作目录固定为：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`

执行前逐项核对以下Git元数据：clean、代码基线为祖先、后继仅docs；
记录实际HEAD及本方案SHA，任何不符不进入主命令。本包准备起点为
clean `eec81d1ef56e1696f290a939d5a5fac1a17fbdf7`，新增内容仅docs。

```bash
git status --porcelain
git rev-parse HEAD
git merge-base --is-ancestor 6514160302be3f654d96bf19ba8d2d747c6bfd26 HEAD
git diff --name-only 6514160302be3f654d96bf19ba8d2d747c6bfd26 HEAD
shasum -a 256 docs/research/S03/S03-E019/font_svg_sidecar_s01_plan.md
```

主命令原文如下；here-document只是内存程序，不在磁盘新建执行器：

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -I -S -B -W error - <<'PY'
import time
started = time.monotonic()
import hashlib, json, logging, os, stat, sys, warnings
from datetime import datetime, timezone
from pathlib import Path
warnings.simplefilter('error')
def need(ok, message):
    if not ok:
        raise RuntimeError('STOP_F01_S01_NO_RETRY: '+message)
def budget():
    need(time.monotonic()-started < 60, 'soft60s exceeded')
base_factory = logging.getLogRecordFactory()
def log_factory(*args, **kwargs):
    need(type(args[1]) is int and args[1] < logging.WARNING, 'logging warning/error')
    return base_factory(*args, **kwargs)
logging.setLogRecordFactory(log_factory)
root = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001')
fixed = {
 'residuals.svg':'8228c9b7b8e2f247f0ce9fb764c5ea9863be2b96a4eb3cbf8add39803b07893f',
 'residuals.md':'33632165d5cf01b8b8e8b8ffc46a3ba9953e8d3af61608118e1bc0f5a9c7fed1',
 'square_ledger.svg':'210aeb0aaa3ea03a51c6cd6a0575ed223f62828044e212ec69a5c8cd6a7772a5',
 'square_ledger.md':'cf14301c56c61853ad19a0ca5e5b58bf3ea906d81409501e4a19e31d0deeae6a',
 'runtime_guard_events.log':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
 'derived_receipt.json':'22a84024dd011230e0a89790c6d8681ffeebb2684b257978a6a8cee63892cc5a',
 'derived_completion.json':'f4c649e1c18b9d08ce7d279e26d46b59e876ed019350ba9eaff0929f8c3dc0c2'}
new_names = {'residuals.sidecar_s01.md','square_ledger.sidecar_s01.md','sidecar_mapping_s01.receipt.json'}
old_paths = {str(root/n) for n in fixed}
new_paths = {str(root/n) for n in new_names}
for p in (root, *root.parents):
    need(stat.S_ISDIR(p.lstat().st_mode), 'directory/symlink '+str(p))
need({p.name for p in root.iterdir()} == set(fixed), 'initial exact seven assets')
for n in new_names:
    need(not os.path.lexists(root/n), 'new path already exists '+n)
threads = ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS')
need(os.environ.get('CUDA_VISIBLE_DEVICES') == '' and all(os.environ.get(k) == '1' for k in threads), 'single CPU environment')
need(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode, 'isolated no-site no-bytecode')
def audit(event, args):
    if event == 'open':
        p, mode, flags = args
        need(isinstance(p, (str,bytes,os.PathLike)), 'descriptor/path open')
        path = os.fsdecode(p)
        need(path in old_paths|new_paths, 'open outside whitelist')
        write = flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)
        if write:
            need(path in new_paths and flags & os.O_EXCL and flags & os.O_CREAT and not flags & (os.O_TRUNC|os.O_APPEND|os.O_RDWR), 'exclusive new-file writes only')
    need(not event.startswith(('subprocess.','socket.')) and event not in ('os.system','os.mkdir','os.remove','os.rename','os.rmdir','os.link','os.symlink'), 'forbidden side effect '+event)
    if event == 'import':
        need(args[0].split('.')[0] not in ('numpy','scipy','matplotlib') and not args[0].startswith('aa2024_'), 'forbidden import')
sys.addaudithook(audit)
def sha(value):
    return hashlib.sha256(value).hexdigest()
def info(path):
    s = path.lstat()
    need(stat.S_ISREG(s.st_mode), 'regular non-symlink file required')
    return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
before = {n:info(root/n) for n in fixed}
original = {}
for n in fixed:
    budget()
    original[n] = (root/n).read_bytes()
    need(info(root/n) == before[n] and sha(original[n]) == fixed[n], 'source identity '+n)
old = b'No caching, interpolation or smoothing.'
new = b'No caching. RGB interpolation is used only for the residual colour scale. It does not interpolate point data in space; no spatial interpolation or smoothing of point data is performed.'
derived, mapping = {}, []
for stem in ('residuals','square_ledger'):
    name, output = stem+'.md', stem+'.sidecar_s01.md'
    need(original[name].count(old) == 1, 'one exact replacement '+name)
    derived[output] = original[name].replace(old,new,1)
    need(derived[output].count(old) == 0 and derived[output].count(new) == 1, 'replacement result '+name)
    mapping.append({'figure':str(root/(stem+'.svg')),'figure_sha256':fixed[stem+'.svg'],
                    'original_sidecar':str(root/name),'original_sidecar_sha256':fixed[name],
                    'companion':str(root/output),'companion_sha256':sha(derived[output]),'replacement_count':1})
def unchanged():
    for n in fixed:
        budget()
        need(info(root/n) == before[n] and (root/n).read_bytes() == original[n], 'original changed '+n)
unchanged()
def create(name, payload):
    budget()
    need(not os.path.lexists(root/name), 'new file collision '+name)
    with (root/name).open('xb') as stream:
        need(stream.write(payload) == len(payload), 'short write '+name)
    need(stat.S_ISREG((root/name).lstat().st_mode) and (root/name).read_bytes() == payload, 'new-file readback '+name)
    budget()
for n,payload in derived.items():
    create(n,payload)
unchanged()
record = {'schema':'F01-S01-v1','status':'text_clarification_written_not_accepted',
          'operation':'one_RGB_vs_spatial_sentence_replacement_per_sidecar',
          'record_utc':datetime.now(timezone.utc).isoformat(),'pid':os.getpid(),
          'original_root':str(root),'originals_sha256_before':fixed,
          'originals_sha256_after':{n:sha((root/n).read_bytes()) for n in fixed},
          'mapping':mapping,'replacement':{'old':old.decode(),'new':new.decode()},
          'new_files':sorted(new_names),'thread_env':{k:os.environ[k] for k in threads},
          'actual_svd':0,'actual_qr':0,'redraw':False,'scientific_recomputation':False,
          'independent_acceptance_run':False,'original_validator_run':False,
          'source_status_preserved':'incomplete_unaccepted_synthetic',
          'elapsed_before_receipt':time.monotonic()-started,
          'limits':['mapped companions only; original same-stem sidecars unchanged',
                    'directory membership expands from seven to ten; old exact-seven command is not rerun',
                    'no visual or numerical acceptance; B003 remains incomplete',
                    'controlled operation fields are not a whole-process syscall audit']}
need(record['originals_sha256_after'] == fixed, 'source hashes before receipt')
receipt_bytes = (json.dumps(record,indent=2,allow_nan=False)+'\n').encode('utf-8')
create('sidecar_mapping_s01.receipt.json',receipt_bytes)
unchanged()
need({p.name for p in root.iterdir()} == set(fixed)|new_names, 'final exact ten assets')
new_payloads = dict(derived)
new_payloads['sidecar_mapping_s01.receipt.json'] = receipt_bytes
for n,payload in new_payloads.items():
    need(stat.S_ISREG((root/n).lstat().st_mode) and (root/n).read_bytes() == payload, 'final new-file readback '+n)
budget()
print(json.dumps({'status':'TEXT_CLARIFICATION_WRITTEN_NOT_ACCEPTED','new_sha256':{n:sha((root/n).read_bytes()) for n in sorted(new_names)},'elapsed_before_print':time.monotonic()-started},sort_keys=True),flush=True)
budget()
PY
```

命令exit0且无非预期终端事件后，仅核对本次新三件读回/收据身份与原七件
保持不变的记录，记录完整终端、退出、HEAD及时间口径；不打开图、不独立
验收新说明。末次Git元数据检查只用于确认执行前后HEAD/clean不变，
不在过程中添加文档造成假阳性。该自检不是官方validator或独立验收。

## 本轮结论与下一决定

此为待批准方案，不是已生成新说明或已解除原停验；原两个SVG、两个说明、
guard/receipt/completion和全部其他冻结产物保持原样。没有启动子代理、
外发或实际修订。未来即使本命令完成，也只证明文本派生成功；剩余说明/
两图目视/目视后身份验收仍须另批采用新映射的方案，不自动继续。
