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

RUN = 'pf_s04e011_uvh_c1_r1_20261018'
CARD = 'S04-E011-UVH-C1-CARD-r1'
ROOT = Path('/mnt/data2/drtao/wennie') / RUN
OUT = Path('/mnt/data2/drtao/pidl_archives') / RUN
CODE = ROOT / 'code'
CONTRACT = CODE / 'docs/research/S04/S04-E011/uv_head_c1_20261018/inputs.json'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def command(args):
    return subprocess.check_output(args, text=True, timeout=10).strip()


def run_worker():
    # Internal child: guard has already consumed the single attempt.
    contract = json.loads(CONTRACT.read_text())
    receipt = dict(protocol=contract['protocol'], run_id=RUN,
                   start_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                   pid=os.getpid(), host=os.uname().nodename,
                   approval_ref=os.environ['UVH_APPROVAL_REF'],
                   code_commit=os.environ['UVH_CODE_COMMIT'], inputs=[])
    save(OUT / 'worker_receipt.json', receipt)
    # Only four exact files; no discovery, copying, MAT or archive-wide read.
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
    result = run(contract, OUT, float(os.environ['UVH_START']))
    receipt.update(status='completed', evaluations=result['evaluations'],
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
    if not args.expected_source or len(args.expected_source) != 40:
        raise SystemExit('exact reviewed source commit required')
    if sys.platform != 'linux' or Path(__file__).resolve().parents[2] != CODE:
        raise SystemExit('fixed Taobo code directory only; Mac execution denied')
    with (ROOT / 'attempt_claim.json').open('x') as claim:
        json.dump(dict(guard_pid=os.getpid(), source=args.expected_source,
                       approval_ref=args.approval_ref,
                       utc=dt.datetime.now(dt.timezone.utc).isoformat()), claim)
    # An approved invocation consumes the card even if any later preflight fails.
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '0':
        raise SystemExit('only approved physical GPU0, no fallback')
    if command(['git', '-C', str(CODE), 'rev-parse', 'HEAD']) != args.expected_source:
        raise SystemExit('source identity mismatch')
    if command(['git', '-C', str(CODE), 'status', '--porcelain', '--untracked-files=all']):
        raise SystemExit('producer code checkout not clean')
    # Binding is reviewed Git content; no alternate contract/path/budget flags.
    contract = json.loads(CONTRACT.read_text())
    if contract['protocol'] != 'S04-E011-UVH-C1-r1' or contract['run_id'] != RUN:
        raise SystemExit('contract identity mismatch')
    if OUT.exists() or OUT.is_symlink():
        raise SystemExit('attempt already consumed; no resume/retry')
    processes = command(['ps', '-eo', 'pid,args'])
    for row in processes.splitlines()[1:]:
        pid, _, arguments = row.strip().partition(' ')
        if int(pid) != os.getpid() and 'python' in arguments and any(
                token in arguments for token in ('s04_e011_uv_head', 'same_energy_head', 'pidl_uv_head')):
            raise SystemExit('possible same-item producer process; resolve ownership before launch')
    # Read-only shared-resource checks precede scientific input access.
    gpu = command(['nvidia-smi', '--query-gpu=index,memory.free', '--format=csv,noheader,nounits'])
    free0 = {int(v.split(',')[0]): int(v.split(',')[1]) for v in gpu.splitlines()}
    if free0.get(0, 0) < 16384:
        raise SystemExit('GPU0 has less than16GiB free; stop without fallback')
    apps = command(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader'])
    uuid0 = command(['nvidia-smi', '-i', '0', '--query-gpu=uuid', '--format=csv,noheader'])
    if uuid0 in apps:
        raise SystemExit('GPU0 has an existing compute process; stop')
    mem = dict((r.split(':')[0], int(r.split()[1])) for r in Path('/proc/meminfo').read_text().splitlines())
    if mem['MemAvailable'] < 16 * 1024 * 1024:
        raise SystemExit('less than16GiB host RAM available')
    if not Path('/mnt/data2').is_mount():
        raise SystemExit('canonical data2 mount unavailable')
    stat = os.statvfs('/mnt/data2')
    if stat.f_bavail * stat.f_frsize < 5 * 1024**3:
        raise SystemExit('less than5GiB data2 space')
    OUT.mkdir()  # Atomic one-shot claim. No scientific access before this point.
    for name in ('tmp', 'cache'):
        (OUT / name).mkdir()
    env = os.environ.copy()
    env.update(UVH_CHILD=CARD, UVH_APPROVAL_REF=args.approval_ref,
               UVH_CODE_COMMIT=args.expected_source,
               TMPDIR=str(OUT / 'tmp'), XDG_CACHE_HOME=str(OUT / 'cache'),
               MPLCONFIGDIR=str(OUT / 'cache'), PYTHONDONTWRITEBYTECODE='1',
               OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               NUMEXPR_NUM_THREADS='1', CUBLAS_WORKSPACE_CONFIG=':4096:8')
    env['UVH_START'] = str(start)
    record = dict(run_id=RUN, status='started', source=args.expected_source,
                  approval_ref=args.approval_ref, start_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                  guard_pid=os.getpid(), host=os.uname().nodename, GPU=0,
                  output=str(OUT), code=str(CODE), budget=contract['budget'])
    save(OUT / 'guard_receipt.json', record)
    reason = None
    peak = 0
    def interrupt(signum, frame):
        raise KeyboardInterrupt('guard received signal ' + str(signum))
    signal.signal(signal.SIGTERM, interrupt)
    # Includes all payload, stdout/stderr, cache/tmp, receipt and plot bytes.
    with (OUT / 'worker.log').open('xb') as log:
        child = subprocess.Popen([sys.executable, '-B', str(Path(__file__).resolve()), '--worker'],
                                 cwd=CODE, env=env, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        record['worker_pid'] = child.pid
        save(OUT / 'guard_receipt.json', record)
        try:
            while child.poll() is None:
                rss = process_tree(child.pid)
                peak = max(peak, rss)
                usage = output_bytes()
                if time.monotonic() - start >= contract['budget']['wall_seconds'] - 5:
                    reason = 'wall_limit'
                elif rss > contract['budget']['rss_bytes']:
                    reason = 'sampled_RSS_limit'
                elif usage > contract['budget']['output_bytes'] - 65536:
                    reason = 'output_limit'
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
                          exit_code=child.returncode, first_limit=reason, sampled_peak_RSS=peak,
                          elapsed_seconds=time.monotonic() - start,
                          sampled_output_bytes=output_bytes(),
                          finish_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                          sampling_note='100ms sampled RSS/output, not OS hard peaks; guard cleanup reserve5s')
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
