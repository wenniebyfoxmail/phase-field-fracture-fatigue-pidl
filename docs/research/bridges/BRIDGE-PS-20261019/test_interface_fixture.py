"""Artificial values only; no scientific input files, fitting, forward or autograd."""
import copy
import unittest
from dataclasses import replace
from interface_fixture import (Packet, history_contract, canonical, uncanonical,
    origin_features, canonical_coefficient, dot, pulled_penalty, check_preparation_plan)


class InterfaceFixtures(unittest.TestCase):
    def setUp(self):
        self.packets = [Packet("published-DIC", "fixture-A", "release_step", n,
                               "fixed-grid", "first-frame", "response")
                        for n in (0, 10, 20)]
        self.base = list(range(12))
        self.q = [[float(k+i) for k in range(8)] for i in range(3)]

    def test_release_is_not_physical_independence(self):
        self.assertEqual(history_contract(self.packets, 20)["physical_independence"], "unknown")

    def test_future_is_rejected(self):
        with self.assertRaises(ValueError): history_contract(self.packets, 10)

    def test_mixed_clocks_are_rejected(self):
        p = list(self.packets); p[-1] = replace(p[-1], clock="cycle")
        with self.assertRaises(ValueError): history_contract(p, 20)

    def test_cycle_requires_unit_and_phase(self):
        p = [replace(x, clock="cycle") for x in self.packets]
        with self.assertRaises(ValueError): history_contract(p, 20)
        p = [replace(x, physical_unit="specimen-fixture", phase="peak") for x in p]
        self.assertEqual(history_contract(p, 20)["clock"], "cycle")

    def test_phase_unit_and_clock_values_cannot_silently_change(self):
        for key,value in (("phase","trough"),("physical_unit","other"),("step",True)):
            p=list(self.packets);p[-1]=replace(p[-1],**{key:value})
            with self.assertRaises(ValueError): history_contract(p,20)

    def test_cross_group_rejected(self):
        p = list(self.packets); p[-1] = replace(p[-1], group="fixture-B")
        with self.assertRaises(ValueError): history_contract(p, 20)

    def test_reference_or_support_change_rejected(self):
        for key in ("reference", "support", "domain"):
            p = list(self.packets); p[-1] = replace(p[-1], **{key:"other"})
            with self.assertRaises(ValueError): history_contract(p, 20)

    def test_mask_cannot_be_phase_damage(self):
        p = [replace(x, role="visible-mask") for x in self.packets]
        with self.assertRaises(ValueError): history_contract(p, 20, "phase-damage")

    def test_out_of_order_duplicate_and_missing_current_rejected(self):
        for p in (self.packets[::-1], self.packets+[self.packets[-1]], self.packets[:-1]):
            with self.assertRaises(ValueError): history_contract(p, 20)

    def test_schema_and_finite(self):
        for q in ([0.]*7, [float("nan")]*8):
            with self.assertRaises(ValueError): canonical(q)

    def test_reversible_response_coordinates(self):
        for q in self.q: self.assertEqual(uncanonical(canonical(q)), q)

    def test_translation_invariant_relative_block_preserves_global(self):
        q = self.q[-1]; shifted=list(q)
        for i, delta in ((0,7.),(4,7.),(1,-3.),(5,-3.)): shifted[i]+=delta
        a,b=canonical(q),canonical(shifted)
        self.assertEqual(a[2:], b[2:]); self.assertNotEqual(a[:2], b[:2])

    def test_current_cannot_see_past_response(self):
        other=copy.deepcopy(self.q);other[0][4]+=17
        self.assertEqual(origin_features(self.base,self.q),origin_features(self.base,other))
        self.assertNotEqual(origin_features(self.base,self.q,True),origin_features(self.base,other,True))

    def test_history_shape_and_no_mutation(self):
        snapshot=copy.deepcopy(self.q)
        self.assertEqual(len(origin_features(self.base,self.q)),20)
        self.assertEqual(len(origin_features(self.base,self.q,True)),32)
        self.assertEqual(snapshot,self.q)

    def test_candidate_current_block_is_exact_raw_baseline(self):
        expected=self.base+self.q[-1]
        self.assertEqual(origin_features(self.base,self.q),expected)
        self.assertEqual(origin_features(self.base,self.q,True)[:20],expected)

    def test_function_invariance_and_pulled_penalty(self):
        beta=[1.,2.,3.,4.,5.,6.,7.,8.]; zbeta=canonical_coefficient(beta)
        self.assertEqual(dot(self.q[-1],beta),dot(canonical(self.q[-1]),zbeta))
        self.assertEqual(dot(beta,beta),pulled_penalty(zbeta))
        self.assertNotEqual(dot(beta,beta),dot(zbeta,zbeta))

    def test_plan_rejects_execution_and_count_change(self):
        p={"execution_enabled":False,"production_runner":None,
           "arms":{"C_RAW":20,"H_RAW":36,"C_REL":18,"H_REL":30,"H_INNOV":32,"H_DONOR":32},
           "budget":{"gpu_hours":0},"data":{"clock":"release_step"},
           "ridge_alphas":[.1,10.,1000.],"work":{"predictor_solves":912}}
        self.assertEqual(check_preparation_plan(p)["predictor_solves"],912)
        for key,value in (("execution_enabled",True),("production_runner","runner.py")):
            bad=copy.deepcopy(p);bad[key]=value
            with self.assertRaises(ValueError):check_preparation_plan(bad)


if __name__ == "__main__":
    unittest.main()
