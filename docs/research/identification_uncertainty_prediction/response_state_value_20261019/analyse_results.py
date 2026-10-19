"""Descriptive aggregation of saved complete scores; no fitting."""
from pathlib import Path
from collections import defaultdict
import csv,json
import numpy as np
import sys
r=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).parent;o=r/'retrieved/outputs'
assert json.loads((o/'receipt.json').read_text())['status']=='COMPLETE'
rows=list(csv.DictReader((o/'per_case_scores.csv').open()));assert len(rows)==27456
arms=sorted({x['arm'] for x in rows});groups=sorted({x['group'] for x in rows});hs=[10,40];assert len(groups)==19
cells=defaultdict(list)
for x in rows:
 cells[(x['arm'],x['group'],int(x['horizon_stages']))].append(x)
metrics=['balanced_nmae','full_nmae','local_nmae'];means={k:{m:float(np.mean([float(x[m]) for x in v])) for m in metrics} for k,v in cells.items()}
primary={a:float(np.mean([means[(a,g,h)]['balanced_nmae'] for g in groups for h in hs])) for a in arms if a!='oracle_output_projection'}
pairs=[('centered_history','current_response'),('centered_history','persistence'),('centered_history','compact_noclock'),('history_response','span_progress'),('current_response','span_progress'),('history_response','current_response'),('global_history','span_progress'),('centered_history','span_progress'),('history_response','global_history'),('history_response','centered_history'),('rich_history','history_response'),('span_progress','span_only'),('history_response','compact_noclock'),('rich_history','rich_noclock'),('history_response','persistence'),('current_response','persistence')]
comparisons={}
for a,b in pairs:
 d={g:float(np.mean([means[(a,g,h)]['balanced_nmae']-means[(b,g,h)]['balanced_nmae'] for h in hs])) for g in groups}
 comparisons[a+' minus '+b]={'mean_delta':float(np.mean(list(d.values()))),'median_group_delta':float(np.median(list(d.values()))),'group_delta_range':[min(d.values()),max(d.values())],'relative_aggregate_error_reduction_pct':100*(1-primary[a]/primary[b]),'groups_better':sum(v<0 for v in d.values()),'groups_worse':sum(v>0 for v in d.values()),'paired_group_delta':d}
byh={str(h):{a:float(np.mean([means[(a,g,h)]['balanced_nmae'] for g in groups])) for a in arms} for h in hs}
full_local={a:{m:float(np.mean([means[(a,g,h)][m] for g in groups for h in hs])) for m in metrics} for a in arms}
phase=defaultdict(list)
for g in groups:
 ns=sorted({int(x['origin_stage']) for x in rows if x['group']==g});p={n:min(2,3*i//len(ns)) for i,n in enumerate(ns)}
 for a in arms:
  for k in range(3):
   vals=[float(x['balanced_nmae']) for x in rows if x['group']==g and x['arm']==a and p[int(x['origin_stage'])]==k]
   phase[(a,k)].append(float(np.mean(vals)))
byphase={a:{str(k):float(np.mean(phase[(a,k)])) for k in range(3)} for a in arms}
out={'primary':primary,'contrasts':comparisons,'by_horizon':byh,'full_local':full_local,'by_release_origin_third_not_physical_lifetime':byphase,'rows':len(rows),'groups':groups,'horizons':hs,'scope':'19 development-exposed released groups; common native current-field anchor; published increment prediction only'}
(r/'analysis.json').write_text(json.dumps(out,indent=2))
print(json.dumps({'primary':primary,'contrasts':{k:{kk:vv for kk,vv in v.items() if kk!='paired_group_delta'} for k,v in comparisons.items()},'by_horizon':byh},indent=2))
