#!/usr/bin/env python3
"""Prepare-only until separately approved: two text edits, new files only.

Standard library only. Never imports the producer or opens report/CSV/figures.
The original same-stem sidecar remains frozen; this is a mapped companion.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import signal
import stat
import sys
import time


ROOT = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S03-E019-D02/S03-E019-D02-R001')
SOURCE = ROOT / 'q_identity_ratio.md'
OUTPUT = ROOT / 'q_identity_ratio.sidecar_v01.md'
RECEIPT = ROOT / 'q_identity_ratio.sidecar_v01.receipt.json'
SOURCE_SHA = '0788c0190a6906f633d01fbbc985ff60e765fdf0af7939a98e0a2cac101df0fc'
EDITS = (
    (b'## Visual grammar and panel guide\n',
     b'## How to read: visual grammar and panel guide\n'),
    (b'Full primary analytic-p/r ratios and all five image/Pythagoras probes are in report.json and summary.csv.\n',
     b'Full primary analytic-p/r ratios and all five image/Pythagoras probe details are in report.json. '
     b'summary.csv contains case-level summary columns only; it does not contain the five-probe details.\n'),
)
THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
           'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def regular_no_links(path):
    """Check every ancestor as well as the leaf; no symlink resolution."""
    for parent in reversed(path.parents):
        mode = parent.lstat().st_mode
        require(stat.S_ISDIR(mode), 'STOP_PATH_ANCESTOR: '+str(parent))
    require(stat.S_ISREG(path.lstat().st_mode), 'STOP_NOT_REGULAR: '+str(path))


def absent(path):
    require(not os.path.lexists(path), 'STOP_OUTPUT_EXISTS: '+str(path))


class WarningStop(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            raise RuntimeError('STOP_LOG_WARNING: '+record.getMessage())


def main():
    started = time.monotonic()

    def budget(*_):
        require(time.monotonic()-started < 60, 'STOP_BUDGET_60_SECONDS')

    def timed_out(*_):
        raise RuntimeError('STOP_BUDGET_60_SECONDS')

    signal.signal(signal.SIGALRM, timed_out)
    signal.setitimer(signal.ITIMER_REAL, 60)
    logging.getLogger().addHandler(WarningStop(logging.WARNING))
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-script-sha256', required=True)
    args = parser.parse_args()
    script = Path(__file__).absolute()
    regular_no_links(script)
    script_bytes = script.read_bytes()
    require(sha(script_bytes) == args.expected_script_sha256, 'STOP_SCRIPT_IDENTITY')
    require(all(os.environ.get(k) == '1' for k in THREADS), 'STOP_THREAD_ENV')
    require(os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'STOP_CUDA_ENV')
    require(sys.flags.isolated and sys.flags.dont_write_bytecode, 'STOP_PYTHON_FLAGS')
    start_utc = datetime.now(timezone.utc).isoformat()
    regular_no_links(SOURCE)
    source_bytes = SOURCE.read_bytes()
    require(sha(source_bytes) == SOURCE_SHA, 'STOP_SOURCE_IDENTITY')
    absent(OUTPUT)
    absent(RECEIPT)
    revised = source_bytes
    for old, new in EDITS:
        require(source_bytes.count(old) == 1, 'STOP_REPLACEMENT_CARDINALITY')
        revised = revised.replace(old, new, 1)
    require(revised != source_bytes, 'STOP_NO_CHANGE')
    text = revised.decode('utf-8')
    require(len(text.strip()) >= 400, 'STOP_SIDECAR_LENGTH')
    require(all(p in text.lower() for p in ('how to read', 'data provenance', 'limitation')),
            'STOP_SIDECAR_PHRASE')
    # These are in-memory string checks, NOT numerical or official directory acceptance.
    regular_no_links(SOURCE)
    require(SOURCE.read_bytes() == source_bytes, 'STOP_SOURCE_CHANGED_BEFORE_WRITE')
    budget()
    with OUTPUT.open('xb') as handle:
        handle.write(revised)
    regular_no_links(OUTPUT)
    require(OUTPUT.read_bytes() == revised, 'STOP_OUTPUT_READBACK')
    regular_no_links(SOURCE)
    require(SOURCE.read_bytes() == source_bytes, 'STOP_SOURCE_CHANGED_AFTER_WRITE')
    regular_no_links(script)
    require(script.read_bytes() == script_bytes, 'STOP_SCRIPT_CHANGED')
    budget()
    record = dict(
        status='sidecar_derivative_written_not_accepted',
        operation='E019-D02-sidecar-v01-two-text-edits-only',
        start_utc=start_utc, pid=os.getpid(), script=str(script),
        script_sha256=sha(script_bytes), source=str(SOURCE),
        source_sha256_before=SOURCE_SHA, source_sha256_after=sha(source_bytes),
        output=str(OUTPUT), output_sha256=sha(revised), replacements=2,
        companion_for=[str(ROOT/'q_identity_ratio.png'), str(ROOT/'q_identity_ratio.pdf')],
        official_same_stem_sidecar=str(SOURCE),
        official_directory_validator_run=False, independent_acceptance_run=False,
        thread_env={k: os.environ[k] for k in THREADS},
        elapsed_before_receipt_write_seconds=time.monotonic()-started,
        limitations=[
            'only a derivative text companion; original same-stem sidecar remains unchanged',
            'no claim that original directory validator passes',
            'no report/CSV/image/PDF/old numerical archive/realarray/holdout content opened',
            'no numerical recomputation/render/QR/SVD or producer import',
            'no whole-process syscall audit or independent numerical acceptance',
            'source location assertion follows frozen producer source and prior stop record, not new report inspection',
        ],
    )
    payload = (json.dumps(record, indent=2)+'\n').encode('utf-8')
    with RECEIPT.open('xb') as handle:
        handle.write(payload)
    regular_no_links(RECEIPT)
    require(RECEIPT.read_bytes() == payload, 'STOP_RECEIPT_READBACK')
    budget()
    print('SIDECAR_DERIVATIVE_WRITTEN_NOT_ACCEPTED '+str(OUTPUT), flush=True)
    budget()
    signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('STOP_NO_RETRY '+str(exc), file=sys.stderr, flush=True)
        raise SystemExit(1)
