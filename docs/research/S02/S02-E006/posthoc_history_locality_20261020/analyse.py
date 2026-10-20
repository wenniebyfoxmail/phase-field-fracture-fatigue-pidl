"""Read saved predictions and published fields; never fit or evaluate coefficients."""
import argparse
import csv
import json
import os
import re
import socket
import time
from collections import OrderedDict, defaultdict
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
import numpy as np
import pandas as pd
import torch
from scipy.stats import spearmanr

ROOT = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
SOURCE = ROOT/'local_archive/experiments/IU-BRIDGE-PS-20261019-R003/retrieved/outputs'
DATA = ROOT/'local_archive/open_data/mendeley_full_displacement_20261017'
ARMS = ['H_INNOV', 'B_STAR', 'C_RAW']
REGIONS = ['full', 'band', 'outside_band', 'edge8', 'interior']


def read_json(p):
    return json.loads(p.read_text())


def write_json(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def identity(paths):
    return {str(p): [p.stat().st_size, p.stat().st_mtime_ns] for p in paths}


def balanced(err, center):
    return .5*err.mean()+.5*err[:, max(0, center-16):min(128, center+17)].mean()


def masks(center):
    band = np.zeros((128, 128), bool)
    band[max(0, center-16):min(128, center+17)] = True
    edge = np.ones((128, 128), bool)
    edge[8:-8, 8:-8] = False
    return {'full': np.ones_like(band), 'band': band, 'outside_band': ~band,
            'edge8': edge, 'interior': ~edge}


def thirds(indices):
    """Deterministic retained-origin rank, never a fatigue-life fraction."""
    return {i: min(2, rank*3//len(indices)) for rank, i in enumerate(indices)}


def weighted_summary(df, by):
    """First origins within group/horizon/stratum; then horizons, then groups."""
    cols = ['B_STAR', 'C_RAW', 'H_INNOV', 'gain_B_STAR', 'gain_C_RAW']
    if isinstance(by, str):
        by = [by]
    one_keys = list(dict.fromkeys(['group', 'horizon']+by))
    two_keys = list(dict.fromkeys(['group']+by))
    one = df.groupby(one_keys, dropna=False)[cols].mean().reset_index()
    two = one.groupby(two_keys, dropna=False)[cols].mean().reset_index()
    out = two.groupby(by, dropna=False)[cols].mean().reset_index()
    out = out.merge(df.groupby(by, dropna=False).size().rename('case_horizon_n').reset_index(), on=by)
    out = out.merge(two.groupby(by, dropna=False).size().rename('groups_n').reset_index(), on=by)
    out['relative_reduction_B_STAR_pct'] = 100*out.gain_B_STAR/out.B_STAR
    out['relative_reduction_C_RAW_pct'] = 100*out.gain_C_RAW/out.C_RAW
    return out


class Fields:
    def __init__(self, inventory):
        self.rows = {(r['group'], int(r['stage'])): r for r in inventory}
        self.cache = OrderedDict()
        self.paths = set()

    def get(self, group, stage):
        r = self.rows[(group, stage)]
        p = DATA/'pt_extracted'/r['pt_member']
        self.paths.add(p)
        if p not in self.cache:
            v = torch.load(p, map_location='cpu', weights_only=True)
            self.cache[p] = v
            if len(self.cache) > 2:
                self.cache.popitem(last=False)
        self.cache.move_to_end(p)
        a = self.cache[p][int(r['list_index'])].detach().numpy()[0]
        assert a.shape == (2, 128, 128) and a.dtype == np.float32 and np.isfinite(a).all()
        return a.copy()


def raw_pair(group, stage):
    d = DATA/'csv_extracted/1.DataFromDIC_CSV'/group
    paths = list(d.glob(f'*/*_{stage}.csv'))
    assert len(paths) == 1, (group, stage, paths)
    p = paths[0]
    with p.open() as f:
        head = [next(f) for _ in range(4)]
    a = np.loadtxt(p, skiprows=4)
    assert a.shape[1] == 7 and np.isfinite(a).all()
    assert len(np.unique(a[:, 0])) == len(a)
    return p, head, a


def main(out):
    started = datetime.now(timezone.utc).isoformat()
    tic = time.monotonic()
    out.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    manifest = read_json(SOURCE/'manifest.json')
    cases = manifest['cases']
    groups = sorted({c['group'] for c in cases})
    assert len(cases) == 1144 and len(groups) == 19
    source_paths = list(SOURCE.glob('*.npz'))+[SOURCE/n for n in ['manifest.json', 'selectors.json', 'per_case_scores.csv']]
    # Record all existing fields' cheap immutable identities, not just subsequently opened chunks.
    field_paths = list((DATA/'pt_extracted').glob('**/InputData.pt'))
    metadata_paths = [DATA/n for n in ['pt_frame_inventory.csv', 'full_csv_header_audit.json',
                                      'probe_v1_concentration/candidate_trajectories.csv']]
    original_identity = identity(source_paths+field_paths+metadata_paths)
    with (DATA/'pt_frame_inventory.csv').open() as f:
        inventory = list(csv.DictReader(f))
    loader = Fields(inventory)
    cand = pd.read_csv(DATA/'probe_v1_concentration/candidate_trajectories.csv').set_index(['group', 'stage'])
    header = read_json(DATA/'full_csv_header_audit.json')
    offsets = {(r['group'], r['file_stage']): r['file_stage']-r['header_numeric_suffix']
               for r in header['header_stage_conflicts']}
    selectors = {(r['fold'], r['horizon_stages']): r['chosen'] for r in read_json(SOURCE/'selectors.json')}
    saved = pd.read_csv(SOURCE/'per_case_scores.csv').set_index(['case_index', 'horizon_stages', 'arm'])
    stage_thirds = {}
    sample_ids = []
    for g in groups:
        ii = sorted([i for i, c in enumerate(cases) if c['group'] == g], key=lambda i: cases[i]['origin_stage'])
        t = thirds(ii)
        stage_thirds.update(t)
        for third in range(3):
            jj = [i for i in ii if t[i] == third]
            sample_ids.append(jj[len(jj)//2])
    records, spatial, rawrows, corr = [], [], [], []
    maps, examples = {}, {}
    max_discrepancy = 0.
    transition_windows = 0
    crossing_chunks = 0
    for fold, group in enumerate(groups):
        ids = [i for i, c in enumerate(cases) if c['group'] == group]
        preds, norms = {}, {}
        for h in (10, 40):
            chosen = selectors[(fold, h)]
            assert chosen in ['C_RAW', 'C_REL', 'P', 'S']
            for arm in set(['H_INNOV', 'C_RAW', chosen])-set(['P', 'S']):
                with np.load(SOURCE/f'fold{fold}_{h}_{arm}.npz', allow_pickle=False) as z:
                    assert list(z['case_indices']) == ids
                    preds[(h, arm)] = z['coarse_delta'].copy()
                    norms[h] = z['normalizer'].copy()
            maps[(fold, h)] = np.zeros((2, 2, 128, 128), np.float64)
        for k, i in enumerate(ids):
            c = cases[i]
            n, center = c['origin_stage'], c['center_row']
            current, past = loader.get(group, n), loader.get(group, n-10)
            low, high = map(int, re.search(r'_(\d+)-(\d+)/InputData.pt$', c['pt_member']).groups())
            assert low <= n-20 and n+40 <= high
            needed = [n-20, n-10, n, n+10, n+40]
            crossing_chunks += len({loader.rows[(group, s)]['pt_member'] for s in needed}) != 1
            off = {offsets.get((group, s), 0) for s in range(n-20, n+41)}
            transition_windows += len(off) != 1
            gap = min(n-20-low, high-(n+40))
            margin_bin = '0-5' if gap <= 5 else ('6-15' if gap <= 15 else '>15')
            d = current.astype(float)-past.astype(float)
            shift = float(np.mean(np.abs(d.mean((1, 2)))))
            shape = float(np.mean(np.abs(d-d.mean((1, 2), keepdims=True))))
            second = .5*(np.abs(np.diff(current.astype(float), n=2, axis=1)).mean()
                         + np.abs(np.diff(current.astype(float), n=2, axis=2)).mean())
            roughness = float(second/max(float(current.std(axis=(1, 2)).mean()), 1e-12))
            setting = float(cand.loc[(group, n), 'threshold_span_range_px'])
            meta = {'group': group, 'case_index': i, 'origin_stage': n, 'stage_third': stage_thirds[i],
                    'pt_chunk_start': low, 'pt_chunk_end': high, 'window_margin': gap, 'margin_bin': margin_bin,
                    'header_offset': offsets.get((group, n), 0), 'header_offset_flag': int(offsets.get((group, n), 0) != 0),
                    'header_transition_window': int(len(off) != 1), 'threshold_range_px': setting,
                    'past10_mean_shift_mm': shift, 'past10_shape_change_mm': shape,
                    'mean_shift_fraction_L1': shift/max(shift+shape, 1e-15), 'current_roughness_ratio': roughness}
            region = masks(center)
            for h in (10, 40):
                target = loader.get(group, n+h)
                chosen = selectors[(fold, h)]
                errors, predictions = {}, {}
                norm = norms[h][:, None, None]
                for arm in ARMS:
                    actual = chosen if arm == 'B_STAR' else arm
                    if actual == 'P':
                        prediction = current
                    elif actual == 'S':
                        prediction = current+(current-past)*h/10.
                    else:
                        delta = np.repeat(np.repeat(preds[(h, actual)][k].reshape(2, 16, 16), 8, 1), 8, 2)
                        prediction = current+delta
                    error = np.abs(prediction-target)/norm
                    score = float(balanced(error, center))
                    expected = float(saved.loc[(i, h, arm), 'balanced_nmae'])
                    diff = abs(score-expected)
                    max_discrepancy = max(max_discrepancy, diff)
                    assert diff < 1e-10, (i, h, arm, diff)
                    errors[arm], predictions[arm] = error, prediction
                rec = dict(meta, horizon=h, chosen_baseline=chosen)
                rec.update({arm: float(balanced(errors[arm], center)) for arm in ARMS})
                rec.update(gain_B_STAR=rec['B_STAR']-rec['H_INNOV'], gain_C_RAW=rec['C_RAW']-rec['H_INNOV'])
                records.append(rec)
                for name, mask in region.items():
                    ss = dict(group=group, case_index=i, horizon=h, stage_third=stage_thirds[i], region=name,
                              pixels=int(mask.sum()))
                    ss.update({a: float(e[:, mask].mean()) for a, e in errors.items()})
                    ss.update(gain_B_STAR=ss['B_STAR']-ss['H_INNOV'], gain_C_RAW=ss['C_RAW']-ss['H_INNOV'])
                    spatial.append(ss)
                for j, comp in enumerate(['B_STAR', 'C_RAW']):
                    gain = errors[comp]-errors['H_INNOV']
                    maps[(fold, h)][j] += gain/len(ids)
                if i in sample_ids:
                    # Fixed 57 cases only, selected by source identity rather than gain.
                    examples[(i, h)] = (current.copy(), target.copy(),
                                        predictions['H_INNOV'].copy(), predictions['B_STAR'].copy(),
                                        (errors['B_STAR']-errors['H_INNOV']).copy())
            if i in sample_ids:
                p, head, raw = raw_pair(group, n)
                pp, ph, old = raw_pair(group, n-10)
                before = identity([p, pp])
                # Coordinates are compared only for shared published node IDs; material tracking is unverified.
                shared, ix, iy = np.intersect1d(raw[:, 0], old[:, 0], return_indices=True)
                rr = dict(meta, csv_path=str(p), past_csv_path=str(pp), nodes=len(raw), past_nodes=len(old),
                          id_jaccard=float(len(shared)/(len(raw)+len(old)-len(shared))),
                          shared_id_coordinate_median_mm=float(np.median(np.linalg.norm(raw[ix, 1:4]-old[iy, 1:4], axis=1))),
                          shared_id_coordinate_p95_mm=float(np.percentile(np.linalg.norm(raw[ix, 1:4]-old[iy, 1:4], axis=1), 95)),
                          raw_ux_std=float(raw[:, 4].std()), raw_uy_std=float(raw[:, 5].std()),
                          pt_ch0_std=float(current[0].std()), pt_ch1_std=float(current[1].std()),
                          csv_stage_header=head[1].strip())
                assert identity([p, pp]) == before
                rawrows.append(rr)
            if time.monotonic()-tic > 600:
                raise TimeoutError('analysis budget; no change to scientific scope')
        print(f'completed {fold+1}/19 {group}', flush=True)
    df = pd.DataFrame(records)
    sp = pd.DataFrame(spatial)
    assert len(df) == 2288 and len(rawrows) == 57 and crossing_chunks == 0
    # Within-group proxy bins use source-only quantities, tied values retained together.
    riskcols = ['threshold_range_px', 'past10_mean_shift_mm', 'current_roughness_ratio']
    origin = df.drop_duplicates('case_index').copy()
    for col in riskcols:
        origin[col+'_third'] = origin.groupby('group')[col].transform(
            lambda x: np.minimum(2, np.floor(x.rank(method='average', pct=True).to_numpy()*3))).astype(int)
    for col in riskcols:
        mapping = origin.set_index('case_index')[col+'_third']
        df[col+'_third'] = df.case_index.map(mapping)
    df.to_csv(out/'case_diagnostics.csv', index=False)
    sp.to_csv(out/'spatial_case_diagnostics.csv', index=False)
    rawdf = pd.DataFrame(rawrows)
    rawdf.to_csv(out/'raw_measurement_samples.csv', index=False)
    tables = {}
    for name, keys in {'stage': ['stage_third'], 'stage_horizon': ['stage_third', 'horizon'],
                       'region': ['region'], 'stage_region': ['stage_third', 'region'],
                       'chunk_margin': ['margin_bin'], 'header_offset': ['header_offset_flag'],
                       'group': ['group']}.items():
        tables[name] = weighted_summary(sp if 'region' in keys else df, keys)
    for col in riskcols:
        tables[col] = weighted_summary(df, col+'_third')
        for group, d in df.groupby('group'):
            # Origins averaged over H before rank association, no independent-window interpretation.
            dd = d.groupby('case_index')[[col, 'gain_B_STAR', 'gain_C_RAW']].mean()
            if dd[col].nunique() > 1:
                for comp in ['B_STAR', 'C_RAW']:
                    rho = float(spearmanr(dd[col], dd['gain_'+comp]).statistic)
                    corr.append(dict(group=group, proxy=col, comparator=comp, spearman_rho=rho))
    pd.DataFrame(corr).to_csv(out/'descriptive_within_group_correlations.csv', index=False)
    for name, t in tables.items():
        t.to_csv(out/(name+'_summary.csv'), index=False)
    meanmaps = np.mean(list(maps.values()), axis=0)
    np.savez_compressed(out/'normalized_gain_maps.npz', equal_group_horizon_mean=meanmaps,
                        by_group_horizon=np.asarray(list(maps.values())),
                        keys=np.asarray(list(maps.keys())), comparators=np.array(['B_STAR', 'C_RAW']))
    # Accounting uses disjoint partitions and every original case, independent of headline gain.
    pivot = sp.pivot(index=['case_index', 'horizon'], columns='region', values=['gain_B_STAR', 'gain_C_RAW', 'pixels'])
    partition_max = 0.
    for comp in ['B_STAR', 'C_RAW']:
        g = 'gain_'+comp
        for a, b in [('band', 'outside_band'), ('edge8', 'interior')]:
            discrepancy = (pivot[g][a]*pivot['pixels'][a]+pivot[g][b]*pivot['pixels'][b])/16384-pivot[g]['full']
            partition_max = max(partition_max, float(np.abs(discrepancy).max()))
    assert partition_max < 1e-12
    assert identity(source_paths+field_paths+metadata_paths) == original_identity
    write_json(out/'source_identity.json', original_identity)
    summary = {'analysis_type': 'descriptive_posthoc_no_refit', 'source_run': 'IU-BRIDGE-PS-20261019-R003',
               'origins': 1144, 'case_horizons': 2288, 'groups': 19, 'raw_sample_origins': 57,
               'raw_csv_files': 114, 'cross_chunk_windows': int(crossing_chunks),
               'header_offset_transition_windows': int(transition_windows),
               'score_reproduction_max_abs': max_discrepancy, 'partition_max_abs': partition_max,
               'overall': {a: float(df.groupby(['group', 'horizon'])[a].mean().mean()) for a in ARMS},
               'group_gain_B_STAR': df.groupby('group').gain_B_STAR.mean().to_dict(),
               'tables': {k: v.to_dict('records') for k, v in tables.items()},
               'source_control_defect_retained': True,
               'original_E005_negative_preserved': True,
               'physical_tip_reference': 'unavailable', 'exact_CSV_PT_grid_mapping': 'unqualified',
               'future_frames_as_diagnostic_targets_only': True,
               'models_fit': 0, 'coefficient_forward_evaluations': 0,
               'started_utc': started, 'finished_utc': datetime.now(timezone.utc).isoformat(),
               'wall_seconds': time.monotonic()-tic, 'hostname': socket.gethostname()}
    write_json(out/'summary.json', summary)
    # Store preselected field panels without rerunning any predictor.
    for group in [groups[0], 'C_30Deg_20%_#1', 'E_0Deg_17.5%_#1']:
        i = next(i for i in sample_ids if cases[i]['group'] == group and stage_thirds[i] == 1)
        cur, target, hist, base, gain = examples[(i, 40)]
        np.savez_compressed(out/f'example_{groups.index(group)}.npz', current=cur, target=target,
                            history=hist, baseline=base, normalized_gain=gain,
                            group=group, origin=cases[i]['origin_stage'], case_index=i)
    print(json.dumps({k: v for k, v in summary.items() if k not in ['tables', 'group_gain_B_STAR']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    main(args.out)
