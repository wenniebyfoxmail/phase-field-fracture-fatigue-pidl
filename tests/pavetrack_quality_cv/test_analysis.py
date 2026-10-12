import importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/pavetrack_quality_cv'))
spec=importlib.util.spec_from_file_location('quality_analysis',ROOT/'scripts/pavetrack_quality_cv/analyze.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class OutcomeTests(unittest.TestCase):
 def test_zero_targets_is_inconclusive(self):
  rows=[{'image_id':'a','reid':'1','box_xyxy':[0,0,10,10],'old_score':.1,'score':.2}];e={'rows':rows,'targets':{'a':[]},'image_locations':{'a':'1'},'delta':None}
  for field,name in [('old_score','baseline'),('score','candidate')]:e[name]=a.metrics(rows,e['targets'],e['image_locations'],field)
  oracle=a.oracle_coverage(rows,e['targets'],e['image_locations']);n=a.numeric(e,{'seed':20261012},oracle)
  self.assertIsNone(n[4]);self.assertIsNone(n[5]);self.assertIsNone(n[8]);self.assertIsNone(n[9]);a.cases(e)
 def test_tie_group_rejected_atomically(self):
  rows=[{'image_id':'a','reid':'1','box_xyxy':[x,0,x+5,5],'score':.5,'old_score':.5} for x in (0,10)];e={'rows':rows,'targets':{'a':[]},'image_locations':{'a':'1'}}
  m=a.metrics(rows,e['targets'],e['image_locations'],'score');self.assertEqual(m['detections_used'],0);self.assertIsNone(m['global_score_threshold']);self.assertEqual(a.exact_outcomes(e,'score',m),([],{}))
 def test_zero_oracle_does_not_divide(self):
  rows=[];targets={'a':[[0,0,5,5]]};loc={'a':'1'};e={'rows':rows,'targets':targets,'image_locations':loc,'delta':0.}
  for field,name in [('old_score','baseline'),('score','candidate')]:e[name]=a.metrics(rows,targets,loc,field)
  n=a.numeric(e,{'seed':20261012},a.oracle_coverage(rows,targets,loc));self.assertEqual(n[5],0.);self.assertIsNone(n[8]);self.assertIsNone(n[9])
if __name__=='__main__':unittest.main()
