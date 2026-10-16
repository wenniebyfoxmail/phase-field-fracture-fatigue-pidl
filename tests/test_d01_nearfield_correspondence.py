from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from d01_nearfield_correspondence import candidates,match,refined_peak,affine_diagnostic,inside_hull,pair_match,combine,side_subset


class NearfieldTests(unittest.TestCase):
    def test_candidate_identity_and_disjoint_old_footprints(self):
        c=candidates();self.assertEqual(len(c),20);self.assertEqual(len({r['anchor_id'] for r in c}),20)
        self.assertTrue(all(abs(r['n'])+17<85 for r in c))

    def test_integer_translation_and_photometric_affine(self):
        rng=np.random.default_rng(12)
        for size in (15,23):
            template=rng.normal(100,20,(size,size)).astype(np.float32)
            search=rng.normal(100,20,(size+12,size+12)).astype(np.float32)
            # n=+2,t=-1 means insertion top-left x8,y5, not reversed axes.
            search[5:5+size,8:8+size]=template*1.2+5
            r=match(template,search);self.assertTrue(r['available'])
            self.assertAlmostEqual(r['dn'],2,delta=.1);self.assertAlmostEqual(r['dt'],-1,delta=.1)

    def test_known_fractional_score_peak(self):
        y,x=np.mgrid[:13,:13];score=-(x-7.25)**2-(y-5.7)**2
        r=refined_peak(score.astype(float))
        self.assertAlmostEqual(r['dn'],1.25);self.assertAlmostEqual(r['dt'],-.3)

    def test_flat_boundary_and_nonfinite(self):
        r=match(np.ones((15,15))*100,np.ones((27,27))*100)
        self.assertFalse(r['available']);self.assertEqual(r['reason'],'weak_template')
        scores=np.zeros((13,13));scores[0,6]=1
        self.assertFalse(refined_peak(scores)['available'])
        with self.assertRaises(ValueError):match(np.full((15,15),np.nan),np.zeros((27,27)))
        with self.assertRaises(ValueError):match(np.zeros((16,16)),np.zeros((28,28)))

    def test_known_subpixel_translation_and_reverse_original_center(self):
        # Smooth analytic texture shifted before sampling, independent of NCC implementation.
        rng=np.random.default_rng(21);centers=rng.uniform(-20,20,(40,2));weights=rng.uniform(-25,25,40)
        yy,xx=np.mgrid[:161,:161]
        def image(dn,dt):
            a=np.zeros_like(xx,dtype=float)+100
            for (cx,cy),w in zip(centers,weights):a+=w*np.exp(-((xx-80-dn-cx)**2+(yy-80-dt-cy)**2)/5)
            return a.astype(np.float32)
        ref=image(0,0);target=image(.7,-.4)
        tr=dict(center=[80.,80.],normal=[1.,0.]);c=dict(n=0,t=0)
        g=dict(native_shape=[161,161],working_shape=[161,161])
        for radius in (7,11):
            template=ref[80-radius:81+radius,80-radius:81+radius]
            f,b,fb,_=pair_match(ref,target,np.eye(3),np.eye(3),g,tr,c,radius,template)
            self.assertTrue(f['available']);self.assertTrue(b['available'])
            self.assertAlmostEqual(f['dn'],.7,delta=.12);self.assertAlmostEqual(f['dt'],-.4,delta=.12)
            self.assertLess(fb,.15)
            # Reverse is about original p: b is near0, not -d_f.
            self.assertLess(np.hypot(b['dn'],b['dt']),.15)

    def test_affine_center_and_loo_support(self):
        p=np.array([[-55,-36],[-55,36],[55,-36],[55,36],[0,-10],[0,10]],float)
        d=np.column_stack((.2+.001*p[:,0],.7-.002*p[:,1]))
        r,loo=affine_diagnostic(p,d)
        self.assertTrue(r['center_interpolation_available']);self.assertAlmostEqual(r['center_dn'],.2)
        self.assertAlmostEqual(r['center_dt'],.7);self.assertLess(r['fit_RMS_px'],1e-12)
        self.assertEqual(len(loo),6);self.assertTrue(any(not x['inside_remaining_hull'] for x in loo))
        self.assertTrue(any(x['inside_remaining_hull'] for x in loo))

    def test_one_side_is_not_center_interpolation(self):
        p=np.array([[35,-36],[35,36],[55,-36],[55,36]],float)
        r,_=affine_diagnostic(p,np.zeros((4,2)))
        self.assertTrue(r['field_available']);self.assertFalse(r['center_interpolation_available'])
        self.assertIsNone(r['center_dn']);self.assertFalse(inside_hull(p,[0,0]))

    def test_degenerate_and_missing_field(self):
        for p in (np.empty((0,2)),np.array([[1,1],[2,2],[3,3],[4,4]])):
            r,_=affine_diagnostic(p,np.zeros_like(p));self.assertFalse(r['field_available'])
        with self.assertRaises(ValueError):affine_diagnostic([[1,np.nan]],[[0,0]])

    def test_combined_flags_keep_primary_data(self):
        r=dict(forward_available=True,peak=.95,separation=.1,reverse_available=True,roundtrip_px=.1,dn=.1,dt=.2,reason='candidate_match')
        c=dict(anchor_id='N01',n=-55,t=-36)
        combined=combine(r,r,c,np.array([.2,.3]))
        self.assertTrue(combined['flags_clear']);self.assertAlmostEqual(combined['residual_dn'],-.1)
        secondary=dict(r,reverse_available=False,roundtrip_px=None)
        x=combine(r,secondary,c,np.zeros(2));self.assertTrue(x['available']);self.assertFalse(x['flags_clear'])
        self.assertIn('secondary_roundtrip',x['flags'])

    def test_side_denominators_and_origin_exclusions(self):
        rows=[dict(r,origin_accepted=r['anchor_id'] not in ('N05','N09','N10')) for r in candidates()]
        for side,nominal,accepted in (('both',20,17),('negative_n',10,7),('positive_n',10,10)):
            pool=side_subset(rows,side)
            self.assertEqual(len(pool),nominal);self.assertEqual(sum(r['origin_accepted'] for r in pool),accepted)


if __name__=='__main__':unittest.main()
