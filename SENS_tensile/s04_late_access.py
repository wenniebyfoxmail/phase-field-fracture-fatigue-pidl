"""Restricted four-source access worker. No attribution, fit, plot or replay.

Definitions/imports perform NO scientific IO. Only the fixed guard may invoke
the explicit worker entry after an independently reviewed, human-approved run.
"""
import sys

if sys.flags.optimize != 0:
    raise RuntimeError('optimized Python is forbidden for real access')

import argparse
import json
import os
from pathlib import Path
import stat

import s04_late_adapter as a

SCOPE = 'FOUR_SOURCE_READONLY_ACCESS_ONLY'
FILES = {'authorization.json', 'access_verification.json', 'access.log', 'guard_receipt.json'}


def full_commit(code):
    a.require(type(code) is str and len(code) == 40 and
              all(c in '0123456789abcdef' for c in code), 'full reviewed commit required')


def read_authorization(path):
    """One fixed control file only, <=64KiB; never a scientific source reader."""
    p = Path(path)
    a.require(str(p) == str(Path(a.REAL_OUTPUT)/'authorization.json') and
              str(p.resolve(strict=True)) == str(p), 'fixed canonical authorization path')
    before = a.token(p.lstat())
    a.require(stat.S_ISREG(before[2]) and 0 < before[3] <= 65536 and
              before[2] & 0o222 == 0 and p.lstat().st_nlink == 1,
              'bounded read-only regular authorization required')
    fd = os.open(p, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        a.require(a.token(os.fstat(fd)) == before, 'authorization descriptor mismatch')
        data = bytearray()
        while len(data) <= 65536:
            block = os.read(fd, min(65536, 65537-len(data)))
            if not block:
                break
            data.extend(block)
        a.require(len(data) == before[3] and len(data) <= 65536, 'authorization size mismatch')
        a.require(a.token(os.fstat(fd)) == before, 'authorization descriptor drift')
    finally:
        os.close(fd)
    a.require(a.token(p.lstat()) == before, 'authorization path drift')
    return bytes(data).decode('utf-8')


def grant_for(code):
    full_commit(code)
    return dict(version=1, action='four_source_readonly_handoff', domain='REAL_SAVED_SCALARS',
                code_commit=code, plan_commit=a.core.PLAN_COMMIT, attempt=a.REAL_RUN,
                output=a.REAL_OUTPUT, sources=list(a.SOURCES), budget=dict(a.BUDGET),
                fit=False, confirmation=False, user_approved_real_execution=True,
                independent_code_review='APPROVED')


def run(out):
    """Only CLI entry, not called during implementation or static review."""
    a.require(str(out) == a.REAL_OUTPUT, 'fixed output required')
    code = os.environ.get('S04_LATE_CODE', '')
    full_commit(code)
    refs = dict(approval_ref=os.environ.get('S04_LATE_APPROVAL_REF'),
                review_ref=os.environ.get('S04_LATE_REVIEW_REF'), reviewed_commit=code)
    a.check_execution_refs(refs, code)
    auth = str(out/'authorization.json')
    # This rejects relative paths, wrong parent/env and paths before auth open.
    a.check_child_handoff(auth, str(out), os.environ, actual_parent=os.getppid(),
                          attempt=a.REAL_RUN, code_commit=code)
    activity = dict(metadata_attempts=0, read_attempts=0, content_bytes=0,
                    content_by_source={path: 0 for path in a.SOURCES})

    def event(kind, path, count):
        a.require(path in a.SOURCES, 'activity outside science allowlist')
        if kind == 'METADATA_ATTEMPT':
            activity['metadata_attempts'] += 1
        elif kind == 'READ_ATTEMPT':
            activity['read_attempts'] += 1
        elif kind == 'CONTENT_BYTES':
            activity['content_bytes'] += count
            activity['content_by_source'][path] += count
        else:
            raise ValueError('unknown access event')
        print(json.dumps(dict(event=kind, path=path, bytes=count)), flush=True)

    snapshot = None
    error = None
    try:
        grant = a.decode_child_grant(auth, str(out), os.environ, actual_parent=os.getppid(),
                                     attempt=a.REAL_RUN, code_commit=code,
                                     read_auth=read_authorization)
        a.check_grant(grant, code_commit=code, attempt=a.REAL_RUN,
                      output=str(out), domain='REAL_SAVED_SCALARS')
        snapshot = a.acquire_real(grant=grant, code_commit=code, env=os.environ,
                                  auth_path=auth, output=str(out), actual_parent=os.getppid(),
                                  execution_refs=refs, access_event=event)
    except BaseException as exc:
        # Do not echo source values through a parser exception message.
        error = dict(type=type(exc).__name__, stage='AUTHORIZATION_OR_ACCESS')
    record = dict(status='READONLY_ACCESS_VERIFIED' if error is None else 'READONLY_ACCESS_FAILED',
                  scope=SCOPE, domain='REAL_SAVED_SCALARS', attempt_id=a.REAL_RUN,
                  code_commit=code, execution_references=refs, sources=list(a.SOURCES),
                  activity=activity, error=error, source_metadata=None,
                  coverage_verified=error is None, rows_verified=None, counts_verified=None,
                  python_optimize=sys.flags.optimize, python_debug=__debug__,
                  source_metadata_accessed=activity['metadata_attempts'] > 0,
                  real_data_read=activity['content_bytes'] > 0,
                  attribution_invoked=False, fitting_invoked=False, confirmation_accessed=False,
                  original_scientific_verdict_unchanged=True,
                  limits='metadata drift checks, not content authentication or physical validation')
    if snapshot is not None:
        record.update(source_metadata=snapshot['source_metadata'], rows_verified=len(snapshot['rows']),
                      counts_verified=dict(a.core.COUNTS), saved_ratio_verified=True)
        # Do not persist rows, background MSE or any source JSON/text.
        del snapshot
    with (out/'access_verification.json').open('x') as file:
        json.dump(record, file, indent=2, allow_nan=False)
    print(json.dumps(dict(worker_status=record['status'], activity=activity)), flush=True)
    return int(error is not None)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.out))
