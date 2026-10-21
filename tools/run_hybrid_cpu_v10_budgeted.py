"""One CPU-only original train_A trajectory; bounded HQ-delegated package.

Reuses the reviewed gated worker, pidfd guardian and resource supervisor.
No install, GPU query, training, second case, resume, or automatic retry.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import signal
import socket
import subprocess
import sys
from time import time,perf_counter

RUN='pf_hybrid_solver_v10_20261021_r7'
BASE=Path('/mnt/data2/drtao/wennie')
ROOT=BASE/RUN
ARCHIVE=Path('/mnt/data2/drtao/pidl_archives')/RUN
INPUTS=BASE/'pf_hybrid_solver_v6_20261020_r3/inputs'
DEPS=ROOT/'deps'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def canonical_sha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()
def regular(path):
    p=Path(path)
    if any(x.is_symlink() for x in [p,*p.parents]):raise RuntimeError('symlink in selected producer path')
    return p


def validate(card):
    if (card.get('schema')!='hybrid-cpu-trajectory-v10' or card.get('execution_enabled') is not True
            or card.get('run_id')!=RUN or card.get('run_root')!=str(ROOT)
            or card.get('archive_root')!=str(ARCHIVE) or card.get('inputs')!=str(INPUTS)):
        raise RuntimeError('wrong CPU trajectory identity/authority')
    if card['producer']!=dict(hostname='GPUServer8',account='drtao',gpu=None):raise RuntimeError('wrong producer')
    if card['authority']['authority_type']!='human_delegated_hq' or card['authority']['human_message']!='01a15b4c-2e3a-7772-b74b-46f4ab752766' or card['authority'].get('authority_id')!='HQ-FEM-BOX-LINEARIZED-RESIDUAL-TRUST-SUBPROBLEM-R007-20261021':
        raise RuntimeError('human delegation source absent')
    b=card['budget']
    wanted=dict(total_envelope_seconds=14400,post_execution_reserve_seconds=600,
        cpu_wall_hours=13800/3600,cpu_cores=4,gpu_hours=0,ram_gib=32,
        address_space_gib=32,primary_gib=1,archive_gib=7,local_retrieval_gib=8,free_storage_gib_required=16,
        producer_retries=0,training_fits=0,numerical_substeps=600,
        replay_analysis_hours=0,termination_reserve_seconds=45)
    if b!=wanted:raise RuntimeError('bounded CPU envelope differs')
    if card['package_start_epoch']!=1792544667. or card['absolute_package_deadline_epoch']!=1792559067.:
        raise RuntimeError('package clock/previous preparation charge differs')
    if card['base_load_cycle']!=[.02999988,.05999988,.08999988,.11999988,0.]:raise RuntimeError('loading changed')
    expected=[dict(id='train_A',kind='trajectory',gpu=False,wall_seconds=13800,
        cycles=120,amplitude_multiplier=.8,role='reference',initializer='previous')]
    if card['phases']!=expected:raise RuntimeError('one original600-step trajectory only')
    if card.get('snapshot_storage')!='lossless_npz_deflate1':raise RuntimeError('complete lossless snapshot policy absent')
    original=dict(force_scale=1.,damage_gradient_scale=1.,force_tolerance=1e-8,
        joint_residual_sum_tolerance=4e-6,damage_tolerance=1e-7,bound_tolerance=1e-10,
        fatigue_tolerance=1e-8,qp_precision=1e-10,max_outer=100,max_mechanics=50,
        max_qp=200000,wall_seconds=300.)
    if card['solver']!=original:raise RuntimeError('original physical settings changed')
    c=card['coupling']
    if (c['mode']!='box_residual_trust' or c['mechanics_solver']!='recycled_gmres'
            or c['backtrack_candidates']!=4 or c['schur_trigger_ratio']!=.9
            or c['schur_restart']!=16 or c['schur_cycles']!=3 or c['schur_action_limit']!=64
            or c['schur_relative_tolerance']!=1e-3 or c['max_newton_directions']!=8
            or c['trust_trials']!=8 or c['trust_initial_radius']!=.1 or c['trust_max_radius']!=.25 or c['trust_min_radius']!=1e-8
            or c['subproblem_action_limit']!=100 or c['subproblem_update_limit']!=16 or c['subspace_steps']!=2
            or c['block_relative_tolerance']!=1e-3 or c['coefficient_l1_cap']!=5.):raise RuntimeError('finite coupling policy differs')
    if card['inputs_sha256']!='51776e2ebb9642a2f6805a87e34842d608f44624b0d0fb06aa4b0792e95f4c1c':
        raise RuntimeError('original input manifest changed')


def verify(root,card,package,review):
    validate(card)
    if canonical_sha(package['files'])!=package['artifact_id']:raise RuntimeError('artifact manifest differs')
    for rel,sha in package['files'].items():
        p=Path(rel)
        if p.is_absolute() or '..' in p.parts or digest(regular(root/'code'/p))!=sha:raise RuntimeError('source differs')
    if (review.get('verdict')!='REVIEW_PASS' or review['artifact_id']!=package['artifact_id']
            or review['card_sha256']!=digest(root/'execution_card.json')):raise RuntimeError('exact review differs')
    if digest(regular(INPUTS/'inputs.json'))!=card['inputs_sha256']:raise RuntimeError('input manifest differs')
    verify_retained_deps(root/'code',card)


def verify_retained_deps(code,card):
    rel=Path(card['retained_deps_manifest'])
    if rel.is_absolute() or '..' in rel.parts:raise RuntimeError('nonlocal retained dependency manifest')
    path=regular(code/rel)
    if digest(path)!=card['retained_deps_manifest_sha256']:raise RuntimeError('retained dependency binding differs')
    expected=read(path)['files'];found=set()
    for base,dirs,files in os.walk(regular(DEPS),followlinks=False):
        for name in dirs:
            if (Path(base)/name).is_symlink():raise RuntimeError('dependency directory symlink')
            if name=='__pycache__':raise RuntimeError('unexpected dependency bytecode cache')
        for name in files:
            if name.endswith('.pyc'):raise RuntimeError('unexpected dependency bytecode')
            p=regular(Path(base)/name);key=str(p.relative_to(DEPS));found.add(key)
            if key not in expected or digest(p)!=expected[key]:raise RuntimeError('retained OSQP bytes differ')
    if found!=set(expected):raise RuntimeError('retained dependency file closure differs')


def launch(root,card,package,review):
    verify(root,card,package,review)
    if platform.system()!='Linux' or socket.gethostname()!='GPUServer8':raise RuntimeError('wrong producer')
    if ARCHIVE.exists():raise RuntimeError('archive exists; never resume')
    charged=time()-card['package_start_epoch']
    seconds=card['budget']['cpu_wall_hours']*3600-charged-45
    if charged<0 or seconds<=0:raise RuntimeError('package budget exhausted before launch')
    reservation=root/'launch_reservation.json'
    # Exclusive reservation survives unknown SSH/receipt outcome. Every second
    # invocation is refused, regardless of whether a PID receipt was returned.
    fd=os.open(reservation,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    allowed=sorted(os.sched_getaffinity(0))
    if len(allowed)<4:raise RuntimeError('fewer than4 available CPUs')
    os.sched_setaffinity(0,set(allowed[:4]))
    resource.setrlimit(resource.RLIMIT_AS,(32*2**30,32*2**30))
    cmd=['/usr/bin/timeout','--signal=TERM','--kill-after=20s',f'{seconds:.6f}s',
        sys.executable,'-u',str(root/'code/tools/run_hybrid_cpu_v10_budgeted.py'),'--supervise']
    receipt=dict(state='reserved',run_id=RUN,command=cmd,artifact_id=package['artifact_id'],
        card_sha256=digest(root/'execution_card.json'),epoch=time(),
        prelaunch_package_wall_charge=charged,outer_timeout_seconds=seconds,cpu_affinity=allowed[:4],
        gpu_seconds=0,scientific_attempt_limit=1)
    with os.fdopen(fd,'w') as f:json.dump(receipt,f);f.flush();os.fsync(f.fileno())
    env=dict(os.environ)
    for name in ['tmp','cache','jitcache','logs']:(root/name).mkdir(exist_ok=True)
    env.update(PYTHONPATH=f'{DEPS}:{root}/code/source:{root}/code/tools',CUDA_VISIBLE_DEVICES='',
        OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='4',MKL_NUM_THREADS='4',NUMEXPR_NUM_THREADS='4',
        TMPDIR=str(root/'tmp'),XDG_CACHE_HOME=str(root/'cache'),TORCH_EXTENSIONS_DIR=str(root/'jitcache'),
        PYTHONWARNINGS='error',MPLBACKEND='Agg',MPLCONFIGDIR=str(root/'cache/matplotlib'),PYTHONDONTWRITEBYTECODE='1')
    with (root/'supervisor.log').open('x') as log:
        proc=subprocess.Popen(cmd,cwd=root/'code',env=env,stdin=subprocess.DEVNULL,
            stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    receipt.update(state='spawned',pid=proc.pid)
    # Reservation written before spawn remains authoritative if this write fails.
    tmp=reservation.with_suffix('.tmp');tmp.write_text(json.dumps(receipt,indent=2)+'\n');tmp.replace(reservation)
    print(json.dumps(receipt),flush=True)


def supervise_cpu(root,card,package,review):
    # Heavy imports and actual version admission are inside GNU timeout.
    # Leave a hard32GiB ceiling that the worker can lower to its30GiB partition;
    # this supervisor remains at1.5GiB soft, guardian at128MiB. Full owned-tree
    # RSS/VMS is monitored including the outer GNU timeout.
    resource.setrlimit(resource.RLIMIT_AS,(1536*2**20,32*2**30))
    import importlib
    import psutil
    from hybrid_producer_common import write_json
    from run_hybrid_producer import run_owned_worker
    verify(root,card,package,review)
    if platform.system()!='Linux' or socket.gethostname()!='GPUServer8' or os.geteuid()!=__import__('pwd').getpwnam('drtao').pw_uid:
        raise RuntimeError('wrong runtime host/account')
    if not os.path.ismount('/mnt/data2') or os.environ.get('CUDA_VISIBLE_DEVICES')!='':raise RuntimeError('mount/CPU isolation differs')
    if len(os.sched_getaffinity(0))>4 or resource.getrlimit(resource.RLIMIT_AS)[0]>32*2**30:raise RuntimeError('CPU/AS envelope not inherited')
    if psutil.virtual_memory().available<32*2**30 or psutil.disk_usage('/mnt/data2').free<16*2**30:
        raise RuntimeError('resource admission failed')
    runtime={name:getattr(importlib.import_module(name),'__version__','unknown') for name in card['runtime_expected']}
    if runtime!=card['runtime_expected']:raise RuntimeError('actual dependency imports differ')
    for rel,sha in read(INPUTS/'inputs.json')['assets'].items():
        p=Path(rel)
        if p.is_absolute() or '..' in p.parts or digest(regular(INPUTS/p))!=sha:raise RuntimeError('original input asset differs')
    regular(ARCHIVE);ARCHIVE.mkdir(exist_ok=False)
    started=perf_counter();charge=time()-card['package_start_epoch']
    if charge<0:raise RuntimeError('negative preparation wall charge')
    outer=psutil.Process(os.getppid())
    command=outer.cmdline()
    if not command or Path(command[0]).name!='timeout' or not any(RUN in x for x in command):
        raise RuntimeError('outer timeout ownership differs')
    totals=dict(start_monotonic=started-charge,phases={},gpu_seconds=0.,resource_owner_pid=outer.pid,
        prelaunch_package_wall_charge=charge,old_research_known_wall_seconds=card['old_research_known_wall_seconds'],
        historical_unknown_control_reserve_seconds=600.,unknown_old_CPU_not_zero=True,
        prior_R4_conservative_package_charge_seconds=card['prior_R4_conservative_package_charge_seconds'],
        prior_R5_conservative_package_charge_seconds=card['prior_R5_conservative_package_charge_seconds'],
        prior_R6_conservative_package_charge_seconds=card['prior_R6_conservative_package_charge_seconds'])
    write_json(root/'launch_receipt.json',dict(pid=os.getpid(),hostname=socket.gethostname(),epoch=time(),
        artifact_id=package['artifact_id'],card_sha256=digest(root/'execution_card.json'),runtime=runtime,
        inputs_read_only=str(INPUTS),cpu_affinity=sorted(os.sched_getaffinity(0)),gpu=None,
        address_space_limit_bytes=resource.getrlimit(resource.RLIMIT_AS)[0]))
    def interrupted(sig,frame):raise RuntimeError(f'CPU supervisor interrupted {sig}')
    signal.signal(signal.SIGTERM,interrupted)
    status='failed';usage={};phase_started=perf_counter();before=resource.getrusage(resource.RUSAGE_CHILDREN)
    try:
        env=dict(os.environ);env['HYBRID_SUPERVISOR_PID']=str(os.getpid())
        env.update(HYBRID_WORKER_AS_BYTES=str(30*2**30),HYBRID_GUARD_AS_BYTES=str(128*2**20))
        cmd=[sys.executable,'-u',str(root/'code/tools/hybrid_producer_worker.py'),
            '--card',str(root/'execution_card.json'),'--phase','train_A',
            '--inputs',str(INPUTS),'--out',str(root),'--archive',str(ARCHIVE)]
        result=run_owned_worker(cmd,root/'code',env,root/'logs/train_A.log',card['phases'][0],
            card,root,ARCHIVE,totals,usage=usage)
        usage.update(result)
        summary=read(ARCHIVE/'train_A/summary.json')
        if not summary.get('completed') or summary.get('states')!=600 or not summary.get('physical_acceptance'):
            raise RuntimeError('incomplete continuous600-step trajectory')
        status='succeeded'
    except BaseException as exc:
        write_json(root/'failure.json',dict(reason=str(exc),scientific_retry=False,usage=usage))
        raise
    finally:
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        usage.update(wall_seconds=perf_counter()-phase_started,
            cpu_seconds=after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
            completed=status=='succeeded')
        totals.update(phases={'train_A':usage},producer_wall_seconds=perf_counter()-started,
            new_package_wall_charge=perf_counter()-totals['start_monotonic'],
            new_package_allocated_core_hours_upper=4*(perf_counter()-totals['start_monotonic'])/3600,
            actual_GPU_seconds=0.,training_fits=0)
        totals['old_known_plus_new_charged_wall_seconds']=totals['old_research_known_wall_seconds']+totals['prior_R4_conservative_package_charge_seconds']+totals['prior_R5_conservative_package_charge_seconds']+totals['prior_R6_conservative_package_charge_seconds']+totals['new_package_wall_charge']
        write_json(root/'cost_ledger.json',totals)
        write_json(root/'terminal.json',dict(status=status,run_id=RUN,epoch=time(),totals=totals,
            scope='one continuous train_A only; no NN or other cases'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--launch',action='store_true');p.add_argument('--supervise',action='store_true');a=p.parse_args()
    if a.launch==a.supervise:raise RuntimeError('select exactly launch or supervise')
    card=read(ROOT/'execution_card.json');package=read(ROOT/'source_manifest.json');review=read(ROOT/'execution_review.json')
    if a.launch:launch(ROOT,card,package,review)
    else:
        try:supervise_cpu(ROOT,card,package,review)
        except BaseException as exc:
            # Admission may fail before heavy imports/worker creation; still
            # retain an honest terminal rather than an ambiguous silent exit.
            if not (ROOT/'terminal.json').exists():
                data=dict(status='failed_before_worker_or_during_admission',run_id=RUN,
                    reason=str(exc),epoch=time(),new_package_wall_charge=time()-card['package_start_epoch'],
                    worker_started=(ROOT/'phases.jsonl').exists(),automatic_retry=False)
                temp=ROOT/'terminal.tmp';temp.write_text(json.dumps(data,indent=2)+'\n');temp.replace(ROOT/'terminal.json')
            raise


if __name__=='__main__':main()
