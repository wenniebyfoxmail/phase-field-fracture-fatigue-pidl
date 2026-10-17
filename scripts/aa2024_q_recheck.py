#!/usr/bin/env python3
"""E019-D03 preparation. CLI execution requires separate human approval.

No legacy producer import, stiffness assembly, solve, held-response parser or fit.
"""
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import warnings

warnings.simplefilter('error')


class StopLogging(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.WARNING:
            raise RuntimeError('unexpected logging warning: '+record.getMessage())


logging.getLogger().addHandler(StopLogging(level=logging.WARNING))

import numpy as np
from scipy import linalg

ARMS = ('old', 'proxy', 'intact')
THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
           'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS')
PREP_KEYS = ('ids', 'xy', 'weights', 'train_v', 'mesh', 'tri', 'boundary', 'bc')
FIELD_KEYS = ARMS + tuple(k+'_sampled' for k in ARMS)
PREP_NAMES = ('preparation.json', 'prepared.npz', 'geometry_audit.json', 'training_geometry.npz')
FIT_NAMES = ('fit.json', 'frozen_predictions.npz', 'solved_fields.npz')
ANCHORS = ('8655d49b30e341d488eeb8c15db9a7d347f236634a22adbbf39fcb7b4bbd3ccf',
           '3173f0f659d6e451f7fccc39a4ca0973ae3caad750c9d98ce754a1bcec325674')
BASE = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments')
PREP = BASE/'S03-E016/S03-E016-R001/prepare'
FIT = BASE/'S03-E016/S03-E016-R002/fit'


class Stop(ValueError):
    pass


def require(condition, label):
    if not condition:
        raise Stop(label)


def close(a, ref, label, kind='vector'):
    a, ref = np.asarray(a), np.asarray(ref)
    atol = {'matrix': 1e-12, 'vector': 1e-15, 'square': 1e-18}[kind]
    require(a.shape == ref.shape and np.isfinite(a).all() and np.isfinite(ref).all(), label+' finite/shape')
    ratio = np.abs(a-ref)/(atol+1e-12*np.abs(ref))
    require(bool(np.all(ratio <= 1)), label)
    return float(np.max(ratio, initial=0))


def mm(a, b):
    require(a.ndim == 2 and b.ndim in (1, 2) and a.shape[1] == b.shape[0], 'contraction shape')
    out = np.einsum('ik,k->i' if b.ndim == 1 else 'ik,kj->ij', a, b, optimize=False)
    require(np.isfinite(out).all(), 'nonfinite contraction')
    return out


def q(H, x):
    return x-mm(H, mm(H.T, x))


def square(x):
    return float(np.einsum('i,i->', x, x, optimize=False))


class Budget:
    def __init__(self, clock=time.monotonic):
        self.clock, self.start = clock, clock()

    def check(self):
        elapsed = self.clock()-self.start
        if elapsed >= 60:
            raise TimeoutError('soft60s incomplete; no retry')
        return elapsed


class Factors:
    """Controlled API counts, not a certificate of whole-process history."""
    def __init__(self, qr=None, svd=None):
        self.qr_fn = linalg.qr if qr is None else qr
        self.svd_fn = linalg.svd if svd is None else svd
        self.qr_calls = self.svd_calls = 0

    def qr(self, a):
        self.qr_calls += 1
        require(self.qr_calls <= 2, 'extra QR forbidden')
        u, t = self.qr_fn(a, mode='economic', pivoting=False, check_finite=True)
        diag = np.diag(t)
        require(np.isfinite(u).all() and np.isfinite(t).all() and np.all(diag != 0), 'QR diagonal/finite')
        signs = np.where(diag < 0, -1., 1.)
        return u*signs, t*signs[:, None]

    def svd(self, a):
        self.svd_calls += 1
        require(self.svd_calls == 1, 'extra SVD forbidden')
        return self.svd_fn(a, full_matrices=False, check_finite=True, lapack_driver='gesvd')


def mesh_definition():
    x, y = np.meshgrid(np.linspace(-18, 18, 41), np.linspace(-9, 9, 21))
    xy = np.c_[x.ravel(), y.ravel()]
    tri = []
    for j in range(20):
        for i in range(40):
            a = 41*j+i
            tri.extend(((a, a+1, a+42), (a, a+42, a+41)))
    bd = (np.abs(xy[:, 0]) == 18) | (np.abs(xy[:, 1]) == 9)
    return xy, np.asarray(tri, dtype=int), bd


def sampling(xy):
    require(xy.ndim == 2 and xy.shape[1] == 2 and np.isfinite(xy).all(), 'sampling input')
    require(np.all(np.abs(xy) < np.array([16.2, 7.2])), 'strict original ROI')
    gx, gy = (xy[:, 0]+18)/36*40, (xy[:, 1]+9)/18*20
    i, j = np.floor(gx).astype(int), np.floor(gy).astype(int)
    fx, fy = gx-i, gy-j
    a = j*41+i
    lower = fy <= fx
    nodes = np.c_[a, np.where(lower, a+1, a+42), np.where(lower, a+42, a+41)]
    coeff = np.c_[1-np.where(lower, fx, fy), np.where(lower, fx-fy, fx), np.where(lower, fy, fy-fx)]
    S = np.zeros((2*len(xy), 1722))
    for c in (0, 1):
        S[2*np.arange(len(xy))[:, None]+c, 2*nodes+c] = coeff
    return S, nodes, coeff


def validate_source(p, fields):
    n = len(p['ids'])
    require(n == 648 and p['ids'].shape == (n,) and np.issubdtype(p['ids'].dtype, np.integer), '648 integer IDs')
    require(np.all(p['ids'] > 0) and len(np.unique(p['ids'])) == n, 'unique positive IDs')
    for key, shape in (('xy', (n, 2)), ('weights', (n,)), ('train_v', (n, 2)), ('bc', (120, 2))):
        require(p[key].shape == shape and np.isfinite(p[key]).all(), 'source '+key)
    require(np.all(p['weights'] > 0), 'positive inherited weights')
    mesh, tri, bd = mesh_definition()
    for key, expected in (('mesh', mesh), ('tri', tri), ('boundary', bd)):
        require(np.array_equal(p[key], expected), 'original mesh '+key)
    require(p['boundary'].dtype == np.bool_, 'boundary bool')
    for k in ARMS:
        require(fields[k].shape == (861, 2) and np.isfinite(fields[k]).all(), 'node field '+k)
        require(fields[k+'_sampled'].shape == (n, 2), 'sample shape '+k)
        close(fields[k][bd], p['bc'], 'original BC '+k)


def construct(p, fields, factors, budget):
    validate_source(p, fields)
    S, nodes, coeff = sampling(p['xy'])
    mesh, _, bd = mesh_definition()
    close(coeff.sum(axis=1), np.ones(648), 'constant reproduction', 'matrix')
    close(np.sum(mesh[nodes]*coeff[:, :, None], axis=1), p['xy'], 'coordinate reproduction', 'matrix')
    fixed, free = np.flatnonzero(np.repeat(bd, 2)), np.flatnonzero(~np.repeat(bd, 2))
    require(not np.any(S[:, fixed]), 'S_B must be zero')
    u0 = np.zeros((861, 2)); u0[bd] = p['bc']
    s0 = mm(S, u0.ravel())
    close(s0, np.zeros(1296), 'SU0 zero')
    w = p['weights']; wn = w/w.sum()
    require(np.isfinite(wn).all() and np.all(wn > 0), 'normalised weights')
    scale = np.repeat(np.sqrt(wn), 2)
    center = np.sum(wn[:, None]*p['xy'], axis=0)
    c = p['xy']-center
    m2 = float(np.sum(wn*np.sum(c*c, axis=1)))
    require(np.isfinite(m2) and m2 > 0, 'rigid design nondegenerate second moment')
    R = np.zeros((1296, 3)); R[0::2, 0] = 1; R[1::2, 1] = 1
    R[0::2, 2], R[1::2, 2] = -c[:, 1], c[:, 0]
    DR = scale[:, None]*R
    budget.check(); H, CH = factors.qr(DR); budget.check()
    close(mm(H.T, H), np.eye(3), 'H Gram', 'matrix')
    close(mm(H, CH), DR, 'H reconstruction', 'matrix')
    A = q(H, scale[:, None]*S[:, free])
    y = q(H, scale*(p['train_v'].ravel()-s0))
    close(q(H, y), y, 'Qy')
    arrays = dict(A=A, y=y, q_y=q(H, y), H=H, C_H=CH, R=R, scale=scale, U0=u0,
                  free_dofs=free, fixed_dofs=fixed, stencil_nodes=nodes, stencil_coeff=coeff,
                  rigid_center=center, rigid_m2=np.asarray(m2))
    arrays.update({'source_'+key: val for key, val in p.items()})
    for k in ARMS:
        uk = fields[k]
        sampled = mm(S, uk.ravel())
        close(sampled.reshape(-1, 2), fields[k+'_sampled'], 'saved sample '+k)
        z = (uk-u0).ravel()[free]
        inserted = np.zeros(1722); inserted[free] = z
        close(inserted, (uk-u0).ravel(), 'Fz '+k)
        b = q(H, scale*(sampled-s0))
        close(mm(A, z), b, 'b=Az '+k)
        arrays.update({k+'_node': uk, k+'_sampled': fields[k+'_sampled'], k+'_z': z, k+'_b': b, k+'_q_b': q(H, b)})
    budget.check()
    return arrays


def repair(H, Lr, y, factors):
    B = q(H, Lr)  # Only candidate Q application; later Q checks never write back.
    U, T = factors.qr(B)
    eta = float(np.max(np.sum(np.abs(np.eye(len(T))-T), axis=1)))
    require(np.isfinite(eta) and eta <= .5, 'eta hard bound')
    close(mm(U, T), B, 'UT=B', 'matrix')
    close(mm(U.T, U), np.eye(len(T)), 'U Gram', 'matrix')
    close(q(H, U), U, 'QU', 'matrix')
    coef = mm(U.T, y); p = mm(U, coef); r = p-y
    close(mm(U.T, r), np.zeros(U.shape[1]), 'UTr')
    close(q(H, p), p, 'Qp'); close(q(H, r), r, 'Qr')
    return dict(B=B, U=U, T=T, p=p, r=r, coef=coef,
                q_p=q(H, p), q_r=q(H, r), eta=np.asarray(eta))


def analyze(a, factors, budget, expected_rank=None):
    A, y, H = a['A'], a['y'], a['H']
    require(A.shape == (1296, 1482) and np.isfinite(A).all() and np.any(A), 'A finite nonzero shape')
    budget.check(); L, s, Vh = factors.svd(A); budget.check()
    require(np.isfinite(s).all() and s[0] > 0 and np.all(s >= 0) and np.all(np.diff(s) <= 0), 'singular values')
    tau = float(1e-12*s[0]); mask = s > tau
    require(not np.any((s >= tau/10) & (s <= 10*tau)), 'cutoff unresolved')
    close(mm(L*s, Vh), A, 'full SVD reconstruction producer only', 'matrix')
    close(mm(L.T, L), np.eye(len(s)), 'full L Gram producer only', 'matrix')
    close(mm(Vh, Vh.T), np.eye(len(s)), 'full V Gram producer only', 'matrix')
    rank = int(mask.sum())
    a.update(s=s, tau=np.asarray(tau), mask=mask, Lr=L[:, mask], Vh_r=Vh[mask])
    require(rank > 0 and (expected_rank is None or rank == expected_rank),
            'RANK_IDENTITY_REVIEW_REQUIRED: observed='+str(rank)+' expected='+str(expected_rank))
    Lr, Vr, sr = a['Lr'], a['Vh_r'].T, s[mask]
    close(mm(A, Vr), Lr*sr, 'AVr=Lr sr', 'matrix')
    close(mm(A.T, Lr), Vr*sr, 'AT Lr=Vr sr', 'matrix')
    legacy_p = mm(Lr, mm(Lr.T, y))
    a.update(legacy_p=legacy_p, legacy_r=legacy_p-y)
    a.update(repair(H, Lr, y, factors)); budget.check()
    rows = []
    JQ = square(a['r'])
    decision = 1e-15+1e-12*max(np.sqrt(square(y)), *(np.sqrt(square(a[k+'_b']-y)) for k in ARMS))
    legacy = {}
    for key in ('legacy_p', 'legacy_r'):
        v = a[key]; check = q(H, v)
        a['q_'+key] = check
        ratio = float(np.max(np.abs(check-v)/(1e-15+1e-12*np.abs(v))))
        legacy[key] = dict(Q_ratio=ratio, Q_pass=ratio <= 1)
    for k in ARMS:
        b = a[k+'_b']
        close(q(H, b), b, 'Qb '+k)
        close(mm(a['U'], mm(a['U'].T, b)), b, 'RETAINED_IMAGE_NOT_CERTIFIED '+k)
        r, d = b-y, b-a['p']
        close(r, a['r']+d, 'residual addition '+k)
        J, extra = square(r), square(d)
        cross = float(2*np.einsum('i,i->', a['r'], d, optimize=False))
        require(abs(cross) <= 1e-18+1e-12*max(J, JQ, extra), 'cross term '+k)
        close(J, JQ+extra, 'final square ledger '+k, 'square')
        a[k+'_r'], a[k+'_d'] = r, d
        rows.append(dict(arm=k, J_Q_mm2=JQ, J_k_mm2=J, gap2_mm2=extra,
                         gap_mm=float(np.sqrt(extra)), cross_mm2=cross,
                         RMS_Q_resolved=bool(np.sqrt(JQ) > decision), gap_resolved=bool(np.sqrt(extra) > decision)))
    require((factors.svd_calls, factors.qr_calls) == (1, 2), 'factor count')
    budget.check()
    return dict(rank=rank, cutoff=tau, eta=float(a['eta']), J_Q_mm2=JQ,
                RMS_Q_mm=float(np.sqrt(JQ)), T_mm=float(decision), rows=rows,
                legacy=legacy, svd_calls=1, qr_calls=2,
                scope='new Q-consistent retained-space training numerical certificate; no physical inversion')


def sha(path):
    safe_path(path, file=True)
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def selective(path, keys):
    safe_path(path, file=True)
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in keys}  # Deliberately do not iterate/decode other members.


def json_read(path):
    safe_path(path, file=True)
    return json.loads(path.read_text())


def safe_path(path, *, file=False):
    path = Path(path)
    require(path.is_absolute(), 'absolute path required')
    for part in (path, *path.parents):
        require(not part.is_symlink(), 'symlink forbidden: '+str(part))
    if file:
        require(path.is_file(), 'regular input file required: '+str(path))


def load_real(opaque_authorized):
    require(opaque_authorized, 'two opaque hashes need explicit execution-package approval')
    receipts = []
    before = {}
    for root, names, anchor, mode, runid in (
            (PREP, PREP_NAMES, ANCHORS[0], 'prepare', 'S03-E016-R001'),
            (FIT, FIT_NAMES, ANCHORS[1], 'fit', 'S03-E016-R002')):
        rp = root/'execution_receipt.json'
        require(sha(rp) == anchor, 'receipt anchor '+mode)
        r = json_read(rp)
        require(r['execution_status'] == 'succeeded' and r['mode'] == mode and r['run_id'] == runid, 'source execution '+mode)
        for name in names:
            path = root/name
            before[str(path)] = sha(path)
            require(before[str(path)] == r['artifacts_sha256'][name], 'source hash '+name)
        before[str(rp)] = anchor
        receipts.append(r)
    pb = dict(receipt_sha256=ANCHORS[0], artifacts_sha256={n: before[str(PREP/n)] for n in PREP_NAMES})
    meta, audit, fm = (json_read(PREP/'preparation.json'), json_read(PREP/'geometry_audit.json'), json_read(FIT/'fit.json'))
    require(receipts[1]['input_bindings'] == pb and fm['source_prepare'] == pb, 'prepare-fit binding')
    require(meta['cycle'] == audit['cycle'] == fm['cycle'] == '292018.5' and meta['reference'] == 1, 'cycle/ref')
    require(audit['stages'] == [13, 14] and meta['observations'] == 648 and len(audit['training_headers']) == 2, 'training metadata')
    require(fm['status'] == 'four_predictions_frozen_before_held_response', 'fit status')
    from decimal import Decimal
    forces = []
    for stage, header, force in zip((13, 14), audit['training_headers'], meta['forces'][:2]):
        require(Decimal(header['current_stage_index']) == stage and Decimal(header['reference_stage_index']) == 1 and
                Decimal(header['cycles']) == Decimal('292018.5'), 'training header')
        require(float(header['force']) == force and np.isfinite(force), 'training force')
        forces.append(force)
    require(len(forces) == 2 and 0 < forces[0] < forces[1], 'training force order')
    return selective(PREP/'prepared.npz', PREP_KEYS), selective(FIT/'solved_fields.npz', FIELD_KEYS), before


def snapshot(repo, reviewed):
    """A later documentation-only commit may record the completed static review."""
    current = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    require(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo, text=True).strip(), 'clean source tree')
    subprocess.run(['git', 'merge-base', '--is-ancestor', reviewed, current], cwd=repo, check=True)
    changed = subprocess.check_output(['git', 'diff', '--name-only', reviewed, current], cwd=repo, text=True).splitlines()
    require(all(name.startswith('docs/') for name in changed), 'only later review-record docs may differ')
    return current


def code_hashes():
    return {name: sha(Path(__file__).with_name(name)) for name in
            ('aa2024_q_recheck.py', 'aa2024_q_verify.py', 'test_aa2024_q_recheck.py')}


def final_identity(repo, reviewed, initial_head, initial_hashes):
    require(snapshot(repo, reviewed) == initial_head, 'runtime HEAD changed')
    require(code_hashes() == initial_hashes, 'runtime code changed')


def artificial():
    """648 artificial points, same mesh/operator dimensions; resource test, not real accuracy."""
    x, y = np.meshgrid(np.linspace(-15.7, 15.7, 27), np.linspace(-6.7, 6.7, 24))
    xy = np.c_[x.ravel(), y.ravel()]
    mesh, tri, bd = mesh_definition()
    p = dict(ids=np.arange(1, 649), xy=xy, weights=np.ones(648), mesh=mesh, tri=tri,
             boundary=bd, bc=np.zeros((120, 2)),
             train_v=np.c_[.001*np.sin(xy[:, 0]), .002*np.cos(xy[:, 1])])
    S, _, _ = sampling(xy)
    fields = {}
    for j, k in enumerate(ARMS, 1):
        u = np.c_[np.sin(j*mesh[:, 0]/18)*np.cos(mesh[:, 1]/9),
                  np.cos(mesh[:, 0]/18)*np.sin(j*mesh[:, 1]/9)]*.001
        u[bd] = 0
        fields[k], fields[k+'_sampled'] = u, mm(S, u.ravel()).reshape(-1, 2)
    return p, fields


def write_json(path, obj):
    safe_path(path)
    with path.open('x') as f:
        json.dump(obj, f, indent=2, allow_nan=False)


def draw(a, report, out, mode):
    # Force all writable plotting caches into this new run before first import.
    for key, name in (('MPLCONFIGDIR', '.mplconfig'), ('XDG_CACHE_HOME', '.cache')):
        cache = out/name
        safe_path(cache)
        cache.mkdir(exist_ok=False)
        os.environ[key] = str(cache)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    title = 'E019-D03 | '+mode+' | stages13/14 training only'
    fig, axes = plt.subplots(2, 4, figsize=(14, 6), sharex=True, sharey=True, constrained_layout=True)
    maps = [(a['r']/a['scale']).reshape(-1, 2)]+[(a[k+'_r']/a['scale']).reshape(-1, 2) for k in ARMS]
    bound = max(float(np.max(np.abs(v))) for v in maps) or 1e-15
    try:
        for col, (name, v) in enumerate(zip(('Q retained projection',)+ARMS, maps)):
            for row, component in enumerate(('U', 'V')):
                ax = axes[row, col]
                points = ax.scatter(*a['source_xy'].T, c=v[:, row], s=12, cmap='RdBu_r', vmin=-bound, vmax=bound)
                ax.set(xlabel='stage13 x [mm]', ylabel='y [mm]', title=name+' / '+component, aspect='equal')
        fig.colorbar(points, ax=axes, label='D^-1 residual [mm]', shrink=.8)
        fig.suptitle(title+'\nAll 648 points; deweighted display only; shared scale', fontsize=10)
        for ext in ('png', 'pdf'):
            fig.savefig(out/('q_residuals.'+ext), dpi=170)
    finally:
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 5), constrained_layout=True)
    try:
        rows = report['rows']; x = np.arange(3)
        floor = [r['J_Q_mm2'] for r in rows]; gap = [r['gap2_mm2'] for r in rows]
        ax.bar(x, floor, label='Q retained residual J_Q', color='#0072B2')
        ax.bar(x, gap, bottom=floor, label='model deviation squared', color='#E69F00')
        ax.plot(x, [r['J_k_mm2'] for r in rows], 'ko', label='original field J_k')
        ax.set(xticks=x, xticklabels=ARMS, ylabel='weighted squared residual [mm²]', title=title)
        ax.legend(loc='upper left', bbox_to_anchor=(0, -.12), ncol=3, frameon=False, fontsize=8)
        for ext in ('png', 'pdf'):
            fig.savefig(out/('q_square_ledger.'+ext), dpi=170)
    finally:
        plt.close(fig)
    for stem, panels in (
            ('q_residuals', 'U/V rows, Q retained projection then old/proxy/intact columns; red/blue signed D^-1 residual mm. One symmetric scale from all panels. Zero maps use display-only +/-1e-15 mm.'),
            ('q_square_ledger', 'old/proxy/intact bars: blue J_Q plus orange gap squared; black dots J_k. Vertical axis mm²; squares add, RMS does not.')):
        (out/(stem+'.md')).write_text('# '+stem+'\n\n## Figure question\n\nIs the retained-space residual ledger numerically consistent?\n\n## How to read\n\n'+panels+
            '\n\n## Data provenance\n\nSame-directory certificate.npz/report.json; E019-D03 '+mode+
            '; all 648 source points, same weights/BC. No held data.\n\n## Key numerical takeaway\n\n'+json.dumps(report['rows'])+
            '\n\n## Limitations and claim boundary\n\nTraining C1 numerical check, one specimen/cycle292018.5 for real mode; artificial mode is resource-only. '
            'No physical inversion, phase field, causal allocation, new prediction or historical E019 rescue. Deweighting is display-only. No interpolation, smoothing, subset selection or component-RMS renormalization.\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('synthetic', 'real'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--allow-two-opaque-hashes', action='store_true')
    args = parser.parse_args()
    require(all(os.environ.get(k) == '1' for k in THREADS) and os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'single CPU environment')
    repo = Path(__file__).resolve().parents[1]
    actual = snapshot(repo, args.source_commit)
    allowed = BASE/'S03-E019-D03'/('S03-E019-D03-B001' if args.mode == 'synthetic' else 'S03-E019-D03-R001')
    safe_path(allowed)
    require(args.output == allowed and not allowed.exists(), 'fresh exact output root')
    allowed.mkdir(parents=True, exist_ok=False)
    receipt = dict(mode=args.mode, source_commit=args.source_commit, runtime_head=actual,
                   python_version=sys.version, numpy_version=np.__version__,
                   hostname=socket.gethostname(), pid=os.getpid(), command=sys.argv,
                   source_sha256=code_hashes(),
                   execution_status='incomplete', inputs={}, artifacts_sha256={})
    budget = Budget(); factors = Factors()
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            with np.errstate(all='raise'):
                budget.check()
                if args.mode == 'real':
                    p, fields, before = load_real(args.allow_two_opaque_hashes)
                    receipt['inputs'] = before
                else:
                    require(not args.allow_two_opaque_hashes, 'synthetic has no real input authority')
                    p, fields = artificial(); before = {}
                budget.check(); arrays = construct(p, fields, factors, budget)
                report = analyze(arrays, factors, budget, expected_rank=1203 if args.mode == 'real' else None)
                safe_path(allowed/'certificate.npz')
                np.savez(allowed/'certificate.npz', **arrays)
                write_json(allowed/'report.json', report)
                budget.check(); draw(arrays, report, allowed, args.mode); budget.check()
                for path, digest in before.items():
                    require(sha(path) == digest, 'source changed '+path)
                receipt['artifacts_sha256'] = {p.name: sha(p) for p in allowed.iterdir() if p.is_file()}
                final_identity(repo, args.source_commit, actual, receipt['source_sha256'])
                receipt.update(elapsed_before_receipt=budget.check(), svd_calls=factors.svd_calls, qr_calls=factors.qr_calls,
                               execution_status='producer_completed_not_independently_accepted')
                write_json(allowed/'execution_receipt.json', receipt)
                budget.check()
                final_identity(repo, args.source_commit, actual, receipt['source_sha256'])
                write_json(allowed/'completion.json', dict(receipt_sha256=sha(allowed/'execution_receipt.json')))
                elapsed = budget.check()
        print(json.dumps(dict(status='producer_completed_not_independently_accepted', elapsed_seconds=elapsed)))
    except BaseException as exc:
        completion = allowed/'completion.json'
        if completion.exists():
            completion.unlink()  # Only this fresh run's invalid success marker, never frozen inputs.
        receipt.update(execution_status='failed', error=type(exc).__name__+': '+str(exc),
                       svd_calls=factors.svd_calls, qr_calls=factors.qr_calls)
        safe_path(allowed/'failure_receipt.json')
        with (allowed/'failure_receipt.json').open('x') as f:
            json.dump(receipt, f, indent=2, allow_nan=False)
        raise


if __name__ == '__main__':
    main()
