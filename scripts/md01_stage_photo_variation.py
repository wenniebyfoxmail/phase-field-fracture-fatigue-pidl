"""E048: all fixed stage27/28/29 photographs; no identification/predictor changes."""
import argparse
from datetime import datetime, timezone
import itertools
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
from md01_geometric_guide_transfer import transfer, tests as guide_tests
from md01_frame_geometry import read_frame, extract
from md01_support_mass_forecast import observe

OLD=ROOT/'local_archive/experiments/S03-E047-MD01/runs'
HISTORY=ROOT/'local_archive/experiments/S03-E046-MD01/runs/S03-E046-MD01-R001'
META=ROOT/'local_archive/open_data/md01_tack_metadata_20261016'
RAW=ROOT/'local_archive/experiments/S03-E048-MD01/raw_images'
PROTOCOL=WORK/'docs/research/S03/S03-E048-MD01/experiment.md'
WINDOWS=((25,26,27),(26,27,28),(27,28,29))


def histories(data,a,b,t):
    if any(s>b for s in data): raise ValueError('Future observation in history')
    return [dict(history_a=a,origin=b,target=t,a_photo=i,b_photo=j,
                 a_area=oa['area'],b_area=ob['area'],**forecast(a,b,t,oa['area'],ob['area']))
            for (i,oa),(j,ob) in itertools.product(sorted(data[a].items()),sorted(data[b].items()))]


def score(pred,area,photo):
    p,t=abs(pred['persistence']-area),abs(pred['secant']-area)
    return dict(**pred,target_photo=photo,observed_area=area,persistence_ae=p,secant_ae=t,gain=p-t)


def paths(scores):
    idx={(r['target'],r['a_photo'],r['b_photo'],r['target_photo']):r for r in scores}
    result=[]
    for i,j,k in itertools.product((1,2,3),repeat=3):
        rr=[idx[(27,1,1,i)],idx[(28,1,i,j)],idx[(29,i,j,k)]]
        p=float(np.mean([r['persistence_ae'] for r in rr])); t=float(np.mean([r['secant_ae'] for r in rr]))
        result.append(dict(path=f'{i}{j}{k}',photo27=i,photo28=j,photo29=k,persistence_mae=p,secant_mae=t,gain=p-t))
    return result


def tests():
    guide_tests()
    d={25:{1:dict(area=10)},26:{1:dict(area=20)}}; ss=[]
    for a,b,t in WINDOWS:
        pp=histories(d,a,b,t); assert len(pp)=={27:1,28:3,29:9}[t]
        d[t]={i:dict(area=20+(t-26)*10) for i in (1,2,3)}
        ss.extend(score(p,o['area'],i) for p in pp for i,o in d[t].items())
    assert len(ss)==39 and len(paths(ss))==27
    assert all(r['secant_mae']==0 and r['gain']==10 for r in paths(ss))
    try: histories(d,27,28,29)
    except ValueError: pass
    else: raise AssertionError('Future guard failed')
    assert score(dict(persistence=2.,secant=5.),4,1)['gain']==1
    print('All combinations,27 coherent paths,constant observations and future guard passed; no real data.')


def prepare(out):
    out.mkdir(parents=True,exist_ok=False)
    lp=OLD/'S03-E047-MD01-R000/selection_lock.json'; old=json.loads(lp.read_text())
    mapping=META/'step_image_metadata_receipt.json'; directory=META/'fixed_camera_file_metadata.json'
    m=json.loads(mapping.read_text())['mapping']; official={r['filename']:r for r in json.loads(directory.read_text())}
    frames=[]
    for s in (27,28,29):
        rr=sorted([r for r in m if r['step']==str(s) and r['matches_in_fixed_folder']==1],key=lambda r:r['filename'])
        assert len(rr)==3 and len({r['filename'] for r in rr})==3
        for i,r in enumerate(rr,1):
            item=official[r['filename']]; url=f"https://data.mendeley.com/public-files/datasets/dns97tfdjn/files/{item['id']}/file_downloaded"
            assert url==item['content_details']['download_url']
            source=next(f['source'] for f in old['frames'] if f['stage']==s) if i==1 else str(RAW/r['filename'])
            frames.append(dict(stage=s,photo=i,filename=r['filename'],source=source,official_id=item['id'],
                 bytes=item['size'],sha256=item['content_details']['sha256_hash'],url=url,
                 available_at_prepare=Path(source).exists(),excel_row=r['excel_row']))
    assert sum(f['bytes'] for f in frames if f['photo']>1)<120_000_000
    protected=dict(old['protected_inputs'])
    for p in sorted(OLD.rglob('*')):
        if p.is_file(): protected[str(p)]=sha(p)
    for p in (mapping,directory,PROTOCOL,Path(__file__)):
        protected[str(p)]=sha(p)
    for f in frames:
        if Path(f['source']).exists():
            assert Path(f['source']).stat().st_size==f['bytes'] and sha(f['source'])==f['sha256']
            protected[f['source']]=f['sha256']
    assert all(sha(p)==h for p,h in protected.items())
    save(out/'input_lock.json',dict(protocol='E048-stage-photo-variation-v1',frames=frames,windows=WINDOWS,
         roi=old['roi'],band=old['band'],original_support=old['original_support'],protected_inputs=protected,
         prepared_utc=datetime.now(timezone.utc).isoformat(),no_extra_pixels_decoded=True,
         expected_new_download_bytes=sum(f['bytes'] for f in frames if not f['available_at_prepare'])))
    print(json.dumps(dict(fixed_files=[f['filename'] for f in frames],protected=len(protected),
         new_download_bytes=sum(f['bytes'] for f in frames if not f['available_at_prepare'])),indent=2))


def run(lockpath,out):
    start,cpu=time.monotonic(),time.process_time(); out.mkdir(parents=True,exist_ok=False); RAW.mkdir(parents=True,exist_ok=True)
    lock=json.loads(lockpath.read_text()); protected=lock['protected_inputs']; events=[]
    receipt=dict(execution='running',host=socket.gethostname(),pid=os.getpid(),runtime=sys.executable,command=sys.argv,
         started_utc=datetime.now(timezone.utc).isoformat(),lock_sha256=sha(lockpath),
         commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),
         dirty=subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).splitlines())
    save(out/'run_start_receipt.json',receipt)
    def event(kind,stage,**extra): events.append(dict(event=kind,stage=stage,utc=datetime.now(timezone.utc).isoformat(),**extra))
    def guard():
        assert sha(lockpath)==receipt['lock_sha256'] and all(sha(p)==h for p,h in protected.items())
    def budget():
        if time.monotonic()-start>300 or time.process_time()-cpu>60: raise TimeoutError('300s wall/60s CPU cap')
    roi,band=lock['roi'],lock['band']; x0,y0,x1,y1=np.array(band)-np.array([roi[0],roi[1],roi[0],roi[1]])
    sl=np.s_[y0:y1,x0:x1]; data={}; obsrows=[]; allscores=[]; targetonly=[]; newhashes={}
    try:
        guard()
        for s in (25,26):
            with np.load(HISTORY/f'step{s}/observation_arrays.npz') as z: v,_=observe(z['band_mask'])
            data[s]={1:v}
        for a,b,t in WINDOWS:
            budget(); stageout=out/f'step{t}'; stageout.mkdir(); pp=histories(data,a,b,t)
            predpath=stageout/'predictions_before_extra_targets.json'; save(predpath,pp); predhash=sha(predpath)
            event('predictions_saved',t,count=len(pp),sha256=predhash)
            original=json.loads((OLD/f'S03-E047-MD01-R001/W{t}/predictions_before_target.json').read_text())['predictions']
            p1=next(p for p in pp if p['a_photo']==p['b_photo']==1)
            assert all(p1[k]==original[k] for k in original)
            stageobs={}
            for f in [f for f in lock['frames'] if f['stage']==t]:
                budget(); photo=f['photo']; case=stageout/f'photo{photo}'; case.mkdir()
                if photo==1:
                    event('cached_target_loaded',t,photo=1)
                    with np.load(OLD/f'S03-E047-MD01-R001/W{t}/observation_arrays.npz') as z:
                        arrays={k:z[k].copy() for k in z.files}
                    reused=True
                else:
                    path=Path(f['source'])
                    if not path.exists():
                        print(f"Acquire Step{t} photo{photo}: {f['filename']}",flush=True)
                        subprocess.run(['curl','--fail','--location','--max-time','30','--max-filesize',str(f['bytes']),
                             '--silent','--show-error','--output',str(path),f['url']],check=True,timeout=35)
                    assert path.stat().st_size==f['bytes'] and sha(path)==f['sha256']
                    newhashes[str(path)]=f['sha256']; event('source_verified_before_decode',t,photo=photo,sha256=f['sha256'])
                    rgb=read_frame(f,roi); support,diag,eligible,pathxy=transfer(rgb,lock['original_support'],roi,band)
                    save(case/'guide_before_extraction.json',dict(support=support,diagnostic=diag))
                    mask,excluded,_=extract(rgb,support,roi)
                    assert not excluded[sl].any() and not (mask & ~eligible).any()
                    arrays=dict(mask=mask,excluded=excluded,band_mask=mask[sl],band_rgb=rgb[sl],guide_path_native=pathxy)
                    reused=False
                v,profile=observe(arrays['band_mask']); arrays['row_mass']=profile
                assert v['mass'] is None or abs(v['area']-v['support']*v['mass'])<1e-9
                np.savez_compressed(case/'observation_arrays.npz',**arrays)
                row=dict(stage=t,photo=photo,filename=f['filename'],**v,reused_E047_mask=reused)
                save(case/'observation.json',row); obsrows.append(row); stageobs[photo]=v
                event('observation_available',t,photo=photo)
                targetonly.append(score(p1,v['area'],photo))
                allscores.extend(score(p,v['area'],photo) for p in pp)
                if photo==1:
                    oldscore=json.loads((OLD/f'S03-E047-MD01-R001/W{t}/comparison.json').read_text())
                    assert all(targetonly[-1][k]==oldscore[k] for k in ('observed_area','persistence_ae','secant_ae'))
            assert sha(predpath)==predhash; data[t]=stageobs
            print(f'Step{t}: all3fixed photographs measured; no selection.',flush=True)
        coherent=paths(allscores); stage_summary=[]
        for s in (27,28,29):
            oo=[r for r in obsrows if r['stage']==s]; base=oo[0]['area']; areas=[r['area'] for r in oo]
            fixed=[r['gain'] for r in targetonly if r['target']==s]; propagated=[r['gain'] for r in allscores if r['target']==s]
            stage_summary.append(dict(stage=s,areas=areas,area_min=min(areas),area_max=max(areas),span=max(areas)-min(areas),
                 span_fraction_of_photo1=(max(areas)-min(areas))/base,max_deviation_from_photo1=max(abs(v-base) for v in areas),
                 supports=[r['support'] for r in oo],masses=[r['mass'] for r in oo],
                 fixed_gain_min=min(fixed),fixed_gain_max=max(fixed),fixed_wins=sum(g>0 for g in fixed),
                 propagated_gain_min=min(propagated),propagated_gain_max=max(propagated),
                 propagated_wins=sum(g>0 for g in propagated),propagated_total=len(propagated)))
        pg=[r['gain'] for r in coherent]
        summary=dict(role='finite within-nominal-stage photo-choice diagnostic, one trajectory, no independent replication',
             stages=stage_summary,observations=obsrows,coherent_paths=coherent,paths_positive=sum(g>0 for g in pg),
             path_gain_min=min(pg),path_gain_max=max(pg),path_count=27,
             path_trend_mae_range=[min(r['secant_mae'] for r in coherent),max(r['secant_mae'] for r in coherent)],
             path_hold_mae_range=[min(r['persistence_mae'] for r in coherent),max(r['persistence_mae'] for r in coherent)],
             original_E047_scores_exact=True,baseline_masks_exact_reused=3,new_extractions=6,
             local_scenarios=len(allscores),target_only_scores=len(targetonly),old_halfdepth_unchanged=True)
        assert len(allscores)==39 and len(targetonly)==9
        table(out/'observations.csv',obsrows); table(out/'target_only_scores.csv',targetonly)
        table(out/'all_local_scenarios.csv',allscores); table(out/'coherent_paths.csv',coherent)
        save(out/'summary.json',summary); save(out/'event_order.json',events); save(out/'new_source_hashes.json',newhashes)
        guard(); assert all(sha(p)==h for p,h in newhashes.items()); budget()
        receipt.update(execution='succeeded',retrieval='verified_local',protected_files_verified=len(protected),
                       verified_extra_sources=len(newhashes),new_source_bytes=sum(Path(p).stat().st_size for p in newhashes),
                       unchanged_E047_masks_scores=3,stage_forecast_snapshots=3)
        print(json.dumps({k:v for k,v in summary.items() if k not in ('coherent_paths','observations')},indent=2),flush=True)
    except Exception as e: receipt.update(execution='failed',error=repr(e)); raise
    finally:
        save(out/'event_order_at_exit.json',events)
        receipt.update(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,
                       ended_utc=datetime.now(timezone.utc).isoformat()); save(out/'run_receipt.json',receipt)


def plot(source,out):
    out.mkdir(parents=True,exist_ok=False); j=json.loads((source/'summary.json').read_text())
    import csv
    with (source/'all_local_scenarios.csv').open() as f: scenarios=list(csv.DictReader(f))
    plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
    prov=f'\n## Data provenance\nE048 R001 {source}; renderer scripts/md01_stage_photo_variation.py. No numerical rerun. '
    limits=('\n## Limitations and claim boundary\nOne MD01 nominal-stage trajectory, finite photo combinations not independent samples or confidence intervals. '
            'Stage-internal real change, pose, lighting and segmentation effects not separately identified. Same native band[3900,1700,4600,1950], '
            'current-image geometry only, no registration fitting. Area px², L occupied rows and M pixels/occupied row, not physical or half-depth width. '
            'Shadows/pores/gaps can remain. E047photo1scores and all old half-depth definitions preserved.\n')
    def export(fig,stem,text):
        fig.savefig(out/f'{stem}.png',dpi=240); fig.savefig(out/f'{stem}.pdf'); plt.close(fig)
        (out/f'{stem}.md').write_text(text)
    for st in j['stages']:
        s=st['stage']; fig,axes=plt.subplots(2,3,figsize=(13,4.9),layout='constrained')
        for k in range(3):
            o=next(o for o in j['observations'] if o['stage']==s and o['photo']==k+1)
            with np.load(source/f'step{s}/photo{k+1}/observation_arrays.npz') as z: rgb=z['band_rgb']; mask=z['band_mask']
            axes[0,k].imshow(rgb); axes[1,k].imshow(rgb)
            overlay=np.zeros((*mask.shape,4)); overlay[mask]=(.35,.25,.65,.8); axes[1,k].imshow(overlay)
            axes[0,k].set_title(f"Photo{k+1} | {o['filename']}"+(' | old cache' if k==0 else ''))
            mass='NA' if o['mass'] is None else f"{o['mass']:.2f}"
            axes[1,k].set_title(f"A={o['area']}; L={o['support']}/250; M={mass}")
            for ax in axes[:,k]: ax.set_axis_off()
        fig.suptitle(f'E048 | Step{s}: all3 fixed photographs, unchanged identification\nSource above / purple candidate below; within-stage spread={st["span"]} px²',fontsize=13)
        export(fig,f'F01_step{s}_all_photos',f'# How to read: Step{s} all photographs\n\n## Figure question\nDoes the same observer change across the fixed3same-stage photos?\n'+prov+
               '\n## Visual grammar and panel guide\nColumns fixedphoto1/2/3 in filename order; top original source, bottom same source with purple mask. '
               'Photo1is exact reused E047array. Same native crop/scale, no good/bad selection. A area, L occupiedrows, M conditional row pixels.\n'
               '\n## Key numerical takeaway\n'+json.dumps(st,indent=2)+limits)
    fig,axes=plt.subplots(1,3,figsize=(13,4.6),layout='constrained')
    for st in j['stages']:
        s=st['stage']; oo=[o for o in j['observations'] if o['stage']==s]
        axes[0].plot([s-.18,s,s+.18],[o['area'] for o in oo],'o-',lw=1.2,label=f'Step{s}')
    axes[0].set(xticks=[27,28,29],xlabel='Stage, photo1/2/3 left→right',ylabel='Candidate area (px²)',title='A  Within-stage observation spread')
    for i,st in enumerate(j['stages']):
        fixed=[float(r['gain']) for r in scenarios if int(r['target'])==st['stage'] and int(r['a_photo'])==int(r['b_photo'])==1]
        allg=[float(r['gain']) for r in scenarios if int(r['target'])==st['stage']]
        axes[1].scatter(np.full(len(fixed),i-.1),fixed,color='#E69F00',s=35,label='Target photo only' if i==0 else None)
        axes[1].scatter(np.full(len(allg),i+.1),allg,color='#0072B2',s=18,alpha=.55,label='History + target choices' if i==0 else None)
    axes[1].axhline(0,color='#777777',lw=1); axes[1].set(xticks=[0,1,2],xticklabels=['→27','→28','→29'],ylabel='Hold AE − trend AE (px²)',title='B  Every per-window gain; positive helps')
    axes[1].legend(fontsize=8)
    pp=j['coherent_paths']; axes[2].plot(np.arange(27),[p['gain'] for p in pp],'o-',lw=1,color='#009E73',ms=4)
    axes[2].axhline(0,color='#777777',lw=1); axes[2].set(xticks=[0,6,13,20,26],xticklabels=[pp[i]['path'] for i in (0,6,13,20,26)],
         xlabel='Photo27/28/29 path, fixed lexical order',ylabel='Hold MAE − trend MAE (px²)',title=f'C  All27 paths; {j["paths_positive"]}/27 positive')
    for ax in axes: ax.grid(axis='y',alpha=.15)
    fig.suptitle('E048 | Photograph-choice sensitivity, NOT a replacement of E047 scores\n39 local combinations and27 coherent3-window paths are finite scenarios, not independent trials',fontsize=13)
    export(fig,'F02_observation_and_gain_sensitivity','# How to read: observation and forecast-gain sensitivity\n\n## Figure question\nCan fixed photograph choices reverse or materially shift the observed trend benefit?\n'+prov+
           '\n## Visual grammar and panels\nA all9candidate areas, photo1/2/3 left-to-right within each stage. B orange3fixed-forecast target-only gains per stage; '
           'blue all3/9/27history+target combinations. Coincident points may overlap; counts in tables authoritative. '
           'C all27coherentphoto27/28/29paths in lexical order, each averages exactly3windows; not ranked by performance. Zero reference, no uncertainty intervals.\n'
           '\n## Key numerical takeaway\n'+json.dumps({k:v for k,v in j.items() if k!='observations'},indent=2)+limits)
    save(out/'render_receipt.json',dict(execution='succeeded',source_summary_sha256=sha(source/'summary.json'),
         renderer_sha256=sha(Path(__file__)),figures=4,numerical_rerun=False,
         output_hashes={p.name:sha(p) for p in out.iterdir() if p.is_file()}))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('mode',choices=['self-test','prepare','run','plot'])
    p.add_argument('--output',type=Path); p.add_argument('--source',type=Path); p.add_argument('--lock',type=Path)
    a=p.parse_args()
    if a.mode=='self-test': tests()
    elif a.mode=='prepare': prepare(a.output)
    elif a.mode=='run': run(a.lock,a.output)
    else: plot(a.source,a.output)
