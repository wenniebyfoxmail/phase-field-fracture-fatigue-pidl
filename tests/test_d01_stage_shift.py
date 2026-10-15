import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import d01_stage_shift as d

class StageShift(unittest.TestCase):
    def evaluate(self,a,b,va=None,vb=None):
        return d.evaluate(a,b,np.ones(9,bool) if va is None else va,np.ones(9,bool) if vb is None else vb)
    def test_shared_affine_gradient(self):
        a=20+3*d.SHIFTS;b=a+1.5
        r,m,e,v=self.evaluate(a,b)
        self.assertEqual(r['common_rms_px'],0)
        self.assertAlmostEqual(r['independent_rms_px'],3*np.sqrt(2*np.mean(d.SHIFTS**2)))
        np.testing.assert_allclose(np.diag(m),1.5)
        self.assertTrue(r['independent_sign_loss']);self.assertFalse(r['common_sign_loss'])
    def test_opposite_gradient_not_automatically_better(self):
        r,*_=self.evaluate(20+d.SHIFTS,21-d.SHIFTS)
        self.assertGreater(r['common_rms_px'],r['independent_rms_px'])
        self.assertLess(r['grid_covariance_px2'],0)
    def test_constant_and_zero_baseline(self):
        r,*_=self.evaluate(np.ones(9)*20,np.ones(9)*20)
        self.assertEqual(r['independent_rms_px'],0);self.assertTrue(np.isnan(r['common_to_independent_ratio']))
        self.assertFalse(r['baseline_nonzero']);self.assertEqual(r['common_nonzero_if_baseline_zero'],0)
    def test_zero_baseline_variable(self):
        r,*_=self.evaluate(20+d.SHIFTS,20+d.SHIFTS)
        self.assertEqual(r['common_nonzero_if_baseline_zero'],0)
        self.assertGreater(r['independent_nonzero_if_baseline_zero'],0)
    def test_missing_no_partial_comparison(self):
        va=np.ones(9,bool);va[0]=False
        r,m,e,v=self.evaluate(20+d.SHIFTS,21+d.SHIFTS,va)
        self.assertFalse(r['paired_valid']);self.assertTrue(r['baseline_valid'])
        self.assertEqual(r['independent_valid'],72);self.assertEqual(r['common_valid'],8)
        self.assertTrue(np.isnan(r['common_rms_px']));self.assertTrue(np.isnan(m[:,0]).all())
        self.assertIsNone(r['common_sign_loss']) # missing is not no-loss
    def test_missing_origin_no_deviation(self):
        va=np.ones(9,bool);va[4]=False
        r,m,e,v=self.evaluate(20+d.SHIFTS,21+d.SHIFTS,va)
        self.assertFalse(r['baseline_valid']);self.assertTrue(np.isnan(e).all());self.assertTrue(np.isfinite(m[:,0]).all())
    def test_sign_zero_and_negative_baseline(self):
        r,m,*_=self.evaluate(20+0*d.SHIFTS,19+d.SHIFTS)
        self.assertEqual(r['baseline_delta_px'],-1)
        self.assertEqual(r['common_opposite'],2);self.assertEqual(r['common_zero'],1)
        self.assertTrue(r['common_sign_loss'])
    def test_matrix_axes_and_covariance_identity(self):
        a=20+d.SHIFTS**2;b=23+.4*d.SHIFTS+d.SHIFTS**3
        r,m,*_=self.evaluate(a,b)
        self.assertEqual(m[0,-1],b[0]-a[-1]);self.assertLess(abs(r['identity_residual_px2']),1e-10)
    def test_nonfinite_valid_rejected(self):
        a=np.ones(9);a[0]=np.nan
        with self.assertRaises(ValueError): self.evaluate(a,np.ones(9))
    def test_primary_paired_difference_and_full_coverage(self):
        groups={}
        for j in range(4):
            for t in range(1,13):
                for arm in d.ARMS:
                    groups[(j,t,arm)]=[dict(width_px=50+j+x,valid=True) for x in np.arange(-10,10.25,.5)]
        pairs,perturb=d.calculate(groups)
        self.assertEqual((len(pairs),len(perturb)),(72,5832));self.assertEqual(sum(r['common'] for r in perturb),648)
        self.assertEqual(d.summary(pairs[:36])['common_lower'],36)
        self.assertTrue(all(r['common_rms_px']==0 for r in pairs))
    def test_paired_median_not_difference_of_medians(self):
        base,*_=self.evaluate(np.ones(9)*20,np.ones(9)*21)
        rows=[dict(base,common_rms_px=c,independent_rms_px=i,paired_rms_change_px=c-i) for c,i in ((0,1),(10,2),(11,12))]
        r=d.summary(rows)
        self.assertEqual(r['median_paired_rms_change_px'],-1)
        self.assertEqual(r['median_common_rms_px']-r['median_independent_rms_px'],8)

if __name__=="__main__": unittest.main()
