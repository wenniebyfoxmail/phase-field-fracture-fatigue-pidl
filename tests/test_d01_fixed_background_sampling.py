import copy
import json
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from d01_fixed_background_sampling import validate_lock,query_summary,error_change,reproduce,ARMS,EXPECTED
from d01_residual_width_propagation import sample_shifted
from d01_t1_local_audit import decompose,read_csv

ROOT=Path(__file__).resolve().parents[1]


class FixedSamplingTests(unittest.TestCase):
    def test_fixed_lock_and_source(self):
        lock=json.loads((ROOT/'docs/research/S03/S03-E030-D01/fixed_positions.json').read_text())
        rows=read_csv(ROOT/'docs/research/S03/S03-E029-D01/evidence/full_centres.csv')
        values=validate_lock(lock,rows)
        np.testing.assert_array_equal(list(values.values()),EXPECTED)
        for key,val in [('shift_t',.5),('stage_index',2),('load_kN',31)]:
            bad=copy.deepcopy(lock);bad['positions'][0][key]=val
            with self.assertRaises(ValueError):validate_lock(bad,rows)
        with self.assertRaises(ValueError):validate_lock(lock,rows[:-2])

    def test_do_not_accept_secondary_support(self):
        lock=json.loads((ROOT/'docs/research/S03/S03-E030-D01/fixed_positions.json').read_text())
        rows=read_csv(ROOT/'docs/research/S03/S03-E029-D01/evidence/full_centres.csv')
        rows[0]['support']='8'
        with self.assertRaises(ValueError):validate_lock(lock,rows)

    def test_null_retained_not_zero(self):
        rows=[dict(arm=a,stage_index=j,valid=j!=2,reason='insufficient_depth' if j==2 else 'ok',width_px=None if j==2 else 10)
              for a in ARMS for j in (1,2,3)]
        for r in query_summary(rows):
            self.assertEqual(r['valid_profiles'],2);self.assertFalse(r['available']);self.assertIsNone(r['secant_error'])
        self.assertIsNone(error_change(query_summary(rows)[0],query_summary(rows)[1])['delta_error'])

    def test_coverage_identity_guard(self):
        with self.assertRaises(ValueError):query_summary([])

    def test_signed_decomposition(self):
        base=dict(available=True,**decompose([10,12,15]));new=dict(available=True,**decompose([11,14,16]))
        r=error_change(new,base)
        self.assertEqual(r['delta_error'],2);self.assertEqual(r['prediction_change'],3)
        self.assertEqual(r['reference_change'],1);self.assertEqual(r['identity_residual'],0)
        self.assertEqual([r[f'contribution{x}'] for x in (30,40,50)],[-1,4,-1])

    def test_clip_separated(self):
        base=dict(available=True,**decompose([20,10,5]));new=dict(available=True,**decompose([30,10,5]))
        r=error_change(new,base)
        self.assertEqual(r['delta_error'],0);self.assertEqual(r['delta_clip'],10)
        self.assertEqual(r['identity_residual'],0)

    def test_reproduction_rejects_nonfinite_and_difference(self):
        ref=decompose([16,16,17]);measured=dict(available=True,**ref);reproduce(measured,ref)
        for v in (float('nan'),float('inf'),16.1):
            with self.assertRaises(ValueError):reproduce(measured,dict(ref,w30=v))

    def test_zero_shift_and_axis_direction(self):
        yy,xx=np.mgrid[:180,:240];im=(xx+2*yy).astype(np.float32)
        g=dict(native_shape=list(im.shape),working_shape=list(im.shape));tr=dict(center=[120.,90.],normal=[1.,0.])
        p,_=sample_shifted(im,np.eye(3),g,tr,[0,0])
        q,_=sample_shifted(im,np.eye(3),g,tr,[.5,0]);np.testing.assert_allclose(q-p,.5)
        q,_=sample_shifted(im,np.eye(3),g,tr,[0,.5]);np.testing.assert_allclose(q-p,1.)


if __name__=='__main__':unittest.main()
