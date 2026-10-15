"""Inference-only guard. No old fit guard, synthetic execution mode or retry."""
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
BASE = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021')
REFERENCE_COMMIT = '6aa21e3c469d53c92240c9689d07a3ffb316d67c'
LOCK_SHA = 'cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c'
SOURCES = ['SENS_tensile/'+n for n in ('s04_raw_replay.py', 's04_raw_replay_guard.py',
           's04_raw_replay_checks.py', 's04_d0.py', 's04_g5_features.py')]


def authorize(path, out):
    # An interlock only; human consent must independently match this exact run.
    if path is None:
        raise ValueError('separate reviewed replay execution approval required')
    a = json.loads(Path(path).read_text())
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    expected = dict(action='frozen_inference_replay_only', user_approved_replay=True,
                    independent_code_review='APPROVED', code_commit=commit,
                    reference_commit=REFERENCE_COMMIT, lock_sha256=LOCK_SHA,
                    plan_commit='bcb58a6', run_id='S04-E021-REPLAY-R001', output=str(out))
    if any(a.get(k) != v for k, v in expected.items()):
        raise ValueError('replay authorization mismatch')
    if out != BASE/'replay_runs/S04-E021-REPLAY-R001':
        raise ValueError('fresh dedicated replay destination required')
    subprocess.check_call(['git', 'ls-files', '--error-unmatch', *SOURCES], cwd=ROOT,
                          stdout=subprocess.DEVNULL)
    if subprocess.check_output(['git', 'status', '--porcelain', '--', *SOURCES], cwd=ROOT, text=True):
        raise ValueError('reviewed replay sources must be clean')
    plan = 'docs/research/S04/S04-E021/next_validation_plan_v1.md'
    if subprocess.check_output(['git', 'diff', 'bcb58a6', '--', plan], cwd=ROOT, text=True):
        raise ValueError('reviewed replay plan changed')
    dependencies = ['SENS_tensile/s04_d0.py', 'SENS_tensile/s04_g5_features.py',
                    'docs/research/S04/S04-E016/paired_s4_lock_candidate_20261013.json']
    if subprocess.check_output(['git', 'diff', REFERENCE_COMMIT, '--', *dependencies], cwd=ROOT, text=True):
        raise ValueError('frozen input/feature dependencies changed')
    return a


def execute(out, auth_path):
    out = Path(out).resolve()
    auth_path = Path(auth_path).resolve() if auth_path is not None else None
    a = authorize(auth_path, out)  # Before output/reference/source access.
    log_path = out.parent/(out.name+'_guard.log')
    receipt_path = out.parent/(out.name+'_guard_receipt.json')
    if out.exists() or log_path.exists() or receipt_path.exists():
        raise FileExistsError('single fresh attempt only; no retry')
    out.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic(); child = None; peak = 0; reason = None
    utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    env = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4',
               VECLIB_MAXIMUM_THREADS='4', CUDA_VISIBLE_DEVICES='', PYTHONUNBUFFERED='1',
               RAW_REPLAY_COMMIT=a['code_commit'], RAW_REPLAY_ID=a['run_id'],
               RAW_REPLAY_START=str(start), RAW_REPLAY_PARENT=str(os.getpid()))
    command = [sys.executable, str(Path(__file__).with_name('s04_raw_replay.py')),
               '--out', str(out), '--authorization', str(auth_path)]

    def size():
        payload = sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) if out.exists() else 0
        return payload+sum(p.stat().st_size for p in (log_path, receipt_path) if p.exists())

    def caps():
        nonlocal peak
        rss = psutil.Process(os.getpid()).memory_info().rss
        if child is not None and child.poll() is None:
            try:
                proc = psutil.Process(child.pid)
                rss += proc.memory_info().rss
                for p in proc.children(recursive=True):
                    try: rss += p.memory_info().rss
                    except psutil.NoSuchProcess: pass
            except psutil.NoSuchProcess:
                if child.poll() is None: raise RuntimeError('lost child visibility')
        peak = max(peak, rss)
        if time.monotonic()-start >= 300: return 'WALL_CAP'
        if peak > 2*1024**3: return 'RSS_CAP'
        if size()+32768 > 100*1024**2: return 'OUTPUT_CAP'
        return None

    with log_path.open('x') as log:
        try:
            reason = caps()
            if not reason:
                child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                         stderr=log, start_new_session=True)
                while child.poll() is None:
                    reason = caps()
                    if reason: break
                    time.sleep(.1)
                reason = reason or caps() or ('CHILD_FAILED' if child.returncode else None)
        except BaseException as e:
            reason = 'GUARD_EXCEPTION_'+type(e).__name__; print(repr(e), file=log, flush=True)
        finally:
            if child is not None and child.poll() is None:
                try: os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                try: child.wait(timeout=.5)
                except subprocess.TimeoutExpired:
                    try: os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    child.wait()
    record = dict(status=reason or 'COMPLETED', action='frozen_inference_replay_only',
                  run_id=a['run_id'], code_commit=a['code_commit'], start_utc=utc,
                  elapsed_seconds=time.monotonic()-start, peak_rss_bytes=peak,
                  output_bytes_before_receipt=size(), producer=socket.gethostname(),
                  guard_pid=os.getpid(), worker_pid=None if child is None else child.pid,
                  worker_exit=None if child is None else child.poll(), command=command,
                  output=str(out), cpu_threads=4, gpu=None, fitting_invoked=False)
    receipt_path.write_text(json.dumps(record, indent=2)); print(json.dumps(record, indent=2))
    return 0 if record['status'] == 'COMPLETED' else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--authorization', type=Path, required=True); args = p.parse_args()
    raise SystemExit(execute(args.out, args.authorization))
