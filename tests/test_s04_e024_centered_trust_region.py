import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'SENS_tensile'))
from s04_e024_centered_trust_region import centered_head


def test_single_feature_shared_uv_budget_closed_form():
    x=np.array([[1.],[2.],[3.]])
    center=np.array([[1.,-2.]])
    direction=np.array([[3.,4.]])
    y=x*(center+direction)
    r=centered_head(x,y,np.ones(3),center)
    radius=.1*np.linalg.norm(center)
    np.testing.assert_allclose(r['delta'],radius*direction/5,rtol=1e-12)
    assert r['active'] and r['delta_relative']==pytest.approx(.1)


def test_inactive_and_nullspace_center_preserved():
    x=np.array([[1.,0.],[2.,0.],[0.,0.]])
    center=np.array([[1.,2.],[30.,-40.]])
    y=x@center+np.array([[.01,-.02],[.02,-.04],[4.,-3.]])
    r=centered_head(x,y,np.array([1.,3.,2.]),center)
    assert not r['active']
    np.testing.assert_array_equal(r['coef'][1],center[1])
    np.testing.assert_allclose(r['delta'][0],[.01,-.02],atol=1e-14)
    assert r['centered_after_rms']>0  # zero-support target remains in objective


def test_anisotropic_boundary_kkt_direct():
    x=np.diag([5.,.01,0.]);center=np.ones((3,2));target=np.array([[2.,4.],[1.,-1.],[5.,6.]])
    mass=np.array([1.,2.,3.]);r=centered_head(x,target,mass,center)
    grad=x.T@((mass/mass.sum())[:,None]*(x@r['coef']-target))
    np.testing.assert_allclose(grad+r['lambda_value']*r['delta'],0,atol=1e-12)
    np.testing.assert_array_equal(r['coef'][2],center[2])
    assert r['delta_norm']==pytest.approx(r['radius'],rel=1e-12)


@pytest.mark.parametrize('change',[lambda x,y,m,c:(x,y,-m,c),lambda x,y,m,c:(x,y[:-1],m,c),lambda x,y,m,c:(x,y,m,c*0),lambda x,y,m,c:(x*np.nan,y,m,c)])
def test_invalid(change):
    args=change(np.ones((3,2)),np.ones((3,2)),np.ones(3),np.ones((2,2)))
    with pytest.raises(ValueError):centered_head(*args)


def test_finite_inputs_with_overflowing_design_refused():
    with pytest.raises(ValueError,match='nonfinite'):
        centered_head(np.array([[1e200]]),np.array([[2e200,2e200]]),np.ones(1),np.ones((1,2)))
