"""Offline preparation seam only: frozen E028 fields -> two GT-free columns.

No loader, fitting, forward, evaluation, producer entry point or network access.
"""
import importlib.util
from pathlib import Path
import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    'e029_frozen_e028_geometry', _ROOT / 'scripts/pavetrack_target_spatial/geometry.py')
geometry = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(geometry)

ARMS = ('aligned', 'half_shift')


def _box(value):
    a = np.asarray(value, dtype=np.float64)
    if a.shape != (4,) or not np.isfinite(a).all() or a[2] <= a[0] or a[3] <= a[1]:
        raise ValueError('positive finite xyxy box required')
    return a


def coverage(value, context):
    """Fractional box overlap with the exact E028 32x32 continuous bins."""
    b, ctx = _box(value), _box(context)
    xs = np.linspace(ctx[0], ctx[2], 33)
    ys = np.linspace(ctx[1], ctx[3], 33)
    wx = np.maximum(0, np.minimum(xs[1:], b[2]) - np.maximum(xs[:-1], b[0])) / np.diff(xs)
    wy = np.maximum(0, np.minimum(ys[1:], b[3]) - np.maximum(ys[:-1], b[1])) / np.diff(ys)
    return wy[:, None] * wx[None, :]


def describe(projected_max, original_box, corrected_box, context, arm):
    """Fixed existence grid (>=.5, matching E028), no GT arguments.

    The shift preserves total occupied-bin count and all probability values.
    It changes alignment only, before both old/corrected box measurements.
    """
    if arm not in ARMS:
        raise ValueError('unfrozen arm')
    geometry.validate_probability(projected_max, (32, 32))
    p = projected_max if arm == 'aligned' else np.roll(projected_max, (16, 16), (0, 1))
    h = p >= np.float32(.5)
    mass = int(h.sum())
    cs, areas, inside = [], [], []
    for b in (original_box, corrected_box):
        cov = coverage(b, context)
        area = float(cov.mean())
        m = float(np.sum(h * cov))
        z = 0. if mass == 0 else m / mass - area
        cs.append(z); areas.append(area); inside.append(m)
    values = [cs[1], (cs[1] - cs[0]) / 2]
    if not np.isfinite(values).all() or any(abs(v) > 1 + 1e-12 for v in values):
        raise ValueError('descriptor bounds')
    return dict(values=values, concentrations=cs, areas=areas, inside_mass=inside,
                occupied_bins=mass, zero_mass=mass == 0, arm=arm)


def append_columns(old_values, descriptor):
    """Same six numeric columns as E022; no new trainable representation."""
    x = np.asarray(old_values, dtype=np.float64)
    z = np.asarray(descriptor['values'], dtype=np.float64)
    if x.shape != (4,) or z.shape != (2,) or not np.isfinite(x).all() or not np.isfinite(z).all():
        raise ValueError('numeric feature shape')
    if (x < 0).any() or (x > 1).any() or (abs(z) > 1 + 1e-12).any():
        raise ValueError('feature bounds')
    return np.concatenate((x, z)).tolist()


def partition(locations, held_groups):
    """Predeclared geographic roles; never choose sites from effect signs."""
    expected = ['24','95','151','514','728','1400','1577','1638','2027','3662','4494','5508']
    groups = [['24','514','1577','3662'], ['95','728','1638','4494'], ['151','1400','2027','5508']]
    if locations != expected or held_groups != groups:
        raise ValueError('frozen twelve-site partition')
    reused = {'24', '1638', '2027'}
    return dict(qualification_reused=[x for x in locations if x in reused],
                primary=[x for x in locations if x not in reused],
                folds=[dict(held=g, fit=[x for x in locations if x not in g],
                            primary_held=[x for x in g if x not in reused]) for g in groups])
