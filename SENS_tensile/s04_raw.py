"""45b8d32 physical-raw V0/V1 implementation. Import is inert; real CLI is gated."""
import argparse
import csv
import itertools
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np
from s04_g5_features import FIELDS
from s04_d0 import cycle_weights, merge_moments, load_inputs, jsonable, LOCK_SHA

ALPHAS = (.01, 1., 100.)
EPS = 1e-10
DESIGN = '45b8d32'
ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT/'docs/research/S04/S04-E016/paired_s4_lock_candidate_20261013.json'


class Terminal(RuntimeError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def require(ok, message, status='INVALID_INPUT'):
    if not ok:
        raise Terminal(status, message)


def finite(*values):
    require(all(np.isfinite(v).all() for v in values), 'nonfinite value', 'INVALID_NUMERICS')


def budget():
    if 'RAW_START_MONOTONIC' in os.environ:
        require(time.monotonic()-float(os.environ['RAW_START_MONOTONIC']) < 295,
                'internal wall reserve', 'INCONCLUSIVE_INCOMPLETE')


def admissible(pin):
    finite(pin)
    require(pin.ndim == 2 and pin.shape[1] == 3, 'output shape')
    return np.column_stack((np.clip(pin[:, 0], 0., 1.), np.maximum(pin[:, 1:], 0.)))


def check_outputs(v0, v1):
    finite(v0, v1)
    for v in (v0, v1):
        require(np.all((v[:, 0] >= 0) & (v[:, 0] <= 1)) and np.all(v[:, 1:] >= 0),
                'mapped output bounds', 'INVALID_IMPLEMENTATION')
    require(np.array_equal(v0[:, :2], v1[:, :2]), 'd/history changed', 'INVALID_IMPLEMENTATION')


def mapped(pin, residual_physical):
    finite(pin, residual_physical)
    v0 = admissible(pin)
    with np.errstate(over='raise', invalid='raise'):
        latent = pin[:, 2]+residual_physical
    finite(latent)  # In particular: do not let max(0,-Inf) hide an error.
    v1 = v0.copy(); v1[:, 2] = np.maximum(0., latent)
    check_outputs(v0, v1)
    return v0, v1


def source(c, cycle, ids, kind):
    v = np.column_stack([c[kind][k][cycle-1, ids] for k in
                         ('damage', 'alpha_bar', 'psi_raw_direct')]).astype(np.float64)
    finite(v)
    require(np.all(v[:, 1:] >= 0), 'source history/raw bounds')
    if kind == 'fem':
        require(np.all((v[:, 0] >= 0) & (v[:, 0] <= 1)), 'FEM damage bounds')
    return v


def features(c, cycle, pipeline, scales, sample=None):
    try:
        x = pipeline.trajectory_cycle(c['pin'], cycle, c['umax'], scales, sample)
    except AssertionError as e:
        raise Terminal('INVALID_INPUT', 'causal feature/source contract') from e
    finite(x)
    return x


def scales(cases, train, pipeline):
    require(len(train) > 0 and len(set(train)) == len(train), 'training identity')
    weights = pipeline.areas/pipeline.areas.sum()
    finite(weights)
    require(np.all(weights > 0), 'native area weights')
    total = np.zeros(2)
    for key in train:
        c = cases[key]
        for cycle, w in enumerate(cycle_weights(c['n']), 1):
            budget()
            for j, field in enumerate(('alpha_bar', 'psi_raw_direct')):
                v = c['pin'][field][cycle-1, pipeline.ids].astype(np.float64)
                finite(v); require(np.all(v >= 0), 'training PIN scale source bounds')
                total[j] += w*np.sum(weights*v)/len(train)
    finite(total)
    require(np.all(total > 1e-12), 'unidentified h/r input scale')
    return total


def training_blocks(cases, train, pipeline, sample, hr):
    area = pipeline.areas[sample]; area = area/area.sum()
    ids = pipeline.ids[sample]
    for key in train:
        c = cases[key]
        for cycle, w in enumerate(cycle_weights(c['n']), 1):
            budget()
            x = features(c, cycle, pipeline, hr, sample)
            p = source(c, cycle, ids, 'pin'); f = source(c, cycle, ids, 'fem')
            y = ((f[:, 2]-p[:, 2])/hr[1])[:, None]
            finite(y)
            yield x, y, area*w/len(train)


def fit_blocks(factory, audit=False):
    """Same weighted moments + normalized Gram, one scalar physical target."""
    sx = sy = None
    for x, y, w in factory():
        budget(); finite(x, y, w)
        require(x.shape == (len(w), 32) and y.shape == (len(w), 1), 'fit block shape')
        require(np.all(w > 0), 'fit weights')
        sx = merge_moments(sx, x, w); sy = merge_moments(sy, y, w)
        finite(*sx, *sy)
    require(sx is not None and sy is not None, 'empty fit')
    require(abs(sx[0]-1.) < 1e-12 and abs(sy[0]-1.) < 1e-12, 'fit mass')
    xm, ym = sx[1], sy[1]
    require(np.all(sx[2] >= 0) and np.all(sy[2] >= 0), 'negative centered moment', 'INVALID_NUMERICS')
    xs, ys = np.sqrt(sx[2]), np.sqrt(sy[2]); finite(xs, ys)
    xs[xs < 1e-12] = 1.; ys[ys < 1e-12] = 1.
    gram = np.zeros((33, 33)); cross = np.zeros((33, 1)); mass = 0.
    for x, y, w in factory():
        budget(); finite(x, y, w)
        require(x.shape == (len(w), 32) and y.shape == (len(w), 1) and np.all(w > 0), 'second-pass block')
        d = np.column_stack((np.ones(len(x)), (x-xm)/xs)); z = (y-ym)/ys
        finite(d, z)
        # Explicit contractions avoid the platform matmul warning path seen in the dense oracle.
        gram += np.einsum('ni,n,nj->ij', d, w, d, optimize=False)
        cross += np.einsum('ni,n,nj->ij', d, w, z, optimize=False)
        finite(gram, cross); mass += float(w.sum())
    require(abs(mass-sx[0]) < 1e-12, 'second-pass mass')
    penalty = np.eye(33); penalty[0, 0] = 0
    coefficients = [np.linalg.solve(gram+a*penalty, cross) for a in ALPHAS]
    finite(*coefficients)
    model = dict(xm=xm, ym=ym, xstd=xs, ystd=ys, coefficients=coefficients)
    if audit:
        model.update(gram=gram, cross=cross)
    return model


def fit(cases, train, pipeline, sample):
    hr = scales(cases, train, pipeline)
    model = fit_blocks(lambda: training_blocks(cases, train, pipeline, sample, hr))
    return dict(train=list(train), scales=hr, **model)


def mse(error, weights):
    finite(error, weights)
    with np.errstate(over='raise', invalid='raise'):
        value = float(np.sum(weights*error**2))
    finite(value)
    require(value >= 0, 'negative MSE', 'INVALID_NUMERICS')
    return value


def ratios(scores, base):
    finite(scores, base)
    require(np.all(scores >= 0) and np.all(base >= 0), 'negative score', 'INVALID_NUMERICS')
    # shape (candidate, stratum); every baseline is required, no floor rescue.
    require(np.mean(base) > 1e-24 and base[0] > 1e-24,
            'unidentified all/early denominator', 'INCONCLUSIVE_UNIDENTIFIED')
    r = np.sqrt(scores.mean(axis=1)/base.mean()); g = np.sqrt(scores[:, 0]/base[0])
    finite(r, g)
    return r, g


def select(inner_r, inner_g):
    finite(inner_r, inner_g)
    require(inner_r.shape == inner_g.shape == (3, 3), 'three validations x three alphas')
    eligible = np.all(inner_g <= 1+EPS, axis=0)
    objective = np.max(inner_r, axis=0)
    choices = np.flatnonzero(eligible).tolist()
    best = min(choices, key=lambda j: (objective[j], -ALPHAS[j])) if choices else None
    if best is None:
        return None, 'NO_EARLY_ELIGIBLE_ALPHA', objective, eligible
    if objective[best] >= 1-EPS:
        return None, 'NO_STRICT_INNER_GAIN', objective, eligible
    return best, 'LEARNED_SELECTED', objective, eligible


def decision(records):
    require(len(records) == 4 and len({r['holdout'] for r in records}) == 4,
            'all four outer folds required')
    r = np.array([v['R'] for v in records]); g = np.array([v['G'] for v in records]); finite(r, g)
    require(np.all(r >= 0) and np.all(g >= 0), 'negative ratio', 'INVALID_NUMERICS')
    for row in records:
        if row['fallback']:
            require(row['R'] == row['G'] == 1., 'fallback must be exact V0', 'INVALID_IMPLEMENTATION')
    q = float(r.max())
    if np.any(g > 1+EPS): status = 'EARLY_REGRESSION'
    elif q > 1+EPS: status = 'RAW_REGRESSION'
    elif q < 1-EPS: status = 'DIRECTIONAL_DEVELOPMENT_GAIN'
    else: status = 'NUMERICAL_TIE'
    return dict(status=status, Q=q, folds=records,
                all_fallback=all(v['fallback'] for v in records),
                label='NO_SELECTED_LEARNED_CORRECTION' if all(v['fallback'] for v in records) else status)


def evaluate(cases, key, model, pipeline, candidates, rows=None, snapshot=None):
    """One cycle at a time; candidates=[None] is preselected whole-case V0."""
    c = cases[key]; area = pipeline.areas/pipeline.areas.sum()
    base = np.zeros(3); scores = np.zeros((len(candidates), 3))
    for cycle, weight in enumerate(cycle_weights(c['n']), 1):
        budget(); s = min((cycle-1)//20, 2)
        p = source(c, cycle, pipeline.ids, 'pin'); f = source(c, cycle, pipeline.ids, 'fem')
        v0 = admissible(p); b = mse(v0[:, 2]-f[:, 2], area); base[s] += 3*weight*b
        design = None
        if model is not None:
            x = features(c, cycle, pipeline, model['scales'])
            design = np.column_stack((np.ones(len(x)), (x-model['xm'])/model['xstd']))
            finite(design)
        for j, ai in enumerate(candidates):
            if ai is None:
                v1 = v0.copy(); check_outputs(v0, v1)
            else:
                require(model is not None and ai in range(3), 'prediction model')
                t = np.einsum('ij,j->i', design, model['coefficients'][ai][:, 0], optimize=False)
                t = t*model['ystd'][0]+model['ym'][0]; finite(t)
                v0, v1 = mapped(p, model['scales'][1]*t)
            error = mse(v1[:, 2]-f[:, 2], area); scores[j, s] += 3*weight*error
            if rows is not None:
                rows.append(dict(holdout=key, cycle=cycle, stratum=s, cycle_weight=float(weight),
                    fallback=ai is None, selected_alpha=None if ai is None else ALPHAS[ai],
                    V0_physical_mse=b, V1_physical_mse=error,
                    V0_raw_min=float(v0[:, 2].min()), V1_raw_min=float(v1[:, 2].min()),
                    V0_raw_max=float(v0[:, 2].max()), V1_raw_max=float(v1[:, 2].max()),
                    raw_negative_area=float(np.sum(area*(v1[:, 2] < 0))),
                    damage_history_identical=bool(np.array_equal(v0[:, :2], v1[:, :2])),
                    PIN_damage_min=float(p[:, 0].min()), PIN_damage_max=float(p[:, 0].max())))
            if snapshot is not None and cycle == 20:
                np.savez(snapshot, ids=pipeline.ids, fem=f, V0=v0, V1=v1)
    finite(scores, base)
    r, g = ratios(scores, base)
    return r, g


def pipeline_run(cases, pipeline, out, sample_count=2048):
    keys = sorted(cases); require(len(keys) == 4, 'four trajectories')
    sample = np.linspace(0, len(pipeline.ids)-1, min(sample_count, len(pipeline.ids)), dtype=int)
    inner = {}; models = {}; selections = []; rows = []; folds = []
    for pair in itertools.combinations(keys, 2):
        model = fit(cases, pair, pipeline, sample)
        for val in sorted(set(keys)-set(pair)):
            inner[pair, val] = evaluate(cases, val, model, pipeline, range(3))
        models['inner_'+'_'.join(pair)] = jsonable(model)
        print('inner', pair, flush=True)
    for held in keys:
        train = tuple(k for k in keys if k != held)
        rr, gg = zip(*(inner[tuple(k for k in train if k != val), val] for val in train))
        ai, reason, objectives, eligible = select(np.array(rr), np.array(gg))
        selections.append(dict(holdout=held, train=list(train), inner_R=np.array(rr).tolist(),
            inner_G=np.array(gg).tolist(), objectives=objectives.tolist(), eligible=eligible.tolist(),
            reason=reason, selected_alpha=None if ai is None else ALPHAS[ai]))
        model = fit(cases, train, pipeline, sample) if ai is not None else None
        models['outer_'+held] = None if model is None else jsonable(model)
        r, g = evaluate(cases, held, model, pipeline, [ai], rows,
                         out/'u0115_C20.npz' if held == 'u0115' else None)
        folds.append(dict(holdout=held, fallback=ai is None, R=float(r[0]), G=float(g[0])))
        print('outer', held, reason, flush=True)
    with (out/'percycle.csv').open('x') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    for name, value in [('models', models), ('selection', selections), ('decision', decision(folds))]:
        (out/(name+'.json')).write_text(json.dumps(value, indent=2, allow_nan=False))
    return dict(sample_ids=sample.tolist(), feature_names=pipeline.names, rows=len(rows))


def authorization(path, out):
    """An execution interlock, not proof of human consent. No such file is made by tests."""
    require(path is not None, 'separate reviewed real-run authorization required')
    a = json.loads(Path(path).read_text())
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    required = dict(user_approved_real_fit=True, independent_code_review='APPROVED',
                    code_commit=commit, design_commit=DESIGN, lock_sha256=LOCK_SHA,
                    output=str(out.resolve()))
    require(all(a.get(k) == v for k, v in required.items()), 'authorization/code/output mismatch')
    exp = a.get('experiment_id', ''); run = a.get('run_id', '')
    require(exp.startswith('S04-E') and exp not in ('S04-E016', 'S04-E017') and
            run.startswith(exp+'-') and out.name == run, 'new experiment/run identity required')
    require(subprocess.check_output(['git', 'diff', DESIGN, '--',
        'docs/research/S04/S04-E016/design_revision_raw_physical_v2_20261015.md'],
        cwd=ROOT, text=True) == '', 'reviewed design changed')
    paths = ['SENS_tensile/'+name for name in ('s04_raw.py', 's04_raw_guard.py',
        's04_raw_report.py', 's04_raw_checks.py', 's04_d0.py', 's04_g5_features.py')]
    require(subprocess.check_output(['git', 'status', '--porcelain', '--', *paths],
        cwd=ROOT, text=True) == '', 'reviewed source must be tracked and clean')
    return a


def main():
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--authorization', type=Path, required=True); a = p.parse_args()
    auth = authorization(a.authorization, a.out)
    require(os.environ.get('RAW_RUN_ID') == auth['run_id'] and
            os.environ.get('RAW_CODE_COMMIT') == auth['code_commit'] and
            'RAW_START_MONOTONIC' in os.environ, 'invoke through reviewed guard')
    a.out.mkdir(parents=True, exist_ok=False)
    try:
        try:
            cases, pipeline = load_inputs(ROOT, LOCK)
        except AssertionError as e:
            raise Terminal('INVALID_INPUT', 'frozen loader identity/admission: '+str(e)) from e
        info = pipeline_run(cases, pipeline, a.out)
        status = 'COMPLETED'
    except (Terminal, AssertionError, FloatingPointError, OverflowError, np.linalg.LinAlgError) as e:
        info = dict(message=str(e)); status = getattr(e, 'status', 'INVALID_NUMERICS')
    record = dict(status=status, run_id=auth['run_id'], code_commit=auth['code_commit'],
                  design_commit=DESIGN, lock_sha256=LOCK_SHA, mode='real', pid=os.getpid(), **info)
    (a.out/'receipt.json').write_text(json.dumps(record, indent=2, allow_nan=False))
    return 0 if status == 'COMPLETED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
