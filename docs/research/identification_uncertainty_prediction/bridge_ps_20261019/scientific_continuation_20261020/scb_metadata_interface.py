"""SCB proposed metadata interface only; no payload opens, labels, fit, scoring or producer.
Actual column names are not assumed: future source adapters must provide provenance.
"""
from collections import defaultdict
import math

TABLE_COLUMNS={
 'entities':('study_id','road_section_id','core_id','specimen_id','test_id','entity_source_asset_id'),
 'frame_load_join':('test_id','pair_id','left_frame_id','right_frame_id','left_asset_id','right_asset_id','cycle','phase_fraction','roi_id','registration_id','machine_source_asset_id','sync_source_asset_id'),
 'response_catalog':('test_id','cycle','phase_fraction','roi_id','feature_source_max_cycle','response_asset_id','geometry_asset_id','geometry_unit','feature_pipeline_id'),
 'reference_catalog':('reference_id','test_id','cycle','roi_id','unit','independent_of_dic','reference_source_asset_id','reference_resolution_mm'),
 'origins':('test_id','origin_cycle','history_cycles','phase_fraction','roi_id','load_plan_known_at_cycle','load_plan_until_cycle','load_plan_asset_id'),
 'splits':('fold_id','test_id','role'),
}

def _number(x,name):
 if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x):raise ValueError('finite numeric metadata required: '+name)
 return x

def audit_metadata(tables,horizons,phase_tolerance):
 """In-memory declared metadata, not length/DIC/image payloads. Successful result is not execution authority."""
 if not all(tables.get(n) for n in TABLE_COLUMNS):return {'status':'NOT_READY_MISSING_RECEIVED_METADATA','missing_tables':[n for n in TABLE_COLUMNS if not tables.get(n)],'counts_verified':None}
 if not horizons or len(set(horizons))!=len(horizons) or any(_number(h,'H')<=0 for h in horizons):raise ValueError('positive distinct physical-cycle horizons')
 if not 0<=_number(phase_tolerance,'phase tolerance')<.5:raise ValueError('phase tolerance must be declared')
 for name,cols in TABLE_COLUMNS.items():
  for row in tables[name]:
   if set(row)!=set(cols):raise ValueError('normalized metadata columns differ: '+name)
   if any(k in row for k in ('length_mm','future_length_mm','dic_values','target_values','final_life_fraction','N_over_Nf','final_crack_path')):raise ValueError('scientific/terminal payload is outside metadata-only interface')
 entities={}
 for e in tables['entities']:
  if not all(e[k] for k in ('study_id','core_id','specimen_id','test_id','entity_source_asset_id')):raise ValueError('entity identity/source missing')
  if e['test_id'] in entities:raise ValueError('duplicate test identity')
  entities[e['test_id']]=e
 if len({e['study_id'] for e in entities.values()})!=1:raise ValueError('do not silently merge SCB2020 and SCB2022')
 def key(row):
  if row['test_id'] not in entities:raise ValueError('unknown physical test')
  n=_number(row['cycle'],'absolute cycle')
  if n<0 or not row['roi_id']:raise ValueError('cycle/ROI')
  return row['test_id'],n,row['roi_id']
 def phase(row):
  p=_number(row['phase_fraction'],'load phase')
  if not 0<=p<1:raise ValueError('phase unit is fraction [0,1)')
  return p
 def close(p,q):return min(abs(p-q),1-abs(p-q))<=phase_tolerance
 frames={};pairs=set()
 for f in tables['frame_load_join']:
  k=key(f);phase(f)
  if k in frames or (f['test_id'],f['pair_id']) in pairs:raise ValueError('duplicate phase-selected frame/pair')
  if not all(f[n] for n in ('left_asset_id','right_asset_id','machine_source_asset_id','sync_source_asset_id','registration_id')):raise ValueError('explicit stereo/load/sync/registration sources required')
  pairs.add((f['test_id'],f['pair_id']));frames[k]=f
 responses={}
 for r in tables['response_catalog']:
  k=key(r)
  if k in responses or k not in frames or not close(phase(r),phase(frames[k])):raise ValueError('response frame/phase join')
  if r['geometry_unit']!='mm' or not r['geometry_asset_id'] or not r['feature_pipeline_id']:raise ValueError('origin geometry source/unit/pipeline missing')
  if _number(r['feature_source_max_cycle'],'source max cycle')>k[1] or not r['response_asset_id']:raise ValueError('response uses future information or lacks source')
  responses[k]=r
 refs={}
 for r in tables['reference_catalog']:
  k=key(r)
  if k in refs or r['unit']!='mm' or r['independent_of_dic'] is not True or not r['reference_source_asset_id']:raise ValueError('independent physical reference/provenance')
  resolution=r['reference_resolution_mm']
  if resolution is not None and _number(resolution,'reference resolution')<=0:raise ValueError('reference resolution')
  refs[k]=r
 missing_resolution=any(r['reference_resolution_mm'] is None for r in refs.values())
 origins=set();forecast_pairs=0
 for o in tables['origins']:
  tid=o['test_id'];n=_number(o['origin_cycle'],'origin');roi=o['roi_id'];history=o['history_cycles'];p=phase(o)
  if (tid,n,roi) in origins:raise ValueError('duplicate origin')
  if tid not in entities or len(history)!=3 or history!=sorted(set(history)) or history[-1]!=n:raise ValueError('three chronological origin-only observations')
  for v in history:
   k=tid,_number(v,'history'),roi
   if v>n or k not in responses or not close(p,phase(responses[k])):raise ValueError('history availability/phase')
  if _number(o['load_plan_known_at_cycle'],'plan availability')>n or not o['load_plan_asset_id']:raise ValueError('future realized load is not an origin-known plan')
  if _number(o['load_plan_until_cycle'],'plan support')<n+max(horizons):raise ValueError('future driving condition unsupported')
  for h in horizons:
   if (tid,n+h,roi) not in refs:raise ValueError('future independent reference join missing')
   forecast_pairs+=1
  origins.add((tid,n,roi))
 roles=defaultdict(lambda:defaultdict(set));fold_tests=defaultdict(set)
 for s in tables['splits']:
  if s['test_id'] not in entities or s['role'] not in ('development','evaluation'):raise ValueError('split identity/role')
  if s['test_id'] in fold_tests[s['fold_id']]:raise ValueError('duplicate split row')
  fold_tests[s['fold_id']].add(s['test_id']);roles[s['fold_id']][s['role']].add(entities[s['test_id']]['core_id'])
 for fold,rr in roles.items():
  if fold_tests[fold]!=set(entities) or not rr['evaluation'] or not rr['development'] or rr['evaluation']&rr['development']:raise ValueError('whole-core split coverage/leakage')
  if len(rr['development'])<2:raise ValueError('matched other-training-core donor unsupported')
 return {'status':'METADATA_CONSISTENT_NOT_EXECUTION_AUTHORITY','counts_verified':{'cores':len({e['core_id'] for e in entities.values()}),'tests':len(entities),'phase_selected_frame_pairs':len(frames),'origins':len(origins),'origin_horizon_pairs':forecast_pairs,'folds':len(roles)},'reference_effect_tolerance_ready':not missing_resolution,'full_R_Q_identification_required_for_state_contrast':False,'measurement_repeat_status':'not asserted by this interface','scientific_values_opened':False}

def cost_counts(stats):
 """Planning counts for the one finite family below; no seconds inferred from other experiments."""
 if any(stats.get(k) is None for k in ('cores','horizon_count','origin_horizon_pairs','source_bytes','dic_processing_seconds_per_pair','reference_hours')):
  return {'status':'NOT_ESTIMABLE_FROM_RECEIVED_DATA','total_wall_seconds':None,'total_storage_bytes':None,'total_annotation_hours':None,'reason':'No received physical manifest/synchronization/reference scale; source-document bytes are not image-data scale','scientific_run_authorized':False}
 k=stats['cores'];h=stats['horizon_count'];n=stats['origin_horizon_pairs']
 return {'status':'COUNT_ONLY_NOT_RUNTIME_BUDGET','final_mean_fits':4*k*h,'shared_input_residualizer_fits':k*h,'current_only_crossfit_scale_fits':k*(k-1)*h,'total_closed_form_fits':k*h*(k+4),'distribution_forecasts_and_CRPS_rows':6*n,'paired_primary_rows':n,'total_wall_seconds':None,'total_storage_bytes':None,'total_annotation_hours':stats['reference_hours'],'scientific_run_authorized':False}
