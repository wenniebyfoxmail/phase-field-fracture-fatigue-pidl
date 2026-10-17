"""Single ATTR-R001 launcher. Static review and human approval are separate.

No scientific IO on import; no old access Run, retry, alternate command or root.
60s / aggregate sampled 512MiB / 5MiB includes reports, caches and receipt.
"""
import sys

if sys.flags.optimize != 0:
    raise RuntimeError('optimized Python is forbidden for real attribution guard')

import argparse
import datetime
import json
import os
from pathlib import Path
import socket
import stat
import subprocess
import time

import psutil

import s04_late_real_attribution as worker
import s04_late_attribution_guard as budget

a = worker.a
ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['SENS_tensile/'+name for name in (
    's04_late_attribution.py', 's04_late_attribution_guard.py', 's04_late_adapter.py',
    's04_late_real_attribution.py', 's04_late_real_attribution_guard.py')]
PLAN = 'docs/research/S04/S04-E021/late_regression_readonly_attribution_plan_v1.md'
SCOPE_DOC = 'docs/research/S04/S04-E021/late_attribution_real_plan_and_run_card_v1_20261017.md'


def inventory(out, *, tolerate_cache_missing=False):
    """Own output only; no symlinks, special files, hardlinks or hidden roots.

    Used during sampling too so caches/temporary files cannot escape accounting.
    Limited traversal does not recurse into a symlink or arbitrary data root.
    """
    files = {}
    directories = [out]
    seen = 0
    while directories:
        directory = directories.pop()
        try:
            entries = os.scandir(directory)
        except FileNotFoundError:
            relative_dir = str(directory.relative_to(out))
            if tolerate_cache_missing and (relative_dir == 'cache' or relative_dir.startswith('cache/')):
                continue
            raise
        with entries:
            for entry in entries:
                seen += 1
                a.require(seen <= 1024, 'bounded output inventory')
                relative = str(Path(entry.path).relative_to(out))
                try:
                    st = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    # Worker libraries may atomically replace/remove their own
                    # temporary caches between enumeration and stat. Skip this
                    # vanished cache item only; next bounded sample enumerates
                    # again. Core files, links and all other errors stay strict.
                    if tolerate_cache_missing and (relative == 'cache' or relative.startswith('cache/')):
                        continue
                    raise
                a.require(not stat.S_ISLNK(st.st_mode), 'output symlink forbidden')
                if stat.S_ISDIR(st.st_mode):
                    a.require(relative == 'cache' or relative.startswith('cache/'), 'unexpected output directory')
                    directories.append(Path(entry.path))
                else:
                    a.require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and
                              (relative in worker.FILES or relative.startswith('cache/')),
                              'unexpected output file')
                    files[relative] = st.st_size
    return files


def read_result(path):
    """Only own bounded summary after worker exit; never reopen science files."""
    st = path.lstat()
    before = a.token(st)
    a.require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and
              0 < st.st_size <= 131072, 'bounded own summary required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        a.require(a.token(os.fstat(fd)) == before, 'summary descriptor mismatch')
        data = bytearray()
        while len(data) <= 131072:
            block = os.read(fd, min(65536, 131073-len(data)))
            if not block:
                break
            data.extend(block)
        a.require(len(data) == st.st_size and a.token(os.fstat(fd)) == before,
                  'summary descriptor/size drift')
    finally:
        os.close(fd)
    a.require(a.token(path.lstat()) == before, 'summary path drift')
    return a.strict_json(bytes(data).decode('utf-8'))


def execute(out, code, refs, allow_real_attribution):
    started = time.monotonic()
    start_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    a.require(allow_real_attribution is True, 'separate explicit attribution execution approval required')
    worker.full_commit(code)
    a.check_execution_refs(refs, code)
    out = Path(out).absolute()
    a.require(str(out) == a.ATTR_OUTPUT and out.resolve() == out, 'fixed canonical new output required')
    a.require(not out.exists(), 'single attempt consumed; no retry or overwrite')
    child = log = None
    owned = False
    primary = None
    errors = []
    peak = 0
    phase = 'RESERVE_OUTPUT'
    checkout = dirty = None
    verification = None
    activity_state = dict(source_metadata_accessed=False, real_data_read=False,
                          attribution_invoked=False, plotting_invoked=False,
                          activity=None, certainty='NO_WORKER_STARTED')
    cleanup = dict(state='NOT_STARTED', exit_confirmed=False, worker_exit=None,
                   signals=[], events=[], errors=[])
    command = [sys.executable, str(Path(__file__).with_name('s04_late_real_attribution.py')),
               '--out', str(out)]

    def fail(reason, exc=None):
        nonlocal primary
        if primary is None:
            primary = reason
        if exc is not None:
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
                for process in [proc, *proc.children(recursive=True)]:
                    try:
                        rss += process.memory_info().rss
                    except psutil.NoSuchProcess:
                        pass
            except psutil.NoSuchProcess:
                if child.poll() is None:
                    raise RuntimeError('lost child visibility')
        peak = max(peak, rss)
        files = inventory(out, tolerate_cache_missing=child is not None and child.poll() is None)
        return budget.cap_reason(time.monotonic()-started, peak, sum(files.values()))

    try:
        out.mkdir(parents=True, exist_ok=False)
        owned = True
        log = (out/'analysis.log').open('x')
        phase = 'IDENTITY'
        checkout = git('rev-parse', 'HEAD')
        dirty = git('status', '--porcelain', '--', *SOURCES, PLAN, SCOPE_DOC)
        a.require(not dirty, 'reviewed sources and contracts must be clean')
        git('ls-files', '--error-unmatch', *SOURCES, PLAN, SCOPE_DOC)
        git('diff', '--exit-code', code, '--', *SOURCES, PLAN, SCOPE_DOC)
        git('diff', '--exit-code', a.ATTR_SCOPE_COMMIT, '--', PLAN, SCOPE_DOC)
        phase = 'AUTHORIZATION'
        grant = worker.grant_for(code, refs)
        a.check_grant(grant, code_commit=code, attempt=a.ATTR_RUN,
                      output=str(out), domain='REAL_SAVED_SCALARS')
        auth = out/'authorization.json'
        with auth.open('x') as file:
            json.dump(grant, file, indent=2, allow_nan=False)
        auth.chmod(0o444)
        handoff = a.prepare_handoff(str(auth), str(out), parent_pid=os.getpid(),
                                    attempt=a.ATTR_RUN, code_commit=code)
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1',
                   OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1',
                   NUMEXPR_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1', PYTHONOPTIMIZE='0',
                   S04_LATE_APPROVAL_REF=refs['approval_ref'], S04_LATE_REVIEW_REF=refs['review_ref'])
        env.update(handoff['env'])
        for key, value in worker.CACHE_ENV.items():
            cache = out/value
            cache.mkdir(parents=True, exist_ok=False)
            env[key] = str(cache)
        phase = 'PRELAUNCH_CAPS'
        reason = measure()
        if reason or time.monotonic()-started >= budget.WORK_WALL:
            fail(reason or 'WALL_RESERVE')
        else:
            phase = 'SPAWN'
            activity_state.update(source_metadata_accessed=None, real_data_read=None,
                                  attribution_invoked=None, plotting_invoked=None,
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

    phase = 'CHECK_WORKER_RECORD'
    try:
        if owned:
            try:
                result = read_result(out/'summary.json')
            except FileNotFoundError:
                result = None
            if result is not None:
                a.require(result['attempt_id'] == a.ATTR_RUN and result['code_commit'] == code and
                          result['scope'] == worker.SCOPE and result['scope_commit'] == a.ATTR_SCOPE_COMMIT and
                          result['plan_commit'] == a.core.PLAN_COMMIT and
                          result['domain'] == 'REAL_SAVED_SCALARS' and
                          result['evidence_domain'] == 'SYNTHETIC_VIEWED_DEVELOPMENT' and
                          result['sources'] == list(a.SOURCES) and result['execution_references'] == refs,
                          'worker record identity')
                activity = result['activity']
                a.require(all(type(activity[key]) is int and activity[key] >= 0 for key in
                              ('metadata_attempts', 'read_attempts', 'content_bytes')) and
                          set(activity['content_by_source']) == set(a.SOURCES) and
                          all(type(v) is int and v >= 0 for v in activity['content_by_source'].values()) and
                          sum(activity['content_by_source'].values()) == activity['content_bytes'] and
                          result['source_metadata_accessed'] is (activity['metadata_attempts'] > 0) and
                          result['real_data_read'] is (activity['content_bytes'] > 0) and
                          type(result['attribution_invoked']) is bool and type(result['plotting_invoked']) is bool,
                          'worker activity flags')
                verification = result
                activity_state.update(**{key: result[key] for key in (
                    'source_metadata_accessed', 'real_data_read', 'attribution_invoked', 'plotting_invoked')},
                    activity=activity, certainty='WORKER_FINAL_RECORD')
        if child is not None and verification is None:
            fail('INCOMPLETE_WORKER_RECORD')
        if primary is None:
            a.require(verification is not None and verification['status'] == 'READONLY_ATTRIBUTION_REPORTED' and
                      verification['error'] is None and verification['coverage_verified'] is True and
                      verification['rows_verified'] == 357 and verification['counts_verified'] == a.core.COUNTS and
                      verification['python_optimize'] == 0 and verification['python_debug'] is True and
                      verification['attribution_invoked'] is True and verification['plotting_invoked'] is True and
                      verification['fitting_invoked'] is False and verification['confirmation_accessed'] is False and
                      verification['real_data_read'] is True and
                      verification['original_scientific_verdict_unchanged'] is True and
                      set(verification['source_metadata']) == set(a.SOURCES) and
                      all(activity['content_by_source'][p] > 0 for p in a.SOURCES), 'invalid completion')
            analysis = verification['analysis']
            a.require(analysis['n'] == 81 and analysis['cycles'] == [41, 121] and
                      analysis['holdout'] == 'u011' and analysis['horizon'] == 0 and
                      analysis['plan_commit'] == a.core.PLAN_COMMIT and
                      analysis['status'] in ('DESCRIPTIVE_ONLY', 'INCONCLUSIVE') and
                      analysis['fitting_invoked'] is False and len(verification['saved_background']) == 3,
                      'analysis completion contract')
            files = inventory(out)
            a.require(set(worker.FILES)-{'guard_receipt.json'} <= set(files) and
                      all(files[name] > 0 for name in worker.FILES-{'guard_receipt.json'}),
                      'incomplete report inventory')
    except BaseException as exc:
        fail('CONTROL_RESULT_ERROR', exc)

    phase = 'FINAL_MEASURE'
    terminal_caps = []
    try:
        reason = measure() if owned else None
        if reason:
            terminal_caps.append(reason)
        files = inventory(out) if owned else {}
        size = sum(files.values())
    except BaseException as exc:
        size = files = None
        fail('FINAL_MEASURE_ERROR', exc)
    record = dict(status=primary or ('TERMINAL_CAP' if terminal_caps else 'COMPLETED'),
                  primary_reason=primary, terminal_caps=terminal_caps, scope=worker.SCOPE,
                  domain='REAL_SAVED_SCALARS', attempt_id=a.ATTR_RUN, start_utc=start_utc,
                  elapsed_seconds=time.monotonic()-started, aggregate_sampled_peak_rss_bytes=peak,
                  output_bytes_before_receipt=size, inventory_before_receipt=files, output=str(out),
                  caps=dict(a.BUDGET), work_wall_seconds=budget.WORK_WALL,
                  code_commit=code, checkout_commit=checkout, dirty_source_status=dirty,
                  plan_commit=a.core.PLAN_COMMIT, scope_commit=a.ATTR_SCOPE_COMMIT, execution_references=refs,
                  operator_must_verify_actual_approval=True, command=command, host=socket.gethostname(),
                  guard_pid=os.getpid(), worker_pid=None if child is None else child.pid,
                  worker_exit=cleanup['worker_exit'], cleanup=cleanup, errors=errors, gpu=None,
                  receipt_persisted=False, **activity_state,
                  fitting_invoked=False, confirmation_accessed=False, retry=False,
                  original_scientific_verdict_unchanged=True)

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
        final_bytes = sum(inventory(out).values()) if owned else None
        extras = []
        if final_bytes is not None and final_bytes >= budget.BYTES:
            extras.append('OUTPUT_CAP')
        if time.monotonic()-started >= budget.WALL:
            extras.append('WALL_CAP')
        if record['status'] == 'COMPLETED':
            a.require(worker.FILES <= set(inventory(out)), 'incomplete final inventory')
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
    parser.add_argument('--allow-real-attribution', action='store_true')
    args = parser.parse_args()
    refs = dict(approval_ref=args.approval_ref, review_ref=args.review_ref,
                reviewed_commit=args.expected_commit)
    raise SystemExit(execute(args.out, args.expected_commit, refs, args.allow_real_attribution))
