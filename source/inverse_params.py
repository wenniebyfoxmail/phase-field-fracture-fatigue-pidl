"""Trainable scalar parameters for inverse PIDL prototypes."""
from __future__ import annotations

import torch
from torch import nn


class TrainablePositiveScalar(nn.Module):
    """A positive scalar parameter represented through a softplus transform."""

    def __init__(
        self,
        initial_value: float,
        *,
        min_value: float = 1.0e-6,
        max_value: float | None = None,
        device: torch.device | str | None = None,
        dtype: torch.dtype = torch.float32,
    ) -> None:
        super().__init__()
        if initial_value <= min_value:
            raise ValueError(
                f"initial_value={initial_value} must be greater than min_value={min_value}"
            )
        self.min_value = float(min_value)
        self.max_value = max_value if max_value is None else float(max_value)

        shifted = torch.as_tensor(
            float(initial_value) - self.min_value, dtype=dtype, device=device
        )
        raw = torch.log(torch.expm1(shifted.clamp_min(torch.finfo(dtype).eps)))
        self.raw = nn.Parameter(raw.reshape(()))

    def forward(self) -> torch.Tensor:
        value = self.min_value + torch.nn.functional.softplus(self.raw)
        if self.max_value is not None:
            value = torch.clamp(value, max=self.max_value)
        return value


def scalar_value(value_or_module) -> float:
    """Return a Python float for logging from a number, tensor, or callable module."""

    value = value_or_module() if callable(value_or_module) else value_or_module
    if torch.is_tensor(value):
        return float(value.detach().cpu().item())
    return float(value)
