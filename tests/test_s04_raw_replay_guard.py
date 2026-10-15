import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / 'SENS_tensile'))

import s04_raw_replay_guard as guard


class ReplayGuardTests(unittest.TestCase):
    def test_missing_authorization_fails_before_output_or_sidecars(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            output = base / 'S04-E022-R001'
            with self.assertRaises(FileNotFoundError):
                guard.execute(base / 'S04-E021-R001', output, base / 'missing.json')
            self.assertEqual(list(base.iterdir()), [])

    def test_mock_children_complete_in_replay_then_report_order(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / 'S04-E021-R001'
            output = base / 'S04-E022-R001'
            approval = base / 'approval.json'
            approval.write_text('{}')
            launched = []

            class Child:
                def __init__(self, phase):
                    self.pid = 90000001 + len(launched)
                    self.returncode = 0
                    self.phase = phase
                def poll(self):
                    return 0

            def spawn(command, **kwargs):
                phase = 'replay' if command[1].endswith('s04_raw_replay.py') else 'report'
                self.assertEqual(kwargs['cwd'], ROOT)
                self.assertTrue(kwargs['start_new_session'])
                if phase == 'replay':
                    output.mkdir()
                else:
                    self.assertTrue(output.is_dir())
                launched.append(phase)
                return Child(phase)

            process = mock.Mock()
            process.memory_info.return_value.rss = 1024
            process.children.return_value = []
            approved = {'run_id': output.name}
            with mock.patch('s04_raw_replay.authorization', return_value=approved), \
                 mock.patch.object(guard.subprocess, 'check_output', side_effect=['abc123\n', '']), \
                 mock.patch.object(guard.subprocess, 'Popen', side_effect=spawn), \
                 mock.patch.object(guard.psutil, 'Process', return_value=process), \
                 contextlib.redirect_stdout(io.StringIO()):
                code = guard.execute(source, output, approval)
            self.assertEqual(code, 0)
            self.assertEqual(launched, ['replay', 'report'])
            receipt = json.loads((base / 'S04-E022-R001_guard_receipt.json').read_text())
            self.assertEqual(receipt['status'], 'COMPLETED')
            self.assertFalse(receipt['fit_performed'])
            self.assertFalse(receipt['confirmation_accessed'])


if __name__ == '__main__':
    unittest.main()
