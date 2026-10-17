#!/usr/bin/env python3
"""Independent saved-operand evaluation; no producer import or factorization.

Execution, including synthetic artifacts, requires separate approval.
"""
import argparse
from decimal import Decimal, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import warnings

import numpy as np
from scipy.linalg.blas import dgemm

ARMS = ('old', 'proxy', 'intact')
BASE = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments')
PREP = BASE/'S03-E016/S03-E016-R001/prepare'
FIT = BASE/'S03-E016/S03-E016-R002/fit'
PREP_KEYS = ('ids', 'xy', 'weights', 'train_v', 'mesh', 'tri', 'boundary', 'bc')
FIELD_KEYS = ARMS+tuple(k+'_sampled' for k in ARMS)
ANCHORS = ('8655d49b30e341d488eeb8c15db9a7d347f236634a22adbbf39fcb7b4bbd3ccf',
           '3173f0f659d6e451f7fccc39a4ca0973ae3caad750c9d98ce754a1bcec325674')


class Rejected(ValueError):
    pass


def demand(ok, text):
    if not ok:
        raise Rejected(text)


def equal(a, b, text, kind='vector'):
    a, b = np.asarray(a), np.asarray(b)
    eps = {'matrix': 1e-12, 'vector': 1e-15, 'square': 1e-18}[kind]
    demand(a.shape == b.shape and np.isfinite(a).all() and np.isfinite(b).all(), text+' finite/shape')
    demand(np.all(np.abs(a-b) <= eps+1e-12*np.abs(b)), text)


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    with path.open() as f:
        return json.load(f)


class Timer:
    def __init__(self):
        self.start = time.monotonic()

    def check(self):
        elapsed = time.monotonic()-self.start
        if elapsed >= 60:
            raise TimeoutError('independent soft60s incomplete; no retry')
        return elapsed


def product(a, b):
    """Full BLAS contraction, not producer einsum or its differences."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if b.ndim == 1:
        return dgemm(1., a, b[:, None])[:, 0]
    return dgemm(1., a, b)


def ref_dot(a, b, method):
    if method == 'fsum':
        return math.fsum(float(x)*float(y) for x, y in zip(a, b))
    return sum((Decimal.from_float(float(x))*Decimal.from_float(float(y)) for x, y in zip(a, b)), Decimal(0))


def vector_product(a, b, method, timer):
    # Decimal results stay Decimal across both stages of a full projection/Q.
    vals = []
    for i, row in enumerate(a):
        if i % 64 == 0:
            timer.check()
        if method == 'fsum':
            vals.append(math.fsum(float(x)*float(y) for x, y in zip(row, b)))
        else:
            vals.append(sum((Decimal.from_float(float(x))*(y if isinstance(y, Decimal) else Decimal.from_float(float(y)))
                             for x, y in zip(row, b)), Decimal(0)))
    return vals


def project(vectors, x, method, timer):
    return vector_product(vectors, vector_product(vectors.T, x, method, timer), method, timer)


def float_vector(x):
    return np.asarray([float(v) for v in x])


def quotient(H, x, method, timer):
    projection = project(H, x, method, timer)
    if method == 'fsum':
        return np.asarray([float(v)-p for v, p in zip(x, projection)])
    return np.asarray([float(Decimal.from_float(float(v))-p) for v, p in zip(x, projection)])


def stencil(xy):
    """Independent loop and barycentric formula on the original lower-left diagonal."""
    S = np.zeros((2*len(xy), 1722)); ns, cs = [], []
    for row, (x, y) in enumerate(xy):
        demand(abs(x) < 16.2 and abs(y) < 7.2, 'strict ROI')
        gx, gy = (x+18)/36*40, (y+9)/18*20
        i, j = math.floor(gx), math.floor(gy)
        u, v = gx-i, gy-j; a = 41*j+i
        if v <= u:
            nodes, coeff = (a, a+1, a+42), (1-u, u-v, v)
        else:
            nodes, coeff = (a, a+42, a+41), (1-v, u, v-u)
        ns.append(nodes); cs.append(coeff)
        for node, weight in zip(nodes, coeff):
            S[2*row, 2*node] = S[2*row+1, 2*node+1] = weight
    return S, np.array(ns), np.array(cs)


def source_and_operators(a, timer):
    xy, w = a['source_xy'], a['source_weights']
    demand(xy.shape == (648, 2) and w.shape == (648,) and np.all(w > 0) and np.isfinite(xy).all() and np.isfinite(w).all(), 'training support')
    ids = a['source_ids']
    demand(ids.shape == (648,) and np.issubdtype(ids.dtype, np.integer) and np.all(ids > 0) and len(np.unique(ids)) == 648, 'fixed IDs')
    demand(a['source_train_v'].shape == (648, 2) and np.isfinite(a['source_train_v']).all(), 'training increment')
    demand(a['source_bc'].shape == (120, 2) and np.isfinite(a['source_bc']).all(), 'boundary values')
    xx, yy = np.meshgrid(np.linspace(-18, 18, 41), np.linspace(-9, 9, 21))
    mesh = np.c_[xx.ravel(), yy.ravel()]
    triangles = []
    for j in range(20):
        for i in range(40):
            left = j*41+i
            triangles += [[left, left+1, left+42], [left, left+42, left+41]]
    bd = (np.abs(mesh[:, 0]) == 18) | (np.abs(mesh[:, 1]) == 9)
    for key, ref in (('source_mesh', mesh), ('source_tri', np.array(triangles)), ('source_boundary', bd)):
        demand(np.array_equal(a[key], ref), 'mesh identity '+key)
    fixed = np.array([2*i+c for i in range(861) if bd[i] for c in (0, 1)])
    free = np.array([2*i+c for i in range(861) if not bd[i] for c in (0, 1)])
    demand(np.array_equal(a['fixed_dofs'], fixed) and np.array_equal(a['free_dofs'], free), 'DOF order')
    S, nodes, coeff = stencil(xy)
    demand(np.array_equal(nodes, a['stencil_nodes']), 'CST node IDs')
    equal(coeff, a['stencil_coeff'], 'CST coefficients', 'matrix')
    demand(not np.any(S[:, fixed]), 'direct BC sampling')
    total = math.fsum(float(x) for x in w)
    wn = w/total; scale = np.repeat(np.sqrt(wn), 2)
    equal(scale, a['scale'], 'D', 'matrix')
    center = np.array([math.fsum(float(wn[i])*float(xy[i, c]) for i in range(648)) for c in (0, 1)])
    centered = xy-center
    m2 = math.fsum(float(wn[i])*(float(centered[i, 0])**2+float(centered[i, 1])**2) for i in range(648))
    demand(math.isfinite(m2) and m2 > 0, 'rigid full rank second moment')
    equal(center, a['rigid_center'], 'rigid center', 'matrix')
    equal(m2, a['rigid_m2'], 'rigid moment', 'matrix')
    R = np.zeros((1296, 3)); R[::2, 0] = 1; R[1::2, 1] = 1
    R[::2, 2], R[1::2, 2] = -centered[:, 1], centered[:, 0]
    equal(R, a['R'], 'rigid design', 'matrix')
    H = a['H']
    equal(product(H, a['C_H']), scale[:, None]*R, 'DR reconstruction', 'matrix')
    equal(product(H.T, H), np.eye(3), 'H Gram', 'matrix')
    u0 = np.zeros((861, 2)); u0[bd] = a['source_bc']
    equal(u0, a['U0'], 'affine origin')
    s0 = product(S, u0.ravel()); equal(s0, np.zeros(1296), 'SU0')
    SF = scale[:, None]*S[:, free]
    A = SF-product(H, product(H.T, SF))
    equal(A, a['A'], 'A=QDSF', 'matrix')
    raw_y = scale*(a['source_train_v'].ravel()-s0)
    y = raw_y-product(H, product(H.T, raw_y))
    equal(y, a['y'], 'y construction')
    for k in ARMS:
        node = a[k+'_node']; equal(node[bd], a['source_bc'], 'BC '+k)
        sampled = product(S, node.ravel()); equal(sampled.reshape(-1, 2), a[k+'_sampled'], 'sample '+k)
        z = (node-u0).ravel()[free]; equal(z, a[k+'_z'], 'z '+k)
        expanded = np.zeros(1722); expanded[free] = z
        equal(expanded, (node-u0).ravel(), 'Fz '+k)
        raw_b = scale*(sampled-s0)
        b = raw_b-product(H, product(H.T, raw_b))
        equal(b, a[k+'_b'], 'b construction '+k)
        equal(product(a['A'], z), a[k+'_b'], 'b=Az '+k)
    timer.check()


def matrices(a, report, timer):
    A, Lr, Vr, U, T, H = (a[k] for k in ('A', 'Lr', 'Vh_r', 'U', 'T', 'H'))
    Vr = Vr.T; s, mask = a['s'], a['mask']; rank = int(mask.sum())
    demand(s.shape == (1296,) and np.isfinite(s).all() and s[0] > 0 and np.all(s >= 0) and np.all(np.diff(s) <= 0), 's')
    demand(float(a['tau']) == 1e-12*float(s[0]) and np.array_equal(mask, s > a['tau']), 'cutoff selection')
    demand(not np.any((s >= a['tau']/10) & (s <= 10*a['tau'])), 'cutoff guard')
    demand(Lr.shape == U.shape == (1296, rank) and Vr.shape == (1482, rank) and T.shape == (rank, rank), 'retained dimensions')
    demand(rank == report['rank'] and rank > 0, 'report rank')
    for name, basis in (('Lr', Lr), ('Vr', Vr), ('U', U)):
        equal(product(basis.T, basis), np.eye(rank), name+' full Gram', 'matrix'); timer.check()
    equal(product(A, Vr), Lr*s[mask], 'retained left relation', 'matrix'); timer.check()
    equal(product(A.T, Lr), Vr*s[mask], 'retained right relation', 'matrix'); timer.check()
    equal(Lr-product(H, product(H.T, Lr)), a['B'], 'B=QLr', 'matrix')
    equal(product(U, T), a['B'], 'UT=B full', 'matrix'); timer.check()
    equal(U-product(H, product(H.T, U)), U, 'QU full', 'matrix')
    demand(np.isfinite(T).all() and np.all(np.diag(T) > 0) and np.count_nonzero(np.tril(T, -1)) == 0, 'positive triangular T')
    eta = max(math.fsum(abs(float(i == j)-float(T[i, j])) for j in range(rank)) for i in range(rank))
    demand(eta <= .5 and float(a['eta']) <= .5, 'eta hard bound')
    equal(eta, a['eta'], 'eta independent evaluation', 'matrix')
    equal(eta, report['eta'], 'eta report', 'matrix')


def vectors(a, report, timer):
    H, U, Lr, y, p, r = (a[k] for k in ('H', 'U', 'Lr', 'y', 'p', 'r'))
    for method in ('fsum', 'decimal80'):
        with localcontext() as context:
            context.prec = 80
            py = project(U, y, method, timer)
            equal(float_vector(py), p, method+' p')
            equal(float_vector(vector_product(U.T, y, method, timer)), a['coef'], method+' coefficients')
            if method == 'decimal80':
                rr = [v-Decimal.from_float(float(yi)) for v, yi in zip(py, y)]
            else:
                rr = [v-float(yi) for v, yi in zip(py, y)]
            equal(float_vector(rr), r, method+' r independent evaluation')
            lp = project(Lr, y, method, timer)
            equal(float_vector(lp), a['legacy_p'], method+' legacy p')
            if method == 'decimal80':
                lr = [v-Decimal.from_float(float(yi)) for v, yi in zip(lp, y)]
            else:
                lr = [v-float(yi) for v, yi in zip(lp, y)]
            equal(float_vector(lr), a['legacy_r'], method+' legacy r')
            for key in ('y', 'p', 'r', 'legacy_p', 'legacy_r')+tuple(k+'_b' for k in ARMS):
                v = a[key]; qv = quotient(H, v, method, timer)
                equal(qv, a['q_'+key] if not key.endswith('_b') else a[key[:-2]+'_q_b'], 'REFERENCE_PATH_UNRESOLVED '+method+' Q evaluation '+key)
                ratio = float(np.max(np.abs(qv-v)/(1e-15+1e-12*np.abs(v))))
                expected = report['legacy'][key]['Q_pass'] if key.startswith('legacy') else True
                demand((ratio <= 1) == expected, 'REFERENCE_PATH_UNRESOLVED '+method+' Q status '+key)
            equal(float_vector(vector_product(U.T, r, method, timer)), np.zeros(U.shape[1]), method+' UTr')
            for k in ARMS:
                b = a[k+'_b']; equal(float_vector(project(U, b, method, timer)), b, method+' retained image '+k)
                equal(b-y, a[k+'_r'], method+' rk '+k)
                equal(b-p, a[k+'_d'], method+' dk '+k)
                equal(a[k+'_r'], r+a[k+'_d'], method+' residual addition '+k)
            scalars(a, report, method)
            timer.check()


def scalars(a, report, method):
    JQ = float(ref_dot(a['r'], a['r'], method))
    equal(JQ, report['J_Q_mm2'], method+' JQ', 'square')
    equal(math.sqrt(JQ), report['RMS_Q_mm'], method+' weighted vector RMS')
    threshold = 1e-15+1e-12*max(math.sqrt(float(ref_dot(a['y'], a['y'], method))),
        *(math.sqrt(float(ref_dot(a[k+'_r'], a[k+'_r'], method))) for k in ARMS))
    equal(threshold, report['T_mm'], method+' arithmetic T')
    demand([row['arm'] for row in report['rows']] == list(ARMS), 'arm order')
    for k, row in zip(ARMS, report['rows']):
        rk, dk = a[k+'_r'], a[k+'_d']
        J, extra = float(ref_dot(rk, rk, method)), float(ref_dot(dk, dk, method))
        cross = 2*float(ref_dot(a['r'], dk, method))
        equal(J, row['J_k_mm2'], method+' Jk '+k, 'square')
        equal(JQ, row['J_Q_mm2'], method+' row JQ '+k, 'square')
        equal(extra, row['gap2_mm2'], method+' gap² '+k, 'square')
        equal(math.sqrt(extra), row['gap_mm'], method+' gap '+k)
        equal(cross, row['cross_mm2'], method+' cross report '+k, 'square')
        demand(abs(cross) <= 1e-18+1e-12*max(J, JQ, extra), method+' cross bound '+k)
        equal(J, JQ+extra, method+' recomputed square identity '+k, 'square')
        equal(row['J_k_mm2'], row['J_Q_mm2']+row['gap2_mm2'], method+' saved square identity '+k, 'square')
        demand(row['RMS_Q_resolved'] == (math.sqrt(JQ) > threshold) and row['gap_resolved'] == (math.sqrt(extra) > threshold), method+' arithmetic classification '+k)


def real_sources(a, receipt):
    names = (('preparation.json', 'prepared.npz', 'geometry_audit.json', 'training_geometry.npz'),
             ('fit.json', 'frozen_predictions.npz', 'solved_fields.npz'))
    expected_paths = {str(root/n) for root, ns in zip((PREP, FIT), names) for n in ns+('execution_receipt.json',)}
    demand(set(receipt['inputs']) == expected_paths, 'exact byte whitelist')
    for path, digest in receipt['inputs'].items():
        demand(file_sha(path) == digest, 'unchanged source '+path)
    for root, anchor in zip((PREP, FIT), ANCHORS):
        demand(file_sha(root/'execution_receipt.json') == anchor, 'source receipt anchor')
    with np.load(PREP/'prepared.npz', allow_pickle=False) as source:
        for key in PREP_KEYS:
            demand(np.array_equal(source[key], a['source_'+key]), 'source array identity '+key)
    with np.load(FIT/'solved_fields.npz', allow_pickle=False) as source:
        for key in FIELD_KEYS:
            saved = key if key.endswith('_sampled') else key+'_node'
            demand(np.array_equal(source[key], a[saved]), 'source field identity '+key)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('synthetic', 'real'))
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--allow-two-opaque-hashes', action='store_true')
    args = parser.parse_args()
    threads = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS', 'BLIS_NUM_THREADS')
    demand(all(os.environ.get(k) == '1' for k in threads) and os.environ.get('CUDA_VISIBLE_DEVICES') == '', 'single CPU environment')
    repo = Path(__file__).resolve().parents[1]
    current = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    subprocess.run(['git', 'merge-base', '--is-ancestor', args.source_commit, current], cwd=repo, check=True)
    changes = subprocess.check_output(['git', 'diff', '--name-only', args.source_commit, current], cwd=repo, text=True).splitlines()
    demand(all(name.startswith('docs/') for name in changes), 'only later review records may differ')
    demand(not subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo, text=True).strip(), 'clean source')
    run = 'S03-E019-D03-B001' if args.mode == 'synthetic' else 'S03-E019-D03-R001'
    demand(args.input == BASE/'S03-E019-D03'/run and args.output == BASE/'S03-E019-D03'/(run+'-acceptance'), 'exact input/output root')
    args.output.mkdir(parents=True, exist_ok=False)
    timer = Timer(); before = {}; result = dict(status='incomplete', command=sys.argv, source_commit=args.source_commit, runtime_head=current)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error')
            with np.errstate(all='raise'):
                demand(not (args.input/'failure_receipt.json').exists(), 'producer failure recorded')
                receipt = read_json(args.input/'execution_receipt.json')
                completion = read_json(args.input/'completion.json')
                demand(completion['receipt_sha256'] == file_sha(args.input/'execution_receipt.json'), 'producer completion binding')
                demand(receipt['mode'] == args.mode and receipt['source_commit'] == args.source_commit and
                       receipt['execution_status'] == 'producer_completed_not_independently_accepted', 'producer identity/status')
                demand((receipt['svd_calls'], receipt['qr_calls']) == (1, 2), 'controlled API count')
                for name, digest in receipt['source_sha256'].items():
                    demand(name in ('aa2024_q_recheck.py', 'aa2024_q_verify.py', 'test_aa2024_q_recheck.py') and
                           file_sha(Path(__file__).with_name(name)) == digest, 'reviewed producer code identity')
                required = {'certificate.npz', 'report.json', 'q_residuals.png', 'q_residuals.pdf', 'q_residuals.md',
                            'q_square_ledger.png', 'q_square_ledger.pdf', 'q_square_ledger.md'}
                demand(set(receipt['artifacts_sha256']) == required, 'exact artifact list')
                for name, digest in receipt['artifacts_sha256'].items():
                    path = args.input/name; demand(file_sha(path) == digest, 'artifact hash '+name); before[str(path)] = digest
                for name in ('execution_receipt.json', 'completion.json'):
                    before[str(args.input/name)] = file_sha(args.input/name)
                with np.load(args.input/'certificate.npz', allow_pickle=False) as z:
                    a = {key: z[key] for key in z.files}
                report = read_json(args.input/'report.json'); timer.check()
                if args.mode == 'real':
                    demand(args.allow_two_opaque_hashes, 'real source opaque-read approval required')
                    real_sources(a, receipt)
                    demand(report['rank'] == 1203, 'rank identity requires review')
                else:
                    demand(not args.allow_two_opaque_hashes and receipt['inputs'] == {}, 'synthetic no real inputs')
                source_and_operators(a, timer); matrices(a, report, timer); vectors(a, report, timer)
                for name in ('q_residuals', 'q_square_ledger'):
                    text = (args.input/(name+'.md')).read_text()
                    demand(all(heading in text for heading in ('How to read', 'Data provenance', 'Limitations', 'Key numerical takeaway')), 'figure sidecar '+name)
                for path, digest in before.items():
                    demand(file_sha(path) == digest, 'artifact changed during acceptance')
                result.update(status='saved_arithmetic_accepted_not_visual_QA', elapsed_before_receipt=timer.check(),
                              input_sha256=before, svd_calls=0, qr_calls=0,
                              limitation='No full SVD replay, unretained-spectrum certificate, physical identification, PNG/PDF visual acceptance or history rescue')
                with (args.output/'acceptance.json').open('x') as f:
                    json.dump(result, f, indent=2, allow_nan=False)
                timer.check()
                with (args.output/'completion.json').open('x') as f:
                    json.dump(dict(acceptance_sha256=file_sha(args.output/'acceptance.json')), f)
                timer.check()
        print(json.dumps(result))
    except BaseException as exc:
        if (args.output/'completion.json').exists():
            (args.output/'completion.json').unlink()
        result.update(status='failed', error=type(exc).__name__+': '+str(exc))
        with (args.output/'failure.json').open('x') as f:
            json.dump(result, f, indent=2, allow_nan=False)
        raise


if __name__ == '__main__':
    main()
