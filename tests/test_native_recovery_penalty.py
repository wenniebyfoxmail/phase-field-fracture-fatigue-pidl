"""Opt-in common MAT_CHAR alignment, beyond the separate raw-export repair.

Prescribed tiny FE arrays only; no neural model, training, or producer solve.
"""
from pathlib import Path
import sys

import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from compute_energy import compute_energy_per_elem  # noqa: E402
from material_properties import MaterialProperties  # noqa: E402
from pff_model import PFFModel  # noqa: E402
from q4_quadrature import q4_shape_data  # noqa: E402
from tri3_quadrature import tri3_shape_data  # noqa: E402


def _case(topology, alpha_values=None):
    if topology == 'q4':
        points = torch.tensor([[0.,0.], [2.,.1], [2.2,1.2], [-.1,1.]], dtype=torch.float64)
        conn = torch.tensor([[0,1,2,3]])
        cfg = {'enable': True, 'mode': 'fem_gp_q4'}
        shape, _, weights = q4_shape_data(points, conn)
        values = [-.05, .06, -.03, .01]
    else:
        points = torch.tensor([[0.,0.], [2.,.1], [.2,1.]], dtype=torch.float64)
        conn = torch.tensor([[0,1,2]])
        cfg = {'enable': True, 'mode': 'fem_gp_tri3', 'spatial_integration': 'native_tri3_gp3'}
        shape, _, weights = tri3_shape_data(points, conn)
        values = [-.05, .06, -.03]
    alpha = torch.tensor(values if alpha_values is None else alpha_values, dtype=torch.float64, requires_grad=True)
    mat = MaterialProperties(1., .3, 1., .01)
    model = PFFModel('AT1', 'volumetric', 5e-3)
    u, v = .01*points[:,0], .02*points[:,1]
    # A lower history removes the separate irreversibility penalty, isolating
    # recovery. This is an algebra witness, not a physical trajectory state.
    history = torch.full_like(alpha, -1.)
    args = (points, u, v, alpha, history, mat, model, weights.sum(1), conn)
    return args, cfg, shape, weights, alpha


@pytest.mark.parametrize('topology', ['q4', 'tri3'])
def test_native_recovery_energy_and_assembled_negative_damage_gradient(topology):
    args, cfg, shape, weights, alpha = _case(topology)
    coefficient = 13781.25
    cfg['recovery_penalty_coefficient'] = coefficient
    _, _, penalty = compute_energy_per_elem(*args, irreversibility_penalty_cfg=cfg)
    damage_gp = torch.einsum('en,gn->eg', alpha[args[-1]], shape)
    expected = .5*coefficient*(damage_gp.clamp(max=0)**2*weights).sum(1)
    torch.testing.assert_close(penalty, expected, rtol=1e-13, atol=1e-14)
    actual_gradient = torch.autograd.grad(penalty.sum(), alpha)[0]
    expected_gradient = torch.einsum('eg,gn,eg->en', coefficient*damage_gp.detach().clamp(max=0), shape, weights).reshape(-1)
    torch.testing.assert_close(actual_gradient, expected_gradient, rtol=1e-13, atol=1e-13)
    assert (damage_gp < 0).any() and (damage_gp > 0).any()


@pytest.mark.parametrize('topology', ['q4', 'tri3'])
def test_zero_recovery_coefficient_preserves_default_exactly_and_positive_damage_adds_nothing(topology):
    args, cfg, _, _, alpha = _case(topology)
    original = compute_energy_per_elem(*args, irreversibility_penalty_cfg=cfg)
    zero = compute_energy_per_elem(*args, irreversibility_penalty_cfg={**cfg, 'recovery_penalty_coefficient': 0.})
    for old, new in zip(original, zero):
        assert torch.equal(old, new)
    positive_args, cfg, _, _, positive = _case(topology, [.1]*len(alpha))
    _, _, penalty = compute_energy_per_elem(*positive_args, irreversibility_penalty_cfg={**cfg, 'recovery_penalty_coefficient': 13781.25})
    assert torch.equal(penalty, torch.zeros_like(penalty))
    gradient = torch.autograd.grad(penalty.sum(), positive)[0]
    assert torch.equal(gradient, torch.zeros_like(gradient))


@pytest.mark.parametrize('coefficient', [-1., float('nan'), float('inf'), -float('inf')])
@pytest.mark.parametrize('topology', ['q4', 'tri3'])
def test_native_recovery_coefficient_rejects_negative_nonfinite_values(topology, coefficient):
    args, cfg, _, _, _ = _case(topology)
    with pytest.raises(ValueError, match='finite and non-negative'):
        compute_energy_per_elem(*args, irreversibility_penalty_cfg={**cfg, 'recovery_penalty_coefficient': coefficient})


def test_legacy_centroid_path_does_not_apply_native_recovery_option():
    args, cfg, _, _, _ = _case('tri3')
    cfg.pop('spatial_integration')
    original = compute_energy_per_elem(*args, irreversibility_penalty_cfg=cfg)
    opted = compute_energy_per_elem(*args, irreversibility_penalty_cfg={**cfg, 'recovery_penalty_coefficient': 13781.25})
    for old, new in zip(original, opted):
        assert torch.equal(old, new)
