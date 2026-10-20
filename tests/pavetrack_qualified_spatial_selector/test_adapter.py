"""Hand-built arrays only; no input reads, models, fits or real policy replay."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np
p=Path(__file__).resolve().parents[2]/'scripts/pavetrack_qualified_spatial_selector/adapter.py'
s=importlib.util.spec_from_file_location('adapter',p);a=importlib.util.module_from_spec(s);s.loader.exec_module(a)

class AdapterChecks(unittest.TestCase):
    def setUp(self):
        self.ctx=[0,0,32,32];self.old=[0,0,16,32];self.new=[16,0,32,32]
    def desc(self,p,arm='aligned',old=None,new=None,ctx=None):
        return a.describe(p,self.old if old is None else old,self.new if new is None else new,self.ctx if ctx is None else ctx,arm)
    def test_aligned_direction(self):
        p=np.zeros((32,32),np.float32);p[:,16:]=1
        self.assertEqual(self.desc(p)['values'],[.5,.5])
        self.assertEqual(self.desc(p,'half_shift')['values'],[-.5,-.5])
    def test_shift_preserves_mass(self):
        p=np.zeros((32,32),np.float32);p[1:8,23:30]=.8
        self.assertEqual(self.desc(p)['occupied_bins'],49)
        self.assertEqual(self.desc(p,'half_shift')['occupied_bins'],49)
    def test_empty_and_full_are_zero_information(self):
        for val in (0.,1.):
            self.assertEqual(self.desc(np.full((32,32),val,np.float32))['values'],[0.,0.])
    def test_fixed_threshold_inclusive(self):
        p=np.full((32,32),np.nextafter(np.float32(.5),np.float32(0)),np.float32)
        self.assertEqual(self.desc(p)['occupied_bins'],0)
        p[0,0]=.5
        self.assertEqual(self.desc(p)['occupied_bins'],1)
    def test_identical_boxes_no_paired_gain(self):
        p=np.zeros((32,32),np.float32);p[:2,:3]=1
        self.assertEqual(self.desc(p,new=self.old)['values'][1],0.)
    def test_fractional_overlap(self):
        cov=a.coverage([.25,.25,1.25,1.25],self.ctx)
        self.assertAlmostEqual(float(cov.sum()),1.)
        self.assertEqual(cov[0,0],.5625)
    def test_subpixel_context(self):
        cov=a.coverage([0,0,.01,.02],[0,0,.01,.02])
        np.testing.assert_array_equal(cov,np.ones((32,32)))
    def test_outside_clipped_not_negative(self):
        cov=a.coverage([-10,-10,16,32],self.ctx)
        self.assertEqual(float(cov.sum()),512.)
    def test_no_mutation(self):
        p=np.arange(1024,dtype=np.float32).reshape(32,32)/1024;before=p.copy();p.flags.writeable=False
        self.desc(p);self.desc(p,'half_shift');np.testing.assert_array_equal(p,before)
    def test_invalid_map(self):
        for p in [np.zeros((16,32),np.float32),np.zeros((32,32),np.float64),np.full((32,32),np.nan,np.float32),np.full((32,32),1.1,np.float32)]:
            with self.assertRaises(ValueError):self.desc(p)
    def test_invalid_geometry_and_arm(self):
        p=np.zeros((32,32),np.float32)
        for kw in [dict(ctx=[0,0,0,1]),dict(old=[0,0,float('inf'),3]),dict(arm='best')]:
            with self.assertRaises(ValueError):self.desc(p,**kw)
    def test_numeric_append(self):
        p=np.zeros((32,32),np.float32);p[:,16:]=1
        self.assertEqual(a.append_columns([.8,.2,1,.5],self.desc(p)),[.8,.2,1,.5,.5,.5])
        with self.assertRaises(ValueError):a.append_columns([.8,.2,1,.5],dict(values=[float('nan'),0]))
    def test_frozen_partition(self):
        loc=['24','95','151','514','728','1400','1577','1638','2027','3662','4494','5508']
        groups=[['24','514','1577','3662'],['95','728','1638','4494'],['151','1400','2027','5508']]
        x=a.partition(loc,groups)
        self.assertEqual(x['qualification_reused'],['24','1638','2027']);self.assertEqual(len(x['primary']),9)
        for f in x['folds']:
            self.assertFalse(set(f['fit'])&set(f['held']));self.assertEqual(len(f['primary_held']),3)
        with self.assertRaises(ValueError):a.partition(loc[1:],groups)
    def test_projected_reuse_geometry(self):
        field=np.zeros((32,32),np.float32);field[7,19]=1
        _,p=a.geometry.reduce(field,self.ctx)
        np.testing.assert_array_equal(p,field)
        self.assertEqual(self.desc(p)['occupied_bins'],1)

if __name__=='__main__':unittest.main()
