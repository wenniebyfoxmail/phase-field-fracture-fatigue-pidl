"""No-fit inference replay. Independent summation/output/scoring, frozen features."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import time

import numpy as np

ABS = REL = 1e-10
RATIO_ABS = 1e-12
COUNTS = dict(u011=121, u0115=99, u012=82, u013=55)
FIELDS = ('damage', 'alpha_bar', 'psi_raw_direct')
ALPHAS = (.01, 1., 100.)


def require(ok, message):
    if not ok: raise ValueError(message)


def finite(*values):
    require(all(np.isfinite(v).all() for v in values), 'nonfinite replay value')


def check_time():
    if 'RAW_REPLAY_START' in os.environ:
        require(time.monotonic()-float(os.environ['RAW_REPLAY_START']) < 295, 'wall reserve')


def close(actual, saved, absolute=ABS, relative=REL):
    finite(actual, saved)
    delta = np.abs(np.asarray(actual)-np.asarray(saved))
    bound = absolute+relative*np.abs(saved)
    require(bool(np.all(delta <= bound)), 'replay differs beyond frozen numeric tolerance')
    return float(np.max(delta)), float(np.max(delta/bound))


def predict(pin, x, model, alpha):
    """Stored scalar model only; no moments, normalizer updates, solve or fit."""
    finite(pin); require(pin.ndim == 2 and pin.shape[1] == 3, 'PIN shape')
    require(np.all(pin[:, 1:] >= 0), 'PIN source history/raw admission')
    v0 = np.column_stack((np.clip(pin[:, 0], 0, 1), np.maximum(pin[:, 1:], 0)))
    if alpha is None:
        require(model is None, 'fallback model must be absent'); return v0, v0.copy()
    require(alpha in ALPHAS and model is not None, 'frozen alpha/model')
    arrays = {k: np.asarray(model[k], dtype=np.float64) for k in
              ('scales', 'xm', 'ym', 'xstd', 'ystd', 'coefficients')}
    finite(x, *arrays.values())
    require(x.shape == (len(pin), 32) and arrays['coefficients'].shape == (3, 33, 1), 'model shape')
    require(arrays['xm'].shape == arrays['xstd'].shape == (32,) and
            arrays['ym'].shape == arrays['ystd'].shape == (1,) and arrays['scales'].shape == (2,), 'normalizer shape')
    require(np.all(arrays['scales'] > 1e-12) and np.all(arrays['xstd'] > 0) and
            np.all(arrays['ystd'] > 0), 'frozen scales/std')
    coeff = arrays['coefficients'][ALPHAS.index(alpha), :, 0]
    with np.errstate(over='raise', invalid='raise', divide='raise'):
        z = (x-arrays['xm'])/arrays['xstd']
        t = (np.sum(z*coeff[1:], axis=1)+coeff[0])*arrays['ystd'][0]+arrays['ym'][0]
        raw_sum = pin[:, 2]+arrays['scales'][1]*t
    finite(z, t, raw_sum)  # Check before projection, including -Inf.
    v1 = v0.copy(); v1[:, 2] = np.maximum(raw_sum, 0)
    finite(v0, v1)
    require(np.array_equal(v0[:, :2], v1[:, :2]), 'damage/history changed')
    require(np.all((v1[:, 0] >= 0) & (v1[:, 0] <= 1)) and np.all(v1[:, 1:] >= 0), 'output bounds')
    return v0, v1


def mse(predicted, target, areas):
    finite(predicted, target, areas)
    require(np.all(areas > 0), 'positive native areas')
    with np.errstate(over='raise', invalid='raise'):
        error = predicted-target
        value = float(np.sum(areas*error*error)/np.sum(areas))
    finite(value); return value


def replay(cases, pipeline, ref, out):
    keys = sorted(cases); require(len(keys) == 4, 'four cases')
    source_rows = ref['rows']; require(len(source_rows) == sum(c['n'] for c in cases.values()), 'row count')
    rows = {(r['holdout'], int(r['cycle'])): r for r in source_rows}
    require(len(rows) == len(source_rows), 'duplicate cycle')
    require(set(rows) == {(k, n) for k in keys for n in range(1, cases[k]['n']+1)}, 'cycle coverage')
    require(pipeline.names == ref['feature_names'], 'frozen feature order')
    sels = {r['holdout']: r for r in ref['selection']}
    folds = {r['holdout']: r for r in ref['decision']['folds']}
    require(set(sels) == set(folds) == set(keys), 'reference fold coverage')
    summaries = []; c20 = None
    columns = ['holdout', 'cycle', 'V0_saved_mse', 'V0_replay_mse', 'V1_saved_mse',
               'V1_replay_mse', 'max_mse_abs_diff', 'max_tolerance_fraction', 'V1_raw_min', 'V1_raw_max']
    with (out/'comparison.csv').open('x') as file:
        writer = csv.DictWriter(file, fieldnames=columns); writer.writeheader()
        for key in keys:
            c = cases[key]; sel = sels[key]; alpha = sel['selected_alpha']; fold = folds[key]
            require(sel['train'] == [k for k in keys if k != key], 'outer training identity')
            require(fold['fallback'] == (alpha is None), 'frozen fallback identity')
            model = ref['models']['outer_'+key]
            if model is not None: require(model['train'] == sel['train'], 'model train identity')
            means = np.zeros((3, 2)); counts = np.zeros(3, dtype=int); worst = 0.; maxdiff = 0.
            for cycle in range(1, c['n']+1):
                check_time(); old = rows[key, cycle]; stratum = min((cycle-1)//20, 2)
                require(int(old['stratum']) == stratum and (old['fallback'] == 'True') == fold['fallback'], 'saved cycle identity')
                nstratum = sum(min((n-1)//20, 2) == stratum for n in range(1, c['n']+1))
                require(abs(float(old['cycle_weight'])-1/(3*nstratum)) < 1e-16, 'saved cycle weight')
                require((old['selected_alpha'] == '') if alpha is None else float(old['selected_alpha']) == alpha, 'saved alpha')
                pin = np.column_stack([c['pin'][f][cycle-1, pipeline.ids] for f in FIELDS]).astype(float)
                fem = np.column_stack([c['fem'][f][cycle-1, pipeline.ids] for f in FIELDS]).astype(float)
                finite(fem); require(np.all((fem[:, 0] >= 0) & (fem[:, 0] <= 1)) and np.all(fem[:, 1:] >= 0), 'FEM admission')
                x = None if model is None else pipeline.trajectory_cycle(c['pin'], cycle, c['umax'], model['scales'])
                v0, v1 = predict(pin, x, model, alpha)
                errors = np.array([mse(v[:, 2], fem[:, 2], pipeline.areas) for v in (v0, v1)])
                saved = np.array([float(old['V0_physical_mse']), float(old['V1_physical_mse'])])
                delta, fraction = close(errors, saved); worst = max(worst, fraction); maxdiff = max(maxdiff, delta)
                require(old['damage_history_identical'] == 'True' and float(old['raw_negative_area']) == 0, 'saved output invariants')
                for name, v in (('V0', v0), ('V1', v1)):
                    close(np.array([v[:, 2].min(), v[:, 2].max()]),
                          np.array([float(old[name+'_raw_min']), float(old[name+'_raw_max'])]))
                means[stratum] += errors; counts[stratum] += 1
                writer.writerow(dict(zip(columns, [key, cycle, saved[0], errors[0], saved[1], errors[1],
                                 delta, fraction, v1[:, 2].min(), v1[:, 2].max()])))
                if key == 'u0115' and cycle == 20:
                    np.testing.assert_array_equal(pipeline.ids, ref['snapshot']['ids'])
                    c20 = {name: close(v, ref['snapshot'][name]) for name, v in
                           (('fem', fem), ('V0', v0), ('V1', v1))}
            require(np.all(counts > 0), 'three nonempty strata')
            means /= counts[:, None]; total = means.mean(axis=0)
            require(total[0] > 1e-24 and means[0, 0] > 1e-24, 'unidentified denominator')
            r = math.sqrt(total[1]/total[0]); g = math.sqrt(means[0, 1]/means[0, 0])
            close(np.array([r, g]), np.array([fold['R'], fold['G']]), RATIO_ABS, 0.)
            summaries.append(dict(holdout=key, R=r, G=g, max_mse_abs_diff=maxdiff,
                                  max_tolerance_fraction=worst, stratum_mse=means.tolist()))
            print('replayed', key, flush=True)
    require(c20 is not None, 'fixed C20 snapshot missing')
    q = max(f['R'] for f in summaries); close(q, ref['decision']['Q'], RATIO_ABS, 0.)
    status = ('EARLY_REGRESSION' if any(f['G'] > 1+1e-10 for f in summaries) else
              'RAW_REGRESSION' if q > 1+1e-10 else
              'DIRECTIONAL_DEVELOPMENT_GAIN' if q < 1-1e-10 else 'NUMERICAL_TIE')
    require(status == ref['decision']['status'], 'original verdict changed')
    return dict(status='REPLAY_ARITHMETIC_MATCH', folds=summaries, Q=q,
                original_verdict=status, C20_field_comparison=c20, fitting_invoked=False,
                limitation='Other-cycle full original predictions unavailable; scalar/bounds replay, not pointwise equality to unsaved fields.')


def reference():
    from s04_raw_replay_guard import BASE, REFERENCE_COMMIT, LOCK_SHA
    out = BASE/'runs/S04-E021-R001'
    audit = json.loads((BASE/'control/S04-E021-R001_saved_output_verification.json').read_text())
    require(audit['status'] == 'VERIFIED_SAVED_OUTPUTS' and audit['run_id'] == out.name and
            audit['code_commit'] == REFERENCE_COMMIT, 'frozen audit identity')
    expected = {'receipt.json', 'models.json', 'selection.json', 'decision.json', 'percycle.csv',
                'folds.csv', 'u0115_C20.npz', 'V0_V1_holdouts.png', 'u0115_C20_raw.png', 'README_analysis.md'}
    require({p.name for p in out.iterdir()} == expected, 'frozen output set')
    allowed = {str(p) for p in out.iterdir() if p.is_file()} | {str(out.parent/(out.name+s)) for s in
               ('_guard.log', '_fit_guard_receipt.json', '_guard_receipt.json')}
    inventory = audit['frozen_files']
    require(len(inventory) == 13 and {v['path'] for v in inventory} == allowed, 'frozen inventory')
    def check():
        for v in inventory:
            s = Path(v['path']).stat()
            require((s.st_mode & 0o222) == 0 and s.st_size == v['bytes'] and s.st_mtime_ns == v['mtime_ns'], 'reference changed')
    check()
    read = lambda name: json.loads((out/name).read_text())
    receipt = read('receipt.json')
    guard = json.loads((out.parent/(out.name+'_guard_receipt.json')).read_text())
    stage = json.loads((out.parent/(out.name+'_fit_guard_receipt.json')).read_text())
    require(all(v['status'] == 'COMPLETED' and v['code_commit'] == REFERENCE_COMMIT and
                v['run_id'] == out.name for v in (receipt, guard, stage)), 'reference receipt')
    require(receipt['lock_sha256'] == LOCK_SHA and receipt['rows'] == 357 and
            len(receipt['feature_names']) == 32 and receipt['mode'] == 'real', 'reference state identity')
    require([v['phase'] for v in guard['children']] == ['fit', 'report'] and
            all(v['exit_code'] == 0 for v in guard['children']) and
            stage['children'][0]['pid'] == receipt['pid'] == guard['children'][0]['pid'], 'reference child binding')
    with (out/'percycle.csv').open() as f: rows = list(csv.DictReader(f))
    with np.load(out/'u0115_C20.npz', allow_pickle=False) as p:
        snapshot = {k: p[k] for k in ('ids', 'fem', 'V0', 'V1')}
    return dict(rows=rows, models=read('models.json'), selection=read('selection.json'),
                decision=read('decision.json'), snapshot=snapshot,
                feature_names=receipt['feature_names']), check


def report(result, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7, 3.5), constrained_layout=True)
    ax.plot([v['holdout'] for v in result['folds']], [v['max_tolerance_fraction'] for v in result['folds']], 'o')
    ax.axhline(1., color='gray', linestyle='--'); ax.set_ylim(bottom=0.)
    ax.set_ylabel('max MSE arithmetic difference / allowed tolerance')
    scope = 'GENERATED FIXTURE — ENGINEERING ONLY' if result.get('generated_fixture') else 'frozen archive / s4 horizon0 replay'
    ax.set_title(scope+'\n'+out.name+' | NOT new method evidence')
    fig.savefig(out/'replay_comparison.png', dpi=150); plt.close(fig)
    (out/'README_analysis.md').write_text(scope+'\nFrozen-model inference replay only; no fitting or fresh holdout.\n'
        'Read comparison.csv and summary.json before replay_comparison.png; threshold1 is arithmetic only.\n'
        'Original U0.11 late regression remains; no physics/teacher/confirmation or NN claim.\n')


def main():
    from s04_raw_replay_guard import authorize, ROOT, LOCK_SHA
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--authorization', type=Path, required=True); args = p.parse_args()
    out = args.out.resolve(); a = authorize(args.authorization.resolve(), out)
    require(os.environ.get('RAW_REPLAY_COMMIT') == a['code_commit'] and
            os.environ.get('RAW_REPLAY_ID') == a['run_id'] and
            os.environ.get('RAW_REPLAY_PARENT') == str(os.getppid()) and
            'RAW_REPLAY_START' in os.environ, 'use inference-only guard')
    out.mkdir(parents=True, exist_ok=False)
    try:
        ref, check_reference = reference()
        from s04_d0 import load_inputs, LOCK_SHA as LOADER_LOCK
        require(LOADER_LOCK == LOCK_SHA, 'loader identity')
        cases, pipeline = load_inputs(ROOT, ROOT/'docs/research/S04/S04-E016/paired_s4_lock_candidate_20261013.json')
        require({k: c['n'] for k, c in cases.items()} == COUNTS and len(pipeline.ids) == 85112, 'admitted scope')
        result = replay(cases, pipeline, ref, out); check_reference(); report(result, out)
    except Exception as e:
        result = dict(status='REPLAY_FAILED_OR_INCOMPLETE', error=type(e).__name__+': '+str(e), fitting_invoked=False)
    result.update(run_id=a['run_id'], code_commit=a['code_commit'], worker_pid=os.getpid())
    (out/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['status'] == 'REPLAY_ARITHMETIC_MATCH' else 1


if __name__ == '__main__':
    raise SystemExit(main())
