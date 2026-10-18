"""E046: unchanged accepted E045 observer, E043 predictors; development replay."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import matplotlib.pyplot as plt
import numpy as np

from md01_cached_stage_forecast import ROOT, WORK, sha, save, table
from md01_frame_geometry import read_frame, extract
from md01_geometric_guide_transfer import transfer, tests as guide_tests
from md01_support_mass_forecast import observe, predict, tests as prediction_tests
from md01_support_mass_forecast import METHODS, COLORS, LABELS

ACCEPTED = ROOT/'local_archive/experiments/S03-E045-MD01/runs'
LOCK45 = ACCEPTED/'S03-E045-MD01-R000/input_lock.json'
SOURCE = WORK/'docs/research/S03/S03-E037-MD01/source_lock.json'
PROTOCOL = WORK/'docs/research/S03/S03-E046-MD01/experiment.md'
WINDOWS = ((22, 23, 24), (23, 24, 25), (24, 25, 26))


def prefix_prediction(history, a, b, t, width):
    if any(s > b for s in history):
        raise ValueError('Future observation in history')
    return predict(history[a], history[b], a, b, t, width)


def tests():
    guide_tests(); prediction_tests()
    h = {22: dict(area=8, support=4, mass=2.),
         23: dict(area=12, support=4, mass=3.)}
    p = prefix_prediction(h, 22, 23, 24, 700)
    assert p['persistence'] == 12 and p['secant'] == p['support_hold'] == 16
    try:
        prefix_prediction(h | {24: {}}, 22, 23, 24, 700)
    except ValueError:
        pass
    else:
        raise AssertionError('Future-input guard failed')
    print('History-prefix guard and unchanged predictor tests passed.')


def prepare(out):
    out.mkdir(parents=True, exist_ok=False)
    old = json.loads(LOCK45.read_text())
    source = json.loads(SOURCE.read_text())
    frames = [f for f in source['frames'] if f['stage'] in (22, 23)]
    assert [f['stage'] for f in frames] == [22, 23]
    protected = dict(old['protected_inputs'])
    for p in sorted(ACCEPTED.rglob('*')):
        if p.is_file(): protected[str(p)] = sha(p)
    for p in (SOURCE, PROTOCOL, Path(__file__),
              WORK/'scripts/md01_cached_stage_forecast.py'):
        protected[str(p)] = sha(p)
    for f in frames:
        p = Path(f['source'])
        assert p.stat().st_size == f['bytes'] and sha(p) == f['sha256']
        protected[str(p)] = f['sha256']
    assert all(sha(p) == h for p, h in protected.items())
    save(out/'input_lock.json', dict(protocol='E046-consistent-E045-v1',
         history_frames=frames, target_frames=old['frames'], roi=old['roi'],
         band=old['band'], original_support=old['original_support'], windows=WINDOWS,
         protected_inputs=protected, prepared_utc=datetime.now(timezone.utc).isoformat(),
         exposure='all five frames already viewed; development replay, not blind',
         no_history_reextraction_yet=True))
    save(out/'prepare_receipt.json', dict(execution='succeeded',
         lock_sha256=sha(out/'input_lock.json'), protected_files=len(protected)))
    print('Frozen E046 input lock:', len(protected), 'protected files')


def run(lockpath, out):
    start, cpu = time.monotonic(), time.process_time()
    out.mkdir(parents=True, exist_ok=False)
    lock = json.loads(lockpath.read_text()); protected = lock['protected_inputs']
    receipt = dict(execution='running', host=socket.gethostname(), pid=os.getpid(),
         runtime=sys.executable, command=sys.argv, started_utc=datetime.now(timezone.utc).isoformat(),
         commit=subprocess.check_output(['git','rev-parse','HEAD'], cwd=WORK, text=True).strip(),
         dirty=subprocess.check_output(['git','status','--porcelain'], cwd=WORK, text=True).splitlines(),
         lock_sha256=sha(lockpath), code_sha256=sha(Path(__file__)))
    save(out/'run_start_receipt.json', receipt)

    def guard():
        assert sha(lockpath) == receipt['lock_sha256']
        assert all(sha(p) == h for p, h in protected.items())

    def budget():
        if max(time.monotonic()-start, time.process_time()-cpu) > 90:
            raise TimeoutError('90s deterministic replay budget')

    roi, band = lock['roi'], lock['band']
    x0,y0,x1,y1 = np.array(band)-np.array([roi[0],roi[1],roi[0],roi[1]])
    sl = np.s_[y0:y1,x0:x1]
    history, observations, events, scored = {}, [], [], []

    def record(stage, mask, rgb, source, **extra):
        assert mask.dtype == bool and mask.shape == (y1-y0,x1-x0)
        v, row = observe(mask)
        assert v['mass'] is None or abs(v['area']-v['support']*v['mass']) < 1e-9
        case = out/f'step{stage}'; case.mkdir(exist_ok=True)
        # Target pixels are exact copies in a separate archive, never re-extracted.
        np.savez_compressed(case/'observation_arrays.npz', band_mask=mask, band_rgb=rgb, row_mass=row)
        r = dict(stage=stage, **v, mask_source=source, **extra)
        save(case/'observation.json', r)
        history[stage] = v; observations.append(r)
        events.append(dict(event='observation_available', stage=stage,
                           observation_sha256=sha(case/'observation.json')))
        return v

    try:
        guard()
        assert lock['windows'] == [list(w) for w in WINDOWS]
        for f in lock['history_frames']:
            budget(); s = f['stage']; rgb = read_frame(f, roi)
            support, diag, eligible, path = transfer(rgb, lock['original_support'], roi, band)
            case = out/f'step{s}'; case.mkdir()
            save(case/'guide_before_extraction.json', dict(support=support, diagnostic=diag))
            mask, excluded, _ = extract(rgb, support, roi)
            assert not excluded[sl].any() and not (mask & ~eligible).any()
            np.savez_compressed(case/'geometry_arrays.npz', mask=mask, excluded=excluded, guide_path_native=path)
            record(s, mask[sl], rgb[sl], f['source'], transferred_guide=diag)
        for a,b,t in WINDOWS:
            budget(); query = out/f'W{t}'; query.mkdir()
            pred = prefix_prediction(history, a, b, t, x1-x0)
            snapshot = dict(history_a=a, origin=b, target=t, horizon=t-b,
                            available_stages=sorted(history), history={str(s):history[s] for s in (a,b)},
                            measurement_version='E045-geometry-guide-v1', **pred)
            save(query/'predictions_before_target.json', snapshot)
            events.append(dict(event='prediction_saved', target=t,
                               prediction_sha256=sha(query/'predictions_before_target.json')))
            path = ACCEPTED/f'S03-E045-MD01-R001/step{t}/comparison_arrays.npz'
            # No target mask is decoded in this run until its forecast is saved.
            with np.load(path) as z:
                target_mask = z['new_mask'][sl].copy(); rgb = z['band_rgb'].copy()
            observed = record(t, target_mask, rgb, str(path), accepted_archive_sha256=sha(path))
            accepted = json.loads((path.parent/'summary.json').read_text())['new_observation']
            assert observed == accepted
            with np.load(out/f'step{t}/observation_arrays.npz') as z:
                assert np.array_equal(z['band_mask'], target_mask)
            r = dict(history_a=a, origin=b, target=t, horizon=t-b, **pred,
                     observed_area=observed['area'], observed_support=observed['support'],
                     observed_mass=observed['mass'])
            for m in METHODS:
                r[m+'_ae'] = None if pred[m] is None else abs(pred[m]-observed['area'])
            r['gain_vs_persistence'] = r['persistence_ae']-r['support_hold_ae'] if pred['support_hold'] is not None else None
            r['gain_vs_secant'] = r['secant_ae']-r['support_hold_ae'] if pred['support_hold'] is not None else None
            save(query/'comparison.json', r); scored.append(r)
        means = {m: float(np.mean([r[m+'_ae'] for r in scored if r[m+'_ae'] is not None])) for m in METHODS}
        summary = dict(role='one already-exposed trajectory, three overlapping development windows',
             measurement_version='E045-geometry-guide-v1', observations=observations,
             windows=scored, mae=means, calculable={m:sum(r[m] is not None for r in scored) for m in METHODS},
             total=3, accepted_target_masks_exact=3, historical_extractions=2,
             all_secant_separated_equal=all(r['secant']==r['support_hold'] for r in scored),
             separated_gain_fraction_vs_persistence=1-means['support_hold']/means['persistence'],
             old_halfdepth_masks_scores_unchanged=True, no_new_images=True, no_parameter_selection=True)
        save(out/'summary.json', summary); table(out/'comparisons.csv', scored)
        save(out/'observations.json', observations); save(out/'event_order.json', events)
        for _,_,t in WINDOWS:
            pi = next(i for i,e in enumerate(events) if e['event']=='prediction_saved' and e['target']==t)
            oi = next(i for i,e in enumerate(events) if e['event']=='observation_available' and e['stage']==t)
            assert pi < oi
        guard(); budget()
        receipt.update(execution='succeeded', retrieval='verified_local',
                       protected_files_verified=len(protected), target_masks_exact=3,
                       forecast_before_target_chains_verified=3)
        print(json.dumps(dict(mae=means, windows=scored, observations=observations), indent=2))
    except Exception as e:
        receipt.update(execution='failed', error=repr(e)); raise
    finally:
        receipt.update(wall_seconds=time.monotonic()-start, cpu_seconds=time.process_time()-cpu,
                       ended_utc=datetime.now(timezone.utc).isoformat())
        save(out/'run_receipt.json', receipt)


def plot(source, out):
    out.mkdir(parents=True, exist_ok=False)
    j = json.loads((source/'summary.json').read_text())
    plt.rcParams.update({'font.size':10, 'pdf.fonttype':42, 'axes.spines.top':False, 'axes.spines.right':False})
    prov = f'\n## Data provenance\nE046 R001: {source}. Renderer scripts/md01_consistent_observer_forecast.py. '
    limits = ('\n## Limitations and claim boundary\nOne exposed trajectory, overlapping development windows, no independent truth/test. '
              'Fixed native image band [3900,1700,4600,1950]; relative stage not time/kN. '
              'A candidate area px², L occupied image rows, M conditional pixels/row; not physical length/aperture or half-depth width. '
              'Current-image measurement is not a predicted future mask. Shadows/pores/gaps can remain. All old scores preserved.\n')

    def export(fig, stem, text):
        fig.savefig(out/f'{stem}.png', dpi=240); fig.savefig(out/f'{stem}.pdf'); plt.close(fig)
        (out/f'{stem}.md').write_text(text)

    fig, axes = plt.subplots(5,2,figsize=(12,11),layout='constrained')
    for axs,o in zip(axes,j['observations']):
        with np.load(source/f"step{o['stage']}/observation_arrays.npz") as z:
            rgb=z['band_rgb']; mask=z['band_mask']
        axs[0].imshow(rgb); axs[1].imshow(rgb)
        overlay=np.zeros((*mask.shape,4)); overlay[mask]=(.35,.25,.65,.8); axs[1].imshow(overlay)
        axs[0].set_title(f"Step {o['stage']} | source")
        axs[1].set_title(f"Accepted rule | A={o['area']}, L={o['support']}, M={o['mass']:.2f}")
        for ax in axs: ax.set_axis_off()
    fig.suptitle('E046 R001 → R002 | Same observer across stages22–26\n22/23 newly measured;24/25/26 reused exactly; purple = candidate pixels',fontsize=13)
    export(fig,'F01_consistent_observations','# How to read: all five consistent observations\n\n## Figure question\nWhat sequence enters prediction after accepting E045?\n'+prov+
           '\n## Visual grammar and panels\nRows all fixed stages22–26, columns source / purple mask. Same crop and scale; no best-case selection. '
           'L counts rows with any candidate, M counts mean candidate pixels in these rows, not normal thickness.\n'
           '\n## Key numerical takeaway\n'+json.dumps(j['observations'],indent=2)+limits)
    fig, axes=plt.subplots(2,3,figsize=(13,7.8),layout='constrained')
    all_areas=[o['area'] for o in j['observations']]+[r[m] for r in j['windows'] for m in METHODS]
    pad=max(100,.08*(max(all_areas)-min(all_areas)))
    area_limits=(max(0,min(all_areas)-pad),max(all_areas)+pad)
    error_limit=max(100,1.18*max(r[m+'_ae'] for r in j['windows'] for m in METHODS))
    for k,r in enumerate(j['windows']):
        ax=axes[0,k]; a,b,t=r['history_a'],r['origin'],r['target']
        oo={o['stage']:o for o in j['observations']}
        ax.plot([a,b],[oo[a]['area'],oo[b]['area']],'o-',color='#333333',label='Observed history',lw=1.5)
        ax.scatter([t],[r['observed_area']],s=65,color='#333333',label='Target observation',zorder=5)
        for m,c,l,marker in zip(METHODS,COLORS,LABELS,('s','^','D')):
            ax.plot([b,t],[oo[b]['area'],r[m]],'--',color=c,lw=1.4)
            ax.scatter([t],[r[m]],marker=marker,s=75 if m=='secant' else 40,
                       facecolors='none' if m=='support_hold' else c,edgecolors=c,label=l,zorder=4)
        ax.axvline(b+.08,color='#bbbbbb',lw=.8)
        ax.set(title=f'{a},{b} → {t} | origin={b}, horizon=1',xlabel='Relative stage',
               ylabel='Candidate area (px²)',xticks=[a,b,t],ylim=area_limits)
        if k==0: ax.legend(fontsize=7,loc='upper left')
        ax=axes[1,k]; vals=[r[m+'_ae'] for m in METHODS]
        bars=ax.bar(np.arange(3),vals,color=COLORS,width=.6)
        for bar,v in zip(bars,vals): ax.text(bar.get_x()+bar.get_width()/2,v+25,f'{v:.0f}',ha='center',fontsize=10)
        ax.set(xticks=np.arange(3),xticklabels=['Hold','Area trend','Separated'],
               ylabel='Absolute error (px²)',ylim=(0,error_limit),title=f"Separated gain vs hold: {r['gain_vs_persistence']:+.0f} px²")
    for ax in axes.flat: ax.grid(axis='y',alpha=.15)
    fig.suptitle('E046 | Every fixed window, same new measurement version | Coverage3/3 each\nArea trend and separated prediction coincide; development replay, not blind validation',fontsize=13)
    export(fig,'F02_every_window_forecast','# How to read: every fixed-window prediction\n\n## Figure question\nDoes accepted-observer trend prediction improve on persistence?\n'+prov+
           '\n## Visual grammar and panels\nColumns fixed22,23→24;23,24→25;24,25→26. Top historyblack and targetblack dot; '
           'orange persistence, blue area secant, green opendiamond separated; blue/green overlap exactly. '
           'Bottom absoluteerror bars on sharedscale, numbers and positivegain label; all cases, no selection.\n'
           '\n## Key numerical takeaway\n'+json.dumps({'mae':j['mae'],'windows':j['windows']},indent=2)+limits)
    save(out/'render_receipt.json',dict(execution='succeeded',source_summary_sha256=sha(source/'summary.json'),
         renderer_sha256=sha(Path(__file__)),figures=2,numerical_rerun=False,
         output_hashes={p.name:sha(p) for p in out.iterdir() if p.is_file()}))


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('mode',choices=['self-test','prepare','run','plot'])
    p.add_argument('--output',type=Path); p.add_argument('--source',type=Path); p.add_argument('--lock',type=Path)
    args=p.parse_args()
    if args.mode=='self-test': tests()
    elif args.mode=='prepare': prepare(args.output)
    elif args.mode=='run': run(args.lock,args.output)
    else: plot(args.source,args.output)
