"""Deployment only. Payload travels as framed binary stdin, never substituted into code.

No scientific imports, source changes, original input reads or fits. Remote execution
requires the exact existing RunID. Import is inert and permits local source-only tests.
"""
from pathlib import Path
import argparse
import datetime
import gzip
import hashlib
import io
import json
import os
import socket
import struct
import subprocess
import sys
import tarfile

ROOT = Path('/mnt/data2/drtao/wennie/IU-OUTPUT-CALIBRATION-C27A25-20261020-R001')
SOURCE = '4297ddc4d16d2e410a7b7a24a0888fa9d2bfa481'
ARCHIVE = 'f76d5c65397f6eadc4b358b3366c33631fcf9a3fb72ef0f7325657ba11d27613'
PACKAGE = '0503d28e8417cb9a2d4a410f90f8faa32fcb9dddd42a56bd82068a196f5c0d63'
CONFIG = '8a5ce65a16f9fadb833787f1c66c8f0e050c9f9434cdc47f914461841f4d3f57'


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_exclusive(path, data):
    if not isinstance(data, bytes):
        data = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode()
    with Path(path).open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def read_exact(stream, count):
    chunks = []
    while count:
        chunk = stream.read(min(count, 1024 * 1024))
        if not chunk:
            raise EOFError('truncated framed deployment payload')
        chunks.append(chunk)
        count -= len(chunk)
    return b''.join(chunks)


def frame(archive, authority):
    wire = gzip.compress(archive, mtime=0)
    header = json.dumps({'encoding': 'gzip', 'wire_bytes': len(wire),
                         'wire_sha256': sha(wire), 'authority': authority},
                        ensure_ascii=False).encode()
    if len(header) > 32768:
        raise ValueError('authority frame too large')
    return struct.pack('!I', len(header)) + header + wire


def decode(stream):
    size = struct.unpack('!I', read_exact(stream, 4))[0]
    if not 0 < size <= 32768:
        raise ValueError('invalid header length')
    h = json.loads(read_exact(stream, size))
    if h['encoding'] != 'gzip' or type(h['wire_bytes']) is not int or not 0 < h['wire_bytes'] <= 2**20:
        raise ValueError('invalid wire envelope')
    wire = read_exact(stream, h['wire_bytes'])
    if sha(wire) != h['wire_sha256']:
        raise ValueError('wire hash mismatch')
    # Known exact archive is less than1MiB; limit decompression before allocating extras.
    with gzip.GzipFile(fileobj=io.BytesIO(wire)) as z:
        raw = z.read(921601)
        if len(raw) != 921600 or z.read(1):
            raise ValueError('archive size mismatch')
    if sha(raw) != ARCHIVE:
        raise ValueError('reviewed archive hash mismatch')
    return raw, h['authority']


def source_members(raw, authority):
    if len(raw) != 921600 or sha(raw) != ARCHIVE:
        raise ValueError('reviewed archive identity')
    with tarfile.open(fileobj=io.BytesIO(raw)) as t:
        members = t.getmembers()
        if any(not m.isfile() or Path(m.name).name != m.name for m in members):
            raise ValueError('unsafe archive member')
        files = {m.name: t.extractfile(m).read() for m in members}
        if len(files) != len(members):
            raise ValueError('duplicate archive member')
    lock = json.loads(files['package_lock.json'])
    if set(files) != set(lock['files']) | {'package_lock.json'}:
        raise ValueError('sealed source set')
    if sha(json.dumps(lock, sort_keys=True, separators=(',', ':')).encode()) != PACKAGE:
        raise ValueError('package identity')
    for name, expected in lock['files'].items():
        if sha(files[name]) != expected:
            raise ValueError('source member identity: ' + name)
    if sha(files['config.json']) != CONFIG:
        raise ValueError('config identity')
    cfg = json.loads(files['config.json'])
    # The sealed package performs the full schema check during formal launch.
    expected = {'source_commit': SOURCE, 'package_sha256': PACKAGE, 'config_sha256': CONFIG,
                'run_id': ROOT.name, 'run_root': str(ROOT), 'budget': cfg['approved_budget'],
                'category_caps': cfg['category_caps'], 'max_attempts': 1}
    if any(authority.get(k) != v for k, v in expected.items()):
        raise ValueError('deployment authority identity')
    return files


def deploy(root, raw, authority):
    """All identities checked before first mutation; root never reused or overwritten."""
    files = source_members(raw, authority)
    root = Path(root)
    if root.exists() or root.is_symlink():
        raise FileExistsError('remote root already exists; do not overwrite or relaunch')
    root.mkdir(exist_ok=False)
    code = root / 'code'
    code.mkdir()
    for name, data in files.items():
        write_exclusive(code / name, data)
    write_exclusive(root / 'source_package.tar', raw)
    write_exclusive(root / 'execution_authority.json', authority)
    result = {'status': 'EXACT_REVIEWED_ARCHIVE_DEPLOYED_NO_LAUNCH_YET', 'utc': utc(),
              'hostname': socket.gethostname(), 'source_commit': SOURCE,
              'package_sha256': PACKAGE, 'config_sha256': CONFIG, 'archive_sha256': ARCHIVE,
              'root': str(root), 'source_files': len(files), 'scientific_inputs_read': False,
              'launch_submitted': False}
    write_exclusive(root / 'deployment_receipt.json', result)
    return result


def preflight():
    result = {'utc': utc(), 'hostname': socket.gethostname(), 'root_exists': ROOT.exists(),
              'root_is_symlink': ROOT.is_symlink(), 'matching_processes': [],
              'canonical_parent': str(ROOT.parent.resolve()),
              'mounts': subprocess.run(['df', '-h', '/', '/mnt/data2', '/mnt/data3'],
                                       capture_output=True, text=True, check=True).stdout,
              'load': os.getloadavg(), 'logical_cpus': os.cpu_count(),
              'mem_available': [s for s in Path('/proc/meminfo').read_text().splitlines()
                                if s.startswith('MemAvailable:')]}
    # Our own -c script (also in an ancestor shell argv) contains ROOT as source
    # text. Exclude this query's ancestor chain, never unrelated matching jobs.
    ancestors = {os.getpid()}
    parent = os.getppid()
    while parent > 1 and parent not in ancestors:
        ancestors.add(parent)
        try:
            stat = Path('/proc') / str(parent) / 'stat'
            text = stat.read_text()
            parent = int(text[text.rfind(')') + 2:].split()[1])
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            break
    for d in Path('/proc').iterdir():
        if not d.name.isdigit() or int(d.name) in ancestors:
            continue
        try:
            cmd = (d / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
            if ROOT.name in cmd:
                result['matching_processes'].append({'pid': int(d.name), 'cmdline': cmd,
                                                     'cwd': str((d / 'cwd').resolve())})
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    if ROOT.exists():
        result['root_entries'] = sorted(p.name for p in ROOT.iterdir())
    # Inspect-only if unknown state exists. Caller never deletes it.
    result['fresh'] = (not result['root_exists'] and not result['root_is_symlink']
                       and not result['matching_processes']
                       and result['canonical_parent'] == '/mnt/data2/drtao/wennie')
    return result


def launch():
    code = ROOT / 'code'
    lock = json.loads((code / 'package_lock.json').read_bytes())
    for name, expected in lock['files'].items():
        if Path(name).name != name or sha((code / name).read_bytes()) != expected:
            raise ValueError('prelaunch sealed source mismatch ' + name)
    if sha(json.dumps(lock, sort_keys=True, separators=(',', ':')).encode()) != PACKAGE:
        raise ValueError('prelaunch package mismatch')
    if {p.name for p in ROOT.iterdir()} != {'code', 'source_package.tar',
                                           'execution_authority.json', 'deployment_receipt.json'}:
        raise RuntimeError('unexpected root entries before launch; no duplicate launch')
    command = json.loads((code / 'launch_command.json').read_bytes())
    expected = ['/usr/bin/python3', '-W', 'error', str(code / 'launch.py'), '--config',
                str(code / 'config.json'), '--approval-receipt', str(ROOT / 'execution_authority.json')]
    if command['argv'] != expected:
        raise ValueError('frozen launch argv mismatch')
    request = {'utc': utc(), 'source_commit': SOURCE, 'package_sha256': PACKAGE,
               'command': expected, 'cwd': str(code), 'gpu': None,
               'mode': 'nohup; new session; stdin devnull; exclusive root logs'}
    write_exclusive(ROOT / 'client_launch_request.json', request)
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES='', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
               MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
    with (ROOT / 'launch.stdout').open('xb') as stdout, (ROOT / 'launch.stderr').open('xb') as stderr:
        child = subprocess.Popen(['nohup'] + expected, cwd=code, env=env,
                                 stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                 start_new_session=True, close_fds=True)
    result = {**request, 'status': 'LAUNCH_SUBMITTED_NOT_YET_ADMITTED',
              'watchdog_pid': child.pid, 'submitted_utc': utc()}
    write_exclusive(ROOT / 'client_launch_receipt.json', result)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=('preflight', 'deploy', 'launch'))
    a = p.parse_args()
    if sys.platform != 'linux' or socket.gethostname() != 'GPUServer8':
        raise RuntimeError('only GPUServer8 Linux producer')
    if a.mode == 'preflight':
        result = preflight()
    elif a.mode == 'deploy':
        result = deploy(ROOT, *decode(sys.stdin.buffer))
    else:
        result = launch()
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
