"""One guarded S04-E022 replay+report invocation; no fitting entry point."""
from __future__ import annotations

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


def execute(source_run: Path, output: Path, authorization_path: Path) -> int:
    source_run = source_run.resolve(); output = output.resolve()
    authorization_path = authorization_path.resolve()
    root = Path(__file__).resolve().parents[1]
    from s04_raw_replay import authorization
    approved = authorization(authorization_path, output, source_run)
    run_id = approved['run_id']
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    sidecars = [output.parent / (output.name + suffix) for suffix in
                ('_guard.log', '_replay_guard_receipt.json', '_guard_receipt.json')]
    if output.exists() or any(path.exists() for path in sidecars):
        raise FileExistsError('fresh output and sidecars required; no retry')
    output.parent.mkdir(parents=True, exist_ok=True)
    environment = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='4',
                       VECLIB_MAXIMUM_THREADS='4', CUDA_VISIBLE_DEVICES='',
                       RAW_REPLAY_START_MONOTONIC=str(time.monotonic()),
                       PYTHONUNBUFFERED='1')
    start = float(environment['RAW_REPLAY_START_MONOTONIC'])
    started_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    children = []; child = None; reason = None; peak = 0
    dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True)

    def size() -> int:
        payload = sum(path.stat().st_size for path in output.rglob('*') if path.is_file()) if output.exists() else 0
        return payload + sum(path.stat().st_size for path in sidecars if path.exists())

    def cap() -> str | None:
        nonlocal peak
        total = psutil.Process(os.getpid()).memory_info().rss
        if child is not None and child.poll() is None:
            try:
                process = psutil.Process(child.pid)
                total += process.memory_info().rss
                for descendant in process.children(recursive=True):
                    try:
                        total += descendant.memory_info().rss
                    except psutil.NoSuchProcess:
                        pass
            except psutil.NoSuchProcess:
                if child.poll() is None:
                    raise RuntimeError('lost process visibility')
        peak = max(peak, total)
        if time.monotonic() - start >= 300:
            return 'WALL_CAP'
        if peak > 2 * 1024**3:
            return 'RSS_CAP'
        if size() + 32768 > 100 * 1024**2:
            return 'OUTPUT_CAP'
        return None

    def receipt(status: str) -> dict:
        return dict(run_id=run_id, status=status, start_utc=started_utc,
                    elapsed_seconds=time.monotonic() - start, peak_rss_bytes=peak,
                    final_output_bytes=size(), code_commit=commit,
                    source_run=str(source_run), output=str(output), dirty_status=dirty,
                    producer=socket.gethostname(), python=sys.executable, gpu=None,
                    cpu_threads=4, children=children, fit_performed=False,
                    confirmation_accessed=False,
                    budget_scope='guard+child tree sampled RSS; replay+report outputs')

    with sidecars[0].open('x') as log:
        try:
            commands = [
                ('replay', [sys.executable, str(Path(__file__).with_name('s04_raw_replay.py')),
                            '--source-run', str(source_run), '--out', str(output),
                            '--authorization', str(authorization_path)]),
                ('report', [sys.executable, str(Path(__file__).with_name('s04_raw_replay_report.py')),
                            '--out', str(output)]),
            ]
            for phase, command in commands:
                reason = cap()
                if reason:
                    break
                child = subprocess.Popen(command, cwd=root, env=environment,
                                         stdout=log, stderr=log, start_new_session=True)
                children.append(dict(phase=phase, pid=child.pid, command=command))
                while child.poll() is None:
                    reason = cap()
                    if reason:
                        break
                    time.sleep(0.1)
                if reason:
                    break
                children[-1]['exit_code'] = child.returncode
                reason = cap() or ('CHILD_FAILED_' + phase if child.returncode else None)
                if reason:
                    break
                if phase == 'replay':
                    sidecars[1].write_text(json.dumps(receipt('COMPLETED'), indent=2))
        except BaseException as error:
            reason = 'GUARD_EXCEPTION_' + type(error).__name__
            print(repr(error), file=log, flush=True)
        finally:
            if child is not None and child.poll() is None:
                try:
                    os.killpg(child.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait()
            if child is not None and children:
                children[-1]['exit_code'] = child.poll()
    reason = reason or cap()
    record = receipt(reason or 'COMPLETED')
    sidecars[2].write_text(json.dumps(record, indent=2))
    print(json.dumps(record, indent=2))
    return 0 if record['status'] == 'COMPLETED' else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-run', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--authorization', type=Path, required=True)
    args = parser.parse_args()
    return execute(args.source_run, args.out, args.authorization)


if __name__ == '__main__':
    raise SystemExit(main())
