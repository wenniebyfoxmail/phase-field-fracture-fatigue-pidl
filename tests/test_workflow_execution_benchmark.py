"""One offline benchmark: real Python children/receipts, injected control faults.

No MATLAB, MEX, FEM, GPU or SSH calls. --case reruns only failed named items.
"""
import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('watchdog', ROOT/'tools/s04_e036/gpu_watchdog.py')
watchdog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watchdog)


class ExecutionBenchmark(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='workflow-offline-')
        self.root = Path(self.tmp.name)
        self.attempt = self.root/'case_attempt.json'
        watchdog.new_json(self.attempt, {'scope': 'offline development fixture; no scientific authority'})

    def tearDown(self):
        self.tmp.cleanup()

    def run_child(self, code='print("child complete")', **kwargs):
        def settle(proc, identity):
            try:
                proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                proc.terminate(); proc.wait(timeout=1)
        return watchdog.run_captured([sys.executable, '-c', code], self.root,
            self.root, 'case', self.attempt, settle=kwargs.pop('settle', settle), **kwargs)

    def test_real_child_to_saved_result(self):
        result = self.run_child('import json; from pathlib import Path; '
            'Path("output.json").write_text(json.dumps({"value":42})); print("actual child stdout")')
        self.assertEqual(result['execution_state'], 'completed')
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual(json.loads((self.root/'output.json').read_text()), {'value': 42})
        self.assertIn('actual child stdout', (self.root/'case_stdout.log').read_text())
        self.assertEqual(json.loads((self.root/'case_started.json').read_text())['cwd'], str(self.root.resolve()))
        self.assertTrue((self.root/'case_finished.json').is_file())
        self.assertEqual(result['resource_measurement'], {'cpu_seconds': None, 'gpu_seconds': None})

    def test_real_worker_exception_is_preserved(self):
        result = self.run_child('raise ValueError("worker fixture error")')
        self.assertEqual(result['execution_state'], 'worker_failure')
        self.assertEqual(result['exit_code'], 1)
        self.assertIn('ValueError: worker fixture error', (self.root/'case_stderr.log').read_text())

    def test_ambiguous_spawn_is_unknown_not_free_retry(self):
        calls = []
        def ambiguous(*args, **kwargs):
            calls.append(args); raise OSError('injected lost spawn acknowledgement')
        result = self.run_child(popen=ambiguous)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result['execution_state'], 'unknown')
        self.assertIsNone(result['exit_code'])
        self.assertIsNone(result['charged_gpu_seconds'])
        self.assertFalse(result['reservation_released'])
        self.assertIn('OSError: injected lost spawn acknowledgement', (self.root/'case_wrapper_error.log').read_text())
        self.assertFalse((self.root/'case_finished.json').exists())
        with self.assertRaisesRegex(RuntimeError, 'unfinished attempt'):
            watchdog.available_seconds(self.root, 100)

    def test_error_after_real_spawn_preserves_pid(self):
        def callback(proc):
            raise RuntimeError('injected observer error after producer creation')
        result = self.run_child(on_started=callback)
        self.assertEqual(result['execution_state'], 'wrapper_failure')
        self.assertIsInstance(result['pid'], int)
        self.assertEqual(result['exit_code'], 0)
        self.assertTrue((self.root/'case_started.json').is_file())
        self.assertIn('observer error', result['wrapper_traceback'])

    def test_unverified_cleanup_retains_reservation(self):
        def unknown_cleanup(proc, identity):
            proc.wait(timeout=1); raise RuntimeError('injected ownership visibility loss')
        result = self.run_child(settle=unknown_cleanup)
        self.assertEqual(result['execution_state'], 'unknown')
        self.assertEqual(result['exit_code'], 0)  # exit known, descendants unverified
        self.assertFalse(result['reservation_released'])
        with self.assertRaises(RuntimeError):
            watchdog.available_seconds(self.root, None)

    def test_task_continuation_deadline_and_unknown_cost(self):
        start = dt.datetime(2026, 10, 25, tzinfo=dt.timezone.utc)
        auth = dict(wall_seconds=100, task_clock=dict(start_utc=start.isoformat(),
            total_wall_seconds=60, cleanup_seconds=10, waiting_included=True))
        self.assertEqual(watchdog.execution_wall_allowance(auth, start+dt.timedelta(seconds=20)), 30)
        self.assertEqual(watchdog.execution_wall_allowance(auth, start+dt.timedelta(seconds=40)), 10)
        auth['task_clock']['hard_end_utc'] = (start+dt.timedelta(seconds=45)).isoformat()
        self.assertEqual(watchdog.execution_wall_allowance(auth, start+dt.timedelta(seconds=40)), 0)
        calls = []
        def forbidden(*args, **kwargs):
            calls.append(args); raise AssertionError('expired task must not spawn')
        result = self.run_child(wall_seconds=0, popen=forbidden)
        self.assertEqual(result['execution_state'], 'not_started_deadline')
        self.assertEqual(calls, [])
        self.assertIsNone(result['exit_code'])
        finished = self.root/'case_finished.json'
        receipt = json.loads(finished.read_text()); receipt['charged_gpu_seconds'] = None
        finished.write_text(json.dumps(receipt))
        with self.assertRaises((TypeError, ValueError)):
            watchdog.available_seconds(self.root, 100)

    def test_real_child_timeout_is_control_failure(self):
        def settle(proc, identity):
            if proc.poll() is None:
                proc.terminate()
            proc.wait(timeout=1)
        result = self.run_child('import time; time.sleep(30)', wall_seconds=.03, settle=settle)
        self.assertEqual(result['execution_state'], 'wrapper_failure')
        self.assertIn('TimeoutExpired', result['wrapper_traceback'])
        self.assertIsNotNone(result['exit_code'])
        self.assertNotEqual(result['exit_code'], 0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--case', action='append', help='rerun named failed items only')
    args = parser.parse_args()
    suite = (unittest.TestSuite(ExecutionBenchmark(name) for name in args.case) if args.case
             else unittest.TestLoader().loadTestsFromTestCase(ExecutionBenchmark))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    payload = dict(benchmark='existing E036 captured execution control path',
        command=[sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]],
        tests_run=result.testsRun, success=result.wasSuccessful(),
        failed_cases=[t._testMethodName for t, _ in result.failures+result.errors],
        actual_calls=['Python child creation', 'stdout/stderr capture', 'PID and immutable receipt writing',
                      'local output save/readback', 'owned direct-child timeout termination'],
        simulated=['ambiguous spawn acknowledgement', 'post-spawn observer error',
                   'ownership visibility loss', 'task clock timestamps'],
        not_executed=['GPU admission/nvidia-smi', 'Linux /proc ownership traversal', 'Windows PowerShell wrapper',
                      'MATLAB initial recovery', 'FEM mechanics', 'loaded phase-field assembly', 'MEX', 'training', 'SSH'],
        native_tools={name: shutil.which(name) for name in ['matlab','octave','pwsh']}, scientific_result=False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2)+'\n')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
