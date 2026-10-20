"""Prepared SYNMEM runner. Default: inspect configuration, never start a solve.

Execution requires an explicit enabled authority receipt and exact code review.
Linux-only supervisor enforces one fresh run, wall/step/RAM/storage/step-count
limits and kills its own process group on the first failure. No retry/resume.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import signal
import stat
import subprocess
import sys
import traceback
from time import monotonic, sleep, time


def json_read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    from hybrid_producer_common import write_json
    write_json(path, value)


def current_commit(code):
    return subprocess.check_output(['git', '-C', str(code), 'rev-parse', 'HEAD'], text=True).strip()


def verify_import_tree(code):
    tracked = set(subprocess.check_output(['git', '-C', str(code), 'ls-files', '-z',
                   'source', 'tools'], text=True).split('\0'))
    for directory in ('source', 'tools'):
        for p in (Path(code)/directory).rglob('*'):
            if p.is_symlink():
                raise RuntimeError('unreviewed import-tree symlink: '+str(p.relative_to(code)))
            if not p.is_file():
                continue
            relative = p.relative_to(code)
            if '__pycache__' in relative.parts and p.suffix == '.pyc':
                continue
            if relative.as_posix() not in tracked:
                raise RuntimeError('unreviewed import-tree file: '+str(relative))


def verify_authority(spec, authority, review, code):
    from hybrid_producer_common import object_sha
    if (authority.get('enabled') is not True or not authority.get('user_approval')
            or authority.get('spec_id') != object_sha(spec)
            or authority.get('producer') != spec['producer']
            or authority.get('maximum_runs') != 1
            or authority.get('retry_allowed') is not False):
        raise RuntimeError('explicit approval of this bounded SYNMEM task is missing')
    head = current_commit(code)
    # Review commit may be an ancestor only when the sole later tracked edits
    # are the review receipt and disabled/enabled authority metadata themselves.
    reviewed = review.get('code_commit', '')
    if (review.get('verdict') != 'REVIEW_PASS' or review.get('spec_id') != object_sha(spec)
            or authority.get('code_commit') != reviewed):
        raise RuntimeError('exact code/config independent review missing')
    subprocess.run(['git', '-C', str(code), 'merge-base', '--is-ancestor', reviewed, head], check=True)
    changed = subprocess.check_output(['git', '-C', str(code), 'diff', '--name-only', reviewed, head], text=True).splitlines()
    allowed = {'docs/research/S04/S04-E027-SYNMEM/review.md',
               'docs/research/S04/S04-E027-SYNMEM/review.json',
               'docs/research/S04/S04-E027-SYNMEM/authority.json'}
    if set(changed)-allowed:
        raise RuntimeError('unreviewed scientific/control files differ from code review')
    dirty = subprocess.check_output(['git', '-C', str(code), 'status', '--porcelain', '--untracked-files=no'], text=True)
    if dirty:
        raise RuntimeError('tracked source is dirty')
    verify_import_tree(code)
    return head


def storage_size(root):
    root = Path(root)
    # Admission checks a not-yet-created run root. Once traversal starts, any
    # missing durable directory remains an error; only StateStore's transient
    # empty lock directory may disappear before or during scandir.
    if not root.exists():
        return 0

    def transient(path):
        return (path.name.startswith('.json-')
                or path.name.startswith('latest.npz.trial-')
                or path.name == 'latest.npz.lock')

    def walk(directory):
        try:
            with os.scandir(directory) as iterator:
                entries = list(iterator)
        except FileNotFoundError:
            if directory != root and directory.name == 'latest.npz.lock':
                return 0
            raise
        total = 0
        for entry in entries:
            path = Path(entry.path)
            try:
                observed = path.stat()
            except FileNotFoundError:
                if transient(path):
                    continue
                raise
            if stat.S_ISREG(observed.st_mode):
                total += observed.st_size
            elif stat.S_ISDIR(observed.st_mode) and not entry.is_symlink():
                total += walk(path)
        return total

    return walk(root)


def resource_check(spec, root, start, *, continuation=None):
    if monotonic()-start >= spec['budget']['wall_seconds']-spec['budget']['cleanup_seconds']:
        raise RuntimeError('total wall budget reached')
    # Leave room for the terminal receipt itself; reserve is not measured cost.
    prior_bytes = continuation['prior_output_bytes'] if continuation else 0
    if continuation and time() >= continuation['deadline_epoch']-spec['budget']['cleanup_seconds']:
        raise RuntimeError('cumulative task wall budget reached')
    if storage_size(root) + prior_bytes > spec['budget']['storage_bytes']-65536:
        raise RuntimeError('storage budget reached')


def stop_worker(proc):
    """Only the newly spawned worker group; tolerate exit between poll/kill."""
    if proc is None or proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait(timeout=5)


def worker(spec, root):
    # Parent-death guard before importing the scientific stack.
    if platform.system() != 'Linux':
        raise RuntimeError('scientific worker is Linux producer-only')
    import ctypes
    import resource
    expected = int(os.environ['SYNMEM_SUPERVISOR_PID'])
    if ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
        raise RuntimeError('parent-death guard unavailable')
    if os.getppid() != expected:
        raise RuntimeError('supervisor lost before worker start')
    gate = int(os.environ['SYNMEM_START_FD'])
    if os.read(gate, 1) != b'1':
        raise RuntimeError('supervisor did not admit worker')
    os.close(gate)
    limit = spec['budget']['ram_bytes']
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    cpus = sorted(os.sched_getaffinity(0))[:spec['budget']['cpu_threads']]
    os.sched_setaffinity(0, cpus)
    from synthetic_history_experiment import run_experiment
    from importlib.metadata import version
    root = Path(root)
    write(root/'runtime.json', dict(python=sys.version, executable=sys.executable,
          numpy=version('numpy'), scipy=version('scipy'), osqp=version('osqp'),
          matplotlib=version('matplotlib'), affinity=sorted(os.sched_getaffinity(0)),
          environment={key: os.environ.get(key) for key in
                       ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'CUDA_VISIBLE_DEVICES')}))
    receipt = json_read(root/'receipt.json')
    continuation = receipt.get('continuation')
    prior_attempts = continuation['prior_attempts'] if continuation else 0
    attempts = prior_attempts

    def marker(trajectory, step):
        nonlocal attempts
        if step is not None:
            attempts += 1
            if attempts > spec['budget']['maximum_steps']:
                raise RuntimeError('physical step budget exhausted')
        write(root/'progress.json', dict(trajectory=trajectory, step=step,
                                        step_started=monotonic() if step is not None else None,
                                        attempted_steps=attempts))
    try:
        if continuation:
            from synthetic_history_recovery import verify_recovery, SOURCE_CODE
            verify_recovery(spec, continuation, root)
            from importlib.metadata import version
            old_runtime = json_read(Path(continuation['source_root'])/'runtime.json')
            if any(version(name) != old_runtime[name] for name in ('numpy','scipy','osqp','matplotlib')):
                raise RuntimeError('recovery numerical runtime differs from original')
            source_id = SOURCE_CODE
        else:
            source_id = receipt['code_commit']
        result = run_experiment(spec, root, source_id, marker, recovery=continuation)
        from plot_synthetic_history import render
        render(root)
        write(root/'worker_terminal.json', dict(state='completed', result=result,
                                                attempted_steps=attempts, prior_attempts=prior_attempts,
                                                new_attempted_steps=attempts-prior_attempts, epoch=time()))
    except BaseException as exc:
        write(root/'worker_terminal.json', dict(state='failed', error=repr(exc),
                                                attempted_steps=attempts, prior_attempts=prior_attempts,
                                                new_attempted_steps=attempts-prior_attempts, epoch=time()))
        raise


def supervise(spec, authority, review, output, code):
    import shutil
    start = monotonic()
    head = verify_authority(spec, authority, review, code)
    if platform.system() != 'Linux' or platform.node() != spec['producer']['hostname']:
        raise RuntimeError('wrong producer; no Mac run or silent machine fallback')
    root = Path(output).resolve()
    owner = Path(spec['producer']['root']).resolve()
    if (root.parent != owner or not root.name.startswith('S04-E027-SYNMEM-R')
            or root.exists() or root != Path(authority['run_root']).resolve()):
        raise RuntimeError('fresh exact approved run root required')
    if len(os.sched_getaffinity(0)) < spec['budget']['cpu_threads']:
        raise RuntimeError('insufficient allowed CPUs')
    if os.getloadavg()[0] > os.cpu_count()-spec['budget']['cpu_threads']:
        raise RuntimeError('producer CPU capacity unavailable; zero start, no automatic retry')
    if shutil.disk_usage(owner).free < spec['budget']['storage_bytes'] + 1024**3:
        raise RuntimeError('insufficient producer disk reserve')
    continuation = authority.get('continuation')
    if continuation:
        from synthetic_history_recovery import verify_recovery
        verify_recovery(spec, continuation, root)
        resource_check(spec, root, start, continuation=continuation)
    root.mkdir()  # one durable run reservation; never reuse or remove on failure
    write(root/'spec.json', spec)
    write(root/'authority.json', authority)
    write(root/'review.json', review)
    write(root/'receipt.json', dict(state='reserved', code_commit=head,
          reviewed_code_commit=review['code_commit'], hostname=platform.node(),
          start_epoch=time(), command=sys.argv, pid=os.getpid(), dirty=False,
          runtime=sys.version, budget=spec['budget'], authority=authority['user_approval'],
          continuation=continuation))
    env = os.environ.copy()
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        env[name] = str(spec['budget']['cpu_threads'])
    for name in ('tmp', 'cache'):
        (root/name).mkdir()
    env.update(CUDA_VISIBLE_DEVICES='', TMPDIR=str(root/'tmp'),
               XDG_CACHE_HOME=str(root/'cache'), MPLCONFIGDIR=str(root/'cache/matplotlib'),
               MPLBACKEND='Agg', PYTHONPATH=str(code/'source')+os.pathsep+str(code/'tools'),
               SYNMEM_SUPERVISOR_PID=str(os.getpid()))
    read_fd, write_fd = os.pipe()
    env['SYNMEM_START_FD'] = str(read_fd)
    proc = None
    reason = None
    exception_traceback = None
    exception_filename = None
    old_handlers = {}
    def interrupted(signum, frame):
        raise RuntimeError('supervisor interrupted by signal '+str(signum))
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        old_handlers[sig] = signal.signal(sig, interrupted)
    try:
        with (root/'worker.log').open('x') as log:
            proc = subprocess.Popen([sys.executable, '-u', str(code/'tools/run_synthetic_history.py'),
                    '--spec', str(root/'spec.json'), '--worker', '--output', str(root)],
                    cwd=code, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                    start_new_session=True, pass_fds=(read_fd,))
            os.close(read_fd); read_fd = None
            write(root/'process.json', dict(pid=proc.pid, process_group=proc.pid,
                                            cwd=str(code), command='run_synthetic_history --worker'))
            os.write(write_fd, b'1'); os.close(write_fd); write_fd = None
            # Worker has no subprocesses. RLIMIT_AS gives a hard virtual
            # allocation ceiling; no unmeasured peak RSS is reported as zero.
            while proc.poll() is None:
                resource_check(spec, root, start, continuation=continuation)
                progress = root/'progress.json'
                if progress.exists():
                    p = json_read(progress)
                    if p['step_started'] is not None and monotonic()-p['step_started'] >= spec['budget']['step_hard_seconds']:
                        raise RuntimeError('physical step hard deadline reached')
                sleep(.5)
            resource_check(spec, root, start, continuation=continuation)  # includes final output at process exit
            if proc.returncode != 0:
                raise RuntimeError('worker failed; exit '+str(proc.returncode))
            terminal = json_read(root/'worker_terminal.json')
            if terminal['state'] != 'completed':
                raise RuntimeError('worker success receipt missing')
    except BaseException as exc:
        reason = repr(exc)
        exception_traceback = traceback.format_exc()
        exception_filename = getattr(exc, 'filename', None)
    finally:
        for fd in (read_fd, write_fd):
            if fd is not None:
                os.close(fd)
        try:
            stop_worker(proc)
        except Exception as exc:
            reason = (reason+'; ' if reason else '')+'worker cleanup: '+repr(exc)
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
        # A previous error remains primary. A clean exit is never upgraded
        # when the last write/cleanup crossed the resource envelope.
        if reason is None:
            try:
                resource_check(spec, root, start, continuation=continuation)
            except Exception as exc:
                reason = repr(exc)
        write(root/'supervisor_terminal.json', dict(state='failed' if reason else 'completed',
              error=reason, wall_seconds=monotonic()-start, storage_bytes=storage_size(root),
              returncode=proc.returncode if proc else None, completed_epoch=time(),
              exception_traceback=exception_traceback, exception_filename=exception_filename,
              cumulative_wall_seconds=time()-1792532920 if continuation else None,
              prior_output_bytes=continuation['prior_output_bytes'] if continuation else 0))
    if reason:
        raise RuntimeError(reason)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec', type=Path, required=True)
    p.add_argument('--execute', action='store_true')
    p.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    p.add_argument('--authority', type=Path)
    p.add_argument('--review', type=Path)
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    spec = json_read(args.spec)
    if args.worker:
        if args.execute or args.output is None:
            raise ValueError('invalid worker arguments')
        worker(spec, args.output)
        return
    from synthetic_history_experiment import validate_spec
    inspection = validate_spec(spec)
    if not args.execute:
        print(json.dumps(inspection)); return
    if not all((args.authority, args.review, args.output)):
        raise ValueError('execution requires authority, review and output')
    supervise(spec, json_read(args.authority), json_read(args.review), args.output,
              Path(__file__).resolve().parents[1])


if __name__ == '__main__':
    main()
