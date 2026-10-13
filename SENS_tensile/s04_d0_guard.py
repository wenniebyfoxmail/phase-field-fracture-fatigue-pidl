"""External hard-cap monitor for exactly one task-owned CPU D0 child."""
import argparse
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', required=True); a = p.parse_args()
    out = Path(a.out).resolve(); assert not out.exists(), 'Fresh output required'
    log = out.parent/(out.name+'_guard.log'); assert not log.exists()
    env = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4',
               VECLIB_MAXIMUM_THREADS='4', CUDA_VISIBLE_DEVICES='')
    env['D0_COMMIT'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    start = time.monotonic(); utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    peak = 0; reason = None
    def output_size():
        return (sum(f.stat().st_size for f in out.rglob('*') if f.is_file()) if out.exists() else 0)+log.stat().st_size

    def stop_owned_child():
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try: child.wait(timeout=.2)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL); child.wait()

    with open(log, 'x') as stream:
        child = subprocess.Popen([sys.executable, str(Path(__file__).with_name('s04_d0.py')),
                                  '--out', str(out)], env=env, stdout=stream, stderr=stream,
                                 start_new_session=True)
        try:
            while child.poll() is None:
                rss = subprocess.run(['ps', '-p', str(child.pid), '-o', 'rss='], capture_output=True, text=True, timeout=1)
                if rss.stdout.strip(): peak = max(peak, int(rss.stdout.strip())*1024)
                elif child.poll() is None: raise RuntimeError('Lost RSS visibility')
                if time.monotonic()-start >= 300: reason = 'WALL_CAP'
                if peak > 2*1024**3: reason = 'RSS_CAP'
                if output_size()+16384 > 100*1024**2: reason = 'OUTPUT_CAP'
                if reason: break
                time.sleep(.2)
        except BaseException as error:
            reason = 'GUARD_EXCEPTION_'+type(error).__name__
        finally:
            stop_owned_child()
    # Child may finish between polls: final elapsed/output recheck is mandatory.
    if time.monotonic()-start >= 300: reason = reason or 'WALL_CAP'
    final_size = output_size()
    if final_size+16384 > 100*1024**2: reason = reason or 'OUTPUT_CAP'
    receipt = dict(run_id='S04-E016-D0-R001', start_utc=utc, exit_code=child.returncode,
                   status=reason or ('COMPLETED' if child.returncode == 0 else 'FAILED'),
                   peak_rss_bytes=peak, elapsed_seconds=time.monotonic()-start,
                   child_pid=child.pid, code_commit=env['D0_COMMIT'], output=str(out),
                   final_output_bytes=final_size, dirty_status=subprocess.check_output(['git', 'status', '--porcelain'], text=True),
                   command=[sys.executable, 's04_d0.py', '--out', str(out)], gpu=None)
    (out.parent/(out.name+'_guard_receipt.json')).write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2)); sys.exit(0 if receipt['status'] == 'COMPLETED' else 1)
