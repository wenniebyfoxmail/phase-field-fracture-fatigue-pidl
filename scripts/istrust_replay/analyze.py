"""Independently recompute archived forecast errors and render the six-fold comparison."""
from pathlib import Path
import argparse,csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw-root',type=Path,required=True);ap.add_argument('--config',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    c=json.loads(a.config.read_text());pre=json.loads((a.raw_root/'preprocessing_audit.json').read_text())
    if not json.loads((a.raw_root/'controller_completion.json').read_text())['complete']:raise ValueError('Incomplete producer batch')
    allmetrics=[];primary_rows={};run_totals=[]
    for run_id,seed in zip(c['run_ids'],c['seeds']):
        if not json.loads((a.raw_root/'runs'/run_id/'completion.json').read_text())['complete']:raise ValueError('Incomplete seed Run')
        reported=json.loads((a.raw_root/'runs'/run_id/'metrics.json').read_text());total=0;count=0
        for fold in range(1,7):
            for split in ['training_eval','testing']:
                stem=f'fold{fold}_{split}_mc40';root=a.raw_root/'runs'/run_id
                with (root/f'{stem}.csv').open() as f:rows=list(csv.DictReader(f))
                values=np.load(root/f'{stem}_draws.npz')['draws_s']
                expected=c['expected_test_windows' if split=='testing' else 'expected_train_windows'][fold-1]
                if values.shape!=(expected,40) or len(rows)!=expected or not np.isfinite(values).all():raise ValueError('Shape/completeness failure')
                ids=[(r['specimen'],r['camera'],r['window']) for r in rows]
                if len(set(ids))!=expected:raise ValueError('Duplicate forecast key')
                if split=='testing' and {r['specimen'] for r in rows}!={c['fold_test_specimens'][fold-1]}:raise ValueError('Incorrect held-out specimen')
                maximum=pre[fold-1]['stored']['max_train']
                targets=np.array([float(r['target_s']) for r in rows],dtype=np.float32)/np.float32(maximum)
                # Float64 recomputation is intentionally independent of the producer's float32 batch reduction.
                means=values.astype(np.float64).mean(axis=1)
                errors=np.abs(means/maximum-targets.astype(np.float64))
                metric=float(errors.mean())
                ref=next(r for r in reported if r['fold']==fold and r['split']==split and r['draws']==40)
                if abs(metric-ref['normalized_mae'])>1e-6:raise ValueError('Archived draws do not reproduce reported MAE')
                np.testing.assert_allclose(means,[float(r['predicted_mean_s']) for r in rows],atol=.001,rtol=0)
                entry={'run_id':run_id,'seed':seed,'fold':fold,'split':split,'n':expected,'normalized_mae':metric,
                       'paper_mae':c['paper_test_mae'][fold-1] if split=='testing' else None}
                allmetrics.append(entry)
                if split=='testing':
                    total+=float(errors.sum());count+=expected
                    if run_id==c['run_ids'][0]:primary_rows[fold]=rows
        if count!=634:raise ValueError('Incorrect pooled test count')
        run_totals.append({'run_id':run_id,'seed':seed,'weighted_test_mae':total/count})
    value=run_totals[0]['weighted_test_mae']
    result={'primary':run_totals[0],'publication_rounded_total':.26,'rounding_bin':[.255,.265],
            'primary_display_precision_match':.255<=value<.265,'runs':run_totals,'fold_metrics':allmetrics,
            'mc_seed_range':[min(r['weighted_test_mae'] for r in run_totals),max(r['weighted_test_mae'] for r in run_totals)],
            'training_steps':0,'observation_uncertainty_testing':False,'normalization_audit':pre}
    (a.out/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    with (a.out/'fold_comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(allmetrics[0]));w.writeheader();w.writerows(allmetrics)
    fig,ax=plt.subplots(figsize=(8,4.8))
    x=np.arange(1,7);paper=np.array(c['paper_test_mae'])
    ax.errorbar(x,paper,yerr=.005,fmt='s',color='#6f6f6f',alpha=.45,capsize=9,lw=7,label='Published MAE and two-decimal rounding bin')
    colors=['#d76b27','#16868b','#6475a5']
    for i,(run_id,seed) in enumerate(zip(c['run_ids'],c['seeds'])):
        vals=[r['normalized_mae'] for r in allmetrics if r['run_id']==run_id and r['split']=='testing']
        ax.scatter(x+(i-1)*.10,vals,s=50 if i==0 else 30,color=colors[i],zorder=4,label=f'Replay seed {seed}'+(' (primary)' if i==0 else ''))
    ax.set_xticks(x,[f'{i}\n{s}' for i,s in enumerate(c['fold_test_specimens'],1)]);ax.set_ylim(bottom=0)
    ax.set_ylabel('Normalized held-out MAE');ax.set_xlabel('Fold and physical test specimen');ax.grid(axis='y',alpha=.2)
    ax.set_title(f'Sixth-epoch ISTRUST replay: pooled primary MAE {value:.4f}\nPublished pooled MAE 0.26; six physical test trajectories')
    ax.legend(frameon=False,fontsize=8);fig.tight_layout();fig.savefig(a.out/'published_vs_replay.png',dpi=180);plt.close(fig)
    fig,axs=plt.subplots(3,2,figsize=(12,11))
    for fold,ax in enumerate(axs.flat,1):
        rows=primary_rows[fold]
        for view,color in [(0,'#16868b'),(1,'#d76b27')]:
            rs=[r for r in rows if int(r['camera'])==view]
            t=np.array([float(r['elapsed_target_s']) for r in rs]);t-=t[0]
            target=[float(r['scored_target_s']) for r in rs];pred=[float(r['predicted_mean_s']) for r in rs]
            ax.plot(t,target,'--',color='#222222',alpha=.75,label='True target RUL' if view==0 else None)
            ax.plot(t,pred,color=color,lw=1.3,label=f'Camera {view} mean')
            low=np.array([float(r['author_band_low_s']) for r in rs]);high=np.array([float(r['author_band_high_s']) for r in rs])
            ax.fill_between(t,low,high,color=color,alpha=.12)
        ax.set_title(f'Fold {fold}: {c["fold_test_specimens"][fold-1]}');ax.set_xlabel('Time since first scored target (s)');ax.set_ylabel('RUL (s)');ax.grid(alpha=.15)
    axs.flat[0].legend(frameon=False,fontsize=8)
    fig.suptitle('Primary seeded replay: all scored targets, both camera views\nShading reproduces original SD-bootstrap bands; it is not a calibrated prediction interval',fontsize=12)
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(a.out/'six_specimen_rul.png',dpi=180);plt.close(fig)
    print(json.dumps({k:v for k,v in result.items() if k not in ['fold_metrics','normalization_audit']},indent=2))


if __name__=='__main__':main()
