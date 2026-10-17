import unittest
import numpy as np
from mendeley_crack_probe import measure, initial_center


class MeasurementControls(unittest.TestCase):
    def field(self, left, right):
        a = np.zeros((2,128,128))
        a[1,64:,left:right] = .05
        return a

    def test_uniform_displacement_has_no_crack_support(self):
        a = np.ones((2,128,128))
        self.assertIsNone(measure(a,63,False)['span_px'])

    def test_edge_and_central_known_discontinuities(self):
        for edge,left,right,expected in [(True,0,35,35),(False,40,86,47)]:
            a = self.field(left,right)
            center = initial_center(a,edge)
            self.assertEqual(center,63)
            self.assertAlmostEqual(measure(a,center,edge)['span_px'],expected,places=3)

    def test_missing_field_is_not_a_zero_length(self):
        a = self.field(0,35);a[1,2,2] = np.nan
        result = measure(a,63,True)
        self.assertEqual(result['status'],'nonfinite_field')
        self.assertIsNone(result['span_px'])

    def test_concentration_rejects_smooth_strain_and_keeps_jump(self):
        smooth = np.zeros((2,128,128))
        smooth[1] = np.arange(128)[:,None]*.0001
        self.assertIsNone(measure(smooth,63,False,mode='concentration')['span_px'])
        cracked = smooth+self.field(40,86)
        result = measure(cracked,63,False,mode='concentration')
        shifted = cracked+2.0
        self.assertEqual(result['status'],'candidate')
        self.assertTrue(44 < result['span_px'] < 48)
        self.assertAlmostEqual(result['span_px'],
            measure(shifted,63,False,mode='concentration')['span_px'],places=5)


if __name__ == '__main__': unittest.main()
