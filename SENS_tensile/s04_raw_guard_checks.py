"""Mock guard fault injection: no child process, allocation, source or fitting."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest import mock

import s04_raw_guard as guard


def check_authorization_handoff(base):
    """Exercise real-mode path plumbing with a mocked validator and children only."""
    base = base.resolve()
    base.mkdir(parents=True, exist_ok=False)
    caller = base/'caller_outside_repo'; caller.mkdir()
    relative = Path('approval_NOT_CREATED.json')
    expected = caller/relative
    out = base/'MOCK_AUTH_HANDOFF'
    root = Path(guard.__file__).resolve().parents[1]
    assert caller != root and not expected.exists()
    validated = []; launched = []

    def authorize(path, output):
        assert Path.cwd() == caller and path == expected and path.is_absolute()
        assert output == out and not expected.exists()
        validated.append(str(path))
        return dict(run_id=out.name)

    def spawn(command, **kwargs):
        assert validated == [str(expected)]
        assert kwargs['cwd'] == root
        assert kwargs['env']['RAW_AUTHORIZATION'] == str(expected)
        if not launched:
            i = command.index('--authorization')
            assert command[i+1] == str(expected)
            # Model the child resolving argv after its cwd has changed.
            assert (kwargs['cwd']/command[i+1]).resolve() == expected
            out.mkdir()
        else:
            assert Path(command[1]).name == 's04_raw_report.py'
        launched.append(dict(command=command, cwd=str(kwargs['cwd']),
                             authorization_env=kwargs['env']['RAW_AUTHORIZATION']))
        return SimpleNamespace(pid=99999992+len(launched), poll=lambda: 0, returncode=0)

    fake_source = SimpleNamespace(authorization=authorize)
    proc = SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=1024))
    with contextlib.chdir(caller), \
         mock.patch.dict(sys.modules, {'s04_raw': fake_source}), \
         mock.patch.object(guard.subprocess, 'check_output', return_value='MOCK\n'), \
         mock.patch.object(guard.subprocess, 'Popen', side_effect=spawn), \
         mock.patch.object(guard.psutil, 'Process', return_value=proc), \
         contextlib.redirect_stdout(io.StringIO()):
        code = guard.execute(out, auth_path=relative)
    record = json.loads((base/(out.name+'_guard_receipt.json')).read_text())
    assert code == 0 and record['status'] == 'COMPLETED'
    assert len(launched) == 2 and not expected.exists()
    result = dict(status='PASS', mock_only=True, caller_cwd=str(caller),
                  parent_authorization=validated, child_handoffs=launched,
                  authorization_artifact_created=False, real_child_processes=0,
                  actual_inputs_opened=False, actual_fit=False, actual_score=False,
                  virtual_guard_receipts_only=True)
    (base/'authorization_handoff_receipt.json').write_text(json.dumps(result, indent=2))
    return result


def check(base):
    base.mkdir(parents=True, exist_ok=False)
    result = {}
    for reason in ('WALL_CAP', 'RSS_CAP', 'OUTPUT_CAP'):
        out = base/('RAW_SYNTHETIC_MOCK_'+reason)
        state = dict(started=False, exit_code=None); killed = []
        child_pid = 99999991  # virtual PID only; killpg is mocked throughout.
        class Child:
            pid = child_pid
            def poll(self): return state['exit_code']
            def wait(self, timeout=None): state['exit_code'] = -15; return -15
        def spawn(*args, **kwargs):
            state['started'] = True; out.mkdir(); (out/'payload_for_cap').write_bytes(b'x')
            return Child()
        def process(pid):
            rss = (2*1024**3+1) if pid == child_pid and reason == 'RSS_CAP' else 10*1024**2
            return SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=rss), children=lambda recursive: [])
        original_stat = Path.stat
        def stat(path, *args, **kwargs):
            value = original_stat(path, *args, **kwargs)
            if path.name == 'payload_for_cap' and reason == 'OUTPUT_CAP':
                fields = list(value); fields[6] = 101*1024**2
                return os.stat_result(fields)
            return value
        def clock(): return 301. if state['started'] and reason == 'WALL_CAP' else 0.
        with mock.patch.object(guard.subprocess, 'check_output', return_value='MOCK\n'), \
             mock.patch.object(guard.subprocess, 'Popen', side_effect=spawn), \
             mock.patch.object(guard.psutil, 'Process', side_effect=process), \
             mock.patch.object(guard.os, 'killpg', side_effect=lambda pid, sig: killed.append((pid, sig))), \
             mock.patch.object(guard.time, 'monotonic', side_effect=clock), \
             mock.patch.object(Path, 'stat', stat), contextlib.redirect_stdout(io.StringIO()):
            code = guard.execute(out, synthetic=True)
        record = json.loads((base/(out.name+'_guard_receipt.json')).read_text())
        assert code == 1 and record['status'] == reason
        assert killed and all(pid == child_pid for pid, _ in killed)
        assert record['children'][0]['exit_code'] == -15 and len(record['children']) == 1
        assert not (base/(out.name+'_fit_guard_receipt.json')).exists()
        result[reason] = dict(stopped_own_virtual_child=True, report_not_launched=True,
                              complete_receipt=True, real_child_processes=0)
    result.update(status='PASS', synthetic_mock_only=True, actual_fit=False, actual_score=False)
    (base/'mock_guard_receipt.json').write_text(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--authorization-handoff-only', action='store_true')
    args = p.parse_args()
    run = check_authorization_handoff if args.authorization_handoff_only else check
    print(json.dumps(run(args.out), indent=2))
