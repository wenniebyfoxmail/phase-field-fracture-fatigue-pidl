#!/usr/bin/env python3
"""Read-only view of all four predeclared training qualification policies."""
import argparse,json,importlib.util
from pathlib import Path
import matplotlib.pyplot as plt
spec=importlib.util.spec_from_file_location('paired_runner',Path(__file__).with_name('run.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--config',type=Path,required=True);a=p.parse_args();cfg=m.read(a.config);d=m.read(a.run/'qualification_decision.json');a.output.mkdir(parents=True,exist_ok=True)
 if d['protocol']!=cfg['protocol'] or d['config_sha256']!=m.sha256_file(a.config):raise ValueError('analysis identity')
 summary={'run_id':a.run.name,'status':d['status'],'selected_harm_limit':d.get('selected_harm_limit'),'scope':'four held train locations; conditional shared encoder;not fresh/development','policies':[]}
 fig,ax=plt.subplots(1,3,figsize=(15,4.5))
 if (a.run/'qualification_evaluation.json').exists():
  e=m.read(a.run/'qualification_evaluation.json')
  if e['protocol']!=cfg['protocol'] or m.sha256_file(a.run/'qualification_evaluation.json')!=d['qualification_evaluation_sha256']:raise ValueError('qualification receipt')
  policies=e['policies'];limits=[str(x['harm_limit']) for x in policies]
  for row in policies:summary['policies'].append({k:row[k] for k in ['harm_limit','delta','retention','protected_exposures','harm_count','harm_rate','qualified','new_detected_targets','lost_old_targets','choice']})
  ax[0].bar(limits,[x['delta'] or 0 for x in policies]);ax[0].axhline(0,color='black',ls='--');ax[0].set_ylabel('Macro recall change at1FP/image')
  ax[1].bar(limits,[x['retention'] if x['retention'] is not None else float('nan') for x in policies]);ax[1].axhline(.95,color='black',ls='--');ax[1].set_ylim(0,1.03);ax[1].set_ylabel('Old target retention')
  ax[2].bar(limits,[x['protected_exposures'] for x in policies]);ax[2].axhline(cfg['qualification_minimum_protected_exposures'],color='black',ls='--');ax[2].set_ylabel('Accepted original-valid pair exposures')
  for item in ax:item.set_xlabel('Fixed harm-score limit');item.grid(axis='y',alpha=.2)
 else:
  for item in ax:item.axis('off')
  ax[1].text(.5,.5,'Paired classes not identifiable\nNo head fitted or development comparison',ha='center',va='center',transform=ax[1].transAxes)
 fig.suptitle(a.run.name+' — four train qualification locations\n'+d['status']+'; harm scores are uncalibrated, not a risk guarantee');fig.tight_layout();fig.savefig(a.output/'F00_training_qualification.png',dpi=180);plt.close(fig);(a.output/'qualification_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
