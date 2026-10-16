from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from d01_nearfield_correspondence import candidates,match,refined_peak


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


if __name__=='__main__':unittest.main()
