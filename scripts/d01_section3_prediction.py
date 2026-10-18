"""Small prefix-only observation forecasting experiment; no neural training."""
import argparse,csv,json,hashlib,math,subprocess,time
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def forecast(prefix,loads,next_load,method,sigma=1.,accel=.05):
    """Only the prefix and specified next load enter; returns next observed-width moments."""
    y=np.asarray(prefix,float);x=np.asarray(loads,float)/10;nx=float(next_load)/10
    assert len(y)==len(x)>=1 and np.isfinite(y).all() and (np.diff(x)>0).all() and nx>x[-1]
    if method=='persistence':return float(y[-1]),None
    if method=='load_secant':
        return float(y[-1] if len(y)==1 else y[-1]+(y[-1]-y[-2])*(nx-x[-1])/(x[-1]-x[-2])),None
    assert method=='state_space'
    # Width level is the bias-contaminated expected mask readout, not physical aperture truth.
    state=np.array([y[0],0.]);cov=np.diag([sigma*sigma,1.]);r=sigma*sigma
    def predict(s,p,d):
        f=np.array([[1.,d],[0.,1.]]);q=accel**2*np.array([[d**3/3,d*d/2],[d*d/2,d]])
        return f@s,f@p@f.T+q
    for j in range(1,len(y)):
        state,cov=predict(state,cov,x[j]-x[j-1]);gain=cov[:,0]/(cov[0,0]+r);state+=gain*(y[j]-state[0]);a=np.eye(2)-np.outer(gain,[1.,0.]);cov=a@cov@a.T+r*np.outer(gain,gain);cov=(cov+cov.T)/2
        assert np.linalg.eigvalsh(cov).min()>-1e-10
    state,cov=predict(state,cov,nx-x[-1]);return float(state[0]),float(cov[0,0]+r)


def write_csv(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def sanity():
    assert forecast([2,4],[10,30],40,'load_secant')[0]==5
    assert forecast([2],[10],20,'load_secant')[0]==2
    for method in ('persistence','load_secant','state_space'):
        m,_=forecast([2,3],[10,20],30,method);shifted,_=forecast([9,10],[10,20],30,method);assert abs(shifted-m-7)<1e-10
    mean,var=forecast([3,3,3],[10,20,40],50,'state_space');assert abs(mean-3)<1e-10 and var>0
    # A later value can change without changing the previously computed prefix forecast.
    a=np.array([1.,2.,100.]);m=forecast(a[:2],[10,20],30,'state_space');a[2]=-100;assert m==forecast(a[:2],[10,20],30,'state_space')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--contract',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--self-test',action='store_true');a=ap.parse_args();sanity()
    if a.self_test:print('Prefix isolation, unequal loads, warm-up, covariance and translation checks passed.');return
    began=time.time();contract=json.loads(a.contract.read_text());data=json.loads(a.inputs.read_text());out=a.output;out.mkdir(parents=True,exist_ok=False);shutil_contract=out/'frozen_contract.json';shutil_contract.write_bytes(a.contract.read_bytes())
    source=a.inputs.parents[1];manifest=json.loads((source/'source_manifest.json').read_text());protected={str(source/'refined_v3'/f'{e["id"]}_mask.png'):sha(source/'refined_v3'/f'{e["id"]}_mask.png') for e in manifest};protected[str(a.inputs)]=sha(a.inputs)
    methods=contract['methods'];nominal=contract['nominal'];records=[];grid=[];perturb=[];bias=[];plotdata=[]
    for seq in data['sequences']:
        beam=seq['beam_id'];col=seq['paired_visible_reference_transects'].index(3);obs=seq['observations'];y=np.array([o['model_widths_strip_px'][col] for o in obs],float);x=np.array([o['metadata']['nominal_stage_load_kN'] for o in obs],float);human=np.array([o['human_reference_widths_strip_px'][col] for o in obs],float)
        for i in range(1,len(y)):
            common={'beam':beam,'origin':obs[i-1]['image'],'target_image':obs[i]['image'],'origin_load_kN':float(x[i-1]),'target_load_kN':float(x[i]),'history_observations':i,'primary_scored':i>=2,'observed_mask_width':float(y[i]),'human_reference_width':None if not np.isfinite(human[i]) else float(human[i]),'target_is_independent_truth':False}
            for method in methods:
                mean,var=forecast(y[:i],x[:i],x[i],method,nominal['measurement_sigma_strip_px'],nominal['acceleration_sigma']);sd=math.sqrt(var) if var is not None else None
                rec={**common,'method':method,'prediction':mean,'error_prediction_minus_observed':mean-y[i],'absolute_error':abs(mean-y[i]),'squared_error':(mean-y[i])**2,'predictive_sd':sd,'assumption_95_lower':mean-1.96*sd if sd is not None else None,'assumption_95_upper':mean+1.96*sd if sd is not None else None};records.append(rec)
                for delta in contract['last_observation_perturbations_strip_px']:
                    yp=y[:i].copy();yp[-1]+=delta;mp,_=forecast(yp,x[:i],x[i],method,nominal['measurement_sigma_strip_px'],nominal['acceleration_sigma']);perturb.append({**common,'method':method,'last_observation_offset':delta,'prediction':mp,'prediction_shift':mp-mean})
            for sigma in contract['measurement_sigma_scenarios_strip_px']:
                for accel in contract['acceleration_sigma_scenarios']:
                    mean,var=forecast(y[:i],x[:i],x[i],'state_space',sigma,accel);sd=math.sqrt(var);grid.append({**common,'measurement_sigma':sigma,'acceleration_sigma':accel,'prediction':mean,'error':mean-y[i],'absolute_error':abs(mean-y[i]),'sd':sd,'lower':mean-1.96*sd,'upper':mean+1.96*sd,'assumption_band_contains_observed':abs(mean-y[i])<=1.96*sd,'gaussian_nll':.5*(math.log(2*math.pi*var)+(mean-y[i])**2/var)})
            for b in contract['constant_bias_scenarios_strip_px']:
                latent,_=forecast(y[:i]-b,x[:i],x[i],'state_space',nominal['measurement_sigma_strip_px'],nominal['acceleration_sigma']);nom,_=forecast(y[:i],x[:i],x[i],'state_space',nominal['measurement_sigma_strip_px'],nominal['acceleration_sigma']);assert abs(latent+b-nom)<1e-9;bias.append({**common,'assumed_constant_positive_mask_bias':b,'latent_visible_width_scenario_prediction':latent,'observed_width_prediction_after_adding_bias':latent+b,'interpretation':'scenario only; constant bias shifts latent level but leaves observable forecast invariant'})
        plotdata.append((beam,x,y,human))
    def summary(rows,error='absolute_error'):
        by={b:[r for r in rows if r['beam']==b] for b in (4,5,6)}
        per={b:{'n':len(rs),'mae':float(np.mean([r[error] for r in rs])),'rmse':float(np.sqrt(np.mean([(r['error_prediction_minus_observed'] if 'error_prediction_minus_observed' in r else r['error'])**2 for r in rs])))} for b,rs in by.items()}
        return {'per_beam':per,'beam_balanced_mae':float(np.mean([s['mae'] for s in per.values()])),'pooled_mae':float(np.mean([r[error] for r in rows])),'n_forecasts':len(rows)}
    results={m:summary([r for r in records if r['method']==m and r['primary_scored']]) for m in methods};allresults={m:summary([r for r in records if r['method']==m]) for m in methods};sensitivity=[]
    for sigma in contract['measurement_sigma_scenarios_strip_px']:
        for accel in contract['acceleration_sigma_scenarios']:
            rs=[r for r in grid if r['primary_scored'] and r['measurement_sigma']==sigma and r['acceleration_sigma']==accel];s=summary(rs);sensitivity.append({'measurement_sigma':sigma,'acceleration_sigma':accel,'beam_balanced_mae':s['beam_balanced_mae'],'pooled_mae':s['pooled_mae'],'mean_assumption_band_width':float(np.mean([r['upper']-r['lower'] for r in rs])),'observed_candidate_coverage_count':sum(r['assumption_band_contains_observed'] for r in rs),'n':len(rs),'mean_gaussian_nll':float(np.mean([r['gaussian_nll'] for r in rs]))})
    perturb_summary={m:{'mean_absolute_forecast_shift':float(np.mean([abs(r['prediction_shift']) for r in perturb if r['method']==m and r['primary_scored']])),'max_absolute_forecast_shift':float(max(abs(r['prediction_shift']) for r in perturb if r['method']==m and r['primary_scored']))} for m in methods}
    (out/'summary.json').write_text(json.dumps({'primary_common_8_forecasts':results,'all_11_including_warmup':allresults,'noise_sensitivity':sensitivity,'last_observation_perturbation_sensitivity':perturb_summary,'hyperparameters_optimized':False,'true_geometry_accuracy_established':False},indent=2));write_csv(out/'predictions_and_errors.csv',records);write_csv(out/'noise_sensitivity_forecasts.csv',grid);write_csv(out/'noise_sensitivity_summary.csv',sensitivity);write_csv(out/'last_observation_sensitivity.csv',perturb);write_csv(out/'constant_bias_sensitivity.csv',bias)
    colors={'persistence':'#777777','load_secant':'#d67b17','state_space':'#007fa8'};fig,axs=plt.subplots(3,2,figsize=(12,11))
    for row,(beam,x,y,human) in enumerate(plotdata):
        axs[row,0].plot(x,y,'ko-',lw=1,label='Observed mask width');valid=np.isfinite(human);axs[row,0].plot(x[valid],human[valid],linestyle='none',marker='D',mfc='none',mec='#ad4583',label='Existing human endpoints')
        for method in methods:
            rs=[r for r in records if r['beam']==beam and r['method']==method];xx=[r['target_load_kN'] for r in rs];mm=[r['prediction'] for r in rs];axs[row,0].plot(xx,mm,'--o',markersize=4,color=colors[method],label=method);axs[row,1].plot(xx,[r['error_prediction_minus_observed'] for r in rs],'-o',color=colors[method],label=method)
            if method=='state_space':axs[row,0].fill_between(xx,[r['assumption_95_lower'] for r in rs],[r['assumption_95_upper'] for r in rs],alpha=.14,color=colors[method],label='SS 95% working band (assumed)')
        axs[row,0].set(title=f'Beam{beam}: rolling one-step predictions',xlabel='Specified next nominal load (kN)',ylabel='Width (strip-coordinate px)');axs[row,1].axhline(0,color='black',lw=.8);axs[row,1].set(title=f'Beam{beam}: error against mask observation',xlabel='Specified next nominal load (kN)',ylabel='Prediction − observed (px)')
        for ax in axs[row]:ax.grid(alpha=.2);ax.legend(fontsize=7)
    fig.suptitle('D01 section 3 — prefix-only conditional forecasts, development data\nShading is assumption-based, not calibrated coverage; first target of each beam is warm-up.',fontsize=12);fig.tight_layout(rect=(0,0,1,.94));fig.savefig(out/'F01_predictions_errors.png',dpi=150);plt.close(fig)
    fig,axs=plt.subplots(1,3,figsize=(15,4.8));values=np.array([[r['beam_balanced_mae'] for r in sensitivity if r['measurement_sigma']==s] for s in contract['measurement_sigma_scenarios_strip_px']]);band=np.array([[r['mean_assumption_band_width'] for r in sensitivity if r['measurement_sigma']==s] for s in contract['measurement_sigma_scenarios_strip_px']])
    for ax,matrix,title in [(axs[0],values,'State-space beam-balanced MAE (px)'),(axs[1],band,'Mean assumed 95% band width (px)')]:
        im=ax.imshow(matrix,cmap='cividis');fig.colorbar(im,ax=ax,shrink=.8);ax.set(xticks=range(3),xticklabels=contract['acceleration_sigma_scenarios'],yticks=range(3),yticklabels=contract['measurement_sigma_scenarios_strip_px'],xlabel='Acceleration SD per load unit',ylabel='Assumed measurement SD (px)',title=title)
        for (i,j),v in np.ndenumerate(matrix):ax.text(j,i,f'{v:.3f}',ha='center',va='center',color='white' if v<matrix.mean() else 'black')
    axs[2].bar(range(3),[perturb_summary[m]['mean_absolute_forecast_shift'] for m in methods],color=[colors[m] for m in methods]);axs[2].set(xticks=range(3),xticklabels=['Persistence','Load secant','State space'],ylabel='Mean absolute forecast shift (px)',title='Last observed width perturbed ±1px');axs[2].grid(axis='y',alpha=.2);fig.suptitle('Fixed assumption scenarios — no grid setting selected by performance',fontsize=12);fig.tight_layout(rect=(0,0,1,.92));fig.savefig(out/'F02_uncertainty_sensitivity.png',dpi=150);plt.close(fig)
    assert all(sha(Path(p))==h for p,h in protected.items());(out/'receipt.json').write_text(json.dumps({'completed_utc':datetime.now(timezone.utc).isoformat(),'elapsed_s':time.time()-began,'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).parents[1],text=True).strip(),'source_inputs':str(a.inputs),'protected_mask_and_input_hashes':protected,'masks_unchanged':True,'neural_training_or_inference':False,'state_estimation_and_one_step_forecasts':True,'parameter_optimization':False,'MD01_touched':False,'prefix_sanity_checks_passed':True},indent=2));print(json.dumps(results,indent=2))


if __name__=='__main__':main()
