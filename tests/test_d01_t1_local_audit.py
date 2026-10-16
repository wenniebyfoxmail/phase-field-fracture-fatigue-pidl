import json
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from d01_t1_local_audit import decompose,position_cases,summarize,extract,validate_background,ARMS,S,T,STAGES,LOADS
from independent_d01_halfdepth import measure
from d01_tangent_width_response import halfdepth_components


def fixture():
    arrays={};records={}
    for arm in ARMS:
        for j,load in zip(STAGES,LOADS):
            profile=(180-100*np.exp(-S*S/(2*(6-j)**2))).astype(np.float32)
            r=measure(S,profile);components=halfdepth_components(S,r)
            key=f"st{j}_tr1_{arm}"
            arrays[key+"_profiles"]=np.tile(profile,(41,1))
            arrays[key+"_deficits"]=np.tile(r["deficit"],(41,1))
            arrays[key+"_strip"]=np.ones((57,121),np.float32)*100
            for k,t in enumerate(T):
                records[(j,arm,float(t))]=dict(t_index=str(k+16),load_kN=str(load),valid="True",
                    components_json=json.dumps(components),**{name:str(r[name]) for name in ("width_px","left_px","right_px","peak_px","depth")})
    return arrays,records


class T1AuditTests(unittest.TestCase):
    def test_decomposition_no_clip(self):
        r=decompose([15,11,14]);self.assertEqual(r["secant_error"],-7)
        self.assertEqual(r["raw_error_identity"],-7);self.assertEqual(r["persistence_error"],-3)
        self.assertTrue(r["reversal_down_up"])

    def test_clipping_is_not_raw_identity(self):
        r=decompose([10,1,2]);self.assertTrue(r["clip_active"])
        self.assertEqual(r["secant_error"],-2);self.assertEqual(r["raw_error_identity"],-10)

    def test_invalid_width_vector(self):
        for w in ([1,2],[1,np.nan,3],[1,2,np.inf]):
            with self.assertRaises(ValueError):decompose(w)

    def test_grid_denominators_and_identity(self):
        w=np.tile([[15],[11],[14]],(1,9));r=position_cases(w,np.ones_like(w,bool),ARMS[0])
        self.assertEqual(len(r),738)
        self.assertEqual(sum(x["mode"]=="common" for x in r),9)
        self.assertEqual(sum(x["mode"]=="independent" for x in r),729)
        self.assertTrue(all(x["secant_error"]==x["raw_error_identity"]==-7 for x in r))
        self.assertTrue(all(x["t30"]==x["t40"]==x["t50"] for x in r if x["mode"]=="common"))

    def test_independent_positions_not_common_only(self):
        w=np.array([T+15,T*2+11,T*3+14])
        rows=position_cases(w,np.ones_like(w,bool),ARMS[0])
        self.assertTrue(any(r["t30"]!=r["t40"] for r in rows if r["mode"]=="independent"))
        self.assertGreater(len({r["secant_error"] for r in rows if r["mode"]=="independent"}),1)

    def test_missing_profile_retains_opportunities(self):
        w=np.tile([[15.],[11.],[14.]],(1,9));v=np.ones_like(w,bool);v[0,0]=False;w[0,0]=np.nan
        rows=[]
        for arm in ARMS:rows.extend(position_cases(w,v,arm))
        s=summarize(rows)
        for a in s["by_arm"]:
            self.assertEqual(a["common"]["total"],9);self.assertEqual(a["common"]["valid"],8)
            self.assertEqual(a["independent"]["valid"],648)

    def test_cache_extraction_reproduces_all_rows(self):
        a,r=fixture();measurements,pairs,positions,arrays=extract(a,r)
        self.assertEqual((len(measurements),len(pairs),len(positions)),(54,4,1476))
        self.assertEqual(len(arrays),24)

    def test_cache_mismatch_rejected(self):
        a,r=fixture();a["st1_tr1_original_H_deficits"][16,0]+=1
        with self.assertRaisesRegex(ValueError,"deficit"):extract(a,r)
        a,r=fixture();r[(1,ARMS[0],-2.)]["width_px"]="999"
        with self.assertRaisesRegex(ValueError,"measurement"):extract(a,r)

    def test_missing_stage_and_bad_grid_rejected(self):
        a,r=fixture();r.pop((1,ARMS[0],-2.))
        with self.assertRaisesRegex(ValueError,"missing"):extract(a,r)
        with self.assertRaises(ValueError):position_cases(np.ones((3,8)),np.ones((3,8),bool),ARMS[0])

    def test_nonfinite_cache_or_reference_cannot_bypass_comparison(self):
        a,r=fixture();a["st1_tr1_original_H_deficits"][16,0]=np.nan
        with self.assertRaisesRegex(ValueError,"nonfinite"):extract(a,r)
        a,r=fixture();r[(1,ARMS[0],-2.)]["width_px"]="nan"
        with self.assertRaisesRegex(ValueError,"measurement"):extract(a,r)

    def test_background_keys_loads_and_first_frame_exclusion(self):
        translations=[dict(stage_index=j,transect_id=1,load_kN=load,available="True",shift_n=".1",shift_t=".2") for j,load in zip(STAGES,LOADS)]
        checks=[dict(stage_index=j,transect_id=1,anchor_id=k,load_kN=load,role="check",available="False" if k==5 else "True",shift_n=".1",shift_t=".2",offset_n=-100 if k<6 else 100,offset_t=-72 if k%2==0 else 72) for j,load in zip(STAGES,LOADS) for k in range(4,8)]
        validate_background(translations,checks)
        bad=[dict(r) for r in checks];bad[1]["available"]="True"
        with self.assertRaisesRegex(ValueError,"a5"):validate_background(translations,bad)
        bad=[dict(r) for r in checks];bad[-1]=dict(bad[0])
        with self.assertRaisesRegex(ValueError,"identity"):validate_background(translations,bad)
        bad=[dict(r) for r in translations];bad[0]["shift_n"]="nan"
        with self.assertRaisesRegex(ValueError,"nonfinite"):validate_background(bad,checks)


if __name__=="__main__":unittest.main()
