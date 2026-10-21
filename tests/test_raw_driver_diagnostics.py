"""Tiny prescribed FE arrays only: no neural network or training loop."""
from pathlib import Path
import sys

import numpy as np
import pytest
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source'))
from compute_energy import (  # noqa: E402
    compute_energy_per_elem, get_psi_plus_per_elem, raw_strain_energy_density,
)
from material_properties import MaterialProperties  # noqa: E402
from model_train import _save_element_diagnostics  # noqa: E402
from pff_model import PFFModel  # noqa: E402


def _analytic_raw(xx, yy, xy, mat, split='volumetric'):
    # Independent total-energy-minus-compressive-volume identity.
    trace = xx + yy
    total = .5 * mat.mat_lmbda * trace**2 + mat.mat_mu * (xx**2 + yy**2 + 2*xy**2)
    if split == 'volumetric':
        total -= .5 * (mat.mat_lmbda + 2*mat.mat_mu/3) * np.minimum(trace, 0)**2
    return total


@pytest.mark.parametrize('eta', [0.0, 1e-6])
@pytest.mark.parametrize('split', ['volumetric', None])
def test_direct_raw_handles_tension_compression_mixed_trace_and_shear(eta, split):
    mat = MaterialProperties(1.0, .3, 1.0, .01)
    if split is None:
        with pytest.warns(UserWarning):
            model = PFFModel('AT1', split, 5e-3, residual_stiffness=eta)
    else:
        model = PFFModel('AT1', split, 5e-3, residual_stiffness=eta)
    xx = torch.tensor([.01, -.02, .02, -.03, 0.0], dtype=torch.float64)
    yy = torch.tensor([.02, -.01, -.02, .01, 0.0], dtype=torch.float64)
    xy = torch.tensor([0.0, 0.0, .007, -.005, .02], dtype=torch.float64)
    result = raw_strain_energy_density(xx, yy, xy, mat, model)
    expected = _analytic_raw(xx.numpy(), yy.numpy(), xy.numpy(), mat, split)
    np.testing.assert_allclose(result.numpy(), expected, rtol=1e-13, atol=1e-17)
    assert torch.isfinite(result).all()


@pytest.mark.parametrize('eta', [0.0, 1e-6])
@pytest.mark.parametrize('reduction', ['centroid', 'probe_g_mean', 'fem_gp_tri3_g_mean'])
@pytest.mark.parametrize('damage', ['full', 'mixed_near_one'])
def test_legacy_writer_raw_is_independent_of_active_reduction_and_zero_g(tmp_path, eta, reduction, damage):
    points = torch.tensor([[0., 0.], [1., 0.], [0., 1.]], dtype=torch.float64)
    conn = torch.tensor([[0, 1, 2]])
    area = torch.tensor([.5], dtype=torch.float64)
    # Compression + shear checks tensor shear and the positive split together.
    u = -.03*points[:, 0] + .012*points[:, 1]
    v = -.004*points[:, 0] + .01*points[:, 1]
    alpha = (torch.ones(3, dtype=torch.float64) if damage == 'full'
             else torch.tensor([.99, 1.0, 1.01], dtype=torch.float64))
    mat = MaterialProperties(1., .3, 1., .01)
    model = PFFModel('AT1', 'volumetric', 5e-3, residual_stiffness=eta)
    hdr = {'enable': reduction != 'centroid', 'mode': reduction}
    active = get_psi_plus_per_elem(points, u, v, alpha, mat, model, area, conn,
                                  history_driver_reduction_dict=hdr)
    active_before = active.clone()
    old = torch.zeros_like(active)
    irr = {'enable': True, 'mode': 'fem_gp_tri3'}
    before = compute_energy_per_elem(points, u, v, alpha, alpha, mat, model, area, conn,
                                    irreversibility_penalty_cfg=irr)
    _save_element_diagnostics(points, conn, u, v, alpha, alpha, old, torch.ones_like(old),
                              active, old, mat, model, area, 1, tmp_path,
                              irreversibility_penalty_cfg=irr)
    after = compute_energy_per_elem(points, u, v, alpha, alpha, mat, model, area, conn,
                                   irreversibility_penalty_cfg=irr)
    for a, b in zip(before, after):
        assert torch.equal(a, b)
    assert torch.equal(active, active_before)
    expected = _analytic_raw(np.array([-.03]), np.array([.01]), np.array([.004]), mat)
    with np.load(tmp_path / 'element_fields_cycle_0001.npz') as saved:
        np.testing.assert_allclose(saved['psi_raw_elem'], expected, rtol=1e-6)
        np.testing.assert_allclose(saved['psi_active_elem'], active.numpy(), rtol=1e-6, atol=1e-30)
        assert saved['psi_raw_support'].item() == 'tri3_centroid'
        assert saved['psi_raw_element_reduction'].item() == 'none'
        assert saved['quadrature_weights_gp'].shape == (0, 0)
        np.testing.assert_array_equal(saved['psi_raw_elem'], saved['psi_raw_from_g_alpha_elem'])
        np.testing.assert_array_equal(saved['psi_raw_elem'], saved['psi_raw_from_g_solver_elem'])
    if damage == 'mixed_near_one' and reduction != 'centroid' and eta == 0:
        assert active.item() > 0  # The old active/centroid-g quotient would explode.


@pytest.mark.parametrize('eta', [0.0, 1e-6])
@pytest.mark.parametrize('topology', ['q4', 'tri3'])
def test_native_writer_preserves_gp_raw_before_reduction_and_active_payload(tmp_path, eta, topology):
    mat = MaterialProperties(1., .3, 1., .01)
    model = PFFModel('AT1', 'volumetric', 5e-3, residual_stiffness=eta)
    if topology == 'q4':
        # Distortion + nonaffine nodal field separates GP energy mean from
        # energy of mean strain, and arithmetic from area-weighted GP mean.
        points = torch.tensor([[0.,0.], [2.,.1], [2.2,1.2], [-.1,1.]], dtype=torch.float64)
        conn = torch.tensor([[0,1,2,3]])
        u = torch.tensor([0., .01, -.03, .02], dtype=torch.float64)
        v = torch.tensor([.01, -.02, .04, .01], dtype=torch.float64)
        irr = {'enable': True, 'mode': 'fem_gp_q4'}
        hdr = {'enable': True, 'mode': 'native_q4_gp4'}
        n_gp = 4
    else:
        points = torch.tensor([[0.,0.], [1.,0.], [1.,1.], [0.,1.]], dtype=torch.float64)
        conn = torch.tensor([[0,1,2], [0,2,3]])
        u = -.03*points[:,0] + .012*points[:,1]
        v = -.004*points[:,0] + .01*points[:,1]
        irr = {'enable': True, 'mode': 'fem_gp_tri3', 'spatial_integration': 'native_tri3_gp3'}
        hdr = {'enable': True, 'mode': 'native_tri3_gp3'}
        n_gp = 3
    alpha = torch.ones(len(points), dtype=torch.float64)
    area = torch.ones(len(conn), dtype=torch.float64)  # native routines use geometry
    active = get_psi_plus_per_elem(points, u, v, alpha, mat, model, area, conn,
                                  history_driver_reduction_dict=hdr)
    old = torch.zeros_like(active)
    before = compute_energy_per_elem(points, u, v, alpha, alpha, mat, model, area, conn,
                                    irreversibility_penalty_cfg=irr)
    _save_element_diagnostics(points, conn, u, v, alpha, alpha, old, torch.ones_like(old),
                              active, old, mat, model, area, 1, tmp_path,
                              irreversibility_penalty_cfg=irr)
    after = compute_energy_per_elem(points, u, v, alpha, alpha, mat, model, area, conn,
                                   irreversibility_penalty_cfg=irr)
    for a, b in zip(before, after):
        assert torch.equal(a, b)
    with np.load(tmp_path / 'element_fields_cycle_0001.npz') as saved:
        raw = saved['psi_raw_gp']
        assert raw.shape == (len(conn), n_gp)
        expected = _analytic_raw(saved['eps_xx_gp'].astype(float), saved['eps_yy_gp'].astype(float),
                                 .5*saved['engineering_shear_gamma_xy_gp'].astype(float), mat)
        np.testing.assert_allclose(raw, expected, rtol=2e-6, atol=1e-12)
        np.testing.assert_allclose(saved['psi_raw_elem'], raw.mean(1), rtol=1e-6)
        weights = saved['quadrature_weights_gp']
        np.testing.assert_allclose(saved['psi_raw_area_mean_elem'], (raw*weights).sum(1)/weights.sum(1), rtol=1e-6)
        np.testing.assert_allclose(saved['psi_active_gp'], active.numpy(), rtol=1e-6, atol=1e-30)
        assert saved['psi_raw_support'].item() == ('native_q4_gp4' if topology == 'q4' else 'native_tri3_gp3')
        assert saved['psi_raw_element_reduction'].item() == 'arithmetic_mean_of_native_gp_energy'
        assert np.all(raw > 0)
        if eta == 0:
            assert np.max(np.abs(saved['psi_active_gp'])) < 1e-30
        if topology == 'q4':
            mean_strain_raw = _analytic_raw(saved['eps_xx_elem'], saved['eps_yy_elem'], saved['eps_xy_elem'], mat)
            assert not np.allclose(saved['psi_raw_elem'], mean_strain_raw, rtol=1e-3)
            assert not np.allclose(saved['psi_raw_elem'], saved['psi_raw_area_mean_elem'], rtol=1e-4)
