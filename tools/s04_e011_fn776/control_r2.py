"""Exact-plan control journal. No default execution and no automatic reconnect.

Only the human-approved plan hash supplies literal child argv, stdin identity,
timeouts and order. Raw streams go directly to files from Popen, so a timeout
cannot discard communicate() buffers. Import is inert; preparation is AST only.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

CARD = 'S04-E011-UVH-C1-FN776-CARD-r2'
INDEX = 'S04-E011-FN776-r2-A1'
RUN = 'pf_s04e011_uvh_c1_fn776_r2_20261019'
CASE = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/runs') / RUN / 'authorized_execution'
CAP = 1024**2
RECEIPT_RESERVE = 64*1024


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def save(path, record):
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(record, indent=2, allow_nan=False)+'\n')
    os.replace(temp, path)


def journal(folder, event):
    with (folder/'events.jsonl').open('a') as stream:
        stream.write(json.dumps(dict(utc=stamp(), **event), allow_nan=False)+'\n')
        stream.flush()
        os.fsync(stream.fileno())


def bytes_used(folder):
    return (sum(p.stat().st_size for p in folder.rglob('*') if p.is_file()) +
            sum(p.stat().st_size for p in CASE.iterdir() if p.is_file() and p.name!='retrieved.tar'))


def cleanup_owned(child):
    result = dict(pid=child.pid, already_exited=child.poll() is not None, actions=[])
    if child.poll() is None:
        # start_new_session=True below establishes this exact owned PGID.
        assert os.getpgid(child.pid) == child.pid, 'owned child process group changed'
        for sig in (signal.SIGTERM, signal.SIGKILL):
            os.killpg(child.pid, sig)
            result['actions'].append(signal.Signals(sig).name)
            try:
                child.wait(timeout=2)
                break
            except subprocess.TimeoutExpired:
                pass
    result.update(exit_code=child.poll(), reaped=child.poll() is not None)
    return result


def execute(folder, name, step, number):
    key = name + (f'_{number:02d}' if step.get('repeat_success_only') else '')
    with (folder/(key+'.claim.json')).open('x') as stream:
        json.dump(dict(step=name, invocation=number, utc=stamp()), stream)
    start = time.monotonic()
    record = dict(step=name, invocation=number, status='started', start_utc=stamp(),
                  argv=step['argv'], timeout_seconds=step['timeout_seconds'],
                  child_wait_seconds=step['timeout_seconds']-4, local_cleanup_reserve_seconds=4,
                  stdin=step.get('stdin'), remote_completion='unknown')
    journal(folder, record)
    save(folder/(key+'.json'), record)
    child = None
    input_stream = None
    # A retrieved archive is a duplicate of already-budgeted producer bytes;
    # it is never a diagnostic stream and is independently size/hash verified.
    stdout = CASE/step['stdout_artifact'] if 'stdout_artifact' in step else folder/(key+'.stdout')
    stderr = folder/(key+'.stderr')
    try:
        if 'stdin' in step:
            item = step['stdin']; path = Path(item['path'])
            raw = path.read_bytes()  # Reviewed CODE script/bundle only, no scientific input.
            assert len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256']
            input_stream = path.open('rb')
        with stdout.open('xb') as out, stderr.open('xb') as err:
            assert bytes_used(folder) <= CAP-RECEIPT_RESERVE, 'phase output reserve exhausted before spawn'
            assert time.monotonic()-start < step['timeout_seconds']-4, 'phase time exhausted before spawn'
            child = subprocess.Popen(step['argv'], stdin=input_stream or subprocess.DEVNULL,
                                     stdout=out, stderr=err, cwd=step['cwd'],
                                     start_new_session=True)
            record['child_pid'] = child.pid
            journal(folder, dict(event='child_started', step=name, invocation=number,
                                 pid=child.pid, cwd=step['cwd']))
            while child.poll() is None:
                if bytes_used(folder) > CAP-RECEIPT_RESERVE:
                    raise RuntimeError('control diagnostic1MiB envelope; terminal/no retry')
                if stdout.stat().st_size > 100*1024**2:
                    raise RuntimeError('retrieved artifact exceeds100MiB; terminal/no retry')
                if time.monotonic()-start >= step['timeout_seconds']-4:
                    raise subprocess.TimeoutExpired(step['argv'], step['timeout_seconds']-4)
                try:
                    child.wait(timeout=.1)
                except subprocess.TimeoutExpired:
                    pass  # Poll only, not a retry/reconnect/child re-execution.
        assert child.returncode == 0, 'child exit '+str(child.returncode)
        assert bytes_used(folder) <= CAP-RECEIPT_RESERVE, 'control diagnostic envelope'
        assert stdout.stat().st_size <= 100*1024**2, 'retrieved artifact envelope'
        if 'success_status' in step:
            reply = json.loads(stdout.read_text().splitlines()[-1])
            assert reply['status'] == step['success_status'], 'remote admission/status not established'
            record['verified_reply'] = reply
        record.update(status='completed', exit_code=child.returncode,
                      remote_completion='only what retained stdout explicitly proves')
    except BaseException as error:
        record.update(status='terminal_failed', error_type=type(error).__name__, error=repr(error),
                      timed_out=isinstance(error, subprocess.TimeoutExpired), retry_allowed=False)
        # Raw stdout/stderr were on disk throughout. Preserve any additional
        # exception buffers too, distinguishing absent from known empty bytes.
        for attribute in ('stdout', 'stderr'):
            partial = getattr(error, attribute, None)
            record['exception_'+attribute+'_present'] = partial is not None
            if partial is not None:
                raw = partial.encode() if isinstance(partial, str) else partial
                (folder/(key+'.exception_'+attribute)).write_bytes(raw)
        if child is not None:
            try:
                record['cleanup'] = cleanup_owned(child)
            except BaseException as cleanup_error:
                record['cleanup_error'] = repr(cleanup_error)
        raise
    finally:
        if input_stream is not None:
            input_stream.close()
        record.update(end_utc=stamp(), elapsed_seconds=time.monotonic()-start,
                      stdout_path=str(stdout), stderr_path=str(stderr),
                      stdout_bytes=stdout.stat().st_size if stdout.exists() else None,
                      stderr_bytes=stderr.stat().st_size if stderr.exists() else None)
        # stdout/stderr can remain partial on timeout, interruption or spawn failure.
        save(folder/(key+'.json'), record)
        journal(folder, dict(event='stage_end', **record))
        if record['status'] != 'completed':
            save(folder/'terminal.json', record)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-approved', action='store_true')
    p.add_argument('--approval-ref', required=True)
    p.add_argument('--approval-index', required=True)
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--plan-sha256', required=True)
    p.add_argument('--step', required=True)
    args = p.parse_args()
    if (not args.execute_approved or args.approval_ref != CARD or args.approval_index != INDEX or
            sys.flags.optimize or sys.platform != 'darwin'):
        raise SystemExit('exact human-approved r2 plan, Mac control only; preparation never executes')
    raw = args.plan.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == args.plan_sha256
    plan = json.loads(raw)
    assert plan['card_id'] == CARD and plan['run_id'] == RUN and plan['approval_index'] == INDEX
    code = Path(__file__).resolve().parents[2]
    source = json.loads((code/'SOURCE_PROVENANCE.json').read_text())
    assert source['development_source'] == plan['development_source']
    assert hashlib.sha1(b'blob '+str(len(Path(__file__).read_bytes())).encode()+b'\0'+Path(__file__).read_bytes()).hexdigest() == plan['controller_blob']
    folder = CASE/'control_diagnostics'
    if not folder.exists():
        assert args.step == 'local_package', 'first stage must be local_package'
        folder.mkdir(parents=True, exist_ok=False)
        save(folder/'approval.json', dict(card=CARD, approval_index=INDEX,
             plan_sha256=args.plan_sha256, utc=stamp(), one_attempt=True))
    approval = json.loads((folder/'approval.json').read_text())
    assert approval['plan_sha256'] == args.plan_sha256 and not (folder/'terminal.json').exists()
    state_path = folder/'state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    step = plan['steps'][args.step]
    for previous in step.get('requires', []):
        assert state.get(previous, {}).get('status') == 'completed', 'missing predecessor '+previous
    if step.get('requires_terminal_monitor'):
        assert state['monitor']['verified_reply']['terminal'], 'wait for producer terminal; no live retrieval'
    if 'fresh_thread_receipt' in step:
        receipt = json.loads((CASE/step['fresh_thread_receipt']).read_text())
        age = (dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(receipt['checked_utc'])).total_seconds()
        assert receipt['run_id']==RUN and receipt['no_duplicate'] is True and 0 <= age <= 60
    prior = state.get(args.step)
    assert prior is None or (step.get('repeat_success_only') and prior['status'] == 'completed')
    number = 1 if prior is None else prior['invocation']+1
    assert number <= step.get('max_invocations',1), 'planned observation count exhausted'
    if prior is not None and 'minimum_interval_seconds' in step:
        interval=(dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(prior['end_utc'])).total_seconds()
        assert interval >= step['minimum_interval_seconds'], 'wait locally for planned observation interval'
    record = execute(folder, args.step, step, number)
    state[args.step] = record
    save(state_path, state)
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        folder=CASE/'control_diagnostics'
        if (folder/'approval.json').exists() and not (folder/'terminal.json').exists():
            save(folder/'terminal.json',dict(status='terminal_control_error',utc=stamp(),
                 error=repr(error),retry_allowed=False,remote_completion='unknown'))
        raise
