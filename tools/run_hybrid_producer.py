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
import signal
import socket
import subprocess
import sys
from time import perf_counter, sleep, time

import psutil

from hybrid_inputs import sha256, read_manifest
from hybrid_producer_common import verify_package, write_json, append_event


def validate_card(card):
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
    if (card["training"]["max_updates"]!=20000 or card["training"]["wall_seconds"]!=28800
            or card["training"]["fits"]!=1):
        raise ValueError("training allowance differs")
    if (card["producer"]["hostname"]!="GPUServer8" or not card["producer"]["gpu_uuid"].startswith("GPU-")):
        raise ValueError("unidentified producer")


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
    rows=list(csv.reader(io.StringIO(subprocess.check_output(command,text=True,timeout=15))))
    selected=next((r for r in rows if r[1].strip()==card["producer"]["gpu_uuid"]),None)
    if selected is None or int(selected[0])!=card["producer"]["gpu_index"]:
        raise RuntimeError("GPU index/UUID changed")
    if float(selected[2])>64 or float(selected[4])>5:
        raise RuntimeError("selected GPU is occupied; no automatic waiting/rebinding")
    return dict(index=int(selected[0]),uuid=selected[1].strip(),used_mib=float(selected[2]),total_mib=float(selected[3]))


def gpu_usage(card, allowed_pids):
    text=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory',
                                  '--format=csv,noheader,nounits'],text=True,timeout=15)
    rows=list(csv.reader(io.StringIO(text)));used=0.
    for row in rows:
        if len(row)==3 and row[1].strip()==card['producer']['gpu_uuid']:
            pid=int(row[0]);used+=float(row[2])
            if pid not in allowed_pids:raise RuntimeError('GPU acquired by another process; stop only our worker')
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
        if os.getpgid(proc.pid)!=proc.pid:raise RuntimeError("child process-group identity changed")
        os.killpg(proc.pid,signal.SIGTERM)
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=10)


def supervise(proc,spec,card,runroot,archive,totals):
    start=perf_counter();peak=0;last_scan=-1.;storage={};gpu_peak=0.;gpu_last=-10.
    try:
        while proc.poll() is None:
            elapsed=perf_counter()-start
            if elapsed>spec['wall_seconds']:raise RuntimeError('phase hard wall cap')
            if perf_counter()-totals['start_monotonic']>card['budget']['cpu_wall_hours']*3600:
                raise RuntimeError('total allocated host wall cap')
            if spec['gpu'] and totals['gpu_seconds']+elapsed>card['budget']['gpu_hours']*3600:
                raise RuntimeError('total GPU wall cap')
            if spec['kind']=='trajectory':
                marker=runroot/'active_step.json'
                if marker.exists():
                    m=read_manifest(marker)
                    if m.get('phase')==spec['id'] and time()-m['start_epoch']>card['solver']['wall_seconds']:
                        raise RuntimeError('physical-substep hard wall cap')
            tree=[]
            try:
                root=psutil.Process(proc.pid)
                tree=[root,*root.children(recursive=True)]
                rss=sum(p.memory_info().rss for p in tree if p.is_running())
            except psutil.NoSuchProcess:rss=0
            peak=max(peak,rss)
            if rss>card['budget']['ram_gib']*2**30:raise RuntimeError('process-tree RAM cap')
            if spec['gpu'] and elapsed-gpu_last>=5:
                gpu_peak=max(gpu_peak,gpu_usage(card,{proc.pid,*[p.pid for p in tree]}))
                gpu_last=elapsed
            if elapsed-last_scan>=10:
                storage={'primary_bytes':bytes_under(runroot),'archive_bytes':bytes_under(archive)}
                last_scan=elapsed
                if storage['primary_bytes']>card['budget']['primary_gib']*2**30 or storage['archive_bytes']>card['budget']['archive_gib']*2**30:
                    raise RuntimeError('attributed storage cap')
            write_json(runroot/'monitor.json',dict(phase=spec['id'],pid=proc.pid,elapsed=elapsed,
                                                    rss_bytes=rss,peak_rss_bytes=peak,storage=storage,
                                                    peak_gpu_mib=gpu_peak,
                                                    totals_before_phase=totals))
            sleep(1)
        if proc.returncode:raise RuntimeError(f"worker exit {proc.returncode}")
        return dict(wall_seconds=perf_counter()-start,peak_rss_bytes=peak,peak_gpu_mib=gpu_peak,storage=storage)
    except BaseException:
        stop_owned(proc)
        raise


def outcome(card,archive,totals):
    ref=read_manifest(archive/'test_reference/summary.json')
    classical=read_manifest(archive/'test_classical/summary.json')
    neural=read_manifest(archive/'test_hybrid/summary.json')
    comparisons=read_manifest(archive/'analysis/summary.json')['methods']
    # Use complete worker wall (setup/IO included), supplied by supervisor totals.
    cf=totals['phases']['test_reference']['wall_seconds']
    cc=totals['phases']['test_classical']['wall_seconds'];ch=totals['phases']['test_hybrid']['wall_seconds']
    criteria=card['criteria']
    n=comparisons['test_hybrid']
    quality=(n['mean_J']<=criteria['mean_J_max'] and n['max_J']<=criteria['max_J_max']
             and max(n['max_A_relative'],n['max_r_relative'])<=criteria['history_relative_max']
             and n['max_f_rms']<=criteria['fatigue_absolute_max']
             and n['max_reaction_relative']<=criteria['reaction_relative_max'])
    speed=(ch<=(1-criteria['speed_fraction_min'])*min(cf,cc))
    fatigue=all(read_manifest(archive/x/'summary.json')['f_min']<1. for x in ['train_A','train_B','validation','test_reference','test_classical','test_hybrid'])
    offline=sum(totals['phases'][x]['wall_seconds'] for x in ['native_replay','train_A','train_B','validation','training'])
    return dict(complete=True,quality_pass=quality,online_speed_pass=speed,fatigue_coverage=fatigue,
                supports_neural_online_acceleration=bool(quality and speed and fatigue),
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
    if not args.execute or args.review is None:raise RuntimeError('explicit execution and exact review required')
    review=read_manifest(args.review)
    if (review.get('verdict')!='REVIEW_PASS' or review.get('card_sha256')!=sha256(args.card)
            or review.get('artifact_id')!=package['artifact_id']):raise RuntimeError('review does not admit exact card/code')
    runroot=Path(card['run_root']);archive=Path(card['archive_root'])
    if archive.exists():raise FileExistsError('fresh archive required; no automatic retry/resume')
    host=host_admission(card,runroot,archive)
    runtime={name:getattr(importlib.import_module(name),'__version__','unknown') for name in card['runtime_expected']}
    if runtime!=card['runtime_expected']:raise RuntimeError(f'producer runtime differs: {runtime}')
    archive.mkdir(parents=True)
    for d in ['tmp','jitcache','cache','logs']:(runroot/d).mkdir(exist_ok=True)
    totals=dict(wall_seconds=0.,gpu_seconds=0.,numerical_seconds=0.,cpu_seconds=0.,phases={},
                start_monotonic=job_started)
    write_json(runroot/'launch_receipt.json',dict(pid=os.getpid(),hostname=socket.gethostname(),
                                                command=sys.argv,card_sha256=sha256(args.card),
                                                artifact_id=package['artifact_id'],host_admission=host,
                                                runtime=runtime,start_epoch=time()))
    def interrupted(sig,frame):raise RuntimeError(f'supervisor interrupted by signal {sig}')
    signal.signal(signal.SIGTERM,interrupted)
    status='failed'
    try:
        for spec in card['phases']:
            if spec['gpu']:write_json(runroot/f"gpu_admission_{spec['id']}.json",gpu_admission(card))
            env=os.environ.copy()
            env.update(PYTHONPATH=f'{runroot}/deps:{code}/source:{code}/tools',CUDA_VISIBLE_DEVICES=str(card['producer']['gpu_index']) if spec['gpu'] else '',
                       OMP_NUM_THREADS='16',OPENBLAS_NUM_THREADS='16',MKL_NUM_THREADS='16',NUMEXPR_NUM_THREADS='16',
                       TMPDIR=str(runroot/'tmp'),XDG_CACHE_HOME=str(runroot/'cache'),
                       TORCH_EXTENSIONS_DIR=str(runroot/'jitcache'),PIDL_ARCHIVE_DIR=str(archive))
            cmd=[sys.executable,'-u',str(code/'tools/hybrid_producer_worker.py'),'--card',str(args.card.resolve()),
                 '--phase',spec['id'],'--inputs',str(args.inputs.resolve()),'--out',str(runroot),'--archive',str(archive)]
            log=runroot/f"logs/{spec['id']}.log"
            phase_started=perf_counter();use_before=resource.getrusage(resource.RUSAGE_CHILDREN)
            usage={};phase_ok=False
            try:
                with log.open('w') as handle:
                    proc=subprocess.Popen(cmd,cwd=code,env=env,stdout=handle,stderr=subprocess.STDOUT,
                                          stdin=subprocess.DEVNULL,start_new_session=True)
                    append_event(runroot/'phases.jsonl',dict(phase=spec['id'],pid=proc.pid,command=cmd,log=str(log),start_epoch=time()))
                    usage=supervise(proc,spec,card,runroot,archive,totals)
                phase_ok=True
            finally:
                use_after=resource.getrusage(resource.RUSAGE_CHILDREN)
                usage.update(wall_seconds=perf_counter()-phase_started,
                             cpu_seconds=(use_after.ru_utime+use_after.ru_stime-use_before.ru_utime-use_before.ru_stime),
                             completed=phase_ok)
                totals['phases'][spec['id']]=usage
                totals['wall_seconds']+=usage['wall_seconds'];totals['cpu_seconds']+=usage['cpu_seconds']
                if spec['gpu']:totals['gpu_seconds']+=usage['wall_seconds']
                if spec['kind']=='trajectory':totals['numerical_seconds']+=usage['wall_seconds']
                # Failed/killed work is always charged, even without a worker result.
                write_json(runroot/'cost_ledger.json',totals)
            result=read_manifest(runroot/f"result_{spec['id']}.json")
            if result.get('completed',result.get('passed')) is not True:raise RuntimeError('incomplete worker result')
            if totals['numerical_seconds']>120*3600:raise RuntimeError('numerical work envelope exhausted')
        write_json(runroot/'decision.json',outcome(card,archive,totals));status='succeeded'
    except BaseException as exc:
        write_json(runroot/'failure.json',dict(reason=str(exc),totals=totals,
                                               rule='no retries/partial fit/threshold relaxation; inspect latest durable versions'))
        raise
    finally:
        totals['total_job_wall_seconds']=perf_counter()-job_started
        totals['supervisor_overhead_seconds']=totals['total_job_wall_seconds']-totals['wall_seconds']
        totals['allocated_cpu_core_hours_upper']=16*totals['total_job_wall_seconds']/3600
        write_json(runroot/'cost_ledger.json',totals)
        write_json(runroot/'terminal.json',dict(status=status,totals=totals,end_epoch=time()))


if __name__=='__main__':main()
