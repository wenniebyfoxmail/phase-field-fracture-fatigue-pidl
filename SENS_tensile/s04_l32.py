"""One L32 solve; B32/V0 are saved scalar controls, never refitted or reevaluated."""
import sys
if sys.flags.optimize:
    raise RuntimeError('non-optimised Python required')
import argparse
import csv
import io as textio
import json
from pathlib import Path
import numpy as np
import s04_l32_inputs as io
import s04_phase as inherited
import s04_raw as raw
from s04_d0 import cycle_weights

EPS = 1e-10


def late_weights(n):
    io.require(type(n) is int and n > 40, 'late prefix required')
    weights = np.zeros(n); weights[40:] = 1./(n-40)
    return weights


def check_baseline(r, g, package):
    for value in (r, g):
        io.require(value['run_id'] == io.BASE_RUN and value['code_commit'] == io.BASE_CODE and
                   value['status'] == 'COMPLETED' and value['confirmation_accessed'] is False and
                   value['output'] == str(io.BASE_OUT) and value['proposal_commit'] == inherited.io.PROPOSAL and
                   value['execution_references']['reviewed_commit'] == io.BASE_CODE and
                   value['execution_references']['approval_ref'] == 'S04-E025-R002-CARD-v1-ba4518d1',
                   'baseline completed identity')
        io.require(value['activity']['solves_attempted'] == value['activity']['fits_completed'] == 2,
                   'baseline two completed arms')
    io.require(r['execution_references'] == g['execution_references'] and r['error'] is None and
               g['dirty_source_status'] == '' and g['primary_reason'] is None and
               not g['errors'] and not g['terminal_caps'] and g['cleanup']['exit_confirmed'] is True and
               g['cleanup']['worker_exit'] == 0 and r['evaluation_rows'] == 121 and
               r['activity'] == g['activity'] and r['input_manifest'] == inherited.io.MANIFEST and
               r['lock_sha256'] == io.LOCK_SHA and r['python_optimize'] == 0 and r['python_debug'] is True,
               'baseline terminal')
    model = package['models']['B32']
    io.require(model['dimensions'] == 32 and model['alpha'] == 1 and model['train'] == list(io.TRAIN),
               'fixed B32 model')
    for key, length in (('scales', 2), ('xm', 32), ('xstd', 32), ('ym', 1), ('ystd', 1), ('coefficient', 33)):
        value = np.asarray(model[key], dtype=float)
        io.require(value.shape == (length,) and np.isfinite(value).all(), 'finite baseline '+key)
    io.require(np.all(np.asarray(model['scales']) > 1e-12) and np.all(np.asarray(model['xstd']) > 0) and
               model['ystd'][0] > 0 and package['sample_ids'] == np.linspace(0, 85111, 2048, dtype=int).tolist() and
               package['sample_ids_semantics'] == 'zero-based positions in admitted pipeline.ids; '
                                                'native cell IDs are pipeline.ids[sample_ids]', 'fixed scales/sample')
    return model, np.asarray(package['sample_ids'], dtype=int)


def fit_one(training, pipeline, reference, sample, activity):
    """Frozen normalisers, late cycle weights, same33-parameter alpha1 system."""
    gram, cross, mass, count = np.zeros((33, 33)), np.zeros(33), 0., 0
    area = pipeline.areas[sample]; area = area/area.sum(); ids = pipeline.ids[sample]
    for key in io.TRAIN:
        case = training[key]
        for cycle in range(41, case['n']+1):
            inherited.check()
            x = raw.features(case, cycle, pipeline, reference['scales'], sample)
            p, f = (raw.source(case, cycle, ids, kind) for kind in ('pin', 'fem'))
            y = ((f[:, 2]-p[:, 2])/reference['scales'][1]-reference['ym'][0])/reference['ystd'][0]
            d = np.column_stack((np.ones(len(x)), (x-reference['xm'])/reference['xstd']))
            w = area*late_weights(case['n'])[cycle-1]/len(io.TRAIN)
            raw.finite(d, y, w)
            gram += np.einsum('ni,n,nj->ij', d, w, d, optimize=False)
            cross += np.einsum('ni,n,n->i', d, w, y, optimize=False)
            mass += float(w.sum()); count += 1
    io.require(count == 116 and abs(mass-1) < 1e-12, 'late training cycles/mass')
    raw.finite(gram, cross)
    penalty = np.eye(33); penalty[0, 0] = 0
    inherited.check(); activity['solves_attempted'] += 1
    coefficient = np.linalg.solve(gram+penalty, cross)
    raw.finite(coefficient)
    activity['fits_completed'] += 1; activity['late_training_cycles'] = count
    return dict(reference, coefficient=coefficient.tolist(), loss_window=[41, 'prefix_end'])


def saved_rows(data):
    rows = list(csv.DictReader(textio.StringIO(data.decode('utf-8'))))
    io.require(len(rows) == 121 and [int(r['cycle']) for r in rows] == list(range(1, 122)), 'saved121 rows')
    for row, weight in zip(rows, cycle_weights(121)):
        io.require(int(row['stratum']) == min((int(row['cycle'])-1)//20, 2) and
                   abs(float(row['cycle_weight'])-weight) < 1e-14, 'saved row weights')
        for arm in ('V0', 'B32'):
            value = float(row[arm+'_physical_mse'])
            io.require(np.isfinite(value) and value >= 0, 'saved error scalar')
        io.require(row['B32_damage_history_identical'] == 'True' and float(row['B32_raw_min']) >= 0 and
                   float(row['B32_raw_negative_area']) == 0, 'saved B32 state')
    return rows


def saved_summary(s, refs):
    io.require(s['run_id'] == io.BASE_RUN and s['code_commit'] == io.BASE_CODE and s['n'] == 121 and
               s['origin'] == 's4 post-history' and s['horizon'] == 0 and s['evaluation'] == 'u011' and
               s['evidence_domain'] == 'SYNTHETIC_VIEWED_DEVELOPMENT' and s['primary_window'] == [41, 121] and
               s['confirmation_accessed'] is False and s['execution_references'] == refs, 'saved summary identity')
    for arm in ('V0', 'B32'):
        value = np.asarray(s['stratum_mse'][arm], dtype=float)
        io.require(value.shape == (3,) and np.isfinite(value).all() and np.all(value >= 0), 'saved aggregate')
    io.require(s['stratum_mse']['B32'][2] == 4409.534774880898, 'fixed saved primary denominator')
    return s


def evaluate(case, pipeline, model, baseline_rows, baseline):
    rows, means = [], np.zeros(3)
    area = pipeline.areas/pipeline.areas.sum()
    for cycle, weight in enumerate(cycle_weights(121), 1):
        inherited.check()
        x = raw.features(case, cycle, pipeline, model['scales'])
        p, f = (raw.source(case, cycle, pipeline.ids, k) for k in ('pin', 'fem'))
        d = np.column_stack((np.ones(len(x)), (x-model['xm'])/model['xstd']))
        t = np.einsum('ij,j->i', d, np.asarray(model['coefficient']), optimize=False)
        t = (t*model['ystd'][0]+model['ym'][0])*model['scales'][1]
        raw.finite(t); v0, candidate = raw.mapped(p, t)
        error = raw.mse(candidate[:, 2]-f[:, 2], area)
        stratum = min((cycle-1)//20, 2); means[stratum] += 3*weight*error
        saved = baseline_rows[cycle-1]
        rows.append(dict(cycle=cycle, stratum=stratum, cycle_weight=float(weight),
            V0_physical_mse=float(saved['V0_physical_mse']), B32_physical_mse=float(saved['B32_physical_mse']),
            L32_physical_mse=error, L32_raw_min=float(candidate[:, 2].min()),
            L32_raw_negative_area=float(np.sum(area*(candidate[:, 2] < 0))),
            L32_damage_history_identical=bool(np.array_equal(candidate[:, :2], v0[:, :2]))))
    ratios = [inherited.safe_ratio(means[j], baseline['stratum_mse']['B32'][j]) for j in range(3)]
    late = ratios[2]; io.require(late is not None, 'identified primary')
    summary = dict(status='DIRECTIONAL_SIGNAL' if late < 1-EPS else
                   'NO_DIRECTIONAL_GAIN' if late > 1+EPS else 'NUMERICAL_TIE',
                   n=121, evaluation='u011', origin='s4 post-history', horizon=0,
                   evidence_domain='SYNTHETIC_VIEWED_DEVELOPMENT', primary_window=[41, 121], primary_R_late=late,
                   stratum_mse=dict(V0=baseline['stratum_mse']['V0'], B32=baseline['stratum_mse']['B32'], L32=means.tolist()),
                   L32_over_B32_stratum_RMSE=ratios,
                   L32_over_B32_balanced_RMSE=inherited.safe_ratio(float(means.mean()), float(np.mean(baseline['stratum_mse']['B32']))),
                   L32_over_V0_stratum_RMSE=[inherited.safe_ratio(means[j], baseline['stratum_mse']['V0'][j]) for j in range(3)],
                   numerical_tie_epsilon=EPS, early_is_reported_cost_not_fatal=True,
                   baseline_recomputed=False, baseline_refitted=False, confirmation_accessed=False,
                   limits='phase-weight sensitivity only; viewed development; no physical-phase, coupling or Pareto proof')
    return rows, summary


def report(out, rows, summary, activity):
    with (out/'percycle.csv').open('x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with (out/'summary.json').open('x') as f:
        json.dump(summary, f, indent=2, allow_nan=False)
    activity['plotting_invoked'] = True
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.3), constrained_layout=True)
    try:
        for name, color in zip(('V0', 'B32', 'L32'), ('#777777', '#0072B2', '#D55E00')):
            ax[0].plot([r['cycle'] for r in rows], [r[name+'_physical_mse'] for r in rows],
                       label=name+(' (saved)' if name != 'L32' else ''), color=color, lw=1.3)
        for boundary in (20.5, 40.5): ax[0].axvline(boundary, color='gray', ls=':', lw=.8)
        ax[0].set(xlabel='Physical cycle (all121)', ylabel='Physical raw MSE (archive units squared)', title='A | Saved controls vs one new L32'); ax[0].legend()
        for j, ratio in enumerate(summary['L32_over_B32_stratum_RMSE']):
            if ratio is not None: ax[1].plot(j, ratio, 'o', color='#D55E00' if j == 2 else '#0072B2')
            else: ax[1].text(j, 1, 'unidentified', ha='center')
        ax[1].axhline(1, color='gray', ls='--')
        ax[1].set(xticks=[0, 1, 2], xticklabels=['C1-20', 'C21-40', 'C41-121 primary'], ylabel='L32 / saved B32 RMSE', title='B | Late direction; other stages are costs')
        fig.suptitle(io.RUN+' | viewed synthetic U0.11 | s4 / horizon0\nTraining-weight probe, NOT a physical phase or coupling test', fontsize=10)
        with (out/'diagnostic.png').open('xb') as f: fig.savefig(f, format='png', dpi=120)
    finally:
        plt.close(fig)
    with (out/'README_analysis.md').open('x') as f:
        f.write('# L32 stage-weight diagnostic\n\nQuestion: can late-only loss improve late U0.11 raw error with the same32 features?\n'
                'Sources: nine fixed native s4 files; frozen E025-R002 controls. B32/V0 scalar errors are copied, NOT predicted again.\n'
                'Read summary,121-row table, then A all-cycle MSE and B fixed-stratum ratios. Late is primary; early/overall costs are not vetoes.\n'
                'Only one L32 solve; frozen B32 normalisers/sample, alpha1. Damage/history remain V0.\n'
                'Directional development signal only, tiny gains weak; C41 is not a physical phase or deployable gate. '
                'No Pareto, coupling, causal, teacher or confirmation claim. Old E025/E021 verdicts unchanged.\n'
                'Next report the saved result and cost, no automatic fit, reweighting sweep or confirmation opening.\n')


def run(out):
    m, code, refs = io.child_authorization(out)
    a = dict(metadata_attempts=0, read_attempts=0, hash_bytes_read=0, decode_attempts=0, verified_inputs=[],
             frozen_read_attempts=0, verified_frozen=[], fitting_invoked=False, solves_attempted=0, fits_completed=0,
             late_training_cycles=0, training_released=False, evaluation_invoked=False, plotting_invoked=False)
    phase, error = 'FROZEN_TRAIN_CONTROLS', None
    try:
        r, g, package = [io.read_frozen(m, name, a) for name in ('receipt.json', 'guard_receipt.json', 'models.json')]
        model, sample = check_baseline(r, g, package)
        expected = [{k: v[k] for k in ('case', 'kind', 'role', 'path', 'sha256')} for v in r['activity']['verified_inputs']]
        io.require(expected == m['scientific_files'], 'baseline scientific identities')
        reader = io.Reader(m, a); phase = 'LOAD_TRAIN'
        pipeline = inherited.load_geometry(reader)
        io.require(package['feature_names'] == pipeline.names+['fatigue_state_x_raw'], 'unchanged original32 names')
        training = {k: inherited.load_case(reader, k) for k in io.TRAIN}
        phase = 'FIT_L32'; a['fitting_invoked'] = True
        candidate = fit_one(training, pipeline, model, sample, a)
        del training; a['training_released'] = True
        with (out/'models.json').open('x') as f:
            json.dump(dict(L32=candidate, baseline_run=io.BASE_RUN, baseline_model=str(io.BASE_OUT/'models.json'),
                           sample_ids=sample.tolist(), feature_names=pipeline.names, baseline_refitted=False), f, indent=2, allow_nan=False)
        phase = 'LOAD_SAVED_EVALUATION'
        old_rows = io.read_frozen(m, 'percycle.csv', a, saved_rows)
        baseline = saved_summary(io.read_frozen(m, 'summary.json', a), r['execution_references'])
        phase = 'LOAD_EVALUATION'; evaluation = inherited.load_case(reader, 'u011')
        phase = 'EVALUATE_L32'; a['evaluation_invoked'] = True
        rows, summary = evaluate(evaluation, pipeline, candidate, old_rows, baseline)
        summary.update(experiment_id=io.EXPERIMENT, run_id=io.RUN, code_commit=code, proposal_commit=io.PROPOSAL,
                       execution_references=refs, baseline_run=io.BASE_RUN, units='raw archive units squared')
        phase = 'REPORT'; report(out, rows, summary, a)
    except BaseException as exc:
        error = dict(stage=phase, type=type(exc).__name__)
        if isinstance(exc, raw.Terminal): error['status'] = exc.status
    receipt = dict(status='COMPLETED' if error is None else 'FAILED', error=error, experiment_id=io.EXPERIMENT,
                   run_id=io.RUN, code_commit=code, proposal_commit=io.PROPOSAL, output=str(out),
                   execution_references=refs, input_manifest=io.MANIFEST, lock_sha256=io.LOCK_SHA, activity=a,
                   source_metadata_accessed=a['metadata_attempts'] > 0, real_data_read=a['hash_bytes_read'] > 0,
                   baseline_recomputed=False, baseline_refitted=False, confirmation_accessed=False,
                   evaluation_rows=121 if error is None else None, python_optimize=sys.flags.optimize, python_debug=__debug__)
    with (out/'receipt.json').open('x') as f: json.dump(receipt, f, indent=2, allow_nan=False)
    print(json.dumps(dict(worker_status=receipt['status'], fits_completed=a['fits_completed'], error=error)), flush=True)
    return int(error is not None)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    raise SystemExit(run(p.parse_args().out))
