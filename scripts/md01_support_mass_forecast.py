"""E043: no mask edits; persist detected support, extrapolate conditional row mass."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone

import matplotlib.pyplot as plt
import numpy as np

from md01_cached_stage_forecast import (ROOT, WORK, CACHE, REPAIR, STAGES, WINDOWS,
                                        ARMS, forecast, sha, save, table)

OLD = ROOT/'local_archive/experiments/S03-E042-MD01/runs/S03-E042-MD01-R001'
METHODS = ('persistence', 'secant', 'support_hold')
COLORS = ('#E69F00', '#0072B2', '#009E73')
LABELS = ('Persistence', 'Area secant', 'Support-hold + mass secant')


def observe(mask):
    if mask.ndim != 2 or mask.dtype != bool:
        raise ValueError('Expected unchanged 2D boolean mask')
    row = mask.sum(axis=1)
    occupied = row > 0
    area = int(row.sum())
    length = int(occupied.sum())
    mass = float(row[occupied].mean()) if length else None
    return dict(area=area, support=length, mass=mass,
                occupied_fraction=length/mask.shape[0],
                p10=float(np.percentile(row[occupied],10)) if length else None,
                p50=float(np.percentile(row[occupied],50)) if length else None,
                p90=float(np.percentile(row[occupied],90)) if length else None), row


def predict(a, b, stage_a, stage_b, target_stage, width):
    pred = forecast(stage_a, stage_b, target_stage, a['area'], b['area'])
    q = (target_stage-stage_b)/(stage_b-stage_a)
    raw = None if a['mass'] is None or b['mass'] is None else b['mass']+q*(b['mass']-a['mass'])
    mass = None if raw is None else float(np.clip(raw,0,width))
    return dict(**pred, support_hold=None if mass is None else float(b['support']*mass),
                predicted_support=b['support'],raw_predicted_mass=raw,predicted_mass=mass,
                mass_clipped=bool(raw is not None and raw!=mass),
                reason='empty_history_support' if raw is None else 'available')


def tests():
    a,_=observe(np.zeros((8,10),bool));assert a['support']==0 and a['mass'] is None
    m=np.zeros((8,10),bool);m[:4,:2]=True;b,row=observe(m)
    assert b['area']==8 and b['support']==4 and b['mass']==2 and row.sum()==8
    n=np.zeros_like(m);n[:2,:4]=True;c,_=observe(n)
    assert c['area']==b['area'] and c['support']==2 and c['mass']==4
    p=predict(b,c,18,19,21,10)
    assert p['persistence']==8 and p['secant']==8 and p['support_hold']==16
    assert p['predicted_support']==2 and p['predicted_mass']==8
    assert predict(a,c,18,19,21,10)['support_hold'] is None
    assert predict(b,c,1,2,20,10)['predicted_mass']==10
    assert predict(c,b,1,2,20,10)['predicted_mass']==0
    same=predict(b,b,18,19,21,10);assert same['support_hold']==same['secant']==8
    # With constant support, identity reduces exactly to area secant, before cap.
    d=dict(area=12,support=4,mass=3.0)
    assert predict(b,d,19,21,22,10)['support_hold']==predict(b,d,19,21,22,10)['secant']==14
    print('Synthetic factorisation, missingness, stage gaps, caps and constant-support tests passed.')


def run(out):
    start,cpu=time.monotonic(),time.process_time()
    out.mkdir(parents=True,exist_ok=False)
    receipt=dict(execution='running',host=socket.gethostname(),pid=os.getpid(),runtime=sys.executable,
                 command=sys.argv,started_utc=datetime.now(timezone.utc).isoformat(),
                 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),
                 dirty=subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).splitlines())
    save(out/'run_start_receipt.json',receipt)
    inputs={}
    def touch(p):
        p=Path(p);inputs[str(p)]=sha(p);return p
    def budget():
        if max(time.monotonic()-start,time.process_time()-cpu)>60:
            raise TimeoutError('60s analysis budget')
    try:
        for p in (Path(__file__),WORK/'scripts/md01_cached_stage_forecast.py',
                  WORK/'scripts/md01_frame_geometry.py',WORK/'scripts/d01_crack_profile_diagnostic.py',
                  WORK/'docs/research/S03/S03-E043-MD01/experiment.md'):
            touch(p)
        # Protect every E042 file; no rewrite of its scores or documentation.
        for p in sorted(OLD.rglob('*')):
            if p.is_file():touch(p)
        old_manifest=json.loads((OLD/'input_manifest.json').read_text())
        for p,h in old_manifest.items():
            assert sha(p)==h, 'Prior input identity changed: '+p
        lock=json.loads(touch(WORK/'docs/research/S03/S03-E037-MD01/source_lock.json').read_text())
        for p,h in lock['protected_old_hashes'].items():
            assert sha(p)==h;touch(p)
        roi,band=lock['roi_xyxy'],lock['forecast_roi_xyxy']
        x0,y0,x1,y1=np.array(band)-np.array([roi[0],roi[1],roi[0],roi[1]])
        width,height=int(x1-x0),int(y1-y0)
        sl=np.s_[y0:y1,x0:x1]
        rows=[];data={};profiles={};default19=None
        for arm in ARMS:
            data[arm]={}
            for stage in STAGES:
                p=touch(CACHE/f'step{stage}'/arm/'geometry_arrays.npz')
                with np.load(p) as z:
                    mask=z['mask'][sl].copy();excluded=z['excluded'][sl].copy()
                assert not excluded.any()
                values,profile=observe(mask)
                cached=json.loads(touch(CACHE/f'step{stage}'/arm/'metrics.json').read_text())['common']
                assert values['area']==cached['area_px2']
                assert abs(values['area']-values['support']*values['mass'])<1e-9 if values['mass'] is not None else values['area']==0
                rows.append(dict(arm=arm,stage=stage,**values))
                data[arm][stage]=values
                profiles[f'{arm}_step{stage}']=profile
                if arm=='v1' and stage==19:default19=mask
                budget()
        with np.load(touch(REPAIR)) as z:assert np.array_equal(z['new_mask'][sl],default19)
        predictions=[]
        for arm in ARMS:
            for a,b,t in WINDOWS:
                predictions.append(dict(arm=arm,history_a=a,origin=b,target=t,horizon=t-b,
                    **predict(data[arm][a],data[arm][b],a,b,t,width)))
        save(out/'predictions_before_scoring.json',predictions)
        scored=[]
        previous={(r['arm'],int(r['history_a']),int(r['origin']),int(r['target'])):r
                  for r in json.loads((OLD/'summary.json').read_text())['nominal']}
        for p in predictions:
            target=data[p['arm']][p['target']]
            r=dict(**p,observed_area=target['area'],observed_support=target['support'],observed_mass=target['mass'])
            for m in METHODS:r[m+'_ae']=None if p[m] is None else abs(p[m]-target['area'])
            r['gain_vs_persistence']=None if p['support_hold'] is None else r['persistence_ae']-r['support_hold_ae']
            r['gain_vs_secant']=None if p['support_hold'] is None else r['secant_ae']-r['support_hold_ae']
            r['support_ae']=abs(p['predicted_support']-target['support'])
            r['mass_ae']=None if p['predicted_mass'] is None or target['mass'] is None else abs(p['predicted_mass']-target['mass'])
            if p['arm']=='v1':
                old=previous[(p['arm'],p['history_a'],p['origin'],p['target'])]
                for k in ('persistence','secant','persistence_ae','secant_ae'):assert r[k]==old[k]
            scored.append(r)
        nominal=[r for r in scored if r['arm']=='v1']
        sensitivity=[]
        for arm in ARMS:
            rr=[r for r in scored if r['arm']==arm]
            s=dict(arm=arm,calculable=sum(r['support_hold'] is not None for r in rr),total=len(rr))
            for m in METHODS:
                valid=[r[m+'_ae'] for r in rr if r['support_hold'] is not None]
                s[m+'_mae']=float(np.mean(valid)) if valid else None
            s['gain_vs_persistence']=s['persistence_mae']-s['support_hold_mae'] if s['calculable'] else None
            s['gain_vs_secant']=s['secant_mae']-s['support_hold_mae'] if s['calculable'] else None
            sensitivity.append(s)
        result=dict(evidence_role='one development-exposed trajectory; three overlapping windows',
                    new_definition='A=L*M; L=occupied image rows, M=conditional candidate row-pixel count',
                    rule='persist L; stage-secant M clipped to image width; multiply',
                    shadow_texture_false_positives='not corrected or quantified; both L and M may be biased',
                    band_xyxy=band,band_width=width,band_height=height,nominal=nominal,
                    nominal_mae=sensitivity[0],sensitivity=sensitivity,
                    default_observations=[r for r in rows if r['arm']=='v1'],
                    calculable=f"{sensitivity[0]['calculable']}/3",mass_caps_applied=sum(r['mass_clipped'] for r in predictions),
                    settings_better_than_persistence=sum(s['gain_vs_persistence']>0 for s in sensitivity),
                    settings_better_than_secant=sum(s['gain_vs_secant']>0 for s in sensitivity),
                    frozen_E041_common_identical=True,previous_E042_nominal_exact=True,
                    original_usage_stop_rule='revoked by direct user 2026-10-18')
        table(out/'observations.csv',rows);table(out/'all_forecasts.csv',scored)
        table(out/'sensitivity.csv',sensitivity)
        np.savez_compressed(out/'row_profiles.npz',**profiles)
        save(out/'summary.json',result)
        budget()
        assert all(sha(p)==h for p,h in inputs.items())
        save(out/'input_manifest.json',inputs)
        receipt.update(execution='succeeded',retrieval='verified_local',input_hashes_verified=len(inputs),
                       old_E042_files_protected=sum(p.is_file() for p in OLD.rglob('*')))
        print(json.dumps(result,indent=2))
    except Exception as e:
        receipt.update(execution='failed',error=repr(e));raise
    finally:
        receipt.update(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,
                       ended_utc=datetime.now(timezone.utc).isoformat())
        save(out/'run_receipt.json',receipt)


def plot(source,out):
    out.mkdir(parents=True,exist_ok=False)
    r=json.loads((source/'summary.json').read_text());obs=r['default_observations']
    plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
    provenance=(f'\n## Data provenance\nE043 numeric R001: {source}. Plot script: scripts/md01_support_mass_forecast.py. '
                'Frozen E038 R001 masks in E037 image band; E041 Step19 common band identical. No new extraction. '
                'All5 stages and3 fixed overlapping windows, same development-exposed MD01 trajectory.\n')
    boundary=('\n## Limitations and claim boundary\nDetected support is not true crack length/recall; conditional row mass is not '
              'normal width, EDT or half-depth width. Shadows, pores and texture remain in masks and can change both components. '
              'No physical aperture, blind validation, independent specimen replication or calibrated uncertainty. '
              'Stage index is not time/cycles/kN. Old half-depth and scores untouched.\n')
    def export(fig,stem,guide):
        fig.savefig(out/f'{stem}.png',dpi=300)
        fig.savefig(out/f'{stem}.pdf');plt.close(fig)
        (out/f'{stem}.md').write_text(guide)
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    stages=[o['stage'] for o in obs]
    axes[0,0].plot(stages,[o['support'] for o in obs],'o-',color='#0072B2')
    axes[0,0].axhline(r['band_height'],color='#777777',ls='--',lw=1,label='Band rows (250)')
    axes[0,0].set(xlabel='Relative stage',ylabel='Occupied image rows (px)',ylim=(0,270),title='A  Detected support L')
    axes[0,0].legend()
    axes[0,1].plot(stages,[o['mass'] for o in obs],'o-',color='#009E73',label='Mean M = A/L')
    axes[0,1].plot(stages,[o['p50'] for o in obs],'s--',color='#999999',label='Median occupied-row count')
    axes[0,1].set(xlabel='Relative stage',ylabel='Candidate pixels per occupied row (px)',title='B  Conditional row-mass proxy (not physical width)')
    axes[0,1].legend()
    colors=['#999999','#CC79A7','#56B4E9','#E69F00','#009E73']
    with np.load(source/'row_profiles.npz') as z:
        for stage,c in zip(STAGES,colors):
            axes[1,0].plot(np.arange(r['band_height'])+r['band_xyxy'][1],z[f'v1_step{stage}'],label=f'Step {stage}',color=c,lw=1)
    axes[1,0].set(xlabel='Native image y (px)',ylabel='Candidate pixel count in row (px)',title='C  Every row retained; zero means no candidate')
    axes[1,0].legend(ncol=3,fontsize=8)
    axes[1,1].plot(stages,[o['area'] for o in obs],'o-',color='#333333',label='Observed area A')
    axes[1,1].plot(stages,[o['support']*o['mass'] for o in obs],'x',color='#009E73',ms=9,label='Exact product L × M')
    axes[1,1].set(xlabel='Relative stage',ylabel='Candidate area (px²)',title='D  Exact factorisation; no missing-row imputation')
    axes[1,1].legend()
    for ax in axes.flat:ax.grid(alpha=.15)
    fig.suptitle('E043 R001 → R002 | Same frozen identification, two distinct observations\nShadow / texture contamination remains; conditional row mass is NOT crack aperture',fontsize=13)
    export(fig,'F01_support_and_row_mass','# How to read: separated support and conditional row mass\n\n## Figure question\nWhat changes in the existing masks are separated before forecasting?\n'+provenance+
           '\n## Visual grammar and panel guide\nA: occupied-row count L, dashed250 fixed image rows. B: mean M=A/L green and median positive row count grey. '
           'C: all250 raw row counts per stage, no smoothing/filling; branches/blobs contribute their total pixels, not enclosing span. '
           'D: candidate area and exact L*M reconstruction. All source native pixels, stages18,19,21,22,23.\n'
           '\n## Key numerical takeaway\n'+json.dumps(obs,indent=2)+boundary)
    fig,axes=plt.subplots(2,2,figsize=(13,8),layout='constrained')
    nominal=r['nominal'];xx=np.arange(3)
    axes[0,0].plot(xx,[p['observed_area'] for p in nominal],'o-',color='#333333',label='Observed mask area',lw=1.5)
    for method,color,label,marker in zip(METHODS,COLORS,LABELS,('s','^','D')):
        axes[0,0].plot(xx,[p[method] for p in nominal],marker+'--',color=color,label=label,lw=1.5)
        axes[0,1].plot(xx,[p[method+'_ae'] for p in nominal],marker+'-',color=color,label=label,lw=1.5)
    labels=['18,19 → 21','19,21 → 22','21,22 → 23']
    for ax in axes[0]:ax.set(xticks=xx,xticklabels=labels,xlabel='History → target stage')
    axes[0,0].set(ylabel='Candidate area (px²)',title='A  All predictions vs unchanged target masks')
    axes[0,1].set(ylabel='Absolute error (px²)',title='B  Every fixed window')
    axes[0,0].legend(fontsize=8);axes[0,1].legend(fontsize=8)
    ax=axes[1,0]
    for i,p in enumerate(nominal):
        ax.scatter([i-.12,i+.12],[p['gain_vs_persistence'],p['gain_vs_secant']],color=['#E69F00','#0072B2'],marker='o')
    ax.scatter([],[],color='#E69F00',label='Gain vs persistence')
    ax.scatter([],[],color='#0072B2',label='Gain vs area secant')
    ax.axhline(0,color='#777777',lw=1)
    ax.set(xticks=xx,xticklabels=labels,ylabel='Baseline AE − separated AE (px²)',title='C  Positive = separated prediction helps')
    ax.legend(fontsize=8)
    ax=axes[1,1];ss=r['sensitivity'];yy=np.arange(len(ss))
    ax.scatter([s['gain_vs_persistence'] for s in ss],yy-.12,color='#E69F00',label='Gain vs persistence')
    ax.scatter([s['gain_vs_secant'] for s in ss],yy+.12,color='#0072B2',label='Gain vs area secant')
    ax.axvline(0,color='#777777',lw=1)
    ax.set(yticks=yy,yticklabels=[s['arm'] for s in ss],xlabel='Baseline MAE − separated MAE (px²)',title='D  All 9 cached definitions; no selection')
    ax.invert_yaxis();ax.legend(fontsize=8)
    for ax in axes.flat:ax.grid(alpha=.15)
    fig.suptitle('E043 R001 → R002 | Hold detected support L; extrapolate conditional mass M\n3 overlapping development windows, not independent validation; masks/shadows unchanged',fontsize=13)
    export(fig,'F02_separated_prediction_comparison','# How to read: separated-input prediction comparison\n\n## Figure question\nDoes fixed support-hold plus mass-secant help relative to frozen area baselines?\n'+provenance+
           '\n## Visual grammar and panel guide\nA: dark target mask area, orange persistence, blue area secant, green separated support-hold+mass-secant. '
           'B: absolute error of each method for every fixed window. C: per-window gain vs persistence/original secant; positive helps. '
           'D: mean gain for all nine already-saved observation settings, same arm through each window; zero line, no best-arm selection. '
           'Coverage is held at origin, mass secant clipped only to fixed horizontal image-size bounds; no fitted coefficients.\n'
           '\n## Key numerical takeaway\n'+json.dumps({'nominal':nominal,'all_settings':ss},indent=2)+boundary)
    save(out/'render_receipt.json',dict(execution='succeeded',source=str(source),
         source_summary_sha256=sha(source/'summary.json'),source_profiles_sha256=sha(source/'row_profiles.npz'),
         renderer_sha256=sha(Path(__file__)),figures=2,new_numeric_analysis=False,
         output_hashes={p.name:sha(p) for p in out.iterdir() if p.is_file()}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['self-test','run','plot'])
    parser.add_argument('--output',type=Path);parser.add_argument('--source',type=Path)
    args=parser.parse_args()
    if args.mode=='self-test':tests()
    elif args.mode=='run':run(args.output)
    else:plot(args.source,args.output)
