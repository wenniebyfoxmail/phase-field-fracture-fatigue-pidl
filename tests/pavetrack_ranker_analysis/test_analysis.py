import importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'scripts/pavetrack_ranker_cv'))
spec=importlib.util.spec_from_file_location('analysis',ROOT/'scripts/pavetrack_ranker_cv/analyze.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
class AnalysisTests(unittest.TestCase):
 def test_duplicate_is_metric_false_positive(self):
  rows=[{'image_id':'x','reid':'1','box_xyxy':[0,0,10,10],'score':.9,'old_score':.9},{'image_id':'x','reid':'1','box_xyxy':[0,0,9.5,10],'score':.8,'old_score':.8}]
  e={'rows':rows,'targets':{'x':[[0,0,10,10]]},'image_locations':{'x':'1'}}
  e['baseline']=a.metrics(rows,e['targets'],e['image_locations'],'old_score');e['candidate']=a.metrics(rows,e['targets'],e['image_locations'],'score')
  cases=a.cases(e);self.assertEqual(len(cases),1);self.assertEqual(cases[0]['kind'],'metric_false_positive')
 def test_partial_image_gain_is_recovered_target(self):
  rows=[{'image_id':'x','reid':'1','box_xyxy':[0,0,10,10],'score':.9,'old_score':.9},{'image_id':'x','reid':'1','box_xyxy':[20,0,30,10],'score':.8,'old_score':.1},{'image_id':'x','reid':'1','box_xyxy':[50,0,60,10],'score':.4,'old_score':.8},{'image_id':'x','reid':'1','box_xyxy':[70,0,80,10],'score':.3,'old_score':.7}]
  e={'rows':rows,'targets':{'x':[[0,0,10,10],[20,0,30,10]]},'image_locations':{'x':'1'}}
  for field,name in [('old_score','baseline'),('score','candidate')]:e[name]=a.metrics(rows,e['targets'],e['image_locations'],field)
  cases=a.cases(e);self.assertTrue(any(c['kind']=='recovered_target' and c['row']['box_xyxy']==[20,0,30,10] for c in cases))
if __name__=='__main__':unittest.main()
