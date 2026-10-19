"""Small correctness tests on artificial arrays, not a model experiment."""
import unittest
import numpy as np
import runner

class NumericalContract(unittest.TestCase):
    def test_cached_feature_interventions_equal_direct(self):
        a=np.arange(2*128*128,dtype=np.float32).reshape(2,128,128)/1e5
        row=dict(span_px='15',span_px_threshold08='19',span_px_threshold125='12',
                 center_row_from_first_frame='64')
        point=runner.state_features(a,row,'rich',0,0.)
        for arm in ['rich','rich_fixed','rich_set']:
            for variant in [-1,0,1]:
                direct=runner.state_features(a,row,arm,variant,3.)
                cached=runner.scenario_from_point(point,row,arm,variant,3.)
                np.testing.assert_array_equal(direct,cached)
        np.testing.assert_array_equal(point,runner.state_features(a,row,'rich',0,0.))

    def test_spatial_pool_and_reconstruction(self):
        a=np.ones((2,128,128));a[1]*=2
        small=runner.pool(a,16)
        np.testing.assert_array_equal(np.repeat(np.repeat(small,8,1),8,2),a)

    def test_local_weight_is_not_diluted_by_background(self):
        target=np.zeros((2,128,128));pred=target.copy();pred[:,48:81]=1
        total,_,_,full,local=runner.score(pred,target,64,np.ones(2),16)
        self.assertEqual(local,1.);self.assertAlmostEqual(full,33/128)
        self.assertAlmostEqual(total,.5*(33/128+1))

    def test_zero_width_set_is_same_point_state(self):
        a=np.zeros((2,128,128));row=dict(span_px='10',span_px_threshold08='10',span_px_threshold125='10',center_row_from_first_frame='64')
        point=runner.state_features(a,row,'rich',0,0.)
        for arm in ['rich_set','rich_fixed']:
            for variant in [-1,0,1]:
                np.testing.assert_array_equal(point,runner.scenario_from_point(point,row,arm,variant,0.))

if __name__=='__main__':unittest.main()
