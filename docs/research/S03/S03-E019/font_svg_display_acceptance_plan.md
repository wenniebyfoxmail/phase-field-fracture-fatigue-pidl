# F01-V001 独立只读图形与说明验收方案 v1

2026-10-19（Europe/London）。仅准备供用户审批；未派发验收、未运行下列
命令、未读取V001图/说明/收据或B003数值、未打开图。复用既有D1和
font_svg_b_results.md中的冻结身份，不新增科学标准或计算实验。

## 目的、执行者与范围

原目标仍为真实DIC到状态反演的桥接；F01只解除显示依赖的工程阻断。
owner仍为本聊天S03-E019-D03-F01，D3已有一次SVG导出记录；本次剩余任务
是确认派生图能否被正确阅读，不能代替训练侧数值复核或物理验证。

建议获批后由独立本地只读Codex（优先既有e019_d02_review）执行下列命令
及目视，不由图器作者代签。该审查者未生成V001；其既有代码审查不计作
本次验收。无需Pro/云端，不上传文件；预计为一次轻量标准库检查和两图
本地目视。当前只准备，尚未唤醒或派发。若原审查者不可用，报告并等待
用户选择，不静默换渠道。

未来交接须传当前installed research-decision-core、road-fracture-experiment-gate、
research-figure-workflow、research-review-channels的SKILL.md绝对路径，
本方案/结果记录、当前D3、下列白名单/停止规则和禁止结论；不另建任务梯子。
独立者只返回结论和证据，主代理在仓库文档记录，不回写V001。

## 唯一资产白名单和结论上限

只消费以下固定目录的7份已有派生产物：

```text
/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001
```

residuals.svg/md、square_ledger.svg/md、runtime_guard_events.log、
derived_receipt.json、derived_completion.json。禁止根据receipt中的来源路径
去打开原文件；B003的certificate.npz/report.json、所有真实数组/stage15/
新留出、其他Run、缓存全部不读、不hash。不导入图器、producer、verifier、
NumPy/SciPy/Matplotlib；不运行测试、SVD/QR、投影、误差或账本重算。

命令1只做哈希、JSON/XML解析、计数、标签/已保存值的直接比较以及打印说明。
这不重算科学量，不检验源数值是否正确；元数据声称零分解不是历史系统审计。
通过最多支持V001的结构/说明/目视一致；B003仍未完成，不追认数值有效。
原数值容差保持且本轮不评价，不增加精度阈值或拿视觉判断代替科学判据。

## 固定顺序、停止与预算

1. 独立者先静态核对本方案确切命令、冻结SHA和权限；发现问题只报告，
   不自行修订/执行。核当前工作区clean，基线后继仍仅docs；记录实际HEAD。
2. 执行命令1一次：单线程CPU、60秒软预算，标准库只读；首个非预期异常、
   警告、解析/身份/权限失败立即停止，不进入目视，不自动修正或重试。
3. 只有命令1 exit0、无异常且输出PENDING_VISUAL_QA时，才执行命令2，
   用本机已安装Safari只读打开两份原SVG各一次。浏览器正常显示既有矢量图
   不属于重新调用图器；不保存/转换/导出PNG、PDF、缩略图或新SVG。
4. 独立者通过本地UI截图直接看原图（内存截图，不另存图像），核下节清单。
   普通查看器自身可能维护应用状态/缓存；只读指不写/改科学资产，不声称
   全系统零写入。不预热字体、不运行Matplotlib、不豁免任何观察到的警告。
   每图首次打开若60秒仍不能显示或出现异常就停，不自动重开/换渲染器。
   人工审阅时间不伪装成原出图耗时，不回写或重解释原60秒预算。
5. 目视无阻断后执行命令3一次，末次哈希逐项对照命令1和冻结值，核HEAD/
   clean未变。任何差异立即停止，不修改产物。独立者报告实际视图、局限及
   已完成/未完成项目，不以命令2的open exit0代替实际看图。

未知执行状态先查原进程/工具状态，不重新启动。所有失败/问题保留并报告；
本方案不包含重绘、修说明、续跑、C/D、真实数据访问或对外发送。

## 命令1：白名单身份、结构与说明直接核对（尚未执行）

工作目录固定为：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013`

先逐条执行以下Git元数据命令并核对：status须为空、基线必须为祖先、
diff列表须全部位于docs/；记录HEAD用于末次比较。任何不符不继续。

```bash
git status --porcelain
git rev-parse HEAD
git merge-base --is-ancestor 6514160302be3f654d96bf19ba8d2d747c6bfd26 HEAD
git diff --name-only 6514160302be3f654d96bf19ba8d2d747c6bfd26 HEAD
```

下列here-document仅向Python提供内存程序，不创建脚本或其他文件。
`-I -S -B`排除用户site/项目路径及字节码写入；只用标准库，不执行SVG。
安装只读审计hook后，文件内容open只允许7份白名单，拒绝写入/子进程/网络。
首轮准备未导入/编译/试跑该命令，未声称动态通过。

```bash
env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 /Users/wenxiaofang/miniconda3/bin/python3 -I -S -B -W error - <<'PY'
import time
start = time.monotonic()
import hashlib, json, math, os, re, stat, sys, warnings
from pathlib import Path
import xml.etree.ElementTree as ET
import pyexpat
warnings.simplefilter('error')
def need(ok, label):
    if not ok:
        raise RuntimeError('STOP_F01_DISPLAY: '+label)
def budget():
    need(time.monotonic()-start < 60, 'soft60s exceeded; no retry')
root = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001')
fixed = {
 'residuals.svg':'8228c9b7b8e2f247f0ce9fb764c5ea9863be2b96a4eb3cbf8add39803b07893f',
 'residuals.md':'33632165d5cf01b8b8e8b8ffc46a3ba9953e8d3af61608118e1bc0f5a9c7fed1',
 'square_ledger.svg':'210aeb0aaa3ea03a51c6cd6a0575ed223f62828044e212ec69a5c8cd6a7772a5',
 'square_ledger.md':'cf14301c56c61853ad19a0ca5e5b58bf3ea906d81409501e4a19e31d0deeae6a',
 'runtime_guard_events.log':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
 'derived_receipt.json':'22a84024dd011230e0a89790c6d8681ffeebb2684b257978a6a8cee63892cc5a'}
names = set(fixed) | {'derived_completion.json'}
paths = {str(root/name) for name in names}
for p in (root, *root.parents):
    need(not p.is_symlink() and p.is_dir(), 'directory/symlink '+str(p))
need({p.name for p in root.iterdir()} == names, 'exact seven assets')
for name in names:
    p = root/name
    need(stat.S_ISREG(p.lstat().st_mode), 'regular non-symlink '+name)
need(os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'CPU only')
need(all(os.environ.get(k) == '1' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS')), 'single-thread environment')
def audit(event, args):
    if event == 'open':
        p, mode, flags = args
        need(isinstance(p, (str, bytes, os.PathLike)) and os.fsdecode(p) in paths, 'open outside whitelist')
        need(not flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND), 'file write forbidden')
    need(not event.startswith(('subprocess.','socket.')) and event not in ('os.system','os.mkdir','os.remove','os.rename','os.rmdir','os.link','os.symlink'), 'forbidden side effect '+event)
    if event == 'import':
        need(args[0].split('.')[0] not in ('numpy','scipy','matplotlib') and not args[0].startswith('aa2024_'), 'forbidden import')
sys.addaudithook(audit)
def info(p):
    s = p.lstat()
    need(stat.S_ISREG(s.st_mode), 'file type changed')
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
before = {n: info(root/n) for n in names}
data = {}
for name in sorted(names):
    budget()
    data[name] = (root/name).read_bytes()
    need(info(root/name) == before[name], 'file changed during read '+name)
hashes = {n: hashlib.sha256(b).hexdigest() for n,b in data.items()}
for n,h in fixed.items():
    need(hashes[n] == h, 'frozen SHA '+n)
def pairs(items):
    out = {}
    for k,v in items:
        need(k not in out, 'duplicate JSON key')
        out[k] = v
    return out
def bad(value):
    raise RuntimeError('STOP_F01_DISPLAY: nonfinite JSON '+value)
def load(s):
    return json.loads(s, object_pairs_hook=pairs, parse_constant=bad)
receipt = load(data['derived_receipt.json'])
completion = load(data['derived_completion.json'])
need(completion == {'derived_receipt_sha256': hashes['derived_receipt.json']}, 'completion binding')
need(receipt['artifacts_sha256'] == {n:fixed[n] for n in fixed if n != 'derived_receipt.json'}, 'five artifacts binding')
need(receipt['status'] == 'derived_display_completed_not_visual_or_numerical_acceptance', 'display-only status')
p = receipt['provenance']
need(p['run_id'] == 'S03-E019-D03-F01-V001' and p['source_status'] == 'incomplete_unaccepted_synthetic', 'provenance boundary')
need(p['actual_svd'] == 0 and p['actual_qr'] == 0, 'saved controlled counters')
need(receipt['runtime_guard']['healthy'] is True and receipt['runtime_guard']['fatal_seen'] is False and data['runtime_guard_events.log'] == b'', 'guard record')
ns = '{http://www.w3.org/2000/svg}'
trees, docs, saved = {}, {}, {}
for stem, box in (('residuals','0 0 1460 730'), ('square_ledger','0 0 1020 660')):
    budget()
    raw = data[stem+'.svg']
    need(b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper(), 'XML declarations')
    tree = ET.fromstring(raw)
    need(tree.tag == ns+'svg' and tree.get('viewBox') == box, 'SVG root/viewBox')
    for e in tree.iter():
        need(e.tag in {ns+t for t in ('svg','title','desc','metadata','rect','text','circle','path')}, 'unsupported SVG tag')
        need(all(not k.lower().startswith('on') and not k.lower().endswith('href') and 'url(' not in v.lower() for k,v in e.attrib.items()), 'external or active SVG')
    need(load(tree.find(ns+'metadata').text) == p, 'SVG provenance')
    text = '\n'.join(e.text or '' for e in tree.iter(ns+'text'))
    need('SYNTHETIC DISPLAY ONLY' in text and 'B003 INCOMPLETE / UNACCEPTED' in text, 'visible scope labels')
    doc = data[stem+'.md'].decode('utf-8')
    for heading in ('Figure question','Data provenance','How to read / Visual grammar / Panel guide','Key numerical takeaway','Limitations and claim boundary','Related assets'):
        need('## '+heading in doc, 'sidecar heading '+heading)
    need(load(doc.split('## Data provenance\n\n',1)[1].split('\n\n## How to read',1)[0]) == p, 'sidecar provenance')
    saved[stem] = load(doc.split('Saved scalar rows only, not independently recomputed:\n\n',1)[1].split('\n\n## Limitations',1)[0])
    need('B003 remains incomplete.' in doc and 'No numerical acceptance, physical inversion, prediction' in doc, 'sidecar boundary')
    trees[stem], docs[stem] = tree, doc
need(saved['residuals'] == saved['square_ledger'], 'same saved scalar rows in both sidecars')
rows = saved['square_ledger']
need(len(rows) == 3 and [r['arm'] for r in rows] == ['old','proxy','intact'], 'saved row order')
points = list(trees['residuals'].iter(ns+'circle'))
panels = {f'{r}:{c}':{} for r in range(2) for c in range(4)}
for e in points:
    panel, index = e.get('data-panel'), e.get('data-point')
    need(panel in panels and index not in panels[panel], 'point/panel uniqueness')
    need(re.fullmatch(r'#[0-9a-fA-F]{6}',e.get('fill','')) is not None, 'RGB fill')
    need(all(math.isfinite(float(e.get(k))) for k in ('cx','cy','data-mm','data-x-mm','data-y-mm')), 'finite saved point attributes')
    panels[panel][index] = (e.get('data-x-mm'),e.get('data-y-mm'))
for panel, coords in panels.items():
    need(set(coords) == {str(i) for i in range(648)}, '648 point IDs '+panel)
    need(coords == panels['0:0'], 'same saved coordinates '+panel)
need(len(points) == 5184, 'eight panels of points')
marks = [e for e in trees['square_ledger'].iter() if e.get('data-arm') is not None]
need(len(marks) == 9, 'nine ledger marks')
for row in rows:
    for quantity, tag, colour in (('J_Q_mm2','rect','#0072B2'),('gap2_mm2','rect','#E69F00'),('J_k_mm2','circle','black')):
        hits = [e for e in marks if e.get('data-arm') == row['arm'] and e.get('data-quantity') == quantity]
        need(len(hits) == 1, 'unique ledger role')
        e = hits[0]
        need(e.tag == ns+tag and e.get('fill') == colour and float(e.get('data-value')) == row[quantity], 'saved ledger mark equals sidecar')
for stem in ('residuals','square_ledger'):
    print('SIDECAR '+stem+' BEGIN\n'+docs[stem]+'\nSIDECAR '+stem+' END')
need({n:info(root/n) for n in names} == before, 'final identity unchanged')
for n in sorted(names):
    need(hashlib.sha256((root/n).read_bytes()).hexdigest() == hashes[n], 'final SHA unchanged '+n)
budget()
print(json.dumps({'status':'PENDING_VISUAL_QA','sha256':hashes,'actual_svd':0,'actual_qr':0,'elapsed_before_print':time.monotonic()-start},sort_keys=True))
budget()
PY
```

命令1的“same saved coordinates”只比SVG里保存的坐标属性，不校验原坐标
来源或屏幕映射数学正确性。账本检查仅直接对照SVG data-value与同名说明
保存行，不计算J_Q+gap²、残差、ratio或柱高。不能写成数值恒等式验收。
结构检查不是充分的可读性证明，必须完成独立者实际目视及说明全文审阅。

## 命令2：打开已有SVG，仅在命令1成功后（尚未执行）

```bash
/usr/bin/open -a Safari /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001/residuals.svg /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001/square_ledger.svg
```

本轮仅确认/Applications/Safari.app存在，未启动或试打开。未来独立者用
原生UI工具选择Safari，依其返回文档读取本地标签页截图；核地址确为这两
个local file，不操作其他标签页、账号或网络页面。不执行SVG脚本；命令1
先拒绝外链/活动元素。若看不到实际图，只能报告视觉范围NOT_REVIEWABLE，
不转换为PNG或静默换查看器。允许仅调整视图缩放/滚动检查原尺寸与整幅，
不刷新重开或保存；记录实际查看器/尺寸/缩放及截图能覆盖的范围。

## 必须人工核对的图形与说明清单

| 对象 | 必核项 | 不得推导 |
|---|---|---|
| residuals.svg | 2×4面板、U/V行和Q retained/old/proxy/intact列；全图可读、坐标单位mm、正y向上、同框尺度及单一对称色标；无空白、遮挡、裁切或误导性翻转 | 原数据坐标已独立校准、r/scale正确或Q更物理 |
| square_ledger.svg | 三臂顺序；蓝J_Q、橙gap²、黑点J_k及mm²；标记/轴/文字可见，堆叠的是平方量而非RMS | Pythagoras/误差分解恒等式已验证、某模型胜出 |
| 两份说明 | 来源/六成员/当前hash边界、每面板/颜色/单位、与图中角色对应；共同保存标量行可追溯；明确B003未接纳和当前仅显示；含关键读图解释而非只列数值 | 历史生成正确、真实反演成功或未来预测有效 |

特别检查：色标RGB插值与“无空间插值/平滑”必须区分；若说明的“无插值”
措辞混淆二者，列为说明需改，不自行改原文件。关键数值行可以作为保存值
展示，但若缺乏必要的读图解释，也须如实列出。字体依赖查看器，不能认证
Matplotlib像素等价、跨平台或论文印刷尺寸质量。两图需分别实际看到，不能
以一图、源码、XML计数或open成功替代另一图的目视。

## 命令3：目视后末次只读身份复核（尚未执行）

在上述固定worktree中：

```bash
git status --porcelain
git rev-parse HEAD
shasum -a 256 /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001/residuals.svg /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001/residuals.md /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001/square_ledger.svg /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001/square_ledger.md /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001/runtime_guard_events.log /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001/derived_receipt.json /Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D03-F01/S03-E019-D03-F01-V001/derived_completion.json
```

独立者逐项比较命令1输出；不是只看shasum命令exit0。只允许Git元数据核对，
不读新增科学数据。末次SHA/HEAD或clean变化立即报告，不自行清理/回滚。

## 返回结论和后续

- 全部命令/说明/两图目视/末次身份通过：REVIEW_PASS，限定V001本机图形
  与说明验收；明确未验数值或物理，不追认B003。
- 发现图形或说明问题：MODIFY_AND_REREVIEW，列精确文件/问题/已完成项，
  不改文件、不重绘；另拟派生修订供用户选择。
- 视图/工具不可用或证据不足：NOT_REVIEWABLE，列具体未见范围，不能当
  科学失败。首个非预期异常立即停，不为了收集完整清单而继续执行。

此方案准备起点clean HEAD fd5643f85d1660065aa937e824a4ba32f0a1cf33。
本轮仅读源码/协议/既有结果文档和Safari应用存在性；未检查派生文件内容或
SHA、未验收、未打开图、未唤醒子代理、未计算或改冻结产物。待用户批准。
