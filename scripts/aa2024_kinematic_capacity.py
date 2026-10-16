#!/usr/bin/env python3
"""E019 fixed-BC observation-space capacity; no stiffness, physical fit or held data."""
import argparse
import csv
import json
import os
import socket
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
from scipy import linalg
from scipy.sparse import csr_matrix
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import aa2024_geometry_prior as prior

ARMS = ('old', 'proxy', 'intact')
THREADS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
           'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')
PROTOCOL_SHA = 'b956f21fa8c417d65d668ca876d91a35b04756c97318938eb95312e758b0cbde'
DEFAULT_LOCK = dict(prepare='8655d49b30e341d488eeb8c15db9a7d347f236634a22adbbf39fcb7b4bbd3ccf',
                    fit='3173f0f659d6e451f7fccc39a4ca0973ae3caad750c9d98ce754a1bcec325674',
                    runs=dict(prepare='S03-E016-R001', fit='S03-E016-R002'), observations=648)


def within(start, clock):
    if clock()-start >= 60.: raise TimeoutError('soft60s whole-analysis budget; no retry')


def hashes(paths):
    return {str(p): prior.sha(p) for p in paths}


def multiply(a, b):
    """Explicit float64 contraction, no local NumPy matmul/BLAS warning path."""
    a, b = np.asarray(a, dtype=np.float64), np.asarray(b, dtype=np.float64)
    if a.ndim != 2 or b.ndim not in (1, 2) or a.shape[1] != b.shape[0]:
        raise ValueError('contraction shape')
    result = np.einsum('ik,k->i' if b.ndim == 1 else 'ik,kj->ij', a, b, optimize=False)
    if not np.isfinite(result).all(): raise ValueError('nonfinite contraction')
    return result


def close(a, b, label, *, square=False, matrix=False):
    atol = 1e-12 if matrix else (1e-18 if square else 1e-15)
    if (np.shape(a) != np.shape(b) or not np.isfinite(a).all() or not np.isfinite(b).all() or
            not np.allclose(a, b, rtol=1e-12, atol=atol)):
        raise ValueError('identity: '+label)


def checked_inputs(prepare, fit, lock):
    protocol = Path(__file__).resolve().parents[1]/'docs/research/S03/S03-E019/experiment.md'
    if prior.sha(protocol) != PROTOCOL_SHA: raise ValueError('confirmed protocol changed')
    for name, root in (('prepare', prepare), ('fit', fit)):
        if prior.sha(root/'execution_receipt.json') != lock[name]:
            raise ValueError('anchored '+name+' receipt mismatch')
    pr, fr = prior.completed(prepare, 'prepare', prior.PREP), prior.completed(fit, 'fit', prior.FIT)
    pb, fb = prior.bindings(prepare, prior.PREP), prior.bindings(fit, prior.FIT)
    fm = json.loads((fit/'fit.json').read_text())
    if (fr.get('input_bindings') != pb or fm.get('source_prepare') != pb or
            dict(prepare=pr['run_id'], fit=fr['run_id']) != lock['runs'] or
            fm.get('cycle') != '292018.5' or fm.get('status') != 'four_predictions_frozen_before_held_response'):
        raise ValueError('prepare-fit lineage/run/cycle/status')
    sources = [protocol, Path(__file__), Path(prior.__file__)]
    sources += [Path(prior.__file__).with_name(n) for n in prior.DEPS]
    sources += [prepare/n for n in prior.PREP+('execution_receipt.json',)]
    sources += [fit/n for n in prior.FIT+('execution_receipt.json',)]
    before = hashes(sources)
    # Other PREP/FIT NPZs are byte-hashed only; never load geometry or high predictions.
    p, fields = prior.load(prepare/'prepared.npz'), prior.load(fit/'solved_fields.npz')
    meta, audit = (json.loads((prepare/n).read_text()) for n in ('preparation.json', 'geometry_audit.json'))
    if (meta.get('cycle') != '292018.5' or meta.get('reference') != 1 or
            audit.get('cycle') != '292018.5' or audit.get('stages') != [13, 14] or
            len(audit['training_headers']) != 2 or len(meta['forces']) < 2):
        raise ValueError('training identity')
    for stage, header, force in zip((13, 14), audit['training_headers'], meta['forces'][:2]):
        if prior.identity(header, stage) != force: raise ValueError('training force identity')
    ids = p['ids']; n = len(ids)
    if (ids.ndim != 1 or not np.issubdtype(ids.dtype, np.integer) or np.any(ids <= 0) or
            len(np.unique(ids)) != n or n != lock['observations'] or meta.get('observations') != n):
        raise ValueError('fixed training IDs/count')
    for name, shape in (('xy', (n, 2)), ('train_v', (n, 2)), ('weights', (n,))):
        if p[name].shape != shape or not np.isfinite(p[name]).all(): raise ValueError('training shape/finite '+name)
    if np.any(p['weights'] <= 0): raise ValueError('positive inherited weights required')
    if np.any(np.abs(p['xy'][:, 0]) >= 16.2) or np.any(np.abs(p['xy'][:, 1]) >= 7.2):
        raise ValueError('original strict training ROI')
    mesh, tri, bd = prior.rectangular_mesh()
    for name, expected in (('mesh', mesh), ('tri', tri), ('boundary', bd)):
        if not np.array_equal(p[name], expected): raise ValueError('frozen mesh identity '+name)
    if p['boundary'].dtype != np.bool_ or p['bc'].shape != (120, 2) or not np.isfinite(p['bc']).all():
        raise ValueError('fixed boundary identity/finite')
    for k in ARMS:
        if fields[k].shape != (861, 2) or not np.isfinite(fields[k]).all():
            raise ValueError('saved model shape/finite '+k)
        close(fields[k][bd], p['bc'], 'saved boundary '+k)
        if fields[k+'_sampled'].shape != (n, 2): raise ValueError('saved sampling shape '+k)
        close(prior.sample_regular_mesh(fields[k], p['xy']), fields[k+'_sampled'], 'saved sampling '+k)
    lineage = dict(source_prepare=pb, source_fit=fb, source_runs=lock['runs'],
                   cycle='292018.5', training_stages=[13, 14], observations=n,
                   input_paths=dict(prepare=str(prepare), fit=str(fit)), protocol_sha256=PROTOCOL_SHA)
    return p, fields, lineage, before


def sampling(xy):
    """Explicit fixed-diagonal CST row stencil, node-major interleaved U,V."""
    if (xy.ndim != 2 or xy.shape[1] != 2 or not np.isfinite(xy).all() or
            np.any(np.abs(xy[:, 0]) > 18) or np.any(np.abs(xy[:, 1]) > 9)):
        raise ValueError('CST sample domain/shape')
    gx, gy = (xy[:, 0]+18)/36*40, (xy[:, 1]+9)/18*20
    i, j = np.minimum(np.floor(gx).astype(int), 39), np.minimum(np.floor(gy).astype(int), 19)
    fx, fy = gx-i, gy-j; a = j*41+i; lower = fy <= fx
    nodes = np.c_[a, np.where(lower, a+1, a+42), np.where(lower, a+42, a+41)]
    coeff = np.c_[1-np.where(lower, fx, fy), np.where(lower, fx-fy, fx), np.where(lower, fy, fy-fx)]
    columns = (2*nodes[:, None, :]+np.arange(2)[None, :, None]).ravel()
    rows = np.repeat(np.arange(2*len(xy)), 3)
    values = np.repeat(coeff[:, None, :], 2, axis=1).ravel()
    S = csr_matrix((values, (rows, columns)), shape=(2*len(xy), 1722))
    S.eliminate_zeros()
    mesh = prior.rectangular_mesh()[0]
    close(coeff.sum(axis=1), np.ones(len(xy)), 'CST constant reproduction', matrix=True)
    close(np.sum(coeff[:, :, None]*mesh[nodes], axis=1), xy, 'CST coordinate reproduction', matrix=True)
    return S, nodes, coeff


def rigid_basis(xy, w):
    if (xy.shape != (len(w), 2) or not np.isfinite(xy).all() or not np.isfinite(w).all() or
            np.any(w <= 0) or len(w) < 2): raise ValueError('global rigid support')
    centered = xy-np.sum(w[:, None]*xy, axis=0)/w.sum()
    R = np.zeros((2*len(w), 3)); R[0::2, 0] = 1.; R[1::2, 1] = 1.
    R[0::2, 2], R[1::2, 2] = -centered[:, 1], centered[:, 0]
    scale = np.repeat(np.sqrt(w/w.sum()), 2)
    B = scale[:, None]*R
    H, upper = linalg.qr(B, mode='economic', check_finite=True)
    if np.any(np.abs(np.diag(upper)) <= 1e-12*np.max(np.abs(upper))):
        raise ValueError('global rigid rank')
    close(multiply(H.T, H), np.eye(3), 'rigid QR orthogonality', matrix=True)
    close(multiply(H, upper), B, 'rigid QR reconstruction', matrix=True)
    return scale, H


def quotient(H, values):
    return values-multiply(H, multiply(H.T, values))


def classify(floor, gap, tolerance):
    return ('floor_unresolved' if floor <= tolerance else 'floor_resolved') + \
           ('_gap_unresolved' if gap <= tolerance else '_gap_resolved')


def project(A, y, models, start, clock):
    """One SVD in observation space; never form or export an arbitrary nodal z."""
    if (A.ndim != 2 or y.shape != (A.shape[0],) or set(models) != set(ARMS) or
            not np.isfinite(A).all() or not np.isfinite(y).all() or not np.any(A)):
        raise ValueError('nonzero finite capacity matrix/target')
    for k in ARMS:
        if models[k].shape != y.shape or not np.isfinite(models[k]).all(): raise ValueError('model vector '+k)
    within(start, clock)
    L, s, Vh = linalg.svd(A, full_matrices=False, check_finite=True, lapack_driver='gesvd')
    within(start, clock)
    if not np.isfinite(s).all() or s[0] <= 0: raise ValueError('nonfinite/zero SVD')
    tau = 1e-12*float(s[0])
    if np.any((s >= tau/10) & (s <= 10*tau)): raise ValueError('numerical rank unresolved near cutoff')
    close(multiply(L*s, Vh), A, 'SVD reconstruction', matrix=True)
    close(multiply(L.T, L), np.eye(len(s)), 'SVD left orthogonality', matrix=True)
    close(multiply(Vh, Vh.T), np.eye(len(s)), 'SVD right orthogonality', matrix=True)
    Lr = L[:, s > tau]
    p = multiply(Lr, multiply(Lr.T, y)); rk = p-y
    close(multiply(Lr.T, rk), np.zeros(Lr.shape[1]), 'floor orthogonality')
    jkin = float(np.sum(rk*rk)); rms = float(np.sqrt(jkin))
    residuals = {k: models[k]-y for k in ARMS}
    T = 1e-15+1e-12*max(float(np.sqrt(np.sum(y*y))), *(float(np.sqrt(np.sum(r*r))) for r in residuals.values()))
    rows, arrays, checks = [], dict(weighted_target_y=y, weighted_projection=p, weighted_r_kin=rk, singular_values=s), {}
    for k in ARMS:
        b, r, d = models[k], residuals[k], models[k]-p
        close(b, multiply(Lr, multiply(Lr.T, b)), 'saved model retained-image feasibility '+k)
        close(r, rk+d, 'residual addition '+k)
        j, extra = float(np.sum(r*r)), float(np.sum(d*d))
        cross = float(2*np.sum(rk*d))
        if abs(cross) > 1e-18+1e-12*max(j, jkin, extra): raise ValueError('square orthogonality '+k)
        close(j, jkin+extra, 'square addition '+k, square=True)
        gap = float(np.sqrt(extra))
        rows.append(dict(arm=k, J_kin_mm2=jkin, RMS_kin_mm=rms, J_model_mm2=j, RMS_model_mm=float(np.sqrt(j)),
                         extra_square_mm2=extra, gap_mm=gap, decision_T_mm=T, state=classify(rms, gap, T)))
        arrays[k+'_weighted_r'], arrays[k+'_weighted_d'] = r, d
        checks[k] = dict(cross_term_mm2=cross, square_addition_error_mm2=j-jkin-extra,
                         max_residual_addition_error_mm=float(np.max(np.abs(r-rk-d))))
    within(start, clock)
    rank = int(np.sum(s > tau))
    report = dict(status='post_hoc_training_only_kinematic_diagnostic', rows=rows, arithmetic_checks=checks,
                  observation_components=A.shape[0], nominal_free_dofs=A.shape[1], numerical_rank=rank,
                  effective_nullity=A.shape[1]-rank, cutoff=tau, svd_driver='gesvd', svd_calls=1,
                  J_kin_mm2=jkin, RMS_kin_mm=rms, decision_T_mm=T,
                  decisions='per-arm RMS_kin and gap compared with common T in mm; no winner or aggregate verdict')
    return arrays, report


def analyze(p, fields, start, clock):
    xy, w, bd = p['xy'], p['weights'], p['boundary']
    S, nodes, coeff = sampling(xy)
    fixed, free = np.flatnonzero(np.repeat(bd, 2)), np.flatnonzero(~np.repeat(bd, 2))
    if S[:, fixed].nnz != 0: raise ValueError('nonzero boundary sampling: original ROI identity')
    scale, H = rigid_basis(xy, w)
    u0 = np.zeros((861, 2)); u0[bd] = p['bc']
    sampled0 = S@u0.ravel()
    close(sampled0, np.zeros(len(sampled0)), 'zero direct boundary observation offset')
    SF = S[:, free]
    active = np.flatnonzero(np.asarray(SF.getnnz(axis=0)).ravel() > 0)
    A = quotient(H, scale[:, None]*SF.toarray())
    y = quotient(H, scale*(p['train_v'].ravel()-sampled0))
    models = {}
    for k in ARMS:
        sampled = S@fields[k].ravel()
        close(sampled.reshape(-1, 2), fields[k+'_sampled'], 'explicit CST/saved sampling '+k)
        models[k] = quotient(H, scale*(sampled-sampled0))
    within(start, clock)
    arrays, report = project(A, y, models, start, clock)
    arrays.update(ids=p['ids'], xy=xy, weights=w, component_scale=scale,
                  stencil_node_indices=nodes, stencil_coefficients=coeff, free_dofs=free,
                  active_sampling_free_columns=active, weighted_rigid_basis=H)
    arrays['e_kin'] = (arrays['weighted_r_kin']/scale).reshape(-1, 2)
    for k in ARMS:
        arrays[k+'_e'] = (arrays[k+'_weighted_r']/scale).reshape(-1, 2)
        arrays[k+'_deviation'] = (arrays[k+'_weighted_d']/scale).reshape(-1, 2)
    report.update(observations=len(xy), active_sampling_columns=len(active), zero_sampling_columns=len(free)-len(active),
                  boundary_sampling_nonzeros=0, fixed_boundary_nodes=int(bd.sum()),
                  BC_scope='S_B=0 only rules out direct boundary sampling; equilibrium-mediated influence remains unseparated',
                  output_scope='unique observation projection only; no oracle nodal field or out-of-support profile')
    return arrays, report


def save_figure(fig, out, name):
    try:
        fig.savefig(out/(name+'.png'), dpi=170)
        fig.savefig(out/(name+'.pdf'))
    finally:
        plt.close(fig)


def draw(data, report, out, title):
    columns = [('kinematic floor', data['e_kin'])]+[(k, data[k+'_e']) for k in ARMS]
    bound = max(float(np.abs(a).max()) for _, a in columns) or 1e-15
    fig, axes = plt.subplots(2, 4, figsize=(13, 6), sharex=True, sharey=True, constrained_layout=True)
    try:
        for j, (label, residual) in enumerate(columns):
            for i, component in enumerate(('U', 'V')):
                ax = axes[i, j]
                points = ax.scatter(data['xy'][:, 0], data['xy'][:, 1], c=residual[:, i], s=13,
                                    cmap='RdBu_r', vmin=-bound, vmax=bound)
                ax.set(xlim=(-18, 18), ylim=(-9, 9), aspect='equal', xlabel='stage13 x [mm]', ylabel='y [mm]',
                       title=label+' | '+component)
        fig.colorbar(points, ax=axes, label='global-rigid-complement residual [mm]', shrink=.75)
        fig.suptitle(title+'\nAll training points; original XY/weights; shared symmetric scale', fontsize=9)
        save_figure(fig, out, 'kinematic_residuals')
    finally:
        plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 4.8), constrained_layout=True)
    try:
        rows = report['rows']; floor = [r['J_kin_mm2'] for r in rows]; extra = [r['extra_square_mm2'] for r in rows]
        x = np.arange(3)
        ax.bar(x, floor, color='#0072B2', label='kinematic floor J_kin')
        ax.bar(x, extra, bottom=floor, color='#E69F00', label='saved-field gap squared')
        ax.plot(x, [r['J_model_mm2'] for r in rows], 'ko', ms=4, label='saved-field total J_k')
        for i, r in enumerate(rows):
            ax.annotate('floor %.3g; gap² %.3g' % (r['J_kin_mm2'], r['extra_square_mm2']),
                        (i, r['J_model_mm2']), xytext=(0, 7), textcoords='offset points', ha='center', fontsize=8)
        top = max(r['J_model_mm2'] for r in rows)
        ax.set_ylim(0, 1.3*top if top else 1e-30)
        ax.set_xticks(x, ARMS); ax.set_ylabel('area-weighted squared residual [mm²]')
        ax.set_title(title+'\nSquares add; RMS does not add; no causal percentages', fontsize=9)
        ax.legend(loc='upper center', bbox_to_anchor=(.5, -.09), ncol=3, frameon=False, fontsize=8)
        save_figure(fig, out, 'kinematic_square_ledger')
    finally:
        plt.close(fig)


def explain(out, lineage, report):
    guide = ('## Figure question\n\nCan the fixed grid/BC observation space represent the training data, and how far '
             'are the saved equilibrium fields from its best observation projection?\n\n'
             '## How to read / panels\n\nkinematic_residuals: U/V rows; kinematic floor, old, proxy, intact columns. '
             'All original training XY points, x/y in mm, red/blue signed D^-1 residual in mm with one symmetric scale. '
             'No smoothing/interpolation, support selection or hidden clipping. kinematic_square_ledger: all three arms; '
             'blue floor plus orange nonnegative extra square, black dot total, y mm². Squares add, RMS does not. '
             'Exactly zero maps use display-only +/-1e-15mm; exactly zero ledger uses display-only 0..1e-30mm².\n\n'
             '## Limitations and claim boundary\n\nPost-hoc C1 training diagnostic, one specimen/cycle292018.5/stages13/14; '
             'not prediction or physical phase-field/material recovery. Common full training rigid subspace and inherited '
             'area weights; no consumed-stage15 missingness. S_B=0 concerns only direct boundary sampling, not BC influence '
             'through equilibrium. BC itself came from training DIC, not independent truth. Nominal DOFs/near-zero training '
             'floor do not establish physical realisability; no amplitude/strain/equilibrium regularity constraints. '
             'Observation projection is unique but nodal field is not, so no oracle nodes/profile or held predictions '
             'are generated. Rank cutoff is numerical, T in mm is arithmetic not noise precision. Each arm has its own '
             'four-state label; no any/all winner or causal allocation. New weighted648point RMS/squares do not replace '
             'old646point MAE or37pair profile norms. No unique noise/BC/material/3D cause.\n\n'
             '## Data provenance\n\n'+json.dumps(lineage, ensure_ascii=False)+'\n\n'
             '## Key numerical takeaway\n\n'+json.dumps(report, ensure_ascii=False, allow_nan=False)+'\n\n'
             '## Related assets\n\nsummary.csv; report.json; pointwise.npz; execution_receipt.json; same-stem PNG/PDF.\n')
    (out/'README_analysis.md').write_text(guide)
    for name in ('kinematic_residuals', 'kinematic_square_ledger'):
        (out/(name+'.md')).write_text('# '+name+'\n\n'+guide)
    images = [p for p in out.iterdir() if p.suffix in ('.png', '.pdf')]
    if len(images) != 4: raise ValueError('two PNG/PDF figures required')
    for image in images:
        note = image.with_suffix('.md').read_text().lower()
        if len(note) < 400 or any(s not in note for s in ('how to read', 'data provenance', 'limitation')):
            raise ValueError('figure sidecar incomplete')


def run(prepare, fit, out, source_commit, run_id, *, lock=None, clock=time.monotonic):
    start = clock()
    if out.exists(): raise ValueError('fresh output required; no retry')
    if any(out.resolve().is_relative_to(r.resolve()) or r.resolve().is_relative_to(out.resolve()) for r in (prepare, fit)):
        raise ValueError('output/source overlap')
    out.mkdir(parents=True, exist_ok=False)
    receipt = dict(run_id=run_id, source_commit_declared=source_commit, protocol_sha256=PROTOCOL_SHA,
                   start_utc=datetime.now(timezone.utc).isoformat(), hostname=socket.gethostname(), pid=os.getpid(),
                   command=sys.argv, budget_seconds=60., execution_status='running',
                   thread_environment={k: os.environ.get(k) for k in THREADS})
    try:
        with warnings.catch_warnings(), np.errstate(all='warn'):
            warnings.simplefilter('error')
            receipt.update(runner_sha256=prior.sha(__file__), numpy_version=np.__version__, scipy_version=scipy.__version__,
                           python_version=sys.version, matplotlib_version=matplotlib.__version__)
            within(start, clock)
            prepared, fields, lineage, before = checked_inputs(prepare, fit, DEFAULT_LOCK if lock is None else lock)
            receipt.update(lineage=lineage, sources_before_sha256=before)
            within(start, clock)
            data, report = analyze(prepared, fields, start, clock)
            within(start, clock)
            with (out/'pointwise.npz').open('wb') as handle: np.savez_compressed(handle, **data)
            prior.write_json(out/'report.json', report)
            with (out/'summary.csv').open('w', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=list(report['rows'][0]))
                writer.writeheader(); writer.writerows(report['rows'])
            within(start, clock)
            title = 'E019 | controlled experiment | cycle292018.5 | training13/14 | '+run_id
            draw(data, report, out, title); explain(out, lineage, report)
            within(start, clock)
            after = hashes([Path(p) for p in before])
            if before != after: raise ValueError('source changed during analysis')
            receipt.update(sources_after_sha256=after,
                           artifacts_sha256={p.name: prior.sha(p) for p in out.iterdir() if p.is_file() and p.name != 'execution_receipt.json'})
            within(start, clock)
            receipt.update(execution_status='succeeded', elapsed_seconds=clock()-start,
                           end_utc=datetime.now(timezone.utc).isoformat())
            prior.write_json(out/'execution_receipt.json', receipt)
            within(start, clock)
    except Exception as exc:
        receipt.update(execution_status='failed', error=str(exc), outputs_role='forensic_only',
                       elapsed_seconds=clock()-start, end_utc=datetime.now(timezone.utc).isoformat())
        prior.write_json(out/'execution_receipt.json', receipt)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prepare', 'fit', 'output'): parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--source-commit', required=True); parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    for key in THREADS:
        if os.environ.get(key) != '1': raise ValueError('single-thread environment required: '+key)
    if os.environ.get('PYTHONWARNINGS') != 'error': raise ValueError('PYTHONWARNINGS=error required')
    run(args.prepare, args.fit, args.output, args.source_commit, args.run_id)


if __name__ == '__main__': main()
