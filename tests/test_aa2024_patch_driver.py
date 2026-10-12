import sys
import unittest
import tempfile
import json
from unittest.mock import patch
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from aa2024_patch_driver import dump,digest,validate,vector_error
import aa2024_patch_driver as driver

SCHEMA="# ID; x_undef [mm]; y_undef [mm]; z_undef [mm]; u [mm]; v [mm]; w [mm]; epsx [%]; epsy [%]; epsxy [1]; epseqv [%]\n"


class ValidationTests(unittest.TestCase):
    def receipt(self,fit):
        dump(fit/"q_profile.json",{"profile":[],"synthetic":True})
        dump(fit/"execution_receipt.json",{"mode":"fit","execution_status":"succeeded",
             "runner_sha256":digest(driver.__file__),"artifacts_sha256":{
             n:digest(fit/n) for n in ("fit.json","frozen_predictions.npz","q_profile.json")}})

    def fixture(self,root,missing=False,z_missing=False):
        root=Path(root);fit=root/"fit";out=root/"out";fit.mkdir();out.mkdir()
        x,y=np.meshgrid(np.arange(4),np.arange(3));xy=np.c_[x.ravel(),y.ravel()]
        u=np.c_[xy[:,0]**2,xy[:,1]**2]*.001
        np.savez(fit/"frozen_predictions.npz",ids=np.arange(1,13),xy=xy,weights=np.ones(12),u7=np.zeros_like(u),candidate=u,secant=u+.001,intact=np.zeros_like(u),d0_only=np.zeros_like(u))
        high=root/"high.txt"
        header="# current_stage_index : 9\n# reference_stage_index : 1\n# cycles : value_element : 126873.5\n# force : value_element : 15000\n"
        text=header+SCHEMA+"".join(f"{i+1};{p[0]};{p[1]};{'nan' if z_missing and i==0 else 0};{'nan' if missing and i==0 else v[0]};{v[1]};0;0;0;0;0\n" for i,(p,v) in enumerate(zip(xy,u)))
        high.write_text(text)
        dump(fit/"fit.json",{"status":"frozen_before_high_response_access","prediction_sha256":digest(fit/"frozen_predictions.npz"),"held_member_sha256":digest(high),"held_force":15000.,"q":.4})
        self.receipt(fit)
        return fit,high,out

    def test_validation_missingness_keeps_common_comparator_support(self):
        with tempfile.TemporaryDirectory() as root:
            fit,high,out=self.fixture(root,missing=True)
            validate(fit,high,out)
            m=json.loads((out/"metrics.json").read_text())
            self.assertEqual(m["eligible"],11)
            self.assertEqual(m["missing"],1)
            self.assertLess(m["vector_MAE_mm"]["candidate"],1e-14)

    def test_changed_holdout_member_rejected_before_scoring(self):
        with tempfile.TemporaryDirectory() as root:
            fit,high,out=self.fixture(root)
            high.write_text(high.read_text()+"\n")
            with self.assertRaisesRegex(ValueError,"external member identity"):
                validate(fit,high,out)
            self.assertFalse((out/"metrics.json").exists())

    def test_changed_frozen_prediction_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            fit,high,out=self.fixture(root)
            with (fit/"frozen_predictions.npz").open("ab") as f:f.write(b"changed")
            with self.assertRaisesRegex(ValueError,"artifact mismatch"):
                validate(fit,high,out)

    def test_vector_error_definition(self):
        self.assertEqual(vector_error(np.array([[3.,4.],[0.,2.]]),np.array([1.,3.])),2.75)

    def test_missing_failed_and_wrong_mode_receipts_stop_before_high_parse(self):
        for state in (None,"failed","wrong_mode"):
            with tempfile.TemporaryDirectory() as root:
                fit,high,out=self.fixture(root)
                if state is None:
                    (fit/"execution_receipt.json").unlink()
                else:
                    r=json.loads((fit/"execution_receipt.json").read_text())
                    if state=="failed":r["execution_status"]="failed"
                    else:r["mode"]="prepare"
                    dump(fit/"execution_receipt.json",r)
                with patch.object(driver,"parse_nodemap",side_effect=AssertionError("target parsed")) as parse:
                    with self.assertRaises(ValueError):validate(fit,high,out)
                    parse.assert_not_called()

    def test_fit_metadata_and_profile_tamper_stop_before_high_parse(self):
        for name in ("fit.json","q_profile.json"):
            with tempfile.TemporaryDirectory() as root:
                fit,high,out=self.fixture(root)
                (fit/name).write_text((fit/name).read_text()+"\n")
                with patch.object(driver,"parse_nodemap",side_effect=AssertionError("target parsed")) as parse:
                    with self.assertRaisesRegex(ValueError,"artifact mismatch"):validate(fit,high,out)
                    parse.assert_not_called()

    def test_z_only_missingness_preserves_in_plane_comparison(self):
        results=[]
        for missing in (False,True):
            with tempfile.TemporaryDirectory() as root:
                fit,high,out=self.fixture(root,z_missing=missing)
                validate(fit,high,out)
                results.append(json.loads((out/"metrics.json").read_text()))
        self.assertEqual(results[0],results[1])


if __name__=="__main__":unittest.main()
