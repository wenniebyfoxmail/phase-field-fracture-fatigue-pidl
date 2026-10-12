import importlib.util,math,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];spec=importlib.util.spec_from_file_location('quality_run',ROOT/'scripts/pavetrack_quality_cv/run.py');q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
class QualityTests(unittest.TestCase):
 def setUp(self):self.r={'width':100,'height':50,'crack_boxes_xyxy':[[10,10,30,20]]};self.row={'box_xyxy':[10,10,30,20],'probability':.9,'proposer_confidence':.2}
 def test_geometry_normalized_without_gt(self):
  f=q.features(self.row,self.r);self.assertEqual(len(f),8);self.assertAlmostEqual(f[4],.2);self.assertAlmostEqual(f[5],.2);self.assertAlmostEqual(f[6],.2);self.assertAlmostEqual(f[7],.3)
  other=dict(self.r,crack_boxes_xyxy=[]);self.assertEqual(f,q.features(self.row,other))
 def test_partial_overlap_is_invalid_detection(self):
  row=dict(self.row,box_xyxy=[10,10,17,20]);self.assertEqual(q.valid_label(row,self.r),0)
  self.assertEqual(q.valid_label(self.row,self.r),1)
 def test_empty_target_is_invalid(self):self.assertEqual(q.valid_label(self.row,dict(self.r,crack_boxes_xyxy=[])),0)
 def test_score_uses_frozen_scale_and_only_features(self):
  model={'intercept':1.,'coefficients':[0.]*8,'means':[99.]*8,'stds':[1.]*8}
  self.assertAlmostEqual(q.quality_score(self.row,self.r,model),1/(1+math.exp(-1)))
 def test_test_partition_unconsumed(self):
  lock=json.loads((ROOT/'docs/research/S01/S01-E004/data_lock.json').read_text());q.base.validate_data_lock(lock)
  self.assertEqual(lock['confirmatory_test_locations'],['1174','1729','2246','2260','2485'])
 def test_invalid_probability_rejected(self):
  with self.assertRaises(ValueError):q.features(dict(self.row,probability=float('nan')),self.r)
 def test_feature_schema_fixed(self):
  cfg=json.loads((ROOT/'docs/research/S01/S01-E004/run_config.json').read_text());self.assertEqual(cfg['features'],q.FEATURES)
if __name__=='__main__':unittest.main()

class DownloadTests(unittest.TestCase):
 def test_incomplete_or_wrong_download_rejected(self):
  lock={'archive_bytes':100,'confirmatory_test_locations':['7']};payload={'url':'u','remote_size':100,'requested_locations':['7'],'selected_files':1,'extracted_files':1,'failed_files':0,'failures':[],'files':[{'location':'7','target':'a','status':'downloaded_crc_verified'}]}
  q.validate_download_payload(payload,lock,'u')
  with self.assertRaises(ValueError):q.validate_download_payload(dict(payload,failed_files=1),lock,'u')
  with self.assertRaises(ValueError):q.validate_download_payload(dict(payload,requested_locations=['8']),lock,'u')
  with self.assertRaises(ValueError):q.validate_download_payload(dict(payload,selected_files=0),lock,'u')
