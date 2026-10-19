"""Hand-authored algebra fixtures ONLY. No saved scientific arrays or real model execution."""
import unittest
from unittest.mock import patch
from pathlib import Path
import numpy as np
import r002_base as base
import state,contract,worker,supervise
from analysis import diagnostic

class StateContract(unittest.TestCase):
 def setUp(self):
  self.c=np.asarray([[(i*j+2*j+i*i)%17/9.+j*.1 for j in range(20)] for i in range(8)])
  self.h=np.asarray([[(i+3*j+i*i)%11/13. for j in range(12)] for i in range(8)])
  self.cases=[{'group':g,'origin_stage':100+i} for i,g in enumerate(['A','A','B','B','C','C','D','D'])]
 def test_query_contamination_cannot_fit_input_estimator(self):
  f=state.Fits();a,e,p=state.innovations(f,self.c,self.h,[0,1,2,3],[4,5],self.cases)
  c=self.c.copy();h=self.h.copy();c[4:]+=999;h[4:]-=777
  b,ee,pp=state.innovations(f,c,h,[0,1,2,3],[4,5],self.cases)
  for key in ['m_mean','m_scale','m_coef','train_donor_indices']:np.testing.assert_array_equal(e[key],ee[key])
  for arm in ('H_INNOV','H_DONOR'):np.testing.assert_array_equal(a[arm][0],b[arm][0])
 def test_donor_cannot_access_query_history(self):
  a,e,p=state.innovations(state.Fits(),self.c,self.h,[0,1,2,3],[4,5],self.cases);h=self.h.copy();h[4:]+=555
  b,_,_=state.innovations(state.Fits(),self.c,h,[0,1,2,3],[4,5],self.cases)
  np.testing.assert_array_equal(a['H_DONOR'][1],b['H_DONOR'][1]);self.assertFalse(np.array_equal(a['H_INNOV'][1],b['H_INNOV'][1]))
 def test_donor_ids_are_train_only_other_group_and_lexical_ties(self):
  x=np.zeros((4,20));ids=[('B',8,3),('A',9,2),('A',4,1),('C',1,0)]
  d,dist=state.nearest(x,x,ids,ids,np.zeros(20),np.ones(20))
  self.assertEqual(list(d),[2,0,0,2])
  for i,j in enumerate(d):self.assertNotEqual(ids[i][0],ids[j][0])
  with self.assertRaises(ValueError):state.nearest(x[:2],x[:1],[('A',1,0),('A',2,1)],[('B',1,2)],np.zeros(20),np.ones(20))
 def test_candidate_current_block_normalisation_is_exact_raw(self):
  f=state.Fits();blocks,e,prefix=state.innovations(f,self.c,self.h,[0,1,2,3],[4,5],self.cases);y=np.asarray([[i,i*i/11] for i in range(4)])
  raw=f.fit(self.c[:4],y,10.,['A','A','B','B'])
  for arm in ('H_INNOV','H_DONOR'):
   model=f.fit(blocks[arm][0],y,10.,['A','A','B','B'],locked_prefix=prefix)
   np.testing.assert_array_equal(model[0][:20],raw[0]);np.testing.assert_array_equal(model[1][:20],raw[1]);np.testing.assert_array_equal(blocks[arm][1][:,:20],self.c[4:6])
 def test_pullback_preserves_function_objective_and_normal_equations(self):
  x=np.asarray([[(i*j+i+3*j)%19/8.+j*(j%3+1) for j in range(36)] for i in range(8)])
  y=np.asarray([[i/7.,(i*i+1)/13.] for i in range(8)]);g=['A','A','B','B','C','C','D','D'];alpha=.1
  model=state.Fits().fit(x,y,alpha,g);p,e=state.pullback(model,x,x+.02)
  np.testing.assert_allclose(p,state.predict(model,x+.02),atol=1e-11,rtol=0)
  raw_pen=float(np.sum(model[2][1:]**2));new_pen=float(np.sum(e['coef'][1:]*(e['penalty']@e['coef'][1:])))
  self.assertAlmostEqual(raw_pen,new_pen,places=11)
  z=np.c_[np.ones(8),(x@e['T'].T-e['feature_mean'])/e['feature_scale']];W=state.weights(g);P=np.zeros((37,37));P[1:,1:]=e['penalty']
  residual=(z.T@(W[:,None]*z)+alpha*P)@e['coef']-z.T@(W[:,None]*y)
  self.assertLess(np.max(np.abs(residual)),1e-11)
 def test_replay_inputs_match_R002_without_current_coordinate_change(self):
  ss=np.arange(8*3*138,dtype=float).reshape(8,3,138)/100.;cases=[dict(group='C_0Deg_15%_#1',origin_stage=100+i) for i in range(8)]
  x,h=state.features(ss,cases,10)
  for new,old in [('C_RAW','current_response'),('H_RAW','history_response'),('H_REL','centered_history')]:
   expected=np.asarray([base.compose_features(old,c['group'],c['origin_stage'],10,s) for c,s in zip(cases,ss)]);np.testing.assert_array_equal(x[new],expected)
  np.testing.assert_array_equal(x['C_REL'][:,12:],state.relative(ss[:,-1,2:10]));self.assertEqual(h.shape,(8,12))
 def test_baseline_tie_order_and_inner_only_interface(self):
  self.assertEqual(state.choose_baseline({'P':1.,'S':1.,'C_RAW':1.,'C_REL':1.}),'P')
  self.assertEqual(state.choose_baseline({'P':2.,'S':2.,'C_RAW':1.,'C_REL':1.}),'C_REL')
  with self.assertRaises(ValueError):state.choose_baseline({'P':0.,'S':1.})
 def test_nonfinite_and_solve_cap_stop_before_extra_solve(self):
  f=state.Fits();f.predictor=912
  with self.assertRaises(RuntimeError):f.fit(self.c[:4],self.h[:4],10.,['A','A','B','B'])
  with self.assertRaises(ValueError):state.relative([np.nan]*8)
 def test_budget_caps_and_archive_file_size(self):
  import tempfile
  self.assertIsNone(contract.budget_reason(1,1,1,1))
  for args,expected in [((1801,1,1,1),'wall_budget'),((1,9*2**30,1,1),'rss_budget'),((1,1,5*2**30,1),'output_budget'),((1,1,1,5*2**30),'archive_budget')]:self.assertEqual(contract.budget_reason(*args),expected)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'fixture.txt';p.write_text('abc');self.assertEqual(supervise.size(p),3);self.assertEqual(supervise.size(Path(d)),3)
 def test_non_BLAS_oracle_matches_finite_ridge_values(self):
  y=np.asarray([[i*.1,(i*i+3)/17.] for i in range(8)]);g=[c['group'] for c in self.cases];model=state.Fits().fit(self.c,y,.1,g)
  z=np.c_[np.ones(8),(self.c-model[0])/model[1]];w=state.weights(g);P=np.eye(21)*.1;P[0,0]=0
  # independent no-BLAS contractions distinguish stale fp flags from nonfinite arithmetic
  lhs=np.einsum('ni,n,nj->ij',z,w,z,optimize=False)+P;rhs=np.einsum('ni,n,nk->ik',z,w,y,optimize=False)
  oracle=np.linalg.solve(lhs,rhs)
  self.assertTrue(np.isfinite(oracle).all());np.testing.assert_allclose(model[2],oracle,rtol=0,atol=1e-11)
 def test_external_config_is_rejected_before_resource_or_array_io(self):
  with self.assertRaises(ValueError):contract.load_config(Path(__file__).parent,'/not/a/sealed/config.json')
 def test_default_paths_cannot_load_arrays_or_start_process(self):
  with patch('numpy.load',side_effect=AssertionError('array access')),patch('subprocess.Popen',side_effect=AssertionError('producer launch')):
   with self.assertRaises(PermissionError):worker.main(['--run'])
   with self.assertRaises(PermissionError):supervise.main([])
 def test_signed_and_exact_zero_reference_are_not_clipped_or_dropped(self):
  out=diagnostic(-np.ones((2,128,128)),-2*np.ones((2,128,128)),np.ones(2),64)
  self.assertEqual(out['pred_positive_mass_0'],0.);self.assertEqual(out['pred_negative_mass_0'],1.);self.assertEqual(out['l1_mass_ratio_0'],.5)
  z=diagnostic(np.ones((2,128,128)),np.zeros((2,128,128)),np.ones(2),64)
  self.assertIsNone(z['l1_mass_ratio_0']);self.assertEqual(z['reference_exact_zero_0'],1);self.assertEqual(z['pred_l1_normalized_0'],1.)

if __name__=='__main__':unittest.main()
