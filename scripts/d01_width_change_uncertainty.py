"""Existing-data evidence and frozen-mask sampling sensitivity, no model fit."""
import csv,json,hashlib,math,socket,subprocess,time
from datetime import datetime,timezone
from pathlib import Path
import cv2,numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from audit_d01_measurement_readiness import mapped_points,intervals
from d01_section3_prediction import write_csv

ROOT=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl');BASE=ROOT/'local_archive/experiments/S03-E016-D01'
OUT=BASE/'width_change_uncertainty_20261018';AN=BASE/'fourteen_stage_extension_20261017/analysis';SOURCE=AN/'state_space_inputs.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2))
def readcsv(p):return list(csv.DictReader(p.open()))
def main():
    began=time.time();started=datetime.now(timezone.utc).isoformat();OUT.mkdir(exist_ok=False)
    data=json.loads(SOURCE.read_text());repeat_path=BASE/'annotation_review_20261017_v2/repeat_pairs.csv';repeat=readcsv(repeat_path)
    maxrepeat=max(float(r['abs_width_difference_px']) for r in repeat);assert abs(maxrepeat-.8)<1e-10
    protected=json.loads((BASE/'other_sections_prefix_20261018/eligibility_and_contract.json').read_text())['protected_files']
    for p in [repeat_path,BASE/'annotation_review_20261017_v2/endpoint_growth.csv',BASE/'common_support_state_space_inputs_20261017_r002/registration_diagnostics.json']:
        protected[str(p)]=sha(p)
    for b in (4,5,6):
        p=AN/f'beam{b}_transforms.npz';protected[str(p)]=sha(p)
    assert all(sha(p)==h for p,h in protected.items())
    contract={'question':'Can saved width changes and local slope-change signs be separated from available observation/registration uncertainty evidence?','stage':'exploratory diagnostic, three controlled-experiment beams, previously exposed archive','scope':'same 36 saved widths / eight paired cuts / 14 frozen masks; no source RGB reads, new registration fit, mask change, training or prediction model','evidence':'reuse six human hidden repeats, eight paired human endpoints, archived registration residuals and control shifts','translation_scenarios':'sample unchanged native binary masks on original mapped fixed center line plus zero/16 equally spaced native x/y shifts; radii 1 native px and each frame archived median reprojection residual; quarter-strip-pixel grid and existing >=0.5 interpolation crossing operator','no_uncertainty_calibration':'residual radius is a diagnostic scale, not transform covariance or confidence radius; first-frame residual0 is coordinate anchor, not known-zero uncertainty; 16 directions are finite scenarios, not exhaustive bounds','measurement_stress':'separately add +/-max hidden-repeat width difference (0.8 strip px) to each observation; conservative assumed sensitivity only, not algorithm error distribution; no noise parameters changed','change_test':'compute signed delta widths and local slope contrasts per 10kN; independent extrema across frame scenario ranges; report sign survival with and without repeat-scale stress, not significance','endpoint_bias':'report every model-minus-human endpoint discrepancy and its within-cut drift; do not subtract pooled bias or assume intermediate bias bounded','unit':'strip px widths; native px shift radii converted through existing mapping by resampling, never directly subtracted from strip width','stop':'one CPU diagnostic, <=2min, no model run or new fit; save evidence and identify unresolved uncertainty','protected_files':protected}
    dump(OUT/'frozen_contract.json',contract)
    samples=[];observations=[];changes=[];curves=[];endpoints=[];ninvalid=0;maxzero=0.
    for seq in data['sequences']:
        b=seq['beam_id'];obs=seq['observations'];hs=np.load(AN/f'beam{b}_transforms.npz')['current_native_to_reference_native'];local={}
        for i,(o,h) in enumerate(zip(obs,hs)):
            mask=(np.asarray(Image.open(o['mask_source']))>0).astype('float32')
            residual=o['metadata']['registration_median_residual_native_px']
            for j,sec in enumerate(seq['paired_visible_reference_transects']):
                cut=next(t for t in seq['fixed_transect_geometry'] if t['id']==sec);dense=np.arange(0,120.001,.25);xy=mapped_points(cut['center'],cut['normal'],h,dense-60,np.array([0]))
                def measure(dx,dy):
                    shifted=(xy[0]+np.float32(dx),xy[1]+np.float32(dy));p=cv2.remap(mask,*shifted,cv2.INTER_LINEAR)[0];runs=[r for r in intervals(dense,p) if r[0]<=75 and r[1]>=45]
                    status='ok' if len(runs)==1 and not runs[0][2] else 'missing_or_multiple_or_censored'
                    return (runs[0][1]-runs[0][0] if status=='ok' else None),status
                baseline,status=measure(0,0);assert status=='ok';diff=abs(baseline-o['model_widths_strip_px'][j]);maxzero=max(maxzero,diff);assert diff<1e-6,(o['image'],sec,diff)
                rec={'beam':b,'section':sec,'image':o['image'],'load_kN':o['metadata']['nominal_stage_load_kN'],'saved_width':o['model_widths_strip_px'][j],'zero_shift_replay':baseline,'registration_residual_native_px':residual,'status':o['width_observation_status'][j],'uncertainty_flags':'|'.join(o['uncertainty_flags'])}
                for name,radius in [('one_native_px',1.),('archived_residual_radius',residual)]:
                    vals=[baseline];invalid=0
                    for k in range(16):
                        theta=k*2*np.pi/16;dx=radius*math.cos(theta);dy=radius*math.sin(theta);v,st=measure(dx,dy)
                        samples.append({'beam':b,'section':sec,'image':o['image'],'scenario':name,'radius_native_px':radius,'direction':k,'dx_native_px':dx,'dy_native_px':dy,'width':v,'status':st})
                        if v is None:invalid+=1
                        else:vals.append(v)
                    rec[name+'_low']=min(vals);rec[name+'_high']=max(vals);rec[name+'_invalid']=invalid;ninvalid+=invalid
                observations.append(rec);local[i,sec]=rec
        for j,sec in enumerate(seq['paired_visible_reference_transects']):
            y=[o['model_widths_strip_px'][j] for o in obs];x=[o['metadata']['nominal_stage_load_kN']/10 for o in obs]
            for i in range(1,len(obs)):
                r={'beam':b,'section':sec,'origin':obs[i-1]['image'],'target':obs[i]['image'],'load_kN':x[i]*10,'delta_load_10kN':x[i]-x[i-1],'delta_width':y[i]-y[i-1],'human_repeat_stress_radius':2*maxrepeat}
                for name in ['one_native_px','archived_residual_radius']:
                    a,z=local[i-1,sec],local[i,sec];lo=z[name+'_low']-a[name+'_high'];hi=z[name+'_high']-a[name+'_low'];invalid=a[name+'_invalid']+z[name+'_invalid']
                    r[name+'_low']=lo;r[name+'_high']=hi;r[name+'_sign_survives']=bool(not invalid and (lo>0 or hi<0));r[name+'_repeat_stress_sign_survives']=bool(not invalid and (lo-2*maxrepeat>0 or hi+2*maxrepeat<0));r[name+'_invalid']=invalid
                changes.append(r)
                if i>=2:
                    d0=x[i-1]-x[i-2];d1=x[i]-x[i-1];weights=[1/d0,-1/d0-1/d1,1/d1];contrast=sum(w*y[k] for w,k in zip(weights,range(i-2,i+1)));stress=sum(abs(w) for w in weights)*maxrepeat
                    rr={'beam':b,'section':sec,'target':obs[i]['image'],'load_kN':x[i]*10,'slope_change_px_per10kN':contrast,'repeat_stress_radius':stress}
                    for name in ['one_native_px','archived_residual_radius']:
                        lo=hi=0.;invalid=0
                        for w,k in zip(weights,range(i-2,i+1)):
                            z=local[k,sec];lo+=w*z[name+'_low' if w>=0 else name+'_high'];hi+=w*z[name+'_high' if w>=0 else name+'_low'];invalid+=z[name+'_invalid']
                        rr[name+'_low']=lo;rr[name+'_high']=hi;rr[name+'_sign_survives']=bool(not invalid and (lo>0 or hi<0));rr[name+'_repeat_stress_sign_survives']=bool(not invalid and (lo-stress>0 or hi+stress<0));rr[name+'_invalid']=invalid
                    curves.append(rr)
            hf=obs[0]['human_reference_widths_strip_px'][j];hl=obs[-1]['human_reference_widths_strip_px'][j];mf=y[0];ml=y[-1]
            endpoints.append({'beam':b,'section':sec,'human_first':hf,'human_last':hl,'model_first':mf,'model_last':ml,'human_growth':hl-hf,'mask_growth':ml-mf,'initial_disagreement':mf-hf,'final_disagreement':ml-hl,'disagreement_drift':(ml-mf)-(hl-hf),'human_growth_exceeds_observed_repeat_max':hl-hf>maxrepeat})
    for name,rs in [('sampling_scenarios',samples),('observation_sensitivity',observations),('adjacent_width_changes',changes),('local_slope_changes',curves),('endpoint_disagreement',endpoints)]:write_csv(OUT/(name+'.csv'),rs)
    summary={'saved_widths':len(observations),'adjacent_section_changes':len(changes),'local_slope_contrasts':len(curves),'human_repeat_pairs':len(repeat),'human_repeat_mean_abs':float(np.mean([float(r['abs_width_difference_px']) for r in repeat])),'human_repeat_max_abs':maxrepeat,'endpoint_pairs':len(endpoints),'endpoint_disagreement_drift_range':[min(e['disagreement_drift'] for e in endpoints),max(e['disagreement_drift'] for e in endpoints)],'translation_scenario_invalid_count':ninvalid,'zero_shift_replay_max_abs_difference':maxzero}
    for name,rs in [('adjacent_changes',changes),('slope_changes',curves)]:
        summary[name]={s:{'sign_survives_sampled_translations':sum(r[s+'_sign_survives'] for r in rs),'sign_survives_translations_plus_repeat_stress':sum(r[s+'_repeat_stress_sign_survives'] for r in rs),'n':len(rs)} for s in ['one_native_px','archived_residual_radius']}
    dump(OUT/'summary.json',summary)
    # Show every exported section, no cherry-picked examples.
    fig,axs=plt.subplots(4,2,figsize=(13,12));keys=[(s['beam_id'],k) for s in data['sequences'] for k in s['paired_visible_reference_transects']]
    for ax,(b,sec) in zip(axs.flat,keys):
        z=[r for r in changes if r['beam']==b and r['section']==sec];xx=np.array([r['load_kN'] for r in z]);yy=np.array([r['delta_width'] for r in z]);lo=np.array([r['archived_residual_radius_low'] for r in z]);hi=np.array([r['archived_residual_radius_high'] for r in z])
        ax.axhspan(-2*maxrepeat,2*maxrepeat,color='#999999',alpha=.12,label='±1.6 px assumed repeat-scale stress');ax.errorbar(xx,yy,yerr=np.array([yy-lo,hi-yy]),fmt='o-',capsize=4,color='#0072b2',label='Saved change + residual-scale shift scenarios');ax.axhline(0,color='black',lw=.7);ax.set(title=f'Beam {b}, section {sec}',xlabel='Target nominal load (kN)',ylabel='Adjacent width change (strip px)');ax.grid(alpha=.2)
    handles,labels=axs.flat[0].get_legend_handles_labels();fig.legend(handles,labels,loc='lower center',fontsize=9);fig.suptitle('D01: all 28 adjacent section changes on unchanged masks\nFinite translation scenarios, not confidence bounds; only three physical beams',fontsize=12);fig.tight_layout(rect=(0,.045,1,.95));fig.savefig(OUT/'F01_all_width_changes.png',dpi=150);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(13,5));xx=np.arange(len(endpoints));axs[0].plot(xx,[e['human_growth'] for e in endpoints],'o-',color='black',label='Single-observer visible-edge change');axs[0].plot(xx,[e['mask_growth'] for e in endpoints],'s-',color='#0072b2',label='Frozen-mask change');axs[0].axhline(maxrepeat,color='#d68a15',ls=':',label='Max observed hidden-repeat difference (0.8)');axs[0].set(xticks=xx,xticklabels=[f'B{e["beam"]}S{e["section"]}' for e in endpoints],ylabel='First-to-last width change (strip px)',title='Eight paired endpoints: growth agreement is not constant bias');axs[0].tick_params(axis='x',rotation=40);axs[0].legend(fontsize=8)
    xx=np.arange(len(curves));yy=np.array([r['slope_change_px_per10kN'] for r in curves]);lo=np.array([r['archived_residual_radius_low'] for r in curves]);hi=np.array([r['archived_residual_radius_high'] for r in curves]);stress=np.array([r['repeat_stress_radius'] for r in curves]);axs[1].vlines(xx,lo-stress,hi+stress,color='#bbbbbb',lw=5,label='Add assumed repeat-scale width stress');axs[1].errorbar(xx,yy,yerr=np.array([yy-lo,hi-yy]),fmt='o',capsize=2,color='#0072b2',label='Residual-scale translation scenarios');axs[1].axhline(0,color='black',lw=.7);axs[1].set(xticks=xx,xticklabels=[f'B{r["beam"]}S{r["section"]}@{r["load_kN"]:g}' for r in curves],ylabel='Slope change (strip px / 10 kN)',title='All local slope contrasts: no calibrated significance');axs[1].tick_params(axis='x',rotation=90,labelsize=7);axs[1].legend(fontsize=8)
    fig.suptitle('Existing human evidence and frozen-mask registration sensitivity; development archive',fontsize=11);fig.tight_layout();fig.savefig(OUT/'F02_endpoint_and_slope_evidence.png',dpi=150);plt.close(fig)
    assert all(sha(p)==h for p,h in protected.items())
    dump(OUT/'receipt.json',{'started_utc':started,'completed_utc':datetime.now(timezone.utc).isoformat(),'runtime_s':time.time()-began,'host':socket.gethostname(),'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).parent.parent,text=True).strip(),'script_sha256':sha(__file__),'protected_files_unchanged':True,'protected_count':len(protected),'zero_shift_matches_saved_widths':True,'no_training_registration_refit_model_or_mask_change':True})
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
