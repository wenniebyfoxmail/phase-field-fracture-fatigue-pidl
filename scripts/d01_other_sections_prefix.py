"""Frozen-equation robustness replay on existing section observations only.

Separate prepare/run phases ensure eligibility is registered without errors.
"""
import argparse,csv,hashlib,json,math,socket,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from d01_section3_prediction import forecast,write_csv
from d01_prefix_slope_initialization import prefix_slope_forecast,sanity

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
BASE=ROOT/'local_archive/experiments/S03-E016-D01'
SOURCE=BASE/'fourteen_stage_extension_20261017/analysis/state_space_inputs.json'
OUT=BASE/'other_sections_prefix_20261018'
METHODS=['original_state_space','load_secant','prefix_slope_state_space']
LABELS=['Original SS','Load extrapolation','Prefix-slope SS']
COLORS=['#777777','#d68a15','#0072b2']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2))

def prepare():
    OUT.mkdir(exist_ok=False)
    data=json.loads(SOURCE.read_text());inventory=[];hashes={str(SOURCE):sha(SOURCE)}
    # Only metadata and exported common-support pixels are used for eligibility.
    for seq in data['sequences']:
        b=seq['beam_id'];obs=seq['observations'];support=np.asarray(Image.open(seq['common_support_file']))>0
        hashes[seq['common_support_file']]=sha(seq['common_support_file'])
        for j,sec in enumerate(seq['paired_visible_reference_transects']):
            cut=next(c for c in seq['fixed_transect_geometry'] if c['id']==sec)
            pts=np.rint(np.array(cut['center'])+np.arange(-60,60.001,.25)[:,None]*np.array(cut['normal'])).astype(int)
            inside=((pts[:,0]>=0)&(pts[:,0]<support.shape[1])&(pts[:,1]>=0)&(pts[:,1]<support.shape[0]))
            supported=bool(inside.all() and support[pts[:,1],pts[:,0]].all())
            values=[o['model_widths_strip_px'][j] for o in obs]
            statuses=[o['width_observation_status'][j] for o in obs]
            allowed={'existing_human_reference_boundary_bias_uncorrected','model_only_boundary_bias_uncorrected'}
            reasons=[]
            if not cut['origin_valid']:reasons.append('origin_invalid')
            if not supported:reasons.append('full_fixed_strip_not_in_saved_common_support')
            if any(v is None or not math.isfinite(v) or v<=0 for v in values):reasons.append('missing_invalid_width')
            if any(s not in allowed for s in statuses):reasons.append('existing_status_not_eligible')
            loads=[o['metadata']['nominal_stage_load_kN'] for o in obs]
            if len(obs)<3 or not np.all(np.diff(loads)>0):reasons.append('insufficient_prefix_or_load_axis')
            inventory.append({'beam':b,'section':sec,'role':'existing_section3_cache' if sec==3 else 'additional_section','eligible':not reasons,'exclusion_reasons':reasons,'n_observations':len(obs),'n_primary':len(obs)-2,'full_strip_common_support':supported,'origin_valid':cut['origin_valid'],'statuses':statuses,'uncertainty_flags':sorted(set(f for o in obs for f in o['uncertainty_flags'])),'images':[o['image'] for o in obs]})
    prior=json.loads((BASE/'section3_prefix_slope_init_20261018/receipt.json').read_text())
    hashes.update(prior['protected_files'])
    for name in ['predictions_and_errors.csv','summary.json','frozen_contract.json']:
        p=BASE/'section3_prefix_slope_init_20261018'/name;hashes[str(p)]=sha(p)
    contract={'stage':'exploratory robustness on previously exposed archive','question':'Does fixed prefix initialization retain value on every other existing eligible section?','registered_before_prediction':True,'created_utc':datetime.now(timezone.utc).isoformat(),'noise':{'measurement_sigma_strip_px':1.,'acceleration_sigma':.05},'methods':METHODS,'eligibility':'all exported paired cuts; origin valid, full saved fixed strip inside all-stage support, positive finite saved widths, allowed existing statuses, >=3 increasing-load observations; no errors used','primary':'additional sections only: MAE within section over >=2-observation-prefix targets; equal-section mean within beam; equal-beam mean across three beams','secondary':'all eligible sections including cached section3, same nested aggregation','grouping':'three physical beams only; sections and adjacent transitions are correlated, no independent-section inference','warmup':'first transition each section separate; original initialization reused','information':'one-step available prefix plus specified next nominal load; no future width initialization','support_limit':'support and paired endpoint selection are retrospective archive choices, not prospectively available support','comparator_cache':'reuse all existing section3 forecasts; no matching other-section caches exist, compute fixed published equations without fitting','uncertainty':'fixed working Gaussian intervals, not calibrated; carry all saved uncertainty flags','resource_cap':'one deterministic CPU replay <1 minute, no search/training/inference/new observations','stop':'register missing/excluded sections, run all eligible exported other sections, save result, no model or parameter changes','protected_files':hashes,'inventory':inventory}
    dump(OUT/'eligibility_and_contract.json',contract)
    print(json.dumps(inventory,indent=2))

def run():
    started=datetime.now(timezone.utc).isoformat();t=time.time();sanity()
    contract_path=OUT/'eligibility_and_contract.json';contract_sha=sha(contract_path);c=json.loads(contract_path.read_text())
    assert all(sha(p)==h for p,h in c['protected_files'].items())
    rows=[];cached=list(csv.DictReader((BASE/'section3_prefix_slope_init_20261018/predictions_and_errors.csv').open()))
    data=json.loads(SOURCE.read_text());new_count=0
    for entry in c['inventory']:
        if not entry['eligible']:continue
        b=entry['beam'];sec=entry['section'];seq=next(s for s in data['sequences'] if s['beam_id']==b);col=seq['paired_visible_reference_transects'].index(sec);obs=seq['observations'];y=[o['model_widths_strip_px'][col] for o in obs];loads=[o['metadata']['nominal_stage_load_kN'] for o in obs]
        for i in range(1,len(obs)):
            for method in METHODS:
                if sec==3:
                    r=next(r for r in cached if int(r['beam'])==b and r['target']==obs[i]['image'] and r['method']==method)
                    mean=float(r['prediction']);sd=float(r['sd']) if r['sd'] else None;source='reused_section3_cache'
                    # Independent equality check only; cached result remains authoritative.
                    test=prefix_slope_forecast(y[:i],loads[:i],loads[i]) if method=='prefix_slope_state_space' else forecast(y[:i],loads[:i],loads[i],'state_space' if method=='original_state_space' else 'load_secant')
                    assert abs(test[0]-mean)<1e-12
                else:
                    mean,var=prefix_slope_forecast(y[:i],loads[:i],loads[i]) if method=='prefix_slope_state_space' else forecast(y[:i],loads[:i],loads[i],'state_space' if method=='original_state_space' else 'load_secant')
                    sd=math.sqrt(var) if var is not None else None;source='fixed_equation_existing_widths';new_count+=1
                rows.append({'beam':b,'section':sec,'origin':obs[i-1]['image'],'target':obs[i]['image'],'load_kN':loads[i],'history_n':i,'primary':i>=2,'additional_section':sec!=3,'method':method,'observed':y[i],'prediction':mean,'error':mean-y[i],'absolute_error':abs(mean-y[i]),'sd':sd,'lower':mean-1.96*sd if sd else None,'upper':mean+1.96*sd if sd else None,'source':source,'origin_status':obs[i-1]['width_observation_status'][col],'target_status':obs[i]['width_observation_status'][col],'uncertainty_flags':'|'.join(entry['uncertainty_flags'])})
    write_csv(OUT/'predictions_and_errors.csv',rows)
    sections=[]
    for entry in c['inventory']:
        if not entry['eligible']:continue
        for m in METHODS:
            rs=[r for r in rows if r['beam']==entry['beam'] and r['section']==entry['section'] and r['method']==m and r['primary']]
            sections.append({'beam':entry['beam'],'section':entry['section'],'method':m,'n_primary':len(rs),'mae':float(np.mean([r['absolute_error'] for r in rs])),'rmse':float(np.sqrt(np.mean([r['error']**2 for r in rs])))})
    write_csv(OUT/'section_scores.csv',sections);summary={};beamrows=[]
    for scope in ['additional_sections','all_eligible_sections','warmup_additional']:
        summary[scope]={}
        for m in METHODS:
            per={}
            for b in (4,5,6):
                rs=[r for r in rows if r['beam']==b and r['method']==m and (r['additional_section'] or scope=='all_eligible_sections') and r['primary']==(scope!='warmup_additional')]
                if not rs:continue
                secids=sorted(set(r['section'] for r in rs));mae=float(np.mean([np.mean([r['absolute_error'] for r in rs if r['section']==s]) for s in secids]));per[str(b)]={'mae':mae,'n_section_targets':len(rs),'sections':secids};beamrows.append({'scope':scope,'beam':b,'method':m,**per[str(b)]})
            summary[scope][m]={'equal_beam_mae':float(np.mean([v['mae'] for v in per.values()])),'per_beam':per}
    dump(OUT/'summary.json',summary);write_csv(OUT/'beam_scores.csv',beamrows)
    eligible=[e for e in c['inventory'] if e['eligible'] and e['section']!=3]
    fig,axs=plt.subplots(len(eligible),2,figsize=(12,3*len(eligible)),squeeze=False)
    for axrow,e in zip(axs,eligible):
        rs=[r for r in rows if r['beam']==e['beam'] and r['section']==e['section']]
        first=[r for r in rs if r['method']==METHODS[0]]
        axrow[0].plot([r['load_kN'] for r in first],[r['observed'] for r in first],'ko-',label='Saved mask width')
        for m,label,color in zip(METHODS,LABELS,COLORS):
            z=[r for r in rs if r['method']==m];xx=[r['load_kN'] for r in z]
            axrow[0].plot(xx,[r['prediction'] for r in z],'--o',color=color,label=label)
            axrow[1].plot(xx,[r['error'] for r in z],'o-',color=color,label=label)
        axrow[0].set_title(f'Beam {e["beam"]}, section {e["section"]}');axrow[0].set_ylabel('Width (strip px)');axrow[1].set_title('Signed error; first point is warm-up');axrow[1].set_ylabel('Prediction - observation (px)');axrow[1].axhline(0,color='black',lw=.7)
        for ax in axrow:ax.set_xlabel('Specified next nominal load (kN)');ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.suptitle('D01 additional sections: all eligible cases, one-step prefix replay\nPreviously exposed controlled-experiment archive; three beams, correlated sections',fontsize=11);fig.tight_layout(rect=(0,0,1,.96));fig.savefig(OUT/'F01_all_other_section_predictions.png',dpi=150);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(12,4.5));xx=np.arange(3);w=.24
    for j,(m,label,color) in enumerate(zip(METHODS,LABELS,COLORS)):
        axs[0].bar(xx+(j-1)*w,[summary['additional_sections'][m]['per_beam'][str(b)]['mae'] for b in (4,5,6)],w,color=color,label=label)
        scores=[v for v in sections if v['method']==m and v['section']!=3];axs[1].plot(range(len(scores)),[v['mae'] for v in scores],'o-',color=color,label=label)
    axs[0].set(xticks=xx,xticklabels=['Beam 4','Beam 5','Beam 6'],ylabel='Equal-section MAE (px)',title='Three physical beams; sections averaged within beam');axs[1].set(xticks=range(len(eligible)),xticklabels=[f'B{e["beam"]} S{e["section"]}' for e in eligible],ylabel='MAE (px)',title='Every additional eligible section; no section selection')
    for ax in axs:ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2)
    fig.suptitle('D01 frozen-noise development robustness; main targets exclude first-transition warm-up',fontsize=10);fig.tight_layout();fig.savefig(OUT/'F02_beam_section_errors.png',dpi=150);plt.close(fig)
    assert sha(contract_path)==contract_sha and all(sha(p)==h for p,h in c['protected_files'].items())
    dump(OUT/'receipt.json',{'start_utc':started,'completed_utc':datetime.now(timezone.utc).isoformat(),'runtime_s':time.time()-t,'host':socket.gethostname(),'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).parent.parent,text=True).strip(),'script_sha256':sha(__file__),'eligibility_contract_sha256':contract_sha,'protected_file_count':len(c['protected_files']),'protected_files_unchanged':True,'reused_section3_forecasts':len(cached),'new_fixed_equation_forecasts':new_count,'no_parameter_fit_or_training':True,'new_images_or_measurements':False,'grouping_units':3,'section3_cache_consistency':True})
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['prepare','run']);args=ap.parse_args()
    prepare() if args.phase=='prepare' else run()
