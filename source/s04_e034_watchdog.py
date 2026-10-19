"""Standalone quota watchdog, standard library only; opt-in producer child."""
import json
import os
from pathlib import Path
import signal
import sys
import time


def watch(pid, out):
    while not (out/'watchdog_done').exists():
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        row = json.loads((out/'phase_deadline.json').read_text())
        if row['pid'] != pid:
            raise ValueError('watchdog process identity changed')
        if time.monotonic() >= row['deadline']-5:
            (out/'watchdog_stop.json').write_text(json.dumps(dict(**row, reason='phase deadline; entire package stopped, no retry'))+'\n')
            os.kill(pid, signal.SIGTERM)
            while time.monotonic() < row['deadline']:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    return
                time.sleep(.01)
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            return
        time.sleep(.05)


if __name__ == '__main__':
    watch(int(sys.argv[1]), Path(sys.argv[2]))
