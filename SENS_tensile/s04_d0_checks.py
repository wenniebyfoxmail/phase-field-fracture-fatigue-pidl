"""Preflight engineering tests only; actual archive mode never fits/scores."""
import argparse
import itertools
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import types

import numpy as np
import s04_d0 as new
from s04_g5_features import FeaturePipeline, FIELDS


def old_module():
    code = subprocess.check_output(['git', 'show', 'cb86a118:SENS_tensile/s04_d0.py'], text=True)
    module = types.ModuleType('frozen_dense_oracle')
    module.__file__ = str(Path(new.__file__).resolve())
    exec(compile(code, 'cb86a118:s04_d0.py', 'exec'), module.__dict__)
    return module


def close(a, b, kind, errors):
    rt, at = (1e-7, 1e-9) if kind == 'coefficients' else ((1e-8, 1e-9) if kind == 'prediction' else (1e-9, 1e-11))
    aa, bb = np.asarray(a), np.asarray(b)
    assert np.isfinite(aa).all() and np.isfinite(bb).all()
    assert np.allclose(aa, bb, rtol=rt, atol=at), (kind, np.max(np.abs(aa-bb)))
    errors[kind] = max(errors.get(kind, 0.), float(np.max(np.abs(aa-bb))))


def toy_cases():
    points = np.column_stack((np.linspace(-.5, .5, 202), np.sin(np.arange(202))*.1))
    pipeline = FeaturePipeline(points, np.linspace(.1, 2, 202), np.array([True]*201+[False]))
    cases = {}
    space = np.linspace(0, 1, 202)[None, :]; cycle = np.arange(1, 42)[:, None]
    for key, u in [('u011', .11), ('u0115', .115), ('u012', .12), ('u013', .13)]:
        pin = dict(damage=.1+u+space*.12+cycle*.0003,
                   alpha_bar=(.2+space+cycle*.01)*(u/.11),
                   fatigue_f=np.broadcast_to(.8-space*.2, (41, 202)).copy(),
                   psi_raw_direct=(.1+space**2+cycle*.003)*(u/.11)**2)
        pin['damage'][0, 0] = -.0002
        fem = {k: pin[k]+(.01+space*.02)*(u/.11) for k in new.TARGETS}
        for value in pin.values(): value[:, -1] = np.nan
        cases[key] = dict(pin=pin, fem=fem, n=41, umax=u)
    return cases, pipeline


def equivalence():
    old = old_module(); errors = {}; keys = ['u011', 'u0115', 'u012', 'u013']
    new.tests()
    # Pure algebra with unequal weights, exact constants and both sides of std floor.
    rng = np.random.default_rng(782)
    x = rng.normal(size=(311, 32)); y = rng.normal(size=(311, 3))
    x[:, 0] = 1.; x[:, 1] = 3.2; x[:, 2] *= 1e-13; x[:, 3] *= 3e-12
    w = rng.uniform(.01, 1., len(x)); w /= w.sum()
    def blocks():
        for sl in np.array_split(np.arange(len(x)), 7): yield x[sl].copy(), y[sl].copy(), w[sl].copy()
    stream = new.fit_streamed(blocks)
    xm, ym = w@x, w@y; xs = np.sqrt(w@((x-xm)**2)); ys = np.sqrt(w@((y-ym)**2))
    xs[xs < 1e-12] = 1.; ys[ys < 1e-12] = 1.
    d = np.column_stack((np.ones(len(x)), (x-xm)/xs)); penalty = np.eye(33); penalty[0, 0] = 0
    coefficients = [np.linalg.solve(d.T@(w[:, None]*d)+a*penalty,
                                    d.T@(w[:, None]*((y-ym)/ys))) for a in new.ALPHAS]
    for name, value in [('xm', xm), ('ym', ym), ('xstd', xs), ('ystd', ys)]:
        close(value, stream[name], name, errors)
    assert np.array_equal(xs == 1., stream['xstd'] == 1.)
    for b0, b1 in zip(coefficients, stream['coefficients']):
        close(b0, b1, 'coefficients', errors)
        close(d@b0*ys+ym, np.column_stack((np.ones(len(x)), (x-stream['xm'])/stream['xstd']))@b1*stream['ystd']+stream['ym'], 'prediction', errors)
    cases, pipeline = toy_cases(); sample = np.linspace(0, 200, 64, dtype=int)
    inner = [{}, {}]; outer_rows = [[], []]
    for pair in itertools.combinations(keys, 2):
        fitted = [m.fit(cases, pair, pipeline, sample) for m in (old, new)]
        for name in ('scales', 'xm', 'ym', 'xstd', 'ystd', 'coefficients'):
            close(fitted[0][name], fitted[1][name], name, errors)
        for val in sorted(set(keys)-set(pair)):
            for j, m in enumerate((old, new)):
                s, b = m.evaluate(cases, val, fitted[j], pipeline, range(3))
                inner[j][pair, val] = m.ratio(s, b)
            close(inner[0][pair, val], inner[1][pair, val], 'prediction', errors)
    selected = []
    for held in keys:
        train = tuple(k for k in keys if k != held); choices = []
        for j, m in enumerate((old, new)):
            means = np.mean([inner[j][tuple(k for k in train if k != val), val] for val in train], axis=0)
            objective = means.max(axis=1)
            best = min(range(3), key=lambda i: (objective[i], -new.ALPHAS[i])); choices.append(best)
            model = m.fit(cases, train, pipeline, sample)
            m.evaluate(cases, held, model, pipeline, [best], outer_rows[j])
        assert choices[0] == choices[1], 'Toy nested alpha selection changed'
        selected.append(dict(heldout=held, alpha=new.ALPHAS[choices[0]]))
    assert len(outer_rows[0]) == len(outer_rows[1]) == 4*41*3
    for r0, r1 in zip(*outer_rows):
        for name in ('B0_physical_mse', 'B1_physical_mse', 'B0_transformed_mse', 'B1_transformed_mse'):
            close(r0[name], r1[name], 'prediction', errors)
    tie = min(range(3), key=lambda i: (1., -new.ALPHAS[i])); assert new.ALPHAS[tie] == 100.
    return dict(status='PASS', mode='equivalence', max_absolute_differences=errors,
                nested_selected=selected, toy_outer_score_rows=len(outer_rows[0]), actual_fit=False)


def memory(root):
    cases, pipeline = new.load_inputs(root, root/'docs/research/S04/S04-E016/paired_s4_lock_candidate_20261013.json')
    owned = {}
    for c in cases.values():
        for source in ('pin', 'fem'):
            for a in c[source].values():
                while isinstance(a.base, np.ndarray): a = a.base
                owned[id(a)] = a.nbytes
    # Read-only dimension check: no fitted normalizer, no label access or scoring.
    x = pipeline.trajectory_cycle(cases['u0115']['pin'], 20, .115, (1., 1.))
    assert x.shape == (85112, 32); feature_bytes = x.nbytes; del x
    # Largest training block x twice303 cycles: synthetic only, never actual fit.
    def blocks():
        for i in range(303):
            rng = np.random.default_rng(i+42)
            yield rng.normal(size=(2048, 32)), rng.normal(size=(2048, 3)), np.full(2048, 1/(303*2048))
    new.fit_streamed(blocks)
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != 'darwin': rss *= 1024
    assert rss < 2*1024**3, 'Memory preflight exceeds original cap'
    return dict(status='PASS', mode='memory', peak_rss_bytes=rss,
                owned_source_array_bytes=sum(owned.values()), full_feature_bytes=feature_bytes,
                synthetic_blocks=303, synthetic_rows_per_block=2048,
                actual_fit=False, actual_score=False,
                limitation='source+full-feature+synthetic accumulation preflight, not full real-pipeline guarantee')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--mode', choices=['equivalence', 'memory'], required=True)
    p.add_argument('--out', required=True); a = p.parse_args(); start = time.monotonic()
    result = equivalence() if a.mode == 'equivalence' else memory(Path(__file__).resolve().parents[1])
    result['elapsed_seconds'] = time.monotonic()-start
    result['code_commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    destination = Path(a.out); assert not destination.exists(); destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2)); print(json.dumps(result, indent=2))
