"""Single mock IO/handoff suite; no real archive reads, fields or figures."""
import argparse
import contextlib
import copy
import csv
import io
import json
import os
from pathlib import Path
import stat
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
            if '/local_archive/' in path or Path(path).suffix.lower() in ('.npz', '.mat', '.pt', '.pth', '.h5'):
                raise RuntimeError('real source open forbidden in adapter mock')
        if event == 'import' and args[0] in ('s04_raw', 's04_raw_replay', 's04_d0', 's04_g5_features'):
            raise RuntimeError('old producer/replay import forbidden')
    sys.addaudithook(hook)


def rejected(call, message=None):
    try:
        call()
    except (ValueError, RuntimeError, KeyError, OSError) as exc:
        if message is not None:
            assert message in str(exc), (message, str(exc))
        return
    raise AssertionError('expected rejection')


class MemoryIO:
    def __init__(self, texts):
        self.texts = copy.deepcopy(texts)
        self.tokens = {p: (1, i+1, stat.S_IFREG | 0o444, len(t.encode('utf-8')), 1000+i)
                       for i, (p, t) in enumerate(self.texts.items())}
        self.calls = []
        self.mutate_after_csv = False

    def metadata(self, path):
        assert path in self.texts
        self.calls.append(('stat', path))
        return self.tokens[path]

    def read(self, path, before):
        assert path in self.texts and self.tokens[path] == before
        self.calls.append(('read', path))
        import s04_late_adapter as adapter
        if self.mutate_after_csv and path == adapter.CSV:
            fields = list(self.tokens[path])
            fields[4] += 1
            self.tokens[path] = tuple(fields)
        return self.texts[path]

    def change_json(self, path, change):
        value = json.loads(self.texts[path])
        change(value)
        self.texts[path] = json.dumps(value)
        fields = list(self.tokens[path])
        fields[3] = len(self.texts[path].encode('utf-8'))
        self.tokens[path] = tuple(fields)


def fixture():
    import s04_late_adapter as a
    import s04_late_attribution as core
    string = io.StringIO()
    writer = csv.DictWriter(string, fieldnames=core.FIELDS)
    writer.writeheader()
    for key, n in core.COUNTS.items():
        for cycle in range(1, n+1):
            s = min((cycle-1)//20, 2)
            writer.writerow(dict(holdout=key, cycle=cycle, stratum=s,
                                 cycle_weight=1/(3*(20 if s < 2 else n-40)),
                                 V0_physical_mse=10., V1_physical_mse=12.1))
    summary = dict(run_id='S04-E021-REPLAY-R001', code_commit=a.REPLAY_COMMIT,
                   status='REPLAY_ARITHMETIC_MATCH', original_verdict='DIRECTIONAL_DEVELOPMENT_GAIN',
                   fitting_invoked=False, folds=[dict(holdout=key, stratum_mse=[[10., 12.1]]*3)
                                                for key in core.COUNTS])
    # Explicit MOCK selectors, NOT an assertion about the real JSON structure.
    values = dict(run_id='S04-E021-REPLAY-R001', runtime_commit=a.REPLAY_COMMIT,
                  rows=357, counts=core.COUNTS, late_ratio=1.1)
    verification = dict(MOCK_SCHEMA_ONLY=values, independent_evidence_review='NOT_YET_REQUESTED')
    binding = {k: ['MOCK_SCHEMA_ONLY', k] for k in values}
    texts = {a.CSV: string.getvalue(), a.SUMMARY: json.dumps(summary),
             a.VERIFICATION: json.dumps(verification), a.INVENTORY: '{}'}
    mem = MemoryIO(texts)
    audit = dict(status='VERIFIED_SAVED_OUTPUTS', run_id='S04-E021-R001', code_commit=a.FIT_COMMIT,
                 frozen_files=[dict(path=a.CSV, bytes=mem.tokens[a.CSV][3], mtime_ns=mem.tokens[a.CSV][4]),
                               dict(path='/FORBIDDEN_ARRAY.npz', bytes=999, mtime_ns=0)])
    mem.change_json(a.INVENTORY, lambda d: d.update(audit))
    return mem, binding


def run(out):
    protect(out)
    import s04_late_adapter as a
    import s04_late_adapter_guard as job
    code = 'a'*40
    attempt = job.ATTEMPT
    output = str(out/'MOCK_OUTPUT_NOT_CREATED')
    grant = dict(version=1, action='four_source_readonly_handoff', domain='MOCK_ONLY',
                 code_commit=code, plan_commit=a.core.PLAN_COMMIT, attempt=attempt, output=output,
                 sources=list(a.SOURCES), budget=a.BUDGET, fit=False, confirmation=False,
                 engineering_only=True, user_approved_real_execution=False)
    mem, binding = fixture()

    def acquire(reader=mem, g=grant, b=binding):
        return a.snapshot(reader, grant=g, code_commit=code, attempt=attempt, output=output,
                          domain='MOCK_ONLY', binding=b, expected_ratio=1.1)

    checks = []
    data = acquire()
    assert len(data['rows']) == 357 and len(data['background']) == 3
    assert {r['holdout'] for r in data['background']} == {'u0115', 'u012', 'u013'}
    assert {p for _, p in mem.calls} == set(a.SOURCES)
    assert [p for op, p in mem.calls if op == 'read'] == [a.INVENTORY, a.VERIFICATION, a.SUMMARY, a.CSV]
    assert not Path(output).exists() and data['real_data_read'] is False
    checks.append('four logical sources only; 357 rows; three saved-background copies; no analysis/output writes')

    for key, value in (('code_commit', 'b'*40), ('plan_commit', 'WRONG'), ('attempt', 'WRONG'),
                       ('output', output+'WRONG'), ('sources', [a.CSV]), ('budget', {}),
                       ('domain', 'REAL_SAVED_SCALARS'), ('fit', True), ('confirmation', True),
                       ('engineering_only', False), ('user_approved_real_execution', True)):
        reader, _ = fixture()
        bad = copy.deepcopy(grant)
        bad[key] = value
        rejected(lambda: acquire(reader, bad))
        assert not reader.calls
    reader, _ = fixture()
    rejected(lambda: acquire(reader, grant, None), 'SCHEMA_BINDING_REQUIRED')
    assert not reader.calls
    with mock.patch.object(a, 'ReadOnlyIO', side_effect=AssertionError('no real IO construction')):
        rejected(lambda: a.acquire_real(grant={}, code_commit=code, env={}, auth_path='unused',
                                        output=a.REAL_OUTPUT, actual_parent=123), 'SCHEMA_BINDING_REQUIRED')
    checks.append('grant drift and missing schema reject before IO; real entry remains closed')

    # A valid mock grant must not enable the native reader, even indirectly
    # through a subclass. Bomb callbacks prove rejection precedes any source IO.
    class NativeSubclass(a.ReadOnlyIO):
        pass
    for reader_type in (a.ReadOnlyIO, NativeSubclass):
        reader = reader_type()
        with mock.patch.object(reader, 'metadata', side_effect=AssertionError('unexpected source stat')) as meta, \
             mock.patch.object(reader, 'read', side_effect=AssertionError('unexpected source read')) as read:
            rejected(lambda: acquire(reader), 'MOCK_ONLY forbids native source reader')
            meta.assert_not_called()
            read.assert_not_called()
    checks.append('mock grant rejects native reader and subclass before any source metadata/read')

    caller = out/'mock_caller'
    caller.mkdir()
    with contextlib.chdir(caller):
        handoff = a.prepare_handoff('MOCK_AUTH_NOT_A_REAL_APPROVAL.json', 'MOCK_CHILD_OUTPUT',
                                    parent_pid=123, attempt=attempt, code_commit=code)
    assert handoff['authorization'] == str(caller/'MOCK_AUTH_NOT_A_REAL_APPROVAL.json')
    handoff_grant = dict(grant, output=handoff['output'])
    read_auth_calls = []

    def read_auth(path):
        read_auth_calls.append(path)
        assert path == handoff['authorization']
        return json.dumps(handoff_grant)

    def child(env=handoff['env'], path=handoff['authorization'], parent=123):
        return a.decode_child_grant(path, handoff['output'], env, actual_parent=parent,
                                    attempt=attempt, code_commit=code, read_auth=read_auth)
    with contextlib.chdir(out):
        decoded = child()
        assert decoded == handoff_grant
        child_reader, child_binding = fixture()
        child_data = a.snapshot(child_reader, grant=decoded, code_commit=code, attempt=attempt,
                                output=handoff['output'], domain='MOCK_ONLY',
                                binding=child_binding, expected_ratio=1.1)
        assert len(child_data['rows']) == 357
    assert read_auth_calls == [handoff['authorization']]
    read_auth_calls.clear()
    for field in handoff['env']:
        bad = dict(handoff['env'])
        bad[field] = 'WRONG'
        rejected(lambda: child(bad), 'handoff')
    rejected(lambda: child(path='relative.json'), 'absolute')
    rejected(lambda: child(parent=124), 'handoff')
    assert not read_auth_calls
    assert not Path(handoff['authorization']).exists() and not Path(handoff['output']).exists()
    checks.append('absolute parent/child authorization path across cwd; every env/PID mismatch rejects before auth read')

    for kind in ('CSV_WRITABLE', 'SYMLINK', 'SIZE_DRIFT', 'MTIME_DRIFT', 'DUPLICATE_CSV',
                 'AUDIT_ID', 'VERIFY_ID', 'VERIFY_COUNT', 'VERIFY_RATIO', 'MISSING_SELECTOR',
                 'SUMMARY_ID', 'SUMMARY_FOLD', 'SUMMARY_NEGATIVE', 'SUMMARY_NAN', 'POST_READ_DRIFT'):
        reader, b = fixture()
        if kind in ('CSV_WRITABLE', 'SYMLINK'):
            t = list(reader.tokens[a.CSV])
            t[2] = stat.S_IFREG | 0o644 if kind == 'CSV_WRITABLE' else stat.S_IFLNK | 0o777
            reader.tokens[a.CSV] = tuple(t)
        elif kind in ('SIZE_DRIFT', 'MTIME_DRIFT'):
            def change(d):
                d['frozen_files'][0]['bytes' if kind == 'SIZE_DRIFT' else 'mtime_ns'] += 1
            reader.change_json(a.INVENTORY, change)
        elif kind == 'DUPLICATE_CSV':
            reader.change_json(a.INVENTORY, lambda d: d['frozen_files'].append(dict(d['frozen_files'][0])))
        elif kind == 'AUDIT_ID':
            reader.change_json(a.INVENTORY, lambda d: d.update(code_commit='WRONG'))
        elif kind in ('VERIFY_ID', 'VERIFY_COUNT', 'VERIFY_RATIO'):
            key, value = {'VERIFY_ID': ('runtime_commit', 'WRONG'),
                          'VERIFY_COUNT': ('rows', 358), 'VERIFY_RATIO': ('late_ratio', 1.2)}[kind]
            reader.change_json(a.VERIFICATION, lambda d: d['MOCK_SCHEMA_ONLY'].update({key: value}))
        elif kind == 'MISSING_SELECTOR':
            b['rows'] = ['MISSING']
        elif kind == 'SUMMARY_ID':
            reader.change_json(a.SUMMARY, lambda d: d.update(status='WRONG'))
        elif kind == 'SUMMARY_FOLD':
            reader.change_json(a.SUMMARY, lambda d: d['folds'].pop())
        elif kind in ('SUMMARY_NEGATIVE', 'SUMMARY_NAN'):
            reader.change_json(a.SUMMARY, lambda d: d['folds'][0]['stratum_mse'][2].__setitem__(0,
                               -1 if kind == 'SUMMARY_NEGATIVE' else float('nan')))
        elif kind == 'POST_READ_DRIFT':
            reader.mutate_after_csv = True
        rejected(lambda: acquire(reader, grant, b))
        assert all(path in a.SOURCES for _, path in reader.calls)
    rejected(lambda: a.strict_json('{"x":1,"x":2}'), 'duplicate')
    rejected(lambda: a.strict_json('{"x":Infinity}'), 'nonfinite')
    checks.append('15 mocked metadata/identity/numeric/schema/drift rejections; duplicate/nonfinite JSON reject')

    for key in ('run_id', 'code_commit'):
        for mode in ('WRONG', 'MISSING'):
            reader, b = fixture()
            def change(d):
                if mode == 'WRONG':
                    d[key] = 'WRONG'
                else:
                    d.pop(key)
            reader.change_json(a.SUMMARY, change)
            rejected(lambda: acquire(reader, grant, b))
            assert ('read', a.CSV) not in reader.calls
            assert all(path in a.SOURCES for _, path in reader.calls)
    checks.append('summary own run/commit wrong or missing: four rejections before CSV read')

    # POSIX descriptor primitive exercised with a fake fd and no real opens.
    t = mem.tokens[a.CSV]
    s = SimpleNamespace(st_dev=t[0], st_ino=t[1], st_mode=t[2], st_size=t[3], st_mtime_ns=t[4])
    flags = []
    chunks = [mem.texts[a.CSV].encode('utf-8'), b'']
    closed = []
    class FakePath:
        def lstat(self):
            return s
    def fake_open(path, mode):
        assert path == a.CSV and mode == os.O_RDONLY | os.O_NOFOLLOW
        flags.append(mode)
        return 987654
    reader = a.ReadOnlyIO()
    with mock.patch.object(reader, '_path', return_value=FakePath()), \
         mock.patch.object(a.os, 'open', side_effect=fake_open), \
         mock.patch.object(a.os, 'fstat', return_value=s), \
         mock.patch.object(a.os, 'read', side_effect=lambda fd, size: chunks.pop(0)), \
         mock.patch.object(a.os, 'close', side_effect=lambda fd: closed.append(fd)):
        assert reader.read(a.CSV, t) == mem.texts[a.CSV]
    assert len(flags) == 1 and closed == [987654]
    rejected(lambda: a.ReadOnlyIO()._path('/NOT_ALLOWED.csv'), 'allowlist')
    with mock.patch.object(Path, 'resolve', return_value=Path('/ALIASED')):
        rejected(lambda: a.ReadOnlyIO()._path(a.CSV), 'symlink/alias')
    checks.append('O_RDONLY|O_NOFOLLOW, descriptor/path token and close mocked; unlisted/aliased paths reject')

    # All OS operations below are fake. No native source is opened or statted.
    changed = SimpleNamespace(**vars(s))
    changed.st_mtime_ns += 1
    changed_token = a.token(changed)
    payload = mem.texts[a.CSV].encode('utf-8')
    fd_cases = (
        ('OPEN_ERROR', OSError('MOCK_OPEN_ERROR'), [], [], [t, t], 'MOCK_OPEN_ERROR', 0, 0),
        ('FD_MISMATCH', None, [changed], [], [t, t], 'descriptor/path mismatch', 1, 0),
        ('FSTAT_ERROR', None, [OSError('MOCK_FSTAT_ERROR')], [], [t, t], 'MOCK_FSTAT_ERROR', 1, 0),
        ('READ_ERROR', None, [s], [OSError('MOCK_READ_ERROR')], [t, t], 'MOCK_READ_ERROR', 1, 1),
        ('FD_DRIFT', None, [s, changed], [payload, b''], [t, t], 'descriptor changed', 1, 2),
        ('SIZE_MISMATCH', None, [s], [b'x', b''], [t, t], 'size/read mismatch', 1, 2),
        ('PATH_DRIFT', None, [s, s], [payload, b''], [t, changed_token], 'path changed', 1, 2),
    )
    fd_checked = []
    for name, open_error, fstats, blocks, metadata, reason, nclose, nread in fd_cases:
        reader = a.ReadOnlyIO()
        with mock.patch.object(reader, '_path', return_value=FakePath()), \
             mock.patch.object(reader, 'metadata', side_effect=metadata) as meta, \
             mock.patch.object(a.os, 'open', return_value=987654, side_effect=open_error) as opened, \
             mock.patch.object(a.os, 'fstat', side_effect=fstats) as fstat_call, \
             mock.patch.object(a.os, 'read', side_effect=blocks) as read, \
             mock.patch.object(a.os, 'close') as close:
            rejected(lambda: reader.read(a.CSV, t), reason)
            opened.assert_called_once_with(a.CSV, os.O_RDONLY | os.O_NOFOLLOW)
            assert close.call_count == nclose and read.call_count == nread, name
            assert fstat_call.call_count == len(fstats), name
            assert meta.call_count == (2 if name == 'PATH_DRIFT' else 1), name
            if nclose:
                close.assert_called_once_with(987654)
            for call in fstat_call.call_args_list:
                assert call.args == (987654,), name
            for call in read.call_args_list:
                assert call.args[0] == 987654 and 0 < call.args[1] <= 65536, name
        fd_checked.append(name)
    checks.append('seven fake-fd error/drift branches; opened descriptors close once, open failure never closes')
    assert a.REAL_VERIFICATION_BINDING is None
    assert not any(k in sys.modules for k in ('s04_raw', 's04_raw_replay', 's04_d0', 's04_g5_features'))
    record = dict(status='GENERATED_CHECKS_COMPLETED', scope='GENERATED_ENGINEERING_ONLY',
                  adapter_mock_checks=checks, fd_error_cases=fd_checked,
                  real_data_read=False, fitting_invoked=False,
                  real_verification_binding='UNBOUND', real_ready=False,
                  sources_are_logical_names_only=list(a.SOURCES),
                  limits='mock IO is not actual archive validation, POSIX fault/stress test or real execution approval')
    with (out/'checks.json').open('x') as file:
        json.dump(record, file, indent=2, allow_nan=False)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.out.resolve())
