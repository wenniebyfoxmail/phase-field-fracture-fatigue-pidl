"""E019 synthetic-only tests; never open real training or held arrays."""
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import warnings
from unittest.mock import patch

import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import aa2024_geometry_prior as m
import aa2024_kinematic_capacity as d
from test_aa2024_geometry_result_view import receipt


def rebind(prep, fit):
    receipt(prep, 'prepare', m.PREP)
    fm = json.loads((fit/'fit.json').read_text()); fm['source_prepare'] = m.bindings(prep, m.PREP)
    m.write_json(fit/'fit.json', fm)
    receipt(fit, 'fit', m.FIT, m.bindings(prep, m.PREP))
    n = json.loads((prep/'preparation.json').read_text())['observations']
    return dict(prepare=m.sha(prep/'execution_receipt.json'), fit=m.sha(fit/'execution_receipt.json'),
                runs=dict(prepare='SYNTHETIC_ONLY_prepare', fit='SYNTHETIC_ONLY_fit'), observations=n)


def fixture(tmp_path, *, full=False, zero=False):
    prep, fit = tmp_path/'prepare', tmp_path/'fit'; prep.mkdir(); fit.mkdir()
    nx, ny = (27, 24) if full else (6, 6)
    xx, yy = np.meshgrid(np.linspace(-15.1, 15.1, nx), np.linspace(-6.5, 6.5, ny))
    xy = np.c_[xx.ravel(), yy.ravel()]
    xy += np.random.default_rng(19019).uniform(-.025, .025, xy.shape)
    n = len(xy); mesh, tri, bd = m.rectangular_mesh()
    base = np.zeros_like(mesh) if zero else np.c_[.0002*mesh[:, 0]-.0003*mesh[:, 1]+.001,
                                                                  -.0001*mesh[:, 0]+.0004*mesh[:, 1]-.0005]
    target = m.sample_regular_mesh(base, xy)
    if not zero: target += .00007*np.c_[np.sin(np.arange(n)), np.cos(np.arange(n)*.7)]
    p = dict(ids=103+7*np.arange(n), xy=xy, train_v=target, weights=np.linspace(.2, 1.3, n),
             mesh=mesh, tri=tri, boundary=bd, bc=base[bd])
    np.savez_compressed(prep/'prepared.npz', **p)
    # Forbidden array inputs are opaque byte-hash placeholders, not readable NPZs.
    (prep/'training_geometry.npz').write_bytes(b'SYNTHETIC_OPAQUE_GEOMETRY_NOT_TO_LOAD')
    (fit/'frozen_predictions.npz').write_bytes(b'SYNTHETIC_OPAQUE_HIGH_PREDICTIONS_NOT_TO_LOAD')
    headers = [dict(current_stage_index=str(i), reference_stage_index='1', cycles='292018.5', force=str(j))
               for i, j in ((13, 100), (14, 200))]
    m.write_json(prep/'preparation.json', dict(cycle='292018.5', reference=1, forces=[100., 200., 300.], observations=n))
    m.write_json(prep/'geometry_audit.json', dict(cycle='292018.5', stages=[13, 14], training_headers=headers))
    fields = {}; taper = (1-(mesh[:, 0]/18)**2)*(1-(mesh[:, 1]/9)**2)
    for i, k in enumerate(d.ARMS):
        values = base.copy()
        if not zero: values += .00013*(i+1)*taper[:, None]*np.c_[np.sin(mesh[:, 0]), np.cos(mesh[:, 1])]
        fields[k], fields[k+'_sampled'] = values, m.sample_regular_mesh(values, xy)
    np.savez_compressed(fit/'solved_fields.npz', **fields)
    m.write_json(fit/'fit.json', dict(cycle='292018.5', status='four_predictions_frozen_before_held_response'))
    return prep, fit, rebind(prep, fit)


def invoke(prep, fit, lock, out, **kwargs):
    return d.run(prep, fit, out, 'SYNTHETIC_SOURCE', 'SYNTHETIC_ONLY_E019', lock=lock, **kwargs)


def test_synthetic_end_to_end_single_svd_no_forbidden_reads(tmp_path):
    prep, fit, lock = fixture(tmp_path); out = tmp_path/'analysis'
    before = {str(p): m.sha(p) for root in (prep, fit) for p in root.iterdir()}
    load = m.load; loaded = []
    def training_only(path):
        loaded.append(Path(path).name)
        assert Path(path).name in ('prepared.npz', 'solved_fields.npz')
        return load(path)
    with patch.object(m, 'load', side_effect=training_only), \
         patch.object(m, 'prepare', side_effect=AssertionError('no prepare')), \
         patch.object(m, 'fit', side_effect=AssertionError('no fit')), \
         patch.object(m, 'validate', side_effect=AssertionError('no validate')), \
         patch.object(m, 'solve_patch', side_effect=AssertionError('no solve')), \
         patch.object(m, 'parse_nodemap', side_effect=AssertionError('no raw parser')), \
         patch.object(d.linalg, 'svd', wraps=d.linalg.svd) as svd:
        invoke(prep, fit, lock, out)
    assert loaded == ['prepared.npz', 'solved_fields.npz'] and svd.call_count == 1
    assert svd.call_args.kwargs['lapack_driver'] == 'gesvd'
    assert before == {p: m.sha(p) for p in before}
    r = json.loads((out/'execution_receipt.json').read_text()); q = json.loads((out/'report.json').read_text())
    assert r['execution_status'] == 'succeeded' and r['sources_before_sha256'] == r['sources_after_sha256']
    assert len(r['artifacts_sha256']) == 10
    for name, sha in r['artifacts_sha256'].items(): assert m.sha(out/name) == sha
    assert len(q['rows']) == 3 and q['boundary_sampling_nonzeros'] == 0 and q['nominal_free_dofs'] == 1482
    a = load(out/'pointwise.npz')
    assert a['e_kin'].shape == (lock['observations'], 2)
    assert a['stencil_node_indices'].shape == (lock['observations'], 3)
    assert not any('nodal' in name or 'oracle' in name or name == 'z' for name in a)
    subprocess.run([sys.executable, 'source/validate_figure_sidecars.py', str(out)],
                   cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)
    assert 'SYNTHETIC_ONLY' in (out/'README_analysis.md').read_text()
    with pytest.raises(ValueError, match='fresh'): invoke(prep, fit, lock, out)
    print('SYNTHETIC_E019_FIGURES='+str(out))


def test_same_size_648_synthetic_budget_only(tmp_path):
    prep, fit, lock = fixture(tmp_path, full=True); out = tmp_path/'full'
    invoke(prep, fit, lock, out)
    r = json.loads((out/'execution_receipt.json').read_text()); q = json.loads((out/'report.json').read_text())
    assert r['elapsed_seconds'] < 60 and q['observation_components'] == 1296 and q['nominal_free_dofs'] == 1482
    assert q['svd_calls'] == 1 and q['numerical_rank'] <= 1293
    assert q['active_sampling_columns']+q['zero_sampling_columns'] == 1482
    print('SYNTHETIC_E019_648_BUDGET='+json.dumps(dict(seconds=r['elapsed_seconds'], shape=[1296, 1482],
                                                        rank=q['numerical_rank'], scipy=r['scipy_version'])))


def test_cst_stencils_match_original_sampling_and_affine_reproduction():
    rng = np.random.default_rng(19)
    xy = np.vstack([rng.uniform([-17.8, -8.8], [17.8, 8.8], (50, 2)),
                    [[-18, -9], [18, 9], [0, 0], [.3, .3], [.3, .30000001]]])
    S, nodes, coeff = d.sampling(xy)
    values = rng.normal(size=(861, 2))*.001
    np.testing.assert_allclose((S@values.ravel()).reshape(-1, 2), m.sample_regular_mesh(values, xy), atol=1e-15, rtol=1e-12)
    mesh = m.rectangular_mesh()[0]
    affine = np.c_[mesh[:, 0]+2*mesh[:, 1]+3, -2*mesh[:, 0]+mesh[:, 1]-1]
    expected = np.c_[xy[:, 0]+2*xy[:, 1]+3, -2*xy[:, 0]+xy[:, 1]-1]
    np.testing.assert_allclose((S@affine.ravel()).reshape(-1, 2), expected, atol=1e-12)
    assert nodes.shape == coeff.shape == (55, 3)


def scalar_projection(xy, u, w):
    total = math.fsum(w)
    center = [math.fsum(float(a)*float(x[j]) for a, x in zip(w, xy))/total for j in (0, 1)]
    shift = [math.fsum(float(a)*float(v[j]) for a, v in zip(w, u))/total for j in (0, 1)]
    rot = [(-(float(x[1])-center[1]), float(x[0])-center[0]) for x in xy]
    theta = math.fsum(float(a)*(r[0]*(v[0]-shift[0])+r[1]*(v[1]-shift[1])) for a, r, v in zip(w, rot, u)) / \
        math.fsum(float(a)*(r[0]**2+r[1]**2) for a, r in zip(w, rot))
    return np.array([[v[j]-shift[j]-theta*r[j] for j in (0, 1)] for v, r in zip(u, rot)])


def test_weighted_quotient_scalar_reference_and_rigid_invariance():
    xy = np.array([[-8., -5.], [2., 6.], [9., -1.], [-2., 4.], [7., 3.]])
    w = np.array([1., 3., 2., 7., .2]); u = .001*np.c_[xy[:, 0]**2, xy[:, 1]**2]
    scale, H = d.rigid_basis(xy, w)
    actual = (d.quotient(H, scale*u.ravel())/scale).reshape(-1, 2)
    np.testing.assert_allclose(actual, scalar_projection(xy, u, w), atol=1e-15, rtol=1e-12)
    rigid = np.array([.4, -.7])+.003*np.c_[-xy[:, 1], xy[:, 0]]
    np.testing.assert_allclose(d.quotient(H, scale*rigid.ravel()), 0, atol=1e-15)
    s2, h2 = d.rigid_basis(xy, 10*w)
    np.testing.assert_allclose(d.quotient(h2, s2*u.ravel()), d.quotient(H, scale*u.ravel()), atol=1e-15)
    with pytest.raises(ValueError, match='rigid rank'): d.rigid_basis(np.ones((5, 2)), w)


def test_non_blas_contraction_matches_independent_fsum():
    rng = np.random.default_rng(19020); a = rng.normal(size=(9, 17)); b = rng.normal(size=(17, 12))
    expected = np.array([[math.fsum(float(x)*float(y) for x, y in zip(row, col)) for col in b.T] for row in a])
    np.testing.assert_allclose(d.multiply(a, b), expected, rtol=1e-12, atol=1e-15)
    np.testing.assert_allclose(d.multiply(a, b[:, 0]), expected[:, 0], rtol=1e-12, atol=1e-15)
    with pytest.raises(ValueError, match='contraction shape'): d.multiply(a, np.ones(3))


@pytest.mark.parametrize('floor,gap', [(False, False), (False, True), (True, False), (True, True)])
def test_analytic_nonunique_projection_square_budget_and_four_states(floor, gap):
    # One unobservable free column, two represented rows, two residual-only rows.
    A = np.array([[1., 0., 0.], [0., 1., 0.], [0., 0., 0.], [0., 0., 0.]])
    y = np.array([.001, -.002, .004 if floor else 0., 0.])
    models = {k: np.array([.001+(.003 if gap else 0), -.002, 0., 0.]) for k in d.ARMS}
    a, q = d.project(A, y, models, time.monotonic(), time.monotonic)
    np.testing.assert_allclose(a['weighted_projection'], [.001, -.002, 0, 0], atol=1e-15)
    assert q['numerical_rank'] == 2 and q['effective_nullity'] == 1
    for row in q['rows']:
        assert row['J_kin_mm2'] == pytest.approx(.004**2 if floor else 0, abs=1e-18)
        assert row['extra_square_mm2'] == pytest.approx(.003**2 if gap else 0, abs=1e-18)
        assert row['J_model_mm2'] == pytest.approx(row['J_kin_mm2']+row['extra_square_mm2'], abs=1e-18)
        assert row['state'] == ('floor_resolved' if floor else 'floor_unresolved')+('_gap_resolved' if gap else '_gap_unresolved')
    # Col(A) unchanged for arbitrary magnitude in the unobserved column: no nodal uniqueness.
    np.testing.assert_array_equal(A@np.array([.001, -.002, 0]), A@np.array([.001, -.002, 1e6]))


def test_millimetre_decision_boundary_not_squared_or_aggregate():
    assert d.classify(.2, .1, .15) == 'floor_resolved_gap_unresolved'
    assert d.classify(.15, .15, .15) == 'floor_unresolved_gap_unresolved'
    A = np.diag([1., 1., 0.]); y = np.array([0., 0., .002])
    models = dict(old=np.zeros(3), proxy=np.array([.001, 0., 0.]), intact=np.array([.003, 0., 0.]))
    _, q = d.project(A, y, models, time.monotonic(), time.monotonic)
    assert q['rows'][0]['state'] == 'floor_resolved_gap_unresolved'
    assert q['rows'][1]['state'] == q['rows'][2]['state'] == 'floor_resolved_gap_resolved'
    assert len({r['decision_T_mm'] for r in q['rows']}) == 1


def test_rank_guard_zero_matrix_and_discarded_model_mode():
    for A, message in ((np.diag([1., 1e-12]), 'rank unresolved'), (np.zeros((2, 2)), 'nonzero finite')):
        with pytest.raises(ValueError, match=message):
            d.project(A, np.zeros(2), {k: np.zeros(2) for k in d.ARMS}, time.monotonic(), time.monotonic)
    with pytest.raises(ValueError, match='retained-image'):
        d.project(np.diag([1., 1e-14]), np.zeros(2), {k: np.array([0., .001]) for k in d.ARMS}, time.monotonic(), time.monotonic)


@pytest.mark.parametrize('mutation', ['ids', 'duplicate', 'fractional', 'count', 'xyshape', 'roi', 'weights',
                                    'negativeweight', 'nan', 'mesh', 'tri', 'boundary', 'bcshape', 'bcvalue',
                                    'fieldshape', 'fieldnan', 'sample', 'sampleshape', 'cycle', 'reference', 'stage', 'force'])
def test_reject_inconsistent_synthetic_assets(tmp_path, mutation):
    prep, fit, _ = fixture(tmp_path)
    p, f = m.load(prep/'prepared.npz'), m.load(fit/'solved_fields.npz')
    meta, audit = (json.loads((prep/n).read_text()) for n in ('preparation.json', 'geometry_audit.json'))
    if mutation == 'ids': p['ids'][0] = -1
    if mutation == 'duplicate': p['ids'][0] = p['ids'][1]
    if mutation == 'fractional': p['ids'] = p['ids'].astype(float)+.1
    if mutation == 'count': meta['observations'] += 1
    if mutation == 'xyshape': p['xy'] = p['xy'][:-1]
    if mutation == 'roi': p['xy'][0, 0] = 16.2
    if mutation == 'weights': p['weights'] = p['weights'][:-1]
    if mutation == 'negativeweight': p['weights'][0] = -1
    if mutation == 'nan': p['train_v'][0, 0] = np.nan
    if mutation == 'mesh': p['mesh'][0, 0] += .01
    if mutation == 'tri': p['tri'][0] = p['tri'][0, ::-1]
    if mutation == 'boundary': p['boundary'][0] = False
    if mutation == 'bcshape': p['bc'] = p['bc'][:-1]
    if mutation == 'bcvalue': p['bc'][0, 0] += .01
    if mutation == 'fieldshape': f['old'] = f['old'][:-1]
    if mutation == 'fieldnan': f['old'][0, 0] = np.inf
    if mutation == 'sample': f['old_sampled'][0, 0] += .01
    if mutation == 'sampleshape': f['old_sampled'] = f['old_sampled'][:1]
    if mutation == 'cycle': audit['cycle'] = 'OTHER'
    if mutation == 'reference': meta['reference'] = 2
    if mutation == 'stage': audit['stages'] = [12, 14]
    if mutation == 'force': audit['training_headers'][0]['force'] = '99'
    np.savez_compressed(prep/'prepared.npz', **p); np.savez_compressed(fit/'solved_fields.npz', **f)
    m.write_json(prep/'preparation.json', meta); m.write_json(prep/'geometry_audit.json', audit)
    lock = rebind(prep, fit); out = tmp_path/'failed'
    with pytest.raises(ValueError): invoke(prep, fit, lock, out)
    assert json.loads((out/'execution_receipt.json').read_text())['execution_status'] == 'failed'
    assert not (out/'pointwise.npz').exists()


def test_boundaries_in_sampling_stop_instead_of_release(tmp_path):
    prep, fit, lock = fixture(tmp_path)
    p, f, _, _ = d.checked_inputs(prep, fit, lock)
    p['xy'][0] = [17.8, 0.]
    with pytest.raises(ValueError, match='nonzero boundary sampling'): d.analyze(p, f, time.monotonic(), time.monotonic)


@pytest.mark.parametrize('mutation', ['anchor', 'run', 'count', 'lineage', 'artifact', 'protocol'])
def test_reject_bindings_before_matrix(tmp_path, mutation):
    prep, fit, lock = fixture(tmp_path)
    if mutation == 'anchor': lock['prepare'] = 'OTHER'
    if mutation == 'run': lock['runs']['fit'] = 'OTHER'
    if mutation == 'count': lock['observations'] += 1
    if mutation == 'lineage':
        meta = json.loads((fit/'fit.json').read_text()); meta['source_prepare'] = {}
        m.write_json(fit/'fit.json', meta); receipt(fit, 'fit', m.FIT, m.bindings(prep, m.PREP))
        lock['fit'] = m.sha(fit/'execution_receipt.json')
    if mutation == 'artifact': (fit/'frozen_predictions.npz').write_bytes(b'SYNTHETIC_TAMPERED')
    with patch.object(d, 'PROTOCOL_SHA', 'OTHER' if mutation == 'protocol' else d.PROTOCOL_SHA), \
         patch.object(d, 'sampling', side_effect=AssertionError('identity before matrix')):
        with pytest.raises(ValueError): invoke(prep, fit, lock, tmp_path/'failed')


def test_default_anchors_before_array_load_and_no_override_flags(tmp_path):
    prep, fit, _ = fixture(tmp_path)
    with patch.object(m, 'load', side_effect=AssertionError('no data before real anchor')):
        with pytest.raises(ValueError, match='anchored'):
            d.run(prep, fit, tmp_path/'failed', 'SYNTHETIC', 'SYNTHETIC_ONLY')
    result = subprocess.run([sys.executable, d.__file__, '--help'], capture_output=True, text=True, check=True)
    for flag in ('--lock', '--budget', '--rcond', '--mesh'): assert flag not in result.stdout


def test_warning_stops_and_does_not_retry(tmp_path):
    prep, fit, lock = fixture(tmp_path); out = tmp_path/'failed'
    def warn(*args): warnings.warn('SYNTHETIC_CAPACITY_WARNING', RuntimeWarning)
    with patch.object(d, 'analyze', side_effect=warn):
        with pytest.raises(RuntimeWarning): invoke(prep, fit, lock, out)
    r = json.loads((out/'execution_receipt.json').read_text())
    assert r['execution_status'] == 'failed' and r['outputs_role'] == 'forensic_only'
    with pytest.raises(ValueError, match='fresh'): invoke(prep, fit, lock, out)


class Clock:
    value = 0.
    def __call__(self): return self.value


@pytest.mark.parametrize('phase', ['svd', 'save', 'draw', 'hash', 'final_receipt'])
def test_budget_covers_svd_and_finalization(tmp_path, phase):
    prep, fit, lock = fixture(tmp_path); out = tmp_path/'failed'; timer = Clock()
    svd, save, draw, hashes, write = d.linalg.svd, d.np.savez_compressed, d.draw, d.hashes, m.write_json
    calls = 0
    def svd_call(*args, **kwargs):
        result = svd(*args, **kwargs)
        if phase == 'svd': timer.value = 60.
        return result
    def save_call(*args, **kwargs):
        save(*args, **kwargs)
        if phase == 'save': timer.value = 60.
    def draw_call(*args):
        draw(*args)
        if phase == 'draw': timer.value = 60.
    def hash_call(paths):
        nonlocal calls
        calls += 1; result = hashes(paths)
        if phase == 'hash' and calls == 2: timer.value = 60.
        return result
    def write_call(path, value):
        write(path, value)
        if phase == 'final_receipt' and value.get('execution_status') == 'succeeded': timer.value = 60.
    with patch.object(d.linalg, 'svd', side_effect=svd_call), patch.object(d.np, 'savez_compressed', side_effect=save_call), \
         patch.object(d, 'draw', side_effect=draw_call), patch.object(d, 'hashes', side_effect=hash_call), \
         patch.object(m, 'write_json', side_effect=write_call):
        with pytest.raises(TimeoutError): invoke(prep, fit, lock, out, clock=timer)
    r = json.loads((out/'execution_receipt.json').read_text())
    assert r['execution_status'] == 'failed' and r['outputs_role'] == 'forensic_only'


def test_source_mutation_detected_after_draw(tmp_path):
    prep, fit, lock = fixture(tmp_path); out = tmp_path/'failed'; draw = d.draw
    def change(*args):
        draw(*args); (prep/'geometry_audit.json').write_text('SYNTHETIC_CHANGED')
    with patch.object(d, 'draw', side_effect=change):
        with pytest.raises(ValueError, match='source changed'): invoke(prep, fit, lock, out)


def test_zero_fields_and_output_overlap(tmp_path):
    prep, fit, lock = fixture(tmp_path, zero=True)
    with pytest.raises(ValueError, match='overlap'): invoke(prep, fit, lock, fit/'new')
    assert not (fit/'new').exists()
    out = tmp_path/'zero'; invoke(prep, fit, lock, out)
    q = json.loads((out/'report.json').read_text())
    assert all(r['J_model_mm2'] == 0 and r['state'] == 'floor_unresolved_gap_unresolved' for r in q['rows'])


def test_cli_thread_warning_environment_and_synthetic_command(tmp_path, monkeypatch):
    prep, fit, lock = fixture(tmp_path); out = tmp_path/'cli'
    monkeypatch.setattr(d, 'DEFAULT_LOCK', lock)
    monkeypatch.setattr(sys, 'argv', [d.__file__, '--prepare', str(prep), '--fit', str(fit), '--output', str(out),
                                    '--source-commit', 'SYNTHETIC', '--run-id', 'SYNTHETIC_ONLY_CLI'])
    for name in d.THREADS: monkeypatch.setenv(name, '1')
    monkeypatch.setenv('PYTHONWARNINGS', 'default')
    with pytest.raises(ValueError, match='PYTHONWARNINGS'): d.main()
    monkeypatch.setenv('PYTHONWARNINGS', 'error'); monkeypatch.setenv('MKL_NUM_THREADS', '2')
    with pytest.raises(ValueError, match='single-thread'): d.main()
    assert not out.exists()
    monkeypatch.setenv('MKL_NUM_THREADS', '1'); d.main()
    assert json.loads((out/'execution_receipt.json').read_text())['execution_status'] == 'succeeded'
