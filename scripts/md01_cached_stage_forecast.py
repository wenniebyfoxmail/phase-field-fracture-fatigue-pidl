"""E042: cached observations only; no segmentation, fitting or parameter selection."""
import argparse
import csv
import hashlib
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
from PIL import Image, ImageOps

ROOT = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
WORK = Path(__file__).resolve().parents[1]
CACHE = ROOT/'local_archive/experiments/S03-E038-MD01/runs/S03-E038-MD01-R001'
REPAIR = ROOT/'local_archive/experiments/S03-E041-MD01/runs/S03-E041-MD01-R001/guide_comparison_arrays.npz'
STAGES = (18, 19, 21, 22, 23)
WINDOWS = ((18, 19, 21), (19, 21, 22), (21, 22, 23))
ARMS = ('v1', 'gray_minus5', 'gray_plus5', 'contrast_minus5', 'contrast_plus5',
        'guide_x_minus5', 'guide_x_plus5', 'guide_y_minus5', 'guide_y_plus5')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(p, data):
    with Path(p).open('x') as f:
        json.dump(data, f, indent=2, allow_nan=False)


def forecast(a_stage, b_stage, target_stage, a, b):
    if not a_stage < b_stage < target_stage:
        raise ValueError('Noncausal stage ordering')
    raw = b + (b-a)*(target_stage-b_stage)/(b_stage-a_stage)
    return {'persistence': float(b), 'secant': float(max(0, raw)), 'raw_secant': float(raw)}


def table(path, rows):
    with path.open('x', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(out):
    start = time.monotonic()
    cpu = time.process_time()
    out.mkdir(parents=True, exist_ok=False)
    receipt = dict(execution='running', host=socket.gethostname(), pid=os.getpid(),
                   command=sys.argv, runtime=sys.executable,
                   started_utc=datetime.now(timezone.utc).isoformat(),
                   commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=WORK,text=True).strip(),
                   dirty=subprocess.check_output(['git','status','--porcelain'],cwd=WORK,text=True).splitlines())
    save(out/'run_start_receipt.json', receipt)
    inputs = {}

    def touch(p):
        inputs[str(p)] = sha(p)
        return p

    def budget():
        if max(time.monotonic()-start, time.process_time()-cpu) > 60:
            raise TimeoutError('60 second analysis cap')

    def figure(fig, stem, guide):
        fig.savefig(out/f'{stem}.png', dpi=220)
        fig.savefig(out/f'{stem}.pdf')
        plt.close(fig)
        (out/f'{stem}.md').write_text(guide)

    try:
        touch(Path(__file__))
        touch(WORK/'docs/research/S03/S03-E042-MD01/experiment.md')
        lock_path = touch(WORK/'docs/research/S03/S03-E037-MD01/source_lock.json')
        lock = json.loads(lock_path.read_text())
        for p, h in lock['protected_old_hashes'].items():
            if sha(p) != h:
                raise ValueError('Protected old evidence changed: '+p)
        for p in ('scripts/md01_frame_geometry.py', 'scripts/d01_crack_profile_diagnostic.py'):
            touch(WORK/p)
        roi, band = lock['roi_xyxy'], lock['forecast_roi_xyxy']
        x0,y0,x1,y1 = np.array(band)-np.array([roi[0],roi[1],roi[0],roi[1]])
        sl = np.s_[y0:y1,x0:x1]
        data = {}
        masks = {}
        rows = []
        for arm in ARMS:
            data[arm] = {}
            for stage in STAGES:
                p = touch(CACHE/f'step{stage}'/arm/'metrics.json')
                data[arm][stage] = json.loads(p.read_text())['common']
                budget()
        for stage in STAGES:
            p = touch(CACHE/f'step{stage}/v1/geometry_arrays.npz')
            with np.load(p) as z:
                mask = z['mask'][sl].copy()
                excluded = z['excluded'][sl].copy()
            assert not excluded.any(), 'Common band excluded'
            assert int(mask.sum()) == data['v1'][stage]['area_px2']
            masks[stage] = mask
            rows.append(dict(stage=stage, area_px2=int(mask.sum()),
                             rows_with_candidate=int(mask.any(axis=1).sum()), band_rows=mask.shape[0],
                             length_px=data['v1'][stage]['length_px'],
                             mask_thickness_p50_px=data['v1'][stage]['thickness_p50_px']))
        with np.load(touch(REPAIR)) as z:
            repair_same = bool(np.array_equal(z['new_mask'][sl], masks[19]))
        assert repair_same, 'E041 candidate changed common-band definition; stop'
        predictions = []
        for arm in ARMS:
            for a,b,t in WINDOWS:
                av,bv = (data[arm][s]['area_px2'] for s in (a,b))
                assert av is not None and bv is not None
                predictions.append(dict(arm=arm, history_a=a, origin=b, target=t,
                                        stage_horizon=t-b, stage_history_gap=b-a,
                                        **forecast(a,b,t,av,bv)))
        save(out/'predictions_before_scoring.json', predictions)
        scored = []
        for pred in predictions:
            target = data[pred['arm']][pred['target']]['area_px2']
            assert target is not None
            ae0,ae1 = abs(pred['persistence']-target),abs(pred['secant']-target)
            scored.append(dict(**pred, observed_area_px2=target,
                               persistence_ae=ae0,secant_ae=ae1,gain=ae0-ae1,
                               existing_E037_query=pred['target']==23))
        table(out/'observations.csv', rows)
        table(out/'all_forecasts.csv', scored)
        nominal = [x for x in scored if x['arm']=='v1']
        sensitivity = [dict(arm=arm,
                           persistence_mae=float(np.mean([x['persistence_ae'] for x in scored if x['arm']==arm])),
                           secant_mae=float(np.mean([x['secant_ae'] for x in scored if x['arm']==arm])),
                           wins=sum(x['gain']>0 for x in scored if x['arm']==arm)) for arm in ARMS]
        table(out/'sensitivity.csv', sensitivity)
        result = dict(stage_role='development-exposed one trajectory; overlapping windows',
                      roi_xyxy=roi,common_band_xyxy=band,coverage='3/3 calculable windows',
                      E041_common_mask_identical_to_v1=repair_same,
                      common_excluded_pixels=0,observations=rows,nominal=nominal,
                      sensitivity=sensitivity,all_nine_settings_secant_better=sum(x['secant_mae']<x['persistence_mae'] for x in sensitivity),
                      prior_protected_files=len(lock['protected_old_hashes']),
                      old_scores_preserved=True, new_segmentation=False)
        save(out/'summary.json', result)
        plt.rcParams.update({'font.size':10,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False})
        fig, axes = plt.subplots(2,5,figsize=(15,4.7),layout='constrained')
        frames = {f['stage']:f for f in lock['frames']}
        for i, stage in enumerate(STAGES):
            f = frames[stage]
            source = touch(Path(f['source']))
            assert inputs[str(source)] == f['sha256']
            with Image.open(source) as im:
                crop = np.array(ImageOps.exif_transpose(im).convert('RGB').crop(band))
            axes[0,i].imshow(crop)
            axes[1,i].imshow(crop)
            rgba = np.zeros((*masks[stage].shape,4))
            rgba[masks[stage]] = (0,.55,.8,.8)
            axes[1,i].imshow(rgba)
            for ax in axes[:,i]: ax.set_axis_off()
            axes[0,i].set_title(f'Step {stage}: source')
            axes[1,i].set_title(f"{rows[i]['area_px2']} candidate px²\n{rows[i]['rows_with_candidate']}/{rows[i]['band_rows']} rows")
            budget()
        fig.suptitle('E042 R001 | Fixed common IMAGE band: native [3900,1700,4600,1950]\nFrozen masks; not material registration, crack truth or physical aperture')
        common = ('\n## Data provenance\nE042 R001; scripts/md01_cached_stage_forecast.py. Input hashes in input_manifest.json. '
                  'E038 R001 cached masks/metrics; E041 Step19 common band verified identical. '
                  'One already-exposed MD01 trajectory; native pixel coordinates. Old half-depth and scores unchanged.\n')
        figure(fig,'F01_common_band_observations', '# Common image-band observations\n\n## Figure question\nCan frozen candidate geometry be extracted across all five existing stages?\n'+common+
               '\n## Visual grammar and panels\nFive columns, stages18,19,21,22,23. Upper row source crop, lower same source with cyan candidate pixels. '
               'All crops identical native bounds and scale. Titles show pixel count and rows containing any candidate; row occupancy is NOT crack recall.\n'
               '\n## Key numerical takeaway\n'+str(rows)+'\n\n## Limitations and claim boundary\nObserver guides, residual pores and changing view remain. '
               'No actual occlusion in this band according to frozen polygons, not proof of complete visibility. No lengthening or physical-width claim.\n')
        fig,axes = plt.subplots(2,2,figsize=(12,8),layout='constrained')
        ax=axes[0,0]
        for arm in ARMS:
            values=[data[arm][s]['area_px2'] for s in STAGES]
            ax.plot(STAGES,values,'o-',color='#999999' if arm!='v1' else '#0072B2',
                    alpha=.35 if arm!='v1' else 1,lw=1 if arm!='v1' else 1.8,label='v1' if arm=='v1' else None)
        ax.set(xlabel='Relative stage (not time / kN)',ylabel='Candidate area (px²)',title='A  Frozen observations + 8 cached alternatives')
        ax.legend()
        ax=axes[0,1]
        targets=[r['target'] for r in nominal]
        for key,label,color,marker in [('observed_area_px2','Observed mask','#333333','o'),('persistence','Persistence','#E69F00','s'),('secant','Stage secant','#0072B2','^')]:
            ax.plot(targets,[r[key] for r in nominal],marker+'-',color=color,label=label,lw=1.5)
        ax.set(xlabel='Requested target stage',ylabel='Candidate area (px²)',title='B  All 3 development forecasts')
        ax.legend()
        ax=axes[1,0]
        ax.axhline(0,color='#777777',lw=.8)
        for i,r in enumerate(nominal):
            ax.plot([i,i],[r['persistence_ae'],r['secant_ae']],color='#aaaaaa')
        ax.scatter(range(3),[r['persistence_ae'] for r in nominal],color='#E69F00',marker='s',label='Persistence AE')
        ax.scatter(range(3),[r['secant_ae'] for r in nominal],color='#0072B2',marker='^',label='Secant AE')
        ax.set(xticks=range(3),xticklabels=['18,19 → 21','19,21 → 22','21,22 → 23\n(existing query)'],ylabel='Absolute error (px²)',title='C  Every window, no selection')
        ax.legend()
        ax=axes[1,1]
        gains=[r['persistence_mae']-r['secant_mae'] for r in sensitivity]
        ax.axvline(0,color='#777777',lw=.8)
        ax.scatter(gains,range(9),color=['#0072B2']+['#999999']*8)
        ax.set(yticks=range(9),yticklabels=ARMS,xlabel='Persistence MAE − secant MAE (px²)',title='D  All cached settings; right favours secant')
        ax.invert_yaxis()
        for ax in axes.flat: ax.grid(alpha=.15)
        fig.suptitle('E042 R001 | Relative-stage AREA prediction, one exposed trajectory\n3 overlapping windows, not 3 independent specimens; alternatives are not confidence intervals')
        figure(fig,'F02_area_forecast_comparison','# Relative-stage candidate-area forecasts\n\n## Figure question\nDoes stage-adjusted secant improve over persistence on all fixed windows?\n'+common+
               '\n## Visual grammar and panels\nA: five observed areas for v1 blue and eight fixed cached settings grey. '
               'B: observed dark, persistence orange square, secant blue triangle at requested stages21,22,23. '
               'C: absolute errors for all three histories. D: mean AE gain for all nine settings, zero reference; no best setting promoted. '
               'Units pixel²; stage indices are not seconds/cycles/load. Secant uses actual stage gaps and clips only negative predicted area to zero.\n'
               '\n## Key numerical takeaway\nNominal: '+str(nominal)+'\nAll settings: '+str(sensitivity)+
               '\n\n## Limitations and claim boundary\nDevelopment reconstruction, source-guided observations; target masks already exposed. '
               'No prospective blind/generalisation claim, noise calibration or physical crack-growth law. Third query is prior E037 result. '
               'Measurement-definition variation can reverse ranking. coverage=3/3 calculable windows, not segmentation recall.\n')
        budget()
        assert all(sha(p)==h for p,h in inputs.items()), 'Input changed during analysis'
        assert all(sha(p)==h for p,h in lock['protected_old_hashes'].items())
        save(out/'input_manifest.json',inputs)
        receipt.update(execution='succeeded',inputs_verified=len(inputs),retrieval='verified_local')
        print(json.dumps(result,indent=2))
    except Exception as e:
        receipt.update(execution='failed',error=repr(e))
        raise
    finally:
        receipt.update(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,
                       ended_utc=datetime.now(timezone.utc).isoformat())
        save(out/'run_receipt.json',receipt)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--output',type=Path)
    p.add_argument('--self-test',action='store_true')
    a=p.parse_args()
    if a.self_test:
        assert forecast(18,19,21,100,150)['secant']==250
        assert forecast(19,21,22,100,150)['secant']==175
        assert forecast(1,2,3,100,20)['secant']==0
        assert forecast(1,2,3,100,20)['raw_secant']==-60
        assert forecast(1,2,3,20,20)['secant']==20
        try: forecast(2,1,3,1,1)
        except ValueError: pass
        else: raise AssertionError('Invalid ordering accepted')
        print('Six deterministic arithmetic/order tests passed; no data accessed.')
    else:
        if a.output is None: p.error('--output required')
        main(a.output)
