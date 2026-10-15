import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import d01_background_anchor_diagnostic as d
from independent_d01_halfdepth import source_to_origin

class TestAnchor(unittest.TestCase):
    def test_known_translation(self):
        rng=np.random.default_rng(20261015)
        search=rng.normal(100,25,(47,47)).astype(np.float32)
        for dn,dt in ((0,0),(3,-2),(-5,4)):
            r=d.match_patch(search[8+dt:39+dt,8+dn:39+dn].copy(),search)
            self.assertTrue(r["available"])
            self.assertLess(abs(r["shift_n"]-dn),.1)
            self.assertLess(abs(r["shift_t"]-dt),.1)
    def test_constant_and_boundary(self):
        r=d.match_patch(np.ones((31,31),np.float32)*100,np.ones((47,47),np.float32)*100)
        self.assertFalse(r["available"])
        rng=np.random.default_rng(4)
        a=rng.normal(100,20,(47,47)).astype(np.float32)
        self.assertEqual(d.match_patch(a[:31,:31].copy(),a)["reason"],"search_boundary")
    def test_fit_excludes_check(self):
        a=[dict(role="fit",available=True,shift_n=1.,shift_t=2.) for _ in range(4)]
        a += [dict(role="check",available=True,shift_n=999.,shift_t=-999.)]
        np.testing.assert_array_equal(d.fit_translation(a),[1.,2.])
        a[0]["available"]=False
        self.assertIsNone(d.fit_translation(a))
    def test_nonoverlap(self):
        fits=[(n,t) for role,n,t in d.ANCHORS if role=="fit"]
        checks=[(n,t) for role,n,t in d.ANCHORS if role=="check"]
        self.assertEqual(len(fits),4)
        for a in fits:
            for b in checks:
                self.assertTrue(abs(a[0]-b[0])>30 or abs(a[1]-b[1])>30)
        for role,n,t in d.ANCHORS: self.assertGreater(abs(n)-15,60)
    def test_shared_translation_sampling(self):
        tr=dict(center=[300.,300.],normal=[1.,0.])
        delta=np.array([2.,-3.])
        grids=[d.sampling_grid(tr["center"],tr["normal"],np.arange(-60,60.25,.25),v) for v in d.VARIANTS]
        np.testing.assert_allclose((grids[1]+delta)-(grids[0]+delta),grids[1]-grids[0])
    def test_shape(self):
        with self.assertRaises(ValueError): d.match_patch(np.ones((3,3)),np.ones((47,47)))
    def test_end_to_end_rotated_nonidentity_mapping(self):
        shape=[300,300]
        geom=dict(native_shape=shape,working_shape=[150,150])
        tr=dict(center=[150.,150.],normal=[.6,.8])
        h=np.array([[1.,.012,1.5],[-.007,1.,-1.2],[.00005,-.00003,1.]])
        yy,xx=np.indices(shape,dtype=float)
        points=np.stack([xx,yy],axis=-1)
        normal=np.array([.6,.8]); tangent=np.array([-.8,.6])
        def texture(q):
            u=(q-150)@normal; v=(q-150)@tangent
            return (130+30*np.sin(.43*u+.13*v)+25*np.cos(.17*u-.37*v)+15*np.sin(.27*u+.51*v)).astype(np.float32)
        source_origin=source_to_origin(points,h,shape,geom["working_shape"])
        delta=2*normal-3*tangent
        template=d.source_sample(texture(points),d.local_grid(tr,0,0,15),np.eye(3),geom)
        search=d.source_sample(texture(source_origin-delta),d.local_grid(tr,0,0,23),h,geom)
        result=d.match_patch(template,search)
        self.assertTrue(result["available"])
        self.assertLess(abs(result["shift_n"]-2),.15)
        self.assertLess(abs(result["shift_t"]+3),.15)

if __name__=="__main__": unittest.main()
