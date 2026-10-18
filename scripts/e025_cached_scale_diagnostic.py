"""D4 offline cache/reference analysis; no model loading or source RGB access."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import argparse
import collections
import csv
import json
import resource
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def pool32(a):
    assert a.shape[:2] == (128, 128)
    return a.reshape(32, 4, 32, 4, *a.shape[2:]).mean(axis=(1, 3))


def sample(a, ctx, size):
    x1, y1, x2, y2 = ctx
    xs = np.floor(x1 + (np.arange(size) + .5) * (x2-x1)/size).astype(int)
    ys = np.floor(y1 + (np.arange(size) + .5) * (y2-y1)/size).astype(int)
    return a[np.ix_(np.clip(ys, 0, a.shape[0]-1), np.clip(xs, 0, a.shape[1]-1))]


def expand(a):
    return a.repeat(4, axis=0).repeat(4, axis=1)


def measure(rgb, y, y32, ctx):
    gray = np.asarray(rgb, dtype=np.float32) @ np.array([.299, .587, .114], np.float32) / 255
    reduced = expand(pool32(gray))
    p = float(y.mean())
    varied = 0 < p < 1
    oracle = expand(pool32(y.astype(np.float32)))
    oracle_error = float(np.mean((oracle-y)**2))
    fg = y.astype(bool)
    contrast = lambda v: abs(float(v[fg].mean() - v[~fg].mean())) if varied else None
    x1, y1, x2, y2 = ctx
    return dict(fg128=int(y.sum()), fg32=int(y32.sum()),
                zero32_with_fg128=bool(y.any() and not y32.any()),
                reference_fraction128=p, reference_fraction32=float(y32.mean()),
                oracle32_Brier=oracle_error,
                oracle32_error_over_constant=None if not varied else oracle_error/(p*(1-p)),
                contrast128=contrast(gray), contrast32=contrast(reduced),
                rgb32_reconstruction_mse=float(np.mean((gray-reduced)**2)),
                source_pixels_per_cell32_x=(x2-x1)/32,
                source_pixels_per_cell32_y=(y2-y1)/32)


def write_csv(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    start = time.monotonic()
    E, D = args.evidence, args.out
    D.mkdir(exist_ok=False, parents=True)
    read = lambda n: json.loads((E/n).read_text(encoding='utf-8-sig'))
    source = read('input_snapshot/input_snapshot/candidate_identity.json')['rows']
    contexts = read('pixel_contexts.json')['rows']
    rgb = np.load(E/'rgb_contexts.npy', mmap_mode='r')
    controls = [read(f'control_fold_{k}.json') for k in range(3)]
    quals = [read(f'qualification_fold_{k}.json') for k in range(3)]
    refs = [read(f'FIT_reference_index_fold_{k}.json') for k in range(3)]
    masks = [np.load(E/f'FIT_masks_fold_{k}.npy', mmap_mode='r') for k in range(3)]
    lookups = [{i:j for j,i in enumerate(ref['indices'])} for ref in refs]
    scopes = collections.defaultdict(list)
    for k in range(3):
        for i in controls[k]['indices']:
            scopes[i].append(('control', k))
        for r in quals[k]['contexts']:
            scopes[r['index']].append(('qualification', k))
    by_image = collections.defaultdict(list)
    for i in sorted(scopes):
        by_image[source[i]['image_id']].append(i)
    annotations = collections.defaultdict(list)
    for r in read('input_snapshot/train_polygons.json')['rows']:
        if r['image_id'] in by_image:
            annotations[r['image_id']].append(r)
    # This choice uses only frozen identities and original classifier scores.
    cases = [('control', k, controls[k]['indices'][0]) for k in range(3)]
    qsites = sorted({r['location'] for q in quals for r in q['contexts']}, key=int)
    if qsites != ['24','1638','2027'] or len({source[i]['image_id'] for c in controls for i in c['indices']}) != 16:
        raise ValueError('D4 fixed scope changed')
    frozen_cases = read('cases.json')['cases']
    for loc in qsites:
        k = min(k for k,q in enumerate(quals) if loc in q['locations'])
        case = next(r for r in frozen_cases if r['location']==loc and r['fold']==k)
        i = next(r['index'] for r in quals[k]['contexts']
                 if r['image_id']==case['image_id'] and contexts[r['index']]==case['context'])
        cases.append(('qualification', k, i))
    (D/'case_rule.json').write_text(json.dumps(cases, indent=2))
    chosen = {i for _,_,i in cases}
    visuals = {}
    rows = []
    for im, indices in by_image.items():
        rec = source[indices[0]]
        with Image.new('L', (rec['width'], rec['height']), 0) as image:
            draw = ImageDraw.Draw(image)
            for r in annotations[im]:
                if r['category'] in ['Alligator Crack', 'Transverse Crack']:
                    draw.polygon([tuple(p) for p in r['polygon']], fill=1)
            native = np.asarray(image, dtype=np.uint8)
            for i in indices:
                y = sample(native, contexts[i], 128)
                y32 = sample(native, contexts[i], 32)
                for _,k in scopes[i]:
                    if not np.array_equal(y32, masks[k][lookups[k][i]]):
                        raise ValueError(f'reference reconstruction mismatch {k}/{i}')
                a = np.asarray(rgb[i]).transpose(1,2,0)
                rows.append(dict(index=i, image_id=im, location=rec['location'],
                                 **measure(a, y, y32, contexts[i])))
                if i in chosen:
                    visuals[i] = (a.copy(), y.copy(), y32.copy())
            if time.monotonic()-start > 600:
                raise TimeoutError('D4 600s cap')
            peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform=='darwin' else 1024)
            if peak_rss >= 2*1024**3:
                raise MemoryError('D4 2GiB cap')
    write_csv(D/'contexts.csv', rows)
    lookup = {r['index']:r for r in rows}
    numerical = [key for key in rows[0] if key not in ['index','image_id','location']]
    groups = []
    for scope in ['control', 'qualification']:
        for k in range(3):
            selected = [lookup[i] for i, roles in scopes.items() if (scope,k) in roles]
            for loc in sorted({r['location'] for r in selected}, key=int):
                rr = [r for r in selected if r['location']==loc]
                images = sorted({r['image_id'] for r in rr})
                values = {}
                for key in numerical:
                    per_image = []
                    for im in images:
                        vals = [r[key] for r in rr if r['image_id']==im and r[key] is not None]
                        if vals:
                            per_image.append(float(np.mean(vals)))
                    values[key] = None if not per_image else float(np.mean(per_image))
                groups.append(dict(scope=scope, fold=k, location=loc, contexts=len(rr),
                                   images=len(images), minimum_fg128=min(r['fg128'] for r in rr if r['fg128']>0),
                                   minimum_fg32=min(r['fg32'] for r in rr if r['fg32']>0),
                                   count_fg128_zero32=sum(r['zero32_with_fg128'] for r in rr), **values))
    write_csv(D/'sites.csv', groups)
    decision = []
    for k in range(3):
        rr = [lookup[i] for i in controls[k]['indices']]
        avg = lambda key: float(np.mean([r[key] for r in rr]))
        decision.append(dict(scope='control', fold_or_site=str(k), contexts=len(rr),
            minimum_positive_fg128=min(r['fg128'] for r in rr),
            minimum_positive_fg32=min(r['fg32'] for r in rr),
            lost_to_zero32=sum(r['zero32_with_fg128'] for r in rr),
            contrast128=avg('contrast128'), contrast32=avg('contrast32'),
            contrast_drop_fraction=1-avg('contrast32')/avg('contrast128'),
            oracle_error_over_constant=avg('oracle32_error_over_constant')))
    for loc in qsites:
        r = next(r for r in groups if r['scope']=='qualification' and r['location']==loc)
        decision.append(dict(scope='qualification', fold_or_site=loc, contexts=r['contexts'],
            minimum_positive_fg128=r['minimum_fg128'], minimum_positive_fg32=r['minimum_fg32'],
            lost_to_zero32=r['count_fg128_zero32'], contrast128=r['contrast128'], contrast32=r['contrast32'],
            contrast_drop_fraction=1-r['contrast32']/r['contrast128'],
            oracle_error_over_constant=r['oracle32_error_over_constant']))
    write_csv(D/'decision_table.csv', decision)
    canvas = Image.new('RGB', (1420, 1390), 'white')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 18)
    draw.text((20, 10), 'E025 D4: fixed cached examples; no training / inference / source RGB reads', fill='black', font=font)
    draw.text((20, 36), 'Reference = region envelope, not crack width. Repeated folds are not independent.', fill='black', font=font)
    titles = ['Saved RGB128', 'Area32, back to128', 'Reference128', 'Saved reference32', 'Saved P [0,1]']
    for col,title in enumerate(titles):
        draw.text((210+240*col,70), title, fill='black', font=font)
    for row, (scope,k,i) in enumerate(cases):
        a, y, y32 = visuals[i]
        if scope=='control':
            pred = np.load(E/f'control_maps_fold_{k}_seed_0.npy', mmap_mode='r')[controls[k]['indices'].index(i)]
        else:
            ids = [r['index'] for r in quals[k]['contexts']]
            pred = np.load(E/f'qualification_maps_fold_{k}.npy', mmap_mode='r')[ids.index(i)]
        panels = [a, expand(pool32(a.astype(np.float32))).astype(np.uint8), y, y32, pred]
        for col, panel in enumerate(panels):
            if col>=2:
                panel = (np.asarray(panel)[...,None]*np.array([255,125,0])).astype(np.uint8)
            with Image.fromarray(panel) as image:
                canvas.paste(image.resize((200,200), Image.Resampling.NEAREST), (210+240*col,110+210*row))
        r=lookup[i]
        draw.text((10,140+210*row), f'{scope} f{k}\nsite{r["location"]}\nindex{i}\nFG128/32\n{r["fg128"]}/{r["fg32"]}', fill='black', font=font)
    canvas.save(D/'F04_cached_scale.png')
    summary = dict(unique_contexts=len(rows), unique_images=len(by_image),
                   source_image_reads=0, model_fits=0, model_inferences=0,
                   reference32_mismatches=0, elapsed_seconds=time.monotonic()-start,
                   peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform=='darwin' else 1024),
                   Pillow_version=Image.__version__,
                   groups=groups, cases=cases)
    (D/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
