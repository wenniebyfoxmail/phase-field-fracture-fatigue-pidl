"""Artificial arrays and mocked orchestration only; no scientific trajectory."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from synthetic_history_inputs import structured_q4_mesh
from synthetic_history_observation import (camera_damage, current_match,
                                          robust_difference, anchor_valid)
from synthetic_history_experiment import frozen_spec, validate_spec, schedule_for, subdivide
from run_synthetic_history import verify_authority


def test_renderer_preserves_q4_affine_field_and_xy_order():
    mesh = structured_q4_mesh(4, 4, 0.)
    values = .5 + .2*mesh.points[:, 0] + .3*mesh.points[:, 1]
    observed = camera_damage(mesh, values)
    x = (np.arange(64)+.5)/64-.5
    expected = .5+.2*x[None, :]+.3*x[:, None]
    assert np.allclose(observed, expected, rtol=0., atol=4*np.finfo(float).eps)
    assert observed[50, 10] > observed[10, 50]


@pytest.mark.parametrize('cells', [16, 32])
def test_prescribed_anchor_is_visible_from_initial_seed_without_filling(cells):
    mesh = structured_q4_mesh(cells, cells, 0.)
    assert anchor_valid(camera_damage(mesh, mesh.crack.astype(float)) >= .5)


def test_matching_uses_whole_mask_not_summary_or_hidden_state():
    masks = np.zeros((3, 2, 64, 64), bool)
    masks[:, :, 31:33, 8:24] = True
    assert current_match(masks)['identical']
    masks[1, 0, 3, 4] = True
    result = current_match(masks)
    assert not result['identical'] and result['differing_pixels'] == 1
    assert result['anchor_valid']


def test_robust_pixels_require_within_arm_numerical_consistency():
    masks = np.zeros((3, 2, 64, 64), bool)
    masks[:, 1, 4, 5] = True
    masks[0, 1, 6, 7] = True  # base-only difference is numerical instability
    d = robust_difference(masks)
    assert d['robust_pixels'] == 1 and d['unstable_pixels'] == 1
    assert d['robust'][4, 5] and not d['robust'][6, 7]
    assert d['xor_pixels_by_variant'] == [2, 1, 1]
    assert d['unstable_pixels_by_arm'] == [0, 1]


def test_half_step_preserves_every_turning_point_including_unloading():
    assert subdivide([.25, .5, .75, 1., 0.], 2) == [.125, .25, .375, .5, .625, .75, .875, 1., .5, 0.]
    spec = frozen_spec()
    schedules = [schedule_for(spec, v, a) for v in spec['variants'] for a in ('low', 'high')]
    assert [len(s) for s in schedules] == [206, 206, 206, 206, 411, 411]
    assert sum(len(s) for s in schedules)+200 == spec['budget']['maximum_steps']
    for schedule in schedules:
        assert sum(s.phase == 'peak' for s in schedule) == 41
        assert sum(s.segment == 'settle' for s in schedule) == 1
        assert schedule[-1].cycle == 41 and schedule[-1].segment_cycle == 20


@pytest.mark.parametrize('change', ['threshold', 'amplitude', 'budget', 'mesh', 'solver'])
def test_no_silent_protocol_or_budget_expansion(change):
    spec = frozen_spec()
    if change == 'threshold': spec['observation']['threshold'] = .4
    if change == 'amplitude': spec['histories']['high'][0] = .02
    if change == 'budget': spec['budget']['wall_seconds'] += 1
    if change == 'mesh': spec['variants'][0]['cells'] = 8
    if change == 'solver': spec['solver']['damage_tolerance'] = 1e-6
    with pytest.raises(ValueError, match='differs'):
        validate_spec(spec)


def test_disabled_authority_rejects_before_git_or_process(monkeypatch):
    import run_synthetic_history as runner
    monkeypatch.setattr(runner, 'current_commit', lambda _: pytest.fail('git must not be called'))
    with pytest.raises(RuntimeError, match='approval'):
        verify_authority(frozen_spec(), {'enabled': False}, {}, Path('.'))


@pytest.mark.parametrize('location', ['source/numpy.py', 'tools/ignored_shadow.so'])
def test_untracked_or_ignored_import_shadow_is_rejected(tmp_path, monkeypatch, location):
    import run_synthetic_history as r
    shadow = tmp_path/location
    shadow.parent.mkdir()
    shadow.write_text('unreviewed')
    monkeypatch.setattr(r.subprocess, 'check_output', lambda *a, **k: 'source/tracked.py\0')
    with pytest.raises(RuntimeError, match='unreviewed import-tree'):
        r.verify_import_tree(tmp_path)


def test_untracked_package_directory_symlink_is_rejected(tmp_path, monkeypatch):
    import run_synthetic_history as r
    (tmp_path/'source').mkdir()
    (tmp_path/'external').mkdir()
    (tmp_path/'source/shadow').symlink_to(tmp_path/'external', target_is_directory=True)
    monkeypatch.setattr(r.subprocess, 'check_output', lambda *a, **k: '')
    with pytest.raises(RuntimeError, match='import-tree symlink'):
        r.verify_import_tree(tmp_path)


@pytest.mark.parametrize('failure', ['wall', 'storage'])
def test_final_resource_check_does_not_trust_exit_success(tmp_path, monkeypatch, failure):
    import run_synthetic_history as r
    spec = frozen_spec()
    monkeypatch.setattr(r, 'monotonic', lambda: 14400 if failure == 'wall' else 0.)
    monkeypatch.setattr(r, 'storage_size', lambda _: 8*1024**3+1 if failure == 'storage' else 0)
    with pytest.raises(RuntimeError, match='budget reached'):
        r.resource_check(spec, tmp_path, 0.)


@pytest.mark.parametrize('timeout_first', [False, True])
def test_worker_exit_race_does_not_interrupt_cleanup(monkeypatch, timeout_first):
    import run_synthetic_history as r
    calls = []
    class Process:
        pid = 12345
        def poll(self): return None
        def wait(self, timeout):
            calls.append(timeout)
            if timeout_first and len(calls) == 1:
                raise r.subprocess.TimeoutExpired('fake', timeout)
            return 0
    monkeypatch.setattr(r.os, 'killpg', lambda *args: (_ for _ in ()).throw(ProcessLookupError()))
    r.stop_worker(Process())
    assert calls == ([5, 5] if timeout_first else [5])


def test_no_future_is_executed_without_current_match(tmp_path, monkeypatch):
    import synthetic_history_experiment as e
    advanced = []
    class Fake:
        def __init__(self, spec, variant, arm, root, source_id, marker):
            self.variant, self.arm = variant, arm
            self.origin = 106
            self.schedule = [SimpleNamespace(segment='probe', phase='peak', step=105)]
            self.old = SimpleNamespace(damage=np.zeros(1), displacement=np.zeros(2),
                                      accumulated=np.zeros((1, 4)), fatigue=np.ones((1, 4)))
            self.mesh = self.backend = self.pair = None
        def advance(self, through):
            assert through in (1, self.origin)
            advanced.append(through)
        def state_path(self, step): return tmp_path/'fake'
    class Store:
        def __init__(self, path): pass
        def load(self): return SimpleNamespace(displacement=np.zeros(2)), {}
    monkeypatch.setattr(e, 'Trajectory', Fake)
    monkeypatch.setattr(e, 'StateStore', Store)
    monkeypatch.setattr(e, 'verify_pair_contract', lambda *a: True)
    monkeypatch.setattr(e, 'numeric_fields_equal', lambda *a: True)
    monkeypatch.setattr(e, 'compare_states', lambda *a: {})
    monkeypatch.setattr(e, 'mask_of', lambda *a: np.zeros((64, 64), bool))
    monkeypatch.setattr(e, 'camera_damage', lambda *a: np.zeros((64, 64)))
    monkeypatch.setattr(e, 'current_match', lambda *a: dict(anchor_valid=True, identical=False))
    result = e.run_experiment(frozen_spec(), tmp_path, 'unit', lambda *a: None)
    assert result['verdict'] == 'inconclusive' and result['future_executed'] is False
    assert len(advanced) == 12
