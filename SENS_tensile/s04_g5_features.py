"""Causal PINN-only feature contract; no FEM target/event inputs or fitting."""
import numpy as np
from scipy.spatial import cKDTree

FIELDS = ('damage', 'alpha_bar', 'fatigue_f', 'psi_raw_direct')


class FeaturePipeline:
    def __init__(self, centers, areas, contained):
        self.ids = np.flatnonzero(contained)
        self.centers = np.asarray(centers, dtype=float)[self.ids]
        self.areas = np.asarray(areas, dtype=float)[self.ids]
        assert len(self.ids) >= 9 and np.isfinite(self.centers).all()
        assert np.isfinite(self.areas).all() and np.all(self.areas > 0)
        self.neighbors = cKDTree(self.centers).query(self.centers, k=9)[1]
        self.names = ([f'current_{k}' for k in (*FIELDS, 'active_proxy')]
                      + [f'lag{j}_{k}' for j in (1, 2) for k in (*FIELDS, 'active_proxy')]
                      + ['lag1_missing', 'lag2_missing', 'x', 'y', 'log_area', 'Umax', 'physical_cycle']
                      + [f'current_global_{k}' for k in (*FIELDS, 'active_proxy')]
                      + [f'current_neighbor_{k}' for k in (*FIELDS, 'active_proxy')])

    def channels(self, pin, scales):
        assert set(pin) == set(FIELDS), 'Only explicitly whitelisted PINN fields accepted'
        h, r = scales
        assert np.isfinite([h, r]).all() and h > 0 and r > 0
        d, ab, f, raw = [np.asarray(pin[k], dtype=float)[self.ids] for k in FIELDS]
        assert all(v.shape == self.areas.shape and np.isfinite(v).all() for v in (d, ab, f, raw))
        assert np.all(ab >= 0) and np.all(raw >= 0) and np.all((f >= 0) & (f <= 1))
        proxy = (1-d)**2*raw  # Auxiliary only, not native joint active driver.
        value = np.column_stack((d, np.log1p(ab/h), f, np.log1p(raw/r), np.log1p(proxy/r)))
        assert np.isfinite(value).all()
        return value

    def build(self, current_pin, lag1_pin, lag2_pin, cycle, umax, scales, rows=None):
        assert isinstance(cycle, int) and cycle >= 1 and np.isfinite(umax) and umax > 0
        assert (lag1_pin is None) == (cycle == 1)
        assert (lag2_pin is None) == (cycle <= 2)
        cur = self.channels(current_pin, scales)
        rows = np.arange(len(self.ids)) if rows is None else np.asarray(rows, dtype=int)
        assert rows.ndim == 1 and np.all((rows >= 0) & (rows < len(self.ids)))
        lag = [np.zeros_like(cur) if p is None else self.channels(p, scales) for p in (lag1_pin, lag2_pin)]
        # Zeros are masked missing-feature sentinels, never fabricated C0 states.
        geom = np.column_stack((self.centers[rows], np.log(self.areas[rows])))
        global_pin = np.average(cur, axis=0, weights=self.areas)
        neighbor_pin = cur[self.neighbors[rows]].mean(axis=1)
        repeat = lambda x: np.broadcast_to(np.asarray(x), (len(rows), len(x)))
        x = np.column_stack((cur[rows], lag[0][rows], lag[1][rows],
                             repeat([lag1_pin is None, lag2_pin is None]), geom,
                             repeat([umax, cycle]), repeat(global_pin), neighbor_pin))
        assert x.shape == (len(rows), len(self.names)) and np.isfinite(x).all()
        return x

    def trajectory_cycle(self, pin_fields, cycle, umax, scales, rows=None):
        """Contiguous c1..cN/s4 archive; slice current and past rows ONLY."""
        assert set(pin_fields) == set(FIELDS)
        shapes = {np.asarray(v).shape for v in pin_fields.values()}
        assert len(shapes) == 1
        shape = shapes.pop(); assert len(shape) == 2 and 1 <= cycle <= shape[0]
        at = lambda i: {k: v[i] for k, v in pin_fields.items()}
        return self.build(at(cycle-1), at(cycle-2) if cycle > 1 else None,
                          at(cycle-3) if cycle > 2 else None, cycle, umax, scales, rows)


def sanity():
    centers = np.column_stack((np.arange(10)/10, np.zeros(10)))
    contained = np.array([True]*9+[False]); areas = np.ones(10)
    f = FeaturePipeline(centers, areas, contained)
    pin = {k: np.ones(10)*.1 for k in FIELDS}; pin['damage'][0] = -.001
    pin['damage'][-1] = np.nan  # Excluded values must not contaminate globals/neighbors.
    a = f.build(pin, None, None, 1, .115, (1., 1.))
    assert a.shape == (9, 32) and a[0, 0] < 0
    assert np.all(a[:, 15:17] == 1)
    try:
        f.build(dict(pin, FEM_event=np.zeros(10)), None, None, 1, .115, (1., 1.))
    except AssertionError:
        pass
    else:
        raise AssertionError('Forbidden feature accepted')
    b = f.build(pin, pin, None, 2, .115, (1., 1.), rows=[0, 3])
    assert b.shape == (2, 32) and np.all(b[:, 15] == 0) and np.all(b[:, 16] == 1)
    stack = {k: np.stack([v]*4) for k, v in pin.items()}
    before = f.trajectory_cycle(stack, 2, .115, (1., 1.))
    for value in stack.values(): value[2:] = 1e10
    assert np.array_equal(before, f.trajectory_cycle(stack, 2, .115, (1., 1.)))
    print('PASS whitelist, signed alpha, excluded-domain isolation, missing lags, row sampling, future perturbation')


if __name__ == '__main__':
    sanity()
