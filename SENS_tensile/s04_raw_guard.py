"""One guarded fit+report pipeline. Real mode requires a separate approval artifact."""
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


def execute(out, synthetic=False, auth_path=None):
    root = Path(__file__).resolve().parents[1]
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    # Authorization is checked BEFORE creating output or opening any source archive.
    if synthetic:
        run_id = out.name
        if not run_id.startswith('RAW_SYNTHETIC_'):
            raise ValueError('synthetic output identity required')
    else:
        from s04_raw import authorization
        a = authorization(auth_path, out); run_id = a['run_id']
    paths = [out.parent/(out.name+s) for s in
             ('_guard.log', '_fit_guard_receipt.json', '_guard_receipt.json')]
    if out.exists() or any(p.exists() for p in paths):
        raise FileExistsError('fresh output and sidecars required; no retry')
    out.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4',
               VECLIB_MAXIMUM_THREADS='4', CUDA_VISIBLE_DEVICES='',
               RAW_CODE_COMMIT=commit, RAW_RUN_ID=run_id, PYTHONUNBUFFERED='1')
    if auth_path is not None:
        env['RAW_AUTHORIZATION'] = str(auth_path.resolve())
    start = time.monotonic(); env['RAW_START_MONOTONIC'] = str(start)
    children = []; peak = 0; child = None; reason = None
    utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True)

    def size():
        payload = sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) if out.exists() else 0
        return payload+sum(p.stat().st_size for p in paths if p.exists())

    def check_caps():
        nonlocal peak
        proc = psutil.Process(os.getpid())
        total = proc.memory_info().rss
        if child is not None and child.poll() is None:
            try:
                cp = psutil.Process(child.pid)
                total += cp.memory_info().rss
                for descendant in cp.children(recursive=True):
                    try: total += descendant.memory_info().rss
                    except psutil.NoSuchProcess: pass
            except psutil.NoSuchProcess:
                if child.poll() is None: raise RuntimeError('lost process visibility')
        peak = max(peak, total)
        if time.monotonic()-start >= 300: return 'WALL_CAP'
        if peak > 2*1024**3: return 'RSS_CAP'
        if size()+32768 > 100*1024**2: return 'OUTPUT_CAP'
        return None

    def receipt(status):
        return dict(run_id=run_id, mode='synthetic_engineering' if synthetic else 'real',
            status=status, start_utc=utc, elapsed_seconds=time.monotonic()-start,
            peak_rss_bytes=peak, final_output_bytes=size(), code_commit=commit,
            design_commit='45b8d32', output=str(out.resolve()), dirty_status=dirty,
            producer=socket.gethostname(), python=sys.executable, gpu=None, cpu_threads=4,
            children=children, budget_scope='guard+child tree RSS; fit+report incl logs/receipts',
            real_fit_requested=not synthetic, real_fit_performed=False if synthetic else None)

    with paths[0].open('x') as log:
        try:
            first = [sys.executable, str(Path(__file__).with_name(
                's04_raw_checks.py' if synthetic else 's04_raw.py')),
                '--out', str(out)]
            first += ['--synthetic-pipeline'] if synthetic else ['--authorization', str(auth_path)]
            second = [sys.executable, str(Path(__file__).with_name('s04_raw_report.py')), '--out', str(out)]
            for phase, command in [('fit', first), ('report', second)]:
                reason = check_caps()
                if reason: break
                child = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=log,
                                         start_new_session=True)
                children.append(dict(phase=phase, pid=child.pid, command=command))
                while child.poll() is None:
                    reason = check_caps()
                    if reason: break
                    time.sleep(.1)
                if reason: break
                children[-1]['exit_code'] = child.returncode
                reason = check_caps() or ('CHILD_FAILED_'+phase if child.returncode else None)
                if reason: break
                if phase == 'fit':
                    paths[1].write_text(json.dumps(receipt('COMPLETED'), indent=2))
        except BaseException as e:
            reason = 'GUARD_EXCEPTION_'+type(e).__name__
            print(repr(e), file=log, flush=True)
        finally:
            if child is not None and child.poll() is None:
                try: os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                try: child.wait(timeout=.5)
                except subprocess.TimeoutExpired:
                    try: os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    child.wait()
            if child is not None and children: children[-1]['exit_code'] = child.poll()
    reason = reason or check_caps()
    record = receipt(reason or 'COMPLETED')
    paths[2].write_text(json.dumps(record, indent=2)); print(json.dumps(record, indent=2))
    return 0 if record['status'] == 'COMPLETED' else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--synthetic', action='store_true'); p.add_argument('--authorization', type=Path)
    args = p.parse_args()
    raise SystemExit(execute(args.out.resolve(), args.synthetic, args.authorization))
