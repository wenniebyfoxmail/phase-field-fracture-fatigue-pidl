"""Bounded, no-retry public archive intake. No image decoding or model execution."""
from pathlib import Path
import argparse, ctypes, json, os, re, signal, subprocess, sys, time
import psutil

LIBC = ctypes.CDLL(None) if sys.platform.startswith('linux') else None


def ranges(total, count):
    if total < 1 or not 1 <= count <= min(32, total):
        raise ValueError('Invalid range dimensions')
    return [(total * i // count, total * (i + 1) // count - 1) for i in range(count)]


def validate_header(text, start, end, total):
    blocks = re.split(r'\r?\n\r?\n', text.strip())
    final = next((b for b in reversed(blocks) if b.startswith('HTTP/')), '')
    lines = final.splitlines()
    if not lines or not re.match(r'^HTTP/\S+\s+206(?:\s|$)', lines[0]):
        raise ValueError('Server did not honor byte range with HTTP 206')
    headers = dict(line.split(':', 1) for line in lines[1:] if ':' in line)
    headers = {k.lower(): v.strip() for k, v in headers.items()}
    if headers.get('content-range') != f'bytes {start}-{end}/{total}':
        raise ValueError('Unexpected Content-Range')


def download(root, url, total, count=32, seconds=5300, rate='320K'):
    root = Path(root)
    parts = root / 'download_parts'
    parts.mkdir()  # Exclusive fresh directory; retain all partials on failure.
    output = root / 'dataset.zip'
    if output.exists():
        raise ValueError('Archive output already exists')
    children = []
    try:
        for i, (start, end) in enumerate(ranges(total, count)):
            body, header, error = [parts / f'part{i:02}.{ext}' for ext in ['bin', 'headers', 'stderr']]
            with error.open('xb') as stderr:
                parent_pid = os.getpid()
                blocked = {signal.SIGTERM, signal.SIGINT}
                previous_mask = signal.pthread_sigmask(signal.SIG_BLOCK, blocked)
                def child_setup():
                    if LIBC is not None:
                        if LIBC.prctl(1, signal.SIGTERM, 0, 0, 0) != 0 or os.getppid() != parent_pid:
                            os._exit(125)
                    signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
                try:
                    p = subprocess.Popen(['curl', '-sS', '--fail', '--retry', '0', '--range', f'{start}-{end}',
                                          '--max-time', str(seconds), '--limit-rate', rate,
                                          '--max-filesize', str(end-start+1),
                                          '--dump-header', str(header), '--output', str(body), url],
                                         cwd=root, stdout=subprocess.DEVNULL, stderr=stderr, preexec_fn=child_setup)
                    children.append((p, body, header, start, end))
                    p._intake_birth = psutil.Process(p.pid).create_time()
                finally:
                    signal.pthread_sigmask(signal.SIG_SETMASK, previous_mask)
        pending = list(children)
        while pending:
            for item in pending[:]:
                p, body, header, start, end = item
                status = p.poll()
                if status is None:
                    continue
                if status != 0:
                    raise RuntimeError(f'Range {start}-{end} failed with curl exit {status}')
                validate_header(header.read_text(), start, end, total)
                if body.stat().st_size != end - start + 1:
                    raise ValueError('Range byte count mismatch')
                pending.remove(item)
            time.sleep(.1)
        with output.open('xb') as dest:
            for _, body, _, _, _ in children:
                with body.open('rb') as src:
                    while block := src.read(8 * 1024 * 1024):
                        dest.write(block)
        if output.stat().st_size != total:
            raise ValueError('Assembled archive byte count mismatch')
        (root / 'range_intake_receipt.json').write_text(json.dumps({
            'complete': True, 'bytes': total, 'ranges': ranges(total, count),
            'connections': count, 'per_connection_rate': rate, 'automatic_retry': False,
            'canonical_sha256_check': 'required by controller before extraction'}) + '\n')
    except BaseException as e:
        # Persist the first trigger before signaling any owned child. Never retry a failed range.
        identities, verified, identity_errors = [], [], []
        for p, *_ in children:
            if p.poll() is None:
                try:
                    live = psutil.Process(p.pid)
                    identity = {'pid': p.pid, 'birth': live.create_time(), 'cwd': live.cwd(),
                                'cmdline': live.cmdline(), 'elapsed_s': time.time()-live.create_time()}
                    if identity['birth'] != p._intake_birth or identity['cwd'] != str(root.resolve()) or identity['cmdline'] != p.args:
                        raise RuntimeError('Owned intake child identity changed')
                    identities.append(identity)
                    verified.append(p)
                except psutil.NoSuchProcess:
                    pass
                except Exception as identity_error:
                    identity_errors.append({'pid': p.pid, 'error': repr(identity_error)})
        (root / 'range_intake_first_stop.json').write_text(json.dumps({'first_stop': repr(e),
            'automatic_retry': False, 'owned_child_identities': identities,
            'cleanup_identity_errors': identity_errors}) + '\n')
        for p in verified:
            if p.poll() is None:
                p.terminate()
        deadline = time.monotonic() + 5
        for p in verified:
            try:
                p.wait(timeout=max(.01, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                p.kill(); p.wait(timeout=5)
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--url', required=True)
    ap.add_argument('--bytes', type=int, required=True)
    ap.add_argument('--config', type=Path, required=True)
    a = ap.parse_args()
    config = json.loads(a.config.read_text())
    if a.root.resolve() != Path(config['remote_root']) or a.root.resolve() != Path('/mnt/data2/drtao/wennie') / config['run_ids'][0]:
        raise ValueError('Unexpected task root')
    intake = config['data_intake']
    expected = {'connections': 32, 'per_connection_rate': '320K', 'max_wall_seconds': 5400,
                'curl_max_seconds': 5300, 'cpu_cores': 4, 'retry': 0}
    if intake != expected or not a.url.startswith('https://'):
        raise ValueError('Intake differs from frozen configuration')
    # Network concurrency is I/O concurrency; physical CPU admission remains at four cores.
    os.sched_setaffinity(0, set(sorted(os.sched_getaffinity(0))[:intake['cpu_cores']]))
    def interrupted(signum, frame):
        raise InterruptedError(f'Intake signal {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    download(a.root, a.url, a.bytes, count=intake['connections'], seconds=intake['curl_max_seconds'],
             rate=intake['per_connection_rate'])


if __name__ == '__main__':
    main()
