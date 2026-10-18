"""E047: metadata-fixed27–29, immutable E045 observer, simple area vs hold."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from md01_cached_stage_forecast import ROOT, WORK, sha, save, table, forecast
from md01_next_stage_validation import select
from md01_geometric_guide_transfer import transfer, tests as guide_tests
from md01_frame_geometry import read_frame, extract
from md01_support_mass_forecast import observe, tests as observation_tests

META=ROOT/'local_archive/open_data/md01_tack_metadata_20261016'
PREVIOUS=ROOT/'local_archive/experiments/S03-E046-MD01/runs'
RAW=ROOT/'local_archive/experiments/S03-E031-MD01/source'
PROTOCOL=WORK/'docs/research/S03/S03-E047-MD01/experiment.md'
WINDOWS=((25,26,27),(26,27,28),(27,28,29))
METHODS=('persistence','secant')
COLORS=('#E69F00','#0072B2')
LABELS=('Persistence','Area trend')


def prediction(history,a,b,t):
    if any(s>b for s in history): raise ValueError('Future observation in predictor history')
    return forecast(a,b,t,history[a]['area'],history[b]['area'])


def tests():
    guide_tests(); observation_tests()
    h={25:dict(area=7361),26:dict(area=9191)}
    assert prediction(h,25,26,27)==dict(persistence=9191.,secant=11021.,raw_secant=11021.)
    try: prediction(h | {27:dict(area=999999)},25,26,27)
    except ValueError: pass
    else: raise AssertionError('Future history guard failed')
    mock=[]
    for s in range(27,30):
        for i in range(3): mock.append(dict(step=str(s),filename=f'{s}_{i}',matches_in_fixed_folder=1))
    assert [r['filename'] for r in select(mock,26)]==['27_0','28_0','29_0']
    print('Metadata selection, causal forecast and unchanged observer tests passed.')


def prepare(out):
    out.mkdir(parents=True,exist_ok=False)
    mapping=META/'step_image_metadata_receipt.json'
    directory=META/'fixed_camera_file_metadata.json'
    chosen=select(json.loads(mapping.read_text())['mapping'],26)
    official={r['filename']:r for r in json.loads(directory.read_text())}
    frames=[]
    for r in chosen:
        item=official[r['filename']]; p=RAW/r['filename']
        digest=item['content_details']['sha256_hash']
        assert p.stat().st_size==item['size'] and sha(p)==digest
        frames.append(dict(stage=int(r['step']),filename=r['filename'],source=str(p),
                           official_id=item['id'],excel_row=r['excel_row'],bytes=item['size'],sha256=digest))
    oldlock=PREVIOUS/'S03-E046-MD01-R000/input_lock.json'
    old=json.loads(oldlock.read_text()); protected=dict(old['protected_inputs'])
    for p in sorted(PREVIOUS.rglob('*')):
        if p.is_file(): protected[str(p)]=sha(p)
    for p in (mapping,directory,PROTOCOL,Path(__file__),WORK/'scripts/md01_next_stage_validation.py'):
        protected[str(p)]=sha(p)
    for f in frames: protected[f['source']]=f['sha256']
    assert all(sha(p)==h for p,h in protected.items())
    selection=dict(protocol='E047-frozen-observer-next3-v1',frames=frames,windows=WINDOWS,
                   selection='first3 complete consecutive after26, smallest linked filename',
                   source_role='already downloaded/exposed E031 sources, not blind targets',
                   roi=old['roi'],band=old['band'],original_support=old['original_support'],
                   initial_stages=[25,26],protected_inputs=protected,
                   prepared_utc=datetime.now(timezone.utc).isoformat(),no_pixels_decoded=True)
    save(out/'selection_lock.json',selection)
    save(out/'prepare_receipt.json',dict(execution='succeeded',selection_sha256=sha(out/'selection_lock.json'),
         protected_files=len(protected),metadata_only=True))
    print(json.dumps(dict(frames=frames,windows=WINDOWS,protected_files=len(protected)),indent=2))


def run(lockpath,out):
    start,cpu=time.monotonic(),time.process_time(); out.mkdir(parents=True,exist_ok=False)
    lock=json.loads(lockpath.read_text()); protected=lock['protected_inputs']
    receipt=dict(execution='running',host=socket.gethostname(),pid=os.getpid(),runtime=sys.executable,
         command=sys.argv,started_utc=datetime.now(timezone.utc).isoformat(),
         commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),
         dirty=subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).splitlines(),
         selection_sha256=sha(lockpath),code_sha256=sha(Path(__file__)))
    save(out/'run_start_receipt.json',receipt)
    def guard():
        assert sha(lockpath)==receipt['selection_sha256']
        assert all(sha(p)==h for p,h in protected.items())
    def budget():
        if max(time.monotonic()-start,time.process_time()-cpu)>90: raise TimeoutError('90s local analysis cap')
    def event(kind,stage,**extra):
        events.append(dict(event=kind,stage=stage,utc=datetime.now(timezone.utc).isoformat(),**extra))
    roi,band=lock['roi'],lock['band']
    x0,y0,x1,y1=np.array(band)-np.array([roi[0],roi[1],roi[0],roi[1]])
    sl=np.s_[y0:y1,x0:x1]
    history={}; observations=[]; rows=[]; events=[]
    try:
        guard(); assert lock['windows']==[list(w) for w in WINDOWS]
        for s in lock['initial_stages']:
            p=PREVIOUS/f'S03-E046-MD01-R001/step{s}/observation_arrays.npz'
            with np.load(p) as z: v,_=observe(z['band_mask'])
            cached=json.loads((p.parent/'observation.json').read_text())
            assert all(v[k]==cached[k] for k in v)
            history[s]=v; observations.append(dict(stage=s,role='exact_E046_history',**v))
        for a,b,t in WINDOWS:
            budget(); case=out/f'W{t}'; case.mkdir()
            pred=prediction(history,a,b,t)
            snapshot=dict(history_a=a,origin=b,target=t,horizon=t-b,
                 available_stages=sorted(history),history={str(s):history[s] for s in (a,b)},
                 predictions=pred,selection_sha256=receipt['selection_sha256'],
                 saved_utc=datetime.now(timezone.utc).isoformat())
            pp=case/'predictions_before_target.json'; save(pp,snapshot); predhash=sha(pp)
            event('prediction_saved',t,sha256=predhash)
            f=next(f for f in lock['frames'] if f['stage']==t)
            event('target_decode_started',t,source=f['source'])
            rgb=read_frame(f,roi)
            support,diag,eligible,path=transfer(rgb,lock['original_support'],roi,band)
            save(case/'guide_before_extraction.json',dict(support=support,diagnostic=diag))
            mask,excluded,_=extract(rgb,support,roi)
            assert not excluded[sl].any() and not (mask & ~eligible).any()
            v,profile=observe(mask[sl])
            assert v['mass'] is None or abs(v['area']-v['support']*v['mass'])<1e-9
            np.savez_compressed(case/'observation_arrays.npz',mask=mask,excluded=excluded,
                 band_mask=mask[sl],band_rgb=rgb[sl],row_mass=profile,guide_path_native=path)
            save(case/'observation.json',dict(stage=t,source=f,measurement=v,diagnostic=diag))
            r=dict(history_a=a,origin=b,target=t,horizon=t-b,observed_area=v['area'],
                 observed_support=v['support'],observed_mass=v['mass'],**pred)
            for m in METHODS: r[m+'_ae']=abs(pred[m]-v['area'])
            r['gain_vs_persistence']=r['persistence_ae']-r['secant_ae']
            r['signed_trend_error']=pred['secant']-v['area']
            r['observed_increment']=v['area']-history[b]['area']
            r['historical_increment']=history[b]['area']-history[a]['area']
            r['empty_candidate_mask']=v['support']==0
            assert sha(pp)==predhash
            save(case/'comparison.json',r); rows.append(r)
            history[t]=v; observations.append(dict(stage=t,role='new_frozen_rule_observation',**v))
            event('target_measured_and_scored',t,prediction_hash_unchanged=True)
        mae={m:float(np.mean([r[m+'_ae'] for r in rows])) for m in METHODS}
        summary=dict(role='one already-exposed MD01 trajectory;3 overlapping next-window queries',
             protocol=lock['protocol'],comparisons=rows,observations=observations,mae=mae,
             relative_gain=1-mae['secant']/mae['persistence'] if mae['persistence'] else None,
             coverage='3/3 paired calculable windows',wins=sum(r['gain_vs_persistence']>0 for r in rows),
             frozen_observer=True,old_halfdepth_masks_scores_unchanged=True,no_new_downloads=True)
        save(out/'summary.json',summary); table(out/'comparisons.csv',rows)
        table(out/'observations.csv',observations); save(out/'event_order.json',events)
        for _,_,t in WINDOWS:
            inds=[i for i,e in enumerate(events) if e['stage']==t]
            assert [events[i]['event'] for i in inds]==['prediction_saved','target_decode_started','target_measured_and_scored']
        guard(); budget()
        receipt.update(execution='succeeded',retrieval='verified_local',protected_files_verified=len(protected),
                       history_cache_exact=2,target_extractions=3,prediction_before_decode_chains=3)
        print(json.dumps(summary,indent=2))
    except Exception as e: receipt.update(execution='failed',error=repr(e)); raise
    finally:
        receipt.update(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,
                       ended_utc=datetime.now(timezone.utc).isoformat()); save(out/'run_receipt.json',receipt)


def plot(source,out):
    out.mkdir(parents=True,exist_ok=False)
    j=json.loads((source/'summary.json').read_text()); rr=j['comparisons']
    obs={o['stage']:o for o in j['observations']}
    plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
    prov=f'\n## Data provenance\nE047 R001 {source}; scripts/md01_frozen_next_three.py. R002 render only. '
    limits=('\n## Limitations and claim boundary\nOne previously exposed MD01 SideA trajectory, overlapping windows, not independent blind validation. '
            'Native band[3900,1700,4600,1950]; stage index not time/kN. Masks can include shadows/pores and omit visible segments. '
            'A pixel²; L occupied image rows and M candidate pixels per occupied row, not normal/half-depth/physical width. '
            'Two-history one-step predictions update after actual target measurement; not autonomous rollout or future spatial masks. '
            'Frozen original stage23 guide/exclusions and E045 transfer/E037 extractor; old scores unchanged.\n')
    def export(fig,stem,guide):
        fig.savefig(out/f'{stem}.png',dpi=250); fig.savefig(out/f'{stem}.pdf'); plt.close(fig)
        (out/f'{stem}.md').write_text(guide)
    fig,axes=plt.subplots(3,2,figsize=(12,7.8),layout='constrained')
    for axs,r in zip(axes,rr):
        s=r['target']
        with np.load(source/f'W{s}/observation_arrays.npz') as z: rgb=z['band_rgb']; mask=z['band_mask']
        axs[0].imshow(rgb); axs[1].imshow(rgb)
        overlay=np.zeros((*mask.shape,4)); overlay[mask]=(.35,.25,.65,.8); axs[1].imshow(overlay)
        axs[0].set_title(f'Step{s} | source')
        mass='NA' if r['observed_mass'] is None else f"{r['observed_mass']:.2f}"
        axs[1].set_title(f"Frozen rule | A={r['observed_area']}, L={r['observed_support']}/250, M={mass}")
        for ax in axs: ax.set_axis_off()
    fig.suptitle('E047 R001 → R002 | All metadata-fixed targets27/28/29\nSame accepted observer, purple candidates; source/mask, not predicted future masks',fontsize=13)
    export(fig,'F01_all_target_observations','# How to read: all3target observations\n\n## Figure question\nWhat entered scoring under the unchanged observer?\n'+prov+
           '\n## Visual grammar and panels\nThree rows27/28/29; left original image band, right same source with purple candidate pixels. '
           'Identical coordinates/native scale, no selected favourable examples. Titles show A/L/M.\n'
           '\n## Key numerical takeaway\n'+json.dumps(j['observations'][2:],indent=2)+limits)
    fig,axes=plt.subplots(2,3,figsize=(13,7.6),layout='constrained')
    vals=[o['area'] for o in obs.values()]+[r[m] for r in rr for m in METHODS]
    pad=max(100,.08*(max(vals)-min(vals))); ylim=(max(0,min(vals)-pad),max(vals)+pad)
    emax=max(100,1.2*max(r[m+'_ae'] for r in rr for m in METHODS))
    for i,r in enumerate(rr):
        a,b,t=r['history_a'],r['origin'],r['target']; ax=axes[0,i]
        ax.plot([a,b],[obs[a]['area'],obs[b]['area']],'o-',color='#333333',lw=1.5,label='Observed history')
        ax.scatter([t],[r['observed_area']],color='#333333',s=65,label='Target observation',zorder=5)
        for m,c,l,marker in zip(METHODS,COLORS,LABELS,('s','^')):
            ax.plot([b,t],[obs[b]['area'],r[m]],'--',color=c,lw=1.5)
            ax.scatter([t],[r[m]],color=c,marker=marker,s=50,label=l)
        ax.axvline(b+.08,color='#bbbbbb',lw=.8)
        ax.set(title=f'{a},{b} → {t} | origin={b}, horizon=1',xticks=[a,b,t],ylim=ylim,
               xlabel='Relative stage',ylabel='Candidate area (px²)')
        if i==0: ax.legend(fontsize=8)
        ax=axes[1,i]; errors=[r[m+'_ae'] for m in METHODS]
        bars=ax.bar([0,1],errors,color=COLORS,width=.55)
        for bar,v in zip(bars,errors): ax.text(bar.get_x()+bar.get_width()/2,v+.015*emax,f'{v:.0f}',ha='center')
        ax.set(title=f"Trend gain vs hold: {r['gain_vs_persistence']:+.0f} px²",xticks=[0,1],
               xticklabels=['Hold','Area trend'],ylim=(0,emax),ylabel='Absolute error (px²)')
    for ax in axes.flat: ax.grid(axis='y',alpha=.15)
    fig.suptitle('E047 | Every fixed window; forecasts saved before each target decode\n3/3 calculable; already-exposed source, no tuning or window replacement',fontsize=13)
    export(fig,'F02_every_window_forecast','# How to read: all3fixed-window forecasts\n\n## Figure question\nDoes simple trend retain an advantage over persistence?\n'+prov+
           '\n## Visual grammar and panels\nColumns25,26→27;26,27→28;27,28→29. Top black history and target, orange persistence, blue area trend. '
           'Shared vertical limits, vertical separator after origin, relative-stage horizontal axis. Bottom absoluteerrors on sharedzero-based scale, '
           'positive gain means trend helps. Every predetermined case shown, including any loss.\n'
           '\n## Key numerical takeaway\n'+json.dumps({'mae':j['mae'],'comparisons':rr},indent=2)+limits)
    save(out/'render_receipt.json',dict(execution='succeeded',source_summary_sha256=sha(source/'summary.json'),
         renderer_sha256=sha(Path(__file__)),figures=2,numerical_rerun=False,
         output_hashes={p.name:sha(p) for p in out.iterdir() if p.is_file()}))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('mode',choices=['self-test','prepare','run','plot'])
    p.add_argument('--output',type=Path); p.add_argument('--source',type=Path); p.add_argument('--lock',type=Path)
    a=p.parse_args()
    if a.mode=='self-test': tests()
    elif a.mode=='prepare': prepare(a.output)
    elif a.mode=='run': run(a.lock,a.output)
    else: plot(a.source,a.output)
