import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from d01_relative_tolerance import evaluate, bounds, RHOS, SHIFTS, EXPECTED_COUNTS, UPSTREAM, load_source
from d01_background_anchor_diagnostic import write_csv

def source_fixture(p):
    (p/"runtime_receipt.json").write_text(json.dumps(dict(experiment_id="S03-E022-D01",protocol="stage-shift-v1",execution="succeeded",code_commit=UPSTREAM,git_status="")))
    (p/"summary.json").write_text(json.dumps(dict(experiment_id="S03-E022-D01",protocol="stage-shift-v1",pair_rows=72,perturbation_rows=5832,common_rows=648)))
    pairs=[];cells=[];loads=[10,30,40,50]
    for arm in ("original_H","background_aligned"):
        for j in range(3):
            for t in range(1,13):
                identity=dict(arm=arm,stage_a=j,stage_b=j+1,load_a_kN=loads[j],load_b_kN=loads[j+1],transect_id=t)
                pairs.append(dict(identity,paired_valid=True,baseline_valid=True,baseline_nonzero=True,baseline_delta_px=1.,common_sign_loss=False,independent_sign_loss=False))
                for da in SHIFTS:
                    for db in SHIFTS:
                        cells.append(dict(identity,shift_a_px=da,shift_b_px=db,common=bool(da==db),valid_difference=True,baseline_valid=True,baseline_delta_px=1.,stage_delta_px=1.,deviation_px=0.))
    write_csv(p/"pair_metrics.csv",pairs);write_csv(p/"perturbations.csv",cells)
    return pairs,cells

class RelativeToleranceTest(unittest.TestCase):
    def test_nested_counts(self):
        _, rows=evaluate(np.ones((9,9)),np.ones((9,9),bool),True)
        self.assertEqual([r["grid_cells"] for r in rows],EXPECTED_COUNTS)
    def test_right_censor(self):
        r,_=evaluate(np.ones((9,9)),np.ones((9,9),bool),True)
        self.assertEqual((r["status"],r["largest_stable_tested_px"],r["first_loss_tested_px"]),("right_censored",4.,None))
    def test_no_admissible_common(self):
        m=np.ones((9,9));m[0,0]=-1
        r,rows=evaluate(m,np.ones((9,9),bool),True)
        self.assertEqual(r["status"],"no_admissible");self.assertIsNone(r["largest_stable_tested_px"])
        self.assertFalse(any(x["direction_stable"] for x in rows))
    def test_zero_only_safe(self):
        m=np.ones((9,9));m[0,1]=0
        r,_=evaluate(m,np.ones((9,9),bool),True)
        self.assertEqual((r["largest_stable_tested_px"],r["first_loss_tested_px"]),(0.,.5))
    def test_axis_and_bracket(self):
        m=1+SHIFTS[:,None]-SHIFTS[None,:]
        r,rows=evaluate(m,np.ones((9,9),bool),True)
        self.assertEqual((r["largest_stable_tested_px"],r["first_loss_tested_px"]),(.5,1.))
        self.assertEqual(rows[2]["max_abs_deviation_px"],1.)
    def test_negative_direction(self):
        m=-np.ones((9,9));m[1,3]=1
        r,_=evaluate(m,np.ones((9,9),bool),True)
        self.assertEqual((r["largest_stable_tested_px"],r["first_loss_tested_px"]),(.5,1.))
    def test_zero_baseline(self):
        m=np.ones((9,9));m[4,4]=0
        r,rows=evaluate(m,np.ones((9,9),bool),True)
        self.assertEqual(r["status"],"unassessable");self.assertTrue(all(x["direction_stable"] is None for x in rows))
    def test_missing_full_support(self):
        m=np.ones((9,9));v=np.ones((9,9),bool);v[0,8]=False;m[0,8]=np.nan
        r,rows=evaluate(m,v,True)
        self.assertEqual(r["status"],"unassessable");self.assertEqual(rows[0]["valid_cells"],9)
    def test_missing_baseline(self):
        m=np.ones((9,9));v=np.ones((9,9),bool);v[4,4]=False;m[4,4]=np.nan
        r,_=evaluate(m,v,False);self.assertFalse(r["baseline_valid"])
    def test_strict_amplitude_distinct(self):
        m=np.ones((9,9));m[0,0]=2
        r,rows=evaluate(m,np.ones((9,9),bool),True)
        self.assertEqual(r["status"],"right_censored");self.assertFalse(rows[0]["amplitude_stable"])
    def test_nonfinite_rejected(self):
        m=np.ones((9,9));m[0,0]=np.nan
        with self.assertRaises(ValueError):evaluate(m,np.ones((9,9),bool),True)
    def test_baseline_flag_rejected(self):
        with self.assertRaises(ValueError):evaluate(np.ones((9,9)),np.ones((9,9),bool),False)
    def test_nonnested_rejected(self):
        with self.assertRaises(ValueError):bounds([True,False,True]+[False]*6)
    def test_wrong_receipt_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/"runtime_receipt.json").write_text(json.dumps({"execution":"succeeded"}))
            with self.assertRaises(ValueError):load_source(p)
    def test_duplicate_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/"runtime_receipt.json").write_text(json.dumps(dict(experiment_id="S03-E022-D01",protocol="stage-shift-v1",execution="succeeded",code_commit=UPSTREAM,git_status="")))
            (p/"summary.json").write_text(json.dumps(dict(experiment_id="S03-E022-D01",protocol="stage-shift-v1",pair_rows=72,perturbation_rows=5832,common_rows=648)))
            row=dict(arm="original_H",stage_a=0,stage_b=1,load_a_kN=10,load_b_kN=30,transect_id=1,baseline_valid=True,baseline_delta_px=1.)
            write_csv(p/"pair_metrics.csv",[row]*72);write_csv(p/"perturbations.csv",[row]*5832)
            with self.assertRaisesRegex(ValueError,"duplicate pair"):load_source(p)
    def test_full_synthetic_source(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);source_fixture(p)
            self.assertEqual(len(load_source(p)),72)
    def test_nonfinite_metric_rejected(self):
        for bad in (np.nan,np.inf,-np.inf):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as d:
                p=Path(d);pairs,_=source_fixture(p);pairs[0]["baseline_delta_px"]=bad;write_csv(p/"pair_metrics.csv",pairs)
                with self.assertRaisesRegex(ValueError,"nonfinite metric D0"):load_source(p)
    def test_duplicate_cell_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);_,cells=source_fixture(p);cells[1]=cells[0];write_csv(p/"perturbations.csv",cells)
            with self.assertRaisesRegex(ValueError,"duplicate cell"):load_source(p)
    def test_malformed_source_rejected(self):
        for field,value,message in (("shift_a_px",.1,"shift grid"),("common",False,"diagonal flag"),("deviation_px",1.,"inconsistent deviation"),("load_a_kN",20,"load labels")):
            with self.subTest(field=field),tempfile.TemporaryDirectory() as d:
                p=Path(d);_,cells=source_fixture(p);cells[0][field]=value;write_csv(p/"perturbations.csv",cells)
                with self.assertRaisesRegex(ValueError,message):load_source(p)
    def test_eps_direction_not_equivalent_amplitude(self):
        m=np.ones((9,9));m[0,0]=5e-9
        _,rows=evaluate(m,np.ones((9,9),bool),True)
        self.assertFalse(rows[0]["direction_stable"]);self.assertTrue(rows[0]["amplitude_stable"])

if __name__=="__main__":unittest.main()
