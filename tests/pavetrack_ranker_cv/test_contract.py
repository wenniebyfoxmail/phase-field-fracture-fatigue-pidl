import importlib.util,sys,unittest,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('ranker_run',ROOT/'scripts/pavetrack_ranker_cv/run.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ContractTests(unittest.TestCase):
 def setUp(self):self.cfg=json.loads((ROOT/'docs/research/S01/S01-E003/run_config.json').read_text())
 def test_negative_padding_never_crosses_crack(self):
  # Disjoint proposal with padding touching a crack must be ignored.
  rows=[{'box_xyxy':[0,0,10,10],'old_score':.9}]
  choices=m.mining_choice(rows,[[10.5,0,20,10]],100,100,self.cfg)
  self.assertFalse(any(label==0 for _,label,_ in choices))
 def test_hard_negatives_use_old_rank_order_and_caps(self):
  rows=[{'box_xyxy':[i*3,50,i*3+2,52],'old_score':i/30} for i in range(30)]
  choices=m.mining_choice(rows,[],100,100,self.cfg)
  self.assertEqual(len(choices),20);self.assertGreater(choices[0][0][0],choices[-1][0][0])
 def test_ambiguous_proposals_ignored(self):
  choices=m.mining_choice([{'box_xyxy':[0,0,10,10],'old_score':.9}],[[5,0,15,10]],100,100,self.cfg)
  self.assertEqual(len(choices),1);self.assertEqual(choices[0][2],'ground_truth')
 def test_same_candidates_different_ranking_changes_recall(self):
  targets={'a':[[0,0,10,10]],'b':[]};loc={'a':'1','b':'2'}
  rows=[{'image_id':'a','reid':'1','box_xyxy':[0,0,10,10],'old':.1,'new':.9},{'image_id':'b','reid':'2','box_xyxy':[0,0,5,5],'old':.9,'new':.1},{'image_id':'b','reid':'2','box_xyxy':[10,10,15,15],'old':.8,'new':.2},{'image_id':'b','reid':'2','box_xyxy':[20,20,25,25],'old':.7,'new':.3}]
  self.assertEqual(m.metrics(rows,targets,loc,'old')['macro_location_recall'],0)
  self.assertEqual(m.metrics(rows,targets,loc,'new')['macro_location_recall'],1)
 def test_lock_consumed_holdouts_excluded(self):
  lock=json.loads((ROOT/'docs/research/S01/S01-E003/data_lock.json').read_text());m.validate_data_lock(lock)
  self.assertEqual(lock['confirmatory_test_locations'],['1174','1729','2246','2260','2485'])
  self.assertTrue({'75','220','577','956','1139'}.issubset(lock['consumed_or_excluded_locations']))
 def test_finite_rejects_nan(self):
  with self.assertRaises(ValueError):m.finite(float('nan'))
if __name__=='__main__':unittest.main()
