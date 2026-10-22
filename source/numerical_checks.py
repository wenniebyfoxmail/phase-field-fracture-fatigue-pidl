"""Fail-closed finite arithmetic checks used before certificate reductions."""
import math
import torch


def require_finite(*values):
    for value in values:
        valid = bool(torch.isfinite(value).all()) if isinstance(value,torch.Tensor) else math.isfinite(float(value))
        if not valid:
            raise ValueError('nonfinite input/intermediate in numerical certificate')


def finite_max(*values):
    require_finite(*values)
    return max(float(v) for v in values)


def require_positive_energy(energy):
    require_finite(energy)
    if not float(energy)>0:
        raise ValueError('nonpositive energy in numerical certificate')
