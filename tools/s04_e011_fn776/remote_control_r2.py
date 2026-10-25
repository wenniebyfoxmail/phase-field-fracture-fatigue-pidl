"""Literal future SSH stdin program. Preparation only AST-parses this file."""
from pathlib import Path
import contextlib
import datetime as dt
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import tarfile
import time

RUN = 'pf_s04e011_uvh_c1_fn776_r7_20261025'
CARD = 'S04-E011-UVH-C1-FN776-CARD-r7'
ROOT = Path('/mnt/data2/drtao/wennie') / RUN
OUT = Path('/mnt/data2/drtao/pidl_archives') / RUN
CODE = ROOT/'code'
CONTRACT = json.loads('{"protocol": "S04-E011-UVH-C1-FN776-v1", "run_id": "pf_s04e011_uvh_c1_fn776_r7_20261025", "cycle": 1, "substep": 4, "load": 0.11999988, "FEM_outer": 9, "source_base": "bf0f21b572ad2f5a74d30dfcf8fbf402ece2ab08", "files": [{"role": "state", "path": "/mnt/data2/drtao/wennie/pf_s04e011_pbd_2c7c5dc_20261017T2110Z_production/inputs/c1_peak.npz", "local_reference": "/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/pidl_block_preparation_20261017_v1/inputs/c1_peak.npz", "bytes": 15183163, "sha256": "ac63ba676376179f0539c156e3fd49f8e74c5eba386f684c71a617bb637b7fdd", "decode_fields": ["nodes", "cells", "freeu", "u_fem", "v_fem", "d_fem"]}, {"role": "model", "path": "/mnt/data2/drtao/pidl_archives/pf_s04e011_pidl_pair_ad749c8_20261008T0912Z/probeDriver_hl8_n400_seed1_AT1_numerical_carrara_asy_aT0.5_Ncyc120_Nstep601_U0.12_s04e011_q4_production_ad749c8_current_active_native_q4_gp4_femIrrGP4_hardAlphaRecoverU0_u0.0299999-0.0599999-0.0899999-0.12-0/best_models/trained_1NN_4.pt", "bytes": 4510165, "sha256": "9c4ebbe4bcf1d4bc6b4997f1072a6a5f68e0c94783d0365b0224a7175ed12d1b", "decode_fields": ["weights_only state_dict"]}, {"role": "frozen_transform", "path": "/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_r2_20261018/head.npz", "bytes": 1204696, "sha256": "deaf3fea860a4563df84f7909afbde49d76430b633bce542b4896ef9526e8d65", "decode_fields": ["transform"]}, {"role": "frozen_summary", "path": "/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_r2_20261018/summary.json", "bytes": 2527, "sha256": "ee4062e4e9d990bee7b5c7507301894b53c88f57c833c67ea092cbdbcafaa877", "decode_fields": ["protocol", "run_id", "original", "saved_PBD", "head", "retained_gradient_l2", "full_head_gradient_l2", "full_head_gradient_inf", "numerical_energy_uncertainty", "stationarity_screen"]}, {"role": "frozen_basis", "path": "/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_r2_20261018/basis.json", "bytes": 11038, "sha256": "f6d6c38ddb75460e7490f96b8a0743659cfad52117fd3455b30580228c5ccda3", "decode_fields": ["rank", "columns", "rcond", "retained_condition", "omitted_directions"]}], "read_semantics": "Future execution only: hash all five exact whole files once, then decode only listed keys; PT weights_only state_dict. head.npz permits transform only, never z/uv_weight/uv_bias. Metadata identities copied from the existing transfer_manifest without reading or hashing source payloads during preparation.", "rcond": 1e-10, "relative_gain_screen": 0.0001, "resource_policy": {"physical_GPU": 7, "gpu_uuid": "GPU-350d3f31-8bd6-4257-4d4c-21ad344eaa81", "minimum_initial_free_MiB": 12288, "minimum_runtime_free_MiB": 4096, "maximum_admission_utilization_percent": 10, "admission_samples": 3, "admission_interval_seconds": 1, "runtime_monitor_interval_seconds": 1, "unknown_or_unreadable_process": "stop_owned_child_only", "admission_modes": ["empty", "exact_services"], "lock_admission_mode_for_attempt": true, "allow_only_exact_services_plus_worker": true, "services": [{"pid": 2742304, "start_ticks": 534715435, "uids": [0, 0, 0, 0], "cmdline_sha256": "9df93584a40b493212aa581aaa5a51566636332610ea3c9f7a7c80a5931efe81", "cgroup_sha256": "55662a44f20befbec491c4dae0247b25b3edc7b1832ee39454e92556db77b5e6", "baseline_MiB": 494, "maximum_MiB": 1518, "description": "python angle_main.py", "utc": "2026-10-18T20:58:40.170059+00:00"}, {"pid": 2742215, "start_ticks": 534715397, "uids": [0, 0, 0, 0], "cmdline_sha256": "3ecbfd5be66e5e0f72dc6714728130af58640b3526927564f9168b453ccc3c96", "cgroup_sha256": "13748762b00b39b9a979c55164b6945788a8d4ed7c74e4134f499cd9be021d33", "baseline_MiB": 446, "maximum_MiB": 1470, "description": "/usr/bin/python3.10 /usr/local/bin/uvicorn det_main:service --host 0.0.0.0 --port 18093", "utc": "2026-10-18T20:58:40.170059+00:00"}, {"pid": 651952, "start_ticks": 541746716, "uids": [0, 0, 0, 0], "cmdline_sha256": "be18325d0086a499e503b772c5a74d63a708299a314533ef5711f5cf5b853808", "cgroup_sha256": "a1e3fcdf826b0ef154308aec0ff2d84eabf72cd221b321f5f1db06e001ee468e", "baseline_MiB": 5638, "maximum_MiB": 6144, "description": "root Docker-scoped python -m uvicorn app.main:app --host 0.0.0.0 --port 28011 --workers 1", "utc": "2026-10-25T17:10:13+00:00"}], "minimum_host_available_kB": 16777216, "minimum_data2_free_bytes": 5368709120}, "work_ledger": {"total": 25424, "curvature": 24832, "controls": 64, "trials": 512, "final": 16, "curvature_slot_units": 1552, "hvp_cost": 2, "energy_or_energy_and_gradient_cost": 1, "standalone_gradient_cost": 1, "no_reallocation": true}, "resource_revision": "GPU7-FN776-shared-r2-uvicorn28011", "fn776": {"seed": 1, "rank": 388, "z_dimension": 776, "max_outer_steps": 16, "max_backtracking_trials": 32, "max_linear_refinements": 3, "gp_chunk": 4096, "curvature_slot_units": 1552, "z_gradient_inf_threshold": 1e-08, "field_abs_tolerance": 1e-09, "energy_abs_tolerance": 1e-10, "derivative_abs_tolerance": 1e-08, "derivative_relative_tolerance": 1e-08, "nonzero_probe_norm": 1e-06, "symmetry_scaled_tolerance": 1e-10, "linear_relative_residual": 0.001, "linear_backward_tolerance": 1e-12, "armijo_c1": 0.0001}, "preparation_authority": "r4 stopped locally before SSH because its operator-created duplicate receipt had an invalid leading plus sign; r5 static review then found retained self resource ceilings inconsistent with the later explicit authorization; r6 completed only read-only Taobo preflight and stopped before upload/deployment/five-file access/solver because GPU7 PID 651952 was not in its exact service allowlist. Those immutable records remain unchanged. This r7 package is a fresh technical-control revision under the same authorization: it retains the same five input identities and fixed FN776 numerical method while adding only the separately read-only-verified GPU7 service identity. It permits one scientific guard launch only.", "resource_evidence_boundary": "Three read-only GPU7 samples on 2026-10-25 verified PID 651952 at start_ticks 541746716, UID quartet [0,0,0,0], exact cmdline/cgroup digests, 5638 MiB and 0% GPU utilization with 16461 MiB free. This contract allowlists only that exact identity at <=6144 MiB alongside the two previously frozen services. Fresh three-sample admission remains mandatory; unknown, changed or over-limit identities stop, with no re-whitelist.", "control_plane": {"card_id": "S04-E011-UVH-C1-FN776-CARD-r7", "approval_index": "S04-E011-FN776-r7-A1", "readonly_preflight_seconds": 60, "resource_policy_changed": true, "science_source": "f1ed1ed969b10637fa774b3a0cc29aa24b2b7f92", "old_r1_partial_output": "unknown; not recoverable by this preparation", "ssh_prefix": ["ssh", "-T", "-v", "-o", "BatchMode=yes", "-o", "ConnectionAttempts=1", "-o", "ConnectTimeout=15", "-o", "ControlMaster=no", "-o", "ControlPath=none", "-o", "ControlPersist=no", "-o", "ClearAllForwardings=yes", "-o", "PermitLocalCommand=no", "gpu-taobo"], "transport_revision": "private_nonmultiplexed_SSH-v1", "connection_probe_receipt_sha256": "8a42be3171a220325ba87d6d508789ccc2dad12c2f7e5e0e1014a88e3507b74a", "technical_retry_policy": "Technical transport/deployment/retrieval retries require preserved prior evidence, fresh duplicate/resource admission and a new reviewed Run identity. No automatic reconnect. A launch with unknown remote state is observed read-only and never resent. There is one guard/numerical solve only. Any numerical, stationarity, Armijo, input-identity or scientific-contract issue requires human discussion.", "self_resource_limits": "none; transport timeouts apply only to an individual SSH/control observation, never to the detached solver"}, "execution_resource_policy": {"self_resource_ceiling": "none", "self_resource_enforcement": "none", "self_resource_telemetry": "elapsed time, RSS, CUDA reserved memory and output size are recorded only", "algorithmic_scope_is_not_a_resource_ceiling": true, "fixed_algorithmic_scope": "The 16 outer steps, 32 Armijo trials per step, 3 linear refinements and 25424 ledger units remain fixed scientific-method bounds."}}')


def emit(event, **fields):
    target = sys.stderr if len(sys.argv)>1 and sys.argv[1]=='archive' else sys.stdout
    print(json.dumps(dict(event=event, utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                          elapsed_seconds=time.monotonic()-START, **fields)), file=target, flush=True)


@contextlib.contextmanager
def stage(name):
    begin=time.monotonic();emit('stage_begin',stage=name)
    try:
        yield
    except BaseException as error:
        emit('stage_end',stage=name,status='failed',error=repr(error),seconds=time.monotonic()-begin)
        raise
    else:
        emit('stage_end',stage=name,status='completed',seconds=time.monotonic()-begin)


def command(args, timeout=10):
    emit('subcommand_begin',argv=args,timeout_seconds=timeout)
    try:
        r=subprocess.run(args,text=True,capture_output=True,timeout=timeout,check=False)
    except subprocess.TimeoutExpired as error:
        def text(v):
            return v.decode(errors='replace') if isinstance(v,bytes) else v
        emit('subcommand_end',argv=args,status='timeout',partial_stdout=text(error.stdout),partial_stderr=text(error.stderr))
        raise
    emit('subcommand_end',argv=args,status='completed' if r.returncode==0 else 'failed',
         exit_code=r.returncode,stdout=r.stdout,stderr=r.stderr)
    if r.returncode:
        raise RuntimeError('subcommand failed: '+repr(args))
    return r.stdout.strip()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def service_identity(expected):
    """Read only OS identity; never attach/request/stop the resident service."""
    base = Path('/proc') / str(expected['pid'])
    raw = (base / 'stat').read_text()
    fields = raw[raw.rfind(')') + 2:].split()
    uids = next(r for r in (base / 'status').read_text().splitlines() if r.startswith('Uid:'))
    return (int(fields[19]) == expected['start_ticks'] and
            [int(v) for v in uids.split()[1:]] == expected['uids'] and
            digest(base / 'cmdline') == expected['cmdline_sha256'] and
            digest(base / 'cgroup') == expected['cgroup_sha256'])

def gpu_snapshot(contract, worker_pid=None, mode=None):
    policy = contract['resource_policy']
    row = command(['nvidia-smi', '-i', str(policy['physical_GPU']),
                   '--query-gpu=uuid,memory.free,utilization.gpu', '--format=csv,noheader,nounits'], timeout=2)
    uuid, free, utilization = [x.strip() for x in row.split(',')]
    if uuid != policy['gpu_uuid']:
        raise RuntimeError('physical GPU index/UUID mapping changed')
    apps = command(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid,used_memory',
                    '--format=csv,noheader,nounits'], timeout=2)
    processes = {}
    for line in apps.splitlines():
        if not line.strip():
            continue
        app_uuid, pid, memory = [v.strip() for v in line.split(',')]
        if app_uuid == uuid:
            processes[int(pid)] = int(memory)
    others = set(processes) - ({worker_pid} if worker_pid is not None else set())
    allowed_services = {row['pid']: row for row in policy['services']}
    if not others:
        observed_mode = 'empty'
    elif others == set(allowed_services):
        for pid, expected in allowed_services.items():
            if not service_identity(expected):
                raise RuntimeError('GPU7 service identity changed; no re-whitelist')
            if processes[pid] > expected['maximum_MiB']:
                raise RuntimeError('GPU7 service memory exceeds frozen allowance')
        observed_mode = 'exact_services'
    else:
        raise RuntimeError('unknown or incomplete GPU7 service set; no whitelist or fallback')
    if observed_mode not in policy['admission_modes']:
        raise RuntimeError('unapproved resource admission mode')
    # Pin empty/exact-service-set mode; runtime permits only that set plus our worker.
    if mode is not None and observed_mode != mode:
        raise RuntimeError('GPU admission mode changed; stop owned child only')
    free, utilization = int(free), int(utilization)
    required = policy['minimum_initial_free_MiB'] if worker_pid is None else policy['minimum_runtime_free_MiB']
    if free < required:
        raise RuntimeError('insufficient shared GPU free-memory margin')
    if worker_pid is None and utilization > policy['maximum_admission_utilization_percent']:
        raise RuntimeError('GPU is active above admission limit')
    return dict(free_MiB=free, utilization_percent=utilization, processes_MiB=processes,
                admission_mode=observed_mode, elapsed_utc=dt.datetime.now(dt.timezone.utc).isoformat())


def duplicates():
    found=[]
    for row in command(['ps','-eo','pid,ppid,etimes,args']).splitlines()[1:]:
        fields=row.strip().split(None,3)
        if len(fields)!=4:continue
        pid,ppid,etimes,args=fields
        if not any(t in args for t in ('s04_e011_uv_head','s04_e011_pc16','s04_e011_fn776','same_energy_head','pidl_uv_head')):continue
        try:exe=Path(os.readlink('/proc/'+pid+'/exe')).name
        except FileNotFoundError:continue
        if exe.startswith('python') and int(pid)!=os.getpid():
            found.append(dict(pid=int(pid),ppid=int(ppid),etimes=int(etimes),args=args,cwd=os.readlink('/proc/'+pid+'/cwd')))
    emit('duplicate_workers',workers=found)
    assert not found,'possible duplicate worker'


def preflight():
    with stage('host_identity'):
        assert socket.gethostname()=='GPUServer8';emit('host',hostname=socket.gethostname())
    with stage('fresh_paths'):
        for path in (ROOT,OUT):
            present=path.exists() or path.is_symlink();emit('path',path=str(path),present=present)
            assert not present,'path collision'
    with stage('duplicate_workers'):duplicates()
    mode=None;samples=[]
    for i in range(3):
        with stage('GPU7_sample_'+str(i+1)):
            sample=gpu_snapshot(CONTRACT,mode=mode)
            if mode is None:mode=sample['admission_mode']
            samples.append(sample);emit('gpu_observation',sample=sample)
        if i<2:time.sleep(1)
    with stage('host_memory_mount_disk'):
        mem=dict((r.split(':')[0],int(r.split()[1])) for r in Path('/proc/meminfo').read_text().splitlines())
        assert mem['MemAvailable']>=CONTRACT['resource_policy']['minimum_host_available_kB'];assert Path('/mnt/data2').is_mount()
        v=os.statvfs('/mnt/data2');assert v.f_bavail*v.f_frsize>=CONTRACT['resource_policy']['minimum_data2_free_bytes']
        emit('host_capacity',MemAvailable_kB=mem['MemAvailable'],data2_free_bytes=v.f_bavail*v.f_frsize)
        command(['df','-h','/','/mnt/data2','/mnt/data3'])
    with stage('previous_terminal'):
        old=json.loads(Path('/mnt/data2/drtao/pidl_archives/pf_s04e011_uvh_c1_pc16_g7_r1_20261018/guard_receipt.json').read_text())
        assert old['status']=='completed' and old['exit_code']==0
        emit('prior_receipt',status=old['status'],exit_code=old['exit_code'])
    return dict(status='PREDEPLOY_ADMISSION_PASS',samples=samples)


def deploy(expected,ref,sha,byte_count):
    with stage('bundle_identity'):
        assert (ROOT/'source.bundle').stat().st_size==int(byte_count)
        assert digest(ROOT/'source.bundle')==sha
        assert not CODE.exists();assert not OUT.exists()
    with stage('empty_materialization'):
        command(['git','init',str(CODE)])
        command(['git','-C',str(CODE),'fetch',str(ROOT/'source.bundle'),ref],timeout=30)
        command(['git','-C',str(CODE),'checkout','--detach',expected])
        result=command(['/usr/bin/python3','-B',str(CODE/'tools/s04_e011_fn776/verify_code_package.py'),'--code',str(CODE),'--expected-source',expected],timeout=30)
        (ROOT/'materialization_receipt.json').write_text(result+'\n')
    return dict(status='DEPLOYMENT_PASS',source=expected)


def launch(expected):
    with stage('immediate_duplicate_workers'):duplicates()
    with stage('one_launch'):
        assert not (ROOT/'attempt_claim.json').exists() and not (ROOT/'launch_receipt.json').exists()
        assert command(['git','-C',str(CODE),'rev-parse','HEAD'])==expected
        assert not command(['git','-C',str(CODE),'status','--porcelain','--untracked-files=all'])
        env=dict(os.environ,CUDA_VISIBLE_DEVICES=CONTRACT['resource_policy']['gpu_uuid'],PYTHONOPTIMIZE='0',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
        argv=['/usr/bin/python3','-B','tools/s04_e011_fn776/guard.py','--execute-approved','--approval-ref',CARD,'--expected-source',expected]
        with (ROOT/'guard.log').open('xb') as log:
            child=subprocess.Popen(argv,cwd=CODE,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        receipt=dict(status='LAUNCH_SUBMITTED',run_id=RUN,source=expected,guard_pid=child.pid,argv=argv,utc=dt.datetime.now(dt.timezone.utc).isoformat())
        try:
            raw=Path('/proc/'+str(child.pid)+'/stat').read_text()
            receipt['guard_start_ticks']=int(raw[raw.rfind(')')+2:].split()[19])
        except FileNotFoundError:
            receipt.update(guard_start_ticks=None,already_exited_at_launch_receipt=True,exit_code=child.poll())
        (ROOT/'launch_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def monitor():
    receipt_path=OUT/'guard_receipt.json'
    launch_receipt=json.loads((ROOT/'launch_receipt.json').read_text())
    guard=json.loads(receipt_path.read_text()) if receipt_path.exists() else None
    terminal_record=(guard is not None and guard.get('status') in ('completed','stopped_or_failed')) or (ROOT/'operator_terminal.json').exists()
    try:
        raw=Path('/proc/'+str(launch_receipt['guard_pid'])+'/stat').read_text()
        fields=raw[raw.rfind(')')+2:].split()
        start_ticks=int(fields[19]);expected=launch_receipt.get('guard_start_ticks')
        live=(expected is None or start_ticks==expected) and fields[0]!='Z'
        process=dict(live=live,state=fields[0],start_ticks=start_ticks,expected_start_ticks=expected)
    except FileNotFoundError:
        process=dict(live=False,missing=True)
    # guard_receipt precedes final root/operator_terminal writes on failure.
    # Do not freeze the report until that exact guard identity has exited.
    worker=dict(live=False,spawn_requested=bool(guard and guard.get('worker_spawn_requested')))
    if guard and guard.get('worker_pid'):
        try:
            raw=Path('/proc/'+str(guard['worker_pid'])+'/stat').read_text()
            fields=raw[raw.rfind(')')+2:].split();ticks=int(fields[19])
            expected=guard.get('worker_start_ticks')
            worker.update(live=(expected is None or ticks==expected) and fields[0]!='Z',
                          state=fields[0],start_ticks=ticks,expected_start_ticks=expected)
        except FileNotFoundError:
            worker.update(live=False,missing=True)
    elif worker['spawn_requested']:
        worker.update(live=True,identity_unknown=True)
    terminal=bool(terminal_record and not process['live'] and not worker['live'])
    emit('owned_process_observation',guard=process,worker=worker,terminal_record_present=terminal_record)
    # Retain full guard resource history only in the one final report copy;
    # repeated observation returns selected identity/terminal scalars.
    keys=('status','exit_code','stop_reason','guard_pid','worker_pid','elapsed_seconds',
          'sampled_peak_RSS','sampled_output_bytes','source','finish_utc')
    summary={key:guard[key] for key in keys if key in guard} if guard is not None else None
    return dict(status='MONITOR_OK',terminal=terminal,launch=launch_receipt,guard=summary,guard_process=process,worker_process=worker,
                guard_receipt_path=str(receipt_path),operator_terminal=json.loads((ROOT/'operator_terminal.json').read_text()) if (ROOT/'operator_terminal.json').exists() else None)


def artifacts():
    # Explicit report allowlist. This defines retrieval scope, not a producer-output quota;
    # caches and temporary compiler/runtime files are deliberately never copied.
    root_names=('source.bundle','materialization_receipt.json','attempt_claim.json','launch_receipt.json','operator_terminal.json','guard.log')
    output_names=('guard_receipt.json','worker_receipt.json','worker.log','work_ledger.jsonl','trace.jsonl','trace.json','accepted.json','optimizer_terminal.json','curvature_controls.jsonl','trials.jsonl','summary.json','basis.json','head.npz','fields.npz','decision.png','decision.md','initial_factor.npz','latest_factor.npz')
    result=[]
    for name in root_names:
        path=ROOT/name
        if path.exists():
            assert path.is_file() and not path.is_symlink();result.append((path,'root/'+name))
    for name in output_names:
        path=OUT/name
        if path.exists():
            assert path.is_file() and not path.is_symlink();result.append((path,'output/'+name))
    return result


def main():
    role=sys.argv[1];emit('remote_script_begin',role=role,run_id=RUN)
    if role=='preflight':return preflight()
    if role=='deploy':return deploy(*sys.argv[2:])
    if role=='launch':return launch(sys.argv[2])
    if role=='monitor':return monitor()
    if role in ('manifest','archive'):
        terminal=monitor();assert terminal['terminal'],'producer not terminal; do not collect live files'
        items=artifacts()
        if role=='manifest':return dict(status='MANIFEST_OK',files=[dict(path=name,bytes=p.stat().st_size,sha256=digest(p)) for p,name in items])
        with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as tar:
            for path,name in items:tar.add(path,arcname=name,recursive=False)
        return None
    raise RuntimeError('unknown fixed role')


if __name__=='__main__':
    START=time.monotonic()
    try:
        result=main()
        if result is not None:print(json.dumps(result),flush=True)
    except BaseException as error:
        emit('remote_terminal_failure',error=repr(error),retry_allowed=False)
        raise
