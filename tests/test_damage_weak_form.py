import sys
from pathlib import Path
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/censor_projection_diagnostic'))
from damage_weak_form import assemble_damage
from weak_form import assemble
from cross_residual import energy_parts

@pytest.mark.parametrize('strain',[(.02,.01,.003),(-.02,-.01,.004),(0.,0.,.02)])
def test_damage_weak_matches_ad_and_directional_difference(strain):
    xy=np.array([[0.,0.],[1.2,.1],[1.,1.1],[-.1,.9]])
    conn=np.array([[0,1,2,3]]);ex,ey,sh=strain
    u=xy@np.array([[ex,sh/2],[sh/2,ey]])
    d=np.array([.2,.4,.3,.7]);prev=np.zeros(4);f=np.array([[.3,.5,.8,1.]])
    psi=assemble(xy,conn,u,d)['psi'];r,_=assemble_damage(xy,conn,d,prev,psi,f)
    t=lambda a:torch.tensor(a,dtype=torch.float64)
    dt=t(d).requires_grad_(True)
    e=sum(energy_parts(t(xy),torch.tensor(conn),t(u),dt,t(prev),t(f)))
    ad=torch.autograd.grad(e,dt)[0].detach().numpy()
    np.testing.assert_allclose(r,ad,rtol=1e-11,atol=1e-13)
    v=np.array([.4,-.3,.8,-.7]);h=1e-6
    fd=(assemble_damage(xy,conn,d+h*v,prev,psi,f)[1]-assemble_damage(xy,conn,d-h*v,prev,psi,f)[1])/(2*h)
    assert abs(fd-r@v)<1e-10

def test_reject_healing_instead_of_dropping_penalty():
    xy=np.array([[0.,0.],[1.,0.],[1.,1.],[0.,1.]])
    with pytest.raises(ValueError,match='Strict feasible'):
        assemble_damage(xy,np.array([[0,1,2,3]]),np.zeros(4),np.ones(4)*1e-14,np.ones((1,4)),np.ones((1,4)))
