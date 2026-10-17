"""Exploratory current-field jump-support span, never a physical crack truth.

No model fitting or temporal smoothing. ROI uses the first available PT frame.
Pixel spans are authoritative; nominal-mm conversion is explicitly provisional.
"""
from pathlib import Path
import argparse, csv, json, re, time
import numpy as np
import torch

MULTIPLIERS = (0.8, 1.0, 1.25)


def initial_center(a, edge):
    g = np.abs(np.diff(a[1], axis=0))
    strip = g[32:96, :8] if edge else g[32:96, 56:72]
    return int(np.argmax(np.nanmean(strip, axis=1))) + 32


def measure(a, center, edge, multiplier=1.0, mode='absolute'):
    if not np.isfinite(a).all():
        return dict(status="nonfinite_field", span_px=None, left_px=None, right_px=None)
    g = np.abs(np.diff(a[1], axis=0))
    lo, hi = max(8, center-16), min(119, center+17)
    bg = np.concatenate((g[8:max(9, center-24)].ravel(),
                         g[min(118, center+25):119].ravel()))
    threshold = max(float(np.quantile(bg, .995)), 1e-8) * multiplier
    profile = g[lo:hi].max(axis=0)
    if mode == 'concentration':
        # One row accounts for at least 1/4 of local vertical variation.
        # A bounded exploratory repair for diffuse elastic-gradient support.
        profile = profile / np.maximum(g[lo:hi].sum(axis=0), 1e-12)
        threshold = .25 * multiplier
    mask = profile > threshold
    # Fill only isolated one-column holes, spatially; no time interpolation.
    mask[1:-1] |= mask[:-2] & mask[2:]
    seed = 0 if edge else 64
    if not mask[seed]:
        return dict(status="no_seed_support", span_px=None, left_px=None,
                    right_px=None, threshold=threshold,
                    peak_to_threshold=float(profile.max()/threshold))
    left = right = seed
    while left > 0 and mask[left-1]: left -= 1
    while right < 127 and mask[right+1]: right += 1
    l, r = float(left), float(right)
    if left > 0:
        den = profile[left]-profile[left-1]
        if den > 0: l = left-1 + np.clip((threshold-profile[left-1])/den, 0, 1)
    if right < 127:
        den = profile[right]-profile[right+1]
        if den > 0: r = right + np.clip((profile[right]-threshold)/den, 0, 1)
    return dict(status="candidate", span_px=float(r-l), left_px=float(l),
                right_px=float(r), threshold=threshold,
                peak_to_threshold=float(profile.max()/threshold))


def main(base, mode):
    start = time.monotonic()
    files = sorted((base/'pt_extracted').rglob('*.pt'),
        key=lambda p:(p.parent.parent.name,int(re.search(r'_(\d+)-',p.parent.name)[1])))
    out = base / ('probe_v0_absolute' if mode=='absolute' else 'probe_v1_concentration')
    out.mkdir(exist_ok=True)
    centers, rows = {}, []
    wanted = json.loads((base/'published_labels.json').read_text())
    label_lookup = {}
    for sheet, values in wanted.items():
        group = 'E_0Deg_17.5%_#1' if sheet.startswith('E_') else 'C_15Deg_20%_#1'
        for stage, cycle, label, _prediction in values:
            label_lookup.setdefault((group, int(stage)), []).append((sheet, cycle, label))
    selected = np.load(base/'pt_selected_frames.npz')
    groups = sorted({p.parent.parent.name for p in files})
    for group in groups:
        centers[group] = initial_center(selected[group+'__early'], group.startswith('E'))
    label_rows = []
    for p in files:
        group = p.parent.parent.name
        first, last = map(int, re.search(r'_(\d+)-(\d+)$', p.parent.name).groups())
        frames = torch.load(p, map_location='cpu', weights_only=True)
        assert len(frames) == last-first+1
        for index, tensor in enumerate(frames):
            stage = first+index
            a = tensor.numpy()[0]
            m = [measure(a, centers[group], group.startswith('E'), v, mode) for v in MULTIPLIERS]
            r = dict(group=group, stage=stage, cycle_from_readme=30*(stage-1),
                     center_row_from_first_frame=centers[group], **m[1])
            r.update(span_px_threshold08=m[0]['span_px'], span_px_threshold125=m[2]['span_px'])
            vals = [x['span_px'] for x in m if x['span_px'] is not None]
            r['threshold_span_range_px'] = max(vals)-min(vals) if len(vals)==3 else None
            # Assumption for a comparison only; not a calibrated PT grid mapping.
            r['nominal_mm_assuming_100_over_127'] = r['span_px']*100/127 if r['span_px'] is not None else None
            rows.append(r)
            for sheet, cycle, label in label_lookup.get((group, stage), []):
                label_rows.append(dict(sheet=sheet, group=group, stage=stage,
                    published_cycle=cycle, published_label=label, **m[1],
                    nominal_mm_assuming_100_over_127=r['nominal_mm_assuming_100_over_127']))
    for filename, data in [('candidate_trajectories.csv', rows), ('published_label_probe.csv', label_rows)]:
        keys = list(dict.fromkeys(k for r in data for k in r))
        with (out/filename).open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(data)
    summary = []
    for group in groups:
        rs = [r for r in rows if r['group']==group]
        good = [r for r in rs if r['span_px'] is not None]
        sensitive = [r['threshold_span_range_px'] for r in good if r['threshold_span_range_px'] is not None]
        # Diagnostic count only: adjacent fluctuations are not measurement error.
        decreases = sum(b['stage']==a['stage']+1 and b['span_px']<a['span_px']-.5
                        for a,b in zip(good,good[1:]))
        summary.append(dict(group=group, frame_count=len(rs), candidate_frames=len(good),
            first_stage=rs[0]['stage'], last_stage=rs[-1]['stage'], center_row=centers[group],
            first_span_px=good[0]['span_px'] if good else None,
            last_span_px=good[-1]['span_px'] if good else None,
            threshold_range_median_px=float(np.median(sensitive)) if sensitive else None,
            threshold_range_p95_px=float(np.quantile(sensitive,.95)) if sensitive else None,
            adjacent_decreases_over_half_pixel=decreases,
            reliability="unqualified_current_field_proxy"))
    (out/'candidate_summary.json').write_text(json.dumps(dict(groups=summary,
        frames=len(rows), label_comparisons=len(label_rows), elapsed_seconds=time.monotonic()-start,
        algorithm=mode+"; first-frame ROI; 0.8/1/1.25 threshold sensitivity",
        training=False, smoothing=False, physical_grid_qualified=False), indent=2))
    print('Probed',len(rows),'frames,',len(groups),'groups;',len(label_rows),'published label rows',flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('base',type=Path)
    parser.add_argument('--mode',choices=['absolute','concentration'],default='absolute')
    args = parser.parse_args();main(args.base,args.mode)
