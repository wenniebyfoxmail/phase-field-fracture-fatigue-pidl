import sys
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/censor_projection_diagnostic'))
from teacher_precision import PERM,relative_l2,weighted_quantile,build_q4_kinematics,q4_shape_data

def test_solver_native_gp_mapping_distorted_quad():
    x=np.array([[0.,0.],[1.2,.1],[1.,1.1],[-.1,.9]]);c=np.array([[0,1,2,3]])
    k=build_q4_kinematics(x,c);n,d,det=q4_shape_data(torch.tensor(x),torch.tensor(c))
    np.testing.assert_allclose(k.shape_values[PERM],n.numpy(),atol=1e-15)
    np.testing.assert_allclose(k.det_jacobians[:,PERM],det.numpy(),atol=1e-15)
    uv=np.array([[.1,.0],[.03,.04],[-.01,.02],[0.,-.02]])
    e=np.einsum('egij,ej->egi',k.b_matrices,uv.ravel()[k.element_dofs])[:,PERM,:]
    grad=np.einsum('egin,enb->egib',d.numpy(),uv[c]);expected=np.stack([grad[:,:,0,0],grad[:,:,1,1],grad[:,:,0,1]+grad[:,:,1,0]],axis=-1)
    np.testing.assert_allclose(e,expected,atol=1e-15)

def test_metrics_weights_and_zero_denominator():
    assert relative_l2(np.ones(2),np.zeros(2),np.ones(2)) is None
    assert weighted_quantile(np.array([0.,1.,10.]),np.array([.98,.015,.005]),.99)==1.
    assert relative_l2(np.array([2.,4.]),np.array([1.,2.]),np.array([.2,.8]))==1.


def test_fem_seed_validation_and_metric_scaling():
    import pytest
    from teacher_precision import norm_report,solve_amor_equilibrium,sens_displacement_boundary_conditions
    x=np.array([[0.,0.],[1.,0.],[1.,1.],[0.,1.]]);c=np.array([[0,1,2,3]])
    k=build_q4_kinematics(x,c);bc,bv=sens_displacement_boundary_conditions(x,.1)
    u=np.zeros(8);u[bc]=bv
    r=solve_amor_equilibrium(k,np.zeros(4),bc,bv,initial_displacement=u)
    np.testing.assert_array_equal(r.displacement,u)
    u[0]=1
    with pytest.raises(ValueError):solve_amor_equilibrium(k,np.zeros(4),bc,bv,initial_displacement=u)
    r=norm_report(np.array([1.]),np.array([0.]),np.array([1.]),2.)
    assert r['kind']=='nominal_scale' and r['value']==.5
