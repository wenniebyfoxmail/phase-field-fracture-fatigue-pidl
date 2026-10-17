"""Conservative pre-first-recorded-intervention coverage; no prediction scores."""
import csv,json,re,subprocess,os,socket,time,argparse
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
BASE=ROOT/'local_archive/experiments/S02-E006/runs/S02-E006-R005/audit'
TL=ROOT/'local_archive/open_data/history_candidate_selection_20261017/raw/timelines'
BOOKKEEPING={'section after','section ends','secton ends','section constructed','section before'}

def read_csv(p):
 with p.open(newline='') as f:return list(csv.DictReader(f))

def check(ok,msg):
 if not ok:raise ValueError(msg)

def select(rs):
 groups={}
 for r in rs:
  if r['lane']!='Driving' or int(r['four_spring_slot_origins_upper_bound'])<=0 or r['old_cell22_excluded_from_new_shortlist']!='False':continue
  cell=int(r['cell_code']);rank=lambda x:(-int(x['four_spring_slot_origins_upper_bound']),x['section_id'])
  if cell not in groups or rank(r)<rank(groups[cell]):groups[cell]=r
 return sorted(groups.values(),key=lambda r:(-int(r['four_spring_slot_origins_upper_bound']),r['section_id']))

def first_cut(events,start):
 dates=[];undated=[]
 for e in events:
  if e.get('EVENT_TYPE')!='Construction Event':continue
  title=' '.join((e.get('EVENT_TITLE') or '').lower().split())
  if title in BOOKKEEPING:continue
  text=e.get('display_date')
  if not text:undated.append(e.get('EVENT_TITLE'));continue
  try:d=datetime.strptime(text,'%m/%d/%Y').date()
  except ValueError:undated.append(e.get('EVENT_TITLE'));continue
  if d>start:dates.append((d,e.get('EVENT_TITLE')))
 return min(dates,key=lambda x:x[0]) if dates else None,undated

def screen(sections,windows,reader):
 table=[];retained=[]
 for r in select(sections):
  sid=r['section_id'];j=reader(sid)
  start=datetime.fromisoformat(r['section_start']).date();end=datetime.fromisoformat(r['section_end']).date()
  events=j.get('timelineData',[])
  check(all(e.get('LDW_SECTION_ID') in [sid,None] for e in events),'wrong timeline section')
  cutoff,undated=first_cut(events,start)
  possible=[q for q in windows if q['section_id']==sid]
  kept=[]
  for q in possible:
   target=datetime.fromisoformat(q['target_slot_cutoff']).date()
   if target<=end and (cutoff is None or target<cutoff[0]) and not undated and j.get('hasEventsData') and len(events)<100:kept.append(q)
  retained.extend(kept)
  table.append({'cell_code':int(r['cell_code']),'section_id':sid,'raw_four_spring_windows':len(possible),
   'first_recorded_action_date':cutoff[0].isoformat() if cutoff else None,'first_recorded_action':cutoff[1] if cutoff else None,
   'windows_before_first_recorded_action':len(kept),'undated_unknown_construction_events':len(undated),
   'events_returned':len(events),'timeline_available':bool(j.get('hasEventsData')),
   'complete_intervention_clearance':False,'physical_nonoverlap_confirmed':False})
 return table,retained

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--authorization',type=Path,required=True);args=ap.parse_args()
 head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();auth=json.loads(args.authorization.read_text())
 check(auth['code_commit']==head and auth['review']=='CODE_REVIEW_PASS' and auth['training'] is False,'review required')
 check(not subprocess.check_output(['git','status','--porcelain'],text=True).strip(),'clean snapshot required')
 out=ROOT/'local_archive/experiments/S02-E006/runs/S02-E006-R006/timeline_screen';check(not out.exists(),'fresh output required')
 started=datetime.now(timezone.utc).isoformat();t=time.monotonic()
 selected=select(read_csv(BASE/'mnroad_sections.csv'))
 paths=[BASE/'mnroad_sections.csv',BASE/'mnroad_spring_slot_inventory.csv']+[TL/(r['section_id']+'.json') for r in selected]
 raw={p:p.read_bytes() for p in paths}
 table,retained=screen(read_csv(paths[0]),read_csv(paths[1]),lambda sid:json.loads((TL/(sid+'.json')).read_text()))
 out.mkdir(parents=True)
 for name,rows in [('driving_cell_screen.csv',table),('retained_windows.csv',retained)]:
  if not rows:continue
  with (out/name).open('w',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 shortlist=sorted([r for r in table if r['windows_before_first_recorded_action']>0],key=lambda r:(-r['windows_before_first_recorded_action'],r['section_id']))[:6]
 summary={'run_id':'S02-E006-R006','screen':'coverage before FIRST recorded construction action; no restarts or outcome filtering',
  'selected_cell_codes':len(table),'raw_windows':sum(r['raw_four_spring_windows'] for r in table),
  'retained_cells_not_certified_independent':sum(r['windows_before_first_recorded_action']>0 for r in table),
  'retained_windows_upper_bound':len(retained),'next_qualification_shortlist':shortlist,
  'complete_maintenance_qualified_cells':0,'training':False,'fitting':False,'model_forward':False}
 (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 check(all(p.read_bytes()==b for p,b in raw.items()),'inputs changed')
 (out/'execution_receipt.json').write_text(json.dumps({'run_id':'S02-E006-R006','code_commit':head,'hostname':socket.gethostname(),'pid':os.getpid(),
  'start_utc':started,'elapsed_seconds':time.monotonic()-t,'input_files_checked':len(raw),'input_bytes_unchanged':True,'execution_status':'succeeded','retrieval':'local verified','dirty_status':'clean','training':False,'fitting':False,'model_forward':False,'command':__import__('sys').argv},indent=2)+'\n')
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
