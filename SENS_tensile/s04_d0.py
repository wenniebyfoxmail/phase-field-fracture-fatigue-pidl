"""D0: nested whole-trajectory, causal direct-field closed-form ridge diagnostic.

No training loop, NN, producer mutation, clipping, event features or lifetime input.
Execute only through s04_d0_guard.py after exact independent code review.
"""
import argparse
import csv
import hashlib
import itertools
import json
import os
from pathlib import Path
import time

import numpy as np
from scipy.io import loadmat
from s04_g5_features import FeaturePipeline, FIELDS, sanity

TARGETS = ('damage', 'alpha_bar', 'psi_raw_direct')
ALPHAS = (.01, 1., 100.)
RUN_ID = 'S04-E016-D0-R002'
LOCK_SHA = 'cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c'
START = time.monotonic()


def check():
    if time.monotonic()-START > 295:
        raise RuntimeError('D0 wall budget exhausted; no restart')


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def cycle_weights(n):
    strata = np.minimum((np.arange(n)//20), 2)
    return np.array([1/(3*np.sum(strata == s)) for s in strata])


def transform(v, scales):
    assert np.isfinite(v).all() and np.all(v[:, 1:] >= 0)
    z = np.column_stack((v[:, 0], np.log1p(v[:, 1]/scales[0]),
                         np.log1p(v[:, 2]/scales[1])))
    assert np.isfinite(z).all(), 'Nonfinite transformed target'
    return z


def inverse(z, scales):
    with np.errstate(over='raise', invalid='raise'):
        v = np.column_stack((z[:, 0], np.expm1(z[:, 1])*scales[0],
                              np.expm1(z[:, 2])*scales[1]))
    assert np.isfinite(v).all()
    return v


def targets(case, cycle, ids, source):
    return np.column_stack([case[source][k][cycle-1, ids] for k in TARGETS]).astype(np.float64)


def scales_from_training(cases, train, pipeline):
    # Full admitted-domain PIN-only scales; equal case and fixed strata.
    area = pipeline.areas/pipeline.areas.sum()
    sums = np.zeros(2)
    for key in train:
        c = cases[key]
        for cycle, weight in enumerate(cycle_weights(c['n']), 1):
            check()
            sums += weight*np.array([np.dot(c['pin'][k][cycle-1, pipeline.ids], area)
                                      for k in ('alpha_bar', 'psi_raw_direct')])/len(train)
    assert np.isfinite(sums).all() and np.all(sums > 1e-12), 'Unidentified PIN scale'
    return sums


def training_blocks(cases, train, pipeline, sample, scales):
    """One cycle only; no lists retained across yields or trajectories."""
    area = pipeline.areas[sample]; area = area/area.sum()
    ids = pipeline.ids[sample]
    for key in train:
        c = cases[key]
        for cycle, weight in enumerate(cycle_weights(c['n']), 1):
            check()
            x = pipeline.trajectory_cycle(c['pin'], cycle, c['umax'], scales, sample)
            y = (transform(targets(c, cycle, ids, 'fem'), scales)
                 - transform(targets(c, cycle, ids, 'pin'), scales))
            yield x, y, area*weight/len(train)


def merge_moments(state, values, weights):
    """Stable centered block moments, then weighted parallel-Welford merge."""
    mass = float(weights.sum())
    assert mass > 0 and np.all(weights > 0) and np.isfinite(weights).all()
    assert np.isfinite(values).all()
    anchor = values[0]
    mean = anchor + np.sum(weights[:, None]*(values-anchor), axis=0)/mass
    m2 = np.sum(weights[:, None]*(values-mean)**2, axis=0)
    if state is None: return mass, mean, m2
    old_mass, old_mean, old_m2 = state
    total = old_mass+mass; delta = mean-old_mean
    return (total, old_mean+delta*(mass/total),
            old_m2+m2+delta**2*(old_mass*mass/total))


def fit_streamed(blocks, audit=False):
    """Factory is traversed twice; memory depends on one block, not cycle count."""
    sx = sy = None
    for x, y, w in blocks():
        check()
        sx = merge_moments(sx, x, w); sy = merge_moments(sy, y, w)
    assert sx is not None and np.isclose(sx[0], 1.) and np.isclose(sy[0], 1.)
    xm, ym = sx[1], sy[1]
    # Raw normalized training weights are unchanged; use weighted sums, as dense.
    xstd = np.sqrt(sx[2]); ystd = np.sqrt(sy[2])
    assert all(np.isfinite(v).all() for v in (xm, ym, xstd, ystd)), 'Nonfinite normalizer'
    xstd[xstd < 1e-12] = 1.; ystd[ystd < 1e-12] = 1.
    gram = np.zeros((33, 33)); cross = np.zeros((33, 3)); mass = 0.
    for x, y, w in blocks():
        check()
        assert x.shape[1] == 32 and y.shape == (len(x), 3)
        design = np.column_stack((np.ones(len(x)), (x-xm)/xstd))
        gram += design.T@(w[:, None]*design)
        cross += design.T@(w[:, None]*((y-ym)/ystd))
        mass += w.sum()
    assert np.isclose(mass, sx[0])
    assert np.isfinite(gram).all() and np.isfinite(cross).all(), 'Nonfinite Gram matrix'
    penalty = np.eye(33); penalty[0, 0] = 0.
    coefficients = [np.linalg.solve(gram+a*penalty, cross) for a in ALPHAS]
    assert all(np.isfinite(v).all() for v in coefficients), 'Nonfinite ridge coefficients'
    result = dict(xm=xm, xstd=xstd, ym=ym, ystd=ystd, coefficients=coefficients)
    if audit: result.update(gram=gram, cross=cross)  # Test-only matrices; no output/schema change in production.
    return result


def fit(cases, train, pipeline, sample):
    scales = scales_from_training(cases, train, pipeline)
    model = fit_streamed(lambda: training_blocks(cases, train, pipeline, sample, scales))
    return dict(train=list(train), scales=scales, **model)


def evaluate(cases, key, model, pipeline, candidates, rows=None, snapshot=None):
    c = cases[key]; area = pipeline.areas/pipeline.areas.sum()
    scores = np.zeros((len(candidates), 3)); base = np.zeros(3)
    for cycle, weight in enumerate(cycle_weights(c['n']), 1):
        check()
        pin = targets(c, cycle, pipeline.ids, 'pin')
        fem = targets(c, cycle, pipeline.ids, 'fem')
        zp, zf = transform(pin, model['scales']), transform(fem, model['scales'])
        x = pipeline.trajectory_cycle(c['pin'], cycle, c['umax'], model['scales'])
        x -= model['xm']; x /= model['xstd']
        x = np.column_stack((np.ones(len(x)), x))
        bz = area@((zp-zf)**2); bp = area@((pin-fem)**2)
        assert np.isfinite(bz).all() and np.isfinite(bp).all(), 'Nonfinite B0 score'
        base += weight*bz
        for i, aidx in enumerate(candidates):
            z = zp+(x@model['coefficients'][aidx])*model['ystd']+model['ym']
            assert np.isfinite(z).all(), 'Nonfinite corrected transformed prediction'
            mse = area@((z-zf)**2); scores[i] += weight*mse
            assert np.isfinite(mse).all() and np.isfinite(scores).all(), 'Nonfinite B1 score'
            if rows is not None:
                pred = inverse(z, model['scales'])
                physical = area@((pred-fem)**2)
                assert np.isfinite(physical).all(), 'Nonfinite B1 physical score'
                bounds = [((pred[:, 0] < 0)|(pred[:, 0] > 1)),
                          pred[:, 1] < 0, pred[:, 2] < 0]
                for j, field in enumerate(TARGETS):
                    rows.append(dict(holdout=key, cycle=cycle, stratum=min((cycle-1)//20, 2),
                                     field=field, alpha=ALPHAS[aidx], cycle_weight=weight,
                                     B0_transformed_mse=bz[j], B1_transformed_mse=mse[j],
                                     B0_physical_mse=bp[j], B1_physical_mse=physical[j],
                                     bound_violation_area=float(area@bounds[j]),
                                     B0_min=float(pin[:, j].min()), B0_max=float(pin[:, j].max()),
                                     B0_below_zero_count=int(np.sum(pin[:, j] < 0)),
                                     B0_above_one_count=int(np.sum(pin[:, j] > 1)) if j == 0 else 0,
                                     B0_bound_area=float(area@(((pin[:, j] < 0)|(pin[:, j] > 1)) if j == 0 else (pin[:, j] < 0))),
                                     B1_min=float(pred[:, j].min()), B1_max=float(pred[:, j].max())))
                if snapshot is not None and cycle == 20:
                    np.savez(snapshot, ids=pipeline.ids, pin=pin, fem=fem, B1=pred)
    assert np.isfinite(scores).all() and np.isfinite(base).all()
    return scores, base


def ratio(candidate, baseline):
    assert np.isfinite(candidate).all() and np.isfinite(baseline).all()
    assert np.all(baseline > 1e-24), 'Unidentified B0 error; stop, no denominator rescue'
    value = candidate/baseline
    assert np.isfinite(value).all(), 'Nonfinite error ratio'
    return value


def load_inputs(root, lock_path):
    assert sha(lock_path) == LOCK_SHA
    lock = json.loads(lock_path.read_text())
    mapping_path = root/lock['geometry']['path']
    assert sha(mapping_path) == lock['geometry']['sha256']
    with np.load(mapping_path) as g:
        pipeline = FeaturePipeline(g['centers'], g['areas'], g['contained'])
    assert len(pipeline.ids) == 85112
    assert sha(root/lock['feature_module']) == lock['feature_sha256']
    cases = {}
    for item in lock['trajectories']:
        check()
        n = item['common_pre_cycle_end_candidate']
        assert n == min(item['pin_first_cycle'], item['fem_first_cycle'])-1
        ppath, fpath = root/item['pin_path'], root/item['fem_path']
        assert sha(ppath) == item['pin_sha256'] and sha(fpath) == item['fem_sha256']
        with np.load(ppath) as p:
            assert np.array_equal(p['cycles'][:n].ravel(), np.arange(1, n+1))
            assert np.array_equal(p['raw_steps'][:n].ravel(), 5*np.arange(1, n+1)-1)
            pin = {k: p[k][:n] for k in FIELDS}
        f = loadmat(fpath, variable_names=[*TARGETS, 'cycles'])
        assert np.array_equal(f['cycles'].ravel()[:n], np.arange(1, n+1))
        fem = {k: f[k][:n] for k in TARGETS}
        for k, a in {**fem}.items():
            assert a.shape == (n, 86408) and np.isfinite(a).all() and np.all(a >= 0)
            if k == 'damage': assert np.all(a <= 1)
        for a in pin.values(): assert a.shape == (n, 86408)
        cases[item['id']] = dict(pin=pin, fem=fem, n=n, umax=item['umax'])
    assert set(cases) == {'u011', 'u012', 'u013', 'u0115'}
    return cases, pipeline


def jsonable(model):
    return {k: ([a.tolist() for a in v] if k == 'coefficients' else
                v.tolist() if isinstance(v, np.ndarray) else v) for k, v in model.items()}


def run(root, out):
    out.mkdir(exist_ok=False, parents=True)
    cases, pipeline = load_inputs(root, root/'docs/research/S04/S04-E016/paired_s4_lock_candidate_20261013.json')
    # Sorted geometry-only IDs; systematic spread, no label/ranking/seed selection.
    sample = np.linspace(0, len(pipeline.ids)-1, 2048, dtype=int)
    inner, selection, metrics, models = {}, [], [], {}
    keys = sorted(cases)
    for pair in itertools.combinations(keys, 2):
        model = fit(cases, pair, pipeline, sample)
        for val in sorted(set(keys)-set(pair)):
            scores, base = evaluate(cases, val, model, pipeline, range(3))
            inner[(pair, val)] = ratio(scores, base)
        models['inner_'+ '_'.join(pair)] = jsonable(model)
        print('inner fit', pair, flush=True)
    for held in keys:
        train = tuple(k for k in keys if k != held)
        means = np.mean([inner[(tuple(k for k in train if k != val), val)] for val in train], axis=0)
        objective = means.max(axis=1)
        assert np.isfinite(means).all() and np.isfinite(objective).all()
        best = min(range(3), key=lambda j: (objective[j], -ALPHAS[j]))
        selection.append(dict(holdout=held, train=list(train), inner_channel_MSE_ratios=means.tolist(),
                              minimax_objectives=objective.tolist(), selected_alpha=ALPHAS[best]))
        model = fit(cases, train, pipeline, sample)
        models['outer_'+held] = jsonable(model)
        evaluate(cases, held, model, pipeline, [best], metrics,
                 out/(held+'_C20.npz'))
        print('outer holdout', held, 'alpha', ALPHAS[best], flush=True)
    with open(out/'percycle.csv', 'w') as f:
        w = csv.DictWriter(f, fieldnames=list(metrics[0])); w.writeheader(); w.writerows(metrics)
    (out/'selection.json').write_text(json.dumps(selection, indent=2))
    (out/'models.json').write_text(json.dumps(models, indent=2))
    (out/'receipt.json').write_text(json.dumps(dict(status='COMPLETED', run_id=RUN_ID,
        lock_sha256=LOCK_SHA, elapsed_seconds=time.monotonic()-START, pid=os.getpid(),
        scope='retrospective horizon0 archive imitation only', code_commit=os.environ['D0_COMMIT'],
        sample_ids=sample.tolist(), feature_names=pipeline.names), indent=2))


def tests():
    sanity()
    for n in (55, 82, 99, 121):
        w = cycle_weights(n); assert np.isclose(w.sum(), 1)
        for s in range(3): assert np.isclose(w[np.minimum(np.arange(n)//20, 2) == s].sum(), 1/3)
    a = np.array([[-.01, 0., 1.], [1.01, 2., 0.]])
    assert np.allclose(inverse(transform(a, (2., 3.)), (2., 3.)), a)
    # Algebraic weighted solve equals direct closed-form solution, including intercept.
    rng = np.random.default_rng(4); x = rng.normal(size=(40, 5)); y = rng.normal(size=(40, 3))
    w = np.full(40, 1/40); d = np.column_stack((np.ones(40), x))
    p = np.eye(6); p[0, 0] = 0
    b = np.linalg.solve(d.T@(w[:, None]*d)+p, d.T@(w[:, None]*y))
    assert np.allclose((d.T@(w[:, None]*d)+p)@b, d.T@(w[:, None]*y))
    try: ratio(np.ones(3), np.zeros(3))
    except AssertionError: pass
    else: raise AssertionError('zero denominator accepted')
    pipeline = FeaturePipeline(np.column_stack((np.arange(10)/10, np.zeros(10))),
                               np.ones(10), np.array([True]*9+[False]))
    cases = {}
    for key, u in [('a', .11), ('b', .12), ('held', .13)]:
        pin = {k: np.ones((41, 10))*(.1+u) for k in FIELDS}
        fem = {k: pin[k]*1.1 for k in TARGETS}
        cases[key] = dict(pin=pin, fem=fem, n=41, umax=u)
    before = fit(cases, ('a', 'b'), pipeline, np.arange(9))
    for v in cases['held']['pin'].values(): v[:] = 1e9
    for v in cases['held']['fem'].values(): v[:] = 1e9
    after = fit(cases, ('a', 'b'), pipeline, np.arange(9))
    for k in ('scales', 'xm', 'xstd', 'ym', 'ystd', 'coefficients'):
        assert np.array_equal(before[k], after[k]), 'Holdout leakage'
    print('PASS heldout perturbation leaves fit/scales unchanged (toy only)')
    print('PASS weights, transforms, ridge algebra, unidentified denominator')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--test', action='store_true'); p.add_argument('--out')
    a = p.parse_args()
    if a.test: tests()
    else: run(Path(__file__).resolve().parents[1], Path(a.out))
