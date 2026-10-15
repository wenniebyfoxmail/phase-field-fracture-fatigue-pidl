"""E018 synthetic-only: no original ZIP, real fields, held response or solve."""
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
import aa2024_training_profile_consistency as d
from test_aa2024_geometry_result_view import receipt


def field(xy, affine=False):
    x, y = xy.T
    u = .0003*x - .0008*y + .002
    v = .0005*x + .0002*y - .001
    if not affine:
        u = u + .00001*x*y + .000003*x*x
        v = v + .00002*y*x*x + .000001*y*y
    return np.c_[u, v]


def rebind(prep, fit):
    receipt(prep, 'prepare', m.PREP)
    fm = json.loads((fit / 'fit.json').read_text())
    fm['source_prepare'] = m.bindings(prep, m.PREP)
    m.write_json(fit / 'fit.json', fm)
    receipt(fit, 'fit', m.FIT, m.bindings(prep, m.PREP))
    p, g = m.load(prep / 'prepared.npz'), m.load(prep / 'training_geometry.npz')
    return dict(prepare=m.sha(prep / 'execution_receipt.json'), fit=m.sha(fit / 'execution_receipt.json'),
                runs=dict(prepare='SYNTHETIC_ONLY_prepare', fit='SYNTHETIC_ONLY_fit'),
                observations=len(p['ids']), source_facets=len(g['ids']))


def fixture(tmp_path, *, affine=False, zero=False, negative=False):
    prep, fit = tmp_path / 'prepare', tmp_path / 'fit'
    prep.mkdir(); fit.mkdir()
    query = np.c_[np.tile(m.X, 2), np.repeat([3.6, -3.6], 53)]
    offsets = np.array([[-.2, -.2], [.2, -.2], [-.2, .2], [.2, .2]])
    xy = (query[:, None, :] + offsets).reshape(-1, 2)
    ids = 101 + 7*np.arange(len(xy))  # non-contiguous original IDs, not ID-1
    coeff = np.array([-.1, .6, .6, -.1]) if negative else np.full(4, .25)
    uv = np.zeros_like(xy) if zero else field(xy, affine)
    # Reverse the source array to force genuine ID mapping through a filtered table.
    np.savez_compressed(prep / 'training_geometry.npz', ids=ids[::-1], xy=xy[::-1],
                        xyz=np.c_[xy, .02*xy[:, 0]][::-1], du=np.c_[uv, .1*uv[:, 0]][::-1])
    selected = np.arange(4*len(query)).reshape(106, 4)[d.SELECT].ravel()[::3]
    obsxy = xy[selected]; n = len(selected)
    mesh, tri, bd = m.rectangular_mesh()
    p = dict(ids=ids[selected], xy=obsxy, train_v=uv[selected], weights=np.linspace(.2, 2, n),
             mesh=mesh, tri=tri, boundary=bd, bc=np.zeros((len(bd), 2)))
    np.savez_compressed(prep / 'prepared.npz', **p)
    notes = []
    for i, q in enumerate(query):
        notes.append(dict(query_xy_mm=q.tolist(), neighbor_ids=ids[4*i:4*i+4].tolist(),
                          coefficients=coeff.tolist(), rank=3, supported=True,
                          fourth_distance_mm=float(np.sqrt(np.sum(offsets**2, axis=1)).max())))
    dic = np.sum(coeff[None, :, None]*uv.reshape(106, 4, 2), axis=1)
    profile = dict(gauge_mm=3.6, x_mm=m.X.tolist(), opening_mm=(dic[:53, 1]-dic[53:, 1]).tolist(),
                   interpolation=notes)
    headers = [dict(current_stage_index=str(i), reference_stage_index='1', cycles='292018.5',
                    force=str(j)) for i, j in ((13, 100), (14, 200))]
    m.write_json(prep / 'geometry_audit.json', dict(cycle='292018.5', stages=[13, 14],
                 training_headers=headers, profiles={'3.6': profile}))
    m.write_json(prep / 'preparation.json', dict(cycle='292018.5', reference=1, forces=[100., 200., 300.]))
    solved = {}
    for i, k in enumerate(d.ARMS):
        values = np.zeros_like(mesh) if zero else field(mesh, affine)
        if not affine and not zero:
            taper = (1-(mesh[:, 0]/18)**2)*(1-(mesh[:, 1]/9)**2)
            values += (i+1)*.00005*taper[:, None]*np.c_[mesh[:, 1], mesh[:, 0]]
        solved[k] = values
        solved[k + '_sampled'] = m.sample_regular_mesh(values, obsxy)
    np.savez_compressed(fit / 'solved_fields.npz', **solved)
    # Intentionally not an NPZ: must only be byte-hashed, never opened with load.
    (fit / 'frozen_predictions.npz').write_bytes(b'SYNTHETIC_ONLY_OPAQUE_HIGH_PREDICTIONS')
    m.write_json(fit / 'fit.json', dict(cycle='292018.5', status='four_predictions_frozen_before_held_response'))
    return prep, fit, rebind(prep, fit)


def invoke(prep, fit, lock, out, **kw):
    return d.run(prep, fit, out, 'SYNTHETIC_SOURCE', 'SYNTHETIC_ONLY_E018', lock=lock, **kw)


def test_end_to_end_no_target_no_solver_source_immutable(tmp_path):
    prep, fit, lock = fixture(tmp_path, negative=True); out = tmp_path / 'analysis'
    before = {str(p): m.sha(p) for r in (prep, fit) for p in r.iterdir()}
    original_load = m.load
    loaded = []
    def training_only(path):
        loaded.append(Path(path).name)
        assert Path(path).name in ('prepared.npz', 'training_geometry.npz', 'solved_fields.npz')
        return original_load(path)
    with patch.object(m, 'load', side_effect=training_only), \
         patch.object(m, 'prepare', side_effect=AssertionError('no prepare')), \
         patch.object(m, 'fit', side_effect=AssertionError('no fit')), \
         patch.object(m, 'validate', side_effect=AssertionError('no validate')), \
         patch.object(m, 'parse_nodemap', side_effect=AssertionError('no parser')), \
         patch.object(m, 'solve_patch', side_effect=AssertionError('no solve')), \
         patch.object(d.helpers, 'run', side_effect=AssertionError('no E017')), \
         patch.object(d.helpers.view, 'render', side_effect=AssertionError('no old render')):
        invoke(prep, fit, lock, out)
    assert len(loaded) == 3
    assert before == {p: m.sha(p) for p in before}
    r = json.loads((out / 'execution_receipt.json').read_text())
    assert r['execution_status'] == 'succeeded'
    assert r['sources_before_sha256'] == r['sources_after_sha256']
    assert len(r['artifacts_sha256']) == 11
    for name, sha in r['artifacts_sha256'].items(): assert m.sha(out / name) == sha
    assert len(list(out.glob('*.png'))) == len(list(out.glob('*.pdf'))) == 2
    assert len(json.loads((out / 'report.json').read_text())['rows']) == 3
    a = original_load(out / 'profiles.npz')
    assert a['neighbor_ids'].shape == (74, 4) and a['J_dic'].shape == (37, 2)
    assert a['coefficients'].min() < 0
    subprocess.run([sys.executable, 'source/validate_figure_sidecars.py', str(out)],
                   cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)
    assert 'SYNTHETIC_ONLY' in (out / 'README_analysis.md').read_text()
    with pytest.raises(ValueError, match='fresh'): invoke(prep, fit, lock, out)
    print('SYNTHETIC_E018_FIGURES=' + str(out))


def scalar_theta(xy, uv, w):
    total = math.fsum(w)
    center = [math.fsum(float(a)*float(x[j]) for a, x in zip(w, xy))/total for j in (0, 1)]
    shift = [math.fsum(float(a)*float(u[j]) for a, u in zip(w, uv))/total for j in (0, 1)]
    r = [(-(x[1]-center[1]), x[0]-center[0]) for x in xy]
    return math.fsum(float(a)*(v[0]*(u[0]-shift[0])+v[1]*(u[1]-shift[1])) for a, u, v in zip(w, uv, r)) / \
        math.fsum(float(a)*(v[0]**2+v[1]**2) for a, v in zip(w, r))


def test_id_mapping_projection_and_independent_scalar_arithmetic(tmp_path):
    prep, fit, lock = fixture(tmp_path)
    c, lineage, _ = d.checked_inputs(prep, fit, lock)
    a, rows, detail, _ = d.profiles(c)
    p = c['prepared']
    expected = scalar_theta(p['xy'], p['train_v'], p['weights'])
    assert c['dic_angle'] == pytest.approx(expected, abs=1e-15, rel=1e-12)
    assert lineage['projection_observations'] == len(p['ids'])
    assert len(detail) == 111
    # Profile-based rotation would be different; the full observation support is required.
    assert abs(d.theta(c['query'], c['dic'], np.ones(74)) - expected) > 1e-7
    for i, q in enumerate(c['query']):
        vals = field(c['neighbor_xy'][i])
        for j in (0, 1):
            value = math.fsum(float(v)*float(u[j]) for v, u in zip(c['coefficients'][i], vals))
            assert c['dic'][i, j] == pytest.approx(value, abs=1e-15)
    for row in rows:
        k = row['arm']
        np.testing.assert_allclose(a[k+'_r_direct'], a[k+'_r_op']+a[k+'_r_match'], atol=1e-15, rtol=1e-12)
        norm_mean = lambda z: math.fsum(math.hypot(*v) for v in z)/37
        assert row['L_direct_mm'] == pytest.approx(norm_mean(a[k+'_r_direct']), abs=1e-15)
        assert row['A_mm'] == pytest.approx(norm_mean(a[k+'_r_direct'])-norm_mean(a[k+'_r_match']), abs=1e-15)
        assert np.array_equal(a[k+'_J_direct']-a[k+'_J_match'], a[k+'_r_op'])


@pytest.mark.parametrize('negative', [False, True])
def test_affine_reproduction_both_interfaces_and_shared_theta(tmp_path, negative):
    prep, fit, lock = fixture(tmp_path, affine=True, negative=negative)
    c, _, _ = d.checked_inputs(prep, fit, lock)
    a, _, _, _ = d.profiles(c)
    for k in d.ARMS:
        np.testing.assert_allclose(a[k+'_direct'], field(c['query'], True), atol=1e-15, rtol=1e-12)
        np.testing.assert_allclose(a[k+'_match'], a[k+'_direct'], atol=1e-15, rtol=1e-12)
        np.testing.assert_allclose(a[k+'_r_direct'], 0, atol=1e-15)
        assert a[k+'_theta'] == pytest.approx(a['theta_dic'], abs=1e-15)


@pytest.mark.parametrize('angle,shift', [(0., [2., -3.]), (.002, [.7, .9]), (-.003, [-.8, .6])])
def test_pure_rigid_correction_sign_and_translation(angle, shift):
    xy = np.array([[-8., -5.], [2., 6.], [9., -1.], [-2., 4.]])
    rigid = lambda q: np.array(shift)+angle*np.c_[-q[:, 1], q[:, 0]]
    w = np.array([1., 3., 2., 7.])
    theta = d.theta(xy, rigid(xy), w)
    assert theta == pytest.approx(angle, abs=1e-16)
    q = np.c_[np.tile(d.X, 2), np.repeat([3.6, -3.6], 37)]
    np.testing.assert_allclose(d.pair(rigid(q), theta), 0, atol=1e-15)


def test_norms_are_not_additive_and_domain_guard():
    # Orthogonal vectors: the vector identity does not imply a scalar budget.
    a, b = np.tile([.001, 0.], (37, 1)), np.tile([0., .002], (37, 1))
    direct = a+b
    assert np.mean(d.helpers.norm(direct)) != pytest.approx(np.mean(d.helpers.norm(a))+np.mean(d.helpers.norm(b)))
    for xy in (np.array([[18.01, 0.]]), np.array([[0., -9.01]]), np.array([[np.nan, 0.]])):
        with pytest.raises(ValueError, match='domain'): d.in_domain(xy)
    with pytest.raises(ValueError, match='rigid rank'):
        d.theta(np.ones((4, 2)), np.zeros((4, 2)), np.ones(4))


@pytest.mark.parametrize('mutation', [
    'obs_id', 'duplicate_id', 'fractional_id', 'xy', 'train_v', 'weights', 'mesh', 'tri', 'sample', 'sample_shape',
    'field_shape', 'nan', 'xyz', 'source_shape', 'query', 'neighbor_missing', 'neighbor_duplicate',
    'coeff', 'moment', 'rank', 'unsupported', 'side', 'distance', 'domain', 'opening', 'stage', 'cycle', 'forces'])
def test_reject_inconsistent_synthetic_assets_before_output(tmp_path, mutation):
    prep, fit, _ = fixture(tmp_path)
    p, g, s = m.load(prep/'prepared.npz'), m.load(prep/'training_geometry.npz'), m.load(fit/'solved_fields.npz')
    audit = json.loads((prep/'geometry_audit.json').read_text()); note = audit['profiles']['3.6']['interpolation'][8]
    profile = audit['profiles']['3.6']
    if mutation == 'obs_id': p['ids'][0] = -100
    if mutation == 'duplicate_id': g['ids'][0] = g['ids'][1]
    if mutation == 'fractional_id': g['ids'] = g['ids'].astype(float)+.5
    if mutation == 'xy': p['xy'][0, 0] += .001
    if mutation == 'train_v': p['train_v'][0, 0] += .001
    if mutation == 'weights': p['weights'][0] = 0
    if mutation == 'mesh': p['mesh'][0, 0] += .001
    if mutation == 'tri': p['tri'][0] = p['tri'][0, ::-1]
    if mutation == 'sample': s['old_sampled'][0, 0] += .001
    if mutation == 'sample_shape': s['old_sampled'] = s['old_sampled'][:1]
    if mutation == 'field_shape': s['old'] = s['old'][:-1]
    if mutation == 'nan': s['old'][0, 0] = np.nan
    if mutation == 'xyz': g['xyz'][0, 0] += .001
    if mutation == 'source_shape': g['du'] = g['du'][:, :2]
    if mutation == 'query': note['query_xy_mm'][0] += .1
    if mutation == 'neighbor_missing': note['neighbor_ids'][0] = -100
    if mutation == 'neighbor_duplicate': note['neighbor_ids'][0] = note['neighbor_ids'][1]
    if mutation == 'coeff': note['coefficients'] = [1., 0., 0.]
    if mutation == 'moment': note['coefficients'][0] += .01
    if mutation == 'rank': note['rank'] = 2
    if mutation == 'unsupported': note['supported'] = False
    if mutation == 'side':
        note['neighbor_ids'] = audit['profiles']['3.6']['interpolation'][61]['neighbor_ids']
    if mutation == 'distance': note['fourth_distance_mm'] = .1
    if mutation == 'domain':
        idx = np.flatnonzero(g['ids'] == note['neighbor_ids'][0])[0]
        g['xy'][idx, 0] = -18.1; g['xyz'][idx, 0] = -18.1
    if mutation == 'opening': profile['opening_mm'][8] += .001
    if mutation == 'stage': audit['stages'] = [12, 14]
    if mutation == 'cycle': audit['cycle'] = 'OTHER'
    if mutation == 'forces': audit['training_headers'] = []
    np.savez_compressed(prep/'prepared.npz', **p); np.savez_compressed(prep/'training_geometry.npz', **g)
    np.savez_compressed(fit/'solved_fields.npz', **s); m.write_json(prep/'geometry_audit.json', audit)
    lock = rebind(prep, fit); out = tmp_path/'failed'
    with pytest.raises(ValueError): invoke(prep, fit, lock, out)
    r = json.loads((out/'execution_receipt.json').read_text())
    assert r['execution_status'] == 'failed' and r['outputs_role'] == 'forensic_only'
    assert not (out/'profiles.npz').exists()


def test_default_anchors_before_arrays_and_no_override_cli(tmp_path):
    prep, fit, _ = fixture(tmp_path)
    with patch.object(m, 'load', side_effect=AssertionError('no array before anchor')):
        with pytest.raises(ValueError, match='anchored'):
            d.run(prep, fit, tmp_path/'failed', 'SYNTHETIC', 'SYNTHETIC_ONLY')
    result = subprocess.run([sys.executable, d.__file__, '--help'], check=True, capture_output=True, text=True)
    assert '--lock' not in result.stdout and '--budget' not in result.stdout


def test_warning_stops_without_retry(tmp_path):
    prep, fit, lock = fixture(tmp_path); out = tmp_path/'failed'
    def warn(*args): warnings.warn('SYNTHETIC_ANOMALY', RuntimeWarning)
    with patch.object(d, 'profiles', side_effect=warn):
        with pytest.raises(RuntimeWarning): invoke(prep, fit, lock, out)
    assert json.loads((out/'execution_receipt.json').read_text())['execution_status'] == 'failed'
    with pytest.raises(ValueError, match='fresh'): invoke(prep, fit, lock, out)


class Clock:
    value = 0.
    def __call__(self): return self.value


@pytest.mark.parametrize('phase', ['save', 'hash', 'final_receipt'])
def test_budget_covers_final_save_hash_and_receipt(tmp_path, phase):
    prep, fit, lock = fixture(tmp_path); out = tmp_path/'failed'; timer = Clock()
    original_save, original_hashes, original_write = d.np.savez_compressed, d.helpers.hashes, m.write_json
    calls = 0
    def save(*args, **kw):
        original_save(*args, **kw)
        if phase == 'save': timer.value = 60.
    def hashes(paths):
        nonlocal calls
        calls += 1; result = original_hashes(paths)
        if phase == 'hash' and calls == 2: timer.value = 60.
        return result
    def write(path, value):
        original_write(path, value)
        if phase == 'final_receipt' and value.get('execution_status') == 'succeeded': timer.value = 60.
    with patch.object(d.np, 'savez_compressed', side_effect=save), patch.object(d.helpers, 'hashes', side_effect=hashes), \
         patch.object(m, 'write_json', side_effect=write):
        with pytest.raises(TimeoutError): invoke(prep, fit, lock, out, clock=timer)
    r = json.loads((out/'execution_receipt.json').read_text())
    assert r['execution_status'] == 'failed' and r['outputs_role'] == 'forensic_only'


def test_source_change_after_draw(tmp_path):
    prep, fit, lock = fixture(tmp_path); out = tmp_path/'failed'; original = d.draw
    def change(*args):
        original(*args); (prep/'geometry_audit.json').write_text('SYNTHETIC_CHANGED')
    with patch.object(d, 'draw', side_effect=change):
        with pytest.raises(ValueError, match='source changed'): invoke(prep, fit, lock, out)


def test_zero_fields_and_output_overlap(tmp_path):
    prep, fit, lock = fixture(tmp_path, zero=True)
    with pytest.raises(ValueError, match='overlap'): invoke(prep, fit, lock, fit/'new')
    assert not (fit/'new').exists()
    out = tmp_path/'zero'; invoke(prep, fit, lock, out)
    report = json.loads((out/'report.json').read_text())
    assert all(row['A_sign'] == 'numerically_unresolved' and row['L_direct_mm'] == 0 for row in report['rows'])


def test_cli_environment_guards(tmp_path, monkeypatch):
    prep, fit, lock = fixture(tmp_path); out = tmp_path/'cli'
    monkeypatch.setattr(d, 'DEFAULT_LOCK', lock)
    monkeypatch.setattr(sys, 'argv', [d.__file__, '--prepare', str(prep), '--fit', str(fit), '--output', str(out),
                        '--source-commit', 'SYNTHETIC', '--run-id', 'SYNTHETIC_ONLY_CLI'])
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        monkeypatch.setenv(name, '1')
    monkeypatch.setenv('PYTHONWARNINGS', 'default')
    with pytest.raises(ValueError, match='PYTHONWARNINGS'): d.main()
    monkeypatch.setenv('PYTHONWARNINGS', 'error'); monkeypatch.setenv('NUMEXPR_NUM_THREADS', '2')
    with pytest.raises(ValueError, match='single-thread'): d.main()
    assert not out.exists()
    monkeypatch.setenv('NUMEXPR_NUM_THREADS', '1'); d.main()
    assert json.loads((out/'execution_receipt.json').read_text())['execution_status'] == 'succeeded'
