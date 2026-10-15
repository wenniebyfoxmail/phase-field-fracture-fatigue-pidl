import sys
from pathlib import Path
import unittest
import json
import tempfile
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import d01_short_support as d

class ShortSupport(unittest.TestCase):
    def test_affine_unchanged(self):
        for slope in (-2.,0.,2.):
            values=100+slope*d.GRID
            for c in d.CENTRES:
                p,m,pok,mok,count=d.estimates(values,np.ones(41,bool),c)
                self.assertEqual(p,m);self.assertEqual(count,9);self.assertTrue(pok and mok)
    def test_isolated_spike_removed(self):
        v=np.ones(41)*10;v[d.index(0)]=50
        p,m,*_=d.estimates(v,np.ones(41,bool),0)
        self.assertEqual(p,50);self.assertEqual(m,10)
    def test_additive_stage_change(self):
        v=30+np.cos(d.GRID)
        a=d.estimates(v,np.ones(41,bool),0)
        b=d.estimates(v+2.5,np.ones(41,bool),0)
        self.assertEqual(b[0]-a[0],2.5);self.assertEqual(b[1]-a[1],2.5)
    def test_missing_not_shrunk(self):
        v=np.ones(41)*10;valid=np.ones(41,bool);valid[d.index(2)]=False
        p,m,pok,mok,count=d.estimates(v,valid,0)
        self.assertTrue(pok);self.assertFalse(mok);self.assertTrue(np.isnan(m));self.assertEqual(count,8)
    def test_no_padding(self):
        with self.assertRaises(ValueError): d.estimates(np.ones(41),np.ones(41,bool),10)
    def test_paired_median_not_difference_of_medians(self):
        rows=[dict(paired_valid=True,point_sensitivity_px=p,segment_sensitivity_px=m,paired_change_px=m-p) for p,m in ((0,1),(10,2),(11,12))]
        summary=d.paired_summary(rows)
        self.assertEqual(summary["median_paired_change_px"],1)
        self.assertEqual(summary["median_segment_px"]-summary["median_point_px"],-8)
    def test_signed_zero_and_reversal(self):
        rows=[dict(paired_valid=True,point_increment_px=p,segment_increment_px=m,absolute_distortion_px=abs(m-p)) for p,m in ((1,-1),(0,1),(-2,-2))]
        summary=d.stage_summary(rows)
        self.assertEqual(summary["sign_agreement"],1);self.assertEqual(summary["nonzero_point_increments"],2)
        self.assertEqual(summary["zero_point_increments"],1);self.assertEqual(summary["nonzero_segment_when_point_zero"],1)
    def test_sensitivity_missing(self):
        self.assertEqual(d.sensitivity([5,3,4]),2)
        self.assertTrue(np.isnan(d.sensitivity([np.nan,3,4])))
    def test_boolean_strict(self):
        with self.assertRaises(ValueError): d.boolean('unknown')
    def test_full_synthetic_calculation_and_endpoint_rule(self):
        groups={};tags={}
        for j in range(4):
            for t in range(1,13):
                for arm in d.ARMS:
                    k=(j,t,arm)
                    groups[k]=[dict(width_px=20+j+float(x),valid=True) for x in d.GRID]
                    tags[k]=False
        centres,sens,stages=d.calculate(groups,tags)
        self.assertEqual((len(centres),len(sens),len(stages)),(864,96,72))
        self.assertTrue(all(r['paired_change_px']==0 for r in sens))
        self.assertTrue(all(r['point_increment_px']==1 and r['segment_increment_px']==1 for r in stages))
        groups[(0,1,d.ARMS[0])][d.index(1)]['width_px']=100
        _,sens,_=d.calculate(groups,tags)
        target=next(r for r in sens if (r['stage_index'],r['transect_id'],r['arm'])==(0,1,d.ARMS[0]))
        self.assertEqual(target['point_sensitivity_px'],2) # interior spike is NOT a new primary endpoint
    def test_snapshot_duplicate_nonfinite_and_event_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'runtime_receipt.json').write_text(json.dumps(dict(execution='succeeded',code_commit=d.E020_COMMIT,git_status='',measurement_rows=3936,adjacent_rows=3840,curve_rows=96)))
            rows=[];pairs=[];curves=[];replay=[]
            for j in range(4):
                for t in range(1,13):
                    for arm in d.ARMS:
                        identity=dict(stage_index=j,transect_id=t,arm=arm,load_kN=d.LOADS[j])
                        rows.extend(dict(identity,t_index=i,tangent_px=x,width_px=10,valid=True) for i,x in enumerate(d.GRID))
                        pairs.extend(dict(identity,t_index_a=i,tangent_a_px=d.GRID[i],tangent_b_px=d.GRID[i+1],paired_valid=True,switch_candidate=False,split_candidate=False,merge_candidate=False,any_band_event=False,width_change_px=0) for i in range(40))
                        curves.append(dict(identity,valid_profiles=41,total_profiles=41,width_range_px=0))
                        replay.append(dict(identity,t0_valid=True,abs_replay_difference_px=0))
            for name,table in (('measurements.csv',rows),('adjacent_pairs.csv',pairs),('curve_summaries.csv',curves),('t0_replay.csv',replay)): d.write_csv(root/name,table)
            # boundary-crossing -4.5→-4 is outside the fixed tag union.
            pairs[11].update(split_candidate=True,any_band_event=True)
            d.write_csv(root/'adjacent_pairs.csv',pairs)
            _,tags=d.load_snapshot(root);self.assertFalse(tags[(0,1,d.ARMS[0])])
            pairs[12].update(split_candidate=True,any_band_event=True) # -4→-3.5 is inside
            d.write_csv(root/'adjacent_pairs.csv',pairs)
            _,tags=d.load_snapshot(root);self.assertTrue(tags[(0,1,d.ARMS[0])])
            rows[0]['width_px']='nan';d.write_csv(root/'measurements.csv',rows)
            with self.assertRaises(ValueError): d.load_snapshot(root)
            rows[0]['width_px']=10;rows[1]=rows[0].copy();d.write_csv(root/'measurements.csv',rows)
            with self.assertRaises(ValueError): d.load_snapshot(root)

if __name__=="__main__": unittest.main()
