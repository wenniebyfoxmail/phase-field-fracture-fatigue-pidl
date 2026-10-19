"""Prepare metadata or run a separately approved exploratory comparison.

No author model, label XLSX, CSV fields, external holdout or data acquisition.
--prepare reads existing inventory/candidate tables only, never torch tensors.
--run requires a human-authorised exact package; the flag is not permission.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import time
from collections import OrderedDict, defaultdict
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table(path):
    with Path(path).open(newline='') as f:
        return list(csv.DictReader(f))


def valid_candidate(row):
    keys = ['left_px', 'right_px', 'span_px', 'span_px_threshold08',
            'span_px_threshold125', 'center_row_from_first_frame']
    try:
        return row['status'] == 'candidate' and all(
            float('-inf') < float(row[k]) < float('inf') for k in keys)
    except (ValueError, KeyError, TypeError):
        return False


def build_manifest(config):
    """Use group-stage identities; never reinterpret CSV header offsets as cycles."""
    root = Path(config['data_root'])
    inv = table(root / 'pt_frame_inventory.csv')
    candidates = table(root / 'probe_v1_concentration/candidate_trajectories.csv')
    frames, by_group, cand = {}, defaultdict(list), {}
    for row in inv:
        key = (row['group'], int(row['stage']))
        if key in frames:
            raise ValueError('duplicate group-stage identity')
        member = Path(row['pt_member'])
        if member.is_absolute() or '..' in member.parts:
            raise ValueError('unsafe PT member')
        row = dict(row, stage=int(row['stage']), list_index=int(row['list_index']))
        frames[key] = row
        by_group[key[0]].append(row)
    for row in candidates:
        key = (row['group'], int(row['stage']))
        if key in cand:
            raise ValueError('duplicate candidate key')
        cand[key] = row
    cases, exclusions = [], []
    offsets = config['history_stage_offsets']
    horizons = config['horizon_stage_steps']
    assert max(offsets) == 0 and min(offsets) < 0 and all(h > 0 for h in horizons)
    for group, rows in sorted(by_group.items()):
        rows.sort(key=lambda r: r['stage'])
        first_stage = rows[0]['stage']
        accepted = []
        for origin in rows:
            n = origin['stage']
            if (n - first_stage) % config['origin_stride']:
                continue
            needed = [n + o for o in offsets] + [n + h for h in horizons]
            block = [frames.get((group, s)) for s in needed]
            reason = None
            if any(r is None for r in block):
                reason = 'missing_history_or_future_release_stage'
            elif any(int(r['nonfinite_values']) != 0 for r in block):
                reason = 'nonfinite_published_field'
            elif len({r['pt_member'] for r in block}) != 1:
                reason = 'crosses_published_PT_chunk_boundary'
            elif any(not valid_candidate(cand.get((group, n + o), {})) for o in offsets):
                reason = 'current_or_past_set_or_point_unavailable'
            else:
                # This is only release-index continuity, not physical reference closure.
                full = [frames.get((group, s)) for s in range(min(needed), max(needed)+1)]
                if any(r is None or int(r['nonfinite_values']) != 0 for r in full):
                    reason = 'gap_or_nonfinite_inside_window'
            if reason:
                exclusions.append({'group': group, 'origin_stage': n, 'reason': reason})
            else:
                accepted.append({'group': group, 'origin_stage': n,
                                 'history_stages': [n + o for o in offsets],
                                 'targets': {str(h): n + h for h in horizons},
                                 'pt_member': origin['pt_member'],
                                 'center_row': int(float(cand[(group,n)]['center_row_from_first_frame']))})
        cap = config['max_origins_per_group']
        if len(accepted) > cap:
            # Uniform selection across an already development-exposed release.
            picks = {i*(len(accepted)-1)//(cap-1) for i in range(cap)}
            accepted = [r for i,r in enumerate(accepted) if i in picks]
        if len(accepted) < config['minimum_origins_per_group']:
            exclusions.append({'group': group, 'reason': 'too_few_complete_release_windows',
                               'available': len(accepted)})
        else:
            cases.extend(accepted)
    if len({r['group'] for r in cases}) < 4:
        raise ValueError('insufficient released groups for outer/inner grouped comparison')
    sources = {str(p): digest(p) for p in [root/'pt_frame_inventory.csv',
               root/'probe_v1_concentration/candidate_trajectories.csv',
               root/'pt_structure_summary.json', root/'full_csv_header_audit.json']}
    expected = config.get('metadata_sha256')
    if expected is not None and sources != expected:
        raise ValueError('reviewed inventory/candidate metadata changed')
    return {'cases': cases, 'exclusions': exclusions, 'metadata_sha256': sources,
            'claim': 'development-exposed published DIC grid, release-stage continuation only',
            'grouping': 'released group code; physical independence not established',
            'cycle_status': '10/40 stages = 300/1200 README-nominal cycles, not machine cycles'}, frames, cand


class Loader:
    def __init__(self, root):
        self.root, self.cache, self.hashes = Path(root), OrderedDict(), {}
        self.fields = OrderedDict()

    def get(self, row):
        import numpy as np
        import torch
        path = self.root/'pt_extracted'/row['pt_member']
        key = (path, row['list_index'])
        if key in self.fields:
            self.fields.move_to_end(key)
            return self.fields[key]
        if path not in self.cache:
            self.hashes[str(path)] = digest(path)
            values = torch.load(path, weights_only=True, map_location='cpu')
            if not isinstance(values, (list, tuple)):
                raise ValueError('PT container changed')
            self.cache[path] = values
            if len(self.cache) > 8:
                self.cache.popitem(last=False)
        values = self.cache[path]
        self.cache.move_to_end(path)
        a = values[row['list_index']].detach().numpy()
        if a.shape != (1,2,128,128) or not np.isfinite(a).all():
            raise ValueError('runtime shape/finite mismatch')
        # Own the frame storage, rather than pinning a complete serialized chunk.
        field = a[0].astype(np.float32, copy=True)
        self.fields[key] = field
        if len(self.fields) > 8192:  # <=1 GiB for the fixed release shape.
            self.fields.popitem(last=False)
        return field


def pool(a, side):
    c,h,w = a.shape
    assert h % side == 0 and w % side == 0
    return a.reshape(c,side,h//side,side,w//side).mean((2,4))


def metadata_features(group):
    m = re.fullmatch(r'([CE])_(\d+)Deg_([\d.]+)%_#(\d+)', group)
    if not m:
        raise ValueError('unrecognised group metadata')
    # Repeat number is deliberately not a model feature.
    return [float(m[1]=='E'), float(m[2])/30., float(m[3])/20.]


def state_features(a, row, arm, variant, fixed_half_width):
    import numpy as np
    span = float(row['span_px'])
    width = float(row['span_px_threshold08']) if variant < 0 else (
        float(row['span_px_threshold125']) if variant > 0 else span)
    if arm == 'rich_fixed':
        width = span + variant*fixed_half_width
    elif arm != 'rich_set':
        width = span
    width = float(np.clip(width,0,127))
    values = [width/128., (width/128.)**2]
    if arm != 'scalar':
        # Same schema for point/fixed/set: richer measurement/field summary.
        # Left/right are omitted for every arm: not exported for threshold variants.
        c = int(float(row['center_row_from_first_frame']))
        band = a[:,max(0,c-16):min(128,c+17)]
        values += list(a.mean((1,2))) + list(a.std((1,2)))
        values += list(band.mean((1,2))) + list(band.std((1,2)))
    if arm.startswith('rich'):
        values += list(pool(a,8).ravel())
    return np.asarray(values, dtype=np.float64)


def scenario_from_point(point, row, arm, variant, width):
    """Exactly the same scalar intervention, reusing invariant field features."""
    import numpy as np
    if arm not in ('rich_fixed','rich_set'):
        return point
    state = point.copy()
    span = float(row['span_px'])
    if arm == 'rich_fixed':
        span += variant*width
    elif variant != 0:
        span = float(row['span_px_threshold08' if variant<0 else 'span_px_threshold125'])
    scaled = np.clip(span,0,127)/128.
    state[:2] = [scaled,scaled**2]
    return state


def ridge_fit(x, y, alpha, weights=None):
    import numpy as np
    mean, scale = x.mean(0), x.std(0)
    scale[scale < 1e-8] = 1.
    z = np.column_stack([np.ones(len(x)), (x-mean)/scale])
    # Mean per-case loss; each of the three deterministic set scenarios has 1/3 weight.
    if weights is None:
        weights = np.full(len(z), 1./len(z))
    penalty = np.eye(z.shape[1])*alpha
    penalty[0,0] = 0.
    coef = np.linalg.solve(z.T@(weights[:,None]*z)+penalty,
                           z.T@(weights[:,None]*y))
    return mean, scale, coef


def ridge_predict(model, x):
    import numpy as np
    mean, scale, coef = model
    return np.column_stack([np.ones(len(x)), (x-mean)/scale])@coef


def score(prediction, target, center, normalizer, half_height):
    import numpy as np
    err = np.abs(prediction-target)/normalizer[:,None,None]
    lo,hi = max(0,center-half_height), min(128,center+half_height+1)
    full, local = float(err.mean()), float(err[:,lo:hi].mean())
    return (.5*full+.5*local, float(np.abs(prediction-target).mean()),
            float(np.abs(prediction-target)[:,lo:hi].mean()), full, local)


def execute(config, manifest, frames, candidates, out):
    import numpy as np
    import torch
    torch.set_num_threads(config['threads'])
    start = time.monotonic()
    def check():
        if time.monotonic()-start > config['wall_seconds']:
            raise TimeoutError('budget reached; no automatic retry')
        if sum(p.stat().st_size for p in out.rglob('*') if p.is_file()) > config['max_output_gib']*2**30:
            raise RuntimeError('output storage budget reached')
    loader = Loader(config['data_root'])
    state_cache = {}
    cases = manifest['cases']
    groups = sorted({r['group'] for r in cases})
    records = []
    # Entire released groups held out. All are previously development-exposed.
    for outer, held in enumerate(groups):
        development = [g for g in groups if g != held]
        inner_valid = set(development[::4])
        if len(set(development)-inner_valid) < 2:
            raise ValueError('inner grouped training too small')
        idx_fit = [i for i,c in enumerate(cases) if c['group'] in set(development)-inner_valid]
        idx_val = [i for i,c in enumerate(cases) if c['group'] in inner_valid]
        idx_dev = [i for i,c in enumerate(cases) if c['group'] != held]
        idx_test = [i for i,c in enumerate(cases) if c['group'] == held]
        for horizon in config['horizon_stage_steps']:
            check()
            delta, summaries, spread = [], [], []
            # No full-field target cache; release arrays loaded through bounded LRU.
            for c in cases:
                g,n = c['group'],c['origin_stage']
                current = loader.get(frames[(g,n)])
                future = loader.get(frames[(g,n+horizon)])
                delta.append(pool(future-current,config['pool_output_side']).ravel())
                summaries.append(np.mean(np.abs(future-current),axis=(1,2)))
                spread.append(abs(float(candidates[(g,n)]['span_px_threshold08'])-
                                  float(candidates[(g,n)]['span_px_threshold125']))/2)
            y = np.asarray(delta)
            # Fold normalization is from DEVELOPMENT target increments only, never held group.
            norm_inner = np.maximum(np.mean(np.asarray(summaries)[idx_fit],axis=0),1e-6)
            norm_final = np.maximum(np.mean(np.asarray(summaries)[idx_dev],axis=0),1e-6)
            def feature_matrix(arm, indexes, width, variant):
                values=[]
                for i in indexes:
                    c=cases[i];g=c['group'];f=metadata_features(g)+[horizon/40.]
                    for n in c['history_stages']:
                        base_arm = 'rich' if arm.startswith('rich') else arm
                        key = (g,n,base_arm)
                        if key not in state_cache:
                            state_cache[key] = state_features(loader.get(frames[(g,n)]),
                                candidates[(g,n)],base_arm,0,0.)
                        state = scenario_from_point(state_cache[key],candidates[(g,n)],arm,variant,width)
                        f.extend(state)
                    values.append(f)
                return np.asarray(values)
            def predict_cases(arm, trainidx, predictidx, alpha):
                width = float(np.median(np.asarray(spread)[trainidx]))
                variants = [-1,0,1] if arm in ('rich_fixed','rich_set') else [0]
                x=np.concatenate([feature_matrix(arm,trainidx,width,k) for k in variants])
                yy=np.concatenate([y[trainidx] for _ in variants])
                # Each group has the same total fitting weight, then each case/scenario shares it.
                counts={g:sum(cases[i]['group']==g for i in trainidx) for g in groups}
                ww=np.array([1./counts[cases[i]['group']] for _ in variants for i in trainidx])
                ww/=ww.sum()
                model=ridge_fit(x,yy,alpha,ww)
                preds=np.asarray([ridge_predict(model,feature_matrix(arm,predictidx,width,k)) for k in variants])
                # Min/max is a scenario envelope, no probability or coverage guarantee.
                return (preds.min(0)+preds.max(0))/2, preds.min(0), preds.max(0), model
            def evaluate(preds,indexes,norm):
                scores=defaultdict(list)
                for k,i in enumerate(indexes):
                    c=cases[i];g,n=c['group'],c['origin_stage']
                    current=loader.get(frames[(g,n)])
                    target=loader.get(frames[(g,n+horizon)])
                    residual=np.repeat(np.repeat(preds[k].reshape(2,16,16),8,axis=1),8,axis=2)
                    scores[g].append(score(current+residual,target,c['center_row'],norm,config['local_band_half_height'])[0])
                return float(np.mean([np.mean(s) for s in scores.values()]))
            for arm in config['arms']:
                check(); choices=[]
                for alpha in config['ridge_alphas']:
                    prediction,_,_,_=predict_cases(arm,idx_fit,idx_val,alpha)
                    choices.append((evaluate(prediction,idx_val,norm_inner),alpha))
                selected=min(choices)[1]
                prediction,lower,upper,model=predict_cases(arm,idx_dev,idx_test,selected)
                np.savez_compressed(out/f'fold{outer}_{horizon}_{arm}.npz',
                    coarse_delta=prediction,scenario_lower=lower,
                    scenario_upper=upper,case_indices=idx_test,
                    training_fixed_half_width=float(np.median(np.asarray(spread)[idx_dev])),
                    normalizer=norm_final,feature_mean=model[0],feature_scale=model[1],coef=model[2])
                for k,i in enumerate(idx_test):
                    c=cases[i];g,n=c['group'],c['origin_stage']
                    current=loader.get(frames[(g,n)]);target=loader.get(frames[(g,n+horizon)])
                    residual=np.repeat(np.repeat(prediction[k].reshape(2,16,16),8,axis=1),8,axis=2)
                    balanced,mae,local_mae,full_norm,local_norm=score(current+residual,target,c['center_row'],norm_final,config['local_band_half_height'])
                    records.append(dict(group=g,origin_stage=n,horizon_stages=horizon,arm=arm,
                                        balanced_nmae=balanced,full_mae=mae,local_mae=local_mae,
                                        full_nmae=full_norm,local_nmae=local_norm,alpha=selected))
            # Native-grid, same-prefix persistence/secant; no author Predicted column.
            for i in idx_test:
                c=cases[i];g,n=c['group'],c['origin_stage']
                current=loader.get(frames[(g,n)]);past=loader.get(frames[(g,n-10)])
                target=loader.get(frames[(g,n+horizon)])
                oracle_delta=np.repeat(np.repeat(pool(target-current,16),8,axis=1),8,axis=2)
                for arm,pred in [('persistence',current),('secant',current+(current-past)*horizon/10.),
                                 ('oracle_output_projection',current+oracle_delta)]:
                    balanced,mae,local_mae,full_norm,local_norm=score(pred,target,c['center_row'],norm_final,config['local_band_half_height'])
                    records.append(dict(group=g,origin_stage=n,horizon_stages=horizon,arm=arm,
                                        balanced_nmae=balanced,full_mae=mae,local_mae=local_mae,
                                        full_nmae=full_norm,local_nmae=local_norm,alpha=None))
        # Persist completed fold immediately; exceptions cannot masquerade as complete results.
        with (out/'per_case_scores.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
        (out/'progress.json').write_text(json.dumps({'completed_groups':outer+1,'total_groups':len(groups)}))
    # Exactly equal group/horizon weights for the one primary deterministic criterion.
    aggregated=defaultdict(lambda:defaultdict(list))
    for r in records:aggregated[r['arm']][(r['group'],r['horizon_stages'])].append(r['balanced_nmae'])
    primary={arm:float(np.mean([np.mean(x) for x in cells.values()])) for arm,cells in aggregated.items()}
    oracle_floor=primary.pop('oracle_output_projection',None)
    (out/'summary.json').write_text(json.dumps({'primary_balanced_nmae':primary,
        'diagnostic_oracle_output_projection':oracle_floor,
        'scope':'exploratory release-grid continuation; not calibrated physical UQ',
        'elapsed_seconds':time.monotonic()-start,'PT_sha256':loader.hashes},indent=2))
    render_results(records,cases,frames,loader,config,out)


def render_results(records,cases,frames,loader,config,out):
    """Deterministic example choice: midpoint retained origin in EVERY release group."""
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    groups=sorted({r['group'] for r in records})
    arms=config['arms']+['persistence','secant']
    fig,axes=plt.subplots(1,2,figsize=(14,5))
    for ax,metric in zip(axes,['full_nmae','local_nmae']):
        for arm in arms:
            values=[np.mean([r[metric] for r in records if r['group']==g and r['arm']==arm]) for g in groups]
            ax.plot(range(len(groups)),values,'o-',label=arm,markersize=3)
        ax.set(title=metric+' (release group equal weight)',xlabel='released group index',ylabel='normalised MAE')
    axes[1].legend(fontsize=7);fig.tight_layout();fig.savefig(out/'group_full_local_scores.png',dpi=150);plt.close(fig)
    for fold,g in enumerate(groups):
        for h in config['horizon_stage_steps']:
            rs=[(i,c) for i,c in enumerate(cases) if c['group']==g]
            i,c=rs[len(rs)//2];n=c['origin_stage']
            current=loader.get(frames[(g,n)]);future=loader.get(frames[(g,n+h)])
            predictions={}
            for arm in ['rich','rich_set']:
                with np.load(out/f'fold{fold}_{h}_{arm}.npz') as z:
                    k=list(z['case_indices']).index(i)
                    d=z['coarse_delta'][k].reshape(2,16,16)
                    predictions[arm]=current+np.repeat(np.repeat(d,8,axis=1),8,axis=2)
            arrays=[future[1]-current[1],predictions['rich'][1]-current[1],
                    predictions['rich_set'][1]-current[1],
                    np.abs(predictions['rich'][1]-future[1]),
                    np.abs(predictions['rich_set'][1]-future[1])]
            lim=max(float(np.max(np.abs(x))) for x in arrays[:3]) or 1e-9
            errlim=max(float(np.max(x)) for x in arrays[3:]) or 1e-9
            fig,axs=plt.subplots(1,5,figsize=(16,4))
            for j,(ax,arr,title) in enumerate(zip(axs,arrays,['published future delta-v','rich point delta-v','set delta-v','point absolute error','set absolute error'])):
                im=ax.imshow(arr,cmap='coolwarm' if j<3 else 'magma',vmin=-lim if j<3 else 0,vmax=lim if j<3 else errlim)
                for y in [max(0,c['center_row']-16),min(127,c['center_row']+16)]:ax.axhline(y,color='lime',lw=.7)
                ax.set_title(title,fontsize=8);fig.colorbar(im,ax=ax,fraction=.046)
            fig.suptitle(f'{g}; origin release-stage {n}; H={h} release steps; no physical crack truth',fontsize=9)
            fig.tight_layout();fig.savefig(out/f'field_group{fold}_H{h}.png',dpi=130);plt.close(fig)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',type=Path,default=Path(__file__).with_name('config.json'))
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--prepare',action='store_true')
    p.add_argument('--run',action='store_true')
    p.add_argument('--approved-package-sha256')
    args=p.parse_args()
    if args.prepare == args.run: p.error('choose exactly one mode')
    config=json.loads(args.config.read_text())
    if (config['history_stage_offsets'] != [-20,-10,0]
            or config['pool_input_side'] != 8 or config['pool_output_side'] != 16):
        p.error('v0.1 fixed temporal/spatial interface changed; revise implementation first')
    # Static core only: data-dependent imports occur solely in execute().
    package=hashlib.sha256(Path(__file__).read_bytes()+args.config.read_bytes()).hexdigest()
    if args.run and args.approved_package_sha256 != package:
        p.error('exact reviewed source/config package hash required; this flag does not grant authorisation')
    if args.output.exists():p.error('fresh output directory required; no overwrite/retry')
    args.output.mkdir(parents=True)
    manifest,frames,candidates=build_manifest(config)
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (args.output/'receipt.json').write_text(json.dumps({'package_sha256':package,
        'mode':'metadata_prepare' if args.prepare else 'approved_exploration',
        'status':'PREPARED' if args.prepare else 'RUNNING'}))
    if args.run:
        for key in ('OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS'):
            os.environ[key] = str(config['threads'])
        try:
            execute(config,manifest,frames,candidates,args.output)
        except Exception as exc:
            (args.output/'receipt.json').write_text(json.dumps({
                'package_sha256':package,'status':'FAILED_NO_RETRY',
                'error':type(exc).__name__+': '+str(exc)}))
            raise
        (args.output/'receipt.json').write_text(json.dumps({'package_sha256':package,'status':'COMPLETE'}))


if __name__ == '__main__':
    main()
