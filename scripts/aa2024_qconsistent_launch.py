"""Separately approved A(unit) or B(synthetic) only. Prepared, NOT RUN."""
import time
START = time.monotonic()

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys

REPO = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/.codex/worktrees/s03-e016-geometry-alignment-20261013')
PROJECT = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
TEST = PROJECT/'local_archive/code_checks/S03-E019-D02-T001'
RUN = PROJECT/'local_archive/experiments/S03-E019-D02/S03-E019-D02-R001'
THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
           'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')
NAMES = ('scripts/aa2024_qconsistent_repair.py', 'scripts/aa2024_qconsistent_launch.py',
         'tests/test_aa2024_qconsistent_repair.py',
         'docs/research/S03/S03-E019/q_consistency_repair_plan.md',
         'docs/research/S03/S03-E019/q_consistency_plan_review.md',
         'docs/research/S03/S03-E019/q_consistency_pro_request.md',
         'docs/research/S03/S03-E019/q_consistency_pro_response.md',
         'docs/research/S03/S03-E019/q_consistency_test_design.md',
         'scripts/aa2024_kinematic_capacity.py', 'scripts/aa2024_qsubspace_diagnostic.py')
ANCHORS = {'scripts/aa2024_kinematic_capacity.py': '4beb88d2a4b9aef20cc2c60face876f5469202c47b0f268bbc3efbd1cf3abaa7',
           'scripts/aa2024_qsubspace_diagnostic.py': '3da24d94de4b18777898969dcf12e19f3442e1c1c3ca3dab4d5732d355c7843c'}
FONT_LOG = 'Matplotlib is building the font cache; this may take a moment.'


def within():
    if time.monotonic()-START >= 60:
        raise TimeoutError('STOP_BUDGET: 60 seconds including final receipt')


def deadline(signum, frame):
    raise TimeoutError('STOP_BUDGET: process deadline; no automatic retry')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def regular_bytes(path):
    if path.resolve() != path or not path.is_file() or path.is_symlink():
        raise ValueError('STOP_PATH: regular nonsymlink fixed path required')
    return path.read_bytes()


def bindings(snapshot):
    if len(snapshot) != 40 or any(c not in '0123456789abcdef' for c in snapshot):
        raise ValueError('STOP_SOURCE: full reviewed snapshot required')
    result = {}
    for name in NAMES:
        within()
        data = regular_bytes(REPO/name)
        expected = subprocess.check_output(['git', 'show', snapshot+':'+name], cwd=REPO)
        value = digest(data)
        if data != expected or (name in ANCHORS and value != ANCHORS[name]):
            raise ValueError('STOP_SOURCE: changed reviewed source '+name)
        result[name] = value
    return result


def new_json(path, value):
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


def failed_receipt(path, value, exc):
    value.update(status='failed', error=repr(exc), outputs_role='forensic_only',
                 elapsed_seconds=time.monotonic()-START, end_utc=datetime.now(timezone.utc).isoformat())
    # Only this new execution's own receipt can be replaced after a late failure.
    with path.open('w', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write('\n')


class WarningStop(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.font_initialization_open = False
        self.expected = []

    def emit(self, record):
        message = record.getMessage()
        if (self.font_initialization_open and not self.expected and
                record.name == 'matplotlib.font_manager' and record.levelno == logging.WARNING and
                message == FONT_LOG):
            self.expected.append(dict(logger=record.name, level='WARNING', message=message))
            return
        raise RuntimeError('STOP_LOG_WARNING: '+record.name+': '+message)


def verify_test(snapshot, before):
    receipt = json.loads(regular_bytes(TEST/'test_receipt.json'))
    if (receipt.get('status') != 'passed' or receipt.get('operation') != 'artificial_unit_tests_only' or
            receipt.get('source_commit') != snapshot or receipt.get('budget_seconds') != 60 or
            not 0 <= receipt.get('elapsed_seconds', 60) < 60 or
            receipt.get('sources_before_sha256') != before or receipt.get('sources_after_sha256') != before or
            receipt.get('thread_environment') != {k: '1' for k in THREADS} or
            receipt.get('test_log_sha256') != digest(regular_bytes(TEST/'tests.log'))):
        raise ValueError('STOP_TEST_IDENTITY: matching approved A success unavailable')
    return digest(regular_bytes(TEST/'test_receipt.json'))


def main():
    signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, max(.001, 60-(time.monotonic()-START)))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('A', 'B'))
    parser.add_argument('--snapshot', required=True)
    args = parser.parse_args()
    if Path.cwd() != REPO or REPO.resolve() != REPO:
        raise ValueError('STOP_PATH: exact worktree required')
    if any(os.environ.get(k) != '1' for k in THREADS) or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('STOP_ENVIRONMENT: single-thread CPU and empty CUDA required')
    if not sys.flags.isolated or not sys.flags.dont_write_bytecode or sys.warnoptions != ['error']:
        raise ValueError('STOP_ENVIRONMENT: Python -I -B -W error required')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=REPO, text=True):
        raise ValueError('STOP_SOURCE: clean worktree required')
    before = bindings(args.snapshot)
    test_identity = verify_test(args.snapshot, before) if args.operation == 'B' else None
    out = TEST if args.operation == 'A' else RUN
    if out.resolve() != out or out.exists():
        raise ValueError('STOP_PATH: fresh canonical directory required; no retry')
    out.mkdir(parents=True, exist_ok=False)
    receipt_path = out/('test_receipt.json' if args.operation == 'A' else 'execution_receipt.json')
    receipt = dict(status='running', operation='artificial_unit_tests_only' if args.operation == 'A' else 'fixed_C1_C3_synthetic_repair',
                   source_commit=args.snapshot, sources_before_sha256=before, budget_seconds=60,
                   start_utc=datetime.now(timezone.utc).isoformat(), pid=os.getpid(), hostname=socket.gethostname(),
                   cwd=str(REPO), command=sys.argv, thread_environment={k: os.environ[k] for k in THREADS},
                   git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(),
                   git_dirty='', matching_A_receipt_sha256=test_identity,
                   budget_scope='process START through final receipt readback/check; no auto retry',
                   scope='synthetic numerical candidate; not real E019 acceptance or inverse validity')
    handler = WarningStop()
    logging.getLogger().addHandler(handler)
    try:
        if args.operation == 'A':
            command = [sys.executable, '-I', '-B', '-W', 'error', str(REPO/'tests/test_aa2024_qconsistent_repair.py')]
            receipt['child_command'] = command
            with (out/'tests.log').open('x', encoding='utf-8') as log:
                subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True,
                               timeout=max(.001, 60-(time.monotonic()-START)))
            within()
            receipt.update(status='passed', test_log_sha256=digest(regular_bytes(out/'tests.log')),
                           actual_qr_calls=0, svd_calls=0,
                           counter_scope='test design/guards; not independent whole-process audit')
        else:
            os.environ['MPLCONFIGDIR'] = str(out/'.mplconfig')
            os.environ['XDG_CACHE_HOME'] = str(out/'.cache')
            os.environ['MPLBACKEND'] = 'Agg'
            sys.path.insert(0, str(REPO/'scripts'))
            import aa2024_qconsistent_repair as d
            with ExitStack() as stack:
                sentinels = d.guards(stack)
                report = d.diagnose(within)
                new_json(out/'report.json', report)
                import csv
                fields = ['case', 'old_Q_ratio', 'new_Q_ratio', 'p_star_ratio', 'r_star_ratio', 'eta', 'retained_modes']
                with (out/'summary.csv').open('x', newline='', encoding='utf-8') as handle:
                    writer = csv.DictWriter(handle, fieldnames=fields)
                    writer.writeheader()
                    for row in report['cases']:
                        writer.writerow(dict(case=row['case'], old_Q_ratio=row['old_r_Q']['producer_einsum_ratio'],
                            new_Q_ratio=row['checks']['r_Q']['producer_einsum_ratio'],
                            p_star_ratio=row['checks']['primary_p'], r_star_ratio=row['checks']['primary_r'],
                            eta=row['eta'], retained_modes=5))
                within()
                handler.font_initialization_open = True
                # The only predeclared logging initialization exception, before drawing.
                import matplotlib.pyplot
                handler.font_initialization_open = False
                d.render(report, out)
                with (out/'q_identity_ratio.md').open('x', encoding='utf-8') as handle:
                    handle.write(d.sidecar(report))
                if any(s.call_count for s in sentinels):
                    raise ValueError('STOP_FORBIDDEN: guarded API called during B')
            within()
            names = ('report.json', 'summary.csv', 'q_identity_ratio.png', 'q_identity_ratio.pdf', 'q_identity_ratio.md')
            receipt.update(status='succeeded', artifacts_sha256={name: digest(regular_bytes(out/name)) for name in names},
                           qr_calls=3, svd_calls=0, expected_initialization_logs=handler.expected,
                           counter_scope='controlled Python API counters; not external process audit')
        after = bindings(args.snapshot)
        if before != after or subprocess.check_output(['git', 'status', '--porcelain'], cwd=REPO, text=True):
            raise ValueError('STOP_SOURCE: sources/worktree changed during operation')
        receipt.update(sources_after_sha256=after, elapsed_seconds=time.monotonic()-START,
                       end_utc=datetime.now(timezone.utc).isoformat())
        within()
        new_json(receipt_path, receipt)
        if json.loads(regular_bytes(receipt_path)) != receipt:
            raise ValueError('STOP_RECEIPT: readback mismatch')
        within()
        print(receipt['status'], out)
        within()
    except BaseException as exc:
        failed_receipt(receipt_path, receipt, exc)
        raise
    finally:
        logging.getLogger().removeHandler(handler)
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    main()
