import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/censor_projection_diagnostic'))
from weak_form import assemble
from cross_residual import energy_parts

@pytest.mark.parametrize('strain',[(.02,.01,.003),(-.02,-.01,.004),(0.,0.,.02)])
def test_weak_form_autograd_and_fd(strain):
    xy=np.array([[0.,0.],[1.2,.1],[1.,1.1],[-.1,.9]])
    conn=np.array([[0,1,2,3]])
    ex,ey,sh=strain;uv=xy@np.array([[ex,sh/2],[sh/2,ey]])
    d=np.array([.1,.4,.25,.7]);kw=assemble(xy,conn,uv,d)
    t=lambda x:torch.tensor(x,dtype=torch.float64)
    u=t(uv).requires_grad_(True)
    e=energy_parts(t(xy),torch.tensor(conn),u,t(d),t(d),torch.ones((1,4),dtype=torch.float64))[0]
    grad=torch.autograd.grad(e,u)[0].detach().numpy()
    np.testing.assert_allclose(kw['force'],grad,rtol=1e-10,atol=1e-12)
    direction=np.random.default_rng(7).normal(size=uv.shape)
    h=1e-7
    fd=(assemble(xy,conn,uv+h*direction,d)['energy']-assemble(xy,conn,uv-h*direction,d)['energy'])/(2*h)
    assert abs(fd-(grad*direction).sum())<1e-8


def test_rigid_motion_and_mass():
    xy=np.array([[0.,0.],[1.2,.1],[1.,1.1],[-.1,.9]])
    uv=np.column_stack([-xy[:,1],xy[:,0]])*.01+np.array([2.,3.])
    r=assemble(xy,np.array([[0,1,2,3]]),uv,np.zeros(4))
    assert np.max(np.abs(r['force']))<1e-14
    assert (r['mass']>0).all() and abs(r['mass'].sum()-1)<1e-14


def test_blocked_dof_order_and_difference_norm():
    from weak_history_audit import blocked_uv,compare
    np.testing.assert_array_equal(blocked_uv([1,2,3,4,5,6]),[[1,4],[2,5],[3,6]])
    # Equal individual norms must not hide opposite residual vectors.
    r=compare(np.array([1.,-1.]),np.array([-1.,1.]),np.array([.2,.8]),1.)
    assert r['status']=='FAIL' and r['scaled_difference']==2.
