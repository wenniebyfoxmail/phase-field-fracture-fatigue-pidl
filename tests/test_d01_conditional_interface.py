import csv
from dataclasses import fields, replace
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from d01_conditional_interface import (HistoryPacket, Measurement, predict, replay,
                                      eligibility, summarize, load_stage, UNIT)


def packet(t=1, case="B4-K1-Q40", beam=4):
    return HistoryPacket(case,beam,t,1,True,
                         (Measurement(0,10.,10.,True,"ok"),Measurement(1,30.,12.,True,"ok")),
                         40.,"E015 development-v1")


class ConditionalInterfaceTests(unittest.TestCase):
    def replay(self, packets=None, reference=None, predictor=None):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d)/"predictions.json"
            def load(case,t):
                self.assertTrue(target.is_file())
                saved=json.loads(target.read_text())
                self.assertEqual(len(saved),len(packets or [packet()]))
                self.assertTrue(all("arms" in r for r in saved))
                return reference
            kwargs={} if predictor is None else dict(predictor=predictor)
            return replay(packets or [packet()],target,load,**kwargs)

    def test_same_formula_unequal_loads(self):
        r=predict(packet())
        self.assertEqual(r["arms"]["persistence"]["prediction_px"],12.)
        self.assertEqual(r["arms"]["secant"]["prediction_px"],13.)

    def test_target_mutation_and_removal_leave_predictions_identical(self):
        baseline=None
        for target in (None,Measurement(2,40.,100.,True,"ok"),Measurement(2,40.,2.,True,"ok"),
                       Measurement(2,40.,None,False,"low_contrast")):
            p,rows=self.replay(reference=target)
            if baseline is None: baseline=p
            self.assertEqual(p,baseline)
            self.assertEqual(rows[0]["C"],bool(target and target.valid))

    def test_prediction_snapshot_precedes_callback(self):
        self.replay(reference=Measurement(2,40.,14.,True,"ok"))

    def test_api_has_no_target_or_ledger_fields(self):
        names={f.name for f in fields(HistoryPacket)}
        self.assertTrue(all("target" not in n and "ledger" not in n for n in names))
        with self.assertRaises(TypeError): HistoryPacket(**dict(packet().__dict__,target_width=40.))

    def test_missing_target_keeps_prediction_and_reports_R(self):
        p,r=self.replay()
        self.assertTrue(p[0]["arms"]["secant"]["success"])
        self.assertFalse(r[0]["R"]);self.assertEqual(r[0]["terminal_status"],"reference_unavailable")
        self.assertIsNone(r[0]["reference_px"])

    def test_missing_history_no_target_callback(self):
        p=replace(packet(),history=(None,packet().history[1]))
        with tempfile.TemporaryDirectory() as d:
            def forbidden(*args): raise AssertionError("target loader called")
            pred,rows=replay([p],Path(d)/"p.json",forbidden)
        self.assertFalse(rows[0]["E"]);self.assertFalse(rows[0]["C"])
        self.assertFalse(pred[0]["arms"]["secant"]["attempted"])

    def test_arm_failure_same_common_support(self):
        def fail(history,loads,q,arm):
            if arm=="secant": raise ArithmeticError("synthetic")
            return history[-1]
        p,r=self.replay(reference=Measurement(2,40.,14.,True,"ok"),predictor=fail)
        self.assertTrue(r[0]["R"]);self.assertFalse(r[0]["C"])
        self.assertIsNone(r[0]["persistence_abs_error_px"])
        self.assertEqual(r[0]["terminal_status"],"arm_failure")

    def test_nonfinite_output_is_failure(self):
        p,r=self.replay(predictor=lambda *args:float("nan"))
        self.assertFalse(p[0]["arms"]["secant"]["success"])

    def test_invalid_queries_and_load_order(self):
        for q in (30.,20.,float("nan"),float("inf")):
            p=replace(packet(),query_nominal_load_kN=q)
            e,valid,_=eligibility(p);self.assertTrue(e);self.assertFalse(valid)
            self.replay(packets=[p])
        p=replace(packet(),history=(Measurement(0,30.,10.,True,"ok"),packet().history[1]))
        self.assertFalse(eligibility(p)[0])

    def test_wrong_cutoff_unit_and_first_frame(self):
        for p in (replace(packet(),history=(packet().history[0],Measurement(2,30.,12.,True,"ok"))),
                  replace(packet(),unit="mm")):
            with self.assertRaises(ValueError): predict(p)
        self.assertFalse(predict(replace(packet(),origin_valid=False))["E"])

    def test_clipping_preserved(self):
        p=replace(packet(),history=(Measurement(0,10.,100.,True,"ok"),Measurement(1,30.,119.,True,"ok")))
        self.assertEqual(predict(p)["arms"]["secant"]["prediction_px"],120.)
        p=replace(packet(),history=(Measurement(0,10.,10.,True,"ok"),Measurement(1,30.,1.,True,"ok")))
        self.assertEqual(predict(p)["arms"]["secant"]["prediction_px"],0.)

    def test_all_denominators_and_missing_beam_not_reweighted(self):
        cases=[dict(case_id=f"B{b}",beam=b) for b in (4,5,6)]
        packets=[packet(t,c["case_id"],c["beam"]) for c in cases for t in range(1,13)]
        with tempfile.TemporaryDirectory() as d:
            _,rows=replay(packets,Path(d)/"p.json",lambda case,t:None if case=="B6" else Measurement(2,40.,14.,True,"ok"))
        metrics,s=summarize(rows,cases)
        self.assertEqual(s["nominal_opportunities"],36);self.assertEqual(s["common_scored"],24)
        self.assertIsNone(s["equal_beam"]["secant_MAE_px"])
        for r in metrics:
            self.assertEqual(sum(v for k,v in r.items() if k.startswith("terminal_")),r["N"])
            self.assertEqual(r["persistence_success"],12)

    def test_missing_and_duplicate_csv_keys_and_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);table=root/"m.csv"
            base=dict(beam=4,stage_index=0,load_kN=10,source=str(root/"a.JPG"),
                      role="crack",transect_id=1,origin_eligible="True",fwhm_native_px=10,valid="True",reason="ok")
            def save(rows):
                with table.open("w",newline="") as f:
                    w=csv.DictWriter(f,fieldnames=list(base));w.writeheader();w.writerows(rows)
            stage=dict(beam=4,stage_index=0,nominal_load_kN=10,image="a.JPG")
            geometry={1:dict(origin_valid=True),2:dict(origin_valid=True)}
            # Malformed future semantic values cannot be decoded as history.
            future=dict(base,stage_index=2,load_kN="FUTURE",fwhm_native_px="SECRET",valid="INVALID")
            save([base,future]);result=load_stage(table,stage,root,geometry)
            self.assertEqual(set(result),{1});self.assertEqual(result[1].width_px,10.)
            save([base,base])
            with self.assertRaises(ValueError):load_stage(table,stage,root,geometry)
            for bad in (dict(base,beam=4,load_kN=20),dict(base,source=str(root/"other.JPG")),dict(base,origin_eligible="False")):
                save([bad])
                with self.assertRaises(ValueError):load_stage(table,stage,root,geometry)

    def test_snapshot_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"p.json";path.write_text("old")
            with self.assertRaises(FileExistsError):replay([packet()],path,lambda *args:None)
            self.assertEqual(path.read_text(),"old")


if __name__=="__main__": unittest.main()
