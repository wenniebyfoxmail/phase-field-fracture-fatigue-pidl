"""Explicit, single real-file access launcher; NOT execution authorization.

An operator must first inspect the actual independent review and human approval
for this exact version/command. References recorded here cannot prove consent.
No scientific IO occurs on import; no retries or command/data-root overrides.
"""
import sys

if sys.flags.optimize != 0:
    raise RuntimeError('optimized Python is forbidden for the real access guard')

import argparse
import datetime
import json
import os
from pathlib import Path
import socket
import subprocess
import time

import psutil

import s04_late_access as access
import s04_late_attribution_guard as budget

a = access.a
ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['SENS_tensile/'+name for name in (
    's04_late_attribution.py', 's04_late_attribution_guard.py',
    's04_late_adapter.py', 's04_late_access.py', 's04_late_access_guard.py')]
PLAN = 'docs/research/S04/S04-E021/late_regression_readonly_attribution_plan_v1.md'
SCOPE_DOC = 'docs/research/S04/S04-E021/late_real_readonly_access_scope_and_run_card_v1_20261017.md'
SCOPE_COMMIT = 'ea9cafbc907cb683544aca75a58480b51c7487bd'


def execute(out, code, refs, allow_real_read):
    # These explicit arguments are machine interlocks, not human authentication.
    a.require(allow_real_read is True, 'separate explicit real execution approval required')
    access.full_commit(code)
    a.check_execution_refs(refs, code)
    out = Path(out).absolute()
    a.require(str(out) == a.REAL_OUTPUT and out.resolve() == out, 'fixed canonical output required')
    a.require(not out.exists(), 'single attempt consumed; no retry or overwrite')
    started = time.monotonic()
    start_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    child = log = None
    owned = False
    primary = None
    errors = []
    peak = 0
    phase = 'RESERVE_OUTPUT'
    checkout = dirty = None
    verification = None
    access_state = dict(source_metadata_accessed=False, real_data_read=False,
                        activity=None, certainty='NO_WORKER_STARTED')
    cleanup = dict(state='NOT_STARTED', exit_confirmed=False, worker_exit=None,
                   signals=[], events=[], errors=[])
    command = [sys.executable, str(Path(__file__).with_name('s04_late_access.py')),
               '--out', str(out)]

    def fail(reason, exc=None):
        nonlocal primary
        if primary is None:
            primary = reason
        if exc is not None:
            # Exception text can contain source parser values: record type only.
            errors.append(dict(phase=phase, error_type=type(exc).__name__))

    def git(*args):
        remaining = budget.WORK_WALL-(time.monotonic()-started)
        if remaining <= 0:
            raise TimeoutError('work reserve reached')
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
        return budget.cap_reason(time.monotonic()-started, peak, budget.output_size(out))

    try:
        out.mkdir(parents=True, exist_ok=False)
        owned = True
        log = (out/'access.log').open('x')
        phase = 'IDENTITY'
        checkout = git('rev-parse', 'HEAD')
        dirty = git('status', '--porcelain', '--', *SOURCES, PLAN, SCOPE_DOC)
        a.require(not dirty, 'reviewed sources and contracts must be clean')
        git('ls-files', '--error-unmatch', *SOURCES, PLAN, SCOPE_DOC)
        git('diff', '--exit-code', code, '--', *SOURCES, PLAN, SCOPE_DOC)
        git('diff', '--exit-code', SCOPE_COMMIT, '--', PLAN, SCOPE_DOC)
        phase = 'AUTHORIZATION'
        grant = access.grant_for(code)
        a.check_grant(grant, code_commit=code, attempt=a.REAL_RUN,
                      output=str(out), domain='REAL_SAVED_SCALARS')
        auth = out/'authorization.json'
        with auth.open('x') as file:
            json.dump(grant, file, indent=2, allow_nan=False)
        auth.chmod(0o444)
        handoff = a.prepare_handoff(str(auth), str(out), parent_pid=os.getpid(),
                                    attempt=a.REAL_RUN, code_commit=code)
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1',
                   OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
                   VECLIB_MAXIMUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', PYTHONOPTIMIZE='0',
                   S04_LATE_APPROVAL_REF=refs['approval_ref'], S04_LATE_REVIEW_REF=refs['review_ref'])
        env.update(handoff['env'])
        phase = 'PRELAUNCH_CAPS'
        reason = measure()
        if reason or time.monotonic()-started >= budget.WORK_WALL:
            fail(reason or 'WALL_RESERVE')
        else:
            phase = 'SPAWN'
            access_state.update(source_metadata_accessed=None, real_data_read=None,
                                certainty='UNKNOWN_UNTIL_WORKER_RECORD')
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log,
                                     stderr=log, start_new_session=True)
            phase = 'MONITOR'
            while child.poll() is None:
                reason = measure()
                if reason or time.monotonic()-started >= budget.WORK_WALL:
                    fail(reason or 'WALL_RESERVE')
                    break
                time.sleep(.02)
            if primary is None and child.poll() != 0:
                fail('CHILD_FAILED' if child.poll() is not None else 'CHILD_EXIT_UNCONFIRMED')
    except BaseException as exc:
        fail('GUARD_EXCEPTION_'+phase+'_'+type(exc).__name__, exc)
    finally:
        phase = 'CLEANUP'
        try:
            cleanup = budget.cleanup_child(child)
        except BaseException as exc:
            fail('CLEANUP_EXCEPTION', exc)
            cleanup.update(state='EXIT_UNCONFIRMED', exit_confirmed=False)
        if child is not None and not cleanup['exit_confirmed']:
            fail('CLEANUP_INCOMPLETE')
        if cleanup['errors']:
            fail('CLEANUP_ERROR')
        if log is not None:
            try:
                log.close()
            except BaseException as exc:
                fail('LOG_CLOSE_ERROR', exc)

    # Read only our own bounded control result, including on a failed worker.
    # No worker/result means unknown, never a fabricated false real-read claim.
    phase = 'CHECK_WORKER_RECORD'
    try:
        result_path = out/'access_verification.json'
        if owned and result_path.is_file() and not result_path.is_symlink():
            a.require(result_path.stat().st_size <= 65536, 'bounded worker record required')
            result = a.strict_json(result_path.read_text())
            a.require(result['attempt_id'] == a.REAL_RUN and result['code_commit'] == code and
                      result['scope'] == access.SCOPE and result['domain'] == 'REAL_SAVED_SCALARS' and
                      result['sources'] == list(a.SOURCES) and result['execution_references'] == refs,
                      'worker record identity')
            activity = result['activity']
            a.require(type(activity['metadata_attempts']) is int and activity['metadata_attempts'] >= 0 and
                      type(activity['content_bytes']) is int and activity['content_bytes'] >= 0 and
                      result['source_metadata_accessed'] is (activity['metadata_attempts'] > 0) and
                      result['real_data_read'] is (activity['content_bytes'] > 0), 'worker access flags')
            verification = result
            access_state.update(source_metadata_accessed=result['source_metadata_accessed'],
                                real_data_read=result['real_data_read'], activity=activity,
                                certainty='WORKER_FINAL_RECORD')
        if child is not None and verification is None:
            fail('INCOMPLETE_WORKER_RECORD')
        if primary is None:
            a.require(verification is not None and verification['status'] == 'READONLY_ACCESS_VERIFIED' and
                      verification['error'] is None and verification['coverage_verified'] is True and
                      verification['rows_verified'] == 357 and verification['counts_verified'] == a.core.COUNTS and
                      verification['python_optimize'] == 0 and verification['python_debug'] is True and
                      verification['saved_ratio_verified'] is True and
                      verification['attribution_invoked'] is False and verification['fitting_invoked'] is False and
                      verification['confirmation_accessed'] is False and
                      verification['real_data_read'] is True and
                      set(verification['source_metadata']) == set(a.SOURCES) and
                      all(verification['activity']['content_by_source'][p] > 0 for p in a.SOURCES),
                      'invalid real access completion')
    except BaseException as exc:
        fail('CONTROL_RESULT_ERROR', exc)

    phase = 'FINAL_MEASURE'
    terminal_caps = []
    try:
        reason = measure()
        if reason:
            terminal_caps.append(reason)
        size = budget.output_size(out)
    except BaseException as exc:
        size = None
        fail('FINAL_MEASURE_ERROR', exc)
    record = dict(status=primary or ('TERMINAL_CAP' if terminal_caps else 'COMPLETED'),
                  primary_reason=primary, terminal_caps=terminal_caps, scope=access.SCOPE,
                  domain='REAL_SAVED_SCALARS', attempt_id=a.REAL_RUN, start_utc=start_utc,
                  elapsed_seconds=time.monotonic()-started, aggregate_sampled_peak_rss_bytes=peak,
                  output_bytes_before_receipt=size, output=str(out), caps=dict(a.BUDGET),
                  work_wall_seconds=budget.WORK_WALL, code_commit=code, checkout_commit=checkout,
                  dirty_source_status=dirty, scope_commit=SCOPE_COMMIT, execution_references=refs,
                  operator_must_verify_actual_approval=True, command=command, host=socket.gethostname(),
                  guard_pid=os.getpid(), worker_pid=None if child is None else child.pid,
                  worker_exit=cleanup['worker_exit'], cleanup=cleanup, errors=errors, gpu=None,
                  receipt_persisted=False, **access_state,
                  attribution_invoked=False, fitting_invoked=False, confirmation_accessed=False, retry=False)

    def persist(mode):
        try:
            if not owned:
                raise OSError('cannot write receipt in unowned output')
            record['receipt_persisted'] = True
            with (out/'guard_receipt.json').open(mode) as file:
                json.dump(record, file, indent=2, allow_nan=False)
        except BaseException as exc:
            record['receipt_persisted'] = False
            record['errors'].append(dict(phase='WRITE_RECEIPT', error_type=type(exc).__name__))
            record['primary_reason'] = record['primary_reason'] or 'RECEIPT_WRITE_FAILED'
            record['status'] = record['primary_reason']

    persist('x')
    try:
        final_bytes = budget.output_size(out)
        extras = []
        if final_bytes >= budget.BYTES:
            extras.append('OUTPUT_CAP')
        if time.monotonic()-started >= budget.WALL:
            extras.append('WALL_CAP')
        if record['status'] == 'COMPLETED':
            a.require({p.name for p in out.iterdir()} == access.FILES, 'unexpected control output inventory')
        if extras:
            record['terminal_caps'] = sorted(set(record['terminal_caps']+extras))
            record['status'] = record['primary_reason'] or 'TERMINAL_CAP'
            if record['receipt_persisted']:
                persist('w')
    except BaseException as exc:
        final_bytes = None
        record['errors'].append(dict(phase='POST_RECEIPT_MEASURE', error_type=type(exc).__name__))
        record['primary_reason'] = record['primary_reason'] or 'POST_RECEIPT_MEASURE_ERROR'
        record['status'] = record['primary_reason']
        if record['receipt_persisted']:
            persist('w')
    print(json.dumps(dict(record, final_output_bytes=final_bytes), indent=2, allow_nan=False))
    return int(record['status'] != 'COMPLETED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--approval-ref', required=True)
    parser.add_argument('--review-ref', required=True)
    parser.add_argument('--allow-real-read', action='store_true')
    args = parser.parse_args()
    refs = dict(approval_ref=args.approval_ref, review_ref=args.review_ref,
                reviewed_commit=args.expected_commit)
    raise SystemExit(execute(args.out, args.expected_commit, refs, args.allow_real_read))
