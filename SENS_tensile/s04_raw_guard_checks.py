"""Mock guard fault injection: no child process, allocation, source or fitting."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import s04_raw_guard as guard


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
    print(json.dumps(check(p.parse_args().out), indent=2))
