from pathlib import Path
import sys
import unittest
import copy
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from d01_background_center_loo import fit_center,analyze_pool,temporal_pairs,validated_rows,summarize,candidates


class CenterTests(unittest.TestCase):
    def rows(self):
        p=[(-55,-36),(-55,36),(55,-36),(55,36),(0,-10),(0,10)]
        return [dict(anchor_id=f'N{i+1:02d}',n=x,t=y,dn=.2+.001*x,dt=.7-.002*y+(i==4)*.1,flags_clear='True') for i,(x,y) in enumerate(p)]

    def test_known_affine_center_and_exact_model_loo(self):
        rr=self.rows()
        for r in rr:r['dt']=.7-.002*r['t']
        f,ll,ww=analyze_pool(rr);self.assertTrue(f['available']);self.assertAlmostEqual(f['n'],.2);self.assertAlmostEqual(f['t'],.7)
        self.assertTrue(all(r['available'] for r in ll));self.assertLess(max(abs(r['delta_t']) for r in ll),1e-12)
        self.assertAlmostEqual(sum(r['weight'] for r in ww),1)

    def test_influence_identity_matches_direct_refit(self):
        f,ll,_=analyze_pool(self.rows());self.assertTrue(f['available'])
        self.assertGreater(max(abs(r['delta_t']) for r in ll),.01)
        self.assertTrue(all(abs(r['influence_identity_error'])<1e-12 for r in ll if r['available']))

    def test_bias_not_detected_as_accuracy(self):
        f,ll,_=analyze_pool(self.rows());rr=self.rows()
        for r in rr:r['dt']+=10
        f2,ll2,_=analyze_pool(rr);self.assertAlmostEqual(f2['t']-f['t'],10)
        np.testing.assert_allclose([r['delta_t'] for r in ll2],[r['delta_t'] for r in ll],atol=1e-12)

    def test_missing_rank_hull(self):
        for p in ([],[[0,0],[1,1]],[[1,1],[2,2],[3,3],[4,4]],[[35,-36],[35,36],[55,-36],[55,36]]):
            f,_=fit_center(p,np.zeros((len(p),2)));self.assertFalse(f['available']);self.assertIsNone(f['t'])
        with self.assertRaises(ValueError):fit_center([[1,2]]*4,[[1,float('nan')]]*4)

    def test_deletion_outside_hull_preserved(self):
        rows=[dict(anchor_id=str(i),n=x,t=y,dn=0,dt=0,flags_clear='True') for i,(x,y) in enumerate([(-1,0),(1,-1),(1,1),(2,-1),(2,1)])]
        f,ll,_=analyze_pool(rows);self.assertTrue(f['available']);self.assertFalse(ll[0]['available']);self.assertIsNone(ll[0]['delta_t'])

    def test_same_id_temporal_differences(self):
        ff=[];ll=[]
        for support in ('all_available','flags_clear'):
            for j in (1,2,3):
                ff.append(dict(support_name=support,stage_index=j,available=True,t=float(j)))
                ll.append(dict(support_name=support,stage_index=j,left_out='N01',available=True,t=j+.1*j,delta_t=.1*j))
        pairs=temporal_pairs(ff,ll);self.assertEqual(len(pairs),4)
        for r in pairs:self.assertAlmostEqual(r['change_delta_t'],.1);self.assertAlmostEqual(r['identity_error'],0)
        ll[0]['available']=False
        self.assertFalse(temporal_pairs(ff,ll)[0]['available']);self.assertIsNone(temporal_pairs(ff,ll)[0]['change_delta_t'])

    def source_rows(self):
        output=[]
        for j,count in zip((1,2,3),(8,6,5)):
            accepted=0
            for c in candidates():
                good=c['anchor_id'] not in ('N05','N09','N10');accepted+=good;clear=good and accepted<=count
                output.append(dict(c,stage_index=str(j),load_kN=(30,40,50)[j-1],available=str(good),origin_accepted=str(good),flags_clear=str(clear),
                    flags='' if clear else 'primary_low_ncc' if good else 'origin_exclude',dn=.1,dt=.2,old_dn=.1,old_dt=.2))
        return output

    def test_source_identity_and_quality_guards(self):
        rows=self.source_rows();self.assertEqual(len(validated_rows(rows)),51)
        for key,value in (('n',-50),('dn',float('nan')),('flags_clear','unknown'),('load_kN',31),('flags','invalid')):
            bad=copy.deepcopy(rows);bad[0][key]=value
            with self.assertRaises(ValueError):validated_rows(bad)
        bad=copy.deepcopy(rows);bad[1]=bad[0]
        with self.assertRaises(ValueError):validated_rows(bad)

    def test_missing_summary_not_zero(self):
        full=dict(support_name='all_available',stage_index=1)
        s=summarize([full],[dict(support_name='all_available',stage_index=1,available=False)],[])
        self.assertEqual(s['by_stage'][0]['valid'],0);self.assertIsNone(s['by_stage'][0]['max_abs_delta_t'])


if __name__=='__main__':unittest.main()
