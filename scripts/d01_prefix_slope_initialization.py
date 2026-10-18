"""One frozen initialization change; reuse original D01 comparison outputs."""
import argparse,csv,hashlib,json,math,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from d01_section3_prediction import forecast,write_csv


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def prefix_slope_forecast(y,loads,next_load,sigma=1.,accel=.05):
    y=np.asarray(y,float);x=np.asarray(loads,float)/10.;nx=float(next_load)/10.
    assert len(y)==len(x)>=1 and np.isfinite(y).all() and (np.diff(x)>0).all() and nx>x[-1]
    if len(y)==1:return forecast(y,loads,next_load,'state_space',sigma,accel)
    d=x[1]-x[0];r=sigma**2;q=accel**2
    # Posterior at the second observation under a diffuse starting slope.
    # First two measurements enter once; initialization is not re-assimilated.
    state=np.array([y[1],(y[1]-y[0])/d])
    cov=np.array([[r,r/d],[r/d,2*r/d**2+q*d/3]])
    def predict(state,cov,d):
        f=np.array([[1.,d],[0.,1.]]);process=q*np.array([[d**3/3,d*d/2],[d*d/2,d]])
        return f@state,f@cov@f.T+process
    for j in range(2,len(y)):
        state,cov=predict(state,cov,x[j]-x[j-1]);k=cov[:,0]/(cov[0,0]+r);state+=k*(y[j]-state[0]);a=np.eye(2)-np.outer(k,[1.,0.]);cov=a@cov@a.T+r*np.outer(k,k);cov=(cov+cov.T)/2
        assert np.linalg.eigvalsh(cov).min()>-1e-10
    state,cov=predict(state,cov,nx-x[-1]);return float(state[0]),float(cov[0,0]+r)


def sanity():
    # Two-observation mean equals a load secant, including unequal load intervals.
    m,v=prefix_slope_forecast([2.,4.],[10.,30.],40.);assert abs(m-5)<1e-10 and v>0
    for sigma in (.5,1.,2.):
        y=np.array([2.,3.,5.5]);x=np.array([10.,20.,40.]);design=np.c_[np.ones(3),(x-x[0])/10];h=np.array([1.,4.]);coef=np.linalg.solve(design.T@design,design.T@y);cov=sigma**2*np.linalg.inv(design.T@design)
        actual=prefix_slope_forecast(y,x,50.,sigma,0.);assert np.allclose(actual,[h@coef,h@cov@h+sigma**2],atol=1e-9)
    y=np.array([2.,3.,5.,99.]);a=prefix_slope_forecast(y[:3],[10,20,30],40);y[3]=-99;assert a==prefix_slope_forecast(y[:3],[10,20,30],40)
    shifted=prefix_slope_forecast([9.,10.,12.],[10,20,30],40);assert abs(shifted[0]-a[0]-7)<1e-9 and abs(shifted[1]-a[1])<1e-9
    assert prefix_slope_forecast([2.],[10],20)==forecast([2.],[10],20,'state_space')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--original',type=Path,required=True);ap.add_argument('--contract',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--self-test',action='store_true');a=ap.parse_args();sanity()
    if a.self_test:print('Two-point secant, batch Gaussian equivalence, translation, prefix isolation and warm-up checks passed.');return
    began=time.time();cfg=json.loads(a.contract.read_text());oldcontract=json.loads((a.original/'frozen_contract.json').read_text());assert cfg['noise']==oldcontract['nominal']
    oldreceipt=json.loads((a.original/'receipt.json').read_text());protected=dict(oldreceipt['protected_mask_and_input_hashes']);protected[str(a.original/'predictions_and_errors.csv')]=digest(a.original/'predictions_and_errors.csv');protected[str(a.original/'summary.json')]=digest(a.original/'summary.json');assert all(digest(Path(p))==h for p,h in protected.items())
    data=json.loads(Path(oldreceipt['source_inputs']).read_text());old=list(csv.DictReader((a.original/'predictions_and_errors.csv').open()));out=a.output;out.mkdir(parents=True,exist_ok=False);(out/'frozen_contract.json').write_bytes(a.contract.read_bytes());sigma=cfg['noise']['measurement_sigma_strip_px'];accel=cfg['noise']['acceleration_sigma'];records=[];newrows=[];sensitivity=[];paired=[];initial=[];sequences=[]
    oldnames={'state_space':'original_state_space','load_secant':'load_secant'}
    for row in old:
        if row['method'] not in oldnames:continue
        rec={'beam':int(row['beam']),'method':oldnames[row['method']],'origin':row['origin'],'target':row['target_image'],'target_load_kN':float(row['target_load_kN']),'history_n':int(row['history_observations']),'primary':row['primary_scored']=='True','observed':float(row['observed_mask_width']),'prediction':float(row['prediction']),'error':float(row['error_prediction_minus_observed']),'absolute_error':float(row['absolute_error']),'sd':float(row['predictive_sd']) if row['predictive_sd'] else None,'lower':float(row['assumption_95_lower']) if row['assumption_95_lower'] else None,'upper':float(row['assumption_95_upper']) if row['assumption_95_upper'] else None};records.append(rec)
    original_lookup={(r['beam'],r['target'],r['method']):r for r in records}
    for seq in data['sequences']:
        beam=seq['beam_id'];col=seq['paired_visible_reference_transects'].index(3);obs=seq['observations'];y=np.array([o['model_widths_strip_px'][col] for o in obs]);x=np.array([o['metadata']['nominal_stage_load_kN'] for o in obs]);d=(x[1]-x[0])/10.;initial.append({'beam':beam,'first_image':obs[0]['image'],'second_image':obs[1]['image'],'init_width':float(y[1]),'prefix_slope_px_per10kN':float((y[1]-y[0])/d),'P_width':sigma**2,'P_cross':sigma**2/d,'P_slope':2*sigma**2/d**2+accel**2*d/3,'first_two_observations_assimilated_again':False});sequences.append((beam,x,y))
        for i in range(1,len(y)):
            mean,var=prefix_slope_forecast(y[:i],x[:i],x[i],sigma,accel);sd=math.sqrt(var);row={'beam':beam,'method':'prefix_slope_state_space','origin':obs[i-1]['image'],'target':obs[i]['image'],'target_load_kN':float(x[i]),'history_n':i,'primary':i>=2,'observed':float(y[i]),'prediction':mean,'error':float(mean-y[i]),'absolute_error':float(abs(mean-y[i])),'sd':sd,'lower':mean-1.96*sd,'upper':mean+1.96*sd};records.append(row);newrows.append(row)
            orig=original_lookup[beam,obs[i]['image'],'original_state_space'];sec=original_lookup[beam,obs[i]['image'],'load_secant'];assert orig['observed']==row['observed'] and orig['primary']==row['primary']
            paired.append({'beam':beam,'target':row['target'],'target_load_kN':row['target_load_kN'],'primary':row['primary'],'new_absolute_error':row['absolute_error'],'original_absolute_error':orig['absolute_error'],'secant_absolute_error':sec['absolute_error'],'new_minus_original_absolute_error':row['absolute_error']-orig['absolute_error'],'new_minus_secant_absolute_error':row['absolute_error']-sec['absolute_error']})
            for delta in (-1.,1.):
                yp=y[:i].copy();yp[-1]+=delta;perturbed,_=prefix_slope_forecast(yp,x[:i],x[i],sigma,accel);sensitivity.append({'beam':beam,'target':row['target'],'primary':row['primary'],'method':'prefix_slope_state_space','last_observation_perturbation':delta,'prediction_shift':perturbed-mean})
    for row in csv.DictReader((a.original/'last_observation_sensitivity.csv').open()):
        if row['method'] in oldnames:sensitivity.append({'beam':int(row['beam']),'target':row['target_image'],'primary':row['primary_scored']=='True','method':oldnames[row['method']],'last_observation_perturbation':float(row['last_observation_offset']),'prediction_shift':float(row['prediction_shift'])})
    methods=['original_state_space','load_secant','prefix_slope_state_space'];scores={};bands={};stability={}
    for method in methods:
        rs=[r for r in records if r['method']==method and r['primary']];per={b:{'n':len([r for r in rs if r['beam']==b]),'mae':float(np.mean([r['absolute_error'] for r in rs if r['beam']==b])),'rmse':float(np.sqrt(np.mean([r['error']**2 for r in rs if r['beam']==b])))} for b in (4,5,6)};scores[method]={'per_beam':per,'beam_balanced_mae':float(np.mean([v['mae'] for v in per.values()])),'pooled_mae':float(np.mean([r['absolute_error'] for r in rs])),'n':len(rs)}
        sr=[r for r in sensitivity if r['method']==method and r['primary']];stability[method]={'mean_absolute_prediction_shift':float(np.mean([abs(r['prediction_shift']) for r in sr])),'max_absolute_prediction_shift':float(max(abs(r['prediction_shift']) for r in sr))}
        if method!='load_secant':bands[method]={'mean_working95_band_width':float(np.mean([r['upper']-r['lower'] for r in rs])),'observed_inside_working_band':sum(r['lower']<=r['observed']<=r['upper'] for r in rs),'n':len(rs),'mean_gaussian_nll':float(np.mean([.5*(math.log(2*math.pi*r['sd']**2)+r['error']**2/r['sd']**2) for r in rs]))}
    summary={'primary_scores':scores,'working_bands_not_calibrated':bands,'last_observation_sensitivity':stability,'noise_settings_unchanged':cfg['noise'],'initialization':initial,'reused_original_forecasts':22,'new_forecasts':11,'no_hyperparameter_search':True};(out/'summary.json').write_text(json.dumps(summary,indent=2));write_csv(out/'predictions_and_errors.csv',records);write_csv(out/'paired_error_changes.csv',paired);write_csv(out/'last_observation_sensitivity.csv',sensitivity);write_csv(out/'initial_states.csv',initial)
    colors={'original_state_space':'#777777','load_secant':'#d68a15','prefix_slope_state_space':'#0072b2'};labels={'original_state_space':'Original state-space','load_secant':'Load secant','prefix_slope_state_space':'Prefix-slope state-space'};fig,axs=plt.subplots(3,2,figsize=(12,11))
    for ri,(beam,x,y) in enumerate(sequences):
        axs[ri,0].plot(x,y,'ko-',lw=1,label='Observed mask width')
        for method in methods:
            rs=sorted([r for r in records if r['beam']==beam and r['method']==method],key=lambda r:r['target_load_kN']);xx=[r['target_load_kN'] for r in rs];axs[ri,0].plot(xx,[r['prediction'] for r in rs],'--o',markersize=4,color=colors[method],label=labels[method]);axs[ri,1].plot(xx,[r['error'] for r in rs],'-o',color=colors[method],label=labels[method])
            if method=='prefix_slope_state_space':axs[ri,0].fill_between(xx,[r['lower'] for r in rs],[r['upper'] for r in rs],color=colors[method],alpha=.12,label='New working95% band (assumed)')
        axs[ri,0].set(title=f'Beam{beam}: prefix-only forecasts',xlabel='Specified next nominal load (kN)',ylabel='Width (strip-coordinate px)');axs[ri,1].axhline(0,color='black',lw=.8);axs[ri,1].set(title=f'Beam{beam}: prediction − mask observation',xlabel='Specified next nominal load (kN)',ylabel='Signed error (px)')
        for ax in axs[ri]:ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.suptitle('D01 section3: two-observation initialization, with fixed R and Q\nSame8 primary forecasts; 3 warm-ups separate. Initial mean and covariance changed coherently; no double counting.',fontsize=12);fig.tight_layout(rect=(0,0,1,.94));fig.savefig(out/'F01_prefix_initialization_predictions.png',dpi=150);plt.close(fig)
    fig,axs=plt.subplots(1,2,figsize=(13,4.8));pr=[r for r in paired if r['primary']];xx=np.arange(len(pr));axs[0].plot(xx,[r['new_minus_original_absolute_error'] for r in pr],'o-',color=colors['original_state_space'],label='New minus original');axs[0].plot(xx,[r['new_minus_secant_absolute_error'] for r in pr],'s-',color=colors['load_secant'],label='New minus secant');axs[0].axhline(0,color='black',lw=.8);axs[0].set(xticks=xx,xticklabels=[f'B{r["beam"]}→{r["target_load_kN"]:g}' for r in pr],ylabel='Change in absolute error (px)',title='Every primary target: negative means improvement');axs[0].tick_params(axis='x',rotation=35);axs[0].legend(fontsize=8);axs[1].bar(range(3),[stability[m]['mean_absolute_prediction_shift'] for m in methods],color=[colors[m] for m in methods]);axs[1].set(xticks=range(3),xticklabels=['Original SS','Load secant','Prefix-slope SS'],ylabel='Mean absolute forecast shift (px)',title='Latest observation perturbed ±1px; fixed noise')
    for ax in axs:ax.grid(axis='y',alpha=.2)
    fig.suptitle('Initialization effect and measurement sensitivity — no noise tuning',fontsize=12);fig.tight_layout(rect=(0,0,1,.93));fig.savefig(out/'F02_paired_errors_sensitivity.png',dpi=150);plt.close(fig)
    assert all(digest(Path(p))==h for p,h in protected.items());(out/'receipt.json').write_text(json.dumps({'completed_utc':datetime.now(timezone.utc).isoformat(),'runtime_s':time.time()-began,'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).parents[1],text=True).strip(),'protected_files':protected,'masks_and_original_results_unchanged':True,'training_or_neural_inference':False,'parameter_optimization':False,'MD01_touched':False,'sanity_checks':'zero-Q batch regression, unequal loads, two-point secant, translation, prefix-only and warm-up passed'},indent=2));print(json.dumps(scores,indent=2))


if __name__=='__main__':main()
