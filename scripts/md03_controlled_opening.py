"""Prepared D3 candidate. No real-image execution is authorised by this module.

prepare hashes existing files only; unit tests use artificial arrays only.
run requires a separately reviewed execution decision and refuses macOS.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'docs/research/S03/S03-E049-MD03/controlled_opening_protocol.md'
OFFSETS = np.array([-72., -48., -24., 24., 48., 72.])
XS = (2598, 2750, 2782, 2902)
YS = tuple(range(1740, 2061, 16))
ARMS = {'central': 0, 'left_internal': -120, 'right_internal': 120}
PERTURBATIONS = ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1))
QC = dict(texture_std=2., ncc=.90, peak_separation=.02, roundtrip=.5)
HALF, SEARCH = 15, 4
WALL_SECONDS, OUTPUT_BYTES = 600, 128 * 1024**2
PACKAGE = 'D3_controlled_opening_20261020'
SOURCE_HASHES = {
    'IMG_0089.tif': 'e6544537b93f436637e08e1ece0c21157a07d9cf45538e79c154af5fb3ed796c',
    'IMG_0132.tif': '1139e92fd629c6cd1f3a50901c501c6be975001e140109c7ce835e3c9dece9be',
    'IMG_0175.tif': '02d57ea2610a7da20532d675898c1738681384ecd41669836c703684ceeb47a6',
}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    # New task-owned files only; never overwrites old evidence.
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def finite(value):
    return None if value is None or not np.isfinite(value) else float(value)


def crop(a, x, y, half):
    """Bilinear patch with a full in-bounds interpolation footprint."""
    h, w = a.shape
    if x-half < 0 or y-half < 0 or x+half >= w-1 or y+half >= h-1:
        return None
    return cv2.getRectSubPix(a.astype(np.float32, copy=False), (2*half+1, 2*half+1), (float(x), float(y)))


def peak(scores):
    """Deterministic NCC maximum; second peak outside its 3x3 neighbourhood."""
    if not np.isfinite(scores).all():
        return None
    hits = np.argwhere(scores == scores.max())
    py, px = min(hits.tolist(), key=lambda p: ((p[1]-SEARCH)**2+(p[0]-SEARCH)**2, p[0], p[1]))
    displacement = [float(px-SEARCH), float(py-SEARCH)]
    edge = px in (0, 2*SEARCH) or py in (0, 2*SEARCH)
    for axis, index in enumerate((px, py)):
        if 0 < index < 2*SEARCH:
            v = scores[py, px-1:px+2] if axis == 0 else scores[py-1:py+2, px]
            den = float(v[0]-2*v[1]+v[2])
            if den < 0:
                displacement[axis] += float(np.clip(.5*(v[0]-v[2])/den, -.5, .5))
    yy, xx = np.indices(scores.shape)
    others = scores[(abs(xx-px) > 1) | (abs(yy-py) > 1)]
    return dict(d=displacement, ncc=float(scores[py, px]), edge=edge,
                separation=float(scores[py, px]-others.max()))


def forward(a, b, x, y, valid_a, valid_b):
    p, s = crop(a, x, y, HALF), crop(b, x, y, HALF+SEARCH)
    va, vb = crop(valid_a, x, y, HALF), crop(valid_b, x, y, HALF+SEARCH)
    if p is None or s is None or va is None or vb is None or va.min() < 1-1e-6 or vb.min() < 1-1e-6:
        return dict(usable=False, reasons=['support'], d=None)
    if not np.isfinite(p).all() or not np.isfinite(s).all():
        return dict(usable=False, reasons=['nonfinite'], d=None)
    std = float(p.std())
    if std < QC['texture_std']:
        return dict(usable=False, reasons=['low_texture'], d=None, std=std)
    # OpenCV can give a misleading defined result for constant search patches.
    if float(s.std()) < QC['texture_std']:
        return dict(usable=False, reasons=['low_target_texture'], d=None, std=std)
    pmax = peak(cv2.matchTemplate(s, p, cv2.TM_CCOEFF_NORMED))
    if pmax is None:
        return dict(usable=False, reasons=['nonfinite_scores'], d=None)
    reasons = []
    if pmax['edge']:
        reasons.append('search_edge')
    if pmax['ncc'] < QC['ncc']:
        reasons.append('low_ncc')
    if pmax['separation'] < QC['peak_separation']:
        reasons.append('ambiguous_peak')
    return dict(**pmax, std=std, usable=not reasons, reasons=reasons)


def bidirectional(a, b, x, y, valid_a, valid_b):
    f = forward(a, b, x, y, valid_a, valid_b)
    if f['d'] is None:
        return dict(forward=f, reverse=None, roundtrip=None, usable=False, reasons=f['reasons'])
    dx, dy = f['d']
    reverse = forward(b, a, x+dx, y+dy, valid_b, valid_a)
    fb = None if reverse['d'] is None else float(np.linalg.norm(np.array(f['d'])+reverse['d']))
    reasons = list(f['reasons']) + ['reverse_'+r for r in reverse['reasons']]
    if fb is None or fb > QC['roundtrip']:
        reasons.append('roundtrip')
    return dict(forward=f, reverse=reverse, roundtrip=fb, usable=not reasons, reasons=sorted(set(reasons)))


def jump_from_displacements(displacements):
    """Both side fits use 3 points, identical distances and OLS resources."""
    d = np.asarray(displacements, float)
    if d.shape != (6, 2) or not np.isfinite(d).all():
        raise ValueError('Six finite 2D displacements required')
    intercepts, errors = [], []
    for i in (slice(0, 3), slice(3, 6)):
        design = np.column_stack((np.ones(3), OFFSETS[i]))
        coef = np.linalg.lstsq(design, d[i], rcond=None)[0]
        intercepts.append(coef[0])
        errors.append(float(np.sqrt(np.mean((design@coef-d[i])**2))))
    return (intercepts[1]-intercepts[0]).tolist(), max(errors)


def gauge(a, b, oldmask, valid_a, valid_b, x, y):
    matches = [bidirectional(a, b, x+o, y, valid_a, valid_b) for o in OFFSETS]
    reasons = sorted({r for m in matches for r in m['reasons']})
    ds = [m['forward']['d'] for m in matches]
    raw, fit = (None, None) if any(d is None for d in ds) else jump_from_displacements(ds)
    if not reasons and raw is None:
        reasons = ['missing_displacement']
    c = np.s_[int(y)-15:int(y)+16, int(x)-2:int(x)+3]
    def delta_slice(sl):
        return a[sl].astype(float)-b[sl].astype(float)
    center_delta = delta_slice(c)
    flank = .5*(delta_slice(np.s_[int(y)-15:int(y)+16, int(x)-13:int(x)-5]).mean() +
                  delta_slice(np.s_[int(y)-15:int(y)+16, int(x)+6:int(x)+14]).mean())
    # Appearance and old occupancy are diagnostics, never crack truth / selectors.
    return dict(numerically_usable=not reasons, reasons=reasons,
                raw_jump_xy=raw, jump_normal_px=raw[0] if raw is not None and not reasons else None,
                jump_tangent_px=raw[1] if raw is not None and not reasons else None,
                fit_rms_px=fit, matches=matches,
                central_darkening_gray=finite(center_delta.mean()-flank),
                residual_abs_gray=finite(abs(center_delta).mean()),
                old_candidate_fraction=finite(oldmask[c].mean()),
                visibility='unknown_not_annotated', crossing='unverified', physical_width=None)


def warp(a, matrix):
    h, w = a.shape
    matrix = np.asarray(matrix, float)
    inv = cv2.invertAffineTransform(matrix)
    yy, xx = np.indices(a.shape)
    sx = inv[0, 0]*xx+inv[0, 1]*yy+inv[0, 2]
    sy = inv[1, 0]*xx+inv[1, 1]*yy+inv[1, 2]
    valid = (np.floor(sx) >= 0) & (np.floor(sx)+1 < w) & (np.floor(sy) >= 0) & (np.floor(sy)+1 < h)
    return cv2.warpAffine(a.astype(np.float32), matrix, (w, h), flags=cv2.INTER_LINEAR), valid


def distribution(values):
    v = [float(x) for x in values if x is not None and np.isfinite(x)]
    return dict(n=len(v), median=float(np.median(v)) if v else None,
                p10=float(np.percentile(v, 10)) if v else None,
                p90=float(np.percentile(v, 90)) if v else None)


def summarize(records):
    rows = []
    for arm in ARMS:
        pool = [r for r in records if r['arm'] == arm and r['perturbation'] == [0, 0]]
        rows.append(dict(arm=arm, nominal=len(pool), numerical_usable=sum(r['numerically_usable'] for r in pool),
                         unknown_visibility=len(pool), fail_groups=dict(Counter(v for r in pool for v in r['reasons'])),
                         normal_px=distribution(r['jump_normal_px'] for r in pool),
                         tangent_px=distribution(r['jump_tangent_px'] for r in pool)))
    paired = []
    for site in sorted({r['site'] for r in records}):
        base = {r['arm']: r for r in records if r['site'] == site and r['perturbation'] == [0, 0]}
        group = [r for r in records if r['site'] == site]
        all_usable = len(group) == 15 and all(r['numerically_usable'] for r in group)
        spread = {arm: distribution(r['jump_normal_px'] for r in group if r['arm'] == arm) for arm in ARMS}
        envelope = None
        if all_usable:
            central = [r['jump_normal_px'] for r in group if r['arm'] == 'central']
            controls = [abs(r['jump_normal_px']) for r in group if r['arm'] != 'central']
            envelope = float(min(central)-max(controls))
        paired.append(dict(site=site, all_arms_and_perturbations_usable=all_usable,
                           positive_central_minus_abs_internal_envelope_px=envelope,
                           spreads=spread, baseline={k: v['jump_normal_px'] for k, v in base.items()},
                           crack_interpretation='unknown_without_located_reference'))
    return dict(arms=rows, sites=paired, spatial_ranges_not_ci=True,
                internal_arms_not_confirmed_crack_free=True, independent_physical_units=1,
                no_crack_accuracy_or_forecast_score=True)


def prepare(base, output):
    """Identity-only preparation: no np.load, TIFF decode, matching or plotting."""
    base = base.resolve()
    spec = base/'D3_20261019/R001/input_specification.json'
    meta = json.loads(spec.read_text())
    paths = [base/'history_support.json', spec, base/'R000_selection/selection_lock.json']
    paths += [base/'R002_history'/str(i)/'arrays.npz' for i in (89, 132)]
    paths += [base/'R003_target/arrays.npz']
    for f in meta['source_records']:
        p = base/'source'/f['filename']
        if p.stat().st_size != f['bytes'] or sha(p) != f['sha256']:
            raise ValueError('Source identity mismatch: '+str(p))
        paths.append(p)
    if meta['roi'] != [2260, 1600, 3240, 2160] or [x[:2] for x in meta['pairs']] != [[89, 132], [132, 175]]:
        raise ValueError('Unexpected old pair/coordinate definition')
    if len(meta['matrices']) != 2 or any(np.asarray(m).shape != (2, 3) for m in meta['matrices']):
        raise ValueError('Unexpected saved transform')
    payload = dict(candidate=PACKAGE, archive=str(base), files={str(p.relative_to(base)): sha(p) for p in paths},
                   raw_source_sha256={f['filename']: f['sha256'] for f in meta['source_records']},
                   pairs=[[89, 132], [132, 175]], roi=meta['roi'], matrices=meta['matrices'],
                   normal=[1, 0], tangent=[0, 1], xs=XS, ys=YS, arms=ARMS,
                   offsets=OFFSETS.tolist(), patch_size=31, search_radius=SEARCH,
                   perturbations=PERTURBATIONS, quality=QC, wall_seconds=WALL_SECONDS,
                   output_bytes=OUTPUT_BYTES, code_sha256=sha(__file__), protocol_sha256=sha(PROTOCOL),
                   prepared_utc=stamp(), state='prepared_no_real_algorithm_executed')
    write_json(output, payload)


def validate_contract(contract):
    expected = dict(candidate=PACKAGE, normal=[1, 0], tangent=[0, 1], xs=list(XS), ys=list(YS), arms=ARMS,
                    offsets=OFFSETS.tolist(), perturbations=[list(p) for p in PERTURBATIONS],
                    patch_size=31, search_radius=SEARCH, quality=QC, wall_seconds=WALL_SECONDS,
                    output_bytes=OUTPUT_BYTES, pairs=[[89, 132], [132, 175]], roi=[2260, 1600, 3240, 2160])
    for key, value in expected.items():
        if contract.get(key) != value:
            raise ValueError('Contract differs from implementation: '+key)
    required = {'history_support.json', 'D3_20261019/R001/input_specification.json',
                'R000_selection/selection_lock.json', 'R002_history/89/arrays.npz',
                'R002_history/132/arrays.npz', 'R003_target/arrays.npz'} | {'source/'+n for n in SOURCE_HASHES}
    if set(contract['files']) != required or contract['raw_source_sha256'] != SOURCE_HASHES:
        raise ValueError('Exact input set changed')
    if any(contract['files']['source/'+n] != h for n, h in SOURCE_HASHES.items()):
        raise ValueError('Source identity contract changed')
    if len(contract['matrices']) != 2 or any(np.asarray(m).shape != (2, 3) or not np.isfinite(m).all() for m in contract['matrices']):
        raise ValueError('Invalid transform contract')
    if contract['code_sha256'] != sha(__file__) or contract['protocol_sha256'] != sha(PROTOCOL):
        raise ValueError('Code/protocol changed since preparation')


def admit(contract_path, decision_path, output, worker_mode=False):
    if platform.system() == 'Darwin':
        raise RuntimeError('Mac is preparation-only; no real-image candidate execution')
    contract = json.loads(contract_path.read_text())
    decision = json.loads(decision_path.read_text())
    validate_contract(contract)
    # A decision file records authority; creating one is not itself human approval.
    for k, expected in dict(contract_sha256=sha(contract_path), host=socket.gethostname(),
                            candidate=PACKAGE, output=str(output.resolve()), wall_seconds=WALL_SECONDS).items():
        if decision.get(k) != expected:
            raise ValueError('Execution decision mismatch: '+k)
    if not decision.get('approval_source') or not decision.get('run_id'):
        raise ValueError('Exact approval source and fresh run ID required')
    root = Path(contract['archive']).resolve()/PACKAGE/'runs'
    if output.resolve().parent != root or output.name != decision['run_id'] or output.exists() != worker_mode:
        raise ValueError('Use the exact fresh task-owned run directory')
    if worker_mode:
        start = json.loads((output/'start_receipt.json').read_text())
        if start.get('execution') != 'running' or start.get('contract_sha256') != sha(contract_path) or start.get('code_sha256') != sha(__file__):
            raise ValueError('Worker requires matching parent start receipt')
    base = Path(contract['archive']).resolve()
    for name, digest in contract['files'].items():
        p = base/name
        if p.resolve().parent == base.parent or not p.resolve().is_relative_to(base) or sha(p) != digest:
            raise ValueError('Input identity mismatch: '+name)
    old = json.loads((base/'D3_20261019/R001/input_specification.json').read_text())
    if contract['matrices'] != old['matrices']:
        raise ValueError('Saved transforms were changed in contract')
    return contract, decision


def worker(contract, output):
    cv2.setNumThreads(1)
    write_json(output/'worker_identity.json', dict(host=socket.gethostname(), pid=os.getpid(),
               runtime=sys.executable, started_utc=stamp(), opencv_threads=cv2.getNumThreads()))
    base = Path(contract['archive'])
    arrays, masks = {}, {}
    for i in (89, 132, 175):
        path = base/'R002_history'/str(i)/'arrays.npz' if i != 175 else base/'R003_target/arrays.npz'
        with np.load(path, allow_pickle=False) as z:
            arrays[i] = z['roi_rgb'][:, :, 0].astype(np.float32)
            masks[i] = z['mask'].astype(bool)
        if arrays[i].shape != (560, 980) or masks[i].shape != (560, 980):
            raise ValueError('Unexpected cached ROI shape')
    for pi, (a, b) in enumerate(contract['pairs']):
        records = []
        for perturb in PERTURBATIONS:
            matrix = np.array(contract['matrices'][pi], float)
            matrix[:, 2] += perturb
            reference, valid = warp(arrays[a], matrix)
            valid = valid.astype(np.float32)
            target_valid = np.ones_like(valid)
            for xn in XS:
                for yn in YS:
                    for arm, dx in ARMS.items():
                        if (output/'STOP').exists():
                            raise RuntimeError('Task STOP requested; no retry')
                        x, y = xn+dx-contract['roi'][0], yn-contract['roi'][1]
                        row = gauge(reference, arrays[b], masks[b], valid, target_valid, x, y)
                        records.append(dict(pair=[a, b], site=f'x{xn}_y{yn}',
                                            base_xy=[xn, yn], arm=arm, gauge_xy=[xn+dx, yn],
                                            perturbation=list(perturb), **row))
            if sum(p.stat().st_size for p in output.iterdir() if p.is_file()) > OUTPUT_BYTES:
                raise RuntimeError('Output cap reached; no retry')
        write_json(output/f'{a}_{b}_records.json', records)
        write_json(output/f'{a}_{b}_summary.json', summarize(records))
        render(output, a, b, arrays[a], arrays[b], records)
    for name, digest in contract['files'].items():
        if sha(base/name) != digest:
            raise ValueError('Protected input changed: '+name)


def render(output, a, b, reference, target, records):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(15, 8), layout='constrained')
    for ax, image, label in zip(axes[0, :2], (reference, target), (f'Raw cached ROI {a}', f'Raw cached ROI {b}')):
        ax.imshow(image, cmap='gray', vmin=0, vmax=255, extent=(2260, 3240, 2160, 1600))
        ax.set_title(label+' | same image grid, NOT same material position')
        ax.set_xlabel('native image x (px)'); ax.set_ylabel('native image y (px)')
    for ax, (arm, shift) in zip(axes[1], ARMS.items()):
        grid = np.full((len(YS), len(XS)), np.nan)
        for r in records:
            if r['arm'] == arm and r['perturbation'] == [0, 0] and r['jump_normal_px'] is not None:
                grid[YS.index(r['base_xy'][1]), XS.index(r['base_xy'][0])] = r['jump_normal_px']
        cmap = plt.get_cmap('RdBu_r').copy(); cmap.set_bad('#999999')
        im = ax.imshow(np.ma.masked_invalid(grid), cmap=cmap, vmin=-4, vmax=4, aspect='auto', interpolation='nearest')
        ax.set_xticks(range(4), [str(x+shift) for x in XS]); ax.set_yticks([0, 10, 20], [1740, 1900, 2060])
        ax.set_title(arm+' | gray=QC unknown; not a crack label')
        ax.set_xlabel('gauge centre x (px), categorical columns'); ax.set_ylabel('y (px)')
        fig.colorbar(im, ax=ax, label='normal displacement jump (image px)', extend='both')
    axes[0, 2].axis('off')
    s = summarize(records)
    axes[0, 2].text(0, 1, '\n'.join([f"{r['arm']}: numerical {r['numerical_usable']}/{r['nominal']}" for r in s['arms']])+
                            '\nAll visibility/crossing labels unknown.\nAll 5 registration variants saved.\nSpatial points are dependent; no CI.\n175 is exposed development.\nNo physical width / forecast score.', va='top')
    fig.suptitle(f'{a} → {b}: central vs matched-resource internal gauges; no endpoint truth assumed')
    fig.savefig(output/f'{a}_{b}_comparison.png', dpi=150)
    plt.close(fig)
    (output/f'{a}_{b}_comparison.md').write_text(
        '# Matched-resource opening diagnostic\n\nQuestion: is a normal jump specific to the central stencil rather than internal texture/registration?\n'
        'Inputs: exact cached ROI arrays and immutable masks named in contract.json; renderer scripts/md03_controlled_opening.py.\n'
        'Panels: top two untouched cached raw ROIs, top right numerical coverage. Bottom central/left-internal/right-internal jump maps on identical discrete sites. '
        'Shared ±4 image-pixel scale, gray QC-unknown; arrows on bars indicate values can exceed the colour limit. No auto-selected hotspot. '
        'Five-variant raw records and per-site envelopes are in paired JSON. No selected positive example or omitted negative site.\n'
        'Key readout: '+json.dumps(s['arms'])+'\n\nLimitations: one beam, dependent spatial probes, internal gauges not confirmed crack-free, '
        'horizontal component not actual local normal, high NCC not material identity, visibility unknown, no author endpoints or physical aperture truth. '
        'Original half-depth/masks/scores remain unchanged; this is no future prediction.\n')
    # Every site and transform range, not only a favourable central response.
    sites = [f'x{x}_y{y}' for x in XS for y in YS]
    fig, axes = plt.subplots(3, 1, figsize=(15, 10), layout='constrained', sharex=True)
    colors = {'central': '#0072B2', 'left_internal': '#D55E00', 'right_internal': '#009E73'}
    for arm in ARMS:
        for axis, key in zip(axes[:2], ('jump_normal_px', 'jump_tangent_px')):
            med, low, high = [], [], []
            for site in sites:
                group = [r for r in records if r['site'] == site and r['arm'] == arm]
                values = [r[key] for r in group if r[key] is not None]
                # Missing any variant creates a hole, not a favourable narrower range.
                available = len(values) == 5
                med.append(float(np.median(values)) if available else np.nan)
                low.append(min(values) if available else np.nan)
                high.append(max(values) if available else np.nan)
            for group in range(4):
                sl = slice(21*group, 21*(group+1)); ids = list(range(21*group, 21*(group+1)))
                axis.plot(ids, med[sl], '.-', ms=2, lw=.7, color=colors[arm], label=arm if group == 0 else None)
                axis.fill_between(ids, low[sl], high[sl], color=colors[arm], alpha=.16)
    envelopes = {r['site']: r['positive_central_minus_abs_internal_envelope_px'] for r in s['sites']}
    values = [envelopes.get(site) for site in sites]
    for group in range(4):
        ids = list(range(21*group, 21*(group+1)))
        axes[2].plot(ids, [np.nan if values[i] is None else values[i] for i in ids], '.-', color='#555555', lw=.8)
    for axis, label in zip(axes, ('normal J (image px)', 'tangential J (image px)', 'central minus internal envelope (px)')):
        axis.axhline(0, color='#999999', lw=.7); axis.set_ylabel(label); axis.grid(alpha=.15)
    axes[0].legend(ncol=3)
    axes[2].set_xticks([0, 21, 42, 63, 83], ['x2598/y1740', 'x2750/y1740', 'x2782/y1740', 'x2902/y1740', 'x2902/y2060'])
    axes[2].set_xlabel('all84 fixed sites in x-major/y-increasing order; dependent, not a time axis')
    fig.suptitle(f'{a} → {b}: all five declared registration variants; shading=min/max, NOT confidence interval\n'
                 'Holes=at least one required QC-unknown; every raw record retained')
    fig.savefig(output/f'{a}_{b}_perturbations.png', dpi=150); plt.close(fig)
    (output/f'{a}_{b}_perturbations.md').write_text(
        '# All-site perturbation comparison\n\nQuestion: is central jump distinguishable from internal response and declared registration sensitivity?\n'
        'Exact data: paired records.json and summary.json in this run, renderer scripts/md03_controlled_opening.py.\n'
        'Panels: all84sites normal J, tangential J, then the positive-central-minus-absolute-internal nuisance envelope. '
        'Blue central, orange left-internal, green right-internal. Lines show medians of five transform variants; shading their finite min/max range, NOT CI. '
        'A line/range is absent if any of that arm’s five variants is unknown; the envelope needs all15 estimates. '
        'x positions are categorical spatial sites, not time or independent trials. All sites shown, no selection by value.\n'
        'Key readout: '+json.dumps({'jointly_usable_sites': sum(r['all_arms_and_perturbations_usable'] for r in s['sites']), 'nominal_sites': 84})+'\n'
        'Limits: no verified crack-free/positive labels, true local normal, physical aperture, exhaustive uncertainty or independent future validation.\n')


def run(contract_path, decision_path, output):
    contract, decision = admit(contract_path, decision_path, output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output/'contract.json', contract)
    write_json(output/'decision.json', decision)
    receipt = dict(started_utc=stamp(), host=socket.gethostname(), command=sys.argv,
                   parent_pid=os.getpid(), runtime=sys.executable,
                   commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   dirty=subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).splitlines(),
                   code_sha256=sha(__file__), protocol_sha256=sha(PROTOCOL),
                   contract_sha256=sha(contract_path), execution='running', scientific_verdict='pending',
                   old_scores_replaced=False, reference_annotations=0, source_downloads=0, trained_models=0)
    write_json(output/'start_receipt.json', receipt)
    start = time.monotonic()
    command = [sys.executable, str(Path(__file__).resolve()), '_worker', '--contract', str(output/'contract.json'), '--output', str(output)]
    try:
        # Parent enforces a hard wall limit on this task's sole child, not other processes.
        with (output/'worker.log').open('x') as log:
            env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=WALL_SECONDS, check=True, env=env)
        if sum(p.stat().st_size for p in output.iterdir() if p.is_file()) > OUTPUT_BYTES:
            raise RuntimeError('Output cap exceeded; no retry')
        for name, digest in contract['files'].items():
            if sha(Path(contract['archive'])/name) != digest:
                raise ValueError('Protected input changed: '+name)
        receipt.update(execution='succeeded', scientific_verdict='pending_visual_interpretation',
                       contracted_files_verified=len(contract['files']))
    except Exception as exc:
        receipt.update(execution='stopped_no_retry', error=repr(exc), scientific_verdict='uninterpreted_partial')
        raise
    finally:
        receipt.update(ended_utc=stamp(), wall_seconds=time.monotonic()-start)
        write_json(output/'receipt.json', receipt)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase', choices=['prepare', 'run', '_worker'])
    p.add_argument('--base', type=Path)
    p.add_argument('--contract', type=Path)
    p.add_argument('--decision', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.phase == 'prepare':
        prepare(args.base, args.output)
    elif args.phase == 'run':
        run(args.contract, args.decision, args.output)
    else:
        if platform.system() == 'Darwin':
            raise RuntimeError('No real-image worker on Mac')
        # Recheck full host/output/input/authority contract; not a bypass of run.
        c, _ = admit(args.contract, args.output/'decision.json', args.output, worker_mode=True)
        worker(c, args.output)
