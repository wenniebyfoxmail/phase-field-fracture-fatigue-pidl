from pathlib import Path
from collections import defaultdict
import csv,json
import numpy as np
root=Path(__file__).parent;out=root/'retrieved/outputs'
receipt=json.loads((out/'receipt.json').read_text());assert receipt['status']=='COMPLETE',receipt
rows=list(csv.DictReader((out/'per_case_scores.csv').open()));cells=defaultdict(list)
for r in rows:
 cells[(r['arm'],r['group'],int(r['horizon_stages']))].append(float(r['balanced_nmae']))
means={k:float(np.mean(x)) for k,x in cells.items()};arms=sorted({k[0] for k in cells});groups=sorted({k[1] for k in cells});hs=sorted({k[2] for k in cells})
assert len(groups)==19 and hs==[10,40]
rank={arm:float(np.mean([means[(arm,g,h)] for g in groups for h in hs])) for arm in arms if arm!='oracle_output_projection'}
comparisons={}
for alt,base in [('compact','scalar'),('compact','persistence'),('compact','secant'),('rich','scalar'),('rich','compact'),('rich_set','rich'),('rich_set','rich_fixed'),('rich','secant'),('rich_set','secant')]:
 delta=[float(np.mean([means[(alt,g,h)]-means[(base,g,h)] for h in hs])) for g in groups]
 comparisons[alt+' minus '+base]={'paired_mean_difference':float(np.mean(delta)),'groups_better':sum(x<0 for x in delta),'groups_worse':sum(x>0 for x in delta),'n_release_groups':len(groups),'range':[min(delta),max(delta)]}
by_h={str(h):{a:float(np.mean([means[(a,g,h)] for g in groups])) for a in arms} for h in hs}
by_position={}
for g in groups:
 origins=sorted({int(r['origin_stage']) for r in rows if r['group']==g})
 pos={n:min(2,3*i//len(origins)) for i,n in enumerate(origins)}
 for arm in arms:
  for phase in range(3):
   vals=[float(r['balanced_nmae']) for r in rows if r['group']==g and r['arm']==arm and pos[int(r['origin_stage'])]==phase]
   if vals:by_position.setdefault(arm,{}).setdefault(str(phase),[]).append(float(np.mean(vals)))
by_position={a:{phase:float(np.mean(x)) for phase,x in phases.items()} for a,phases in by_position.items()}
analysis={'by_early_mid_late_release_position_not_lifetime':by_position,'primary_equal_group_horizon_scores':rank,'paired_release_group_comparisons':comparisons,'by_horizon_stages':by_h,'rows':len(rows),'scope':'Exploratory release-observable prediction; no independent physical UQ, crack truth or unseen-asset claim.'}
(root/'analysis.json').write_text(json.dumps(analysis,indent=2));print(json.dumps(analysis,indent=2))
