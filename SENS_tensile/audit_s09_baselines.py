"""No training: locked-data persistence/secant and target-scale inspection."""
import argparse,csv,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from s09_data import load_data,inventory,weighted_abs

def main():
 p=argparse.ArgumentParser();p.add_argument('--dataset',type=Path,required=True);p.add_argument('--reference-output',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 c=json.loads((a.reference_output/'receipt.json').read_text())['config'];cap=json.loads((a.reference_output/'data_capability.json').read_text())
 tr,mesh=load_data(a.dataset,c);area=mesh['areas'];area=area/area.sum();inv=inventory(tr,area,c)
 assert inv['p1_windows']==cap['p1_windows'];scale=cap['statistics']['increment_scale'][0]
 rows=[]
 for tid,o in inv['p1_windows']:
  prev,now,future=tr[tid]['raw'][o-1:o+2,:,0]
  inc=future-now;old=now-prev;linear=np.clip(now+old,now,1)
  growth=float(weighted_abs(inc,area));mask=inc>c['tau'];raw=inc/scale
  order=np.argsort(-inc);cum=np.cumsum(area[order]);mass=area[order]*inc[order]
  rows.append({'trajectory_id':tid,'origin_index':o,'origin_cycle':o+1,'growth':growth,'persistence_error':growth,'secant_error':float(weighted_abs(linear-future,area)),
   'secant_growth':float(weighted_abs(linear-now,area)),'active_area':float(area[mask].sum()),'positive_area':float(area[inc>0].sum()),
   'raw_target_max':float(raw.max()),'raw_target_p99':float(np.quantile(raw,.99)),
   'huber_linear_region_area':float(area[raw>1].sum()),'top_1pct_area_growth_share':float(mass[cum<=.01].sum()/growth),'top_3pct_area_growth_share':float(mass[cum<=.03].sum()/growth)})
 a.out.mkdir(parents=True,exist_ok=False)
 with (a.out/'windows.csv').open('w') as f:
  w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 summary={'stage':'exploratory offline audit, no model training','windows':len(rows),'damage_increment_scale':scale,'persistence_ratio':1.,
 'secant_ratio':sum(r['secant_error'] for r in rows)/sum(r['growth'] for r in rows),
 'secant_growth_ratio':sum(r['secant_growth'] for r in rows)/sum(r['growth'] for r in rows),
 'mean_active_area':float(np.mean([r['active_area'] for r in rows])),
 'raw_target_max':max(r['raw_target_max'] for r in rows),
 'mean_top_1pct_area_growth_share':float(np.mean([r['top_1pct_area_growth_share'] for r in rows])),
 'mean_top_3pct_area_growth_share':float(np.mean([r['top_3pct_area_growth_share'] for r in rows])),
 'scope':'16 seen windows only; baseline inputs use origin and previous state; no generalization or causal diagnosis'}
 (a.out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
