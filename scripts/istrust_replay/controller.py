"""Bound a single producer replay process group; first failure ends the batch."""
from __future__ import annotations
import argparse, ctypes, hashlib, json, os, signal, subprocess, sys, tarfile, time, zipfile
from pathlib import Path
import psutil


def emit(path, record):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(record, indent=2) + '\n')
    tmp.replace(path)


def tree_bytes(root):
    return sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink())


def stop_group(process):
    # This group was created by Popen(start_new_session=True), never inferred from username.
    if getattr(process, '_istrust_stopped', False):
        return
    def descendants_alive():
        for pid, born in getattr(process, '_istrust_known_children', []):
            try:
                p = psutil.Process(pid)
                if p.create_time() == born and p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                    return True
            except psutil.NoSuchProcess:
                pass
        return False
    if process.poll() is not None and not descendants_alive():
        process.wait()
        process._istrust_stopped = True
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        process.wait(timeout=5)
        process._istrust_stopped = True
        return
    except PermissionError:
        # Darwin may report EPERM for a group whose leader has just exited.
        # Accept this only after proving the child exited and no known descendant is alive.
        process.wait(timeout=.2)
        if descendants_alive():
            raise
        process._istrust_stopped = True
        return
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        pass
    if process.poll() is None or descendants_alive():
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    process.wait(timeout=5)
    process._istrust_stopped = True


def supervise(command, root, config, receipt_name='worker_receipt.json', gpu_uuid=None):
    started = time.monotonic()
    record = {'command': command, 'execution_status': 'prepared', 'start_unix': time.time()}
    receipt = root / receipt_name
    with (root / (receipt_name + '.stdout')).open('w') as stdout, (root / (receipt_name + '.stderr')).open('w') as stderr:
        parent_pid = os.getpid()
        def child_setup():
            if sys.platform.startswith('linux'):
                if ctypes.CDLL(None).prctl(1, signal.SIGTERM, 0, 0, 0) != 0:
                    os._exit(125)
                if os.getppid() != parent_pid:
                    os._exit(125)
        process = subprocess.Popen(command, cwd=root, stdout=stdout, stderr=stderr, start_new_session=True, preexec_fn=child_setup)
        record.update(pid=process.pid, pgid=process.pid, execution_status='running')
        emit(receipt, record)
        maximum_rss = 0
        try:
            while True:
                elapsed = time.monotonic() - started
                status = process.poll()
                try:
                    parent = psutil.Process(process.pid)
                    owned = [parent] + parent.children(recursive=True)
                    process._istrust_known_children = [(p.pid, p.create_time()) for p in owned[1:] if p.is_running()]
                    rss = sum(p.memory_info().rss for p in owned if p.is_running())
                except psutil.NoSuchProcess:
                    owned, rss = [], 0
                maximum_rss = max(maximum_rss, rss)
                size = tree_bytes(root)
                reason = None
                if elapsed > config['max_wall_seconds']:
                    reason = 'wall_time_limit'
                elif maximum_rss > config['max_rss_bytes']:
                    reason = 'rss_limit'
                elif size > config['max_task_bytes']:
                    reason = 'storage_limit'
                # Limits are checked even at exit, so an over-budget clean exit cannot pass.
                if reason:
                    record.update(execution_status='failed', first_stop=reason, elapsed_s=elapsed,
                                  peak_sampled_rss=maximum_rss, task_bytes=size)
                    emit(receipt, record)
                    stop_group(process)
                    raise RuntimeError(reason)
                if status is not None:
                    record.update(execution_status='succeeded' if status == 0 else 'failed',
                                  returncode=status, elapsed_s=elapsed, peak_sampled_rss=maximum_rss,
                                  task_bytes=size)
                    emit(receipt, record)
                    if status != 0:
                        raise RuntimeError(f'Child exit {status}; no automatic retry')
                    break
                if gpu_uuid:
                    query = subprocess.run(['nvidia-smi', '--query-compute-apps=pid,gpu_uuid', '--format=csv,noheader,nounits'],
                                           capture_output=True, text=True, timeout=15, check=True)
                    pids = {p.pid for p in owned}
                    for line in query.stdout.splitlines():
                        pid, uuid = [s.strip() for s in line.split(',')]
                        if uuid == gpu_uuid and int(pid) not in pids:
                            raise RuntimeError(f'GPU shared-resource conflict: foreign PID {pid}')
                time.sleep(min(5, max(.02, config['max_wall_seconds'] / 10)))
        except BaseException as error:
            if record.get('execution_status') != 'failed':
                record.update(execution_status='failed', first_stop=repr(error), elapsed_s=time.monotonic()-started,
                              peak_sampled_rss=maximum_rss)
                emit(receipt, record)
            stop_group(process)
            raise
    return record


def verify(path, expected):
    actual = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(16 * 1024 * 1024), b''):
            actual.update(block)
    if actual.hexdigest() != expected:
        raise ValueError(f'Identity mismatch: {path.name}')


def safe_tar(path, dest):
    with tarfile.open(path) as archive:
        for member in archive.getmembers():
            p = Path(member.name)
            if p.is_absolute() or '..' in p.parts or not (member.isdir() or member.isfile()):
                raise ValueError('Unsafe source archive member')
        archive.extractall(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--python', type=Path, required=True)
    ap.add_argument('--config', type=Path, required=True)
    ap.add_argument('--lock', type=Path, required=True)
    ap.add_argument('--gpu-uuid', required=True)
    ap.add_argument('--max-seconds', type=float)
    args = ap.parse_args()
    root = args.root.resolve()
    config, lock = json.loads(args.config.read_text()), json.loads(args.lock.read_text())
    if root != Path(config['remote_root']) or root != Path('/mnt/data2/drtao/wennie') / config['run_ids'][0]:
        raise ValueError('Unexpected producer root')
    if args.max_seconds is not None:
        if not 0 < args.max_seconds <= config['max_wall_seconds']:
            raise ValueError('Invalid remaining batch allowance')
        config = dict(config, max_wall_seconds=args.max_seconds)
    def interrupted(signum, frame):
        raise InterruptedError(f'Controller signal {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        start = time.monotonic()
        archive = root / 'dataset.zip'
        if archive.exists():
            raise ValueError('Fresh run root unexpectedly contains a dataset archive')
        # Public inbound download, bounded write rate; no global installation or shared data mutation.
        download_config = dict(config, max_wall_seconds=min(config['data_intake']['max_wall_seconds'], config['max_wall_seconds']))
        intake = Path(__file__).with_name('download_ranges.py')
        supervise([str(args.python), '-u', str(intake), '--root', str(root),
                   '--url', lock['dataset_download_url'], '--bytes', str(lock['dataset_bytes']), '--config', str(args.config)],
                  root, download_config, 'download_receipt.json')
        if archive.stat().st_size != lock['dataset_bytes']:
            raise ValueError('Dataset byte count mismatch')
        verify(archive, lock['dataset_sha256'])
        source_tar = root / lock['source_archive']
        verify(source_tar, lock['source_archive_sha256'])
        source = root / 'author_source'
        source.mkdir()
        safe_tar(source_tar, source)
        with zipfile.ZipFile(archive) as z:
            if len(z.infolist()) != 2417:
                raise ValueError('Unexpected archive member count')
            for member in z.infolist():
                p = Path(member.filename)
                if p.is_absolute() or '..' in p.parts or p.parts[0] != 'dataset' or ((member.external_attr >> 16) & 0o170000) == 0o120000:
                    raise ValueError('Unsafe dataset member')
            z.extractall(root)  # CRC verified on full reads; previously verified full archive identity.
        emit(root / 'input_receipt.json', {'dataset_sha256': lock['dataset_sha256'], 'images': 2416,
                                           'source_archive_sha256': lock['source_archive_sha256'],
                                           'author_commit': lock['author_commit'], 'extracted': True})
        remaining = config['max_wall_seconds'] - (time.monotonic() - start)
        if remaining <= 0:
            raise RuntimeError('Preparation exhausted total time budget')
        limits = dict(config, max_wall_seconds=remaining)
        script = Path(__file__).with_name('replay.py')
        record = supervise([str(args.python), '-u', str(script), '--root', str(root), '--config', str(args.config),
                            '--source', str(source), '--dataset', str(root / 'dataset')],
                           root, limits, gpu_uuid=args.gpu_uuid)
        completion = json.loads((root / 'completion.json').read_text())
        if not completion['complete']:
            raise ValueError('Missing replay completion')
        emit(root / 'controller_completion.json', {'complete': True, 'elapsed_s': time.monotonic() - start,
                                                  'worker': record, 'training_steps': 0})
    except BaseException as error:
        emit(root / 'first_stop.json', {'first_stop': repr(error), 'time_unix': time.time(),
                                      'automatic_retry': False, 'observation_uncertainty_testing': False})
        raise


if __name__ == '__main__':
    main()
