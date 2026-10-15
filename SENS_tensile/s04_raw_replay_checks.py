"""Generated inference fixtures and virtual guard only. No fits or real sources."""
import argparse
import contextlib
import copy
import csv
import io
import json
import math
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest import mock

import numpy as np
import s04_d0
import s04_raw as oracle
import s04_raw_checks as generated
import s04_raw_replay as replay
import s04_raw_replay_guard as guard


def deny(*args, **kwargs):
    raise RuntimeError('real-source/fit/solver path forbidden in engineering')


def protect():
    def hook(event, args):
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            path = os.fsdecode(args[0])
            if any(s in path for s in ('g5_export_20261013', 'paired_s4_lock_candidate',
                    'pidl_peak_trajectories_three_umax', 'u01175', 'u0125',
                    '/S04-E021/runs/', '/S04-E021/control/')):
                raise RuntimeError('real evidence/source open forbidden: '+path)
    sys.addaudithook(hook)


def rejected(call):
    try: call()
    except (ValueError, AssertionError, FloatingPointError, RuntimeError): return
    raise AssertionError('expected rejection')


def fixture(base):
    cases, pipeline, _ = generated.fixture()
    rng = np.random.default_rng(2927); models = {}; selections = []; rows = []; folds = []
    for key, alpha in zip(sorted(cases), (1., 1., .01, 1.)):
        # Arbitrarily generated stored coefficients; NEVER fitted to any label.
        model = dict(train=[k for k in sorted(cases) if k != key], scales=[1.1, 2.],
                     xm=np.zeros(32), xstd=np.ones(32), ym=np.array([.02]), ystd=np.ones(1),
                     coefficients=rng.normal(0, .0003, size=(3, 33, 1)))
        model['coefficients'][:, 0, 0] = .02
        models['outer_'+key] = oracle.jsonable(model)
        selections.append(dict(holdout=key, train=model['train'], selected_alpha=alpha))
        r, g = oracle.evaluate(cases, key, model, pipeline, [oracle.ALPHAS.index(alpha)], rows,
                               base/'generated_C20.npz' if key == 'u0115' else None)
        folds.append(dict(holdout=key, fallback=False, R=float(r[0]), G=float(g[0])))
    # CSV roundtrip mirrors real types/blank fields rather than handing floats to parser.
    path = base/'generated_reference.csv'
    with path.open('x') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    with path.open() as f: saved = list(csv.DictReader(f))
    with np.load(base/'generated_C20.npz') as p: snapshot = {k: p[k] for k in p.files}
    return cases, pipeline, dict(rows=saved, models=models, selection=selections,
                                decision=oracle.decision(folds), snapshot=snapshot,
                                feature_names=pipeline.names)


def guard_checks(base):
    results = {}; caller = base/'caller'; caller.mkdir(); expected = caller/'NOT_CREATED.json'
    for reason in ('COMPLETED', 'WALL_CAP', 'RSS_CAP', 'OUTPUT_CAP', 'CHILD_FAILED'):
        out = base/('MOCK_'+reason); state = dict(started=False, exit=None); killed = []; calls = []
        class Child:
            pid = 99999971
            @property
            def returncode(self): return state['exit']
            def poll(self): return state['exit']
            def wait(self, timeout=None): state['exit'] = -15; return -15
        def authorize(path, destination):
            assert path == expected and path.is_absolute() and not expected.exists()
            assert destination == out
            return dict(code_commit='MOCK', run_id=out.name)
        def spawn(command, **kwargs):
            assert command[command.index('--authorization')+1] == str(expected)
            assert Path(command[1]).name == 's04_raw_replay.py' and kwargs['cwd'] == guard.ROOT
            assert kwargs['env']['CUDA_VISIBLE_DEVICES'] == ''
            state['started'] = True
            state['exit'] = 0 if reason == 'COMPLETED' else 1 if reason == 'CHILD_FAILED' else None
            calls.append(command); out.mkdir(); (out/'virtual_payload').write_bytes(b'x')
            return Child()
        def process(pid):
            rss = 2*1024**3+1 if pid == Child.pid and reason == 'RSS_CAP' else 1024
            return SimpleNamespace(memory_info=lambda: SimpleNamespace(rss=rss), children=lambda recursive: [])
        original = Path.stat
        def stat(path, *args, **kwargs):
            v = original(path, *args, **kwargs)
            if path.name == 'virtual_payload' and reason == 'OUTPUT_CAP':
                fields = list(v); fields[6] = 101*1024**2; return os.stat_result(fields)
            return v
        with contextlib.chdir(caller), mock.patch.object(guard, 'authorize', side_effect=authorize), \
             mock.patch.object(guard.subprocess, 'Popen', side_effect=spawn), \
             mock.patch.object(guard.psutil, 'Process', side_effect=process), \
             mock.patch.object(guard.os, 'killpg', side_effect=lambda pid, sig: killed.append(pid)), \
             mock.patch.object(guard.time, 'monotonic', side_effect=lambda: 301. if state['started'] and reason == 'WALL_CAP' else 0.), \
             mock.patch.object(Path, 'stat', stat), contextlib.redirect_stdout(io.StringIO()):
            code = guard.execute(out, Path('NOT_CREATED.json'))
        receipt = json.loads((base/(out.name+'_guard_receipt.json')).read_text())
        assert receipt['status'] == reason and code == (0 if reason == 'COMPLETED' else 1)
        assert len(calls) == 1 and not expected.exists()
        if reason.endswith('_CAP'): assert killed == [Child.pid] and receipt['worker_exit'] == -15
        results[reason] = dict(virtual_only=True, launches=1, real_child_processes=0)
    return results


def run(out):
    protect(); out = out.resolve(); out.mkdir(parents=True, exist_ok=False)
    checks = []; errors = {}
    with mock.patch.object(s04_d0, 'load_inputs', side_effect=deny), \
         mock.patch.object(oracle, 'load_inputs', side_effect=deny), \
         mock.patch.object(oracle, 'fit', side_effect=deny), \
         mock.patch.object(oracle, 'fit_blocks', side_effect=deny), \
         mock.patch.object(np.linalg, 'solve', side_effect=deny), \
         mock.patch.object(np.linalg, 'lstsq', side_effect=deny):
        generated.sanity(); cases, pipeline, ref = fixture(out)
        dest = out/'generated_replay'; dest.mkdir()
        before = json.dumps(ref['models'], sort_keys=True)
        result = replay.replay(cases, pipeline, ref, dest)
        assert before == json.dumps(ref['models'], sort_keys=True)
        errors['max_mse_abs_diff'] = max(f['max_mse_abs_diff'] for f in result['folds'])
        errors['max_tolerance_fraction'] = max(f['max_tolerance_fraction'] for f in result['folds'])
        errors['C20_max_abs_diff'] = max(v[0] for v in result['C20_field_comparison'].values())
        checks.append('164 generated-cycle replay versus original einsum scorer; unequal areas; immutable models; C20 arrays')
        result['generated_fixture'] = True
        replay.report(result, dest)  # Small generated audit graphic, never real-data render.
        pin = np.array([[-.001, .2, 1.], [1.001, .3, 2.]])
        model = copy.deepcopy(ref['models']['outer_u011']); x = np.zeros((2, 32))
        model['coefficients'] = np.zeros((3, 33, 1)).tolist(); model['ym'] = [-3.]
        v0, v1 = replay.predict(pin, x, model, 1.)
        assert np.all(v1[:, 2] == 0) and np.array_equal(v0[:, :2], v1[:, :2])
        model['ym'] = [0.]; assert np.array_equal(*replay.predict(pin, x, model, 1.))
        assert np.array_equal(*replay.predict(pin, None, None, None))
        scaled = copy.deepcopy(ref['models']['outer_u011'])
        scaled['xm'] = np.linspace(-.1, .1, 32).tolist()
        scaled['xstd'] = np.logspace(-4, 4, 32).tolist()
        scaled['ystd'] = [2.5]; scaled['ym'] = [.7]
        rng = np.random.default_rng(991)
        z = rng.normal(size=(2, 32)); z[:, 0] = 0.  # Constant-column input.
        xx = np.asarray(scaled['xm'])+z*np.asarray(scaled['xstd'])
        a, b = replay.predict(pin, xx, scaled, 1.)
        coeff = np.array(scaled['coefficients'])[1, :, 0]
        expected = np.array([max(0., pin[j, 2]+scaled['scales'][1]*(
            math.fsum([coeff[0]]+[((xx[j, i]-scaled['xm'][i])/scaled['xstd'][i])*coeff[i+1]
                                 for i in range(32)])*2.5+.7)) for j in range(2)])
        errors['scaled_fsum_prediction_abs_diff'] = replay.close(b[:, 2], expected)[0]
        assert replay.mse(np.array([1., 2.]), np.zeros(2), np.array([1., 3.])) == 3.25
        replay.close(1e-10, 0.); rejected(lambda: replay.close(np.nextafter(1e-10, np.inf), 0.))
        for bad in (np.nan, np.inf, -np.inf):
            corrupt = copy.deepcopy(model); corrupt['ym'] = [bad]
            rejected(lambda: replay.predict(pin, x, corrupt, 1.))
        corrupt = copy.deepcopy(model); corrupt['xstd'][0] = 0
        rejected(lambda: replay.predict(pin, x, corrupt, 1.))
        corrupt = copy.deepcopy(model); corrupt['coefficients'][1][1][0] = 1e308
        rejected(lambda: replay.predict(pin, np.full((2, 32), 1e308), corrupt, 1.))
        # Severe cancellation is not promised to be stable: tolerance must detect loss.
        a = np.sum(np.array([1e16, 1., -1e16])); rejected(lambda: replay.close(a, 1.))
        checks.append('zero residual/fallback/constant feature, std1e-4..1e4 and fsum reconstruction; projection/tolerance; nonfinite/overflow/std/cancellation rejection')
        broken = copy.deepcopy(ref); broken['rows'][0]['V1_physical_mse'] = '123456'
        mismatch = out/'expected_mismatch'; mismatch.mkdir()
        rejected(lambda: replay.replay(cases, pipeline, broken, mismatch))
        checks.append('changed saved score is terminal mismatch, never fallback or tolerance relaxation')
        rejected(lambda: guard.execute(out/'MUST_NOT_EXIST', None))
        assert not (out/'MUST_NOT_EXIST').exists()
        checks.append('real entry without new replay approval rejected before output/source access')
        destination = guard.BASE/'replay_runs/S04-E021-REPLAY-R001'
        virtual = dict(action='frozen_inference_replay_only', user_approved_replay=True,
                       independent_code_review='APPROVED', code_commit='MOCK',
                       reference_commit=guard.REFERENCE_COMMIT, lock_sha256=guard.LOCK_SHA,
                       plan_commit='bcb58a6', run_id='S04-E021-REPLAY-R001', output=str(destination))
        def check_output(command, **kwargs): return 'MOCK\n' if 'rev-parse' in command else ''
        with mock.patch.object(Path, 'read_text', side_effect=lambda *a, **k: json.dumps(virtual)), \
             mock.patch.object(guard.subprocess, 'check_output', side_effect=check_output), \
             mock.patch.object(guard.subprocess, 'check_call', return_value=0):
            assert guard.authorize(Path('VIRTUAL_NOT_A_FILE'), destination) == virtual
            for field, bad in (('user_approved_replay', False), ('code_commit', 'WRONG'),
                               ('action', 'fit'), ('independent_code_review', 'PENDING')):
                old = virtual[field]; virtual[field] = bad
                rejected(lambda: guard.authorize(Path('VIRTUAL_NOT_A_FILE'), destination))
                virtual[field] = old
        checks.append('approval policy positive/mismatch paths use in-memory JSON/git mocks only; no consent file')
        guards = out/'virtual_guard'; guards.mkdir(); caps = guard_checks(guards)
        checks.append('mock success/child failure/three caps; only own virtual PID; non-root relative approval path')
    summary = dict(status='PASS_GENERATED_AND_MOCK_ONLY', checks=checks, observed=errors,
                   guard_checks=caps, real_inputs_opened=False, actual_replay=False,
                   fitting_invoked=False, full_resource_test=False)
    (out/'engineering_receipt.json').write_text(json.dumps(summary, indent=2, allow_nan=False))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    run(p.parse_args().out)
