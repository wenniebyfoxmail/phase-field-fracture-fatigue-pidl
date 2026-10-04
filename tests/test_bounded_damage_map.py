import sys
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from field_computation import BoundedNonsmoothSigmoid, NonsmoothSigmoid  # noqa: E402


def test_bounded_map_is_exact_projection_of_legacy_map() -> None:
    raw = torch.tensor([-20.0, -2.0, -1.0, 0.0, 1.0, 2.0, 20.0])
    legacy = NonsmoothSigmoid(2.0, 1.0e-3)(raw)
    bounded = BoundedNonsmoothSigmoid(2.0)(raw)
    torch.testing.assert_close(bounded, legacy.clamp(0.0, 1.0), rtol=0.0, atol=0.0)
    assert torch.all((bounded >= 0.0) & (bounded <= 1.0))


def test_bounded_map_preserves_central_affine_values_and_blocks_tail_gradients() -> None:
    raw = torch.tensor([-3.0, -1.0, 0.0, 1.0, 3.0], requires_grad=True)
    bounded = BoundedNonsmoothSigmoid(2.0)(raw)
    torch.testing.assert_close(bounded, torch.tensor([0.0, 0.25, 0.5, 0.75, 1.0]))
    bounded.sum().backward()
    torch.testing.assert_close(raw.grad, torch.tensor([0.0, 0.25, 0.25, 0.25, 0.0]))
