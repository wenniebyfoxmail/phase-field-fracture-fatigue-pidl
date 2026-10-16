"""Single generated engineering invocation; 60 s / 512 MiB / 5 MiB.

No real-data mode or command override. Caps are sampled, not OS hard limits.
Fresh directory is the attempt marker and remains on any failure; never retry.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[1]
ENGINEERING = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021/engineering')
WALL, RSS, BYTES = 60., 512*1024**2, 5*1024**2
RESERVE = 16384


def cap_reason(elapsed, rss, size):
    if elapsed >= WALL:
        return 'WALL_CAP'
    if rss >= RSS:
        return 'RSS_CAP'
    if size+RESERVE >= BYTES:
        return 'OUTPUT_CAP'
    return None


def output_size(out):
    return sum(p.stat().st_size for p in out.rglob('*') if p.is_file())


def execute(out):
    out = Path(out).absolute()
    if out.parent != ENGINEERING or out.resolve() != out or out.name != 'late-attribution-20261016-9984226':
        raise ValueError('only fixed generated-engineering destination is enabled')
    if out.exists():
        raise FileExistsError('single attempt consumed; no retry or overwrite')
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    child = None
    peak = 0
    reason = None
    command = [sys.executable, str(Path(__file__).with_name('s04_late_attribution_checks.py')),
               '--out', str(out)]
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1',
               MPLCONFIGDIR=str(out/'mplcache'), PYTHONDONTWRITEBYTECODE='1')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain', '--',
                                    'SENS_tensile/s04_late_attribution*.py'], cwd=ROOT, text=True)

    def measure():
        nonlocal peak
        rss = psutil.Process(os.getpid()).memory_info().rss
        if child is not None:
            try:
                proc = psutil.Process(child.pid)
                for p in [proc, *proc.children(recursive=True)]:
                    try:
                        rss += p.memory_info().rss
                    except psutil.NoSuchProcess:
                        pass
            except psutil.NoSuchProcess:
                if child.poll() is None:
                    raise RuntimeError('lost child visibility')
        peak = max(peak, rss)
        return cap_reason(time.monotonic()-started, peak, output_size(out))

    with (out/'engineering.log').open('x') as log:
        try:
            reason = measure()
            if reason is None:
                child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                         stderr=log, start_new_session=True)
                while child.poll() is None:
                    reason = measure()
                    if reason:
                        break
                    time.sleep(.02)
                reason = reason or measure() or ('CHILD_FAILED' if child.returncode else None)
                if reason is None and not (out/'checks.json').is_file():
                    reason = 'INCOMPLETE_OUTPUT'
        except BaseException as exc:
            reason = 'GUARD_EXCEPTION_'+type(exc).__name__
            print(repr(exc), file=log, flush=True)
        finally:
            if child is not None and child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=.5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait(timeout=.5)
    record = dict(status=reason or 'COMPLETED', scope='GENERATED_ENGINEERING_ONLY',
                  start_utc=utc, elapsed_seconds=time.monotonic()-started,
                  aggregate_sampled_peak_rss_bytes=peak,
                  output_bytes_before_receipt=output_size(out), output=str(out),
                  caps=dict(seconds=WALL, rss_bytes=RSS, output_bytes=BYTES),
                  code_commit=commit, dirty_source_status=dirty, command=command,
                  host=socket.gethostname(), guard_pid=os.getpid(),
                  worker_pid=None if child is None else child.pid,
                  worker_exit=None if child is None else child.poll(), gpu=None,
                  real_data_read=False, fitting_invoked=False, retry=False)
    with (out/'guard_receipt.json').open('x') as file:
        json.dump(record, file, indent=2, allow_nan=False)
    final_bytes = output_size(out)
    if final_bytes >= BYTES or time.monotonic()-started >= WALL:
        record['status'] = 'FINAL_OUTPUT_OR_WALL_CAP'
        with (out/'guard_receipt.json').open('w') as file:
            json.dump(record, file, indent=2, allow_nan=False)
    print(json.dumps(dict(record, final_output_bytes=output_size(out)), indent=2))
    return int(record['status'] != 'COMPLETED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(execute(args.out))
