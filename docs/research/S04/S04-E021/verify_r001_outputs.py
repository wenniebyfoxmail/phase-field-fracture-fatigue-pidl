"""Read saved R001 outputs only; no source trajectories, model fitting or rendering."""
import csv
import json
from pathlib import Path

import numpy as np

BASE = Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E021')
OUT = BASE/'runs/S04-E021-R001'
COMMIT = '6aa21e3c469d53c92240c9689d07a3ffb316d67c'
COUNTS = {'u011': 121, 'u0115': 99, 'u012': 82, 'u013': 55}
EPS = 1e-10


def read(path):
    return json.loads(path.read_text())


def verify():
    paths = sorted(OUT.rglob('*'))
    paths = [p for p in paths if p.is_file()]+[
        BASE/'runs/S04-E021-R001_guard.log',
        BASE/'runs/S04-E021-R001_fit_guard_receipt.json',
        BASE/'runs/S04-E021-R001_guard_receipt.json']
    before = {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in paths}
    assert all((p.stat().st_mode & 0o222) == 0 for p in paths), 'freeze first'
    required = {'receipt.json', 'models.json', 'selection.json', 'decision.json',
                'percycle.csv', 'folds.csv', 'u0115_C20.npz', 'V0_V1_holdouts.png',
                'u0115_C20_raw.png', 'README_analysis.md'}
    assert {p.name for p in OUT.iterdir()} == required
    guard = read(paths[-1]); stage = read(paths[-2]); worker = read(OUT/'receipt.json')
    for r in (guard, stage, worker):
        assert r['status'] == 'COMPLETED' and r['code_commit'] == COMMIT
        assert r['run_id'] == OUT.name and r['design_commit'] == '45b8d32'
    assert guard['mode'] == worker['mode'] == 'real'
    assert guard['output'] == stage['output'] == str(OUT)
    assert [c['phase'] for c in guard['children']] == ['fit', 'report']
    assert all(c['exit_code'] == 0 for c in guard['children'])
    assert stage['children'][0]['pid'] == worker['pid'] == guard['children'][0]['pid']
    assert worker['lock_sha256'] == 'cb9f63f8bd4b73afe0bd0f74bc7836018ce2e6bfcbd46edae80e7fef7b07868c'
    assert guard['elapsed_seconds'] < 300 and guard['peak_rss_bytes'] <= 2*1024**3
    assert sum(p.stat().st_size for p in paths) <= 100*1024**2
    assert len(worker['sample_ids']) == 2048 and len(worker['feature_names']) == 32
    assert worker['rows'] == 357
    rows = list(csv.DictReader((OUT/'percycle.csv').open()))
    assert len(rows) == 357
    decision = read(OUT/'decision.json'); selection = read(OUT/'selection.json')
    assert len(decision['folds']) == len(selection) == 4
    assert {f['holdout'] for f in decision['folds']} == set(COUNTS)
    with (OUT/'folds.csv').open() as f:
        saved_folds = list(csv.DictReader(f))
    checks = []
    for fold, sel, saved in zip(decision['folds'], selection, saved_folds):
        key = fold['holdout']; assert key == sel['holdout'] == saved['holdout']
        assert set(sel['train']) == set(COUNTS)-{key}
        rr = np.array(sel['inner_R']); gg = np.array(sel['inner_G'])
        assert rr.shape == gg.shape == (3, 3)
        assert np.isfinite(rr).all() and np.isfinite(gg).all()
        eligible = np.all(gg <= 1+EPS, axis=0); objectives = rr.max(axis=0)
        choices = np.flatnonzero(eligible).tolist(); alphas = (.01, 1., 100.)
        best = min(choices, key=lambda j: (objectives[j], -alphas[j])) if choices else None
        chosen = alphas[best] if best is not None and objectives[best] < 1-EPS else None
        assert chosen == sel['selected_alpha'] and fold['fallback'] == (chosen is None)
        np.testing.assert_array_equal(eligible, sel['eligible'])
        np.testing.assert_allclose(objectives, sel['objectives'], rtol=0, atol=0)
        part = [r for r in rows if r['holdout'] == key]
        assert [int(r['cycle']) for r in part] == list(range(1, COUNTS[key]+1))
        values = np.array([[float(r[k]) for k in ('V0_physical_mse', 'V1_physical_mse',
                         'cycle_weight', 'V0_raw_min', 'V1_raw_min', 'V0_raw_max',
                         'V1_raw_max', 'raw_negative_area')] for r in part])
        assert np.isfinite(values).all() and np.all(values >= 0)
        strata = np.minimum(np.arange(len(part))//20, 2)
        expected_weights = np.array([1/(3*np.sum(strata == s)) for s in strata])
        np.testing.assert_allclose(values[:, 2], expected_weights, rtol=0, atol=1e-16)
        assert all(int(r['stratum']) == s for r, s in zip(part, strata))
        assert all(r['damage_history_identical'] == 'True' for r in part)
        assert all((r['fallback'] == 'True') == fold['fallback'] for r in part)
        assert np.all(values[:, -1] == 0)
        v0 = float(np.sum(values[:, 0]*values[:, 2])); v1 = float(np.sum(values[:, 1]*values[:, 2]))
        b0 = float(values[:20, 0].mean()); b1 = float(values[:20, 1].mean())
        assert v0 > 1e-24 and b0 > 1e-24
        r = float(np.sqrt(v1/v0)); g = float(np.sqrt(b1/b0))
        np.testing.assert_allclose([r, g], [fold['R'], fold['G']], rtol=1e-12, atol=1e-14)
        np.testing.assert_allclose([float(saved['R']), float(saved['G'])], [r, g], rtol=1e-12, atol=1e-14)
        checks.append(dict(holdout=key, rows=len(part), R=r, G=g,
                           selected_alpha=chosen, fallback=fold['fallback'],
                           V0_balanced_physical_mse=v0, V1_balanced_physical_mse=v1,
                           inner_eligible=eligible.tolist(), inner_worst_R=objectives.tolist()))
    q = max(f['R'] for f in checks)
    status = ('EARLY_REGRESSION' if any(f['G'] > 1+EPS for f in checks) else
              'RAW_REGRESSION' if q > 1+EPS else
              'DIRECTIONAL_DEVELOPMENT_GAIN' if q < 1-EPS else 'NUMERICAL_TIE')
    np.testing.assert_allclose(q, decision['Q'], rtol=1e-12, atol=1e-14)
    assert status == decision['status']
    models = read(OUT/'models.json')
    assert len([k for k in models if k.startswith('inner_')]) == 6
    for name, model in models.items():
        if model is None:
            assert name.startswith('outer_'); continue
        assert np.array(model['coefficients']).shape == (3, 33, 1)
        for field in ('scales', 'xm', 'ym', 'xstd', 'ystd', 'coefficients'):
            assert np.isfinite(np.array(model[field])).all()
        assert np.all(np.array(model['scales']) > 1e-12)
        assert np.all(np.array(model['xstd']) > 0) and np.all(np.array(model['ystd']) > 0)
        if name.startswith('outer_'):
            assert set(model['train']) == set(COUNTS)-{name.removeprefix('outer_')}
    with np.load(OUT/'u0115_C20.npz', allow_pickle=False) as snap:
        ids = snap['ids']; assert ids.shape == (85112,) and len(np.unique(ids)) == 85112
        assert np.all((ids >= 0) & (ids < 86408)) and np.all(np.diff(ids) > 0)
        for name in ('fem', 'V0', 'V1'):
            a = snap[name]; assert a.shape == (85112, 3) and np.isfinite(a).all()
            assert np.all((a[:, 0] >= 0) & (a[:, 0] <= 1)) and np.all(a[:, 1:] >= 0)
        np.testing.assert_array_equal(snap['V0'][:, :2], snap['V1'][:, :2])
    after = {str(p): (p.stat().st_size, p.stat().st_mtime_ns) for p in paths}
    assert before == after, 'frozen files changed during audit'
    log = paths[-3].read_text()
    result = dict(status='VERIFIED_SAVED_OUTPUTS', run_id=OUT.name, code_commit=COMMIT,
                  evidence_domain='synthetic development s4 horizon0 archive imitation',
                  outcome=status, Q=q, folds=checks, fit_rerun=False, source_trajectories_opened=False,
                  frozen_files=[dict(path=p, bytes=v[0], mtime_ns=v[1]) for p, v in before.items()],
                  total_frozen_bytes=sum(v[0] for v in before.values()),
                  warnings_present='Warning' in log, traceback_present='Traceback' in log,
                  visual_qa='pending separately; this script does not inspect pixels')
    dest = BASE/'control/S04-E021-R001_saved_output_verification.json'
    assert not dest.exists()
    dest.write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps({k: v for k, v in result.items() if k != 'frozen_files'}, indent=2))


if __name__ == '__main__':
    verify()
