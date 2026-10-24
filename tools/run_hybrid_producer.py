"""Single-owner, bounded supervisor for the complete hybrid execution card.

--check is read-only. --execute requires the exact independent review receipt.
No retries/resume. Workers are separate attributed process groups; the hard
watchdog stops only its own children on time/RAM/disk/admission failures.
"""
import argparse
import csv
import io
import importlib
import json
import os
from pathlib import Path
import platform
import resource
import select
import signal
import socket
import subprocess
import sys
from time import perf_counter, sleep, time

import psutil

from hybrid_inputs import sha256, read_manifest
from hybrid_producer_common import verify_package, write_json, append_event


def require_enabled_execution(card, code_root=None):
    if card.get('execution_enabled') is not True:
        raise RuntimeError('preparation card cannot reserve or spawn a producer')
    reconciliation=card.get('budget_reconciliation',{})
    if (reconciliation.get('complete') is not True
            or not reconciliation.get('receipt_sha256')
            or reconciliation.get('active_or_unknown_runs') != []):
        raise RuntimeError('consumed runs and remaining study allowance must be reconciled before execution')
    rel=Path(reconciliation.get('receipt',''))
    if not str(rel) or str(rel)=='.' or rel.is_absolute() or '..' in rel.parts:
        raise RuntimeError('reconciliation receipt must be a bound local source')
    path=Path(code_root or Path(__file__).resolve().parents[1])/rel
    if sha256(path)!=reconciliation['receipt_sha256']:
        raise RuntimeError('reconciliation receipt hash differs')
    receipt=read_manifest(path)
    consumed='pf_hybrid_complete_20261020_r2'
    if (receipt.get('schema')!='hybrid-budget-reconciliation-v1'
            or receipt.get('complete') is not True or receipt.get('active_or_unknown_runs')!=[]
            or consumed not in receipt.get('settled_runs',[])
            or card.get('run_id') in receipt.get('settled_runs',[])):
        raise RuntimeError('consumed run is not settled or run identity is reused')
    for key,needed in [('remaining_numerical_steps',card['budget']['numerical_substeps']),
                       ('remaining_training_fits',card['budget']['training_fits'])]:
        if type(receipt.get(key)) is not int or receipt[key]<needed:
            raise RuntimeError('reconciled step/fit allowance cannot cover complete plan')
    # initial_totals verifies this same source's SHA and nonnegative metrics,
    # then charges it before launch/worker admission. A nonempty claim is not
    # a replacement for a real receipt or a new allotment of old budget.
    if not any(e.get('source')==str(rel) and e.get('sha256')==reconciliation['receipt_sha256']
               and consumed in e.get('lineage',[]) and e.get('cost_only_not_admission') is True
               for e in card.get('prior_costs',[])):
        raise RuntimeError('reconciled consumed-run costs absent from actual prior ledger')


def validate_card(card):
    from hybrid_state_contract import CONTRACT_ID
    if card.get('state_contract_id') != CONTRACT_ID:
        raise ValueError('accepted-state field timing contract missing/incompatible')
    from hybrid_coupled_acceleration import CouplingSettings
    CouplingSettings(**card.get('coupling',{}))
    if any('coupling' in p for p in card['phases']):raise ValueError('one shared coupling policy required')
    if card.get("schema") != "hybrid-execution-card-v1":
        raise ValueError("unsupported execution card")
    phases=card["phases"]
    ids=[x["id"] for x in phases]
    if ids != ["native_replay","train_A","train_B","validation","training","test_reference","test_classical","test_hybrid","analysis"]:
        raise ValueError("phase ordering/input boundary differs")
    if len(set(ids))!=len(ids):raise ValueError("duplicate phase")
    trajectories=[x for x in phases if x["kind"]=="trajectory"]
    if sum(x["cycles"]*len(card["base_load_cycle"]) for x in trajectories)!=3600:
        raise ValueError("numerical-step budget mismatch")
    if any(x["cycles"]!=120 for x in trajectories):raise ValueError("unexpected trajectory cap")
    if [x["amplitude_multiplier"] for x in trajectories]!=[.8,1.2,1.,.9,.9,.9]:
        raise ValueError("frozen trajectory amplitude differs")
    if card["base_load_cycle"] != [.02999988,.05999988,.08999988,.11999988,0.]:
        raise ValueError("frozen retained load path differs")
    b=card["budget"]
    if (b["gpu_hours"]!=12 or b["cpu_wall_hours"]!=136 or b["cpu_core_hours"]!=2176
            or b["cpu_cores"]!=16 or card["solver"]["wall_seconds"]!=120):
        raise ValueError("resource card differs from reviewed envelope")
    if (card["training"]["max_updates"]!=20000 or card["training"]["wall_seconds"] not in (21600,28800)
            or card["training"]["fits"]!=1):
        raise ValueError("training allowance differs")
    if next(p["wall_seconds"] for p in phases if p["id"]=="test_hybrid")+card["training"]["wall_seconds"]!=43200:
        raise ValueError("GPU phase allocation must stay within exact12h split")
    if (card["producer"]["hostname"]!="GPUServer8" or not card["producer"]["gpu_uuid"].startswith("GPU-")):
        raise ValueError("unidentified producer")


def execution_specs(card):
    """Required dependency admission precedes every replay/state/fit phase."""
    spec=card.get('plotting_admission')
    if spec!={'id':'plotting_admission','kind':'admission','gpu':False,'wall_seconds':120}:
        raise ValueError('required bounded plotting admission differs')
    if 'matplotlib' not in card['runtime_expected']:raise ValueError('Matplotlib exact-version requirement missing')
    return [spec,*card['phases']]


def initial_totals(card, job_started, code_root=None):
    """Charge actual admission work to the same study envelope before launch."""
    if card.get('prior_costs'):
        if card.get('pre_execution_cost') is not None:raise RuntimeError('duplicate prior cost mechanisms')
        charges=dict(wall_seconds=0.,cpu_seconds=0.,gpu_seconds=0.,numerical_seconds=0.)
        lineages=set();facts=[]
        for entry in card['prior_costs']:
            relative=Path(entry['source'])
            if code_root is None or relative.is_absolute() or '..' in relative.parts:raise RuntimeError('nonlocal prior cost source')
            path=Path(code_root)/relative
            if sha256(path)!=entry['sha256']:raise RuntimeError('frozen prior cost source differs')
            if entry.get('cost_only_not_admission') is not True:raise RuntimeError('past costs cannot admit execution')
            ids=entry['lineage']
            if not isinstance(ids,list) or not ids or any(not isinstance(i,str) or not i for i in ids):raise RuntimeError('invalid prior cost lineage')
            if len(set(ids))!=len(ids) or lineages.intersection(ids):raise RuntimeError('overlapping prior cost lineage')
            lineages.update(ids);source=read_manifest(path);one={}
            for key in charges:
                value=source
                for part in entry['metrics'][key]:value=value[part]
                if isinstance(value,bool) or not isinstance(value,(int,float)):raise RuntimeError('nonnumeric frozen prior cost')
                value=float(value)
                if not __import__('math').isfinite(value) or value<0:raise RuntimeError('invalid frozen prior cost')
                charges[key]+=value;one[key]=value
            if one['numerical_seconds']>one['wall_seconds']:raise RuntimeError('prior numerical cost exceeds wall')
            facts.append(dict(source=str(relative),sha256=entry['sha256'],lineage=ids,**one))
        if charges['wall_seconds']>=card['budget']['cpu_wall_hours']*3600-card['budget']['termination_reserve_seconds']:
            raise RuntimeError('prior work exhausted host allowance')
        if charges['gpu_seconds']>=card['budget']['gpu_hours']*3600-card['budget']['termination_reserve_seconds']:
            raise RuntimeError('prior work exhausted GPU allowance')
        return dict(**charges,phases={},start_monotonic=job_started-charges['wall_seconds'],
                    shared_analysis_seconds=charges['wall_seconds']-charges['numerical_seconds'],
                    pre_execution_cost=dict(**charges,facts=facts,cost_only_not_admission=True))
    pre=card.get('pre_execution_cost')
    if pre is None:
        return dict(wall_seconds=0.,gpu_seconds=0.,numerical_seconds=0.,cpu_seconds=0.,phases={},
                    start_monotonic=job_started,shared_analysis_seconds=0.)
    receipt=Path(pre['receipt'])
    if sha256(receipt)!=pre['receipt_sha256']:raise RuntimeError('admission cost receipt differs')
    actual=read_manifest(receipt)
    if actual.get('passed') is not True:raise RuntimeError('actual Linux admission did not pass')
    wall=float(actual['wall_seconds']);cpu=float(actual['cpu_seconds_children']+actual['cpu_seconds_self'])
    numerical=float(pre['numerical_seconds']);shared=wall-numerical
    if (not all(__import__('math').isfinite(v) for v in (wall,cpu,numerical)) or not 0<=numerical<=wall<=1800
            or cpu<0 or actual['gpu_seconds']!=0 or actual['diagnostic_substeps_max']!=5
            or wall!=pre['wall_seconds'] or cpu!=pre['cpu_seconds']):
        raise RuntimeError('invalid or mismatched actual admission cost')
    return dict(wall_seconds=wall,gpu_seconds=0.,numerical_seconds=numerical,cpu_seconds=cpu,phases={},
                start_monotonic=job_started-wall,shared_analysis_seconds=shared,pre_execution_cost=pre)


def bytes_under(path):
    total=0
    for base,dirs,files in os.walk(path,followlinks=False):
        dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink()]
        for f in files:
            p=Path(base)/f
            if not p.is_symlink():total+=p.stat().st_size
    return total


def gpu_admission(card):
    command=["nvidia-smi","--query-gpu=index,uuid,memory.used,memory.total,utilization.gpu","--format=csv,noheader,nounits"]
    rows=list(csv.reader(io.StringIO(subprocess.check_output(command,text=True,timeout=2))))
    selected=next((r for r in rows if r[1].strip()==card["producer"]["gpu_uuid"]),None)
    if selected is None or int(selected[0])!=card["producer"]["gpu_index"]:
        raise RuntimeError("GPU index/UUID changed")
    if float(selected[2])>64 or float(selected[4])>5:
        raise RuntimeError("selected GPU is occupied; no automatic waiting/rebinding")
    return dict(index=int(selected[0]),uuid=selected[1].strip(),used_mib=float(selected[2]),total_mib=float(selected[3]))


def gpu_usage(card, allowed_pids,usage=None):
    text=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory',
                                  '--format=csv,noheader,nounits'],text=True,timeout=2)
    rows=list(csv.reader(io.StringIO(text)));used=0.;foreign=[]
    for row in rows:
        if len(row)==3 and row[1].strip()==card['producer']['gpu_uuid']:
            pid=int(row[0]);used+=float(row[2])
            if pid not in allowed_pids:foreign.append(pid)
    if usage is not None:usage.update(peak_gpu_mib=max(used,usage.get('peak_gpu_mib') or 0.),foreign_gpu_pids=foreign,gpu_observed=True,gpu_status='observed',gpu_sample_count=usage.get('gpu_sample_count',0)+1,last_gpu_sample_monotonic=perf_counter())
    if foreign:raise RuntimeError('GPU acquired by another process; stop only our worker')
    if used>card['budget']['gpu_vram_gib']*1024:raise RuntimeError('owned GPU memory cap')
    return used


def host_admission(card,runroot,archive):
    if platform.system()!="Linux" or socket.gethostname()!=card["producer"]["hostname"]:
        raise RuntimeError("wrong producer; Mac is development-only")
    if psutil.virtual_memory().available<card["budget"]["ram_gib"]*2**30:
        raise RuntimeError("host RAM capacity below frozen allowance")
    mount=Path('/mnt/data2')
    if not os.path.ismount(mount):raise RuntimeError("canonical data2 mount absent")
    if psutil.disk_usage(mount).free<card["budget"]["free_storage_gib_required"]*2**30:
        raise RuntimeError("data2 free storage below complete allowance")
    for path,base in ((runroot,Path('/mnt/data2/drtao/wennie')),(archive,Path('/mnt/data2/drtao/pidl_archives'))):
        if path.parent!=base or path.name!=card['run_id']:
            raise RuntimeError("attribution/output root mismatch")
    available=os.sched_getaffinity(0)
    if len(available)<card['budget']['cpu_cores']:
        raise RuntimeError("insufficient CPU affinity capacity")
    # Parent and all descendants inherit one shared <=16-core pool.
    os.sched_setaffinity(0,set(sorted(available)[:card['budget']['cpu_cores']]))
    return dict(available_ram_bytes=psutil.virtual_memory().available,
                available_disk_bytes=psutil.disk_usage(mount).free,
                cpu_affinity=sorted(os.sched_getaffinity(0)),load_average=list(os.getloadavg()))


def stop_owned(proc):
    if proc.poll() is None:
        try:
            if os.getpgid(proc.pid)!=proc.pid:raise RuntimeError("child process-group identity changed")
            os.killpg(proc.pid,signal.SIGTERM)
        except ProcessLookupError:
            proc.wait(timeout=10);return
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=10)


def supervise(proc,spec,card,runroot,archive,totals,usage=None,guardian=None):
    usage={} if usage is None else usage
    usage.update(rss_observed=False,rss_sample_count=0,gpu_observed=False,gpu_sample_count=0,gpu_status='pending' if spec['gpu'] else 'not_applicable')
    def measured_peaks():
        return dict(peak_rss_bytes=peak if usage['rss_observed'] else None,peak_gpu_mib=usage.get('peak_gpu_mib') if usage['gpu_observed'] else None)
    start=perf_counter();reserve=card['budget']['termination_reserve_seconds'];peak=0;last_scan=-1.;storage={};gpu_peak=0.;gpu_last=-10.
    try:
        while proc.poll() is None:
            if guardian is not None and guardian.poll() is not None:
                if proc.poll() is not None:break
                raise RuntimeError('independent deadline controller exited')
            elapsed=perf_counter()-start
            if elapsed>spec['wall_seconds']-reserve:raise RuntimeError('phase hard wall cap')
            if perf_counter()-totals['start_monotonic']>card['budget']['cpu_wall_hours']*3600-reserve:
                raise RuntimeError('total allocated host wall cap')
            if spec['gpu'] and totals['gpu_seconds']+elapsed>card['budget']['gpu_hours']*3600-reserve:
                raise RuntimeError('total GPU wall cap')
            if spec['id'] in ('plotting_admission','native_replay','analysis') and totals.get('shared_analysis_seconds',0.)+elapsed>card['budget']['replay_analysis_hours']*3600-reserve:
                raise RuntimeError('shared replay and analysis wall cap')
            if spec['kind']=='trajectory':
                marker=runroot/'active_step.json'
                if marker.exists():
                    m=read_manifest(marker)
                    if m.get('phase')==spec['id'] and perf_counter()-m['start_monotonic']>card['solver']['wall_seconds']:
                        raise RuntimeError('physical-substep hard wall cap')
            tree=[];current_rss_observed=False
            try:
                root=psutil.Process(proc.pid)
                tree=[root,*root.children(recursive=True)]
                rss=sum(p.memory_info().rss for p in tree)
                current_rss_observed=True
                usage.update(rss_observed=True,rss_sample_count=usage['rss_sample_count']+1,last_rss_sample_monotonic=perf_counter())
            except psutil.NoSuchProcess:rss=0
            peak=max(peak,rss)
            usage.update(**measured_peaks(),storage=storage,last_sample_monotonic=perf_counter())
            if rss>card['budget']['ram_gib']*2**30:raise RuntimeError('process-tree RAM cap')
            if spec['gpu'] and elapsed-gpu_last>=5:
                gpu_peak=max(gpu_peak,gpu_usage(card,{proc.pid,*[p.pid for p in tree]},usage=usage))
                gpu_last=elapsed
            if elapsed-last_scan>=10:
                storage['primary_bytes']=bytes_under(runroot);usage.update(storage=dict(storage),last_primary_storage_sample_monotonic=perf_counter())
                storage['archive_bytes']=bytes_under(archive);usage.update(storage=dict(storage),last_archive_storage_sample_monotonic=perf_counter())
                last_scan=elapsed
                if storage['primary_bytes']>card['budget']['primary_gib']*2**30 or storage['archive_bytes']>card['budget']['archive_gib']*2**30:
                    raise RuntimeError('attributed storage cap')
            usage.update(**measured_peaks(),storage=dict(storage),last_sample_monotonic=perf_counter())
            write_json(runroot/'monitor.json',dict(phase=spec['id'],pid=proc.pid,elapsed=elapsed,
                                                    rss_bytes=rss if current_rss_observed else None,peak_rss_bytes=measured_peaks()['peak_rss_bytes'],storage=storage,
                                                    peak_gpu_mib=measured_peaks()['peak_gpu_mib'],rss_observed=usage['rss_observed'],gpu_observed=usage['gpu_observed'],gpu_status=usage['gpu_status'],
                                                    totals_before_phase=totals))
            sleep(1)
        if perf_counter()-start>spec['wall_seconds']:raise RuntimeError('late successful phase exit')
        if perf_counter()-totals['start_monotonic']>card['budget']['cpu_wall_hours']*3600:raise RuntimeError('late total exit')
        if proc.returncode:raise RuntimeError(f"worker exit {proc.returncode}")
        usage.update(**measured_peaks())
        return dict(wall_seconds=perf_counter()-start,**measured_peaks(),storage=storage)
    except BaseException as exc:
        usage.update(stop_reason=str(exc),**measured_peaks(),storage=dict(storage))
        t=perf_counter();stop_owned(proc);usage["termination_seconds"]=perf_counter()-t
        raise


def wait_guard_ready(fd):
    if not select.select([fd],[],[],5)[0] or os.read(fd,1)!=b'1':
        raise RuntimeError('deadline guardian admission failed; worker gate stays closed')


def run_owned_worker(command,code,env,log,spec,card,runroot,archive,totals,usage=None):
    """Guard from spawn onward; no monitor IO participates in deadline control."""
    usage={} if usage is None else usage
    usage.update(peak_rss_bytes=None,peak_gpu_mib=None,rss_observed=False,gpu_observed=False,rss_sample_count=0,gpu_sample_count=0,gpu_status='pending' if spec['gpu'] else 'not_applicable')
    proc=None;guardian=None;left=None;right=None;fds=[]
    try:
        left,right=socket.socketpair(socket.AF_UNIX,socket.SOCK_DGRAM)
        start_r,start_w=os.pipe();ready_r,ready_w=os.pipe();fds=[start_r,start_w,ready_r,ready_w]
        env=dict(os.environ if env is None else env);env['HYBRID_GUARD_FD']=str(right.fileno());env['HYBRID_START_FD']=str(start_r)
        with Path(log).open('w') as handle:
            proc=subprocess.Popen(command,cwd=code,env=env,stdout=handle,stderr=subprocess.STDOUT,
                                  stdin=subprocess.DEVNULL,start_new_session=True,pass_fds=(right.fileno(),start_r))
            reserve=card['budget']['termination_reserve_seconds'];now=perf_counter()
            deadlines=[now+spec['wall_seconds']-reserve,totals['start_monotonic']+card['budget']['cpu_wall_hours']*3600-reserve]
            if spec['gpu']:deadlines.append(now+card['budget']['gpu_hours']*3600-totals['gpu_seconds']-reserve)
            if spec['id'] in ('plotting_admission','native_replay','analysis'):deadlines.append(now+card['budget']['replay_analysis_hours']*3600-totals.get('shared_analysis_seconds',0)-reserve)
            report=runroot/f"guard_{spec['id']}.json"
            guardian=subprocess.Popen([sys.executable,str(Path(code)/'tools/hybrid_deadline_guard.py'),
                '--worker',str(proc.pid),'--supervisor',str(os.getpid()),'--fd',str(left.fileno()),
                '--deadline',str(min(deadlines)),'--step-seconds',str(card['solver']['wall_seconds']),
                '--report',str(report),'--ready-fd',str(ready_w)],cwd=code,env=env,stdout=handle,stderr=subprocess.STDOUT,
                start_new_session=True,pass_fds=(left.fileno(),ready_w))
            os.close(ready_w);fds.remove(ready_w)
            wait_guard_ready(ready_r)
            if spec['gpu']:usage['gate_gpu_admission']=gpu_admission(card)
            os.write(start_w,b'1')
            append_event(runroot/'phases.jsonl',dict(phase=spec['id'],pid=proc.pid,guardian_pid=guardian.pid,
                                                    command=command,log=str(log),start_epoch=time()))
            result=supervise(proc,spec,card,runroot,archive,totals,usage=usage,guardian=guardian)
            guardian.wait(timeout=5)
            audit=read_manifest(report);usage['deadline_guard']=audit
            if guardian.returncode or audit['reason'] is not None:raise RuntimeError('independent deadline stop: '+str(audit.get('reason')))
            return result
    finally:
        if proc is not None:stop_owned(proc)
        if guardian is not None:
            try:guardian.wait(timeout=2)
            except subprocess.TimeoutExpired:stop_owned(guardian)
            report=runroot/f"guard_{spec['id']}.json"
            if report.exists():
                try:usage['deadline_guard']=read_manifest(report)
                except Exception as exc:usage['guard_report_error']=str(exc)
        for fd in fds:os.close(fd)
        for s in (left,right):
            if s is not None:s.close()


def outcome(card,archive,totals):
    ref=read_manifest(archive/'test_reference/summary.json')
    classical=read_manifest(archive/'test_classical/summary.json')
    neural=read_manifest(archive/'test_hybrid/summary.json')
    comparisons=read_manifest(archive/'analysis/summary.json')['methods']
    # Use complete worker wall (setup/IO included), supplied by supervisor totals.
    cf=totals['phases']['test_reference']['wall_seconds']
    cc=totals['phases']['test_classical']['wall_seconds'];ch=totals['phases']['test_hybrid']['wall_seconds']
    criteria=card['criteria']
    if set(comparisons)!={'test_classical','test_hybrid'}:raise RuntimeError('both matched quality reports required')
    n=comparisons['test_hybrid']
    def quality_for(n):
        return (n['mean_J']<=criteria['mean_J_max'] and n['max_J']<=criteria['max_J_max']
             and max(n['max_A_relative'],n['max_r_relative'])<=criteria['history_relative_max']
             and n['max_f_rms']<=criteria['fatigue_absolute_max']
             and n['max_reaction_relative']<=criteria['reaction_relative_max'])
    qualities={k:quality_for(v) for k,v in comparisons.items()}
    quality=qualities['test_hybrid']
    speed=(ch<=(1-criteria['speed_fraction_min'])*min(cf,cc))
    fatigue=all(read_manifest(archive/x/'summary.json')['f_min']<1. for x in ['train_A','train_B','validation','test_reference','test_classical','test_hybrid'])
    offline=sum(totals['phases'][x]['wall_seconds'] for x in ['native_replay','train_A','train_B','validation','training'])+totals['phases'].get('plotting_admission',{}).get('wall_seconds',0.)+totals.get('pre_execution_cost',{}).get('wall_seconds',0.)
    return dict(complete=True,quality_pass=quality,matched_quality=qualities,online_speed_pass=speed,fatigue_coverage=fatigue,
                supports_neural_online_acceleration=bool(all(qualities.values()) and speed and fatigue),
                cost=dict(reference_wall=cf,classical_wall=cc,hybrid_wall=ch,offline_wall=offline,
                          study_evaluation_wall=totals['phases']['analysis']['wall_seconds'],
                          break_even_tasks=offline/(cf-ch) if ch<cf else None),
                claim='one synthetic mesh/material family; no physical or material/geometry generalization',
                reference=ref,classical=classical,hybrid=neural,comparisons=comparisons)


def main():
    job_started=perf_counter()
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--card',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--package',type=Path,required=True);p.add_argument('--review',type=Path)
    p.add_argument('--check',action='store_true');p.add_argument('--execute',action='store_true')
    args=p.parse_args();card=read_manifest(args.card);validate_card(card)
    code=Path(__file__).resolve().parents[1]
    package=read_manifest(args.package);verify_package(code,package)
    if sha256(args.inputs/'inputs.json')!=card['inputs_sha256']:raise RuntimeError('input manifest differs')
    if args.check:
        print(json.dumps(dict(card_valid=True,artifact_id=package['artifact_id'],execution=False),indent=2));return
    require_enabled_execution(card)
    if not args.execute or args.review is None:raise RuntimeError('explicit execution and exact review required')
    review=read_manifest(args.review)
    if (review.get('verdict')!='REVIEW_PASS' or review.get('card_sha256')!=sha256(args.card)
            or review.get('artifact_id')!=package['artifact_id']):raise RuntimeError('review does not admit exact card/code')
    runroot=Path(card['run_root']);archive=Path(card['archive_root'])
    if archive.exists():raise FileExistsError('fresh archive required; no automatic retry/resume')
    host=host_admission(card,runroot,archive)
    # Matplotlib is imported/rendered in the independently bounded first worker,
    # never in this supervisor's unguarded runtime import loop.
    runtime_expected={k:v for k,v in card['runtime_expected'].items() if k!='matplotlib'}
    runtime={name:getattr(importlib.import_module(name),'__version__','unknown') for name in runtime_expected}
    if runtime!=runtime_expected:raise RuntimeError(f'producer runtime differs: {runtime}')
    totals=initial_totals(card,job_started,code)
    archive.mkdir(parents=True)
    for d in ['tmp','jitcache','cache','logs']:(runroot/d).mkdir(exist_ok=True)
    write_json(runroot/'launch_receipt.json',dict(pid=os.getpid(),hostname=socket.gethostname(),
                                                command=sys.argv,card_sha256=sha256(args.card),
                                                artifact_id=package['artifact_id'],host_admission=host,
                                                runtime=runtime,start_epoch=time()))
    def interrupted(sig,frame):raise RuntimeError(f'supervisor interrupted by signal {sig}')
    signal.signal(signal.SIGTERM,interrupted)
    status='failed'
    try:
        for spec in execution_specs(card):
            if spec['gpu']:write_json(runroot/f"gpu_admission_{spec['id']}.json",gpu_admission(card))
            env=os.environ.copy()
            env.update(PYTHONPATH=f'{runroot}/deps:{code}/source:{code}/tools',CUDA_VISIBLE_DEVICES=str(card['producer']['gpu_index']) if spec['gpu'] else '',
                       OMP_NUM_THREADS='16',OPENBLAS_NUM_THREADS='16',MKL_NUM_THREADS='16',NUMEXPR_NUM_THREADS='16',
                       TMPDIR=str(runroot/'tmp'),XDG_CACHE_HOME=str(runroot/'cache'),
                       TORCH_EXTENSIONS_DIR=str(runroot/'jitcache'),PIDL_ARCHIVE_DIR=str(archive),
                       MPLBACKEND='Agg',MPLCONFIGDIR=str(runroot/'cache/matplotlib'))
            env['HYBRID_SUPERVISOR_PID']=str(os.getpid())
            cmd=[sys.executable,'-u',str(code/'tools/hybrid_producer_worker.py'),'--card',str(args.card.resolve()),
                 '--phase',spec['id'],'--inputs',str(args.inputs.resolve()),'--out',str(runroot),'--archive',str(archive)]
            log=runroot/f"logs/{spec['id']}.log"
            phase_started=perf_counter();use_before=resource.getrusage(resource.RUSAGE_CHILDREN)
            usage={};phase_ok=False
            try:
                result_usage=run_owned_worker(cmd,code,env,log,spec,card,runroot,archive,totals,usage=usage)
                usage.update(result_usage)
                phase_ok=True
            finally:
                use_after=resource.getrusage(resource.RUSAGE_CHILDREN)
                usage.update(wall_seconds=perf_counter()-phase_started,
                             cpu_seconds=(use_after.ru_utime+use_after.ru_stime-use_before.ru_utime-use_before.ru_stime),
                             completed=phase_ok)
                totals['phases'][spec['id']]=usage
                totals['wall_seconds']+=usage['wall_seconds'];totals['cpu_seconds']+=usage['cpu_seconds']
                if spec['id'] in ('plotting_admission','native_replay','analysis'):totals['shared_analysis_seconds']+=usage['wall_seconds']
                if spec['gpu']:totals['gpu_seconds']+=usage['wall_seconds']
                if spec['kind']=='trajectory':totals['numerical_seconds']+=usage['wall_seconds']
                if spec['id']=='plotting_admission':
                    try:
                        failure_path=runroot/'plotting_admission_failure.json'
                        if failure_path.exists():usage['dependency_failure']=read_manifest(failure_path)
                    except (OSError,ValueError) as exc:
                        # Auxiliary diagnostics cannot mask the worker failure
                        # or prevent its basic wall/CPU charge.
                        usage['dependency_failure_read_error']=f'{type(exc).__name__}: {exc}'
                # Failed/killed work is always charged, even without a worker result.
                write_json(runroot/'cost_ledger.json',totals)
            result=read_manifest(runroot/f"result_{spec['id']}.json")
            if result.get('completed',result.get('passed')) is not True:raise RuntimeError('incomplete worker result')
            if spec['id']=='plotting_admission':
                runtime['matplotlib']=result['matplotlib'];usage['plotting_runtime']=result
            if totals['numerical_seconds']>120*3600:raise RuntimeError('numerical work envelope exhausted')
        write_json(runroot/'decision.json',outcome(card,archive,totals));status='succeeded'
    except BaseException as exc:
        write_json(runroot/'failure.json',dict(reason=str(exc),totals=totals,
                                               rule='no retries/partial fit/threshold relaxation; inspect latest durable versions'))
        raise
    finally:
        totals['producer_wall_seconds']=perf_counter()-job_started
        totals['total_job_wall_seconds']=perf_counter()-totals['start_monotonic']
        totals['supervisor_overhead_seconds']=totals['total_job_wall_seconds']-totals['wall_seconds']
        totals['allocated_cpu_core_hours_upper']=16*totals['total_job_wall_seconds']/3600
        write_json(runroot/'cost_ledger.json',totals)
        write_json(runroot/'terminal.json',dict(status=status,totals=totals,end_epoch=time()))


if __name__=='__main__':main()
