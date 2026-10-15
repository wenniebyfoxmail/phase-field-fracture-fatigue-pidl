"""E017 synthetic fixtures only: never load real frozen fields or new responses."""
import json
import math
from pathlib import Path
import subprocess
import sys
import warnings
from unittest.mock import patch

import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import aa2024_geometry_prior as m
import aa2024_geometry_result_view as view
import aa2024_frozen_error_decomposition as d
from test_aa2024_geometry_result_view import fixture as base_fixture, receipt


def rebind(prep, fit, val):
    receipt(prep, 'prepare', m.PREP)
    fm = json.loads((fit / 'fit.json').read_text())
    fm['source_prepare'] = m.bindings(prep, m.PREP)
    m.write_json(fit / 'fit.json', fm)
    receipt(fit, 'fit', m.FIT, m.bindings(prep, m.PREP))
    metrics = json.loads((val / 'metrics.json').read_text())
    metrics['source_fit'] = m.bindings(fit, m.FIT)
    m.write_json(val / 'metrics.json', metrics)
    receipt(val, 'validate', view.VALIDATION, m.bindings(fit, m.FIT))
    evidence = val.parent / 'figures'
    evidence.mkdir(exist_ok=True)
    # Hash-bound synthetic evidence placeholders, not real E016 figure files.
    for name in d.EVIDENCE_NAMES:
        (evidence / name).write_text('SYNTHETIC_ONLY_EVIDENCE ' + name)
    er = dict(source_prepare=m.bindings(prep, m.PREP), source_fit=m.bindings(fit, m.FIT),
              source_validation=m.bindings(val, view.VALIDATION), plotter_sha256=m.sha(view.__file__),
              artifacts_sha256={name: m.sha(evidence / name) for name in d.EVIDENCE_NAMES})
    m.write_json(evidence / 'render_receipt.json', er)
    return dict(prepare=m.sha(prep / 'execution_receipt.json'), fit=m.sha(fit / 'execution_receipt.json'),
                validation=m.sha(val / 'execution_receipt.json'), evidence=m.sha(evidence / 'render_receipt.json'),
                prior_view=m.sha(view.__file__), eligible=metrics['eligible'], target='SYNTHETIC_TARGET_ID',
                source_runs=dict(prepare='SYNTHETIC_ONLY_prepare', fit='SYNTHETIC_ONLY_fit', validation='SYNTHETIC_ONLY_validate'))


def fixture(tmp_path, *, zero=False):
    prep, fit, val = base_fixture(tmp_path)
    frozen = m.load(fit / 'frozen_predictions.npz')
    p = m.load(prep / 'prepared.npz')
    fields = m.load(val / 'validation_fields.npz')
    if zero:
        for k in m.ARMS:
            frozen[k] = np.zeros_like(frozen[k]); fields[k] = np.zeros_like(fields[k])
            fields[k + '_residual'] = np.zeros_like(fields[k])
        fields['target'] = np.zeros_like(fields['target'])
        np.savez_compressed(fit / 'frozen_predictions.npz', **frozen)
        np.savez_compressed(val / 'validation_fields.npz', **fields)
        metrics = json.loads((val / 'metrics.json').read_text())
        metrics.update(MAE_mm={k: 0. for k in m.ARMS}, primary_old_minus_proxy_mm=0., descriptive_outcome='equal')
        m.write_json(val / 'metrics.json', metrics)
    p['train_v'] = frozen['secant'] / frozen['alpha']
    np.savez_compressed(prep / 'prepared.npz', **p)
    np.savez_compressed(fit / 'solved_fields.npz', **{k + '_sampled': frozen[k] / frozen['alpha'] for k in d.ARMS})
    return prep, fit, val, rebind(prep, fit, val)


def invoke(prep, fit, val, lock, out, **kwargs):
    return d.run(prep, fit, val, out, 'SYNTHETIC_SOURCE', 'SYNTHETIC_ONLY_E017', lock=lock, **kwargs)


def test_synthetic_end_to_end_and_source_immutability(tmp_path):
    prep, fit, val, lock = fixture(tmp_path)
    before = {str(p): m.sha(p) for r in (prep, fit, val, val.parent / 'figures') for p in r.iterdir()}
    out = tmp_path / 'decomposition'
    with patch.object(m, 'prepare', side_effect=AssertionError('no prepare')), \
         patch.object(m, 'fit', side_effect=AssertionError('no fit')), \
         patch.object(m, 'validate', side_effect=AssertionError('no validate')), \
         patch.object(m, 'parse_nodemap', side_effect=AssertionError('no nodemap')), \
         patch.object(m, 'solve_patch', side_effect=AssertionError('no solve')), \
         patch.object(view, 'render', side_effect=AssertionError('no old render')):
        invoke(prep, fit, val, lock, out)
    assert before == {p: m.sha(p) for p in before}
    r = json.loads((out / 'execution_receipt.json').read_text())
    assert r['execution_status'] == 'succeeded'
    assert r['sources_before_sha256'] == r['sources_after_sha256']
    for name, sha in r['artifacts_sha256'].items(): assert m.sha(out / name) == sha
    assert len(list(out.glob('*.png'))) == len(list(out.glob('*.pdf'))) == 2
    q = json.loads((out / 'decomposition.json').read_text())
    assert len(q['rows']) == 9 and set(q['arithmetic_checks']) == set(d.ARMS)
    z = m.load(out / 'pointwise.npz')
    assert z['region_B'].dtype == np.bool_ and len(z['ids']) == lock['eligible']
    subprocess.run([sys.executable, 'source/validate_figure_sidecars.py', str(out)],
                   cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)
    assert 'SYNTHETIC_ONLY' in (out / 'README_analysis.md').read_text()
    with pytest.raises(ValueError, match='fresh'): invoke(prep, fit, val, lock, out)
    print('SYNTHETIC_E017_FIGURES=' + str(out))


def scalar_project(xy, raw, w):
    total = math.fsum(float(x) for x in w)
    center = [math.fsum(float(ww) * float(x[j]) for ww, x in zip(w, xy)) / total for j in range(2)]
    shift = [math.fsum(float(ww) * float(x[j]) for ww, x in zip(w, raw)) / total for j in range(2)]
    rot = [(-(float(x[1]) - center[1]), float(x[0]) - center[0]) for x in xy]
    denom = math.fsum(float(ww) * (r[0]**2 + r[1]**2) for ww, r in zip(w, rot))
    theta = math.fsum(float(ww) * (r[0]*(float(u[0])-shift[0]) + r[1]*(float(u[1])-shift[1]))
                      for ww, r, u in zip(w, rot, raw)) / denom
    return np.array([[float(u[j]) - shift[j] - theta*r[j] for j in range(2)] for u, r in zip(raw, rot)])


def test_common_subset_scalar_reference_and_regional_conservation(tmp_path):
    prep, fit, val, lock = fixture(tmp_path)
    a, metrics, p, solved, idx, _, _ = d.checked_inputs(prep, fit, val, lock)
    point, rows, checks = d.decompose(a, metrics, p, solved, idx)
    es = scalar_project(a['xy'], a['secant'] - a['target'], a['weights'])
    np.testing.assert_allclose(point['e_s'], es, atol=1e-15, rtol=1e-12)
    w = a['weights']; total = math.fsum(w)
    for k in d.ARMS:
        c = scalar_project(a['xy'], a[k] - a['secant'], w)
        gaps = [math.hypot(*(x+y)) - math.hypot(*x) for x, y in zip(es, c)]
        expected = math.fsum(float(ww)*g for ww, g in zip(w, gaps)) / total
        all_row = next(r for r in rows if r['arm'] == k and r['region'] == 'all')
        assert all_row['G_contribution_mm'] == pytest.approx(expected, rel=1e-12, abs=1e-15)
        assert all_row['E_k_contribution_mm2'] - all_row['E_s_contribution_mm2'] == pytest.approx(
            all_row['C_contribution_mm2'] + all_row['I_contribution_mm2'], rel=1e-12, abs=1e-18)
        assert checks[k]['max_scaled_training_error_mm'] < 1e-15
    f = m.load(fit / 'frozen_predictions.npz')
    # Removing one point changes the projection: never truncate a 45-point result.
    full_residual = view.closed_form_residual(f['xy'], f['secant'], f['weights'])[idx]
    subset_residual = view.closed_form_residual(a['xy'], a['secant'], w)
    assert np.max(np.abs(full_residual - subset_residual)) > 1e-8
    # Regional re-projection is different too; only aggregation is permitted.
    mask = point['region_B']
    wrong = view.closed_form_residual(a['xy'][mask], (a['secant']-a['target'])[mask], w[mask])
    assert np.max(np.abs(wrong - point['e_s'][mask])) > 1e-8


@pytest.mark.parametrize('mutation', ['train_v', 'sample', 'xy', 'weights', 'alpha', 'nonfinite', 'shape', 'sample_order'])
def test_reject_new_training_and_sample_inconsistencies(tmp_path, mutation):
    prep, fit, val, _ = fixture(tmp_path)
    p = m.load(prep / 'prepared.npz'); s = m.load(fit / 'solved_fields.npz')
    if mutation == 'train_v': p['train_v'][0, 0] += .001
    if mutation == 'sample': s['old_sampled'][0, 0] += .001
    if mutation == 'xy': p['xy'][0, 0] += .001
    if mutation == 'weights': p['weights'][0] *= 2
    if mutation == 'alpha': p['alpha'] *= 1.01
    if mutation == 'nonfinite': p['train_v'][0, 0] = np.nan
    if mutation == 'shape': s['proxy_sampled'] = s['proxy_sampled'][:-1]
    if mutation == 'sample_order': s['intact_sampled'] = s['intact_sampled'][::-1]
    np.savez_compressed(prep / 'prepared.npz', **p); np.savez_compressed(fit / 'solved_fields.npz', **s)
    lock = rebind(prep, fit, val)
    out = tmp_path / 'failed'
    with pytest.raises(ValueError): invoke(prep, fit, val, lock, out)
    assert json.loads((out / 'execution_receipt.json').read_text())['execution_status'] == 'failed'
    assert not (out / 'pointwise.npz').exists()


def test_real_default_anchors_reject_synthetic_before_array_loading(tmp_path):
    prep, fit, val, _ = fixture(tmp_path)
    out = tmp_path / 'failed'
    with patch.object(m, 'load', side_effect=AssertionError('anchor must precede NPZ')):
        with pytest.raises(ValueError, match='anchored'):
            d.run(prep, fit, val, out, 'SYNTHETIC', 'SYNTHETIC_ONLY')
    assert not (out / 'pointwise.npz').exists()


@pytest.mark.parametrize('mutation', ['anchor', 'evidence', 'run', 'target', 'count', 'source_reader'])
def test_reject_lock_or_evidence_mismatch(tmp_path, mutation):
    prep, fit, val, lock = fixture(tmp_path)
    if mutation == 'anchor': lock['validation'] = 'OTHER'
    if mutation == 'evidence': (val.parent / 'figures/scores.csv').write_text('tampered')
    if mutation == 'run': lock['source_runs']['fit'] = 'OTHER'
    if mutation == 'target': lock['target'] = 'OTHER'
    if mutation == 'count': lock['eligible'] += 1
    if mutation == 'source_reader': lock['prior_view'] = 'OTHER'
    with pytest.raises(ValueError): invoke(prep, fit, val, lock, tmp_path / 'failed')


def test_warning_stops_and_cannot_retry_same_output(tmp_path):
    prep, fit, val, lock = fixture(tmp_path); out = tmp_path / 'failed'
    def warn(*args): warnings.warn('synthetic anomaly', RuntimeWarning)
    with patch.object(d, 'decompose', side_effect=warn):
        with pytest.raises(RuntimeWarning): invoke(prep, fit, val, lock, out)
    r = json.loads((out / 'execution_receipt.json').read_text())
    assert r['execution_status'] == 'failed' and 'synthetic anomaly' in r['error']
    with pytest.raises(ValueError, match='fresh'): invoke(prep, fit, val, lock, out)


class Clock:
    value = 0.
    def __call__(self): return self.value


@pytest.mark.parametrize('phase', ['save', 'hash', 'final_receipt'])
def test_budget_includes_serialization_hashing_and_last_receipt(tmp_path, phase):
    prep, fit, val, lock = fixture(tmp_path); out = tmp_path / 'failed'; timer = Clock()
    original_save, original_hashes, original_write = d.np.savez_compressed, d.hashes, m.write_json
    calls = 0
    def save(*args, **kwargs):
        original_save(*args, **kwargs)
        if phase == 'save': timer.value = 60.
    def hash_values(paths):
        nonlocal calls
        calls += 1; result = original_hashes(paths)
        if phase == 'hash' and calls == 2: timer.value = 60.
        return result
    def write(path, value):
        original_write(path, value)
        if phase == 'final_receipt' and value.get('execution_status') == 'succeeded': timer.value = 60.
    with patch.object(d.np, 'savez_compressed', side_effect=save), patch.object(d, 'hashes', side_effect=hash_values), \
         patch.object(m, 'write_json', side_effect=write):
        with pytest.raises(TimeoutError): invoke(prep, fit, val, lock, out, clock=timer)
    r = json.loads((out / 'execution_receipt.json').read_text())
    assert r['execution_status'] == 'failed' and r['outputs_role'] == 'forensic_only'


def test_source_mutation_is_detected_after_draw(tmp_path):
    prep, fit, val, lock = fixture(tmp_path); out = tmp_path / 'failed'
    original = d.draw
    def mutate(*args):
        original(*args)
        (prep / 'geometry_audit.json').write_text('SYNTHETIC_CHANGE_DURING_RUN')
    with patch.object(d, 'draw', side_effect=mutate):
        with pytest.raises(ValueError, match='source changed'): invoke(prep, fit, val, lock, out)


def test_zero_fields_and_empty_region_are_not_failures(tmp_path):
    prep, fit, val, lock = fixture(tmp_path, zero=True); out = tmp_path / 'zero'
    invoke(prep, fit, val, lock, out)
    q = json.loads((out / 'decomposition.json').read_text())
    assert all(r['G_sign'] == 'numerically_unresolved' for r in q['rows'])
    a, metrics, p, solved, idx, _, _ = d.checked_inputs(prep, fit, val, lock)
    a['xy'] = a['xy'].copy(); a['xy'][:, 1] *= .25
    _, rows, _ = d.decompose(a, metrics, p, solved, idx)
    outer = [r for r in rows if r['region'] == 'O']
    assert all(r['count'] == 0 and r['G_contribution_mm'] == 0 and r['conditional_G_mm'] is None for r in outer)


def test_output_cannot_overlap_sources(tmp_path):
    prep, fit, val, lock = fixture(tmp_path)
    out = fit / 'new_directory'
    with pytest.raises(ValueError, match='overlap'): invoke(prep, fit, val, lock, out)
    assert not out.exists()


def test_known_cancellation_reinforcement_and_oversized_deviation(tmp_path):
    prep, fit, val, lock = fixture(tmp_path)
    a, _, _, _, _, _, _ = d.checked_inputs(prep, fit, val, lock)
    es = scalar_project(a['xy'], a['secant'] - a['target'], a['weights'])
    a['target'] = np.zeros_like(es); a['secant'] = es.copy(); a['secant_residual'] = es.copy()
    alpha = 2.; factors = dict(old=-.5, proxy=.5, intact=-3.)
    p = dict(alpha=alpha, train_v=es / alpha); solved = {}; metrics = dict(MAE_mm={})
    metrics['MAE_mm']['secant'] = float(np.sum(a['weights']*d.norm(es))/a['weights'].sum())
    for k, factor in factors.items():
        a[k] = (1+factor)*es
        a[k+'_residual'] = scalar_project(a['xy'], a[k], a['weights'])
        solved[k+'_sampled'] = a[k] / alpha
        metrics['MAE_mm'][k] = float(np.sum(a['weights']*d.norm(a[k+'_residual']))/a['weights'].sum())
    _, rows, _ = d.decompose(a, metrics, p, solved, np.arange(len(es)))
    r = {x['arm']: x for x in rows if x['region'] == 'all'}
    assert r['old']['I_sign'] == 'negative' and r['old']['G_sign'] == 'negative'
    assert r['proxy']['I_sign'] == 'positive' and r['proxy']['G_sign'] == 'positive'
    assert r['intact']['I_sign'] == 'negative' and r['intact']['G_sign'] == 'positive'
    assert r['intact']['C_contribution_mm2'] + r['intact']['I_contribution_mm2'] > 0
    # MAE is a difference of norms, not the mean norm of c.
    assert r['old']['G_contribution_mm'] < 0 < r['old']['conditional_deviation_norm_mm']


def test_cli_synthetic_and_environment_guards(tmp_path, monkeypatch):
    prep, fit, val, lock = fixture(tmp_path); out = tmp_path / 'cli'
    monkeypatch.setattr(d, 'DEFAULT_LOCK', lock)  # no CLI override exists in production
    monkeypatch.setattr(sys, 'argv', ['aa2024_frozen_error_decomposition.py',
        '--prepare', str(prep), '--fit', str(fit), '--validation', str(val), '--output', str(out),
        '--source-commit', 'SYNTHETIC_SOURCE', '--run-id', 'SYNTHETIC_ONLY_CLI'])
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        monkeypatch.setenv(name, '1')
    monkeypatch.setenv('PYTHONWARNINGS', 'default')
    with pytest.raises(ValueError, match='PYTHONWARNINGS'): d.main()
    assert not out.exists()
    monkeypatch.setenv('PYTHONWARNINGS', 'error'); monkeypatch.setenv('MKL_NUM_THREADS', '2')
    with pytest.raises(ValueError, match='single-thread'): d.main()
    assert not out.exists()
    monkeypatch.setenv('MKL_NUM_THREADS', '1'); d.main()
    assert json.loads((out / 'execution_receipt.json').read_text())['execution_status'] == 'succeeded'
