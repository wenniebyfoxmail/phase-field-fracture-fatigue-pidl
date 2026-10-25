"""Fail-closed, one-shot prospective producer launcher. Import is inert."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

RUN = 'pf_s04e011_uvh_c1_fn776_r7_20261025'
CARD = 'S04-E011-UVH-C1-FN776-CARD-r7'
ROOT = Path('/mnt/data2/drtao/wennie') / RUN
OUT = Path('/mnt/data2/drtao/pidl_archives') / RUN
CODE = ROOT / 'code'
CONTRACT = CODE / 'docs/research/S04/S04-E011/uv_head_c1_solver_d3_20261019/inputs_fn776_r7.json'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def command(args, timeout=10):
    return subprocess.check_output(args, text=True, timeout=timeout).strip()


def run_worker():
    # Internal child: guard has already consumed the single attempt.
    contract = json.loads(CONTRACT.read_text())
    receipt = dict(protocol=contract['protocol'], run_id=RUN,
                   start_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                   pid=os.getpid(), host=os.uname().nodename,
                   approval_ref=os.environ['UVH_APPROVAL_REF'],
                   code_commit=os.environ['UVH_CODE_COMMIT'], inputs=[])
    save(OUT / 'worker_receipt.json', receipt)
    # Only five exact files; no discovery, copying, MAT or archive-wide read.
    for row in contract['files']:
        p = Path(row['path'])
        if not p.is_file() or p.is_symlink() or p.stat().st_size != row['bytes']:
            raise RuntimeError('input path/size mismatch: ' + row['role'])
        actual = digest(p)
        if actual != row['sha256']:
            raise RuntimeError('input identity mismatch: ' + row['role'])
        receipt['inputs'].append(dict(role=row['role'], path=str(p), sha256=actual,
                                      whole_file_hash=True, bytes=row['bytes']))
        save(OUT / 'worker_receipt.json', receipt)
    from worker import run
    try:
        result = run(contract, OUT, float(os.environ['UVH_START']))
    except BaseException as error:
        receipt.update(status='failed_terminal', error=repr(error), retry_allowed=False,
                       finish_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        save(OUT / 'worker_receipt.json', receipt)
        raise
    receipt.update(status='completed', work_units=result['work_ledger']['used'],
                   finish_utc=dt.datetime.now(dt.timezone.utc).isoformat())
    save(OUT / 'worker_receipt.json', receipt)


def process_tree(pid):
    """Linux /proc sampled aggregate RSS for this child and descendants only."""
    rows = {}
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            raw = path.read_text()
            fields = raw[raw.rfind(')') + 2:].split()
            rows[int(path.parent.name)] = (int(fields[1]), int(fields[21]))
        except (OSError, ValueError, IndexError):
            continue
    ids = {pid}
    while True:
        new = {i for i, (parent, _) in rows.items() if parent in ids}
        if new <= ids:
            break
        ids |= new
    return sum(rows[i][1] for i in ids if i in rows) * os.sysconf('SC_PAGE_SIZE')


def size_tree(path):
    return sum(p.lstat().st_size for p in path.rglob('*') if p.is_file())


def output_bytes():
    return size_tree(OUT) + sum(p.stat().st_size for p in ROOT.iterdir() if p.is_file())


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


def main():
    start = time.monotonic()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-approved', action='store_true')
    p.add_argument('--approval-ref')
    p.add_argument('--expected-source')
    p.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = p.parse_args()
    if args.worker:
        if os.environ.get('UVH_CHILD') != CARD:
            raise SystemExit('internal child invocation denied')
        return run_worker()
    if not args.execute_approved or args.approval_ref != CARD:
        raise SystemExit('No execution: exact human-approved run card required')
    if sys.flags.optimize:
        raise SystemExit('Python optimization must be disabled; assertions are validity checks')
    if not args.expected_source or len(args.expected_source) != 40:
        raise SystemExit('exact reviewed source commit required')
    if sys.platform != 'linux' or Path(__file__).resolve().parents[2] != CODE:
        raise SystemExit('fixed Taobo code directory only; Mac execution denied')
    with (ROOT / 'attempt_claim.json').open('x') as claim:
        json.dump(dict(guard_pid=os.getpid(), source=args.expected_source,
                       approval_ref=args.approval_ref,
                       utc=dt.datetime.now(dt.timezone.utc).isoformat()), claim)
    # An approved invocation consumes the card even if any later preflight fails.
    if os.environ.get('CUDA_VISIBLE_DEVICES') != 'GPU-350d3f31-8bd6-4257-4d4c-21ad344eaa81':
        raise SystemExit('only approved physical GPU7 UUID, no ordinal fallback')
    if command(['git', '-C', str(CODE), 'rev-parse', 'HEAD']) != args.expected_source:
        raise SystemExit('source identity mismatch')
    if command(['git', '-C', str(CODE), 'status', '--porcelain', '--untracked-files=all']):
        raise SystemExit('producer code checkout not clean')
    command([sys.executable, '-B', str(CODE / 'tools/s04_e011_fn776/verify_code_package.py'),
             '--code', str(CODE), '--expected-source', args.expected_source], timeout=30)
    # Binding is reviewed Git content; no alternate contract/path flags.
    contract = json.loads(CONTRACT.read_text())
    if (contract['protocol'] != 'S04-E011-UVH-C1-FN776-v1' or contract['run_id'] != RUN or
            contract['resource_revision'] != 'GPU7-FN776-shared-r2-uvicorn28011'):
        raise SystemExit('contract identity mismatch')
    if OUT.exists() or OUT.is_symlink():
        raise SystemExit('attempt already consumed; no resume/retry')
    processes = command(['ps', '-eo', 'pid,args'])
    for row in processes.splitlines()[1:]:
        pid, _, arguments = row.strip().partition(' ')
        if int(pid) == os.getpid() or not any(token in arguments for token in
                ('s04_e011_uv_head', 's04_e011_pc16', 's04_e011_fn776', 'same_energy_head', 'pidl_uv_head')):
            continue
        try:
            executable = Path(os.readlink('/proc/' + pid + '/exe')).name
        except FileNotFoundError:
            continue  # Process exited between ps and executable inspection.
        except PermissionError:
            raise SystemExit('possible duplicate process identity unreadable; stop')
        # A launching shell can contain our whole command in argv; only an actual
        # Python executable is a competing worker, never bash/sshd by substring.
        if executable.startswith('python'):
            raise SystemExit('possible same-item producer process; resolve ownership before launch')
    # Read-only shared-resource checks precede scientific input access.
    admission = []
    admission_mode = None
    for i in range(contract['resource_policy']['admission_samples']):
        snapshot = gpu_snapshot(contract, mode=admission_mode)
        if admission_mode is None:
            admission_mode = snapshot['admission_mode']
        admission.append(snapshot)
        if i + 1 < contract['resource_policy']['admission_samples']:
            time.sleep(contract['resource_policy']['admission_interval_seconds'])
    mem = dict((r.split(':')[0], int(r.split()[1])) for r in Path('/proc/meminfo').read_text().splitlines())
    if mem['MemAvailable'] < contract['resource_policy']['minimum_host_available_kB']:
        raise SystemExit('host RAM safety margin unavailable')
    if not Path('/mnt/data2').is_mount():
        raise SystemExit('canonical data2 mount unavailable')
    stat = os.statvfs('/mnt/data2')
    if stat.f_bavail * stat.f_frsize < contract['resource_policy']['minimum_data2_free_bytes']:
        raise SystemExit('data2 shared-disk safety margin unavailable')
    OUT.mkdir()  # Atomic one-shot claim. No scientific access before this point.
    for name in ('tmp', 'cache'):
        (OUT / name).mkdir()
    env = os.environ.copy()
    env.update(UVH_CHILD=CARD, UVH_APPROVAL_REF=args.approval_ref,
               UVH_CODE_COMMIT=args.expected_source,
               TMPDIR=str(OUT / 'tmp'), XDG_CACHE_HOME=str(OUT / 'cache'),
               MPLCONFIGDIR=str(OUT / 'cache'), PYTHONDONTWRITEBYTECODE='1',
               TORCH_EXTENSIONS_DIR=str(OUT / 'cache' / 'torch_extensions'),
               CUDA_CACHE_PATH=str(OUT / 'cache' / 'cuda'),
               PYTORCH_KERNEL_CACHE_PATH=str(OUT / 'cache' / 'torch_kernels'),
               OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               NUMEXPR_NUM_THREADS='1', CUBLAS_WORKSPACE_CONFIG=':4096:8')
    env['UVH_START'] = str(start)
    record = dict(run_id=RUN, status='started', source=args.expected_source,
                  approval_ref=args.approval_ref, start_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  guard_pid=os.getpid(), host=os.uname().nodename, GPU=7,
                  output=str(OUT), code=str(CODE), execution_resource_policy=contract['execution_resource_policy'],
                  resource_policy=contract['resource_policy'], admission_mode=admission_mode, admission=admission)
    save(OUT / 'guard_receipt.json', record)
    reason = None
    peak = 0
    gpu_monitor = dict(samples=0, minimum_free_MiB=None, maximum_utilization_percent=None, last=None)
    host_monitor = dict(samples=0, minimum_available_kB=None, minimum_data2_free_bytes=None, last=None)
    next_safety_check = 0.
    def interrupt(signum, frame):
        raise KeyboardInterrupt('guard received signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupt)
    # Output, RSS and CUDA use are retained only as final telemetry; no self quota is enforced.
    with (OUT / 'worker.log').open('xb') as log:
        record['worker_spawn_requested'] = True
        save(OUT / 'guard_receipt.json', record)
        child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--worker'],
                                 cwd=CODE, env=env, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        try:
            record['worker_pid'] = child.pid
            try:
                raw = Path('/proc/' + str(child.pid) + '/stat').read_text()
                record['worker_start_ticks'] = int(raw[raw.rfind(')') + 2:].split()[19])
            except FileNotFoundError:
                record['worker_start_ticks'] = None
            save(OUT / 'guard_receipt.json', record)
            while child.poll() is None:
                rss = process_tree(child.pid)
                peak = max(peak, rss)
                if time.monotonic() >= next_safety_check:
                    try:
                        snapshot = gpu_snapshot(contract, child.pid, mode=admission_mode)
                        gpu_monitor['samples'] += 1
                        gpu_monitor['minimum_free_MiB'] = snapshot['free_MiB'] if gpu_monitor['minimum_free_MiB'] is None else min(gpu_monitor['minimum_free_MiB'], snapshot['free_MiB'])
                        gpu_monitor['maximum_utilization_percent'] = snapshot['utilization_percent'] if gpu_monitor['maximum_utilization_percent'] is None else max(gpu_monitor['maximum_utilization_percent'], snapshot['utilization_percent'])
                        gpu_monitor['last'] = snapshot
                        mem = dict((r.split(':')[0], int(r.split()[1])) for r in Path('/proc/meminfo').read_text().splitlines())
                        if not Path('/mnt/data2').is_mount():
                            raise RuntimeError('canonical data2 mount unavailable')
                        stat = os.statvfs('/mnt/data2')
                        free_bytes = stat.f_bavail * stat.f_frsize
                        host_monitor['samples'] += 1
                        host_monitor['minimum_available_kB'] = mem['MemAvailable'] if host_monitor['minimum_available_kB'] is None else min(host_monitor['minimum_available_kB'], mem['MemAvailable'])
                        host_monitor['minimum_data2_free_bytes'] = free_bytes if host_monitor['minimum_data2_free_bytes'] is None else min(host_monitor['minimum_data2_free_bytes'], free_bytes)
                        host_monitor['last'] = dict(MemAvailable_kB=mem['MemAvailable'], data2_free_bytes=free_bytes)
                        if mem['MemAvailable'] < contract['resource_policy']['minimum_host_available_kB']:
                            raise RuntimeError('host RAM safety margin unavailable')
                        if free_bytes < contract['resource_policy']['minimum_data2_free_bytes']:
                            raise RuntimeError('data2 shared-disk safety margin unavailable')
                    except Exception as error:
                        reason = 'shared_machine_safety_monitor: ' + repr(error)
                    next_safety_check = time.monotonic() + contract['resource_policy']['runtime_monitor_interval_seconds']
                if reason:
                    break
                time.sleep(.1)
        except BaseException:
            reason = 'guard_interrupted'
            raise
        finally:
            if reason and child.poll() is None:
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    child.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=2)
            child.wait()
            record.update(status='completed' if child.returncode == 0 and not reason else 'stopped_or_failed',
                          exit_code=child.returncode, stop_reason=reason, sampled_peak_RSS=peak,
                          gpu_monitor=gpu_monitor, host_monitor=host_monitor,
                          elapsed_seconds=time.monotonic() - start,
                          sampled_output_bytes=output_bytes(),
                          finish_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                          sampling_note='RSS/CUDA/output are telemetry only. Runtime checks enforce only GPU/service identity, GPU free margin and shared host/disk safety; two NVML commands use a 2s query timeout.')
            save(OUT / 'guard_receipt.json', record)
    if child.returncode or reason:
        raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        claim = ROOT / 'attempt_claim.json'
        if sys.platform == 'linux' and claim.is_file():
            owner = json.loads(claim.read_text())
            if owner.get('guard_pid') == os.getpid():
                save(ROOT / 'operator_terminal.json', dict(error=repr(error),
                     retry_allowed=False, utc=dt.datetime.now(dt.timezone.utc).isoformat()))
        raise
