"""One authorized D01 comparison from frozen numeric coverage tables only."""
import csv,json,hashlib,time,socket,subprocess,math
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl');BASE=ROOT/'local_archive/experiments/S03-E016-D01';PREP=BASE/'spatial_baseline_preparation_20261019';SOURCE=BASE/'geometry_state_audit_20261018';OUT=BASE/'spatial_baselines_20261019'
METHODS=['persistence','load_secant'];NAMES=['Spatial persistence','Prefix load secant'];COLORS=['#777777','#0072b2']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def csvread(p):return list(csv.DictReader(p.open()))
def csvwrite(p,rows):
    with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def dump(p,x):p.write_text(json.dumps(x,indent=2))
def predict(prefix,loads,next_load,method):
    y=np.asarray(prefix,float);x=np.asarray(loads,float);assert y.ndim==2 and y.shape[1]==16 and len(y)==len(x) and np.isfinite(y).all() and np.all(np.diff(x)>0) and next_load>x[-1]
    if method=='persistence' or len(y)==1:return y[-1].copy()
    assert method=='load_secant';return y[-1]+(y[-1]-y[-2])*(next_load-x[-1])/(x[-1]-x[-2])
def sanity():
    y=np.vstack([np.ones(16)*.02,np.ones(16)*.04]);assert np.allclose(predict(y,[10,30],40,'load_secant'),.05)
    assert np.array_equal(predict(y[:1],[10],30,'load_secant'),predict(y[:1],[10],30,'persistence'))
    future=np.vstack([y,np.ones(16)*99]);p=predict(future[:2],[10,30],40,'load_secant');future[2]=-99;assert np.array_equal(p,predict(future[:2],[10,30],40,'load_secant'))
    assert np.allclose(predict(y+.1,[10,30],40,'load_secant')-p,.1)
    w=np.array([1.,3.]);err=np.array([-.2,.1]);assert abs((w@np.abs(err)/w.sum())-.125)<1e-12
def main():
    sanity();started=datetime.now(timezone.utc).isoformat();t=time.time();manifest=json.loads((PREP/'preparation_manifest.json').read_text());protected=dict(manifest['source_hashes'])
    for p in [PREP/'PREPARATION_CARD.md',PREP/'allowed_prefix_target_pairs.csv',PREP/'preparation_manifest.json']:protected[str(p)]=sha(p)
    assert all(sha(p)==h for p,h in protected.items());OUT.mkdir(exist_ok=False)
    dump(OUT/'execution_contract.json',{'authorization':'User2026-10-19 explicitly requested running exactly the prepared comparison','preparation_commit':'adb2f665','source_preparation':str(PREP),'score':manifest['score'],'point_methods':manifest['baseline_formulas'],'source_hashes':protected,'scope':'same3 beams,14 exposed stages,8main+3warmups; numeric tables only; no mask/image/holdout reads,training,registration or MD03 work','no_clipping':'retain raw out-of-range secant values and flag; no growth-monotonicity constraint','uncertainty':'carry origin and retrospective target labels, not used in predictor; no probabilistic calibration claimed'})
    meta=csvread(SOURCE/'geometry_time_series.csv');grid=csvread(SOURCE/'fixed_grid_coverage.csv');pairs=csvread(PREP/'allowed_prefix_target_pairs.csv');byimage={r['image']:r for r in meta};states={};supports={};quality={}
    for image in byimage:
        rs=sorted([r for r in grid if r['image']==image],key=lambda r:int(r['cell']));assert len(rs)==16 and [int(r['cell']) for r in rs]==list(range(16));states[image]=np.array([float(r['coverage_fraction']) for r in rs]);supports[image]=np.array([int(r['support_reference_px2']) for r in rs]);quality[image]=[float(r['uncertain_mask_share']) if r['uncertain_mask_share'] else None for r in rs];assert (supports[image]>0).all();assert abs(states[image]@supports[image]-float(byimage[image]['candidate_area_reference_px2']))<1e-6
    percell=[];pertarget=[];fields=[]
    for pair in pairs:
        origin=pair['origin_image'];target=pair['target_image'];beam=int(pair['beam']);prefix_ids=pair['allowed_prefix_images'].split('|');loads=[float(x) for x in pair['allowed_prefix_loads_kN'].split('|')];next_load=float(pair['specified_next_nominal_load_kN']);assert prefix_ids[-1]==origin and target not in prefix_ids and int(byimage[origin]['beam'])==int(byimage[target]['beam'])==beam;assert float(byimage[target]['load_kN'])==next_load
        for image,load in zip(prefix_ids,loads):assert int(byimage[image]['beam'])==beam and float(byimage[image]['load_kN'])==load and np.array_equal(supports[image],supports[origin])
        weight=supports[origin];assert np.array_equal(weight,supports[target]);prefix=[states[image] for image in prefix_ids]
        # Predict with prefix only, then access the target for evaluation.
        preds={method:predict(prefix,loads,next_load,method) for method in METHODS};actual=states[target]
        for method in METHODS:
            pred=preds[method];err=pred-actual;out_of_range=(pred<0)|(pred>1);weighted=float(weight@np.abs(err)/weight.sum());signed_area=float(weight@err);rec={'beam':beam,'origin':origin,'target':target,'origin_load_kN':loads[-1],'target_load_kN':next_load,'prefix_images':'|'.join(prefix_ids),'history_n':len(prefix_ids),'score_role':pair['score_role'],'method':method,'spatial_weighted_L1_fraction':weighted,'spatial_error_pp':100*weighted,'pred_total_coverage_percent':100*float(weight@pred/weight.sum()),'observed_total_coverage_percent':100*float(weight@actual/weight.sum()),'total_area_signed_error_ref_px2':signed_area,'total_area_absolute_error_ref_px2':abs(signed_area),'out_of_range_cells':int(out_of_range.sum()),'origin_uncertain_candidate_share':byimage[origin]['uncertain_candidate_share'],'target_uncertain_candidate_share_retrospective_only':byimage[target]['uncertain_candidate_share'],'origin_flags':byimage[origin]['uncertainty_flags'],'target_flags_retrospective_only':byimage[target]['uncertainty_flags']};pertarget.append(rec)
            for k in range(16):percell.append({'beam':beam,'origin':origin,'target':target,'specified_next_load_kN':next_load,'allowed_prefix_images':rec['prefix_images'],'history_n':len(prefix_ids),'score_role':pair['score_role'],'method':method,'cell':k,'support_ref_px2':int(weight[k]),'origin_coverage':float(states[origin][k]),'target_coverage':float(actual[k]),'prediction':float(pred[k]),'signed_error':float(err[k]),'absolute_error':float(abs(err[k])),'out_of_range_prediction':bool(out_of_range[k]),'origin_uncertain_mask_share':quality[origin][k],'target_uncertain_mask_share_retrospective_only':quality[target][k],'origin_flags':rec['origin_flags'],'target_flags_retrospective_only':rec['target_flags_retrospective_only']})
        fields.append({'pair':pair,'actual':actual,'persistence':preds['persistence'],'load_secant':preds['load_secant']})
    csvwrite(OUT/'predictions_by_cell.csv',percell);csvwrite(OUT/'per_target_errors.csv',pertarget);warm=[r for r in pertarget if r['score_role']=='warmup'];csvwrite(OUT/'warmup_errors.csv',warm)
    summary=[]
    for method in METHODS:
        beamvalues=[]
        for b in (4,5,6):
            rs=[r for r in pertarget if r['beam']==b and r['method']==method and r['score_role']=='primary'];value=float(np.mean([r['spatial_error_pp'] for r in rs]));beamvalues.append(value);summary.append({'beam':b,'method':method,'primary_targets':len(rs),'mean_spatial_error_pp':value,'out_of_range_primary_cells':sum(r['out_of_range_cells'] for r in rs)})
        summary.append({'beam':'equal_beam_mean','method':method,'primary_targets':8,'mean_spatial_error_pp':float(np.mean(beamvalues)),'out_of_range_primary_cells':sum(r['out_of_range_cells'] for r in pertarget if r['method']==method and r['score_role']=='primary')})
    csvwrite(OUT/'per_beam_summary.csv',summary);p=next(r['mean_spatial_error_pp'] for r in summary if r['beam']=='equal_beam_mean' and r['method']=='persistence');s=next(r['mean_spatial_error_pp'] for r in summary if r['beam']=='equal_beam_mean' and r['method']=='load_secant');paired=[]
    for f in fields:
        pair=f['pair'];a=next(r for r in pertarget if r['target']==pair['target_image'] and r['method']=='persistence');b=next(r for r in pertarget if r['target']==pair['target_image'] and r['method']=='load_secant');paired.append({'beam':a['beam'],'origin':a['origin'],'target':a['target'],'target_load_kN':a['target_load_kN'],'score_role':a['score_role'],'persistence_spatial_error_pp':a['spatial_error_pp'],'secant_spatial_error_pp':b['spatial_error_pp'],'secant_minus_persistence_pp':b['spatial_error_pp']-a['spatial_error_pp'],'secant_out_of_range_cells':b['out_of_range_cells']})
    csvwrite(OUT/'paired_target_errors.csv',paired);dump(OUT/'summary.json',{'per_beam':summary,'primary_equal_beam_error_pp':{'persistence':p,'load_secant':s},'relative_error_reduction_secant_percent':100*(1-s/p),'main_targets_improved':sum(r['secant_minus_persistence_pp']<0 for r in paired if r['score_role']=='primary'),'main_targets_worsened':sum(r['secant_minus_persistence_pp']>0 for r in paired if r['score_role']=='primary'),'uncertainty_flags_preserved':True,'reference':'frozen biased mask coverage, not independent physical truth','development_only':True})
    fig,axs=plt.subplots(3,2,figsize=(12,10))
    for i,b in enumerate((4,5,6)):
        rs=sorted([r for r in meta if int(r['beam'])==b],key=lambda r:float(r['load_kN']));axs[i,0].plot([float(r['load_kN']) for r in rs],[100*float(r['candidate_coverage_fraction']) for r in rs],'ko-',label='Saved observed mask');warm_load=float(rs[1]['load_kN']);axs[i,0].axvspan(warm_load-.8,warm_load+.8,color='gray',alpha=.12);axs[i,1].axvspan(warm_load-.8,warm_load+.8,color='gray',alpha=.12)
        for method,name,color in zip(METHODS,NAMES,COLORS):
            z=[r for r in pertarget if r['beam']==b and r['method']==method];axs[i,0].plot([r['target_load_kN'] for r in z],[r['pred_total_coverage_percent'] for r in z],'--o',color=color,label=name);axs[i,1].plot([r['target_load_kN'] for r in z],[r['spatial_error_pp'] for r in z],'o-',color=color,label=name)
        axs[i,0].set(ylabel=f'Beam{b} total coverage (%)',title='Total coverage: diagnostic summary');axs[i,1].set(ylabel='Spatial weighted L1 (pp)',title='Primary metric; grey first-target warm-up')
        for ax in axs[i]:ax.set_xlabel('Specified next nominal load (kN)');ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.suptitle('D01 fixed4x4 spatial baselines:8primary targets +3separate warm-ups\nAvailable-prefix replay;3exposed development beams; no uncertainty calibration',fontsize=11);fig.tight_layout(rect=(0,0,1,.94));fig.savefig(OUT/'F01_predictions_and_spatial_errors.png',dpi=160);plt.close(fig)
    values=np.concatenate([f[k] for f in fields for k in ['actual']+METHODS])*100;vmin=min(0,float(values.min()));vmax=float(values.max());maxerr=max(float(np.max(np.abs(f[m]-f['actual'])))*100 for f in fields for m in METHODS)
    def maps(subset,name):
        fig,axs=plt.subplots(len(subset),5,figsize=(12,2.3*len(subset)),squeeze=False)
        for i,f in enumerate(subset):
            arrays=[f['actual'],f['persistence'],f['load_secant'],f['persistence']-f['actual'],f['load_secant']-f['actual']];pair=f['pair']
            for j,arr in enumerate(arrays):
                ax=axs[i,j];im=ax.imshow(arr.reshape(4,4)*100,cmap='cividis' if j<3 else 'RdBu_r',vmin=vmin if j<3 else -maxerr,vmax=vmax if j<3 else maxerr);ax.set_xticks([]);ax.set_yticks([])
                if i==0:ax.set_title(['Observed mask','Persistence','Load secant','Persistence error','Secant error'][j],fontsize=9)
                if j==0:ax.set_ylabel(f'B{pair["beam"]}: {pair["origin_load_kN"]}→{pair["specified_next_nominal_load_kN"]}kN',fontsize=8)
        fig.subplots_adjust(right=.87,hspace=.18,wspace=.1,top=.94);ca=fig.add_axes([.9,.57,.015,.28]);ce=fig.add_axes([.9,.16,.015,.28]);fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(vmin,vmax),cmap='cividis'),cax=ca,label='Cell coverage (%)');fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(-maxerr,maxerr),cmap='RdBu_r'),cax=ce,label='Prediction - observed (pp)');fig.suptitle('D01 '+name.replace('_',' ')+' | common scales; raw secant incl. out-of-range values; same16fixed cells',fontsize=10);fig.savefig(OUT/(name+'.png'),dpi=160);plt.close(fig)
    maps([f for f in fields if f['pair']['score_role']=='primary'],'F02_all_8_primary_predictions');maps([f for f in fields if f['pair']['score_role']=='warmup'],'F03_all_3_warmup_predictions')
    assert len(percell)==352 and len(pertarget)==22 and len(warm)==6
    assert all(np.array_equal(f['persistence'],f['load_secant']) for f in fields if f['pair']['score_role']=='warmup')
    # Independent CSV scalar recomputation, not another forecast run.
    for r in pertarget:
        z=[x for x in percell if x['target']==r['target'] and x['method']==r['method']];assert abs(100*sum(x['support_ref_px2']*x['absolute_error'] for x in z)/sum(x['support_ref_px2'] for x in z)-r['spatial_error_pp'])<1e-12
    assert all(sha(path)==h for path,h in protected.items());dump(OUT/'validation.json',{'prediction_cells':352,'primary_targets':8,'separate_warmup_targets':3,'all_3_warmup_methods_identical':True,'unequal_load_and_prefix_isolation_sanity':True,'spatial_metric_independently_recomputed_from_cell_errors':True,'source_hashes_unchanged':True,'no_mask_image_holdout_reads':True,'no_training_or_MD03_work':True,'all_targets_and_out_of_range_values_retained':True});dump(OUT/'receipt.json',{'started_utc':started,'completed_utc':datetime.now(timezone.utc).isoformat(),'runtime_s':time.time()-t,'host':socket.gethostname(),'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).parent.parent,text=True).strip(),'script_sha256':sha(__file__),'protected_input_hashes':protected,'execution':'one deterministic numeric-table comparison; no new images,masks,training,parameter search or holdout access'})
    print(json.dumps({'per_beam':summary,'relative_error_reduction_percent':100*(1-s/p),'paired':paired},indent=2))
if __name__=='__main__':main()
