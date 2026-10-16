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
    results = {}
    for reason in ('COMPLETED', 'WALL_CAP', 'RSS_CAP', 'OUTPUT_CAP',
                   'CHILD_FAILED', 'INCOMPLETE_OUTPUT'):
        root = base/reason
        root.mkdir()
        out = root/'late-attribution-20261016-9984226'
        state = dict(started=False, exit=None)
        killed, launches = [], []

        class Child:
            pid = 99999971

            @property
            def returncode(self):
                return state['exit']

            def poll(self):
                return state['exit']

            def wait(self, timeout=None):
                state['exit'] = -15
                return -15

        def spawn(command, **kwargs):
            launches.append(command)
            assert Path(command[1]).name == 's04_late_attribution_checks.py'
            assert Path(command[command.index('--out')+1]) == out
            assert kwargs['env']['CUDA_VISIBLE_DEVICES'] == ''
            assert kwargs['env']['OMP_NUM_THREADS'] == '1'
            state['started'] = True
            state['exit'] = (0 if reason in ('COMPLETED', 'INCOMPLETE_OUTPUT') else
                             1 if reason == 'CHILD_FAILED' else None)
            if reason != 'INCOMPLETE_OUTPUT':
                (out/'checks.json').write_text('{}')
            return Child()

        def process(pid):
            rss = guard.RSS if state['started'] and reason == 'RSS_CAP' else 1024
            return SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=rss),
                                   children=lambda recursive: [])

        actual_size = guard.output_size

        def size(path):
            # Simulate a threshold at one sample, not a real 5 MiB write.
            if state['started'] and state['exit'] is None and reason == 'OUTPUT_CAP':
                return guard.BYTES
            return actual_size(path)

        with mock.patch.object(guard, 'ENGINEERING', root), \
             mock.patch.object(guard.subprocess, 'check_output', return_value='MOCK\n'), \
             mock.patch.object(guard.subprocess, 'Popen', side_effect=spawn), \
             mock.patch.object(guard.psutil, 'Process', side_effect=process), \
             mock.patch.object(guard.os, 'killpg', side_effect=lambda pid, sig: killed.append(pid)), \
             mock.patch.object(guard.time, 'monotonic', side_effect=lambda:
                               60. if state['started'] and reason == 'WALL_CAP' else 0.), \
             mock.patch.object(guard, 'output_size', side_effect=size), \
             contextlib.redirect_stdout(io.StringIO()):
            exit_code = guard.execute(out)
            # A failed/finished attempt cannot be reused; no second spawn.
            rejected(lambda: guard.execute(out))
        receipt = json.loads((out/'guard_receipt.json').read_text())
        expected = 'FINAL_OUTPUT_OR_WALL_CAP' if reason == 'WALL_CAP' else reason
        assert receipt['status'] == expected
        assert exit_code == (0 if reason == 'COMPLETED' else 1)
        assert len(launches) == 1
        if reason.endswith('_CAP'):
            assert killed == [Child.pid] and receipt['worker_exit'] == -15
        else:
            assert killed == []
        results[reason] = dict(virtual_only=True, real_child_processes=0, mock_launches=1)
    assert guard.cap_reason(60., 0, 0) == 'WALL_CAP'
    assert guard.cap_reason(0, guard.RSS, 0) == 'RSS_CAP'
    assert guard.cap_reason(0, 0, guard.BYTES-guard.RESERVE) == 'OUTPUT_CAP'
    assert guard.cap_reason(59., guard.RSS-1, guard.BYTES-guard.RESERVE-1) is None
    rejected(lambda: guard.execute(base/'not_an_enabled_destination'))
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
    assert source.read_text() == text
    assert (out/'generated_report/diagnostic.png').stat().st_size > 1000
    assert len(engine.parse_csv(source.read_text())) == 357
    assert len(list(csv.DictReader((out/'generated_report/diagnostic.csv').open()))) == 81
    checks.append('generated disk CSV read-only preserved; 81-row report and labelled two-panel figure')
    caps = guard_checks(out)
    checks.append('six virtual guard paths, exact cap boundaries, no retries, fixed destination and CPU-only child')
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
