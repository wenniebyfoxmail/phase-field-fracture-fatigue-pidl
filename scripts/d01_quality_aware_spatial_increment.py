"""Frozen D01 quality-location ablation; saved numeric tables only, no fitting."""
import csv, json, hashlib, time, socket, subprocess
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
BASE = ROOT/'local_archive/experiments/S03-E016-D01'
GEO = BASE/'geometry_state_audit_20261018'
OLD = BASE/'spatial_baselines_20261019'
PREP = BASE/'spatial_baseline_preparation_20261019'
OUT = BASE/'quality_aware_spatial_increment_20261019'
METHODS = ['persistence', 'load_secant', 'quality_aware_increment', 'matched_budget_uniform_damping']
LABELS = ['P: persistence', 'L: load secant', 'Q: quality location', 'U: uniform damping']
COLORS = ['#777777', '#0072b2', '#009e73', '#d55e00']

def read(p):
    with p.open() as f: return list(csv.DictReader(f))
def write(p, rows):
    with p.open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p, value): p.write_text(json.dumps(value, indent=2))

def increments(previous, origin, u_previous, u_origin, weight, ratio):
    """Inputs contain no target observation or target quality."""
    d = (origin-previous)*ratio
    defined = np.isfinite(u_previous) & np.isfinite(u_origin)
    g = np.zeros_like(d)
    g[defined] = 1-np.maximum(u_previous[defined], u_origin[defined])
    assert np.all((g >= 0) & (g <= 1))
    denominator = float(weight@np.abs(d))
    gbar = float((weight@(np.abs(d)*g))/denominator) if denominator else 0.
    return origin+g*d, origin+gbar*d, d, g, gbar, ~defined

def sanity():
    a = np.array([.02,.03]); b = np.array([.04,.01]); w = np.array([1.,3.])
    for u in [0.,.3,1.]:
        q,v,d,g,gb,_ = increments(a,b,np.full(2,u),np.full(2,u),w,.5)
        assert np.allclose(q,v) and np.allclose(q,b+(1-u)*(b-a)*.5)
    q,v,d,g,gb,missing = increments(a,b,np.array([np.nan,.2]),np.array([.1,.8]),w,.5)
    assert g[0] == 0 and missing[0] and q[0] == b[0]
    assert abs(w@np.abs(q-b)-w@np.abs(v-b)) < 1e-15
    q,v,*_ = increments(b,b,np.zeros(2),np.zeros(2),w,.5)
    assert np.array_equal(q,b) and np.array_equal(v,b)
    # Replacing future values cannot affect a function with prefix-only arguments.
    future = np.array([99.,99.]); before = increments(a,b,np.zeros(2),np.zeros(2),w,.5)[0]
    future[:] = -99
    assert np.array_equal(before,increments(a,b,np.zeros(2),np.zeros(2),w,.5)[0])

def main():
    sanity(); started = datetime.now(timezone.utc).isoformat(); tic = time.time()
    protected = json.loads((OLD/'receipt.json').read_text())['protected_input_hashes']
    for p in [OLD/'predictions_by_cell.csv', OLD/'per_target_errors.csv', OLD/'summary.json', OLD/'NEXT_DESIGN_DRAFT.md']:
        protected[str(p)] = sha(p)
    assert all(sha(p) == h for p,h in protected.items())
    OUT.mkdir(exist_ok=False)
    dump(OUT/'execution_contract.json', {
        'authorization':'User 2026-10-19 explicitly authorized the exact draft four-arm comparison',
        'stage':'exploratory C3 controlled-experiment development replay',
        'draft':str(OLD/'NEXT_DESIGN_DRAFT.md'), 'source_hashes':protected,
        'formulas':{'d':'(origin-previous)*delta_load_next/delta_load_previous',
                    'g':'1-max(u_previous,u_origin); either undefined => 0',
                    'Q':'origin+g*d', 'gbar':'sum(C*abs(d)*g)/sum(C*abs(d)); zero denominator => 0',
                    'U':'origin+gbar*d'},
        'score':'100*sum(C*abs(pred-target))/sum(C), then within-beam primary mean, then equal three-beam mean',
        'units':'percentage points (pp); reference pixels for increment budget',
        'scope':'14 exposed stages, 8 primary targets and 3 separate warm-ups; numeric tables only; no tuning, masks, images, training, new holdouts or MD03 work',
        'reference':'frozen mask coverage, biased observation rather than independent physical truth',
        'uncertainty':'deterministic existing eligibility labels, not calibrated probabilities; target labels retrospective only',
        'support':'existing retrospective all-selected-stage common support; cells not independent beams',
        'out_of_range':'retain raw values without clipping',
        'cached_arms':'copy P/L old CSV strings exactly; do not rerun old forecasts'})
    meta = {r['image']:r for r in read(GEO/'geometry_time_series.csv')}
    grid = read(GEO/'fixed_grid_coverage.csv'); pairs = read(PREP/'allowed_prefix_target_pairs.csv')
    y,u,C = {},{},{}
    for image in meta:
        rs = sorted((r for r in grid if r['image']==image),key=lambda r:int(r['cell']))
        assert [int(r['cell']) for r in rs] == list(range(16))
        y[image] = np.array([float(r['coverage_fraction']) for r in rs])
        u[image] = np.array([float(r['uncertain_mask_share']) if r['uncertain_mask_share'] else np.nan for r in rs])
        C[image] = np.array([float(r['support_reference_px2']) for r in rs])
        assert np.all(C[image]>0)
    cached = read(OLD/'predictions_by_cell.csv'); cells = [dict(r) for r in cached]
    pertarget, weights, budgets, fields = [],[],[],[]
    for pair in pairs:
        origin,target = pair['origin_image'],pair['target_image']; prefix = pair['allowed_prefix_images'].split('|')
        loads = [float(x) for x in pair['allowed_prefix_loads_kN'].split('|')]
        assert origin == prefix[-1] and target not in prefix
        c = C[origin]; assert all(np.array_equal(C[z],c) for z in prefix+[target])
        assert all(float(meta[z]['load_kN']) == l for z,l in zip(prefix,loads))
        predictions = {}
        for method in METHODS[:2]:
            rs = sorted((r for r in cached if r['target']==target and r['method']==method),key=lambda r:int(r['cell']))
            assert len(rs)==16 and all(r['allowed_prefix_images']==pair['allowed_prefix_images'] for r in rs)
            predictions[method] = np.array([float(r['prediction']) for r in rs])
        if len(prefix)==1:
            q = y[origin].copy(); uniform = q.copy(); d = np.zeros(16); g = np.zeros(16); gb = 0.; missing = np.zeros(16,dtype=bool)
        else:
            ratio = (float(pair['specified_next_nominal_load_kN'])-loads[-1])/(loads[-1]-loads[-2])
            q,uniform,d,g,gb,missing = increments(y[prefix[-2]],y[origin],u[prefix[-2]],u[origin],c,ratio)
        predictions[METHODS[2]] = q; predictions[METHODS[3]] = uniform
        bq,bu = float(c@np.abs(q-y[origin])),float(c@np.abs(uniform-y[origin]))
        assert abs(bq-bu)<1e-8
        budgets.append({'beam':pair['beam'],'origin':origin,'target':target,'score_role':pair['score_role'],
                        'gbar':gb,'raw_increment_budget_ref_px2':float(c@np.abs(d)),
                        'quality_budget_ref_px2':bq,'uniform_budget_ref_px2':bu,'budget_abs_difference':abs(bq-bu),
                        'undefined_quality_fallback_cells':int(missing.sum()),'warmup_fallback':len(prefix)==1})
        for k in range(16):
            weights.append({'beam':pair['beam'],'origin':origin,'target':target,'score_role':pair['score_role'],'cell':k,
                            'previous':prefix[-2] if len(prefix)>1 else '',
                            'previous_uncertain_share':u[prefix[-2]][k] if len(prefix)>1 and np.isfinite(u[prefix[-2]][k]) else '',
                            'origin_uncertain_share':u[origin][k] if np.isfinite(u[origin][k]) else '',
                            'raw_increment':float(d[k]),'g':float(g[k]),'gbar':gb,'undefined_g_fallback':bool(missing[k]),
                            'warmup_fallback':len(prefix)==1,'support_ref_px2':float(c[k])})
        # Only after prefix-only predictions are formed, access target for scoring.
        actual = y[target]
        template = next(r for r in cached if r['target']==target)
        for method,pred in predictions.items():
            error = pred-actual
            pertarget.append({'beam':int(pair['beam']),'origin':origin,'target':target,
                'origin_load_kN':loads[-1],'target_load_kN':float(pair['specified_next_nominal_load_kN']),
                'history_n':len(prefix),'score_role':pair['score_role'],'method':method,
                'spatial_error_pp':100*float(c@np.abs(error)/c.sum()),
                'pred_total_coverage_percent':100*float(c@pred/c.sum()),
                'observed_total_coverage_percent':100*float(c@actual/c.sum()),
                'total_area_signed_error_ref_px2':float(c@error),
                'total_area_absolute_error_ref_px2':abs(float(c@error)),
                'out_of_range_cells':int(((pred<0)|(pred>1)).sum()),
                'origin_flags':meta[origin]['uncertainty_flags'],
                'target_flags_retrospective_only':meta[target]['uncertainty_flags']})
            if method in METHODS[2:]:
                for k in range(16):
                    r = dict(template)
                    r.update(method=method,cell=k,support_ref_px2=int(c[k]),origin_coverage=float(y[origin][k]),
                             target_coverage=float(actual[k]),prediction=float(pred[k]),signed_error=float(error[k]),
                             absolute_error=float(abs(error[k])),out_of_range_prediction=bool(pred[k]<0 or pred[k]>1),
                             origin_uncertain_mask_share='' if not np.isfinite(u[origin][k]) else float(u[origin][k]),
                             target_uncertain_mask_share_retrospective_only='' if not np.isfinite(u[target][k]) else float(u[target][k]))
                    cells.append(r)
        if len(prefix)==1: assert all(np.array_equal(q,p) for p in predictions.values())
        fields.append({'pair':pair,'actual':actual,'g':g,**predictions})
    assert len(cells)==704 and len(pertarget)==44
    assert cells[:352]==cached
    write(OUT/'predictions_by_cell.csv',cells); write(OUT/'per_target_errors.csv',pertarget)
    write(OUT/'quality_weights_by_cell.csv',weights);write(OUT/'increment_budgets.csv',budgets)
    write(OUT/'warmup_errors.csv',[r for r in pertarget if r['score_role']=='warmup'])
    summaries=[]; scores={}
    for method in METHODS:
        vals=[]
        for beam in [4,5,6]:
            rs=[r for r in pertarget if r['method']==method and r['beam']==beam and r['score_role']=='primary']
            value=float(np.mean([r['spatial_error_pp'] for r in rs])); vals.append(value)
            summaries.append({'beam':beam,'method':method,'primary_targets':len(rs),'mean_spatial_error_pp':value,
                              'out_of_range_cells':sum(r['out_of_range_cells'] for r in rs)})
        scores[method]=float(np.mean(vals))
        summaries.append({'beam':'equal_beam_mean','method':method,'primary_targets':8,'mean_spatial_error_pp':scores[method],
                          'out_of_range_cells':sum(r['out_of_range_cells'] for r in pertarget if r['method']==method and r['score_role']=='primary')})
    write(OUT/'per_beam_summary.csv',summaries)
    paired=[]
    for pair in pairs:
        rs={r['method']:r for r in pertarget if r['target']==pair['target_image']}
        paired.append({'beam':pair['beam'],'origin':pair['origin_image'],'target':pair['target_image'],'score_role':pair['score_role'],
                       **{m+'_error_pp':rs[m]['spatial_error_pp'] for m in METHODS},
                       'Q_minus_U_pp':rs[METHODS[2]]['spatial_error_pp']-rs[METHODS[3]]['spatial_error_pp']})
    write(OUT/'paired_target_errors.csv',paired)
    # CSV-derived checks do not refit or rerun any predictor.
    for r in pertarget:
        z=[x for x in cells if x['target']==r['target'] and x['method']==r['method']]
        check=100*sum(float(x['support_ref_px2'])*float(x['absolute_error']) for x in z)/sum(float(x['support_ref_px2']) for x in z)
        assert abs(check-r['spatial_error_pp'])<1e-12
    oldscores=json.loads((OLD/'summary.json').read_text())['primary_equal_beam_error_pp']
    assert all(abs(scores[m]-oldscores[m])<1e-15 for m in METHODS[:2])
    result={'primary_equal_beam_error_pp':scores,'per_beam':summaries,
            'Q_relative_reduction_vs_U_percent':100*(1-scores[METHODS[2]]/scores[METHODS[3]]),
            'Q_relative_reduction_vs_L_percent':100*(1-scores[METHODS[2]]/scores[METHODS[1]]),
            'Q_relative_reduction_vs_P_percent':100*(1-scores[METHODS[2]]/scores[METHODS[0]]),
            'Q_vs_U_primary_wins':sum(r['Q_minus_U_pp'] < -1e-12 for r in paired if r['score_role']=='primary'),
            'Q_vs_U_primary_losses':sum(r['Q_minus_U_pp'] > 1e-12 for r in paired if r['score_role']=='primary'),
            'max_budget_abs_difference_ref_px2':max(r['budget_abs_difference'] for r in budgets),
            'undefined_quality_fallback_primary_cells':sum(r['undefined_quality_fallback_cells'] for r in budgets if r['score_role']=='primary'),
            'development_only':True,'reference':'saved frozen mask observations, not physical truth'}
    dump(OUT/'summary.json',result)
    plots(fields, pertarget, summaries, paired)
    assert all(sha(p)==h for p,h in protected.items())
    dump(OUT/'validation.json',{'cells':704,'primary_targets':8,'warmup_targets':3,'warmup_rows':12,
        'cached_P_L_rows_exactly_preserved':cells[:352]==cached,'equal_budget_each_target':True,
        'source_hashes_unchanged':True,'all_spatial_scores_independently_recomputed':True,
        'constant_g_zero_g_one_g_undefined_g_zero_increment_unequal_load_checks':True,
        'no_target_input_in_prediction_function':True,'raw_out_of_range_values_retained':True,
        'no_images_masks_new_holdouts_training_MD03_reads':True})
    dump(OUT/'receipt.json',{'started_utc':started,'completed_utc':datetime.now(timezone.utc).isoformat(),
        'runtime_s':time.time()-tic,'host':socket.gethostname(),'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=Path(__file__).parent.parent,text=True).strip(),
        'script_sha256':sha(__file__),'protected_input_hashes':protected,'execution':'one deterministic comparison from saved numeric tables; no tuning'})
    print(json.dumps(result,indent=2))

def plots(fields, rows, summaries, paired):
    fig,axs=plt.subplots(1,2,figsize=(12,4.5))
    for j,(m,label,color) in enumerate(zip(METHODS,LABELS,COLORS)):
        z=[next(r['mean_spatial_error_pp'] for r in summaries if r['beam']==b and r['method']==m) for b in [4,5,6,'equal_beam_mean']]
        axs[0].plot(np.arange(4),z,'o-',label=label,color=color,linewidth=1.5)
    axs[0].set(xticks=range(4),xticklabels=['Beam 4 (2)','Beam 5 (4)','Beam 6 (2)','Equal beam'],ylabel='Spatial weighted L1 (pp)',title='Eight primary targets; lower is better')
    axs[0].legend(fontsize=8); z=[r for r in paired if r['score_role']=='primary']
    axs[1].barh(range(8),[r['Q_minus_U_pp'] for r in z],color=['#009e73' if r['Q_minus_U_pp']<0 else '#d55e00' for r in z])
    axs[1].set(yticks=range(8),yticklabels=[r['target'] for r in z],xlabel='Q error - U error (pp)',title='Same increment budget: spatial quality allocation')
    axs[1].axvline(0,color='black',lw=.7);axs[1].invert_yaxis()
    for ax in axs:ax.grid(alpha=.15)
    fig.tight_layout();fig.savefig(OUT/'F01_quality_vs_uniform.png',dpi=170);plt.close(fig)
    values=np.concatenate([f[k] for f in fields for k in ['actual']+METHODS])*100
    vmin,vmax=min(0,float(values.min())),float(values.max())
    emax=max(float(np.max(np.abs(f[m]-f['actual'])))*100 for f in fields for m in METHODS)
    def maps(subset, keys, error, name):
        n=len(keys);fig,axs=plt.subplots(len(subset),n,figsize=(2.1*n+1.1,1.75*len(subset)),squeeze=False)
        for i,f in enumerate(subset):
            for j,k in enumerate(keys):
                a=(f[k]-f['actual'] if error else f[k])*100
                axs[i,j].imshow(a.reshape(4,4),cmap='RdBu_r' if error else 'viridis',vmin=-emax if error else vmin,vmax=emax if error else vmax)
                axs[i,j].set_xticks([]);axs[i,j].set_yticks([])
                if i==0:axs[i,j].set_title('Observed' if k=='actual' else LABELS[METHODS.index(k)],fontsize=9)
                if j==0:
                    p=f['pair'];axs[i,j].set_ylabel(f"B{p['beam']}\n{float(p['origin_load_kN']):g} → {float(p['specified_next_nominal_load_kN']):g} kN",fontsize=9)
        fig.subplots_adjust(left=.09,right=.86,bottom=.025,top=.84 if len(subset)==3 else .94,wspace=.06,hspace=.14)
        cax=fig.add_axes([.9,.28,.018,.42]);fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(-emax if error else vmin,emax if error else vmax),cmap='RdBu_r' if error else 'viridis'),cax=cax,label='Prediction - observed (pp)' if error else 'Cell coverage (%)')
        fig.suptitle(('All signed spatial errors' if error else 'All spatial predictions')+' | same fixed 4×4 cells, shared scales\n'+('Separate warm-ups; all four arms coincide' if len(subset)==3 else 'Eight exposed primary targets; no clipping'),fontsize=10)
        fig.savefig(OUT/(name+'.png'),dpi=170);plt.close(fig)
    primary=[f for f in fields if f['pair']['score_role']=='primary']; warm=[f for f in fields if f['pair']['score_role']=='warmup']
    maps(primary,['actual']+METHODS,False,'F02_all_primary_predictions')
    maps(primary,METHODS,True,'F03_all_primary_spatial_errors')
    maps(warm,['actual']+METHODS,False,'F04_separate_warmup_predictions')
    maps(warm,METHODS,True,'F05_separate_warmup_spatial_errors')

if __name__=='__main__':main()
