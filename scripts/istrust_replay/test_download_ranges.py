"""Synthetic HTTP range/cleanup checks; no scientific images or model execution."""
from pathlib import Path
import contextlib, hashlib, http.server, json, re, sys, tempfile, threading, time, unittest
import psutil
sys.path.insert(0, str(Path(__file__).resolve().parent))
import download_ranges


@contextlib.contextmanager
def server(payload, mode='range'):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            start, end = map(int, re.fullmatch(r'bytes=(\d+)-(\d+)', self.headers['Range']).groups())
            if mode == 'failure' and start == 0:
                self.send_error(404); return
            if mode == 'failure': time.sleep(5)
            body = payload[start:end+1]
            if mode == 'ignore': body = payload
            if mode == 'short': body = body[:-1]
            self.send_response(200 if mode == 'ignore' else 206)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Content-Range', f'bytes {start+1 if mode == "wrong" else start}-{end}/{len(payload)}')
            self.end_headers()
            try: self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError): pass
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    srv.daemon_threads = True
    thread = threading.Thread(target=srv.serve_forever, daemon=True); thread.start()
    try: yield f'http://127.0.0.1:{srv.server_port}/archive'
    finally: srv.shutdown(); srv.server_close(); thread.join()


class IntakeTests(unittest.TestCase):
    def test_exact_assembly_independent_sha(self):
        payload=bytes(range(256))*1024
        with tempfile.TemporaryDirectory() as d, server(payload) as url:
            root=Path(d)
            download_ranges.download(root, url, len(payload), count=4, seconds=5, rate='1M')
            self.assertEqual(hashlib.sha256((root/'dataset.zip').read_bytes()).digest(), hashlib.sha256(payload).digest())
            self.assertTrue(json.loads((root/'range_intake_receipt.json').read_text())['complete'])
    def test_ignored_wrong_and_short_ranges_stop_before_assembly(self):
        for mode in ['ignore', 'wrong', 'short']:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d, server(b'x'*65536, mode) as url:
                root=Path(d)
                with self.assertRaises((ValueError, RuntimeError)):
                    download_ranges.download(root, url, 65536, count=4, seconds=5, rate='1M')
                self.assertFalse((root/'dataset.zip').exists())
                self.assertFalse(json.loads((root/'range_intake_first_stop.json').read_text())['automatic_retry'])
    def test_first_failure_cleans_slow_owned_children(self):
        with tempfile.TemporaryDirectory() as d, server(b'x'*65536, 'failure') as url:
            root=Path(d);started=time.monotonic()
            with self.assertRaises(RuntimeError):
                download_ranges.download(root, url, 65536, count=4, seconds=10, rate='1M')
            self.assertLess(time.monotonic()-started, 4)
            record=json.loads((root/'range_intake_first_stop.json').read_text())
            self.assertFalse(record['cleanup_identity_errors'])
            self.assertTrue(record['owned_child_identities'])
            for item in record['owned_child_identities']:
                self.assertFalse(psutil.pid_exists(item['pid']))
    def test_range_partition_has_no_missing_or_repeated_bytes(self):
        for total in [1, 2, 31, 1000]:
            for count in [1, min(total, 32)]:
                parts=download_ranges.ranges(total,count)
                self.assertEqual([n for a,b in parts for n in range(a,b+1)],list(range(total)))
        with self.assertRaises(ValueError): download_ranges.ranges(3,4)


if __name__ == '__main__': unittest.main()
