"""E025 two fixed ridge systems, B32 vs one fatigue/raw interaction C33.

Import is inert with respect to scientific IO. No NN, alpha selection, early
fatal performance guard, replay or confirmation mode. Use the approved guard.
"""
import sys

if sys.flags.optimize:
    raise RuntimeError('non-optimised Python required')

import argparse
import csv
import json
import os
from pathlib import Path
import time

import numpy as np
from scipy.io import loadmat

import s04_phase_inputs as io
import s04_raw as raw
from s04_d0 import merge_moments, cycle_weights
from s04_g5_features import FeaturePipeline, FIELDS

EPS = 1e-10
ARMS = ('V0', 'B32', 'C33')
FILES = {'authorization.json', 'models.json', 'percycle.csv', 'summary.json',
         'diagnostic.png', 'README_analysis.md', 'receipt.json', 'run.log', 'guard_receipt.json'}


def check():
    start = float(os.environ['RAW_START_MONOTONIC'])
    raw.require(time.monotonic()-start < 295, 'work reserve reached', 'INCONCLUSIVE_INCOMPLETE')


def load_geometry(reader):
    def decode(file):
        with np.load(file, allow_pickle=False) as g:
            centers, areas, contained = (g[k] for k in ('centers', 'areas', 'contained'))
        io.require(centers.shape == (86408, 2) and areas.shape == contained.shape == (86408,) and
                   contained.dtype == np.dtype(bool), 'native geometry shape/type')
        p = FeaturePipeline(centers, areas, contained)
        io.require(len(p.ids) == 85112, 'admitted support')
        return p
    return reader.read(None, 'geometry', decode)


def load_case(reader, key):
    n = io.COUNTS[key]
    def pin_decode(file):
        with np.load(file, allow_pickle=False) as p:
            io.require(np.array_equal(p['cycles'][:n].ravel(), np.arange(1, n+1)) and
                       np.array_equal(p['raw_steps'][:n].ravel(), 5*np.arange(1, n+1)-1),
                       'PIN s4 prefix')
            values = {k: p[k][:n] for k in FIELDS}
        io.require(all(v.shape == (n, 86408) and np.issubdtype(v.dtype, np.number)
                       for v in values.values()), 'PIN field shape/type')
        # Admitted-cell finite/range checks occur in the unchanged features.
        # Excluded PIN values must not contaminate current globals/neighbours.
        return values
    def fem_decode(file):
        f = loadmat(file, variable_names=['damage', 'alpha_bar', 'psi_raw_direct', 'cycles'])
        io.require(np.array_equal(f['cycles'].ravel()[:n], np.arange(1, n+1)), 'FEM s4 prefix')
        values = {k: f[k][:n] for k in ('damage', 'alpha_bar', 'psi_raw_direct')}
        for k, v in values.items():
            io.require(v.shape == (n, 86408) and np.isfinite(v).all() and np.all(v >= 0), 'FEM shape/finite/range')
            if k == 'damage':
                io.require(np.all(v <= 1), 'FEM damage bound')
        return values
    return dict(n=n, umax={'u011': .11, 'u0115': .115, 'u012': .12, 'u013': .13}[key],
                pin=reader.read(key, 'pin', pin_decode), fem=reader.read(key, 'fem', fem_decode))


def augmented(x, names):
    io.require(x.ndim == 2 and x.shape[1] == 32, 'original 32 columns')
    q = 1.-x[:, names.index('current_global_fatigue_f')]
    z = q*x[:, names.index('current_psi_raw_direct')]
    raw.finite(q, z)
    return np.column_stack((x, z)), q


def fit(training, pipeline, activity):
    """Train-only shared moments/Gram; exactly two alpha=1 linear solves."""
    io.require(set(training) == set(io.TRAIN), 'only three training cases')
    scales = raw.scales(training, io.TRAIN, pipeline)
    sample = np.linspace(0, len(pipeline.ids)-1, 2048, dtype=int)
    area = pipeline.areas[sample]; area = area/area.sum()
    ids = pipeline.ids[sample]
    def blocks():
        for key in io.TRAIN:
            c = training[key]
            for cycle, weight in enumerate(cycle_weights(c['n']), 1):
                check()
                x, q = augmented(raw.features(c, cycle, pipeline, scales, sample), pipeline.names)
                p = raw.source(c, cycle, ids, 'pin'); f = raw.source(c, cycle, ids, 'fem')
                y = ((f[:, 2]-p[:, 2])/scales[1])[:, None]
                w = area*weight/len(io.TRAIN)
                raw.finite(x, y, w)
                yield x, y, w, q
    sx = sy = None
    q_min, q_max = float('inf'), -float('inf')
    for x, y, w, q in blocks():
        sx = merge_moments(sx, x, w); sy = merge_moments(sy, y, w)
        q_min = min(q_min, float(q.min())); q_max = max(q_max, float(q.max()))
    io.require(sx is not None and sy is not None and abs(sx[0]-1) < 1e-12 and abs(sy[0]-1) < 1e-12,
               'training mass')
    io.require(np.all(sx[2] >= 0) and np.all(sy[2] >= 0), 'nonnegative centred moments')
    xs, ys = np.sqrt(sx[2]), np.sqrt(sy[2]); raw.finite(*sx, *sy, xs, ys)
    z_std_before_sentinel = float(xs[-1])
    xs[xs < 1e-12] = 1.; ys[ys < 1e-12] = 1.
    gram = np.zeros((34, 34)); cross = np.zeros((34, 1)); mass = 0.
    for x, y, w, _ in blocks():
        d = np.column_stack((np.ones(len(x)), (x-sx[1])/xs))
        target = (y-sy[1])/ys
        raw.finite(d, target)
        gram += np.einsum('ni,n,nj->ij', d, w, d, optimize=False)
        cross += np.einsum('ni,n,nj->ij', d, w, target, optimize=False)
        mass += float(w.sum())
        raw.finite(gram, cross)
    io.require(abs(mass-sx[0]) < 1e-12, 'second pass mass')
    models = {}
    for name, dimensions in (('B32', 32), ('C33', 33)):
        check()
        penalty = np.eye(dimensions+1); penalty[0, 0] = 0.
        activity['solves_attempted'] += 1
        coefficient = np.linalg.solve(gram[:dimensions+1, :dimensions+1]+penalty,
                                      cross[:dimensions+1])
        raw.finite(coefficient)
        activity['fits_completed'] += 1
        models[name] = dict(train=list(io.TRAIN), alpha=1., dimensions=dimensions, scales=scales.tolist(),
                            xm=sx[1][:dimensions].tolist(), xstd=xs[:dimensions].tolist(),
                            ym=sy[1].tolist(), ystd=ys.tolist(), coefficient=coefficient[:, 0].tolist())
    proxy = dict(training_q_min=q_min, training_q_max=q_max,
                 training_z_std=z_std_before_sentinel,
                 near_constant=(q_max-q_min <= 1e-12 or z_std_before_sentinel < 1e-12),
                 interpretation='proxy only; feature/regularisation effect not physical stage proof')
    return models, proxy, sample.tolist()


def safe_ratio(candidate, baseline):
    if baseline <= 1e-24:
        return None
    value = float(np.sqrt(candidate)/np.sqrt(baseline))
    io.require(np.isfinite(value), 'finite ratio')
    return value


def evaluate(c, pipeline, models):
    area = pipeline.areas/pipeline.areas.sum()
    means = np.zeros((3, 3)); rows = []
    qmin, qmax = float('inf'), -float('inf')
    for cycle, weight in enumerate(cycle_weights(c['n']), 1):
        check(); s = min((cycle-1)//20, 2)
        p = raw.source(c, cycle, pipeline.ids, 'pin'); f = raw.source(c, cycle, pipeline.ids, 'fem')
        v0 = raw.admissible(p)
        x, q = augmented(raw.features(c, cycle, pipeline, models['B32']['scales']), pipeline.names)
        qmin = min(qmin, float(q.min())); qmax = max(qmax, float(q.max()))
        row = dict(cycle=cycle, stratum=s, cycle_weight=float(weight),
                   V0_physical_mse=raw.mse(v0[:, 2]-f[:, 2], area))
        means[0, s] += 3*weight*row['V0_physical_mse']
        for index, name in enumerate(('B32', 'C33'), 1):
            model = models[name]; dim = model['dimensions']
            d = np.column_stack((np.ones(len(x)), (x[:, :dim]-model['xm'])/model['xstd']))
            raw.finite(d)
            t = np.einsum('ij,j->i', d, np.asarray(model['coefficient']), optimize=False)
            t = t*model['ystd'][0]+model['ym'][0]
            raw.finite(t)
            base, value = raw.mapped(p, model['scales'][1]*t)
            io.require(np.array_equal(base, v0), 'shared V0')
            error = raw.mse(value[:, 2]-f[:, 2], area)
            means[index, s] += 3*weight*error
            row.update({name+'_physical_mse': error, name+'_raw_min': float(value[:, 2].min()),
                        name+'_raw_negative_area': float(np.sum(area*(value[:, 2] < 0))),
                        name+'_damage_history_identical': bool(np.array_equal(value[:, :2], v0[:, :2]))})
        raw.finite(means)
        rows.append(row)
    io.require(len(rows) == 121 and [r['cycle'] for r in rows] == list(range(1, 122)), 'complete evaluation prefix')
    io.require(means[1, 2] > 1e-24, 'unidentified primary baseline')
    ratios = [safe_ratio(means[2, s], means[1, s]) for s in range(3)]
    late = ratios[2]
    status = 'DIRECTIONAL_SIGNAL' if late < 1-EPS else 'NO_DIRECTIONAL_GAIN' if late > 1+EPS else 'NUMERICAL_TIE'
    summary = dict(status=status, experiment_id=io.EXPERIMENT, run_id=io.RUN,
                   evidence_domain='SYNTHETIC_VIEWED_DEVELOPMENT', origin='s4 post-history', horizon=0,
                   evaluation='u011', n=121, primary_window=[41, 121], primary_R_late=late,
                   stratum_mse={name: means[j].tolist() for j, name in enumerate(ARMS)},
                   C33_over_B32_stratum_RMSE=ratios,
                   auxiliary_ratio_unidentified=[v is None for v in ratios],
                   C33_over_B32_balanced_RMSE=safe_ratio(float(means[2].mean()), float(means[1].mean())),
                   B32_over_V0_stratum_RMSE=[safe_ratio(means[1, s], means[0, s]) for s in range(3)],
                   C33_over_V0_stratum_RMSE=[safe_ratio(means[2, s], means[0, s]) for s in range(3)],
                   evaluation_q_min=qmin, evaluation_q_max=qmax,
                   numerical_tie_epsilon=EPS, early_is_reported_cost_not_fatal=True,
                   units='raw archive units squared', phase_causality_established=False,
                   original_E021_verdict_unchanged=True,
                   limits='single viewed trajectory; correlated cycles; no statistical, causal or confirmation claim')
    return rows, summary


def report(out, rows, summary, on_plot):
    with (out/'percycle.csv').open('x', newline='') as file:
        w = csv.DictWriter(file, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with (out/'summary.json').open('x') as file:
        json.dump(summary, file, indent=2, allow_nan=False)
    on_plot()
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.3), constrained_layout=True)
    try:
        for name, color in zip(ARMS, ('#777777', '#0072B2', '#D55E00')):
            axes[0].plot([r['cycle'] for r in rows], [r[name+'_physical_mse'] for r in rows],
                         label=name, color=color, lw=1.3)
        for boundary in (20.5, 40.5):
            axes[0].axvline(boundary, color='gray', ls=':', lw=.8)
        axes[0].set(xlabel='Physical cycle (all 121)', ylabel='Physical raw MSE (archive units squared)',
                    title='A | Same-state outputs, all cycles retained')
        axes[0].legend()
        for j, value in enumerate(summary['C33_over_B32_stratum_RMSE']):
            if value is None:
                axes[1].text(j, 1., 'unidentified', ha='center', rotation=90)
            else:
                axes[1].plot(j, value, 'o', color='#D55E00' if j == 2 else '#0072B2')
        axes[1].axhline(1., color='gray', ls='--', lw=1)
        axes[1].set(xticks=[0, 1, 2], xticklabels=['C1-20', 'C21-40', 'C41-121 (primary)'],
                    ylabel='C33 / B32 RMSE', title='B | Directional late signal; other phases are costs')
        fig.suptitle(io.RUN+' | viewed synthetic development, U0.11 | s4 / horizon 0\n'
                     'Exploratory representation increment, NOT a physical stage or confirmation test', fontsize=10)
        with (out/'diagnostic.png').open('xb') as file:
            fig.savefig(file, format='png', dpi=120)
    finally:
        plt.close(fig)
    with (out/'README_analysis.md').open('x') as file:
        file.write('# S04-E025 analysis\n\nQuestion: does one fatigue/raw interaction add a directional '
                   'late benefit over a matched alpha=1 B32 ridge?\n'
                   'Sources: the fixed input manifest/legacy G5 lock in receipt.json; three viewed training cases, '
                   'seen u011 evaluation, same s4 post-history/horizon0 support. New B32 is not historical selected V1.\n'
                   'Read summary, percycle table, then A (V0/B32/C33 physical MSE, all121cycles) and B '
                   '(three fixed strata C33/B32 RMSE, late primary, baseline1). Units and states are shared.\n'
                   'Only the late ratio selects direction. Early/overall trade-offs are reported, not fatal '
                   'performance guards. Epsilon1e-10 is a numerical tie, not a practical/significance margin. '
                   'Tiny gains are weak exploratory signals, not robust improvement.\n'
                   'Proxy range and near-constant status are in summary/models; a constant proxy or effective '
                   'ridge shrinkage change cannot establish phase action. No physical cause, gradient conflict, '
                   'independent-cycle inference, chosen loss or confirmation generalisation is established.\n'
                   'Old E021 result is unchanged. Next only review saved evidence and propose whether to continue; '
                   'no automatic additional fit, proxy/alpha search, loss change or confirmation opening.\n')


def run(out):
    m, code, refs = io.child_authorization(out)
    activity = dict(metadata_attempts=0, read_attempts=0, hash_bytes_read=0, decode_attempts=0,
                    verified_inputs=[], fitting_invoked=False, solves_attempted=0, fits_completed=0,
                    evaluation_invoked=False, plotting_invoked=False)
    phase, error = 'LOAD_TRAIN', None
    try:
        reader = io.Reader(m, activity)
        pipeline = load_geometry(reader)
        training = {key: load_case(reader, key) for key in io.TRAIN}
        phase = 'FIT'
        activity['fitting_invoked'] = True
        models, proxy, sample = fit(training, pipeline, activity)
        with (out/'models.json').open('x') as file:
            json.dump(dict(models=models, proxy=proxy, sample_ids=sample,
                           feature_names=pipeline.names+['fatigue_state_x_raw']), file, indent=2, allow_nan=False)
        del training  # Evaluation inputs cannot enter train-only normalisers.
        phase = 'LOAD_EVALUATION'
        io.require(activity['fits_completed'] == 2, 'evaluation only after both fits')
        evaluation = load_case(reader, 'u011')
        phase = 'EVALUATE'
        activity['evaluation_invoked'] = True
        rows, summary = evaluate(evaluation, pipeline, models)
        summary.update(proxy=proxy, code_commit=code, proposal_commit=io.PROPOSAL,
                       execution_references=refs, fitting_invoked=True, confirmation_accessed=False)
        phase = 'REPORT'
        def on_plot():
            activity['plotting_invoked'] = True
        report(out, rows, summary, on_plot)
    except BaseException as exc:
        error = dict(stage=phase, type=type(exc).__name__)
        if isinstance(exc, raw.Terminal):
            error['status'] = exc.status
    receipt = dict(status='COMPLETED' if error is None else 'FAILED', experiment_id=io.EXPERIMENT,
                   run_id=io.RUN, code_commit=code, proposal_commit=io.PROPOSAL, output=str(out),
                   execution_references=refs, input_manifest=io.MANIFEST, lock_sha256=io.LOCK_SHA,
                   activity=activity, source_metadata_accessed=activity['metadata_attempts'] > 0,
                   real_data_read=activity['hash_bytes_read'] > 0, error=error,
                   evaluation_rows=121 if error is None else None,
                   python_optimize=sys.flags.optimize, python_debug=__debug__, confirmation_accessed=False)
    with (out/'receipt.json').open('x') as file:
        json.dump(receipt, file, indent=2, allow_nan=False)
    print(json.dumps(dict(worker_status=receipt['status'], fits_completed=activity['fits_completed'], error=error)), flush=True)
    return int(error is not None)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.out))
