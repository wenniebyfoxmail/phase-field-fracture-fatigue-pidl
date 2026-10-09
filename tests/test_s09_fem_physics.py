import sys
from pathlib import Path
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from s09_fem_physics import *


def fixture():
    xy=torch.tensor([[0.,0.],[1.,0.],[1.,1.],[0.,1.]],dtype=torch.float64)
    conn=torch.tensor([[0,1,2,3]])
    return xy,conn,*q4_shape_data(xy,conn)


def test_equilibrium_is_energy_gradient_both_trace_signs():
    xy,c,n,b,w=fixture()
    for sign in [-1,1]:
        u=(xy*torch.tensor([.12*sign,.03],dtype=xy.dtype)).requires_grad_()
        d=torch.tensor([.1,.2,.4,.3],dtype=xy.dtype)
        force,f=equilibrium(u,d,c,n,b,w)
        expected=torch.autograd.grad((f['energy']*w).sum(),u)[0]
        torch.testing.assert_close(force,expected,atol=1e-14,rtol=1e-12)


def test_phase_is_frozen_energy_gradient_including_penalties():
    xy,c,n,b,w=fixture();d=torch.tensor([-.1,.2,.35,.1],dtype=xy.dtype,requires_grad=True)
    old=torch.full_like(d,.2);psi=torch.tensor([[.2,.3,.1,.4]],dtype=xy.dtype);f=torch.ones_like(psi)*.6
    dg=q4_interpolate(d,c,n);og=q4_interpolate(old,c,n);grad=q4_gradient(d,c,b)
    energy=((1-dg).square()*psi+3/8*f*(dg+.01**2*grad.square().sum(-1))
            +10/2*torch.relu(og-dg).square()+20/2*torch.relu(-dg).square())
    expected=torch.autograd.grad((energy*w).sum(),d)[0]
    got=phase_penalty(d,old,psi,f,c,n,b,w,penalty_irrev=10.,penalty_recov=20.)
    torch.testing.assert_close(got,expected,atol=1e-14,rtol=1e-12)


def test_trial_does_not_mutate_or_double_accumulate():
    d=torch.tensor([.2]);psi=torch.tensor([2.]);old=torch.tensor([.1]);q=torch.tensor([.3])
    a=trial_fatigue(d,psi,old,q);bb=trial_fatigue(d,psi,old,q)
    for x,y in zip(a,bb):torch.testing.assert_close(x,y)
    torch.testing.assert_close(old,torch.tensor([.1]));torch.testing.assert_close(q,torch.tensor([.3]))
    assert a[0]>old and 0<a[2]<=1


def test_hard_boundary_and_trainable_residual():
    xy,c,n,b,w=fixture();model=DisplacementPINN().double()
    u=model(xy,.12)
    torch.testing.assert_close(u[:,0],torch.zeros(4,dtype=xy.dtype))
    torch.testing.assert_close(u[:,1],xy[:,1]*.12)
    # Interior node on a 2x2 mesh, so correction need not vanish everywhere.
    xx=torch.tensor([[i/2,j/2] for j in range(3) for i in range(3)],dtype=xy.dtype)
    cc=torch.tensor([[0,1,4,3],[1,2,5,4],[3,4,7,6],[4,5,8,7]])
    nn,bb,ww=q4_shape_data(xx,cc)
    dd=xx[:,0]*.6
    force,_=equilibrium(model(xx,.12),dd,cc,nn,bb,ww)
    loss=force[boundary(xx)].square().sum();loss.backward()
    assert model.net[-1].weight.grad.abs().sum()>0
