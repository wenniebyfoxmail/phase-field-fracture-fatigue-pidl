"""Fixed digital sensor for SYNMEM Q1; never a physical crack truth operator."""
import numpy as np


def camera_damage(mesh, damage, pixels=64):
    """Q4 bilinear samples at fixed pixel centres on the full unit square."""
    d = np.asarray(damage, dtype=float)
    if (type(pixels) is not int or pixels < 2 or d.shape != (len(mesh.points),)
            or not np.isfinite(d).all() or np.any(d < 0) or np.any(d > 1)):
        raise ValueError('invalid digital sensor input')
    axis = (np.arange(pixels) + .5) / pixels
    xx, yy = np.meshgrid(axis, axis, indexing='xy')
    ix = np.minimum((xx * mesh.nx).astype(int), mesh.nx - 1)
    iy = np.minimum((yy * mesh.ny).astype(int), mesh.ny - 1)
    tx, ty = xx * mesh.nx - ix, yy * mesh.ny - iy
    n = iy * (mesh.nx + 1) + ix
    return ((1-tx)*(1-ty)*d[n] + tx*(1-ty)*d[n+1]
            + tx*ty*d[n+mesh.nx+2] + (1-tx)*ty*d[n+mesh.nx+1])


def mask_of(mesh, state, threshold=.5):
    if not 0 < threshold < 1:
        raise ValueError('invalid sensor threshold')
    return camera_damage(mesh, state.damage) >= threshold


def anchor_valid(mask):
    """A priori 32 pixels behind the notch tip; never filled into the image."""
    a = np.asarray(mask)
    return bool(a.shape == (64, 64) and a.dtype == bool and a[31:33, 8:24].all())


def current_match(masks):
    """Require identical entire current images across both arms and 3 variants."""
    a = np.asarray(masks)
    if a.shape != (3, 2, 64, 64) or a.dtype != bool:
        raise ValueError('expected variant x arm x camera Boolean masks')
    return dict(anchor_valid=all(anchor_valid(x) for x in a.reshape(-1, 64, 64)),
                identical=bool(np.all(a == a[0, 0])),
                differing_pixels=int(np.any(a != a[0, 0], axis=(0, 1)).sum()))


def robust_difference(masks):
    """Pixels stable within EACH arm across variants, but different across arms.

    The tested discretisations are a sensitivity check, not an error bound.
    The full unstable map is retained; no selection among horizons is allowed.
    """
    a = np.asarray(masks)
    if a.shape != (3, 2, 64, 64) or a.dtype != bool:
        raise ValueError('expected variant x arm x camera Boolean masks')
    stable = np.all(a == a[0], axis=0)
    different = a[0, 0] != a[0, 1]
    robust = stable[0] & stable[1] & different
    return dict(robust=robust, unstable=~(stable[0] & stable[1]),
                robust_pixels=int(robust.sum()),
                robust_area=float(robust.sum() / 4096),
                xor_pixels_by_variant=np.sum(a[:, 0] != a[:, 1], axis=(1, 2)).tolist(),
                unstable_pixels_by_arm=np.sum(~stable, axis=(1, 2)).tolist(),
                unstable_pixels=int((~(stable[0] & stable[1])).sum()))


def numeric_fields_equal(a, b):
    # IDs may differ between legal branches; restart replay compares IDs too.
    return all(np.array_equal(getattr(a, key), getattr(b, key)) for key in
               ('displacement', 'damage', 'accumulated', 'driver', 'fatigue', 'opaque'))
