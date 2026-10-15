#!/usr/bin/env python3
"""E018 saved-training profile arithmetic only; no raw data, held response or solve entry."""
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
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import aa2024_geometry_prior as prior
import aa2024_frozen_error_decomposition as helpers

ARMS = ('old', 'proxy', 'intact')
X = .9 * np.arange(-18, 19)
SELECT = np.r_[np.arange(8, 45), np.arange(61, 98)]
PROTOCOL_SHA = '42fe3505d5616f82879dda113af1f211b45ba76cd85442eb94d8745f7f59ab27'
DEFAULT_LOCK = dict(prepare='8655d49b30e341d488eeb8c15db9a7d347f236634a22adbbf39fcb7b4bbd3ccf',
                    fit='3173f0f659d6e451f7fccc39a4ca0973ae3caad750c9d98ce754a1bcec325674',
                    runs=dict(prepare='S03-E016-R001', fit='S03-E016-R002'),
                    observations=648, source_facets=39970)
HELPER_SHA = '2ff3e35365dc74a030ac5b19faee7a95ece0df6d140c75cf6445c0549d8ca137'


def close(a, b, label, *, moment=False):
    atol = 1e-12 if moment else 1e-15
    if (np.shape(a) != np.shape(b) or not np.isfinite(a).all() or not np.isfinite(b).all() or
            not np.allclose(a, b, rtol=1e-12, atol=atol)):
        raise ValueError('identity: ' + label)


def unique_ids(ids, label):
    if ids.ndim != 1 or not np.issubdtype(ids.dtype, np.integer) or len(np.unique(ids)) != len(ids):
        raise ValueError('integer unique IDs: ' + label)


def in_domain(xy):
    if (not np.isfinite(xy).all() or xy.shape[-1] != 2 or
            np.any(np.abs(xy[..., 0]) > 18) or np.any(np.abs(xy[..., 1]) > 9)):
        raise ValueError('CST sampling outside frozen domain')


def theta(xy, u, w):
    """Same weighted global planar rigid subspace, no matrix multiplication."""
    if (xy.shape != u.shape or xy.shape != (len(w), 2) or not np.isfinite(xy).all() or
            not np.isfinite(u).all() or not np.isfinite(w).all() or np.any(w <= 0)):
        raise ValueError('global training rigid support')
    centered = xy - np.sum(w[:, None] * xy, axis=0) / w.sum()
    rotation = np.c_[-centered[:, 1], centered[:, 0]]
    shift = np.sum(w[:, None] * u, axis=0) / w.sum()
    denom = np.sum(w * np.sum(rotation * rotation, axis=1))
    if not np.isfinite(denom) or denom <= 0:
        raise ValueError('global training rigid rank')
    value = float(np.sum(w * np.sum(rotation * (u - shift), axis=1)) / denom)
    if not np.isfinite(value): raise ValueError('nonfinite global training theta')
    return value


def pair(values, angle):
    if values.shape != (74, 2) or not np.isfinite(values).all() or not np.isfinite(angle):
        raise ValueError('paired profile shape/finite')
    jump = values[:37] - values[37:]
    jump[:, 0] += 7.2 * angle
    return jump  # columns: global-rigid-complement tangential, raw normal


def checked_inputs(prepare, fit, lock):
    protocol = Path(__file__).resolve().parents[1] / 'docs/research/S03/S03-E018/experiment.md'
    if prior.sha(protocol) != PROTOCOL_SHA or prior.sha(helpers.__file__) != HELPER_SHA:
        raise ValueError('confirmed protocol/helper changed')
    for key, root in (('prepare', prepare), ('fit', fit)):
        if prior.sha(root / 'execution_receipt.json') != lock[key]:
            raise ValueError('anchored ' + key + ' receipt mismatch')
    pr = prior.completed(prepare, 'prepare', prior.PREP)
    fr = prior.completed(fit, 'fit', prior.FIT)
    pb, fb = prior.bindings(prepare, prior.PREP), prior.bindings(fit, prior.FIT)
    fm = json.loads((fit / 'fit.json').read_text())
    if fr.get('input_bindings') != pb or fm.get('source_prepare') != pb:
        raise ValueError('prepare-fit lineage')
    if (dict(prepare=pr['run_id'], fit=fr['run_id']) != lock['runs'] or
            fm.get('cycle') != '292018.5' or fm.get('status') != 'four_predictions_frozen_before_held_response'):
        raise ValueError('run/cycle/fit status')
    paths = [protocol, Path(__file__), Path(helpers.__file__), Path(prior.__file__),
             Path(helpers.view.__file__)] + [Path(prior.__file__).with_name(n) for n in prior.DEPS]
    paths += [prepare / n for n in prior.PREP + ('execution_receipt.json',)]
    paths += [fit / n for n in prior.FIT + ('execution_receipt.json',)]
    before = helpers.hashes(paths)
    p = prior.load(prepare / 'prepared.npz')
    g = prior.load(prepare / 'training_geometry.npz')
    solved = prior.load(fit / 'solved_fields.npz')
    # Frozen high-load predictions are hash-bound only; never load their NPZ.
    audit = json.loads((prepare / 'geometry_audit.json').read_text())
    meta = json.loads((prepare / 'preparation.json').read_text())
    if (meta.get('cycle') != '292018.5' or meta.get('reference') != 1 or
            audit.get('cycle') != '292018.5' or audit.get('stages') != [13, 14]):
        raise ValueError('training identity')
    if len(audit['training_headers']) != 2 or len(meta['forces']) < 2:
        raise ValueError('two training headers/forces required')
    for stage, header, force in zip((13, 14), audit['training_headers'], meta['forces'][:2]):
        if prior.identity(header, stage) != force: raise ValueError('training force identity')
    unique_ids(p['ids'], 'observations'); unique_ids(g['ids'], 'source facets')
    n, ng = len(p['ids']), len(g['ids'])
    if n != lock['observations'] or ng != lock['source_facets']:
        raise ValueError('fixed training counts')
    for name, shape in (('xy', (ng, 2)), ('xyz', (ng, 3)), ('du', (ng, 3))):
        if g[name].shape != shape or not np.isfinite(g[name]).all(): raise ValueError('source shape/finite ' + name)
    if not np.array_equal(g['xy'], g['xyz'][:, :2]): raise ValueError('source stage13 XY')
    lookup = {int(v): i for i, v in enumerate(g['ids'])}
    if any(int(v) not in lookup for v in p['ids']): raise ValueError('training observation ID absent')
    obs = np.array([lookup[int(v)] for v in p['ids']])
    if (not np.array_equal(p['xy'], g['xy'][obs]) or not np.array_equal(p['train_v'], g['du'][obs, :2]) or
            p['weights'].shape != (n,) or not np.isfinite(p['weights']).all() or np.any(p['weights'] <= 0)):
        raise ValueError('saved training observation identity/weights')
    mesh, tri, bd = prior.rectangular_mesh()
    for name, expected in (('mesh', mesh), ('tri', tri), ('boundary', bd)):
        if not np.array_equal(p[name], expected): raise ValueError('frozen mesh identity ' + name)
    in_domain(p['xy'])
    profile = audit['profiles']['3.6']
    if (profile['gauge_mm'] != 3.6 or len(profile['interpolation']) != 106 or
            not np.array_equal(np.asarray(profile['x_mm']), prior.X) or len(profile['opening_mm']) != 53):
        raise ValueError('primary profile indexing')
    query = np.c_[np.tile(X, 2), np.repeat([3.6, -3.6], 37)]
    neighbors, coefficients = [], []
    for q, source_index in zip(query, SELECT):
        note = profile['interpolation'][int(source_index)]
        ids, a = np.asarray(note['neighbor_ids']), np.asarray(note['coefficients'])
        unique_ids(ids, 'four-neighbour query')
        if (ids.shape != (4,) or a.shape != (4,) or not np.isfinite(a).all() or
                note['rank'] != 3 or note['supported'] is not True or
                not np.isfinite(note['fourth_distance_mm']) or note['fourth_distance_mm'] > 2):
            raise ValueError('saved query support/rank/coefficients')
        close(np.asarray(note['query_xy_mm']), q, 'query order', moment=True)
        if any(int(v) not in lookup for v in ids): raise ValueError('saved neighbour ID absent')
        idx = np.array([lookup[int(v)] for v in ids])
        coords = g['xy'][idx]
        if not np.all(coords[:, 1] > 0 if q[1] > 0 else coords[:, 1] < 0):
            raise ValueError('saved neighbour side')
        close(np.sum(a), 1., 'affine constant moment', moment=True)
        close(np.sum(a[:, None] * coords, axis=0), q, 'affine coordinate moment', moment=True)
        close(float(np.sqrt(np.sum((coords - q)**2, axis=1)).max()), note['fourth_distance_mm'],
              'saved fourth distance', moment=True)
        in_domain(coords)
        neighbors.append(idx); coefficients.append(a)
    in_domain(query)
    neighbors, coefficients = np.asarray(neighbors), np.asarray(coefficients)
    source_uv = g['du'][neighbors, :2]
    dic = np.sum(coefficients[:, :, None] * source_uv, axis=1)
    dic_angle = theta(p['xy'], p['train_v'], p['weights'])
    dic_pair = pair(dic, dic_angle)
    raw_opening = np.asarray(profile['opening_mm'])[np.arange(8, 45)]
    close(dic_pair[:, 1], raw_opening, 'original raw primary opening')
    for k in ARMS:
        if solved[k].shape != (861, 2) or not np.isfinite(solved[k]).all():
            raise ValueError('full saved model field ' + k)
        if solved[k + '_sampled'].shape != (n, 2): raise ValueError('saved sample shape ' + k)
        sampled = prior.sample_regular_mesh(solved[k], p['xy'])
        close(sampled, solved[k + '_sampled'], 'original saved observation sampling ' + k)
    lineage = dict(source_prepare=pb, source_fit=fb, source_runs=lock['runs'],
                   input_paths=dict(prepare=str(prepare), fit=str(fit)),
                   cycle='292018.5', training_stages=[13, 14], projection_observations=n,
                   source_facets=ng, pair_count=37, gauge_mm=3.6,
                   query_integer_indices=list(range(-18, 19)),
                   protocol_sha256=PROTOCOL_SHA)
    context = dict(prepared=p, solved=solved, query=query, coefficients=coefficients,
                   neighbor_xy=g['xy'][neighbors], neighbor_ids=g['ids'][neighbors],
                   neighbor_du=source_uv, dic=dic, dic_pair=dic_pair, dic_angle=dic_angle)
    return context, lineage, before


def profiles(context):
    p, solved = context['prepared'], context['solved']
    q, a, xy = context['query'], context['coefficients'], context['neighbor_xy']
    data = dict(x_mm=X, query_xy=q, query_original_indices=SELECT,
                neighbor_ids=context['neighbor_ids'], coefficients=a, neighbor_xy=xy,
                neighbor_du=context['neighbor_du'], dic=context['dic'], J_dic=context['dic_pair'],
                theta_dic=np.array(context['dic_angle']))
    rows, detail, checks = [], [], {}
    for k in ARMS:
        direct = prior.sample_regular_mesh(solved[k], q)
        at_neighbors = prior.sample_regular_mesh(solved[k], xy.reshape(-1, 2)).reshape(74, 4, 2)
        matched = np.sum(a[:, :, None] * at_neighbors, axis=1)
        angle = theta(p['xy'], solved[k + '_sampled'], p['weights'])
        jd, jm = pair(direct, angle), pair(matched, angle)
        rd, ro, rm = jd - context['dic_pair'], jd - jm, jm - context['dic_pair']
        close(rd, ro + rm, 'paired residual addition ' + k)
        ld, lm, lo = (float(np.mean(helpers.norm(v))) for v in (rd, rm, ro))
        difference = float(np.mean(helpers.norm(rd) - helpers.norm(rm)))
        close(difference, ld - lm, 'profile norm difference ' + k)
        row = dict(arm=k, pair_count=37, theta_model=angle, theta_dic=context['dic_angle'],
                   L_direct_mm=ld, L_match_mm=lm, L_op_mm=lo, A_mm=difference,
                   A_sign=helpers.sign(difference, max(ld, lm)))
        for name, value in (('direct', rd), ('op', ro), ('match', rm)):
            row[name + '_mean_abs_tangential_mm'] = float(np.mean(np.abs(value[:, 0])))
            row[name + '_mean_abs_normal_mm'] = float(np.mean(np.abs(value[:, 1])))
        rows.append(row)
        checks[k] = dict(max_addition_error_mm=float(np.max(np.abs(rd - ro - rm))))
        for name, value in (('direct', direct), ('match', matched), ('neighbor_values', at_neighbors),
                            ('J_direct', jd), ('J_match', jm), ('r_direct', rd), ('r_op', ro), ('r_match', rm)):
            if not np.isfinite(value).all(): raise ValueError('nonfinite derived ' + k + '/' + name)
            data[k + '_' + name] = value
        data[k + '_theta'] = np.array(angle)
        for i, x in enumerate(X):
            item = dict(arm=k, x_mm=float(x))
            for name, value in (('DIC', context['dic_pair']), ('direct', jd), ('match', jm),
                                ('r_direct', rd), ('r_op', ro), ('r_match', rm)):
                item[name + '_tangential_mm'], item[name + '_normal_mm'] = map(float, value[i])
            detail.append(item)
    return data, rows, detail, checks


def draw(data, out, title):
    for residual, name in ((False, 'training_profiles'), (True, 'profile_discrepancies')):
        fig, axes = plt.subplots(2, 3, figsize=(13.5, 7), sharex=True, sharey='row' if not residual else True,
                                 constrained_layout=True)
        bound = max(float(np.abs(data[k + '_' + r]).max()) for k in ARMS for r in ('r_direct', 'r_op', 'r_match'))
        for col, k in enumerate(ARMS):
            for row, channel in enumerate(('normal', 'tangential')):
                ax, component = axes[row, col], 1 - row
                if residual:
                    curves = [('direct-DIC', data[k + '_r_direct'], '#222222', '-'),
                              ('direct-match', data[k + '_r_op'], '#D55E00', '--'),
                              ('match-DIC', data[k + '_r_match'], '#0072B2', ':')]
                    limit = 1.08 * bound if bound else 1e-15
                    ax.set_ylim(-limit, limit); ax.axhline(0, color='.65', lw=.6)
                else:
                    curves = [('DIC', data['J_dic'], '#222222', '-'),
                              ('FEM direct', data[k + '_J_direct'], '#0072B2', '--'),
                              ('FEM matched', data[k + '_J_match'], '#D55E00', ':')]
                for label, values, color, style in curves:
                    ax.plot(X, values[:, component], color=color, ls=style, lw=1.4, label=label)
                ax.set_title(k + ' | ' + channel, fontsize=10)
                ax.set_xlabel('stage13 reference x [mm]'); ax.set_ylabel(channel + ' relative increment [mm]')
                ax.set_xlim(X[0], X[-1])
        handles, labels = axes[0, 0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='outside lower center', ncol=3, frameon=False)
        fig.suptitle(title + '\n37 fixed pairs | raw normal | tangential +2b theta from all training points', fontsize=9)
        helpers.save_figure(fig, out, name)


def explain(out, lineage, report):
    guide = ('## Figure question\n\n'
             'Does the sampling interface change the saved training-profile comparison, and what mismatch remains under matched sampling?\n\n'
             '## How to read / panels and visual grammar\n\n'
             'Both figures: columns old/proxy/intact, rows normal (V upper-minus-lower) and tangential '
             '(U upper-minus-lower plus2b theta), x stage13 reference x[mm], y relative increment[mm]. '
             'training_profiles: DIC black, direct FEM blue dashed, DIC-weight-matched FEM orange dotted. '
             'Same component shares y scale across all three arms. profile_discrepancies: direct-DIC black, '
             'direct-match orange dashed, match-DIC blue dotted, all six panels share one symmetric signed scale and zero line. '
             'No selected examples, smoothing, clipping, background subtraction or new endpoints. '
             'An exactly zero residual field uses display-only +/-1e-15mm.\n\n'
             '## Limitations and claim boundary\n\n'
             'Post-hoc training diagnostic, one specimen/cycle292018.5, no held response or future-cycle validation. '
             '37 equally weighted pairs are not independent repeats or the E016/E017 area-weighted score. '
             'Proxy geometry used the training opening, so this is not independent geometry validation. '
             'Direct/matched sampling is an interface contrast, not a parameter or model repair. '
             'The same model theta is shared by its two interfaces; all theta values use the same full training support, '
             'not high-load missingness or per-side/profile fitting. Theta is a nuisance projection coefficient, '
             'not physical rotation truth; tangential is not independently measured crack slip. '
             'No unique noise/material/3D/BC/export-compensation cause or E017 original-MAE attribution. '
             'Norms do not add; A is only this profile norm difference, never a causal percentage.\n\n'
             '## Data provenance\n\n' + json.dumps(lineage, ensure_ascii=False) + '\n\n'
             '## Key numerical takeaway\n\n' + json.dumps(report, ensure_ascii=False, allow_nan=False) + '\n\n'
             '## Related assets\n\nprofiles.npz; profiles.csv; summary.csv; report.json; execution_receipt.json; same-stem PNG/PDF.\n')
    (out / 'README_analysis.md').write_text(guide)
    for name in ('training_profiles', 'profile_discrepancies'):
        (out / (name + '.md')).write_text('# ' + name + '\n\n' + guide)
    images = [p for p in out.iterdir() if p.suffix in ('.png', '.pdf')]
    if len(images) != 4: raise ValueError('two PNG/PDF figures required')
    for image in images:
        note = image.with_suffix('.md').read_text().lower()
        if len(note) < 400 or any(x not in note for x in ('how to read', 'data provenance', 'limitation')):
            raise ValueError('figure sidecar incomplete')


def run(prepare, fit, out, source_commit, run_id, *, lock=None, clock=time.monotonic):
    start = clock()
    if out.exists(): raise ValueError('fresh output required; no retry')
    if any(out.resolve().is_relative_to(r.resolve()) or r.resolve().is_relative_to(out.resolve()) for r in (prepare, fit)):
        raise ValueError('output/source overlap')
    out.mkdir(parents=True, exist_ok=False)
    receipt = dict(run_id=run_id, source_commit_declared=source_commit, protocol_sha256=PROTOCOL_SHA,
                   hostname=socket.gethostname(), pid=os.getpid(), command=sys.argv,
                   start_utc=datetime.now(timezone.utc).isoformat(), budget_seconds=60., execution_status='running',
                   thread_environment={k: os.environ.get(k) for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                                                                    'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS')})
    try:
        with warnings.catch_warnings(), np.errstate(all='warn'):
            warnings.simplefilter('error')
            receipt.update(runner_sha256=prior.sha(__file__), numpy_version=np.__version__,
                           python_version=sys.version, matplotlib_version=matplotlib.__version__)
            helpers.within(start, clock)
            context, lineage, before = checked_inputs(prepare, fit, DEFAULT_LOCK if lock is None else lock)
            receipt.update(lineage=lineage, sources_before_sha256=before)
            helpers.within(start, clock)
            data, rows, detail, checks = profiles(context)
            helpers.within(start, clock)
            report = dict(status='post_hoc_training_only_profile_diagnostic', channel_order=['tangential', 'normal'],
                          rows=rows, arithmetic_checks=checks)
            np.savez_compressed(out / 'profiles.npz', **data)
            prior.write_json(out / 'report.json', report)
            for name, records in (('summary.csv', rows), ('profiles.csv', detail)):
                with (out / name).open('w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=list(records[0])); writer.writeheader(); writer.writerows(records)
            helpers.within(start, clock)
            title = 'E018 | post-hoc controlled experiment | cycle292018.5 | train13/14 only | ' + run_id
            draw(data, out, title); explain(out, lineage, report)
            helpers.within(start, clock)
            after = helpers.hashes([Path(n) for n in before])
            if after != before: raise ValueError('source changed during analysis')
            receipt['sources_after_sha256'] = after
            receipt['artifacts_sha256'] = {p.name: prior.sha(p) for p in out.iterdir() if p.is_file() and p.name != 'execution_receipt.json'}
            helpers.within(start, clock)
            receipt.update(execution_status='succeeded', elapsed_seconds=clock() - start,
                           end_utc=datetime.now(timezone.utc).isoformat())
            prior.write_json(out / 'execution_receipt.json', receipt)
            helpers.within(start, clock)
    except Exception as e:
        receipt.update(execution_status='failed', error=str(e), outputs_role='forensic_only',
                       elapsed_seconds=clock() - start, end_utc=datetime.now(timezone.utc).isoformat())
        prior.write_json(out / 'execution_receipt.json', receipt)
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('prepare', 'fit', 'output'): p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--source-commit', required=True); p.add_argument('--run-id', required=True)
    a = p.parse_args()
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        if os.environ.get(key) != '1': raise ValueError('single-thread environment required: ' + key)
    if os.environ.get('PYTHONWARNINGS') != 'error': raise ValueError('PYTHONWARNINGS=error required')
    run(a.prepare, a.fit, a.output, a.source_commit, a.run_id)


if __name__ == '__main__': main()
