"""Counterexamples for allowed information and feature decomposition; no data fit."""
import unittest
import numpy as np
import runner
class ResponseContract(unittest.TestCase):
 def setUp(self):
  self.states=np.arange(414,dtype=float).reshape(3,138)/100.
 def f(self,arm,states=None,n=100):return runner.compose_features(arm,'C_0Deg_15%_#1',n,10,self.states if states is None else states)
 def test_dimensions(self):
  for a,d in runner.ARM_DIMS.items():self.assertEqual(len(self.f(a)),d)
 def test_span_cannot_access_response(self):
  s=self.states.copy();s[:,2:]+=17
  for a in ('span_only','span_progress'):np.testing.assert_array_equal(self.f(a),self.f(a,s))
 def test_current_cannot_access_past_response(self):
  s=self.states.copy();s[:2,2:]+=17
  np.testing.assert_array_equal(self.f('current_response'),self.f('current_response',s))
  self.assertFalse(np.array_equal(self.f('history_response'),self.f('history_response',s)))
 def test_clock_is_origin_only_and_absent_in_replays(self):
  for a in ('span_only','compact_noclock','rich_noclock'):np.testing.assert_array_equal(self.f(a,n=100),self.f(a,n=900))
  a=self.f('span_progress',n=100);b=self.f('span_progress',n=200)
  np.testing.assert_array_equal(a[:-2],b[:-2]);np.testing.assert_allclose(a[-2:],[.1,.01]);np.testing.assert_allclose(b[-2:],[.2,.04])
 def test_centered_is_uniform_translation_invariant(self):
  s=self.states.copy();s[:,2:4]+=[3.,-2.];s[:,6:8]+=[3.,-2.]
  np.testing.assert_allclose(self.f('centered_history'),self.f('centered_history',s),atol=1e-14)
  self.assertFalse(np.array_equal(self.f('global_history'),self.f('global_history',s)))
 def test_legacy_schema_exactly_replayed(self):
  for arm,k in [('compact_noclock',10),('rich_noclock',138)]:
   expected=np.r_[runner.metadata_features('C_0Deg_15%_#1'),.25,self.states[:,:k].ravel()]
   np.testing.assert_array_equal(self.f(arm),expected)
 def test_global_and_centered_recover_compact_statistics(self):
  # A linear invertible decomposition; ridge regularisation is not invariant to it.
  global_mean=self.states[:,2:4];local_diff=self.states[:,6:8]-global_mean
  np.testing.assert_allclose(global_mean+local_diff,self.states[:,6:8])
if __name__=='__main__':unittest.main()
