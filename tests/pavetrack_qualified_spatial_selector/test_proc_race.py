"""Regression for Linux proc exit races; manual mocks, no model/data/GPU."""
import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/pavetrack_qualified_spatial_selector'))
import e029_system_proc as proc
class ProcExitRace(unittest.TestCase):
    def process(self):
        p=object.__new__(proc.Process);p.pid=123;p.birth=7;return p
    def test_stat_exit_forms_are_normalised(self):
        for exc in [FileNotFoundError(2,'gone'),ProcessLookupError(3,'gone')]:
            with self.subTest(exc=type(exc).__name__),patch.object(Path,'read_text',side_effect=exc):
                with self.assertRaises(proc.NoSuchProcess):proc.stat(123)
    def test_exit_during_identity_read_is_normalised(self):
        for method,target in [('uids',(Path,'stat')),('cmdline',(Path,'read_bytes')),('cwd',(proc.os,'readlink'))]:
            for exc in [FileNotFoundError(2,'gone'),ProcessLookupError(3,'gone')]:
                with self.subTest(method=method,exc=type(exc).__name__),patch.object(proc.Process,'_stat',return_value={'birth':7}),patch.object(*target,side_effect=exc):
                    with self.assertRaises(proc.NoSuchProcess):getattr(self.process(),method)()
    def test_exit_after_signal_identity_check_is_normalised(self):
        with patch.object(proc.Process,'_stat',return_value={'birth':7}),patch.object(proc.os,'kill',side_effect=ProcessLookupError(3,'gone')):
            with self.assertRaises(proc.NoSuchProcess):self.process().send_signal(15)
    def test_global_enumeration_skips_exited_unrelated_pid(self):
        with patch.object(proc.os,'listdir',return_value=['123']),patch.object(Path,'read_text',side_effect=ProcessLookupError(3,'gone')):
            self.assertEqual(list(proc.process_iter()),[])
    def test_permissions_and_unexpected_io_still_stop(self):
        with patch.object(Path,'read_text',side_effect=PermissionError(13,'denied')):
            with self.assertRaises(proc.AccessDenied):proc.stat(123)
        with patch.object(Path,'read_text',side_effect=OSError(5,'io error')):
            with self.assertRaises(OSError):proc.stat(123)
    def test_pid_reuse_still_refuses_signal(self):
        with patch.object(proc,'stat',return_value={'birth':8}),patch.object(proc.os,'kill') as kill:
            with self.assertRaises(proc.NoSuchProcess):self.process().send_signal(15)
            kill.assert_not_called()
if __name__=='__main__':unittest.main()
