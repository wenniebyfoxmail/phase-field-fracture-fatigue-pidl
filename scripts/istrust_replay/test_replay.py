"""Lightweight manifest/lifecycle checks. No real model forward or training."""
import importlib.util,json,sys,tempfile,tarfile,io,unittest,csv,random,time
from pathlib import Path
import psutil
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import replay,controller

class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/research_hq/identification_uncertainty_prediction_20261006/istrust_reproduction_preparation_20261020/image_manifest.csv')
        with p.open() as f:
            cls.names=[Path(r['filename']).name for r in csv.DictReader(f)]
    def test_complete_archive_order_invariance(self):
        baseline=replay.ordered_groups(self.names)
        shuffled=list(self.names);random.Random(74).shuffle(shuffled)
        self.assertEqual(baseline,replay.ordered_groups(shuffled))
        self.assertEqual(baseline,replay.ordered_groups(reversed(self.names)))
        self.assertEqual(len(baseline),14)
    def test_physical_folds_and_declared_windows(self):
        groups=replay.ordered_groups(self.names)
        config=json.loads((HERE.parents[1]/'docs/research/S02/S02-E007/config.json').read_text())
        for i,test in enumerate(config['fold_test_specimens']):
            te=[g for g in groups if g['specimen']==test]
            tr=[g for g in groups if g['specimen']!=test]
            self.assertEqual({g['camera'] for g in te},{0,1})
            self.assertFalse({g['specimen'] for g in tr}&{g['specimen'] for g in te})
            self.assertEqual(len(replay.windows(te)),config['expected_test_windows'][i])
            self.assertEqual(len(replay.windows(tr)),config['expected_train_windows'][i])
    def test_target_after_inputs_and_fractional_labels(self):
        groups=replay.ordered_groups(self.names)
        for g in groups:
            row=replay.windows([g])[0]
            self.assertEqual(row['input_files'],[g['rows'][i][1] for i in [0,3,6]])
            self.assertEqual(row['target_file'],g['rows'][7][1])
            self.assertGreater(row['latest_input_rul_s'],row['target_s'])
            self.assertNotIn(row['target_file'],row['input_files'])
    def test_singleton_mc_shape(self):
        import torch
        batch=torch.stack([torch.ones(1,1) for _ in range(40)],dim=-1).reshape(1,40)
        self.assertEqual(tuple(batch.shape),(1,40))
    def test_duplicate_label_rejected(self):
        names=self.names+['A003_0_0_00.tiff']
        with self.assertRaises(ValueError):replay.ordered_groups(names)

class LifecycleTests(unittest.TestCase):
    def limits(self,seconds):return {'max_wall_seconds':seconds,'max_rss_bytes':2*1024**3,'max_task_bytes':1024**3}
    def test_success_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            row=controller.supervise([sys.executable,'-c','print(1)'],Path(d),self.limits(5))
            self.assertEqual(row['execution_status'],'succeeded')
    def test_failed_exit_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):controller.supervise([sys.executable,'-c','raise SystemExit(3)'],Path(d),self.limits(5))
            row=json.loads((Path(d)/'worker_receipt.json').read_text())
            self.assertEqual(row['returncode'],3)
            self.assertEqual(row['execution_status'],'failed')
    def test_timeout_stops_owned_descendant(self):
        with tempfile.TemporaryDirectory() as d:
            script="import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);Path('child.pid').write_text(str(p.pid));time.sleep(30)"
            with self.assertRaises(RuntimeError):controller.supervise([sys.executable,'-c',script],Path(d),self.limits(.5))
            pid=int((Path(d)/'child.pid').read_text())
            time.sleep(.1)
            if psutil.pid_exists(pid):self.assertEqual(psutil.Process(pid).status(),psutil.STATUS_ZOMBIE)
            row=json.loads((Path(d)/'worker_receipt.json').read_text())
            self.assertEqual(row['first_stop'],'wall_time_limit')
    def test_over_budget_clean_exit_cannot_pass(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(RuntimeError):controller.supervise([sys.executable,'-c','pass'],Path(d),self.limits(.000001))
            self.assertEqual(json.loads((Path(d)/'worker_receipt.json').read_text())['first_stop'],'wall_time_limit')
    def test_source_archive_paths_and_types(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);dest=root/'dest';dest.mkdir()
            for name,kind in [('../outside',tarfile.REGTYPE),('link',tarfile.SYMTYPE)]:
                f=root/'bad.tar'
                with tarfile.open(f,'w') as t:
                    member=tarfile.TarInfo(name);member.type=kind
                    t.addfile(member)
                with self.assertRaises(ValueError):controller.safe_tar(f,dest)
            self.assertFalse((root/'outside').exists())
    def test_identity_mismatch_stops(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input';p.write_bytes(b'wrong')
            with self.assertRaises(ValueError):controller.verify(p,'0'*64)

if __name__=='__main__':unittest.main()
