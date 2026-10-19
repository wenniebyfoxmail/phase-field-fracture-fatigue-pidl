"""E028 frozen observation operators; no model or labels in prediction paths."""
import numpy as np


def reflect_indices(start, length, size):
    if size < 2:
        raise ValueError('reflect requires at least two pixels')
    i = np.arange(start, start + length) % (2 * (size - 1))
    return np.where(i < size, i, 2 * (size - 1) - i)


def native_predict(rgb, predict, take):
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[0] != 3:
        raise ValueError('RGB CHW uint8')
    h, w = rgb.shape[1:]
    out = np.empty((h, w), np.float32)
    for y in range(0, h, 256):
        for x in range(0, w, 256):
            ys, xs = reflect_indices(y-128, 512, h), reflect_indices(x-128, 512, w)
            take('native_tiles')
            p = predict(np.ascontiguousarray(rgb[:, ys[:, None], xs]))
            validate_probability(p, (512, 512))
            hh, ww = min(256, h-y), min(256, w-x)
            out[y:y+hh, x:x+ww] = p[128:128+hh, 128:128+ww]
    return out


def validate_probability(p, shape):
    if p.shape != shape or p.dtype != np.float32 or not np.isfinite(p).all() or (p < 0).any() or (p > 1).any():
        raise ValueError('finite float32 probability shape/range')


def axis_weights(lo, hi, size):
    if not (0 <= lo < hi <= size):
        raise ValueError('context outside source')
    edges = np.linspace(lo, hi, 33)
    pixels = np.arange(size)
    weight = np.maximum(0, np.minimum(edges[1:, None], pixels+1) - np.maximum(edges[:-1, None], pixels))
    if not (weight.sum(1) > 0).all():
        raise ValueError('empty continuous bin')
    return weight


def reduce(field, context):
    """Overlap-weighted mean and existence maximum over native unit pixels."""
    a = np.asarray(field)
    if a.ndim != 2 or not np.isfinite(a).all():
        raise ValueError('finite 2D field')
    x1, y1, x2, y2 = context
    wx, wy = axis_weights(x1, x2, a.shape[1]), axis_weights(y1, y2, a.shape[0])
    # Restrict dense arithmetic to the context; no per-bin whole-image scans.
    xx, yy = np.flatnonzero(wx.sum(0)), np.flatnonzero(wy.sum(0))
    b = a[np.ix_(yy, xx)].astype(np.float64)
    wx, wy = wx[:, xx], wy[:, yy]
    weighted = np.einsum('ij,jk->ik', wy, b, optimize=False)
    integral = np.einsum('ij,kj->ik', weighted, wx, optimize=False)
    mean = integral / (wy.sum(1)[:, None] * wx.sum(1)[None, :])
    # Separability preserves exact max for fractional and subpixel-width bins.
    horizontal = np.stack([b[:, v > 0].max(1) for v in wx], axis=1)
    maximum = np.stack([horizontal[v > 0].max(0) for v in wy])
    return mean.astype(np.float32), maximum.astype(np.float32)


def reference(mask, context):
    if mask.dtype != np.uint8 or not np.isin(mask, [0, 1]).all():
        raise ValueError('binary partial envelope')
    x1, y1, x2, y2 = context
    xs = np.floor(x1+(np.arange(32)+.5)*(x2-x1)/32).astype(int)
    ys = np.floor(y1+(np.arange(32)+.5)*(y2-y1)/32).astype(int)
    center = mask[np.ix_(np.clip(ys, 0, mask.shape[0]-1), np.clip(xs, 0, mask.shape[1]-1))]
    area, any_ = reduce(mask, context)
    return center, any_.astype(np.uint8), area
