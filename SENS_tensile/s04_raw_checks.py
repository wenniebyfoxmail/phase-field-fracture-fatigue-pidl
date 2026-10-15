"""Synthetic-only engineering: no real archive loading, fitting or scoring."""
import argparse
import gc
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time
from unittest import mock

import numpy as np
import s04_raw as raw
from s04_g5_features import FeaturePipeline, sanity


def prohibit_real_inputs():
    def deny(*args, **kwargs):
        raise RuntimeError('engineering process may not load real inputs')
    raw.load_inputs = deny
    def hook(event, args):
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            path = os.fsdecode(args[0])
            if any(s in path for s in ('g5_export_20261013', 'paired_s4_lock_candidate',
                'pidl_peak_trajectories_three_umax', 'u01175', 'u0125')):
                raise RuntimeError('real/confirmation input open forbidden: '+path)
    sys.addaudithook(hook)


def fixture(full=False):
    if full:
        nx, ny = 432, 201
        xx, yy = np.meshgrid(np.linspace(-.5, .5, nx+1), np.linspace(-.5, .5, ny+1))
        coordinates = np.column_stack((xx.ravel(), yy.ravel()))
        lo = (np.arange(ny)[:, None]*(nx+1)+np.arange(nx)[None, :]).ravel()[:86408]
        cells = np.column_stack((lo, lo+1, lo+nx+2, lo+nx+1))+1
        centers = coordinates[cells-1].mean(axis=1)
        areas = np.full(86408, 1/(nx*ny)); contained = np.arange(86408) < 85112
        counts = [121, 99, 82, 55]
    else:
        centers = np.column_stack((np.linspace(-.5, .5, 202), np.sin(np.arange(202))*.1))
        areas = np.linspace(.1, 2., 202); contained = np.arange(202) < 201
        coordinates = cells = None; counts = [41]*4
    pipeline = FeaturePipeline(centers, areas, contained)
    cases = {}; space = np.linspace(0, 1, len(areas), dtype=np.float32)
    for (key, u), n in zip((('u011', .11), ('u0115', .115), ('u012', .12), ('u013', .13)), counts):
        pin = {k: np.empty((n, len(areas)), dtype=np.float32) for k in raw.FIELDS}
        fem = {k: np.empty((n, len(areas)), dtype=np.float32) for k in
               ('damage', 'alpha_bar', 'psi_raw_direct')}
        for j in range(n):
            pin['damage'][j] = -.0001+space*.35+(j+1)*.0002
            pin['alpha_bar'][j] = .2+space+(j+1)*.01+u
            pin['fatigue_f'][j] = .8-space*.2
            pin['psi_raw_direct'][j] = .5+space**2+(j+1)*.003+u*2
            fem['damage'][j] = np.clip(pin['damage'][j]+.01, 0, 1)
            fem['alpha_bar'][j] = pin['alpha_bar'][j]+.03
            fem['psi_raw_direct'][j] = pin['psi_raw_direct'][j]+.15+space*.04+(j+1)*.0001
        cases[key] = dict(pin=pin, fem=fem, n=n, umax=u)
    mesh = None if not full else dict(coordinates=coordinates, cells=cells)
    return cases, pipeline, mesh


def dense(factory, audit=False):
    """Independent concatenated oracle, called ONLY on small generated fixtures."""
    blocks = list(factory()); x = np.concatenate([b[0] for b in blocks])
    y = np.concatenate([b[1] for b in blocks]); w = np.concatenate([b[2] for b in blocks])
    xm = np.sum(w[:, None]*x, axis=0); ym = np.sum(w[:, None]*y, axis=0)
    xs = np.sqrt(np.sum(w[:, None]*(x-xm)**2, axis=0))
    ys = np.sqrt(np.sum(w[:, None]*(y-ym)**2, axis=0))
    xs[xs < 1e-12] = 1.; ys[ys < 1e-12] = 1.
    d = np.column_stack((np.ones(len(x)), (x-xm)/xs)); z = (y-ym)/ys
    gram = d.T @ (w[:, None]*d); cross = d.T @ (w[:, None]*z)
    penalty = np.eye(33); penalty[0, 0] = 0
    result = dict(xm=xm, ym=ym, xstd=xs, ystd=ys,
                  coefficients=[np.linalg.solve(gram+a*penalty, cross) for a in raw.ALPHAS])
    if audit: result.update(gram=gram, cross=cross)
    return result


def unit(out):
    out.mkdir(parents=True, exist_ok=False)
    checked = []; differences = {}
    def close(a, b, name, rt=1e-7, at=1e-10):
        a, b = np.asarray(a), np.asarray(b); raw.finite(a, b)
        assert np.allclose(a, b, rtol=rt, atol=at), (name, np.max(np.abs(a-b)))
        differences[name] = max(differences.get(name, 0.), float(np.max(np.abs(a-b))))
    def terminal(call, status):
        try: call()
        except raw.Terminal as e: assert e.status == status, (e.status, status)
        else: raise AssertionError('expected terminal '+status)
    sanity(); checked.append('original causal feature whitelist/missing/future tests')
    rng = np.random.default_rng(3817); x = rng.normal(size=(311, 32)); y = rng.normal(size=(311, 1))
    x[:, 0] = 1.; x[:, 1] = 3.2; x[:, 2] *= 1e-13; x[:, 3] *= 3e-12
    w = rng.uniform(.01, 2, len(x)); w /= w.sum()
    def blocks():
        for ids in np.array_split(np.arange(len(x)), 7): yield x[ids].copy(), y[ids].copy(), w[ids].copy()
    stream = raw.fit_blocks(blocks, True); oracle = dense(blocks, True)
    for k in oracle: close(stream[k], oracle[k], k)
    assert np.array_equal(stream['xstd'] == 1., oracle['xstd'] == 1.)
    checked.append('weighted dense/stream oracle, unequal weights, constants and std floor')
    zeros = lambda: iter([(x, np.zeros((len(x), 1)), w)])
    model = raw.fit_blocks(zeros)
    assert np.array_equal(model['ystd'], [1.]) and all(np.all(c == 0) for c in model['coefficients'])
    pin = np.array([[-.001, .2, 1.], [1.01, .3, 2.]])
    v0, v1 = raw.mapped(pin, np.zeros(2)); assert np.array_equal(v0, v1)
    z = np.array([-1e8, -2., -1e-20, 0, .3, 2.]); ref = np.array([0., .1, 2., 0., .5, 3.])
    assert np.all((np.maximum(z, 0)-ref)**2 <= (z-ref)**2)
    refd = np.clip(ref, 0, 1)
    assert np.all((np.clip(z, 0, 1)-refd)**2 <= (z-refd)**2)
    checked.append('zero target/predicted residual identity, d/ab equality, projection inequality')
    for bad in (np.nan, np.inf, -np.inf):
        terminal(lambda: raw.mapped(pin, np.array([bad, 0.])), 'INVALID_NUMERICS')
        rr = np.full((3, 3), .9); rr[0, 0] = bad
        terminal(lambda: raw.select(rr, np.ones((3, 3))), 'INVALID_NUMERICS')
    broken = v1.copy(); broken[0, 2] = -1
    terminal(lambda: raw.check_outputs(v0, broken), 'INVALID_IMPLEMENTATION')
    broken = v1.copy(); broken[0, 0] = .5
    terminal(lambda: raw.check_outputs(v0, broken), 'INVALID_IMPLEMENTATION')
    terminal(lambda: raw.ratios(np.ones((1, 3)), np.array([0., 1., 1.])), 'INCONCLUSIVE_UNIDENTIFIED')
    with mock.patch.object(np.linalg, 'solve', side_effect=np.linalg.LinAlgError('injected')):
        try: raw.fit_blocks(blocks)
        except np.linalg.LinAlgError: pass
        else: raise AssertionError('solver error hidden')
    checked.append('NaN/Inf/-Inf, bounds/state corruption, denominator and solver errors never fallback')
    chosen, reason, _, _ = raw.select(np.full((3, 3), .9), np.full((3, 3), 1+raw.EPS))
    assert chosen == 2 and reason == 'LEARNED_SELECTED'
    g = np.full((3, 3), np.nextafter(1+raw.EPS, np.inf))
    assert raw.select(np.full((3, 3), .9), g)[:2] == (None, 'NO_EARLY_ELIGIBLE_ALPHA')
    assert raw.select(np.full((3, 3), 1-raw.EPS), np.ones((3, 3)))[:2] == (None, 'NO_STRICT_INNER_GAIN')
    def records(r, g=1., fallback=False):
        return [dict(holdout=str(i), R=r, G=g, fallback=fallback) for i in range(4)]
    for q in (1-raw.EPS, 1+raw.EPS): assert raw.decision(records(q))['status'] == 'NUMERICAL_TIE'
    assert raw.decision(records(.9, 1+raw.EPS))['status'] == 'DIRECTIONAL_DEVELOPMENT_GAIN'
    assert raw.decision(records(.9, np.nextafter(1+raw.EPS, np.inf)))['status'] == 'EARLY_REGRESSION'
    p = records(.8); p[0].update(R=1., fallback=True)
    assert raw.decision(p)['status'] == 'NUMERICAL_TIE'
    p[1]['R'] = 1.1; assert raw.decision(p)['status'] == 'RAW_REGRESSION'
    assert raw.decision(records(1., fallback=True))['label'] == 'NO_SELECTED_LEARNED_CORRECTION'
    checked.append('exact alpha tie, eps boundary, partial/all fallback and all-fold decision')
    terminal(lambda: raw.authorization(None, out/'MUST_NOT_EXIST'), 'INVALID_INPUT')
    assert not (out/'MUST_NOT_EXIST').exists()
    checked.append('real execution blocked before source access/output creation without separate approval')
    cases, pipeline, _ = fixture(); sample = np.linspace(0, 200, 64, dtype=int)
    a = raw.fit(cases, ('u011', 'u012'), pipeline, sample)
    area = pipeline.areas/pipeline.areas.sum()
    expected = [np.mean([sum(float(cw)*np.sum(area*cases[k]['pin'][f][c, pipeline.ids])
                  for c, cw in enumerate(raw.cycle_weights(cases[k]['n'])))
                  for k in ('u011', 'u012')]) for f in ('alpha_bar', 'psi_raw_direct')]
    close(a['scales'], expected, 'both_full_domain_scales', rt=1e-12)
    for source in ('pin', 'fem'):
        for arr in cases['u013'][source].values(): arr[:] = 1000
    b = raw.fit(cases, ('u011', 'u012'), pipeline, sample)
    for k in a:
        if k != 'train': assert np.array_equal(a[k], b[k]), k
    checked.append('heldout PIN/FEM perturbation leaves both scales/fit unchanged')
    cases, pipeline, _ = fixture()
    for c in cases.values():
        c['pin']['psi_raw_direct'][:] = 1.; c['fem']['psi_raw_direct'][:] = 2.
    constant = dict(scales=np.ones(2), xm=np.zeros(32), xstd=np.ones(32), ym=np.array([-2.]),
                    ystd=np.ones(1), coefficients=[np.zeros((33, 1)) for _ in range(3)])
    rr, gg = raw.evaluate(cases, 'u011', constant, pipeline, [0])
    close(rr, [2.], 'physical_after_map', rt=1e-12)
    close(gg, [2.], 'early_after_map', rt=1e-12)
    checked.append('physical scoring uses final map (R=2, not unmapped R=3)')
    cases, pipeline, _ = fixture()
    (out/'stream').mkdir(); (out/'dense').mkdir()
    raw.pipeline_run(cases, pipeline, out/'stream', sample_count=64)
    with mock.patch.object(raw, 'fit_blocks', side_effect=dense):
        raw.pipeline_run(cases, pipeline, out/'dense', sample_count=64)
    for filename in ('selection.json', 'decision.json'):
        aa = json.loads((out/'stream'/filename).read_text()); bb = json.loads((out/'dense'/filename).read_text())
        if filename == 'selection.json':
            assert [(x['selected_alpha'], x['reason']) for x in aa] == [(x['selected_alpha'], x['reason']) for x in bb]
        else:
            assert aa['status'] == bb['status']
            for a, b in zip(aa['folds'], bb['folds']): close([a['R'], a['G']], [b['R'], b['G']], 'nested_R_G')
    import csv
    aa = list(csv.DictReader((out/'stream'/'percycle.csv').open()))
    bb = list(csv.DictReader((out/'dense'/'percycle.csv').open()))
    assert len(aa) == len(bb) == 164
    for a, b in zip(aa, bb):
        close([float(a[k]) for k in ('V0_physical_mse', 'V1_physical_mse')],
              [float(b[k]) for k in ('V0_physical_mse', 'V1_physical_mse')], 'nested_percycle')
    checked.append('complete toy nested CV: same alpha/fallback/outcome and physical percycle scores')
    return dict(status='PASS', checks=checked, max_absolute_differences=differences,
                actual_inputs_opened=False, actual_fit=False, actual_score=False)


def synthetic_pipeline(out):
    out.mkdir(parents=True, exist_ok=False)
    cases, pipeline, mesh = fixture(full=True)
    # Conservative loader transient: three additional max-length source columns,
    # touched while every source-shaped array remains resident. No actual payload IO.
    scratch = np.ones((3, 122, 86408), dtype=np.float32)
    transient_sum = float(scratch.sum(dtype=np.float64)); del scratch; gc.collect()
    np.savez(out/'synthetic_mesh.npz', **mesh)
    info = raw.pipeline_run(cases, pipeline, out)
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != 'darwin': rss *= 1024
    record = dict(status='COMPLETED', run_id=os.environ['RAW_RUN_ID'],
        code_commit=os.environ['RAW_CODE_COMMIT'], design_commit=raw.DESIGN,
        mode='synthetic_engineering', pid=os.getpid(), peak_self_rss_bytes=rss,
        source_array_bytes=sum(v.nbytes for c in cases.values() for s in ('pin', 'fem') for v in c[s].values()),
        synthetic_cells=86408, scored_cells=85112, synthetic_cycles=357,
        loader_transient_sum=transient_sum, actual_inputs_opened=False,
        actual_fit=False, actual_score=False, **info)
    (out/'receipt.json').write_text(json.dumps(record, indent=2, allow_nan=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--synthetic-pipeline', action='store_true'); args = p.parse_args()
    prohibit_real_inputs(); start = time.monotonic()
    if args.synthetic_pipeline:
        synthetic_pipeline(args.out)
    else:
        result = unit(args.out)
        result.update(elapsed_seconds=time.monotonic()-start,
            code_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip())
        (args.out/'unit_receipt.json').write_text(json.dumps(result, indent=2, allow_nan=False))
        print(json.dumps(result, indent=2))
