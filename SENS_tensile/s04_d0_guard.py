"""One external guard: fit + renderer jointly <=300s/2GiB/100MiB. No retry."""
import argparse
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def execute(out):
    assert not out.exists(), 'Fresh output required'
    log = out.parent/(out.name+'_guard.log')
    fit_receipt = out.parent/(out.name+'_fit_guard_receipt.json')
    final_receipt = out.parent/(out.name+'_guard_receipt.json')
    assert not any(p.exists() for p in (log, fit_receipt, final_receipt))
    env = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4',
               VECLIB_MAXIMUM_THREADS='4', CUDA_VISIBLE_DEVICES='')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    env['D0_COMMIT'] = commit
    dirty = subprocess.check_output(['git', 'status', '--porcelain'], text=True)
    start = time.monotonic(); utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    peak = 0; reason = None; children = []; child = None

    def size():
        payload = sum(f.stat().st_size for f in out.rglob('*') if f.is_file()) if out.exists() else 0
        return payload+sum(p.stat().st_size for p in (log, fit_receipt, final_receipt) if p.exists())

    def caps():
        if time.monotonic()-start >= 300: return 'WALL_CAP'
        if peak > 2*1024**3: return 'RSS_CAP'
        if size()+16384 > 100*1024**2: return 'OUTPUT_CAP'
        return None

    def stop_owned():
        if child is None: return
        if child.poll() is None:
            try: os.killpg(child.pid, signal.SIGTERM)
            except ProcessLookupError: pass
            try: child.wait(timeout=.2)
            except subprocess.TimeoutExpired:
                try: os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                child.wait()

    def receipt(status):
        return dict(run_id='S04-E016-D0-R002', status=status, start_utc=utc,
                    elapsed_seconds=time.monotonic()-start, peak_rss_bytes=peak,
                    final_output_bytes=size(), code_commit=commit, dirty_status=dirty,
                    output=str(out), children=children, gpu=None,
                    budget_scope='fit plus renderer, logs and both guard receipts')

    with open(log, 'x') as stream:
        try:
            for phase, script in [('fit', 's04_d0.py'), ('report', 's04_d0_report.py')]:
                reason = caps()
                if reason: break
                child = None
                command = [sys.executable, str(Path(__file__).with_name(script)), '--out', str(out)]
                child = subprocess.Popen(command, env=env, stdout=stream, stderr=stream, start_new_session=True)
                children.append(dict(phase=phase, pid=child.pid, command=command))
                while child.poll() is None:
                    rss = subprocess.run(['ps', '-p', str(child.pid), '-o', 'rss='],
                                         capture_output=True, text=True, timeout=1)
                    if rss.stdout.strip(): peak = max(peak, int(rss.stdout.strip())*1024)
                    elif child.poll() is None: raise RuntimeError('Lost RSS visibility')
                    reason = caps()
                    if reason: break
                    time.sleep(.2)
                if reason: break
                children[-1]['exit_code'] = child.returncode
                reason = caps() or ('CHILD_FAILED_'+phase if child.returncode != 0 else None)
                if reason: break
                if phase == 'fit':
                    fit_receipt.write_text(json.dumps(receipt('COMPLETED'), indent=2))
        except BaseException as error:
            reason = 'GUARD_EXCEPTION_'+type(error).__name__
        finally:
            try: stop_owned()
            except BaseException as error:
                reason = reason or 'CLEANUP_EXCEPTION_'+type(error).__name__
            if child is not None and children:
                children[-1]['exit_code'] = child.poll()
    reason = reason or caps()
    record = receipt(reason or 'COMPLETED')
    final_receipt.write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))
    return 0 if record['status'] == 'COMPLETED' else 1


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', required=True); a = p.parse_args()
    sys.exit(execute(Path(a.out).resolve()))
