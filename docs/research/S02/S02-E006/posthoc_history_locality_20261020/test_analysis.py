import unittest
import numpy as np
import pandas as pd
from analyse import masks, balanced, thirds, weighted_summary


class Arithmetic(unittest.TestCase):
    def test_equal_group_not_equal_window(self):
        rows = []
        for group, n, value in [('a', 1, 2.), ('b', 9, 10.)]:
            for h in [10, 40]:
                for _ in range(n):
                    rows.append(dict(group=group, horizon=h, stage_third=0, B_STAR=value,
                                     C_RAW=value, H_INNOV=1., gain_B_STAR=value-1., gain_C_RAW=value-1.))
        result = weighted_summary(pd.DataFrame(rows), 'stage_third').iloc[0]
        self.assertEqual(result.B_STAR, 6.)
        self.assertEqual(result.gain_B_STAR, 5.)
        self.assertEqual(result.groups_n, 2)
        self.assertEqual(len(weighted_summary(pd.DataFrame(rows), ['stage_third', 'horizon'])), 2)
        self.assertEqual(len(weighted_summary(pd.DataFrame(rows), 'group')), 2)

    def test_partition_at_edges(self):
        err = np.arange(2*128*128).reshape(2, 128, 128)/100.
        for center in [0, 63, 127]:
            m = masks(center)
            self.assertTrue(np.all(m['band'] ^ m['outside_band']))
            self.assertTrue(np.all(m['edge8'] ^ m['interior']))
            self.assertAlmostEqual(balanced(err, center), .5*err.mean()+.5*err[:, m['band']].mean())

    def test_release_thirds(self):
        t = thirds([5, 7, 100, 120, 121, 200, 500])
        self.assertEqual([t[x] for x in [5, 7, 100, 120, 121, 200, 500]], [0, 0, 0, 1, 1, 2, 2])


if __name__ == '__main__':
    unittest.main()
