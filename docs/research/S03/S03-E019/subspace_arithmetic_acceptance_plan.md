# E019-D01 — 剩余独立算术只读验收方案与确切命令 v1

2026-10-16；proposal only，未执行、未导入、未测试，未读取report数值。
承接已冻结D01 v1.1的验收，不新开诊断、不更改数值定义或原门槛。
V01独立显示验收已经完成，不重做图形检查或重绘旧图。

## 1. 问题与完成边界

只问：已有合成report的保存操作数、分层账本、CSV及运行来源是否一致？
不是再次运行四fixture，不认证原真实E019根因、相场反演或预测有效性。
当前仅准备本方案/确切命令；用户确认前不运行任何验算或测试。

按冻结producer的保存契约（实际schema将在获批后核对）：

| 对象 | 可只读核验 | 本次不可宣称核验 |
|---|---|---|
| 身份/序列化 | 原收据、11项来源、审批副本、T001、6产物哈希，CSV逐字段对应 | 仅靠收据独立认证全部历史进程或零调用计数 |
| C0 | 固定人工坐标/权重、H形状/Gram及保存Gram缺陷标量 | 原C/A未保存，不重构C/A，不核原A层五项账本 |
| C1–C3 | 已存H/A/L/V/s/y/p/r，因子与p/r账本、原负控、跨例相同p/r但不同A | 不生成新fixture或重新分解，不证明真实gesvd机制 |
| Q判据 | 从保存H/r独立fsum参考评估，与保存最大差/ratio/状态核对 | 原逐分量Qr未保存，不认证原Qr的逐bit计算历史 |
| 显示 | 复用已完成V01验收记录作为说明，不再执行 | 不把显示通过替代算术或缺失操作数 |

C0缺C/A是已知保存范围限制，不是新异常，也不记数值失败。若实际schema
与冻结契约不一致、原本应有的C1–C3操作数缺失，则为非预期异常，立即停。
不得以保存stencil/常量网格重建C/A、调用sampling/quotient/rigid_basis
或补做QR来抹去缺项。原C0标量仅可确认字节/CSV一致，仍未独立算术核验。

## 2. 允许输入与只读纪律

唯一算术操作数来源：
`/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D01/S03-E019-D01-R001/analysis/report.json`
SHA256=f6276a7d474cde6675d99649d8256027edea16902e7c259af2fab24c3535a689。

只再读该Run既有CSV/收据/审批副本/空日志，以及原D01-T001测试记录、
固定11项源码/方案/测试设计/审批正文。其他原图/PDF/说明仅核字节，不
再次目视已知旧排版缺陷。禁止递归扫描、NPZ/ZIP/真实E019 H/p/y/r、
prepared/solved/预测、stage15/R003、新留出、nodemap或其他数据。
先核固定清单再读，不按JSON收据中任意路径扩大文件范围。

只用Python标准库，-I -B -Werror，五项线程1、CUDA禁用，软60秒含导入/
哈希/读取/参考算术/末次身份核对。禁止NumPy/SciPy/Matplotlib和任何
producer导入；零QR/SVD/eig/求解、零绘图/测试，不调用diagnostic/run。
全程无文件写入、无新输出目录；结果只打印到工具stdout，之后另将完整
独立回复追加项目记录，绝不写回冻结report/CSV/原收据或V01资产。

## 3. 参考算术和拟定验收映射（待确认，不救结果）

Decimal.from_float转换已存binary64操作数，精度固定80；独立math.fsum
对HᵀL、AV、Lᵀy、Hᵀr和Q参考求值交叉核对。只是在内存核验保存操作数
的恒等式，不生成或替换producer输入/输出，也不做数值分解。

原数值容差保持；本方案待确认的是其在保存标量核验中的单位映射，
不是声称这些尚未执行的验收已有通过结果。原形式
abs(value-ref)<=atol+1e-12*abs(ref)保持：无量纲矩阵/标量atol1e-12，
位移向量/标量atol1e-15mm，平方量atol1e-18mm²（本次无平方指标）。
报告的ratio为无量纲标量，按矩阵量原容差核对；Q最大差按向量量核对。
标量核对不宣称字符串所有末位相同；同时记录Decimal差及exact_match，
后者仅诊断，不新增更苛刻的逐字/逐bit通过门槛。不得从“低于atol”推断
极小舍入项精确为零或断言某一因果份额已证实。

C1干净基线需原Q判据通过；C2/C3需保持预登记负控及原Q判据不通过。
只有这两项预定负控可正常记录不通过；任何其他检查不符、非有限值、
新警告、哈希/schema/字段/预算异常首个即停，不自动重试/修复/更换算法。
此前获批的字体缓存日志仅属已结束的V01运行；本命令不导入绘图库，
不预设任何新警告豁免，不重新产生或删改该日志。

主要核验等式：E=AV−LΣ，HᵀL=(HᵀAV−HᵀE)Σ⁻¹；
p_ref=L(Lᵀy)，delta_p=p−p_ref，delta_r=r−(p−y)；
Hᵀp=(HᵀL)(Lᵀy)+Hᵀdelta_p；Hᵀr=Hᵀp−Hᵀy+Hᵀdelta_r。
核因子重构与左右Gram原容差、保存的分层最大值、干净基线和跨例定义。
不把各项max相加作为总因果份额。

## 4. 输出与结论映射

- 完整性/某必要检查异常：STOP_AT_FIRST_UNEXPECTED，不补查/不重试。
- 可核项目均一致：PASS_SAVED_C1_C3_ARITHMETIC_WITH_C0_LIMITATION，明确
  C0原A账本与原逐分量Qr未保存，不能写完整D01所有算术均独立通过。
- 实际算术未执行前，只有方案/命令已准备，不声称代码审查/测试通过。

后续执行者为独立只读Codex，先静态核对本确切命令；若发现问题只报告，
不边改边执行。当前尚未安排或完成该静态审查；修改命令后需再展示确认。
验收结果只改变保存合成证据的有限核验状态，不恢复真实E019暂停结论。

## 5. 确切待确认命令（本轮不执行）

唯一命令；无A/B串联、重定向、新目录或文件写入。标准库stdout仅输出
核对结果/范围/末次哈希，失败输出已完成清单后立即抛出，不继续末次检查。
只有工具exit0且无后续STOP才可采纳通过输出；若输出后超时或非零退出，
之前的通过字段不构成最终通过，不重试。
原producer来源固定8471002；本命令不依赖新脚本或未定义入口。

```bash
set -euo pipefail
cd '/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013'
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 NUMEXPR_NUM_THREADS=1
unset PYTHONPATH PYTHONHOME PYTHONSTARTUP PYTEST_ADDOPTS PYTEST_PLUGINS
'/Users/wenxiaofang/miniconda3/bin/python3' -I -B -W error -u - <<'PY'
import time
started=time.monotonic()
import signal
def deadline(signum,frame): raise TimeoutError('60-second read-only audit budget')
signal.signal(signal.SIGALRM,deadline)
signal.setitimer(signal.ITIMER_REAL,max(.001,60-(time.monotonic()-started)))
import csv,hashlib,io,json,math,os,subprocess
from pathlib import Path
from decimal import Decimal as D,localcontext
repo=Path.cwd()
project=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
if repo!=project/'.codex/worktrees/s03-e016-geometry-alignment-20261013':raise ValueError('wrong cwd')
run=project/'local_archive/experiments/S03-E019-D01/S03-E019-D01-R001'
test=project/'local_archive/code_checks/S03-E019-D01-T001'
snapshot='8471002db09cd1cb072552b00f3fd736a607b11a'
names=['docs/research/S03/S03-E019/subspace_localisation_plan.md',
       'docs/research/S03/S03-E019/experiment.md','scripts/aa2024_kinematic_capacity.py',
       'scripts/aa2024_geometry_prior.py','scripts/aa2024_boundary_basis.py',
       'scripts/aa2024_triplet_structure.py','scripts/aa2024_patch_mechanics.py',
       'scripts/aa2024_rigid_observable.py','scripts/aa2024_qsubspace_diagnostic.py',
       'tests/test_aa2024_qsubspace_diagnostic.py',
       'docs/research/S03/S03-E019/subspace_test_design.md']
anchors={
 run/'analysis/report.json':'f6276a7d474cde6675d99649d8256027edea16902e7c259af2fab24c3535a689',
 run/'analysis/execution_receipt.json':'3677f36fdce41c61fd0173ae16dfecdc90ff5e0eeef61cef4acaaf220d43f48a',
 run/'analysis/summary.csv':'25ae87fcb284e55ae5d8a8c452ba6dca4c0673064eef07cc24ecb9d0c49a2101',
 run/'analysis/q_identity_ratio.png':'5f37dabce7b123943e050caa554dbf61c366b365801ae9e0d40cf3a4fc500df5',
 run/'analysis/q_identity_ratio.pdf':'364777ef3964be14349658a16b5edbf4fb3355467ba3e1af3e68d790ec87b685',
 run/'analysis/q_identity_ratio.md':'3800503ad56e823dd8bf7334d47519bed47697d859754d6bccd8cd2906bc6612',
 run/'analysis/README_analysis.md':'bb61eee883229babf83d38e017cb30dfb5a82d90b955fa28ce31e525c7df733b',
 run/'00_intent_approved.md':'ee408ccee63a9509e889421134a25bdd215ac764f473d57110dffb821096345e',
 run/'run.log':'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
 test/'test_receipt.json':'46c53f84381ef7b3338fe256c2e22bda0ad2999d361400df46334c7156221671',
 test/'tests.log':'46964e1183d1a78aa0bb48d599c0dc711c479e4dc1ee5254c6ce9b9557f8e731',
 test/'00_intent_approved.md':'ee408ccee63a9509e889421134a25bdd215ac764f473d57110dffb821096345e',
 repo/'docs/research/S03/S03-E019/subspace_execution_approval.md':
 'ee408ccee63a9509e889421134a25bdd215ac764f473d57110dffb821096345e'}
done=[]; metrics=[]; blobs={}
threads=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS')
def require(ok,label):
    if not ok:raise ValueError(label)
def read(path):
    require(path.resolve()==path and path.is_file(),'fixed nonsymlink file '+str(path))
    with path.open('rb') as h:return h.read()
def sha(data):return hashlib.sha256(data).hexdigest()
def state():return [subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
                    subprocess.check_output(['git','status','--porcelain'],text=True)]
def reject(value):raise ValueError('nonstandard JSON constant '+value)
def load(path):return json.loads(blobs[path],parse_constant=reject)
def number(x):
    require(type(x) in (int,float) and math.isfinite(x),'finite binary64 operand')
    return D.from_float(float(x))
def matrix(x,rows,cols):
    require(isinstance(x,list) and len(x)==rows and all(isinstance(r,list) and len(r)==cols for r in x),'saved matrix shape')
    return [[number(v) for v in r] for r in x]
def tr(x):return list(map(list,zip(*x)))
def mul(a,b):return [[sum((x*y for x,y in zip(row,col)),D(0)) for col in zip(*b)] for row in a]
def add(a,b,sign=1):return [[x+sign*y for x,y in zip(r,s)] for r,s in zip(a,b)]
def eye(n):return [[D(int(i==j)) for j in range(n)] for i in range(n)]
def mag(a):return max(abs(v) for row in a for v in row)
def scalar(value):
    out=D(value) if isinstance(value,str) else number(value)
    require(out.is_finite(),'finite reported scalar');return out
def close(a,b,label,kind='matrix'):
    require(len(a)==len(b) and all(len(r)==len(s) for r,s in zip(a,b)),label+' shape')
    absolute=D.from_float(1e-12 if kind=='matrix' else 1e-15)
    relative=D.from_float(1e-12)
    require(all(x.is_finite() and y.is_finite() and abs(x-y)<=absolute+relative*abs(y)
                for r,s in zip(a,b) for x,y in zip(r,s)),label)
def metric(row,key,ref,kind='matrix'):
    saved=scalar(row[key]);close([[saved]],[[ref]],key,kind)
    metrics.append(dict(case=row['case'],metric=key,saved=str(saved),reference=str(ref),
                        delta=str(saved-ref),exact_match=saved==ref,kind=kind))
def fsum_cross(a,b,ref,label,kind='matrix'):
    out=[[D.from_float(math.fsum(float(x)*float(y) for x,y in zip(row,col)))
          for col in zip(*b)] for row in a]
    close(out,ref,label,kind);return out
try:
    require(all(os.environ.get(k)=='1' for k in threads) and os.environ.get('CUDA_VISIBLE_DEVICES')=='','CPU threads')
    before_state=state();require(before_state[1]=='','dirty start')
    for path,expected in anchors.items():
        data=read(path);require(sha(data)==expected,'anchored bytes '+str(path));blobs[path]=data
    source_hashes={}
    for name in names:
        data=read(repo/name)
        require(data==subprocess.check_output(['git','show',snapshot+':'+name]),'reviewed source '+name)
        source_hashes[name]=sha(data)
    r=load(run/'analysis/execution_receipt.json');t=load(test/'test_receipt.json')
    for item,status,key in ((r,'succeeded','execution_status'),(t,'passed','status')):
        require(item[key]==status and item['budget_seconds']==60 and 0<=item['elapsed_seconds']<60,'prior status/budget')
        require(item['sources_before_sha256']==source_hashes==item['sources_after_sha256'],'prior 11-source chain')
        require(item['thread_environment']=={k:'1' for k in threads},'prior thread record')
    require(r['source_commit_declared']==snapshot and t['source_commit']==snapshot,'prior source commit')
    expected_artifacts={p.name:h for p,h in anchors.items() if p.parent==run/'analysis' and p.name!='execution_receipt.json'}
    require(r['artifacts_sha256']==expected_artifacts,'six artifacts receipt binding')
    require(t['tests_log_sha256']==anchors[test/'tests.log'],'T001 log binding')
    report=load(run/'analysis/report.json')
    require(report['domain']=='synthetic' and report['protocol_revision']=='E019-D01_v1.1','report identity')
    require(report['precision_digits']==80 and report['reference_conversion']=='Decimal.from_float','reference identity')
    require(report['tolerances']==dict(rtol=1e-12,matrix=1e-12,vector=1e-15,square=1e-18),'original tolerances')
    require(all(report[k]==0 for k in ('svd_calls','eig_calls','fem_solves','array_file_inputs')),'reported counters')
    rows=report['cases'];require([x['case'] for x in rows]==['C0','C1','C2','C3'],'case order')
    csv_reader=csv.DictReader(io.StringIO(blobs[run/'analysis/summary.csv'].decode(),newline=''))
    require(csv_reader.fieldnames==list(dict.fromkeys(k for row in rows for k in row)),'CSV columns')
    csv_rows=list(csv_reader);require(len(csv_rows)==4,'CSV rows')
    for row,saved in zip(rows,csv_rows):
        for key in csv_reader.fieldnames:
            value=row.get(key,'');require(saved[key]==('' if value is None else str(value)),'CSV field '+key)
    done.append('frozen provenance and CSV serialization')
    evidence=report['evidence'];require(set(evidence)=={'C0','C1','C2','C3'},'evidence case keys')
    with localcontext() as ctx:
        ctx.prec=80
        c0=evidence['C0']
        require(set(c0)=={'xy','weights','H','scale','stencil_nodes','stencil_coeff','free_dofs'},'C0 saved schema')
        require(c0['xy']==[[-13.05,-4.95],[-8.55,-2.25],[-4.05,2.25],[-.45,4.95],
                          [.45,-4.95],[4.05,-2.25],[8.55,2.25],[13.05,4.95]] and c0['weights']==list(range(1,9)),'C0 fixed metadata')
        h0=matrix(c0['H'],16,3);g0=mul(tr(h0),h0);close(g0,eye(3),'C0 saved H Gram')
        metric(rows[0],'gram_defect_max',mag(add(eye(3),g0,-1)))
        require(rows[0]['Q_identity_ratio'] is None and rows[0]['Q_identity_pass'] is None and
                rows[0]['Q_identity_role']=='not_applicable' and rows[0]['Q_identity_outcome']=='no_y_p_r_in_C0','C0 not applicable')
        done.append('C0 saved H/Gram only; original C/A ledger unavailable')
        for row in rows[1:]:
            name=row['case'];e=evidence[name]
            require(set(e)=={'H','L','y','p','r','A','V','s','constants'},name+' saved schema')
            h=matrix(e['H'],16,3);a=matrix(e['A'],16,16);l=matrix(e['L'],16,5);v=matrix(e['V'],16,5)
            y=matrix(e['y'],16,1);p=matrix(e['p'],16,1);res=matrix(e['r'],16,1)
            require(e['s']==[1,2**-4,2**-12,2**-24,2**-32],name+' five fixed modes')
            s=[number(x) for x in e['s']];ht=tr(h);lt=tr(l)
            tau=number(e['constants']['tau']);require(all(x>10*tau for x in s),name+' cutoff separation')
            close(mul(ht,h),eye(3),name+' H Gram');close(mul(lt,l),eye(5),name+' L Gram');close(mul(tr(v),v),eye(5),name+' V Gram')
            ls=[[x*s[j] for j,x in enumerate(r0)] for r0 in l]
            av=mul(a,v);err=add(av,ls,-1);ha=mul(ht,a);hl=mul(ht,l)
            it=mul(ha,v);et=mul(ht,err)
            reconstructed=[[z/s[j] for j,z in enumerate(r0)] for r0 in add(it,et,-1)]
            close(hl,reconstructed,name+' factor ledger')
            factor_reconstruction=mul(ls,tr(v));close(factor_reconstruction,a,name+' reconstruction')
            fsum_cross(ht,l,hl,name+' fsum HtL');fsum_cross(a,v,av,name+' fsum AV')
            for key,value in dict(A_total_max=mag(ha),factor_gram_defect_max=mag(add(mul(lt,l),eye(5),-1)),
                factor_HtL_max=mag(hl),factor_E_max=mag(err),factor_input_term_max=mag(it),
                factor_residual_term_max=mag(et),
                factor_input_amplified_max=mag([[z/s[j] for j,z in enumerate(r0)] for r0 in it]),
                factor_residual_amplified_max=mag([[z/s[j] for j,z in enumerate(r0)] for r0 in et]),
                factor_ledger_error_max=mag(add(hl,reconstructed,-1)),
                factor_reconstruction_max=mag(add(factor_reconstruction,a,-1))).items():metric(row,key,value)
            require(row['factor_reconstruction_pass'] is True,name+' reconstruction saved status')
            coefficient=mul(lt,y);pref=mul(l,coefficient);dp=add(p,pref,-1);dr=add(res,add(p,y,-1),-1)
            existing=mul(hl,coefficient);evaluation=mul(ht,dp);subtraction=mul(ht,dr)
            hp=mul(ht,p);hy=mul(ht,y);hr=mul(ht,res)
            close(p,pref,name+' p saved/reference','vector');close(res,add(p,y,-1),name+' r saved/subtraction','vector')
            close(hp,add(existing,evaluation),name+' p ledger','vector')
            close(hr,add(add(hp,hy,-1),subtraction),name+' r ledger','vector')
            fsum_cross(lt,y,coefficient,name+' fsum coefficient','vector')
            hr_f=fsum_cross(ht,res,hr,name+' fsum Htr','vector')
            for key,value in dict(p_existing_subspace_max_mm=mag(existing),p_new_evaluation_max_mm=mag(evaluation),
                r_new_subtraction_max_mm=mag(subtraction),p_float_error_max_mm=mag(dp),r_float_error_max_mm=mag(dr),
                Htp_max_mm=mag(hp),Hty_max_mm=mag(hy),Htr_max_mm=mag(hr)).items():metric(row,key,value,'vector')
            correction=fsum_cross(h,hr_f,mul(h,hr),name+' fsum Q correction','vector')
            delta=[(float(res[i][0])-float(correction[i][0]))-float(res[i][0]) for i in range(16)]
            bound=[1e-15+1e-12*abs(float(r0[0])) for r0 in res]
            ratio=max(abs(x)/b for x,b in zip(delta,bound));passed=all(abs(x)<=b for x,b in zip(delta,bound))
            metric(row,'Q_identity_max_mm',number(max(map(abs,delta))),'vector');metric(row,'Q_identity_ratio',number(ratio))
            clean=name=='C1'
            require(passed==clean and row['Q_identity_pass'] is clean,name+' original Q outcome')
            require(row['Q_identity_role']==('clean_baseline' if clean else 'predeclared_negative_control') and
                    row['Q_identity_outcome']==('passed' if clean else 'expected_not_passed_at_original_tolerance'),name+' original role')
            if clean:
                close(hp,[[D(0)]]*3,'C1 clean Htp','vector');close(hr,[[D(0)]]*3,'C1 clean Htr','vector')
                close(ha,[[D(0)]*16 for _ in range(3)],'C1 clean HtA');close(hl,[[D(0)]*5 for _ in range(3)],'C1 clean HtL')
            done.append(name+' saved factor/projection ledgers and independent Q reference')
        c1,c2,c3=(evidence[k] for k in ('C1','C2','C3'))
        require(c2['p']==c3['p'] and c2['r']==c3['r'] and c2['L']==c3['L'] and
                c2['A']!=c3['A'] and c1['A']==c3['A'],'different saved input, same saved p/r')
        require(all(c1[k]==c2[k]==c3[k] for k in ('H','V','s','y')),'shared fixed saved operands')
        done.append('saved cross-case mechanism contrast')
    for path,expected in anchors.items():require(sha(read(path))==expected,'end artifact hash '+str(path))
    for name,expected in source_hashes.items():require(sha(read(repo/name))==expected,'end source hash '+name)
    require(state()==before_state,'end HEAD/dirty changed')
    require(time.monotonic()-started<60,'final60s')
    print(json.dumps(dict(status='PASS_SAVED_C1_C3_ARITHMETIC_WITH_C0_LIMITATION',completed=done,
        limitations=['original C0 C/A ledger unavailable','original componentwise Qr not saved',
                     'no actual E019 root cause or physical claim','counter fields are self-report, not process audit'],
        scalar_checks=metrics,source_sha256=source_hashes,head=before_state[0],
        elapsed_before_stdout_seconds=time.monotonic()-started),indent=2,allow_nan=False),flush=True)
    require(time.monotonic()-started<60,'stdout completion60s')
except BaseException as exc:
    print(json.dumps(dict(status='STOP_AT_FIRST_UNEXPECTED',error=repr(exc),completed=done,
                          elapsed_seconds=time.monotonic()-started),allow_nan=False),flush=True)
    raise
finally:
    signal.setitimer(signal.ITIMER_REAL,0)
PY
```

## 6. 当前请求

请确认上述只读范围、C0/原Qr保存缺口的处理方式，以及确切命令。
当前没有运行该命令、导入、参考算术、测试、读取report数值或创建任何目录；
也没有独立静态审查或新的数值通过结论。确认后再安排独立执行者核对，
发现命令问题先报告；不在同一许可下改命令后重试。
