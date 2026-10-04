from pathlib import Path
import sys

import torch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "SENS_tensile"))

from run_native_q4_bounded_picard import (  # noqa: E402
    clamp_autograd_contract,
    project_box_kkt_gradient,
)


def test_box_kkt_projection_keeps_only_feasible_descent_violations():
    damage = torch.tensor([0.0, 0.0, 0.5, 1.0, 1.0])
    gradient = torch.tensor([2.0, -3.0, 4.0, -5.0, 6.0])
    projected = project_box_kkt_gradient(damage, gradient, 1e-7)
    assert torch.equal(projected, torch.tensor([0.0, -3.0, 4.0, 0.0, 6.0]))


def test_installed_clamp_strict_tail_derivative_contract():
    contract = clamp_autograd_contract(torch.device("cpu"))
    assert contract["derivatives"][0:2] == [0.0, 0.0]
    assert contract["derivatives"][3] == 1.0
    assert contract["derivatives"][-2:] == [0.0, 0.0]
