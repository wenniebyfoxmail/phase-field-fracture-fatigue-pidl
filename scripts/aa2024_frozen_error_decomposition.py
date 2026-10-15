#!/usr/bin/env python3
"""E017 post-hoc frozen-field arithmetic only; no raw parser, fit or solve entry."""
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
import aa2024_geometry_result_view as view

ARMS = ('old', 'proxy', 'intact')
BUDGET = 60.0
RTOL, ATOL, SQUARE_ATOL = 1e-12, 1e-15, 1e-18
PROTOCOL_SHA256 = 'c2dbcc77e283d9b11f912a99407cef618578790999f7b8de9dd25c1ccbc2da02'
DEFAULT_LOCK = dict(
    prepare='8655d49b30e341d488eeb8c15db9a7d347f236634a22adbbf39fcb7b4bbd3ccf',
    fit='3173f0f659d6e451f7fccc39a4ca0973ae3caad750c9d98ce754a1bcec325674',
    validation='a243775f639c41fa3fd2843b1f0efd8ffb42e346836dba5a62616b64bb29a296',
    evidence='72f64d82b06237f0b160d791562813a9df243659925806a965e54674ebe4bdcf',
    source_runs=dict(prepare='S03-E016-R001', fit='S03-E016-R002', validation='S03-E016-R003'),
    eligible=646,
    target='7148b8544294eff0aea25ff1e903a7acd66c5a68bdc3a2d7139b4e4f75096b16',
    prior_view='484d6130f2a672fd8bb1a62fc32a38a2ab82830e0066b90da5f17912b72d5a96')
EVIDENCE_NAMES = tuple(n + ext for n in ('held_scores', 'held_residuals', 'held_increment_fields')
                       for ext in ('.png', '.pdf', '.md')) + (
                           'README_analysis.md', 'scores.csv', 'arithmetic_crosscheck.json')


def require_close(actual, expected, label, *, square=False):
    if (not np.isfinite(actual).all() or not np.isfinite(expected).all() or
            not np.allclose(actual, expected, rtol=RTOL, atol=SQUARE_ATOL if square else ATOL)):
        raise ValueError('arithmetic identity: ' + label)


def norm(a):
    return np.sqrt(np.sum(a * a, axis=1))


def sign(value, scale, *, square=False):
    tolerance = (SQUARE_ATOL if square else ATOL) + RTOL * abs(scale)
    return 'numerically_unresolved' if abs(value) <= tolerance else ('positive' if value > 0 else 'negative')


def within(start, clock):
    if clock() - start >= BUDGET:
        raise TimeoutError('soft60s whole-analysis budget; forensic outputs only; no retry')


def hashes(paths):
    return {str(p): prior.sha(p) for p in paths}


def checked_inputs(prepare, fit, validation, lock):
    roots = dict(prepare=prepare, fit=fit, validation=validation,
                 evidence=validation.parent / 'figures')
    protocol = Path(__file__).resolve().parents[1] / 'docs/research/S03/S03-E017/experiment.md'
    if prior.sha(protocol) != PROTOCOL_SHA256:
        raise ValueError('confirmed protocol changed')
    paths = [protocol]
    for key, names in (('prepare', prior.PREP), ('fit', prior.FIT),
                       ('validation', view.VALIDATION)):
        receipt = roots[key] / 'execution_receipt.json'
        if prior.sha(receipt) != lock[key]:
            raise ValueError('anchored ' + key + ' receipt mismatch')
        paths.extend([receipt] + [roots[key] / n for n in names])
    evidence = roots['evidence'] / 'render_receipt.json'
    if prior.sha(evidence) != lock['evidence'] or prior.sha(view.__file__) != lock['prior_view']:
        raise ValueError('anchored evidence/checked-reader mismatch')
    er = json.loads(evidence.read_text())
    if set(er['artifacts_sha256']) != set(EVIDENCE_NAMES):
        raise ValueError('evidence artifact whitelist')
    for name in EVIDENCE_NAMES:
        p = roots['evidence'] / name
        if prior.sha(p) != er['artifacts_sha256'][name]:
            raise ValueError('evidence artifact mismatch: ' + name)
        paths.append(p)
    paths.append(evidence)
    paths += [Path(__file__), Path(view.__file__), Path(prior.__file__)]
    paths += [Path(prior.__file__).with_name(n) for n in prior.DEPS]
    before = hashes(paths)
    a, metrics, lineage, _ = view.checked_data(prepare, fit, validation)
    if (lineage['run_ids'] != lock['source_runs'] or len(a['ids']) != lock['eligible'] or
            lineage['target_member_sha256'] != lock['target']):
        raise ValueError('anchored run/support/target mismatch')
    for name in ('source_prepare', 'source_fit', 'source_validation'):
        if er[name] != lineage[name]:
            raise ValueError('evidence lineage mismatch: ' + name)
    if er['plotter_sha256'] != lock['prior_view']:
        raise ValueError('evidence plotter mismatch')
    p = prior.load(prepare / 'prepared.npz')
    f = prior.load(fit / 'frozen_predictions.npz')
    solved = prior.load(fit / 'solved_fields.npz')
    for name in ('ids', 'xy', 'weights', 'u13', 'alpha'):
        if not np.array_equal(p[name], f[name]):
            raise ValueError('training/frozen identity: ' + name)
    if (not np.issubdtype(p['ids'].dtype, np.integer) or p['ids'].ndim != 1 or
            len(set(p['ids'])) != len(p['ids'])):
        raise ValueError('training ID identity')
    if p['train_v'].shape != (len(p['ids']), 2) or not np.isfinite(p['train_v']).all():
        raise ValueError('training increment shape/finite')
    lookup = {int(v): i for i, v in enumerate(p['ids'])}
    idx = np.array([lookup[int(v)] for v in a['ids']])
    require_close(f['secant'], p['alpha'] * p['train_v'], 'frozen secant construction')
    for k in ARMS:
        sampled = solved[k + '_sampled']
        if sampled.shape != p['train_v'].shape or not np.isfinite(sampled).all():
            raise ValueError('sampled shape/finite: ' + k)
        require_close(f[k], p['alpha'] * sampled, 'frozen mechanical construction ' + k)
    lineage['accepted_evidence_receipt_sha256'] = lock['evidence']
    lineage['input_paths'] = {k: str(v) for k, v in roots.items()}
    return a, metrics, p, solved, idx, lineage, before


def decompose(a, metrics, prepared, solved, idx):
    """Use one full common-support projection, then aggregate without reprojecting."""
    xy, w = a['xy'], a['weights']
    total = float(w.sum())
    es = view.closed_form_residual(xy, a['secant'] - a['target'], w)
    require_close(es, a['secant_residual'], 'secant stored residual')
    ls = float(np.sum(w * norm(es)) / total)
    require_close(ls, metrics['MAE_mm']['secant'], 'secant MAE')
    band = np.abs(xy[:, 1]) <= 3.6
    masks = dict(all=np.ones(len(w), dtype=bool), B=band, O=~band)
    point = dict(ids=a['ids'], xy=xy, weights=w, e_s=es, region_B=band)
    rows, checks = [], {}
    for k in ARMS:
        c = view.closed_form_residual(xy, a[k] - a['secant'], w)
        training_c = prepared['alpha'] * view.closed_form_residual(
            xy, solved[k + '_sampled'][idx] - prepared['train_v'][idx], w)
        require_close(c, training_c, 'scaled training deviation ' + k)
        ek = view.closed_form_residual(xy, a[k] - a['target'], w)
        require_close(ek, es + c, 'residual addition ' + k)
        require_close(ek, a[k + '_residual'], 'stored model residual ' + k)
        model_norm, secant_norm = norm(es + c), norm(es)
        d = model_norm - secant_norm
        es2, ek2, c2 = np.sum(es * es, axis=1), np.sum((es + c)**2, axis=1), np.sum(c * c, axis=1)
        interaction = 2 * np.sum(es * c, axis=1)
        point[k + '_c'], point[k + '_d_mm'] = c, d
        arm_rows = {}
        for region, mask in masks.items():
            area = float(w[mask].sum())
            weighted = lambda v: float(np.sum(w[mask] * v[mask]) / total)
            g, cs, inter = weighted(d), weighted(c2), weighted(interaction)
            row = dict(arm=k, region=region, count=int(mask.sum()), area_mm2=area,
                       area_fraction=area / total,
                       source_MAE_mm=metrics['MAE_mm'][k], source_secant_MAE_mm=metrics['MAE_mm']['secant'],
                       G_contribution_mm=g, E_s_contribution_mm2=weighted(es2),
                       E_k_contribution_mm2=weighted(ek2), C_contribution_mm2=cs,
                       I_contribution_mm2=inter,
                       conditional_G_mm=g * total / area if area else None,
                       conditional_secant_MAE_mm=weighted(secant_norm) * total / area if area else None,
                       conditional_model_MAE_mm=weighted(model_norm) * total / area if area else None,
                       conditional_deviation_norm_mm=weighted(norm(c)) * total / area if area else None)
            row['G_sign'] = sign(g, max(metrics['MAE_mm'].values()))
            row['I_sign'] = sign(inter, max(cs, weighted(es2), weighted(ek2)), square=True)
            require_close(row['E_k_contribution_mm2'] - row['E_s_contribution_mm2'],
                          cs + inter, 'square identity ' + k + '/' + region, square=True)
            arm_rows[region] = row
            rows.append(row)
        all_row = arm_rows['all']
        require_close(all_row['G_contribution_mm'], metrics['MAE_mm'][k] - metrics['MAE_mm']['secant'],
                      'existing MAE gap ' + k)
        for key in ('G_contribution_mm', 'E_s_contribution_mm2', 'E_k_contribution_mm2',
                    'C_contribution_mm2', 'I_contribution_mm2'):
            require_close(all_row[key], arm_rows['B'][key] + arm_rows['O'][key],
                          'region addition ' + k + '/' + key, square=key.endswith('mm2'))
        checks[k] = dict(max_residual_addition_error_mm=float(np.max(np.abs(ek - es - c))),
                         max_scaled_training_error_mm=float(np.max(np.abs(c - training_c))),
                         MAE_gap_mm=all_row['G_contribution_mm'],
                         saved_MAE_gap_mm=metrics['MAE_mm'][k] - metrics['MAE_mm']['secant'])
    return point, rows, checks


def save_figure(fig, out, name):
    try:
        fig.savefig(out / (name + '.png'), dpi=170)
        fig.savefig(out / (name + '.pdf'))
    finally:
        plt.close(fig)


def draw(point, rows, out, title):
    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    for offset, region, color in ((-.14, 'B', '#0072B2'), (.14, 'O', '#D55E00')):
        vals = [next(r['G_contribution_mm'] for r in rows if r['arm'] == k and r['region'] == region) for k in ARMS]
        ax.bar(np.arange(3) + offset, vals, width=.26, color=color, label=region + ' contribution / global W')
    values = [next(r['G_contribution_mm'] for r in rows if r['arm'] == k and r['region'] == 'all') for k in ARMS]
    ax.scatter(np.arange(3), values, marker='D', color='black', label='total = B + O', zorder=3)
    ax.axhline(0, color='.4', lw=.8)
    ax.set_xticks(range(3), ARMS)
    ax.set_ylabel('MAE gap versus secant [mm]; positive = worse')
    ax.legend(fontsize=9, loc='upper left', bbox_to_anchor=(0, -.12), ncol=2)
    fig.suptitle(title + '\nFixed training band B: |y|<=3.6mm; O: complement; no regional reprojection', fontsize=9)
    save_figure(fig, out, 'mae_gap_contributions')
    bound = max(float(np.abs(point[k + '_d_mm']).max()) for k in ARMS)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4), constrained_layout=True)
    for ax, k in zip(axes, ARMS):
        c = ax.scatter(*point['xy'].T, c=point[k + '_d_mm'], s=10, cmap='RdBu_r',
                       vmin=-bound if bound else -1e-15, vmax=bound if bound else 1e-15)
        for y in (-3.6, 3.6):
            ax.axhline(y, color='.5', ls='--', lw=.8)
        ax.set_title(k)
        ax.set_aspect('equal'); ax.set_xlim(-18, 18); ax.set_ylim(-9, 9)
        ax.set_xlabel('stage13 reference x [mm]'); ax.set_ylabel('stage13 reference y [mm]')
    bar = fig.colorbar(c, ax=axes.tolist())
    bar.set_label('norm gap vs secant [mm]\nred worse / blue better', fontsize=9)
    fig.suptitle(title + '\nAll common points; blank support is not a crack label; shared signed scale', fontsize=9)
    save_figure(fig, out, 'pointwise_mae_gap')


def explanations(out, lineage, report):
    guide = ('## Figure question\n\n'
             'Post-hoc diagnosis: how does frozen mechanics differ from secant, and where does this affect the existing MAE gap?\n\n'
             '## How to read / panels and visual grammar\n\n'
             'mae_gap_contributions: old/proxy/intact on x, signed vector-MAE gap [mm] on y. '
             'Blue B and orange O use global weight denominator; black diamond equals their sum. Positive is worse than secant.\n'
             'pointwise_mae_gap: three fixed model panels, every common point, stage13 x/y [mm]. '
             'Shared symmetric RdBu_r scale: red worse, blue better. Dashed y=+/-3.6 marks the training band, not a physical process zone. '
             'No smoothing, filtering or rescaling; exactly-zero color range alone uses display-only +/-1e-15mm.\n'
             'One common global rigid-complement projection precedes regional aggregation. Regions are not separately aligned. '
             'Squared C+I [mm2] is auxiliary table arithmetic, never substituted for MAE [mm].\n\n'
             '## Limitations and claim boundary\n\n'
             'Known-result single-cycle/specimen controlled experiment; no new held-out or future-cycle validation. '
             'No parameter, blending or boundary search. Secant residual is not identified noise or irreducible/physical nonlinearity; '
             'mechanics-minus-secant deviation is not a verified causal correction. Shared stage13 origin can correlate errors. '
             'Retain documented auxiliary interpolation/source anomalies, W/2D/static assumptions, export-compensation uncertainty '
             'and historical BLAS warnings; none is uniquely attributed by this decomposition. '
             'Arithmetic tolerances and numerically_unresolved signs are not physical/noise acceptance thresholds.\n\n'
             '## Data provenance\n\n' + json.dumps(lineage, ensure_ascii=False) + '\n\n'
             '## Key numerical takeaway\n\n' + json.dumps(report, ensure_ascii=False, allow_nan=False) + '\n\n'
             '## Related assets\n\n'
             'decomposition.csv; pointwise.npz; decomposition.json; execution_receipt.json; same-stem PNG/PDF.\n')
    (out / 'README_analysis.md').write_text(guide)
    for name in ('mae_gap_contributions', 'pointwise_mae_gap'):
        (out / (name + '.md')).write_text('# ' + name + '\n\n' + guide)
    figures = sorted(p for p in out.iterdir() if p.suffix in ('.png', '.pdf'))
    for p in figures:
        note = p.with_suffix('.md').read_text().lower()
        if len(note) < 400 or any(s not in note for s in ('how to read', 'data provenance', 'limitation')):
            raise ValueError('figure sidecar incomplete')
    if len(figures) != 4:
        raise ValueError('two PNG/PDF figures required')


def run(prepare, fit, validation, out, source_commit, run_id, *, lock=None, clock=time.monotonic):
    """CLI uses immutable real anchors; injectable lock/clock only support synthetic unit tests."""
    start = clock()
    roots = (prepare, fit, validation, validation.parent / 'figures')
    if out.exists():
        raise ValueError('fresh output required; no retry')
    if any(out.resolve().is_relative_to(r.resolve()) or r.resolve().is_relative_to(out.resolve()) for r in roots):
        raise ValueError('output/source overlap')
    out.mkdir(parents=True, exist_ok=False)
    receipt = dict(run_id=run_id, source_commit_declared=source_commit, hostname=socket.gethostname(),
                   pid=os.getpid(), command=sys.argv, start_utc=datetime.now(timezone.utc).isoformat(),
                   execution_status='running', budget_seconds=BUDGET, protocol_sha256=PROTOCOL_SHA256,
                   thread_environment={k: os.environ.get(k) for k in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')})
    try:
        with warnings.catch_warnings(), np.errstate(all='warn'):
            warnings.simplefilter('error')
            receipt.update(runner_sha256=prior.sha(__file__), numpy_version=np.__version__,
                           python_version=sys.version, matplotlib_version=matplotlib.__version__)
            within(start, clock)
            a, metrics, p, solved, idx, lineage, before = checked_inputs(
                prepare, fit, validation, DEFAULT_LOCK if lock is None else lock)
            receipt['sources_before_sha256'] = before
            receipt['lineage'] = lineage
            within(start, clock)
            point, rows, checks = decompose(a, metrics, p, solved, idx)
            within(start, clock)
            report = dict(status='post_hoc_diagnostic_only', source_MAE_mm=metrics['MAE_mm'],
                          original_primary_contrast_unchanged=metrics['primary_old_minus_proxy_mm'],
                          arithmetic_checks=checks, rows=rows)
            np.savez_compressed(out / 'pointwise.npz', **point)
            prior.write_json(out / 'decomposition.json', report)
            with (out / 'decomposition.csv').open('w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
            within(start, clock)
            title = 'E017 | post-hoc controlled experiment | cycle292018.5 | train13/14 -> consumed15 | ' + run_id
            draw(point, rows, out, title)
            explanations(out, lineage, report)
            within(start, clock)
            after = hashes([Path(n) for n in before])
            if before != after:
                raise ValueError('source changed during analysis')
            receipt['sources_after_sha256'] = after
            receipt['artifacts_sha256'] = {p.name: prior.sha(p) for p in out.iterdir() if p.is_file() and p.name != 'execution_receipt.json'}
            within(start, clock)
            receipt.update(execution_status='succeeded', elapsed_seconds=clock() - start,
                           end_utc=datetime.now(timezone.utc).isoformat())
            prior.write_json(out / 'execution_receipt.json', receipt)
            # A successful marker is invalidated if final serialization itself crossed the cap.
            within(start, clock)
    except Exception as e:
        receipt.update(execution_status='failed', error=str(e), elapsed_seconds=clock() - start,
                       end_utc=datetime.now(timezone.utc).isoformat(), outputs_role='forensic_only')
        prior.write_json(out / 'execution_receipt.json', receipt)
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('prepare', 'fit', 'validation', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--source-commit', required=True)
    p.add_argument('--run-id', required=True)
    args = p.parse_args()
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        if os.environ.get(key) != '1':
            raise ValueError('single-thread environment required: ' + key)
    if os.environ.get('PYTHONWARNINGS') != 'error':
        raise ValueError('PYTHONWARNINGS=error required, including import-time warnings')
    run(args.prepare, args.fit, args.validation, args.output, args.source_commit, args.run_id)


if __name__ == '__main__':
    main()
