"""Generated scalar tables + virtual cap paths only; never import old runners."""
import argparse
import contextlib
import copy
import csv
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from unittest import mock


def protect(out):
    allowed = str(out.resolve())+os.sep

    def hook(event, args):
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            path = str(Path(os.fsdecode(args[0])).resolve())
            if path.startswith(allowed):
                return
            if ('/local_archive/' in path or
                    Path(path).suffix.lower() in ('.npz', '.mat', '.pt', '.pth', '.h5') or
                    any(s in path for s in ('g5_export_20261013', 'paired_s4_lock_candidate',
                                           'pidl_peak_trajectories', '/u01175', '/u0125'))):
                raise RuntimeError('scientific source access forbidden in generated check')
        if event == 'import' and args[0] in ('s04_raw', 's04_raw_replay', 's04_d0', 's04_g5_features'):
            raise RuntimeError('producer/fit/replay module import forbidden')
    sys.addaudithook(hook)


def rejected(call, classes=(ValueError, RuntimeError, FileExistsError)):
    try:
        call()
    except classes:
        return
    raise AssertionError('expected rejection')


def table(deltas):
    import s04_late_attribution as engine
    require = engine.require
    require(len(deltas) == 81, 'fixture must retain all focus rows')
    rows = []
    for key, n in engine.COUNTS.items():
        for cycle in range(1, n+1):
            stratum = min((cycle-1)//20, 2)
            nstratum = 20 if stratum < 2 else n-40
            delta = deltas[cycle-41] if key == 'u011' and cycle >= 41 else 0.
            rows.append(dict(holdout=key, cycle=cycle, stratum=stratum,
                             cycle_weight=1/(3*nstratum), V0_physical_mse=1024.,
                             V1_physical_mse=1024.+delta))
    string = io.StringIO()
    writer = csv.DictWriter(string, fieldnames=engine.FIELDS)
    writer.writeheader()
    writer.writerows(rows)
    return string.getvalue()


def oracle(deltas):
    return math.sqrt((1024.+math.fsum(deltas)/81)/1024.)


def guard_checks(base):
    """No real waits, memory stress, large file or child processes."""
    import s04_late_attribution_guard as guard
    expected_commit = 'a'*40
    results = {}
    cleanup_cases = ('TERM_TIMEOUT_KILL_EXIT', 'TERM_KILL_TIMEOUT',
                     'WAIT_ERROR_KILL_EXIT', 'SIGNAL_ERRORS')
    scenarios = ('COMPLETED', 'WALL_CAP', 'RSS_CAP', 'OUTPUT_CAP',
                 'CHILD_FAILED', 'INCOMPLETE_OUTPUT', 'INVALID_COMPLETION_RECORD',
                 'GIT_FAILED', 'GIT_TIMEOUT', 'SOURCE_MISMATCH', 'DIRTY_SOURCE',
                 'LOG_OPEN_FAILED', 'LOG_CLOSE_FAILED', 'FINAL_MEASURE_FAILED',
                 'SPAWN_FAILED', 'POLL_FAILED', 'RECEIPT_WRITE_FAILED',
                 'CHILD_FAILED_WITH_FINAL_CAP', *cleanup_cases)
    for reason in scenarios:
        root = base/reason
        root.mkdir()
        out = root/guard.OUTPUT_NAME
        state = dict(started=False, exit=None, waits=0, polls=0)
        killed, launches, git_calls = [], [], []

        class Child:
            pid = 99999971

            @property
            def returncode(self):
                return state['exit']

            def poll(self):
                state['polls'] += 1
                if reason == 'POLL_FAILED':
                    raise RuntimeError('virtual poll failure')
                return state['exit']

            def wait(self, timeout=None):
                assert timeout == .25
                state['waits'] += 1
                if reason in ('TERM_KILL_TIMEOUT', 'SIGNAL_ERRORS') or (
                        reason == 'TERM_TIMEOUT_KILL_EXIT' and state['waits'] == 1):
                    raise subprocess.TimeoutExpired('VIRTUAL_CHILD', timeout)
                if reason == 'WAIT_ERROR_KILL_EXIT' and state['waits'] == 1:
                    raise OSError('virtual wait failure')
                state['exit'] = -15 if state['waits'] == 1 else -9
                return state['exit']

        def git(command, **kwargs):
            git_calls.append(command)
            assert 0 < kwargs['timeout'] <= 2.
            if reason == 'GIT_FAILED':
                raise subprocess.CalledProcessError(128, command)
            if reason == 'GIT_TIMEOUT':
                raise subprocess.TimeoutExpired(command, kwargs['timeout'])
            if command[1] == 'rev-parse':
                return expected_commit+'\n'
            if command[1] == 'status':
                return ' M SENS_tensile/s04_late_attribution_guard.py\n' if reason == 'DIRTY_SOURCE' else ''
            if command[1] == 'diff':
                assert expected_commit in command and '--exit-code' in command
                if reason == 'SOURCE_MISMATCH':
                    raise subprocess.CalledProcessError(1, command)
            return ''

        def spawn(command, **kwargs):
            launches.append(command)
            assert Path(command[1]).name == 's04_late_attribution_checks.py'
            assert Path(command[command.index('--out')+1]) == out
            assert kwargs['env']['CUDA_VISIBLE_DEVICES'] == ''
            assert kwargs['env']['OMP_NUM_THREADS'] == '1'
            if reason == 'SPAWN_FAILED':
                raise OSError('virtual spawn failure')
            state['started'] = True
            state['exit'] = (0 if reason in ('COMPLETED', 'INCOMPLETE_OUTPUT',
                                            'INVALID_COMPLETION_RECORD', 'LOG_CLOSE_FAILED',
                                            'RECEIPT_WRITE_FAILED', 'FINAL_MEASURE_FAILED') else
                             1 if reason in ('CHILD_FAILED', 'CHILD_FAILED_WITH_FINAL_CAP') else None)
            if reason != 'INCOMPLETE_OUTPUT':
                content = ({} if reason == 'INVALID_COMPLETION_RECORD' else
                           dict(status='GENERATED_CHECKS_COMPLETED',
                                scope='GENERATED_ENGINEERING_ONLY',
                                real_data_read=False, fitting_invoked=False))
                (out/'checks.json').write_text(json.dumps(content))
            return Child()

        def process(pid):
            if state['started'] and reason == 'FINAL_MEASURE_FAILED':
                raise OSError('virtual final measurement failure')
            rss = guard.RSS if state['started'] and reason in ('RSS_CAP', *cleanup_cases) else 1024
            return SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=rss),
                                   children=lambda recursive: [])

        actual_size = guard.output_size
        actual_open = Path.open

        def file_open(path, *args, **kwargs):
            if reason == 'LOG_OPEN_FAILED' and path == out/'engineering.log':
                raise OSError('virtual log open failure')
            if reason == 'RECEIPT_WRITE_FAILED' and path == out/'guard_receipt.json':
                raise OSError('virtual receipt write failure')
            file = actual_open(path, *args, **kwargs)
            if reason == 'LOG_CLOSE_FAILED' and path == out/'engineering.log':
                def close():
                    file.close()
                    raise OSError('virtual close failure')
                return SimpleNamespace(close=close)
            return file

        def kill(pid, sig):
            assert pid == Child.pid
            killed.append(sig)
            if reason == 'SIGNAL_ERRORS':
                raise PermissionError('virtual signal failure')

        def size(path):
            # Simulate a threshold at one sample, not a real 5 MiB write.
            if state['started'] and state['exit'] is None and reason == 'OUTPUT_CAP':
                return guard.BYTES
            return actual_size(path)

        captured = io.StringIO()
        with mock.patch.object(guard, 'ENGINEERING', root), \
             mock.patch.object(guard.subprocess, 'check_output', side_effect=git), \
             mock.patch.object(guard.subprocess, 'Popen', side_effect=spawn), \
             mock.patch.object(guard.psutil, 'Process', side_effect=process), \
             mock.patch.object(guard.os, 'killpg', side_effect=kill), \
             mock.patch.object(guard.time, 'monotonic', side_effect=lambda:
                               60. if state['started'] and reason in
                               ('WALL_CAP', 'CHILD_FAILED_WITH_FINAL_CAP') else 0.), \
             mock.patch.object(guard, 'output_size', side_effect=size), \
             mock.patch.object(Path, 'open', file_open), \
             contextlib.redirect_stdout(captured):
            exit_code = guard.execute(out, guard.ATTEMPT, expected_commit)
            # A failed/finished attempt cannot be reused; no second spawn.
            rejected(lambda: guard.execute(out, guard.ATTEMPT, expected_commit))
        console = json.loads(captured.getvalue())
        if reason == 'RECEIPT_WRITE_FAILED':
            assert not (out/'guard_receipt.json').exists()
            receipt = console
            assert receipt['receipt_persisted'] is False
        else:
            receipt = json.loads((out/'guard_receipt.json').read_text())
            assert receipt['receipt_persisted'] is True
        expected = dict(GIT_FAILED='GUARD_EXCEPTION_IDENTITY_CalledProcessError',
                        GIT_TIMEOUT='GUARD_EXCEPTION_IDENTITY_TimeoutExpired',
                        SOURCE_MISMATCH='GUARD_EXCEPTION_IDENTITY_CalledProcessError',
                        DIRTY_SOURCE='GUARD_EXCEPTION_IDENTITY_ValueError',
                        LOG_OPEN_FAILED='GUARD_EXCEPTION_OPEN_LOG_OSError',
                        LOG_CLOSE_FAILED='LOG_CLOSE_ERROR',
                        SPAWN_FAILED='GUARD_EXCEPTION_SPAWN_OSError',
                        POLL_FAILED='GUARD_EXCEPTION_MONITOR_RuntimeError',
                        FINAL_MEASURE_FAILED='FINAL_MEASURE_ERROR',
                        CHILD_FAILED_WITH_FINAL_CAP='CHILD_FAILED').get(reason, reason)
        if reason in cleanup_cases:
            expected = 'RSS_CAP'
        assert receipt['status'] == expected, (reason, receipt)
        assert receipt['primary_reason'] == (None if reason == 'COMPLETED' else expected)
        assert exit_code == (0 if reason == 'COMPLETED' else 1)
        not_launched = reason in ('GIT_FAILED', 'GIT_TIMEOUT', 'SOURCE_MISMATCH',
                                  'DIRTY_SOURCE', 'LOG_OPEN_FAILED')
        assert len(launches) == (0 if not_launched else 1)
        if not_launched or reason == 'SPAWN_FAILED':
            assert receipt['cleanup']['state'] == 'NOT_STARTED'
            assert receipt['worker_pid'] is None and not killed
        elif reason in ('TERM_KILL_TIMEOUT', 'SIGNAL_ERRORS'):
            assert receipt['cleanup']['state'] == 'EXIT_UNCONFIRMED'
            assert receipt['worker_exit'] is None and not receipt['cleanup']['exit_confirmed']
            assert state['waits'] == 2 and killed == [guard.signal.SIGTERM, guard.signal.SIGKILL]
        elif reason in ('TERM_TIMEOUT_KILL_EXIT', 'WAIT_ERROR_KILL_EXIT'):
            assert receipt['cleanup']['state'] == 'KILL_EXITED'
            assert receipt['worker_exit'] == -9 and receipt['cleanup']['exit_confirmed']
            assert killed == [guard.signal.SIGTERM, guard.signal.SIGKILL]
        elif reason in ('WALL_CAP', 'RSS_CAP', 'OUTPUT_CAP', 'POLL_FAILED'):
            assert receipt['worker_exit'] == -15 and receipt['cleanup']['exit_confirmed']
            assert killed == [guard.signal.SIGTERM]
        else:
            assert killed == []
        if reason in ('WALL_CAP', 'CHILD_FAILED_WITH_FINAL_CAP'):
            assert 'WALL_CAP' in receipt['terminal_caps']
        if reason in ('WAIT_ERROR_KILL_EXIT', 'SIGNAL_ERRORS', 'POLL_FAILED'):
            assert receipt['cleanup']['errors']
        results[reason] = dict(virtual_only=True, real_child_processes=0,
                              mock_launches=len(launches), expected_status=expected)
    assert guard.cap_reason(60., 0, 0) == 'WALL_CAP'
    assert guard.cap_reason(0, guard.RSS, 0) == 'RSS_CAP'
    assert guard.cap_reason(0, 0, guard.BYTES-guard.RESERVE) == 'OUTPUT_CAP'
    assert guard.cap_reason(59., guard.RSS-1, guard.BYTES-guard.RESERVE-1) is None
    rejected(lambda: guard.execute(base/'not_an_enabled_destination', guard.ATTEMPT, expected_commit))
    rejected(lambda: guard.execute(base/guard.OUTPUT_NAME, 'WRONG_ATTEMPT', expected_commit))
    with mock.patch.object(guard, 'ENGINEERING', base):
        rejected(lambda: guard.execute(base/guard.OUTPUT_NAME, guard.ATTEMPT, 'not-a-commit'))
    assert not (base/guard.OUTPUT_NAME).exists()
    return results


def run(out):
    protect(out)  # Before importing either implementation, including guard.
    import s04_late_attribution as engine
    import s04_late_attribution_guard as guard
    assert not (Path(__file__).resolve().parents[1]/'local_archive').exists()
    # Verify the audit hook itself without opening any existing scientific file.
    rejected(lambda: Path('/never/local_archive/forbidden.csv').read_text())
    rejected(lambda: Path('/never/forbidden.npz').read_bytes())
    checks = []
    cases = dict(single_majority=[256.]+[1.]*40+[-.5]*40,
                 multi_majority=[1.]*41+[-.5]*40,
                 multi_minority_40=[1.]*40+[-.5]*41,
                 multi_minority=[1.]*10+[-.25]*71,
                 cancellation=[4., 4., -8.]+[0.]*78,
                 all_zero=[0.]*81,
                 below_identifiability=[1e-8]*81,
                 all_improve=[-1.]*81)
    results = {}
    for name, deltas in cases.items():
        rows = engine.parse_csv(table(deltas))
        before = copy.deepcopy(rows)
        late, summary, cumulative = engine.describe(rows, oracle(deltas))
        assert rows == before and len(late) == 81
        assert sum(summary['counts'].values()) == 81
        assert abs(summary['S_net']-math.fsum(deltas)) <= summary['sum_tau']
        assert summary['late_mean_MSE_difference'] == summary['S_net']/81
        if name == 'single_majority':
            assert summary['k50'] == 1 and summary['counts']['harm'] == 41
            assert summary['branch'] == 'PROPOSE_SINGLE_STATE_PROVENANCE_CHECK'
            assert summary['S_plus'] == 296 and summary['S_minus'] == 20
            assert summary['contributing_cycles'] == [41]
            assert summary['max_positive'] == dict(cycle=41, D=256.)
        elif name == 'multi_majority':
            assert summary['k50'] == 21 and summary['counts']['harm'] == 41
            assert summary['contributing_cycles'] == list(range(41, 62))
            assert summary['branch'] == 'PROPOSE_PHASE_OBJECTIVE_REPRESENTATION_QUESTIONS'
        elif name == 'multi_minority':
            assert summary['k50'] == 5 and summary['counts']['harm'] == 10
            assert summary['branch'] == 'PROPOSE_CONTRIBUTING_STATES_PROVENANCE_CHECK'
        elif name == 'multi_minority_40':
            assert summary['k50'] == 20 and summary['counts']['harm'] == 40
            assert summary['branch'] == 'PROPOSE_CONTRIBUTING_STATES_PROVENANCE_CHECK'
        elif name == 'cancellation':
            assert summary['S_plus'] == summary['S_minus'] == 8
            assert summary['S_net'] == 0 and summary['k50'] == 1
        else:
            assert summary['k50'] is None and not cumulative
            assert summary['status'] == 'INCONCLUSIVE'
        results[name] = {k: summary[k] for k in ('k50', 'counts', 'branch', 'S_plus', 'S_minus', 'S_net')}
    checks.append('all four decision branches, deterministic exact ties, signed decomposition, immutable rows')
    deltas = [1.]*41+[-.5]*40
    text = table(deltas)
    rows = engine.parse_csv(text)
    expected = oracle(deltas)
    baseline = engine.describe(rows, expected)[1]
    assert engine.describe(list(reversed(rows)), expected)[1] == baseline
    altered = copy.deepcopy(rows)
    for r in altered:
        if r['holdout'] != 'u011':
            r['V0_physical_mse'], r['V1_physical_mse'] = '9', '900'
    assert engine.describe(altered, expected)[1] == baseline
    checks.append('complete-prefix validation independent of input order; no other-case attribution')
    # Threshold equality with m0=0 makes D=tau exactly representable as the
    # same stored float. This row need not identify the whole baseline.
    ties = copy.deepcopy(rows)
    for cycle, value in ((41, 1e-10), (42, 2e-10)):
        row = next(r for r in ties if r['holdout'] == 'u011' and r['cycle'] == str(cycle))
        row['V0_physical_mse'], row['V1_physical_mse'] = '0', repr(value)
    values = engine.validate(ties)
    tie_ratio = math.sqrt(math.fsum(r['V1_physical_mse']/81 for r in values))/math.sqrt(
        math.fsum(r['V0_physical_mse']/81 for r in values))
    late, _, _ = engine.describe(ties, tie_ratio)
    assert late[0]['numeric_class'] == 'tie' and late[1]['numeric_class'] == 'harm'
    checks.append('tau equality is tie; above tau is harm')
    # Exact identifiability equality: 80 zero-baseline rows contribute 81*tau
    # (first row contributes 2*tau). One tiny positive baseline identifies the
    # aggregate denominator without changing its rounded tau=1e-10.
    boundary = copy.deepcopy(rows)
    for row in boundary:
        if row['holdout'] == 'u011' and int(row['cycle']) >= 41:
            row['V0_physical_mse'], row['V1_physical_mse'] = '0', '1e-10'
            if row['cycle'] == '41':
                row['V1_physical_mse'] = '2e-10'
            if row['cycle'] == '121':
                row['V0_physical_mse'] = row['V1_physical_mse'] = '1e-20'
    boundary_late = engine.validate(boundary)
    boundary_ratio = math.sqrt(math.fsum(r['V1_physical_mse']/81 for r in boundary_late))/math.sqrt(
        math.fsum(r['V0_physical_mse']/81 for r in boundary_late))
    _, boundary_summary, boundary_curve = engine.describe(boundary, boundary_ratio)
    assert boundary_summary['S_plus'] == boundary_summary['sum_tau']
    assert boundary_summary['k50'] is None and not boundary_curve
    assert boundary_summary['branch'] == 'STOP_UNIDENTIFIABLE_POSITIVE_EXCESS'
    checks.append('S_plus exactly equals sum_tau stops; paired n_harm=40/41 decisions')
    for field, value in (('holdout', 'u01175'), ('cycle', '0'), ('cycle', '122'),
                         ('cycle', '41.0'), ('stratum', '2'), ('cycle_weight', '.5'),
                         ('V0_physical_mse', '-1'), ('V1_physical_mse', 'nan'),
                         ('V0_physical_mse', 'inf'), ('V1_physical_mse', '-inf')):
        bad = copy.deepcopy(rows)
        bad[0][field] = value
        rejected(lambda: engine.describe(bad, expected))
    for bad in (rows[:-1], rows+[rows[0]], [rows[0]]+rows[:-1]):
        rejected(lambda: engine.describe(bad, expected))
    bad = copy.deepcopy(rows)
    del bad[0]['cycle_weight']
    rejected(lambda: engine.describe(bad, expected))
    bad = copy.deepcopy(rows)
    for row in bad:
        row['V0_physical_mse'] = row['V1_physical_mse'] = '0'
    rejected(lambda: engine.describe(bad, 1.))
    rejected(lambda: engine.describe(rows, expected+2e-12))
    rejected(lambda: engine.describe(rows, float('nan')))
    rejected(lambda: engine.parse_csv('holdout,cycle\nu011,41\n'))
    rejected(lambda: engine.parse_csv(text.replace('holdout,cycle', 'holdout,holdout', 1)))
    checks.append('bad fields, nonfinite/negative values, coverage, duplicate, strata, weights, ratio and baseline reject')
    edge = [0.]*80+[100.]
    _, summary, _ = engine.describe(engine.parse_csv(table(edge)), oracle(edge))
    assert summary['contributing_cycles'] == [121] and summary['C121_provenance_check_proposed']
    checks.append('C121 contribution flagged only for proposed provenance check, not exclusion or cause')
    # Generated CSV disk roundtrip, before/after metadata and contents.
    source = out/'GENERATED_ONLY.csv'
    source.write_text(text)
    source.chmod(0o444)
    stat = source.stat()
    saved = (stat.st_size, stat.st_mtime_ns, stat.st_mode)
    late, summary, cumulative = engine.describe(engine.parse_csv(source.read_text()), expected)
    engine.report(late, summary, cumulative, out/'generated_report', generated=True)
    rejected(lambda: engine.report(late, summary, cumulative, out/'forbidden_report', generated=False))
    assert not (out/'forbidden_report').exists()
    stat = source.stat()
    assert (stat.st_size, stat.st_mtime_ns, stat.st_mode) == saved
    # read_text() normalises CSV CRLF into LF; compare the stored bytes, not
    # newline-translated text, when checking source immutability.
    assert source.read_bytes() == text.encode('utf-8')
    assert (out/'generated_report/diagnostic.png').stat().st_size > 1000
    assert len(engine.parse_csv(source.read_text())) == 357
    with (out/'generated_report/diagnostic.csv').open() as file:
        assert len(list(csv.DictReader(file))) == 81
    checks.append('generated disk CSV read-only preserved; 81-row report and labelled two-panel figure')
    caps = guard_checks(out)
    checks.append('virtual guard failure/cleanup/receipt paths; exact caps; no retries; reviewed identity; CPU-only child')
    assert not any(n in sys.modules for n in ('s04_raw', 's04_raw_replay', 's04_d0', 's04_g5_features'))
    record = dict(status='GENERATED_CHECKS_COMPLETED', scope='GENERATED_ENGINEERING_ONLY',
                  checks=checks, cases=results, virtual_guard=caps,
                  real_data_read=False, fitting_invoked=False,
                  limitations=['not real analysis', 'no real source adapter',
                               'caps sampled, not hard OS limit', 'mock cap paths are not stress tests'])
    with (out/'checks.json').open('x') as file:
        json.dump(record, file, indent=2, allow_nan=False)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.out.resolve())
