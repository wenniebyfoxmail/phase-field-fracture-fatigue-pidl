"""Fixed mock-only job configuration for the tested bounded supervisor."""
import argparse
from pathlib import Path

import s04_late_attribution_guard as guard

ATTEMPT = 'S04-E021-LATE-ADAPTER-MOCK-R002'
OUTPUT_NAME = 'late-adapter-mock-20261016-R002'


def execute(out, expected_commit):
    # Process-local fixed configuration, no caller-controlled worker or source.
    guard.ATTEMPT = ATTEMPT
    guard.OUTPUT_NAME = OUTPUT_NAME
    guard.WORKER_NAME = 's04_late_adapter_checks.py'
    guard.SOURCES = ['SENS_tensile/'+name for name in (
        's04_late_attribution.py', 's04_late_attribution_guard.py',
        's04_late_adapter.py', 's04_late_adapter_guard.py', 's04_late_adapter_checks.py')]
    return guard.execute(out, ATTEMPT, expected_commit)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--expected-commit', required=True)
    args = parser.parse_args()
    raise SystemExit(execute(args.out, args.expected_commit))
