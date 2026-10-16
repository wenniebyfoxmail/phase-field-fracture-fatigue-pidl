from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from d01_residual_width_propagation import perturbation,sample_shifted,scenario,summarize,STAGES,MODES
from d01_t1_local_audit import decompose


class PropagationTests(unittest.TestCase):
    def test_modes_keep_pair_and_other_old_component(self):
        old=np.array([.6,-.2]);r=np.array([.3,.4])
        for mode,expected in [('normal_only',[.9,-.2]),('tangent_only',[.6,.2]),('joint',[.9,.2])]:
            np.testing.assert_allclose(old+perturbation(r,mode),expected)
        np.testing.assert_allclose(old+perturbation(r,'joint'),old+r)
        for bad in ([np.nan,0],[1],[1,2,3]):
            with self.assertRaises(ValueError):perturbation(bad,'joint')

    def test_real_sampler_axes_and_sign(self):
        yy,xx=np.mgrid[:180,:240];im=(xx+2*yy).astype(np.float32)
        g=dict(native_shape=list(im.shape),working_shape=list(im.shape));tr=dict(center=[120.,90.],normal=[1.,0.])
        p0,_=sample_shifted(im,np.eye(3),g,tr,[0,0])
        pn,_=sample_shifted(im,np.eye(3),g,tr,[.5,0])
        pt,_=sample_shifted(im,np.eye(3),g,tr,[0,.5])
        np.testing.assert_allclose(pn-p0,.5);np.testing.assert_allclose(pt-p0,1.)

    def test_zero_residual_reproduces_baseline_profile(self):
        yy,xx=np.mgrid[:180,:240];im=(180-90*np.exp(-(xx-120)**2/20)).astype(np.float32)
        g=dict(native_shape=list(im.shape),working_shape=list(im.shape));tr=dict(center=[120.,90.],normal=[1.,0.])
        p0,m0=sample_shifted(im,np.eye(3),g,tr,[.25,.5])
        for mode in MODES:
            p,m=sample_shifted(im,np.eye(3),g,tr,np.array([.25,.5])+perturbation([0,0],mode))
            np.testing.assert_array_equal(p,p0);self.assertEqual(m['width_px'],m0['width_px'])

    def records(self,widths,clear=True,valid=True):
        return {(j,'N01','joint'):dict(valid=valid,reason='ok' if valid else 'low_contrast',width_px=w,flags_clear=clear) for j,w in zip(STAGES,widths)}

    def test_stage_contributions_and_postclip(self):
        base=decompose([10,12,15]);r=scenario(self.records([11,14,16]),'joint',('N01',)*3,'coherent',base)
        self.assertAlmostEqual(r['delta_error'],2);self.assertAlmostEqual(r['contribution30'],-1)
        self.assertAlmostEqual(r['contribution40'],4);self.assertAlmostEqual(r['contribution50'],-1)
        self.assertAlmostEqual(r['decomposition_residual'],0)
        base=decompose([20,10,5]);r=scenario(self.records([30,10,5]),'joint',('N01',)*3,'coherent',base)
        self.assertAlmostEqual(r['delta_error'],0);self.assertAlmostEqual(r['clip_change'],10)
        self.assertAlmostEqual(r['decomposition_residual'],0)

    def test_invalid_remains_missing_and_empty_subset_not_zero(self):
        base=decompose([10,12,15]);r=scenario(self.records([11,14,16],False,False),'joint',('N01',)*3,'coherent',base)
        self.assertFalse(r['valid']);self.assertIsNone(r['secant_error'])
        result=summarize([r]);self.assertEqual(len(result),12)
        clear=next(x for x in result if x['mode']=='joint' and x['temporal']=='coherent' and x['support']=='flags_clear')
        self.assertEqual(clear['opportunities'],0);self.assertIsNone(clear['min_abs_error']);self.assertIsNone(clear['extrema_bracket_zero'])

    def test_coherent_flags_are_three_stage_intersection(self):
        d=self.records([11,14,16]);d[2,'N01','joint']['flags_clear']=False
        r=scenario(d,'joint',('N01',)*3,'coherent',decompose([10,12,15]))
        self.assertTrue(r['valid']);self.assertFalse(r['flags_clear'])

    def test_out_of_source_never_pads(self):
        g=dict(native_shape=[100,100],working_shape=[100,100]);tr=dict(center=[0,50],normal=[1.,0.])
        with self.assertRaisesRegex(ValueError,'sample_out_of_bounds'):sample_shifted(np.zeros((100,100)),np.eye(3),g,tr,[0,0])


if __name__=='__main__':unittest.main()
