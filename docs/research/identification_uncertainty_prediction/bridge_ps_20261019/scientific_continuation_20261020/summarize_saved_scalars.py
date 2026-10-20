"""Aggregate stored scalar metrics only. No new native scoring, NPZ/PT, fit, torch or SSH."""
from pathlib import Path
import json,csv,collections,statistics,hashlib
ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
OLD=ROOT/'local_archive/experiments/IU-BRIDGE-PS-20261019-R003'
FIXED=ROOT/'local_archive/experiments/IU-OUTPUT-CALIBRATION-C27A25-20261020-R002'
PLAN=ROOT/'.codex/worktrees/cross-track-predictive-state-20261019/docs/research/bridges/BRIDGE-PS-20261019/plan.json'
OUT=ROOT/'local_archive/analyses/BRIDGE-PS-scientific-continuation-20261020'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 if OUT.exists():raise FileExistsError('preserve previous analysis')
 OUT.mkdir(parents=True)
 plan=read(PLAN);actual=read(OLD/'retrieved/code/config.producer.json');progress=read(OLD/'retrieved/outputs/progress.json');verified=read(OLD/'independent_saved_output_checks.json')
 assert sha(OLD/'retrieved/code/frozen_cohort.json')==plan['data']['manifest_sha256']
 for k,j in [('history_stage_offsets','history_offsets'),('horizon_stage_steps','horizons')]:assert actual[k]==plan['data'][j]
 assert actual['ridge_alphas']==plan['ridge_alphas'] and actual['arms']==list(plan['arms'])
 assert progress=={'completed_group_horizons':38,'total':38,'predictor_fits':912,'input_fits':76}
 source=OLD/'retrieved/outputs/per_case_scores.csv';grouped=collections.defaultdict(list)
 with source.open() as f:
  for row in csv.DictReader(f):grouped[row['group'],int(row['horizon_stages']),row['arm']].append(row)
 cells=[]
 for (g,h) in sorted({(g,h) for g,h,a in grouped}):
  item={'group':g,'H':h}
  for arm in ('P','S','C_RAW','C_REL','H_RAW','H_RAW_PULLBACK','H_REL','H_INNOV','H_DONOR','B_STAR'):
   rr=grouped[g,h,arm];assert rr
   keys=['balanced_nmae']
   if arm in ('B_STAR','C_RAW','H_INNOV','H_DONOR'):
    keys+=['mean_increment_error_0','mean_increment_error_1','centered_increment_nmae_0','centered_increment_nmae_1','pred_mean_increment_0','ref_mean_increment_0','pred_mean_increment_1','ref_mean_increment_1','l1_mass_ratio_0','l1_mass_ratio_1']
   for k in keys:
    vs=[float(r[k]) for r in rr if r[k]!=''];item[arm+'__'+k]=statistics.mean(vs) if vs else None
   if arm in ('C_RAW','H_INNOV'):item[arm+'__alpha']=sorted(set(float(r['alpha']) for r in rr))
  item['Bstar_minus_Hinnov']=item['B_STAR__balanced_nmae']-item['H_INNOV__balanced_nmae'];item['Donor_minus_Hinnov']=item['H_DONOR__balanced_nmae']-item['H_INNOV__balanced_nmae'];cells.append(item)
 assert len(cells)==38
 assert abs(statistics.mean(x['Bstar_minus_Hinnov'] for x in cells)-verified['primary_delta'])<1e-12
 fixed=read(FIXED/'analysis/checkpoint_verification_and_C30.json')
 summary={'route':'REUSE_ALREADY_COMPLETED_BRIDGE_PS_EXPLORATORY_RESULTS_NO_NEW_RUN','approved_design_covered':True,'cohort_sha256':plan['data']['manifest_sha256'],'completed_work':progress,'scientific_status':'EXPLORATORY_ONLY_ORIGINAL_STOP_CONTRACT_BREACH_PRESERVED','primary_delta':verified['primary_delta'],'losses':verified['overall'],'per_H':verified['per_horizon'],'leave_one_group_out_range':verified['leave_one_group_out_range'],'donor_minus_innov':verified['donor_minus_innov'],'pullback_max_saved_score_difference':verified['max_saved_pullback_score_difference'],'C30_six_cells':[c for c in cells if c['group'].startswith('C_30')],'all_group_H_cells':cells,'fixed_alpha_C30':fixed['C30_cells'],'fixed_alpha_complete_groups':15,'fixed_alpha_full19_available':False,'saved_field_claim_limits':'G/S are separate saved increment descriptors, not additive native error shares; cross-alpha/protocol comparison is descriptive, not an isolated alpha ablation','actions_this_analysis':{'stored_scalar_aggregation':True,'native_scoring':False,'fit_or_forward':False,'npz_or_pt_read':False,'torch':False,'ssh':False,'new_run_id':False,'new_four_group_permission':False}}
 sources=[PLAN,OLD/'retrieved/code/config.producer.json',OLD/'retrieved/code/frozen_cohort.json',source,OLD/'independent_saved_output_checks.json',OLD/'warning_contract_audit.json',FIXED/'analysis/checkpoint_verification_and_C30.json',FIXED/'analysis/C30_inner_outer_preference.csv']
 summary['sources']={str(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in sources}
 (OUT/'saved_scalar_synthesis.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
 with (OUT/'all19_group_H_existing_metrics.csv').open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(cells[0]));w.writeheader();w.writerows(cells)
 print(json.dumps({'route':summary['route'],'primary_delta':summary['primary_delta'],'H10':verified['per_horizon']['10']['B_STAR']-verified['per_horizon']['10']['H_INNOV'],'H40':verified['per_horizon']['40']['B_STAR']-verified['per_horizon']['40']['H_INNOV'],'C30_H10_H40_effects':[(c['group'],c['H'],c['Bstar_minus_Hinnov']) for c in summary['C30_six_cells']],'out':str(OUT)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
