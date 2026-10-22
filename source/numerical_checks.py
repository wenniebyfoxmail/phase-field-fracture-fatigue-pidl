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


def require_parameter_contract(module, reference):
    """Check actual parameter/buffer placement before the first model call.

    Historical construct_model returns a CPU module even with a CUDA argument.
    The caller must explicitly move it; a CUDA checkpoint load does not move
    destination Parameters. This guard performs no forward or optimization.
    """
    tensors=list(module.named_parameters())+list(module.named_buffers())
    if not tensors:
        raise ValueError('empty model parameter contract')
    for name,value in tensors:
        if value.device != reference.device:
            raise ValueError(f'device mismatch before model execution: {name}')
        if value.is_floating_point() and value.dtype != reference.dtype:
            raise ValueError(f'dtype mismatch before model execution: {name}')
