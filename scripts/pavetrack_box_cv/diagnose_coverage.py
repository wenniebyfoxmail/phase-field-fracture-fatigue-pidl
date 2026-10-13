#!/usr/bin/env python3
"""Posthoc descriptive coverage transitions; never a primary or deployable selector."""
import argparse,json,importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('e005_diagnostic_helpers',Path(__file__).with_name('run.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def diagnose(e):
 by={}
 for field in ['baseline_rows','all_corrected_rows','rows']:
  groups={im:[] for im in e['targets']}
  for row in e[field]:groups[row['image_id']].append(row['box_xyxy'])
  by[field]={(im,i) for im,ts in e['targets'].items() for i,t in enumerate(ts) if any(m.box_iou(b,t)>=.5 for b in groups[im])}
 a=by['baseline_rows'];b=by['rows'];pre=by['all_corrected_rows']
 return {'label':'posthoc descriptive coverage-transition diagnostic; no new fit or operating-threshold selection; cannot rescue used primary','original_covered_targets':len(a),'corrected_pre_nms_covered_targets':len(pre),'corrected_post_nms_covered_targets':len(b),'retained_targets':len(a&b),'lost_targets':len(a-b),'newly_covered_targets':len(b-a),'union_covered_targets':len(a|b),'union_macro_oracle':m.oracle_coverage(e['baseline_rows']+e['rows'],e['targets'],e['image_locations'])['macro_location_recall'],'original_macro_oracle':e['baseline_oracle']['macro_location_recall'],'corrected_macro_oracle':e['oracle']['macro_location_recall'],'scientific_effect':'head replacement loses existing coverage; retaining originals would protect candidate coverage only, not prove fixed-budget detection gain'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--evaluation',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.write_text(json.dumps(diagnose(json.loads(a.evaluation.read_text())),indent=2)+'\n')
if __name__=='__main__':main()
