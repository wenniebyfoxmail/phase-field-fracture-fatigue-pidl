"""Artificial fixtures only. No scientific CSV/NPZ, subprocess or fit."""
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import analyse as a
import diagnostic_contract as c
import run_bounded as runner

class ContractTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.out=Path(self.tmp.name).resolve();a.AUDIT=c.Audit(self.out,source_version='SYNTHETIC_ONLY')
 def tearDown(self):self.tmp.cleanup();a.AUDIT=None
 def row(self):
  r={n:'0' for n in a.FIELDS};r.update(case_index='toy',group='ARTIFICIAL',origin_stage='0',horizon_stages='10',arm='C_RAW')
  for ch in (0,1):r[f'reference_exact_zero_{ch}']='1'
  return r
 def test_cross_representation_counterexample_is_not_rejected(self):
  current=np.float32(.1);target=np.float32(-.2);prediction=float(target)+1e-8
  native=abs(prediction-float(target));increment=abs((prediction-float(current))-float(target-current))
  self.assertGreater(increment,native+1e-11)
  r=self.row();r.update(full_nmae=str(native),mean_increment_error_0=str(increment),mean_increment_error_1=str(increment))
  a.enter_csv(r);x=a.validate_metrics(r);self.assertEqual(x['full_nmae'],native);self.assertFalse((self.out/'failure.json').exists())
 def test_common_residual_bounds_only_on_artificial_arrays(self):
  for residual in (np.array([1.,-2.,4.]),np.array([1.,1.]),np.array([-1.,1.])):
   e=np.mean(abs(residual));g=abs(np.mean(residual));s=np.mean(abs(residual-np.mean(residual)))
   self.assertLessEqual(g,e+1e-15);self.assertLessEqual(e,g+s+1e-15)
 def test_failure_persisted_before_raise_and_not_overwritten(self):
  r=self.row();r['full_nmae']='-1';a.enter_csv(r)
  with self.assertRaises(c.DiagnosticStop):a.validate_metrics(r)
  original=(self.out/'failure.json').read_bytes();record=json.loads(original)
  self.assertEqual(record['context']['identity']['group'],'ARTIFICIAL');self.assertEqual(record['context']['E_native'],'-1')
  self.assertIsNone(record['context']['margin']);self.assertIn('no cross-representation',record['context']['margin_reason'])
  self.assertEqual(record['code_source_version'],'SYNTHETIC_ONLY');self.assertIn('G_S_increment',record['semantics'])
  with self.assertRaises(c.DiagnosticStop):a.AUDIT.fail('second failure')
  self.assertEqual(original,(self.out/'failure.json').read_bytes())
 def test_parse_exception_keeps_identity_and_missing_reason(self):
  r=self.row();del r['mean_increment_error_0'];a.enter_csv(r)
  try:a.validate_metrics(r)
  except Exception as exc:
   with self.assertRaises(c.DiagnosticStop):a.AUDIT.fail(type(exc).__name__+': '+str(exc))
  record=json.loads((self.out/'failure.json').read_text());self.assertIn('G_increment',record['context']['missing_reason']);self.assertIn('KeyError',record['error'])
 def test_nonfinite_encoding_and_bounded_snapshot(self):
  a.AUDIT.enter('toy',E_native=float('nan'),identity={'group':'x'*10000})
  with self.assertRaises(c.DiagnosticStop):a.finite([np.nan],'artificial')
  raw=(self.out/'failure.json').read_bytes();self.assertLessEqual(len(raw),8192);self.assertIn(b'nonfinite:nan',raw)
 def test_whitelist_stops_before_stat(self):
  with patch.object(Path,'stat',side_effect=AssertionError('no data stat permitted')):
   with self.assertRaises(c.DiagnosticStop):a.source('origin_feature_evidence.npz')
 def test_missing_authority_precedes_mkdir_and_popen(self):
  out=self.out/'never_created'
  with patch.object(c,'package_id',return_value='syntheticdigest'),patch.object(runner.subprocess,'Popen',side_effect=AssertionError('no subprocess permitted')):
   with self.assertRaises(PermissionError):runner.main(['--output',str(out)])
  self.assertFalse(out.exists())
 def test_size_scan_tolerates_only_disappearance(self):
  class Disappeared:
   def stat(self):raise FileNotFoundError('artificial atomic rename')
  live=self.out/'live';live.write_bytes(b'12345')
  with patch.object(Path,'rglob',return_value=iter([Disappeared(),live])):
   self.assertEqual(runner.output_size(self.out),5)
  class Inaccessible:
   def stat(self):raise PermissionError('artificial non-race failure')
  with patch.object(Path,'rglob',return_value=iter([Inaccessible()])):
   with self.assertRaises(PermissionError):runner.output_size(self.out)
 def test_authority_exact_budget_binding(self):
  payload={'authority_kind':'hq_arithmetic_continuation','allow_saved_derivative_read':True,'hq_thread_id':'01a14bb9-6cd1-7ee2-9647-5190d786f7ba','approval_text':'ARTIFICIAL TEST ONLY','source_commit':'a'*40,'package_sha256':'toy','source_root':c.SOURCE,'output_root':str(self.out),'budget':c.BUDGET}
  p=self.out/'synthetic_authority.json';p.write_text(json.dumps(payload));self.assertEqual(c.authority(p,'toy',self.out)['package_sha256'],'toy')
  payload['budget']={**c.BUDGET,'wall_seconds':601};p.write_text(json.dumps(payload))
  with self.assertRaises(PermissionError):c.authority(p,'toy',self.out)

if __name__=='__main__':unittest.main()
