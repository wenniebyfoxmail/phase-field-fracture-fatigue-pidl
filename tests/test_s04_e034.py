"""Synthetic fixtures only: no real MAT/NPZ/PT, model loading, GPU or producer."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
import torch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'source'))
sys.path.insert(0, str(ROOT/'SENS_tensile'))
import s04_e027 as old
import s04_e034 as m
import run_s04_e034 as runner
import s04_e034_watchdog as watchdog


def geometry():
    basis = np.eye(802)[:8]
    gradients = np.zeros((11, 802)); gradients[:, 0] = 1; gradients[:, 20] = .3
    return m.Geometry(basis, gradients)


def oracle(n, gain=True):
    def evaluate(x):
        ratios = np.ones(13)+(.1*x[0] if gain else 0)
        jac = np.zeros((13, n)); jac[:, 0] = .1 if gain else 0
        return ratios, jac, dict(synthetic=True)
    return evaluate


class FiniteComparisonTests(unittest.TestCase):
    def test_common_denominators_nested_cones_and_zero_jacobian(self):
        g = geometry(); z = np.arange(8.)/30; h = np.einsum('i,ij->j', z, g.basis)
        a, j8 = g.constraints(z, 'F8'); b, jf = g.constraints(h, 'F802')
        np.testing.assert_allclose(a, b, atol=1e-15)
        np.testing.assert_allclose(j8, np.einsum('ij,kj->ik', jf, g.basis), atol=1e-15)
        c, j = g.constraints(np.zeros(8), 'F8')
        self.assertTrue(np.isfinite(j).all()); self.assertEqual(c[0], 1)
        # Full gradient normalization would change the inherited F8 cone.
        self.assertAlmostEqual(g.cone[0, 0], 1.)
        self.assertAlmostEqual(g.cone[0, 20], .3)
        eps = 1e-6; d = np.linspace(-.3, .2, 8)
        fd = (g.constraints(z+eps*d, 'F8')[0]-g.constraints(z-eps*d, 'F8')[0])/(2*eps)
        np.testing.assert_allclose(fd, np.einsum('ij,j->i', j8, d), atol=1e-9)

    def test_first_target_and_independent_zero_starts_both_dimensions(self):
        starts = []; verifications = []
        for arm, n in [('F8', 8), ('F802', 802)]:
            fn = oracle(n)
            def evaluate(x):
                starts.append((arm, x.copy()))
                return fn(x)
            cache = m.PointCache(arm, geometry(), evaluate, lambda x, r: verifications.append((arm, x.copy())), lambda row: None, lambda: None)
            x, result = m.solve_arm(cache)
            self.assertTrue(result['accepted']); self.assertEqual(cache.calls['actual_forward'], 1)
            self.assertLessEqual(result['distinct_points'], 120)
            self.assertTrue(m.meets_target(oracle(n)(x)[0], geometry().constraints(x, arm)[0]))
            self.assertTrue(np.array_equal(next(x for a, x in starts if a == arm), np.zeros(n)))
        self.assertEqual(len(verifications), 2)

    def test_exact_cache_last_allowed_point_and_121_stop(self):
        observations = []
        cache = m.PointCache('F8', geometry(), oracle(8, False), lambda x, r: None, observations.append, lambda: None)
        zero = np.zeros(8)
        cache.fun(zero); cache.jac(zero); cache.con(zero); cache.conjac(zero)
        self.assertEqual(cache.calls['physical'], 1)
        for i in range(1, 120):
            x = zero.copy(); x[1] = i/1000
            cache.fun(x)
        self.assertEqual(len(cache.rows), 120)
        x = zero.copy(); x[1] = .12
        with self.assertRaisesRegex(RuntimeError, 'cap'): cache.fun(x)
        self.assertEqual(cache.calls['physical'], 120)

    def test_no_tiny_gain_endpoint_and_allowed_status9(self):
        cache = m.PointCache('F8', geometry(), oracle(8, False), lambda x, r: None, lambda r: None, lambda: None)
        x, result = m.solve_arm(cache)
        self.assertFalse(result['accepted']); self.assertTrue(np.array_equal(x, np.zeros(8)))
        for status in (9, 8):
            with patch.object(m, 'minimize', return_value=SimpleNamespace(x=np.ones(8)*.01, status=status, message='fixture')):
                if status == 9:
                    x, result = m.solve_arm(cache)
                    self.assertFalse(result['accepted']); self.assertTrue(np.array_equal(x, np.zeros(8)))
                else:
                    with self.assertRaisesRegex(RuntimeError, 'status 8'): m.solve_arm(cache)

    def test_separate_reactions_no_slack_and_first_target_verify_failure_stops(self):
        ratios = np.full(13, .997)
        geometric = np.ones(12)
        self.assertTrue(m.meets_target(ratios, geometric))
        for index in (7, 11, 12):
            bad = ratios.copy(); bad[index] = np.nextafter(1., 2.)
            self.assertFalse(m.meets_target(bad, geometric))
        bad = ratios.copy(); bad[2] = .998001+1e-12
        self.assertFalse(m.meets_target(bad, geometric))
        def fail(x, r): raise ValueError('actual network mismatch')
        cache = m.PointCache('F8', geometry(), oracle(8), fail, lambda row: None, lambda: None)
        with self.assertRaisesRegex(ValueError, 'network mismatch'): m.solve_arm(cache)
        self.assertIsNone(cache.winner); self.assertEqual(cache.calls['actual_forward'], 1)

    def test_nonfinite_observation_persisted_and_stop(self):
        rows = []
        def bad(x): return np.full(13, np.nan), np.zeros((13, 8)), {}
        cache = m.PointCache('F8', geometry(), bad, lambda x, r: None, rows.append, lambda: None)
        with self.assertRaisesRegex(ValueError, 'nonfinite'): cache.fun(np.zeros(8))
        self.assertEqual(len(cache.rows), 1); self.assertTrue(np.isnan(rows[-1]['ratios']).all())

    def test_thirteen_native_metric_jacobians_and_affine_UV(self):
        xy = np.array([[x, y] for y in (-.5, -.02, .02, .5) for x in (-.2, .2)])
        conn = np.array([[2*i, 2*i+1, 2*i+3, 2*i+2] for i in range(3)])
        ref = np.column_stack((.001*xy[:, 0], old.US*(xy[:, 1]+.5), np.full(8, .3)))
        p = old.Problem(dict(xy=xy, conn=conn, ref=ref, previous=np.full(8, .1), f=np.ones((3, 4)), free_u=np.arange(16), free_d=np.arange(8)))
        features = torch.zeros((8, 400), dtype=torch.float64); features[:, :2] = p.xy
        theta = torch.zeros((2, 401), dtype=torch.float64)
        theta[:, :2] = torch.tensor([[.1, .02], [.02, .1]])
        theta[:, -1] = torch.tensor([.03, -.03])
        damage = torch.full((8,), .2, dtype=torch.float64)
        reference = tuple(a.detach() for a in p.parts(*p.ref.unbind(1)))
        matrix = np.zeros((8, 802)); indices = [0, 1, 400, 401, 402, 801, 2, 403]
        matrix[np.arange(8), indices] = 1
        matrix = torch.as_tensor(matrix, dtype=torch.float64)
        baseline = torch.ones(13, dtype=torch.float64)
        x = np.linspace(-.02, .03, 8); direction = np.linspace(-.2, .4, 8); eps = 1e-6
        def evaluate(z): return m.values_and_jacobian(p, theta, features, damage, matrix, z, baseline, reference, 1.)
        r, j, extra = evaluate(x)
        fd = (evaluate(x+eps*direction)[0]-evaluate(x-eps*direction)[0])/(2*eps)
        np.testing.assert_allclose(np.einsum('ij,j->i', j, direction), fd, rtol=2e-5, atol=1e-7)
        self.assertEqual(len(extra['reactions']), 2)
        self.assertAlmostEqual(r[0], r[7]+r[9], places=13)
        self.assertAlmostEqual(r[1], r[8]+r[10], places=13)

    def test_projection_attribution_thresholds_and_frozen_radius(self):
        g = geometry(); h = np.zeros(802); h[0] = .2
        z, info = g.decompose(h)
        self.assertEqual(info['outside_norm'], 0); self.assertEqual(z[0], .2)
        h[20] = 1e-8
        self.assertGreaterEqual(g.decompose(h)[1]['outside_norm'], 1e-8)
        with self.assertRaisesRegex(ValueError, 'radius'): m.Geometry(g.basis, np.ones((11, 802)), radius=.1)

    def test_authorization_fails_before_any_resource_or_input_call(self):
        lock = json.loads((ROOT/'docs/research/S04/S04-E034/data_lock.json').read_text())
        grant = json.loads((ROOT/'docs/research/S04/S04-E034/grant.template.json').read_text())
        with patch.object(runner.platform, 'system', return_value='Linux'), patch.object(runner.subprocess, 'check_output', side_effect=['fixturecommit', '']), patch.object(runner, 'device_admission', side_effect=AssertionError('must not inspect resources')):
            grant['approved_commit'] = 'fixturecommit'
            with self.assertRaisesRegex(PermissionError, 'authorization'): runner.authorization(lock, grant, Path(grant['output']))
        with patch.object(runner.platform, 'system', return_value='Darwin'), patch.object(runner.subprocess, 'check_output', side_effect=AssertionError('no IO')):
            with self.assertRaisesRegex(PermissionError, 'Mac'): runner.authorization(lock, grant, Path(grant['output']))

    def test_phase_quotas_do_not_transfer(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner.subprocess, 'Popen'):
            now = [0.]
            with patch.object(runner.time, 'monotonic', side_effect=lambda: now[0]):
                b = runner.Budget(Path(tmp), 0.)
                now[0] = 100; b.phase_to('F8')
                self.assertEqual(json.loads((Path(tmp)/'phase_deadline.json').read_text())['deadline'], 700)
                now[0] = 120; b.phase_to('F802')
                self.assertEqual(json.loads((Path(tmp)/'phase_deadline.json').read_text())['deadline'], 720)
                now[0] = 150; b.phase_to('shared')
                self.assertEqual(b.shared, 100)
                self.assertEqual(json.loads((Path(tmp)/'phase_deadline.json').read_text())['deadline'], 530)
                now[0] = 530
                with self.assertRaisesRegex(TimeoutError, 'shared'): b.guard()

    def test_arm_exports_charge_shared_and_arm_quota(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(runner.subprocess, 'Popen'):
            now = [0.]
            with patch.object(runner.time, 'monotonic', side_effect=lambda: now[0]):
                b = runner.Budget(Path(tmp), 0.)
                now[0] = 100; b.phase_to('F8')
                now[0] = 120
                with b.exporting():
                    self.assertEqual(json.loads((Path(tmp)/'phase_deadline.json').read_text())['deadline'], 500)
                    now[0] = 130
                self.assertEqual(b.shared, 110)
                self.assertEqual(b.phase_started, 100)

    def test_watchdog_terminates_only_named_parent_at_deadline(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp); (out/'phase_deadline.json').write_text(json.dumps(dict(pid=1234567, phase='F8', deadline=2)))
            with patch.object(watchdog.os, 'kill') as kill, patch.object(watchdog.time, 'monotonic', side_effect=[0., 2.]):
                watchdog.watch(1234567, out)
            self.assertEqual([c.args for c in kill.call_args_list], [(1234567, 0), (1234567, watchdog.signal.SIGTERM), (1234567, watchdog.signal.SIGKILL)])
            self.assertTrue((out/'watchdog_stop.json').exists())

    def test_synthetic_native_export_and_figure_sidecars(self):
        # This is a disposable synthetic three-element fixture, never an E034 result.
        xy = np.array([[x, y] for y in (-.5, -.02, .02, .5) for x in (-.2, .2)])
        ref = np.column_stack((.001*xy[:, 0], old.US*(xy[:, 1]+.5), np.full(8, .3)))
        p = old.Problem(dict(xy=xy, conn=np.array([[2*i, 2*i+1, 2*i+3, 2*i+2] for i in range(3)]), ref=ref,
                             previous=np.full(8, .1), f=np.ones((3, 4)), free_u=np.arange(16), free_d=np.arange(8)))
        q = p.ref.clone(); q[:, 0] *= 1.1; q[:, 2] = .2
        with tempfile.TemporaryDirectory(prefix='E034_SYNTHETIC_FIXTURE_') as tmp:
            out = Path(tmp); history = out/'history'; history.mkdir()
            np.savez_compressed(history/'fields.npz', endpoint=q.numpy())
            receipt = dict(snapshot_physics_calls=0, e033_output=str(history))
            runner.snapshot(p, q, out, 'Z0', receipt)
            endpoints = {}
            for arm in ('F8', 'F802'):
                armout = out/arm; armout.mkdir()
                runner.snapshot(p, q, armout, 'endpoint', receipt)
                (armout/'points.jsonl').write_text(json.dumps(dict(index=1, ratios=[1.]*13))+'\n')
                endpoints[arm] = dict(q=q.numpy(), accepted=False)
            runner.render(out, p, endpoints, dict(reference=ref, UVjoint=q.numpy()), receipt)
            images = list(out.glob('*.png'))
            self.assertEqual(len(images), 9)
            for path in images:
                text = path.with_suffix('.md').read_text().lower()
                for term in ('how to read', 'data provenance', 'limitation'): self.assertIn(term, text)
            payload = np.load(out/'Z0.npz')
            self.assertEqual(payload['stress'].shape, (3, 4, 3))
            self.assertTrue(np.array_equal(payload['fields'][:, 2], np.full(8, .2)))


if __name__ == '__main__': unittest.main()
