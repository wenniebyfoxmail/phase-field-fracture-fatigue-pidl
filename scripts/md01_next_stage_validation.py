"""E044: metadata-fixed rolling extension; unchanged E037 extractor/E043 predictor."""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from md01_cached_stage_forecast import ROOT, WORK, CACHE, sha, save, table
from md01_support_mass_forecast import observe, predict, tests, METHODS, COLORS, LABELS
from md01_frame_geometry import read_frame, extract

META=ROOT/'local_archive/open_data/md01_tack_metadata_20261016'
OLD=ROOT/'local_archive/experiments/S03-E043-MD01/runs'
RAW=ROOT/'local_archive/experiments/S03-E034-MD01/raw_images'
PROTOCOL=WORK/'docs/research/S03/S03-E044-MD01/experiment.md'
SUPPORT=WORK/'docs/research/S03/S03-E037-MD01/frame_support_lock.json'
SOURCE=WORK/'docs/research/S03/S03-E037-MD01/source_lock.json'


def select(mapping, max_old=23):
    groups={}
    for row in mapping:
        step=row.get('step')
        if step is None or not str(step).isdigit():continue
        s=int(step)
        if s>max_old and row['filename'] is not None and row['matches_in_fixed_folder']==1:
            groups.setdefault(s,[]).append(row)
    complete=sorted(s for s,rr in groups.items() if len({r['filename'] for r in rr})==3)
    if len(complete)<3:raise ValueError('Fewer than3 complete later stages')
    chosen=complete[:3]
    if chosen!=[max_old+1,max_old+2,max_old+3]:raise ValueError('Next complete stages are not consecutive; stop')
    return [min(groups[s],key=lambda r:r['filename']) for s in chosen]


def prepare(out):
    out.mkdir(parents=True,exist_ok=False)
    m=META/'step_image_metadata_receipt.json';f=META/'fixed_camera_file_metadata.json'
    mapping=json.loads(m.read_text())['mapping'];directory=json.loads(f.read_text())
    byname={x['filename']:x for x in directory};rows=select(mapping)
    assert [int(r['step']) for r in rows]==[24,25,26]
    files=[]
    for row in rows:
        item=byname[row['filename']];p=RAW/row['filename'];content=item['content_details']
        assert p.stat().st_size==item['size'] and sha(p)==content['sha256_hash']
        files.append(dict(stage=int(row['step']),filename=row['filename'],source=str(p),
                          official_id=item['id'],excel_row=row['excel_row'],bytes=item['size'],sha256=sha(p)))
    lock=json.loads(SOURCE.read_text());support=json.loads(SUPPORT.read_text())['frames']['23']
    inputs={str(p):sha(p) for p in (m,f,SOURCE,SUPPORT,PROTOCOL,Path(__file__),
             WORK/'scripts/md01_support_mass_forecast.py',WORK/'scripts/md01_cached_stage_forecast.py',
             WORK/'scripts/md01_frame_geometry.py',WORK/'scripts/d01_crack_profile_diagnostic.py')}
    for p,h in json.loads((OLD/'S03-E043-MD01-R001/input_manifest.json').read_text()).items():
        assert sha(p)==h;inputs[p]=h
    for p in sorted(OLD.rglob('*')):
        if p.is_file():inputs[str(p)]=sha(p)
    for row in files:inputs[row['source']]=row['sha256']
    selection=dict(protocol='E044-next3-frozen-v1',selection='first3 complete chronological stages after23; smallest linked filename',
                   source_role='previously viewed E034 raw files, new E043-method targets; not virgin holdout',
                   frames=files,windows=[[22,23,24],[23,24,25],[24,25,26]],
                   roi=lock['roi_xyxy'],band=lock['forecast_roi_xyxy'],new_stage_support=support,
                   initial_cache_stages=[22,23],fixed_support_stage=23,protected_inputs=inputs,
                   prepared_utc=datetime.now(timezone.utc).isoformat(),no_pixels_decoded=True)
    save(out/'selection_lock.json',selection)
    save(out/'prepare_receipt.json',dict(execution='succeeded',metadata_only=True,no_pixels_decoded=True,
        selection_sha256=sha(out/'selection_lock.json'),files=files,protected_inputs=len(inputs)))
    print(json.dumps(dict(frames=files,windows=selection['windows'],no_pixels_decoded=True),indent=2))


def run(lockpath,out):
    start,cpu=time.monotonic(),time.process_time();out.mkdir(parents=True,exist_ok=False)
    receipt=dict(execution='running',host=socket.gethostname(),pid=os.getpid(),command=sys.argv,
                 runtime=sys.executable,started_utc=datetime.now(timezone.utc).isoformat(),
                 commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),
                 dirty=subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).splitlines(),
                 selection_sha256=sha(lockpath))
    save(out/'run_start_receipt.json',receipt)
    lock=json.loads(lockpath.read_text());protected=lock['protected_inputs']
    def guard():
        assert all(sha(p)==h for p,h in protected.items()),'Frozen evidence changed'
        assert sha(lockpath)==receipt['selection_sha256']
    def budget():
        if max(time.monotonic()-start,time.process_time()-cpu)>90:raise TimeoutError('90s run cap')
    try:
        guard();roi,band=lock['roi'],lock['band']
        x0,y0,x1,y1=np.array(band)-np.array([roi[0],roi[1],roi[0],roi[1]])
        sl=np.s_[y0:y1,x0:x1];width=int(x1-x0)
        obs={};rows=[];scores=[];events=[]
        for s in lock['initial_cache_stages']:
            p=CACHE/f'step{s}/v1/geometry_arrays.npz'
            with np.load(p) as z:values,profile=observe(z['mask'][sl]);assert not z['excluded'][sl].any()
            metrics=json.loads((CACHE/f'step{s}/v1/metrics.json').read_text())['common']
            assert values['area']==metrics['area_px2']
            obs[s]=values;rows.append(dict(stage=s,role='unchanged_history_cache',**values))
        for a,b,t in lock['windows']:
            budget();case=out/f'W{t}';case.mkdir()
            pred=predict(obs[a],obs[b],a,b,t,width)
            frozen=dict(history_a=a,origin=b,target=t,stage_horizon=t-b,history={str(s):obs[s] for s in (a,b)},
                        predictions=pred,selection_sha256=receipt['selection_sha256'],
                        saved_utc=datetime.now(timezone.utc).isoformat())
            save(case/'predictions_before_target.json',frozen)
            predhash=sha(case/'predictions_before_target.json')
            events.append(dict(event='prediction_saved',target=t,hash=predhash,utc=datetime.now(timezone.utc).isoformat()))
            f=next(x for x in lock['frames'] if x['stage']==t)
            rgb=read_frame(f,roi)
            mask,excluded,_=extract(rgb,lock['new_stage_support'],roi)
            target,profile=observe(mask[sl]);comparable=not bool(excluded[sl].any())
            obs[t]=target;rows.append(dict(stage=t,role='new_target_then_next_history',**target))
            np.savez_compressed(case/'observation_arrays.npz',mask=mask,excluded=excluded,
                                band_mask=mask[sl],band_rgb=rgb[sl],row_mass=profile)
            save(case/'observation.json',dict(stage=t,**target,source=f,common_band_clear=comparable,
                 fixed_support_stage=23,decoded_utc=datetime.now(timezone.utc).isoformat()))
            scored=dict(history_a=a,origin=b,target=t,observed_area=target['area'],observed_support=target['support'],
                        observed_mass=target['mass'],common_band_clear=comparable,**pred)
            for method in METHODS:
                scored[method+'_ae']=abs(pred[method]-target['area']) if comparable and pred[method] is not None else None
            scored['paired_scored']=bool(comparable and pred['support_hold'] is not None)
            for base in ('persistence','secant'):
                scored['gain_vs_'+base]=scored[base+'_ae']-scored['support_hold_ae'] if scored['paired_scored'] else None
            scored['support_ae']=abs(pred['predicted_support']-target['support']) if comparable else None
            scored['mass_ae']=abs(pred['predicted_mass']-target['mass']) if comparable and pred['predicted_mass'] is not None and target['mass'] is not None else None
            assert sha(case/'predictions_before_target.json')==predhash
            save(case/'comparison.json',scored);scores.append(scored)
            events.append(dict(event='target_measured_and_scored',target=t,prediction_hash_unchanged=True,
                               utc=datetime.now(timezone.utc).isoformat()))
        paired=[s for s in scores if s['paired_scored']]
        mae={m:float(np.mean([s[m+'_ae'] for s in paired])) if paired else None for m in METHODS}
        result=dict(role='new rolling query extension on previously exposed images; one trajectory',
                    selection_sha256=receipt['selection_sha256'],windows=lock['windows'],
                    coverage=f'{len(paired)}/3 paired windows',observations=rows,comparisons=scores,paired_mae=mae,
                    fixed_identification=True,old_cache_unmodified=True,new_stage_support_from=23,
                    new_stage_extraction_count=3,clipped=sum(s['mass_clipped'] for s in scores),
                    not_material_registration=True,shadow_false_positives='retained; not quantified',
                    equal_support_regime=[s['target'] for s in scores if obs[s['history_a']]['support']==obs[s['origin']]['support']],
                    prediction_equals_area_secant=[s['target'] for s in scores if s['support_hold'] is not None and abs(s['support_hold']-s['secant'])<1e-9])
        table(out/'observations.csv',rows);table(out/'comparisons.csv',scores)
        save(out/'event_order.json',events);save(out/'summary.json',result)
        guard();budget()
        receipt.update(execution='succeeded',retrieval='verified_local',inputs_verified=len(protected),
                       per_target_predictions_precede_decode=True,original_parameters_unchanged=True)
        print(json.dumps(result,indent=2))
    except Exception as e:
        receipt.update(execution='failed',error=repr(e));raise
    finally:
        receipt.update(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,
                       ended_utc=datetime.now(timezone.utc).isoformat())
        save(out/'run_receipt.json',receipt)


def plot(source,out):
    out.mkdir(parents=True,exist_ok=False);r=json.loads((source/'summary.json').read_text())
    obs={o['stage']:o for o in r['observations']};rr=r['comparisons']
    plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
    source_text=f'\n## Data provenance\nE044 R001: {source}. R002 renderer: scripts/md01_next_stage_validation.py. '
    limit=('\n## Limitations and claim boundary\nPreviously viewed MD01 images, new fixed query extension in one trajectory; '
           'three overlapping windows, not independent specimens. Masks may contain shadows/texture; no truth/physical aperture claim. '
           'Relative stage is not time/kN. Guide/exclusions from stage23 fixed for24–26, no target-guided re-centering. '
           'Initial22/23 retain older observer supports. L is occupied image rows, M conditional candidate-pixel count, not half-depth width. '
           'Old scores and widths unchanged.\n')
    def export(fig,stem,guide):
        fig.savefig(out/f'{stem}.png',dpi=300);fig.savefig(out/f'{stem}.pdf');plt.close(fig)
        (out/f'{stem}.md').write_text(guide)
    fig,axes=plt.subplots(2,3,figsize=(15,4.7),layout='constrained')
    for i,s in enumerate((24,25,26)):
        with np.load(source/f'W{s}/observation_arrays.npz') as z:
            rgb=z['band_rgb'];m=z['band_mask']
        axes[0,i].imshow(rgb);axes[1,i].imshow(rgb)
        rgba=np.zeros((*m.shape,4));rgba[m]=(0,.55,.8,.8);axes[1,i].imshow(rgba)
        axes[0,i].set_title(f'Step{s} | source (same fixed image band)')
        axes[1,i].set_title(f"{obs[s]['area']} candidate px² | L={obs[s]['support']}/250 | M={obs[s]['mass']:.2f}")
        for ax in axes[:,i]:ax.set_axis_off()
    fig.suptitle('E044 R001 → R002 | All 3 new targets; stage23 guide transferred unchanged\nCyan = candidate, not ground truth; shadows/texture are NOT removed',fontsize=13)
    export(fig,'F01_all_new_target_masks','# How to read: all3 fixed new target masks\n\n## Figure question\nWhat was actually measured in each new target?\n'+source_text+
           '\n## Visual grammar and panels\nThree columns stages24,25,26; upper source native band[3900,1700,4600,1950], lower same source with cyan unchanged-rule candidates. '
           'Titles give area, occupiedrows L of250 and conditionalrowmass M=A/L. All samecrop/nativepixel scale. No best-case selection.\n'
           '\n## Key numerical takeaway\n'+json.dumps([obs[s] for s in (24,25,26)],indent=2)+limit)
    fig,axes=plt.subplots(3,2,figsize=(12,11),layout='constrained')
    for i,s in enumerate(rr):
        a,b,t=s['history_a'],s['origin'],s['target'];ax=axes[i,0]
        ax.plot([a,b],[obs[a]['area'],obs[b]['area']],'ko-',label='Observed history',lw=1.5)
        ax.plot([b,t],[obs[b]['area'],obs[t]['area']],'k:',lw=1)
        ax.scatter([t],[obs[t]['area']],color='#333333',marker='x',s=60,label=f"Target mask: {obs[t]['area']}")
        for m,c,label,marker in zip(METHODS,COLORS,LABELS,('s','^','D')):
            if s[m] is None:continue
            ax.plot([b,t],[obs[b]['area'],s[m]],color=c,ls='--',lw=1.1)
            ax.scatter([t],[s[m]],facecolors='none',edgecolors=c,marker=marker,s=90,
                       label=f'{label}: {s[m]:.1f}')
        ax.axvline(b,color='#999999',lw=.7)
        ax.set(xticks=[a,b,t],xlabel='Relative stage; vertical line = origin',ylabel='Candidate area (px²)',
               title=f'{a},{b} → {t}: predictions saved before target measurement')
        ax.legend(fontsize=8)
        ax=axes[i,1]
        for j,(m,c,label) in enumerate(zip(METHODS,COLORS,LABELS)):
            e=s[m+'_ae']
            if e is not None:ax.scatter([e],[j],color=c,s=55);ax.annotate(f' {e:.2f}',(e,j),xytext=(5,0),textcoords='offset points',va='center')
        ax.set(yticks=range(3),yticklabels=LABELS,xlabel='Absolute candidate-area error (px²)',
               ylim=(2.6,-.6),title=f"Target{t}: L={s['observed_support']}, M={s['observed_mass']:.2f}")
        ax.set_xlim(0,max(x[m+'_ae'] or 0 for x in rr for m in METHODS)*1.2+1)
        ax.grid(axis='x',alpha=.15)
    fig.suptitle('E044 | All fixed rolling queries, unchanged predictors and identification\nNew query extension, NOT untouched-image blind validation; masks/shadows unchanged',fontsize=13)
    export(fig,'F02_every_window_forecast','# How to read: every fixed new forecast window\n\n## Figure question\nHow does the frozen separated-input predictor compare in every new query?\n'+source_text+
           '\n## Visual grammar and panel guide\nEach row is22/23→24,23/24→25,24/25→26 in order. Left: blackhistory, verticalorigin, targetcross, '
           'orange persistence, blue area secant, green support-hold/mass-secant, hollowmarkers and exact legends reveal ties. '
           'Right: same methods per-case AE, commonxscale across rows, exact annotations. No favourable-case filtering. '
           'Target is observed only after predictionfile saved; rolling updates use newlyobservedtarget only for laterwindows.\n'
           '\n## Key numerical takeaway\n'+json.dumps({'comparisons':rr,'paired_mae':r['paired_mae'],'coverage':r['coverage']},indent=2)+limit)
    save(out/'render_receipt.json',dict(execution='succeeded',numeric_summary_sha256=sha(source/'summary.json'),
         source=str(source),renderer_sha256=sha(Path(__file__)),numerical_rerun=False,figures=2,
         output_hashes={p.name:sha(p) for p in out.iterdir() if p.is_file()}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['self-test','prepare','run','plot'])
    p.add_argument('--output',type=Path);p.add_argument('--lock',type=Path);p.add_argument('--source',type=Path);a=p.parse_args()
    if a.mode=='self-test':
        tests()
        fake=[dict(step=str(s),filename=f'{s}-{i}',matches_in_fixed_folder=1) for s in range(24,28) for i in range(3)]
        assert [int(x['step']) for x in select(fake)]==[24,25,26]
        assert select(fake[::-1])==select(fake)
        try:select([x for x in fake if x['step']!='24'])
        except ValueError:pass
        else:raise AssertionError('Missing consecutive stages accepted')
        print('Metadata stage selection/order/missing-stage tests passed; no data opened.')
    elif a.mode=='prepare':prepare(a.output)
    elif a.mode=='run':run(a.lock,a.output)
    else:plot(a.source,a.output)
