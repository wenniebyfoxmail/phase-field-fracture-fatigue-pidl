"""Shared-support, image/site hierarchical envelope correspondence, not pixel truth."""
import numpy as np


def dice(p, y):
    b, t = np.asarray(p) >= .5, np.asarray(y, dtype=bool)
    den = int(b.sum()) + int(t.sum())
    return 1. if den == 0 else 2*int((b & t).sum())/den


def one_combination(pred, target, common, rows, sites, margin=1e-6):
    n = len(rows)
    if pred.shape != (n, 32, 32) or target.shape != pred.shape or common.shape != pred.shape:
        raise ValueError('comparison shape')
    if not np.isfinite(pred).all() or (pred < 0).any() or (pred > 1).any():
        raise ValueError('probability')
    if not np.isin(target, [0, 1]).all() or not np.isin(common, [0, 1]).all():
        raise ValueError('reference')
    by_image = {}
    for j, row in enumerate(rows):
        by_image.setdefault(row['image_id'], []).append(j)
    image_site = {im: rows[js[0]]['location'] for im, js in by_image.items()}
    if any(any(rows[j]['location'] != image_site[im] for j in js) for im, js in by_image.items()):
        raise ValueError('image/site identity')
    means = {im: target[js].mean(0, dtype=np.float64) for im, js in by_image.items()}
    records, image_records, site_records = [], [], []
    for site in sites:
        ims = sorted(im for im in by_image if image_site[im] == site)
        if len(ims) < 2:
            raise ValueError('LOO requires at least two images per site')
        total = sum(means[im] for im in ims)
        prevalence = float((total/len(ims)).mean())
        for z, im in enumerate(ims):
            js = by_image[im]; next_js = by_image[ims[(z+1) % len(ims)]]
            prior = (total-means[im])/(len(ims)-1)
            for ordinal, j in enumerate(js):
                y = target[j]; p = pred[j]
                baselines = dict(zero=0., one=1., oracle_constant=prevalence,
                                 loo_image_position=prior,
                                 fixed_identity_mismatch=pred[next_js[ordinal % len(next_js)]],
                                 fixed_half_shift=np.roll(p, (16,16), (0,1)))
                bs = {k: dice(np.broadcast_to(a, y.shape), y) for k, a in baselines.items()}
                correct = dice(p, y); chosen = bool(common[j].any())
                records.append(dict(index=rows[j]['index'],image_id=im,location=site,common_FG=chosen,
                                    reference_FG=bool(y.any()),Dice=correct,baseline_Dice=bs,
                                    gain=correct-max(bs.values()),Brier=float(np.mean((p.astype(float)-y)**2)),
                                    predicted_cells=int((p>=.5).sum()),reference_cells=int(y.sum()),
                                    inside_envelope_mass=float(p[y.astype(bool)].sum()),
                                    outside_envelope_mass=float(p[~y.astype(bool)].sum())))
        own = [r for r in records if r['location'] == site]
        for im in ims:
            rr = [r for r in own if r['image_id'] == im]
            fg = [r for r in rr if r['common_FG']]
            image_records.append(dict(image_id=im,location=site,contexts=len(rr),common_contexts=len(fg),
                                      Dice=None if not fg else float(np.mean([r['Dice'] for r in fg])),
                                      gain=None if not fg else float(np.mean([r['gain'] for r in fg]))))
        ir = [r for r in image_records if r['location']==site and r['common_contexts']]
        gain = None if not ir else float(np.mean([r['gain'] for r in ir]))
        site_records.append(dict(location=site,images=len(ims),common_images=len(ir),
                                 Dice=None if not ir else float(np.mean([r['Dice'] for r in ir])),
                                 gain=gain,qualified=gain is not None and gain>margin,
                                 status='inconclusive' if gain is None else 'pass' if gain>margin else 'negative'))
    return dict(contexts=sorted(records,key=lambda r:r['index']),images=image_records,sites=site_records)


def compare(maps, refs, rows, cfg):
    combinations = {}
    for arm in ['cached','native']:
        for pool in ['mean','max']:
            for ref in ['center','any']:
                name = f'{arm}_{pool}_{ref}'
                combinations[name] = one_combination(maps[f'{arm}_{pool}'], refs[ref], refs['any'], rows, cfg['sites'], cfg['margin'])
    primary = combinations['native_max_any']
    admission = {r['location']:r['qualified'] for r in primary['sites']}
    pairs = [dict(fold=k,locations=locs,qualified=all(admission[v] for v in locs)) for k,locs in enumerate(cfg['qual_locations'])]
    return dict(protocol=cfg['protocol'],primary_candidate='native_max_any',combinations=combinations,
                pairs=pairs,primary_pass=any(v['qualified'] for v in pairs),
                selector=False,OOF=None,retention=None,net_GT=None,
                reference='partial envelope presence correspondence, not exact pixel truth',
                grouping='shared R_any-FG contexts -> image -> site; three reused development qualification sites')
