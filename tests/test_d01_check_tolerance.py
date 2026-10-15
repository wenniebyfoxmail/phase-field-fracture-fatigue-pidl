import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from d01_check_tolerance import (assess,classify,residual_rows,load_background,load_tolerance,calculate,
                                 OFFSETS,BG_COMMIT,TOL_COMMIT,ARMS,LOADS)
from d01_relative_tolerance import evaluate,RHOS
from d01_background_anchor_diagnostic import write_csv

def tol_fixture(last=4.,common=False,eligible=True):
    tol=dict(eligible=eligible,status="no_admissible" if common else "right_censored" if last==4 else "bracketed",largest_stable_tested_px="" if common else str(last),first_loss_tested_px="0" if common else "" if last==4 else str(last+.5))
    bands={float(r):dict(direction_stable=not common and r<=last,amplitude_stable=not common and r<=last) for r in RHOS}
    return tol,bands

def background_fixture(root):
    bg=root/"bg";bg.mkdir();manifest=[];translations=[];anchors=[]
    for t in range(1,13):
        for k,(n,tt) in enumerate(OFFSETS):manifest.append(dict(transect_id=t,anchor_id=k,role="fit" if k<4 else "check",offset_n=n,offset_t=tt,eligible_first_frame=(t,k)!=(1,5)))
        for j in range(4):
            cn,ct=(.1,j*.2+.015) if j else (0.,0.)
            translations.append(dict(stage_index=j,load_kN=LOADS[j],transect_id=t,available=True,shift_n=cn,shift_t=ct))
            if not j:continue
            for k,(n,tt) in enumerate(OFFSETS):
                valid=(t,k)!=(1,5);sn=.1 if valid else np.nan;st=j*.2+k*.01 if valid else np.nan
                anchors.append(dict(stage_index=j,load_kN=LOADS[j],transect_id=t,anchor_id=k,role="fit" if k<4 else "check",offset_n=n,offset_t=tt,available=valid,reason="available_proxy" if valid else "unsafe_first_frame",correction_available=True,shift_n=sn,shift_t=st,before_residual_px=math.hypot(sn,st),after_residual_px=math.hypot(sn-cn,st-ct)))
    write_csv(bg/"anchor_matches.csv",anchors);write_csv(bg/"translations.csv",translations);write_csv(root/"manifest.csv",manifest)
    (bg/"runtime_receipt.json").write_text(json.dumps(dict(code_commit=BG_COMMIT,git_status="",execution="succeeded",anchor_rows=288,translation_rows=48)))
    return bg,root/"manifest.csv",anchors,translations,manifest

def tolerance_fixture(root):
    out=root/"tol";out.mkdir();pairs=[];bands=[]
    for arm in ARMS:
        for j in range(3):
            for t in range(1,13):
                identity=dict(arm=arm,stage_a=j,stage_b=j+1,load_a_kN=LOADS[j],load_b_kN=LOADS[j+1],transect_id=t)
                result,rows=evaluate(np.ones((9,9)),np.ones((9,9),bool),True)
                pairs.append(dict(identity,**result));bands.extend(dict(identity,**r) for r in rows)
    write_csv(out/"pair_bounds.csv",pairs);write_csv(out/"band_metrics.csv",bands)
    (out/"runtime_receipt.json").write_text(json.dumps(dict(experiment_id="S03-E023-D01",protocol="relative-tolerance-v1",code_commit=TOL_COMMIT,git_status="",execution="succeeded",pair_rows=72,band_rows=648)))
    return out,pairs,bands

class CheckToleranceTest(unittest.TestCase):
    def result(self,a,b,last=4.,valid=None,eligible=None,common=False):
        tol,bands=tol_fixture(last,common)
        return assess(a,b,valid if valid is not None else [True]*4,eligible if eligible is not None else [True]*4,tol,bands)
    def test_signed_not_magnitude_difference(self):
        r=self.result([1]*4,[-1]*4)
        self.assertEqual(r["matched_max_relative_t_px"],2.)
    def test_common_drift_cancellation(self):
        r=self.result([1]*4,[1]*4,last=0)
        self.assertEqual(r["status"],"proxy_compatible");self.assertEqual(r["required_tested_rho_px"],0.)
    def test_cross_anchor_distinct(self):
        r=self.result([-1,1,-1,1],[-1,1,-1,1],last=0)
        self.assertEqual(r["status"],"proxy_compatible");self.assertEqual(r["cross_status"],"beyond_stable_band")
        self.assertEqual(r["cross_max_relative_t_px"],2.)
    def test_fractional_ceiling(self):
        r=self.result([0]*4,[.50001]*4,last=.5)
        self.assertEqual(r["required_tested_rho_px"],1.)
        self.assertEqual(r["status"],"beyond_stable_band")
    def test_exact_half_ceiling(self):
        r=self.result([0]*4,[.5]*4,last=.5)
        self.assertEqual(r["required_tested_rho_px"],.5);self.assertEqual(r["status"],"proxy_compatible")
    def test_absolute_outside_despite_zero_relative(self):
        r=self.result([2.01]*4,[2.01]*4)
        self.assertEqual(r["status"],"outside_grid");self.assertTrue(r["absolute_outside_grid"])
    def test_exact_absolute_limit(self):
        self.assertEqual(self.result([2]*4,[-2]*4)["status"],"proxy_compatible")
    def test_common_sensitive_priority_and_flags(self):
        r=self.result([3]*4,[3]*4,common=True)
        self.assertEqual(r["status"],"common_sensitive");self.assertTrue(r["absolute_outside_grid"])
    def test_fixed_three_not_missing(self):
        r=self.result([0,np.nan,0,0],[.1,np.nan,.1,.1],eligible=[True,False,True,True],valid=[True,False,True,True])
        self.assertEqual(r["status"],"proxy_compatible");self.assertEqual(r["valid_checks"],3);self.assertFalse(r["full_four_checks"])
    def test_missing_eligible_does_not_shrink(self):
        r=self.result([0,0,0,0],[.1,np.nan,.1,.1],valid=[True,False,True,True])
        self.assertEqual(r["status"],"unassessable");self.assertFalse(r["complete_eligible_checks"])
    def test_nonfinite_valid_rejected(self):
        with self.assertRaises(ValueError):self.result([0]*4,[np.nan,0,0,0])
    def test_ineligible_tolerance(self):
        _,b=tol_fixture();r=classify(True,False,False,1,.2,b)
        self.assertEqual(r["status"],"unassessable")
    def test_full_source_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bg,manifest,*_=background_fixture(root);out,_,_=tolerance_fixture(root)
            m,t,a=load_background(bg,manifest);p,b=load_tolerance(out)
            pairs,checks,stages,summary=calculate(m,t,a,p,b)
            self.assertEqual((len(pairs),len(checks),len(stages)),(72,288,384))
            self.assertTrue(all(r["status"]=="proxy_compatible" for r in pairs))
            self.assertEqual([r["valid_check_pairs"] for r in summary["by_arm"]],[141,141])
            origins=[r for r in stages if r["stage_index"]==0 and r["valid"]]
            self.assertTrue(all(r["reference_zero_by_definition"] and r["residual_t_px"]==0 for r in origins))
            # Existing units are already native; no5616/2000 scale conversion.
            r=next(r for r in stages if r["arm"]==ARMS[0] and r["stage_index"]==1 and r["transect_id"]==2 and r["anchor_id"]==4)
            self.assertAlmostEqual(r["residual_t_px"],.24)
            r=next(r for r in stages if r["arm"]==ARMS[1] and r["stage_index"]==1 and r["transect_id"]==2 and r["anchor_id"]==4)
            self.assertAlmostEqual(r["residual_t_px"],.025)
    def test_malformed_background(self):
        for field,value,message in (("shift_t",float("nan"),"before norm replay"),("before_residual_px",99.,"before norm replay"),("role","check","anchor role/geometry")):
            with self.subTest(field=field),tempfile.TemporaryDirectory() as d:
                root=Path(d);bg,manifest,anchors,*_=background_fixture(root);anchors[0][field]=value;write_csv(bg/"anchor_matches.csv",anchors)
                with self.assertRaisesRegex(ValueError,message):load_background(bg,manifest)
    def test_duplicate_background(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bg,manifest,anchors,*_=background_fixture(root);anchors[1]=anchors[0];write_csv(bg/"anchor_matches.csv",anchors)
            with self.assertRaisesRegex(ValueError,"anchor key/duplicate"):load_background(bg,manifest)
    def test_frozen_manifest_exclusion(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bg,manifest,_,_,rows=background_fixture(root);rows[5]["eligible_first_frame"]=True;write_csv(manifest,rows)
            with self.assertRaisesRegex(ValueError,"frozen exclusion"):load_background(bg,manifest)
    def test_wrong_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/"runtime_receipt.json").write_text("{}")
            with self.assertRaisesRegex(ValueError,"background receipt identity"):load_background(p,p/"manifest.csv")
            with self.assertRaisesRegex(ValueError,"tolerance receipt identity"):load_tolerance(p)
    def test_nonfinite_tolerance(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);out,pairs,_=tolerance_fixture(p);pairs[0]["baseline_delta_px"]=float("nan");write_csv(out/"pair_bounds.csv",pairs)
            with self.assertRaisesRegex(ValueError,"invalid eligible D0"):load_tolerance(out)
    def test_duplicate_tolerance_band(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);out,_,bands=tolerance_fixture(p);bands[1]=bands[0];write_csv(out/"band_metrics.csv",bands)
            with self.assertRaisesRegex(ValueError,"band key/duplicate"):load_tolerance(out)
    def test_tolerance_replay(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);out,pairs,_=tolerance_fixture(p);pairs[0]["status"]="bracketed";write_csv(out/"pair_bounds.csv",pairs)
            with self.assertRaisesRegex(ValueError,"bounds status replay"):load_tolerance(out)
    def test_incomplete_eligible_pair(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);out,pairs,_=tolerance_fixture(p);pairs[0]["valid_cells"]=80;write_csv(out/"pair_bounds.csv",pairs)
            with self.assertRaisesRegex(ValueError,"eligible full81 support"):load_tolerance(out)
    def test_incomplete_band_and_false_amplitude(self):
        for field,value,message in (("valid_cells",8,"eligible band support"),("amplitude_stable",False,"strict amplitude replay")):
            with self.subTest(field=field),tempfile.TemporaryDirectory() as d:
                p=Path(d);out,_,bands=tolerance_fixture(p);bands[0][field]=value;write_csv(out/"band_metrics.csv",bands)
                with self.assertRaisesRegex(ValueError,message):load_tolerance(out)
    def test_origin_translation_unavailable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);bg,manifest,_,translations,_=background_fixture(root);translations[0]["available"]=False;write_csv(bg/"translations.csv",translations)
            with self.assertRaisesRegex(ValueError,"origin translation must be available"):load_background(bg,manifest)

if __name__=="__main__":unittest.main()
