import sys
from pathlib import Path
import unittest
import tempfile
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import d01_tangent_width_response as d

S=np.arange(-60,60.25,.25)

def result(deficit):
    r=d.measure(S,180-np.asarray(deficit))
    r["components"]=d.halfdepth_components(S,r)
    return r

class TestTangent(unittest.TestCase):
    def test_smooth_width_response(self):
        prior=None
        for t in d.TANGENTS:
            sigma=3+.05*t
            r=result(100*np.exp(-S*S/(2*sigma*sigma)))
            self.assertTrue(r["valid"])
            self.assertLess(abs(r["width_px"]-2*np.sqrt(2*np.log(2))*sigma),.02)
            if prior is not None: self.assertFalse(d.classify_pair(prior,r)["any_band_event"])
            prior=r
    def test_selected_switch(self):
        a=np.exp(-(S+5)**2/8); b=np.exp(-(S-5)**2/8)
        left=result(100*a+80*b); right=result(80*a+100*b)
        self.assertTrue(d.classify_pair(left,right)["switch_candidate"])
    def test_merge_split(self):
        two=result(100*np.exp(-(S+5)**2/8)+95*np.exp(-(S-5)**2/8))
        one=result(np.where(abs(S)<=10,100.,0.))
        self.assertTrue(d.classify_pair(two,one)["merge_candidate"])
        self.assertTrue(d.classify_pair(one,two)["split_candidate"])
    def test_peak_motion_in_same_band_not_switch(self):
        base=np.where(abs(S)<=10,90.,0.)
        a=base.copy(); b=base.copy()
        a[np.argmin(abs(S+8))]=100; b[np.argmin(abs(S-8))]=100
        x,y=result(a),result(b)
        self.assertEqual(abs(x["peak_px"]-y["peak_px"]),16)
        self.assertFalse(d.classify_pair(x,y)["any_band_event"])
    def test_invalid_and_censored(self):
        a=result(np.zeros_like(S)); b=result(100*np.exp(-S*S/18))
        self.assertFalse(d.classify_pair(a,b)["paired_valid"])
        # Underlying censor detection is tested in E018; this adapter must retain it.
        c=dict(b,valid=False,reason="censored")
        self.assertEqual(d.halfdepth_components(S,c),[])
    def test_tangent_zero_geometry(self):
        tr=dict(center=[100.,100.],normal=[.6,.8])
        x=d.sampling_grid(tr["center"],tr["normal"],S)
        y=d.sampling_grid(tr["center"],tr["normal"],S,tangent_offsets=np.arange(-2,3)+d.TANGENTS[20])
        np.testing.assert_array_equal(x,y)
    def test_snapshot_digest_detects_change(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"synthetic.txt";p.write_bytes(b"one")
            digest=d.input_digest([p]);p.write_bytes(b"two")
            self.assertNotEqual(digest,d.input_digest([p]))
    def test_reference_finite_and_origin_zero(self):
        translations=[dict(stage_index=j,transect_id=t,load_kN=(10,30,40,50)[j],available="True",shift_n="0",shift_t="0") for j in range(4) for t in range(1,13)]
        expected=[dict(stage_index=j,transect_id=t,load_kN=(10,30,40,50)[j],arm=arm,variant=v,valid="True",width_px="10") for j in range(4) for t in range(1,13) for arm in d.ARMS for v in ("baseline","normal_minus2","normal_plus2","tangent_minus2","tangent_plus2")]
        self.assertEqual(len(d.validate_records(translations,expected)[1]),96)
        expected[0]["width_px"]="nan"
        with self.assertRaises(ValueError): d.validate_records(translations,expected)
        expected[0]["width_px"]="10";translations[0]["shift_t"]="1"
        with self.assertRaises(ValueError): d.validate_records(translations,expected)

if __name__=="__main__": unittest.main()
