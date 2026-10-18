"""E026 future one-shot launcher, not an execution approval.

300s / sampled aggregate 2GiB / all run files 100MiB. Failure consumes the
fixed new directory; no retry, alternate input/command, resume or confirmation.
Import performs no scientific IO. Static review is not a runtime test.
"""
import sys

if sys.flags.optimize:
    raise RuntimeError('non-optimised Python required')

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

import s04_l32_inputs as io
from s04_late_attribution_guard import cleanup_child

WALL, WORK, RSS, BYTES, RESERVE = 300., 295., 2*1024**3, 100*1024**2, 32768
FILES = {'authorization.json', 'models.json', 'percycle.csv', 'summary.json',
         'diagnostic.png', 'README_analysis.md', 'receipt.json', 'run.log', 'guard_receipt.json'}
PROPOSAL_DOC = 'docs/research/S04/S04-E025/stage_state_review_and_minimal_proposal_v1_20261017.md'
CONTRACTS = [PROPOSAL_DOC, io.MANIFEST, 'docs/research/S04/S04-E026/experiment.md',
             'docs/research/S04/S04-E025/input_manifest.json',
             'docs/research/S04/S04-E016/paired_s4_lock_candidate_20261013.json',
             'docs/research/S04/S04-E016/g5_archive_admission_verdict_20261013.md']
SOURCES = ['SENS_tensile/'+name for name in (
    's04_l32.py', 's04_l32_inputs.py', 's04_l32_guard.py', 's04_phase.py', 's04_phase_inputs.py', 's04_raw.py',
    's04_d0.py', 's04_g5_features.py', 's04_late_attribution_guard.py')]


def inventory(out, active=False):
    files, directories, count = {}, [out], 0
    while directories:
        directory = directories.pop()
        try:
            entries = os.scandir(directory)
        except FileNotFoundError:
            if active and str(directory.relative_to(out)).startswith('cache/'):
                continue
            raise
        with entries:
            for entry in entries:
                count += 1
                io.require(count <= 1024, 'bounded output inventory')
                relative = str(Path(entry.path).relative_to(out))
                try:
                    st = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    if active and relative.startswith('cache/'):
                        continue
                    raise
                io.require(not stat.S_ISLNK(st.st_mode), 'no output symlinks')
                if stat.S_ISDIR(st.st_mode):
                    io.require(relative == 'cache' or relative.startswith('cache/'), 'only cache directories')
                    directories.append(Path(entry.path))
                else:
                    io.require(stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and
                               (relative in FILES or relative.startswith('cache/')), 'regular own files only')
                    files[relative] = st.st_size
    return files


def execute(out, code, refs, allow_fit):
    started = time.monotonic()
    utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    io.require(allow_fit is True, 'separate human approval of exact real run required')
    io.refs_ok(code, refs)
    out = Path(out).absolute()
    io.require(out == io.OUT and out.resolve() == out and not out.exists(), 'fixed unused canonical output')
    child = log = None
    launch_attempted = False
    owned, peak, primary = False, 0, None
    errors, terminal_caps = [], []
    checkout = dirty = verification = None
    phase = 'RESERVE_OUTPUT'
    cleanup = dict(state='NOT_STARTED', exit_confirmed=False, worker_exit=None, signals=[], events=[], errors=[])
    flags = dict(source_metadata_accessed=False, real_data_read=False, fitting_invoked=False,
                 evaluation_invoked=False, plotting_invoked=False, activity=None, certainty='NO_WORKER_STARTED')
    command = [sys.executable, str(io.ROOT/'SENS_tensile/s04_l32.py'), '--out', str(out)]

    def fail(reason, exc=None):
        nonlocal primary
        primary = primary or reason
        if exc is not None:
            errors.append(dict(phase=phase, type=type(exc).__name__))

    def git(*args):
        remaining = WORK-(time.monotonic()-started)
        io.require(remaining > 0, 'work reserve reached')
        return subprocess.check_output(['git', *args], cwd=io.ROOT, text=True,
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
                io.require(child.poll() is not None, 'lost running child visibility')
        peak = max(peak, rss)
        files = inventory(out, child is not None and child.poll() is None)
        if time.monotonic()-started >= WALL:
            return 'WALL_CAP'
        if peak >= RSS:
            return 'RSS_CAP'
        if sum(files.values())+RESERVE >= BYTES:
            return 'OUTPUT_CAP'
        return None

    try:
        out.mkdir(parents=True, exist_ok=False); owned = True
        log = (out/'run.log').open('x')
        phase = 'GIT_IDENTITY'
        checkout = git('rev-parse', 'HEAD')
        dirty = git('status', '--porcelain', '--', *SOURCES, *CONTRACTS)
        io.require(not dirty, 'reviewed code/contracts must be clean')
        git('ls-files', '--error-unmatch', *SOURCES, *CONTRACTS)
        git('diff', '--exit-code', code, '--', *SOURCES, *CONTRACTS)
        git('diff', '--exit-code', io.PROPOSAL, '--', PROPOSAL_DOC)
        phase = 'AUTHORIZATION'
        m = io.manifest()  # Git records only, still no scientific stat/open.
        with (out/'authorization.json').open('x') as file:
            json.dump(io.grant_for(code, refs, m), file, indent=2, allow_nan=False)
        (out/'authorization.json').chmod(0o444)
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                   MKL_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1', NUMEXPR_NUM_THREADS='1',
                   PYTHONOPTIMIZE='0', PYTHONDONTWRITEBYTECODE='1', RAW_START_MONOTONIC=str(started),
                   S04_L32_OUTPUT=str(out), S04_L32_PARENT=str(os.getpid()), S04_L32_RUN=io.RUN,
                   S04_L32_CODE=code, S04_L32_AUTH=str(out/'authorization.json'),
                   S04_L32_APPROVAL_REF=refs['approval_ref'], S04_L32_REVIEW_REF=refs['review_ref'])
        for key, value in io.CACHE.items():
            (out/value).mkdir(parents=True, exist_ok=False)
            env[key] = str(out/value)
        phase = 'PRELAUNCH'
        reason = measure()
        if reason or time.monotonic()-started >= WORK:
            fail(reason or 'WALL_RESERVE')
        else:
            phase = 'SPAWN'
            # Popen may be interrupted after creating a process but before
            # returning its handle. Unknown must precede even that attempt.
            flags.update({k: None for k in ('source_metadata_accessed', 'real_data_read', 'fitting_invoked',
                                           'evaluation_invoked', 'plotting_invoked')})
            flags['certainty'] = 'UNKNOWN_UNTIL_WORKER_RECORD'
            launch_attempted = True
            child = subprocess.Popen(command, cwd=io.ROOT, env=env, stdout=log, stderr=log, start_new_session=True)
            phase = 'MONITOR'
            while child.poll() is None:
                reason = measure()
                if reason or time.monotonic()-started >= WORK:
                    fail(reason or 'WALL_RESERVE'); break
                time.sleep(.02)
            if primary is None and child.poll() != 0:
                fail('CHILD_FAILED')
    except BaseException as exc:
        fail('GUARD_EXCEPTION_'+phase, exc)
    finally:
        phase = 'CLEANUP'
        try:
            if launch_attempted and child is None:
                # A missing handle after an attempted launch is not proof of
                # failed creation. Do not scan/kill unrelated processes or
                # claim the possible child exited or stayed within the caps.
                cleanup.update(state='LAUNCH_OWNERSHIP_UNCONFIRMED', exit_confirmed=False,
                               events=['LAUNCH_ATTEMPTED_WITHOUT_RETURNED_HANDLE'])
                fail('LAUNCH_OWNERSHIP_UNCONFIRMED')
            else:
                cleanup = cleanup_child(child)
        except BaseException as exc:
            fail('CLEANUP_EXCEPTION', exc)
        if child is not None and (not cleanup['exit_confirmed'] or cleanup['errors']):
            fail('CLEANUP_INCOMPLETE')
        if log is not None:
            try:
                log.close()
            except BaseException as exc:
                fail('LOG_CLOSE_ERROR', exc)

    phase = 'WORKER_RECORD'
    try:
        if owned and child is not None:
            r = io.read_control(out/'receipt.json', 524288)
            io.require(r['experiment_id'] == io.EXPERIMENT and r['run_id'] == io.RUN and
                       r['code_commit'] == code and r['proposal_commit'] == io.PROPOSAL and
                       r['output'] == str(out) and r['execution_references'] == refs and
                       r['input_manifest'] == io.MANIFEST and r['lock_sha256'] == io.LOCK_SHA and
                       r['python_optimize'] == 0 and r['python_debug'] is True and
                       r['confirmation_accessed'] is False, 'worker receipt identity')
            a = r['activity']
            io.require(all(type(a[k]) is int and a[k] >= 0 for k in (
                'metadata_attempts', 'read_attempts', 'hash_bytes_read', 'decode_attempts',
                'solves_attempted', 'fits_completed')) and
                all(type(a[k]) is bool for k in ('fitting_invoked', 'evaluation_invoked', 'plotting_invoked')) and
                r['source_metadata_accessed'] is (a['metadata_attempts'] > 0) and
                r['real_data_read'] is (a['hash_bytes_read'] > 0), 'typed activity')
            verification = r
            flags.update(source_metadata_accessed=r['source_metadata_accessed'], real_data_read=r['real_data_read'],
                         fitting_invoked=a['fitting_invoked'], evaluation_invoked=a['evaluation_invoked'],
                         plotting_invoked=a['plotting_invoked'], activity=a, certainty='WORKER_FINAL_RECORD')
        if primary is None:
            io.require(verification is not None and r['status'] == 'COMPLETED' and r['error'] is None and
                       r['evaluation_rows'] == 121 and a['metadata_attempts'] == a['read_attempts'] ==
                       a['decode_attempts'] == 9 and a['hash_bytes_read'] > 0 and
                       a['solves_attempted'] == a['fits_completed'] == 1 and
                       all(a[k] is True for k in ('fitting_invoked', 'evaluation_invoked', 'plotting_invoked')),
                       'incomplete one-fit execution')
            io.require(r['baseline_recomputed'] is False and r['baseline_refitted'] is False and
                       a['late_training_cycles'] == 116 and a['frozen_read_attempts'] == 5 and
                       a['training_released'] is True, 'frozen baseline / late-only fit')
            io.require([{k: v[k] for k in ('name', 'path', 'bytes', 'role')}
                        for v in a['verified_frozen']] == m['frozen_files'], 'ordered five frozen identities')
            io.require([{k: v[k] for k in ('case', 'kind', 'role', 'path', 'sha256')}
                        for v in a['verified_inputs']] == m['scientific_files'], 'ordered nine input identities')
            files = inventory(out)
            io.require(all(files.get(name, 0) > 0 for name in FILES-{'guard_receipt.json'}), 'incomplete report')
    except BaseException as exc:
        fail('WORKER_RECORD_ERROR', exc)

    phase = 'TERMINAL_MEASURE'
    try:
        reason = measure() if owned else None
        if reason:
            terminal_caps.append(reason)
        files = inventory(out) if owned else {}
    except BaseException as exc:
        files = None; fail('FINAL_MEASURE_ERROR', exc)
    record = dict(status=primary or ('TERMINAL_CAP' if terminal_caps else 'COMPLETED'), primary_reason=primary,
                  terminal_caps=terminal_caps, errors=errors, experiment_id=io.EXPERIMENT, run_id=io.RUN,
                  code_commit=code, checkout_commit=checkout, dirty_source_status=dirty,
                  proposal_commit=io.PROPOSAL, execution_references=refs, output=str(out),
                  start_utc=utc, elapsed_seconds=time.monotonic()-started, budget=dict(io.BUDGET),
                  work_reserve_seconds=5, aggregate_sampled_peak_rss_bytes=peak,
                  inventory_before_receipt=files, host=socket.gethostname(), guard_pid=os.getpid(),
                  worker_pid=None if child is None else child.pid, cleanup=cleanup, command=command,
                  launch_attempted=launch_attempted, child_handle_acquired=child is not None,
                  process_ownership_unconfirmed=launch_attempted and child is None,
                  manual_process_inspection_required=launch_attempted and not cleanup['exit_confirmed'],
                  resource_process_coverage=('GUARD_ONLY_POSSIBLE_CHILD_UNOBSERVED'
                                             if launch_attempted and child is None else
                                             'KNOWN_PROCESS_TREE_SAMPLED'),
                  receipt_persisted=False, **flags, confirmation_accessed=False, retry=False,
                  operator_must_verify_actual_approval=True)

    def persist(mode):
        try:
            io.require(owned, 'no write to unowned output')
            record['receipt_persisted'] = True
            with (out/'guard_receipt.json').open(mode) as file:
                json.dump(record, file, indent=2, allow_nan=False)
        except BaseException as exc:
            record['receipt_persisted'] = False
            record['errors'].append(dict(phase='RECEIPT_WRITE', type=type(exc).__name__))
            record['primary_reason'] = record['primary_reason'] or 'RECEIPT_WRITE_ERROR'
            record['status'] = record['primary_reason']

    persist('x')
    try:
        final = inventory(out) if owned else {}
        extra = []
        if sum(final.values()) >= BYTES:
            extra.append('OUTPUT_CAP')
        if time.monotonic()-started >= WALL:
            extra.append('WALL_CAP')
        if record['status'] == 'COMPLETED':
            io.require(FILES <= set(final), 'final inventory')
        if extra:
            record['terminal_caps'] = sorted(set(record['terminal_caps']+extra))
            record['status'] = record['primary_reason'] or 'TERMINAL_CAP'
            if record['receipt_persisted']:
                persist('w')
    except BaseException as exc:
        record['primary_reason'] = record['primary_reason'] or 'POST_RECEIPT_ERROR'
        record['status'] = record['primary_reason']
        record['errors'].append(dict(phase='POST_RECEIPT', type=type(exc).__name__))
        if record['receipt_persisted']:
            persist('w')
    print(json.dumps(record, indent=2, allow_nan=False))
    return int(record['status'] != 'COMPLETED')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--expected-commit', required=True)
    p.add_argument('--approval-ref', required=True)
    p.add_argument('--review-ref', required=True)
    p.add_argument('--allow-real-fit', action='store_true')
    args = p.parse_args()
    refs = dict(approval_ref=args.approval_ref, review_ref=args.review_ref, reviewed_commit=args.expected_commit)
    raise SystemExit(execute(args.out, args.expected_commit, refs, args.allow_real_fit))
