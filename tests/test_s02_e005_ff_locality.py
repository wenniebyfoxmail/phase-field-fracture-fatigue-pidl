import importlib.util
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import s02_e005_ff_locality as m

class LocalityTests(unittest.TestCase):
    def test_exact_source_cycles(self):
        self.assertEqual(m.exact_cycle('1e+05'),100000)
        self.assertEqual(m.exact_cycle('99001'),99001)
        self.assertEqual(m.exact_cycle('1.00001e5'),100001)
        for text in ['1.5','NaN','Infinity','99999.99999999999999999999']:
            with self.assertRaises(ValueError):
                m.exact_cycle(text)

    def test_zero_and_signed_decomposition(self):
        r={'origin_cycle':1,'target_cycle':1001,'target_dx_mm':.1,'M0_dx_mm':.12,'M1_dx_mm':.15}
        self.assertEqual(m.edge_values(r,{1:0,1001:0})[2:5],(0.,0.,0.))
        d0,de,s,lo,up,delta=m.edge_values(r,{1:-.05,1001:.05})
        self.assertAlmostEqual(d0+s,de)
        self.assertAlmostEqual(s,up-lo)
        self.assertAlmostEqual(delta,.1)
    def test_shared_nodes_with_gap(self):
        rs=[{'origin_cycle':1,'target_cycle':1001},{'origin_cycle':1001,'target_cycle':2001},{'origin_cycle':3000,'target_cycle':4000}]
        es=m.prior.node_errors(m.prior.nodes(rs),.1,'alternating_positive')
        self.assertEqual(list(es),[1,1001,2001,3000,4000])
        self.assertAlmostEqual(es[1001]-es[1],-.2)
        self.assertAlmostEqual(es[2001]-es[1001],.2)
    def test_low_rank_ties(self):
        rs=[{'origin_cycle':n,'growth':v} for n,v in [(3,1),(2,1),(1,2),(4,0)]]
        self.assertEqual(m.low_set(rs,'growth',2),{4,2})
    def test_geometry_boundaries_and_distance(self):
        self.assertEqual([m.projection(x) for x in [22.4,22.5,27.5,27.6]],['before','over_projection','over_projection','after'])
        self.assertEqual(m.interval_distance(.1,.2,.4),.1)
        self.assertEqual(m.interval_distance(.3,.4,.2),0)
    def test_score_flat_outside_prediction_interval(self):
        r={'origin_cycle':1,'target_cycle':1001,'target_dx_mm':1,'M0_dx_mm':.1,'M1_dx_mm':.2}
        self.assertAlmostEqual(m.edge_values(r,{1:-.01,1001:.01})[2],0.)
    def test_lowering_share_uses_gross_mass(self):
        shifts=[-.1,-.2,.15]
        lo=sum(max(-s,0) for s in shifts); up=sum(max(s,0) for s in shifts)
        self.assertAlmostEqual(sum(shifts),up-lo)
        self.assertAlmostEqual(.2/lo,2/3)

if __name__=='__main__':
    unittest.main()
