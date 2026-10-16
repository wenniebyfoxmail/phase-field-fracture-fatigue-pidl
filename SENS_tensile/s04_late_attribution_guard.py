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
ATTEMPT = 'S04-E021-LATE-ENG-R002'
OUTPUT_NAME = 'late-attribution-20261016-R002'
WALL, RSS, BYTES = 60., 512*1024**2, 5*1024**2
RESERVE = 16384
WORK_WALL = WALL-2.  # Leave time for bounded cleanup and receipt IO.
SOURCES = ['SENS_tensile/s04_late_attribution'+s for s in
           ('.py', '_guard.py', '_checks.py')]


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


def cleanup_child(child):
    """Only the process group created by this invocation; never claim an exit
    from a successful signal call. Both waits and the final poll may fail.
    """
    result = dict(state='NOT_STARTED', exit_confirmed=False, worker_exit=None,
                  signals=[], events=[], errors=[])
    if child is None:
        return result

    def poll():
        try:
            code = child.poll()
            if code is not None:
                result.update(exit_confirmed=True, worker_exit=code)
            return code
        except BaseException as exc:
            result['errors'].append('POLL_'+repr(exc))
            return None

    if poll() is not None:
        result['state'] = 'ALREADY_EXITED'
        return result
    for label, sig in (('TERM', signal.SIGTERM), ('KILL', signal.SIGKILL)):
        try:
            os.killpg(child.pid, sig)
            result['signals'].append(label)
        except ProcessLookupError:
            result['events'].append(label+'_GROUP_NOT_FOUND')
        except BaseException as exc:
            result['errors'].append(label+'_SIGNAL_'+repr(exc))
        try:
            code = child.wait(timeout=.25)
            if code is not None:
                result.update(state=label+'_EXITED', exit_confirmed=True, worker_exit=code)
                return result
        except subprocess.TimeoutExpired:
            result['events'].append(label+'_WAIT_TIMEOUT')
        except BaseException as exc:
            result['errors'].append(label+'_WAIT_'+repr(exc))
    result['state'] = 'EXITED_AFTER_FINAL_POLL' if poll() is not None else 'EXIT_UNCONFIRMED'
    return result


def execute(out, attempt, expected_commit):
    # Reject other/consumed destinations before any write: never overwrite the
    # old attempt's evidence or create receipts at caller-selected paths.
    out = Path(out).absolute()
    if (attempt != ATTEMPT or out.parent != ENGINEERING or out.resolve() != out or
            out.name != OUTPUT_NAME):
        raise ValueError('only fixed generated-engineering destination is enabled')
    if out.exists():
        raise FileExistsError('single attempt consumed; no retry or overwrite')
    if len(expected_commit) != 40 or any(c not in '0123456789abcdef' for c in expected_commit):
        raise ValueError('full reviewed source commit required')
    started = time.monotonic()
    utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    child = None
    log = None
    owned_out = False
    peak = 0
    primary = None
    errors = []
    phase = 'RESERVE_OUTPUT'
    checkout_commit = dirty = None
    cleanup = dict(state='NOT_STARTED', exit_confirmed=False, worker_exit=None,
                   signals=[], events=[], errors=[])
    command = [sys.executable, str(Path(__file__).with_name('s04_late_attribution_checks.py')),
               '--out', str(out)]
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1',
               MPLCONFIGDIR=str(out/'mplcache'), PYTHONDONTWRITEBYTECODE='1')

    def fail(reason, exc=None):
        nonlocal primary
        if primary is None:
            primary = reason
        if exc is not None:
            errors.append(dict(phase=phase, error=repr(exc)))

    def git(*args):
        remaining = WORK_WALL-(time.monotonic()-started)
        if remaining <= 0:
            raise TimeoutError('work time reserve reached before Git command')
        return subprocess.check_output(['git', *args], cwd=ROOT, text=True,
                                       timeout=min(2., remaining)).strip()

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

    try:
        out.mkdir(parents=True, exist_ok=False)
        owned_out = True
        phase = 'OPEN_LOG'
        log = (out/'engineering.log').open('x')
        phase = 'IDENTITY'
        checkout_commit = git('rev-parse', 'HEAD')
        dirty = git('status', '--porcelain', '--', *SOURCES)
        if dirty:
            raise ValueError('reviewed sources must be clean')
        git('ls-files', '--error-unmatch', *SOURCES)
        # Documentation-only commits after the reviewed snapshot are allowed;
        # the exact core/guard/checks and frozen plan must still match.
        plan = 'docs/research/S04/S04-E021/late_regression_readonly_attribution_plan_v1.md'
        git('diff', '--exit-code', expected_commit, '--', *SOURCES, plan)
        phase = 'PRELAUNCH_CAPS'
        reason = measure()
        if reason:
            fail(reason)
        elif time.monotonic()-started >= WORK_WALL:
            fail('WALL_RESERVE')
        else:
            phase = 'SPAWN'
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                     stderr=log, start_new_session=True)
            phase = 'MONITOR'
            while child.poll() is None:
                reason = measure()
                if reason or time.monotonic()-started >= WORK_WALL:
                    fail(reason or 'WALL_RESERVE')
                    break
                time.sleep(.02)
            if primary is None:
                # An observed worker failure remains the primary reason even
                # if the terminal budget sample also finds a cap.
                code = child.poll()
                if code != 0:
                    fail('CHILD_FAILED' if code is not None else 'CHILD_EXIT_UNCONFIRMED')
                else:
                    phase = 'CHECK_OUTPUT'
                    if not (out/'checks.json').is_file():
                        fail('INCOMPLETE_OUTPUT')
                    else:
                        result = json.loads((out/'checks.json').read_text())
                        if (result.get('status') != 'GENERATED_CHECKS_COMPLETED' or
                                result.get('scope') != 'GENERATED_ENGINEERING_ONLY' or
                                result.get('real_data_read') is not False or
                                result.get('fitting_invoked') is not False):
                            fail('INVALID_COMPLETION_RECORD')
    except BaseException as exc:
        fail('GUARD_EXCEPTION_'+phase+'_'+type(exc).__name__, exc)
    finally:
        phase = 'CLEANUP'
        try:
            cleanup = cleanup_child(child)
        except BaseException as exc:
            cleanup.update(state='EXIT_UNCONFIRMED', exit_confirmed=False)
            fail('CLEANUP_EXCEPTION', exc)
        if child is not None and not cleanup['exit_confirmed']:
            fail('CLEANUP_INCOMPLETE')
        if cleanup['errors']:
            fail('CLEANUP_ERROR')
        phase = 'CLOSE_LOG'
        if log is not None:
            try:
                log.close()
            except BaseException as exc:
                fail('LOG_CLOSE_ERROR', exc)

    phase = 'FINAL_MEASURE'
    terminal_caps = []
    try:
        reason = measure()
        if reason:
            terminal_caps.append(reason)
    except BaseException as exc:
        fail('FINAL_MEASURE_ERROR', exc)
    try:
        size = output_size(out)
    except BaseException as exc:
        size = None
        fail('OUTPUT_MEASURE_ERROR', exc)
    record = dict(status=primary or ('TERMINAL_CAP' if terminal_caps else 'COMPLETED'),
                  primary_reason=primary, terminal_caps=terminal_caps,
                  scope='GENERATED_ENGINEERING_ONLY', attempt_id=attempt,
                  start_utc=utc, elapsed_seconds=time.monotonic()-started,
                  aggregate_sampled_peak_rss_bytes=peak,
                  output_bytes_before_receipt=size, output=str(out),
                  caps=dict(seconds=WALL, rss_bytes=RSS, output_bytes=BYTES),
                  work_wall_seconds=WORK_WALL, code_commit=expected_commit,
                  checkout_commit=checkout_commit, dirty_source_status=dirty, command=command,
                  host=socket.gethostname(), guard_pid=os.getpid(),
                  worker_pid=None if child is None else child.pid,
                  worker_exit=cleanup['worker_exit'], cleanup=cleanup, errors=errors, gpu=None,
                  receipt_persisted=False,
                  real_data_read=False, fitting_invoked=False, retry=False)

    def persist(mode):
        # Failure to write cannot guarantee a disk receipt. Console JSON and
        # nonzero exit explicitly mark the receipt unconfirmed, never success.
        try:
            if not owned_out:
                raise OSError('output reservation failed; no receipt write into unowned destination')
            record['receipt_persisted'] = True
            with (out/'guard_receipt.json').open(mode) as file:
                json.dump(record, file, indent=2, allow_nan=False)
        except BaseException as exc:
            record['receipt_persisted'] = False
            record['errors'].append(dict(phase='WRITE_RECEIPT', error=repr(exc)))
            if record['primary_reason'] is None:
                record['primary_reason'] = 'RECEIPT_WRITE_FAILED'
            record['status'] = record['primary_reason']

    persist('x')
    try:
        final_bytes = output_size(out)
        extra = []
        if final_bytes >= BYTES:
            extra.append('OUTPUT_CAP')
        if time.monotonic()-started >= WALL:
            extra.append('WALL_CAP')
        if extra:
            record['terminal_caps'] = sorted(set(record['terminal_caps']+extra))
            record['status'] = record['primary_reason'] or 'TERMINAL_CAP'
            if record['receipt_persisted']:
                persist('w')
    except BaseException as exc:
        final_bytes = None
        record['errors'].append(dict(phase='POST_RECEIPT_MEASURE', error=repr(exc)))
        if record['primary_reason'] is None:
            record['primary_reason'] = 'POST_RECEIPT_MEASURE_ERROR'
        record['status'] = record['primary_reason']
        if record['receipt_persisted']:
            persist('w')
    print(json.dumps(dict(record, final_output_bytes=final_bytes), indent=2))
    return int(record['status'] != 'COMPLETED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--attempt', required=True)
    parser.add_argument('--expected-commit', required=True)
    args = parser.parse_args()
    raise SystemExit(execute(args.out, args.attempt, args.expected_commit))
