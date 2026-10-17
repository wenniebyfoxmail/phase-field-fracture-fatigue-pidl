"""Fixed single targeted binding mock; reuse the unchanged bounded guard."""
import sys

if sys.flags.optimize != 0:
    raise RuntimeError('optimized Python is forbidden for the binding mock guard')

import argparse
import os
from pathlib import Path

import s04_late_attribution_guard as guard

ATTEMPT = 'S04-E021-LATE-BINDING-MOCK-R001'
OUTPUT_NAME = 'late-binding-mock-20261017-R001'


def execute(out, expected_commit):
    guard.ATTEMPT = ATTEMPT
    guard.OUTPUT_NAME = OUTPUT_NAME
    guard.WORKER_NAME = 's04_late_binding_checks.py'
    guard.SOURCES = ['SENS_tensile/'+name for name in (
        's04_late_attribution.py', 's04_late_attribution_guard.py',
        's04_late_adapter.py', 's04_late_adapter_checks.py',
        's04_late_binding_guard.py', 's04_late_binding_checks.py')]
    os.environ['S04_BINDING_PARENT'] = str(os.getpid())
    os.environ['S04_BINDING_CODE'] = expected_commit
    os.environ['PYTHONOPTIMIZE'] = '0'
    return guard.execute(out, ATTEMPT, expected_commit)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--expected-commit', required=True)
    args = parser.parse_args()
    raise SystemExit(execute(args.out, args.expected_commit))
