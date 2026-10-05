import sys
from pathlib import Path
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/censor_projection_diagnostic'))
from cross_residual import energy_parts, mass_data, residuals, evaluate


def patch():
    xy=torch.tensor([[0.,0.],[1.1,0.],[1.,1.],[0.,1.]],dtype=torch.float64)
    conn=torch.tensor([[0,1,2,3]])
    uv=torch.stack((.04*xy[:,0]+.01*xy[:,1],.12*xy[:,1]),dim=1)
    d=torch.tensor([.2,.25,.3,.22],dtype=torch.float64)
    return xy,conn,uv,d,torch.ones(4,dtype=torch.float64)*.5,torch.ones((1,4),dtype=torch.float64)*.8


def test_energy_component_directional_derivatives_and_frozen_history():
    xy,c,uv,d,h,f=patch();before=(h.clone(),f.clone());uv.requires_grad_();d.requires_grad_()
    du=torch.tensor([[.01,-.02],[.02,.01],[-.01,.01],[.03,.02]],dtype=torch.float64)
    dd=torch.tensor([.1,-.05,.03,-.08],dtype=torch.float64)
    parts=energy_parts(xy,c,uv,d,h,f)
    for i,part in enumerate(parts):
        gu,gd=torch.autograd.grad(part,(uv,d),retain_graph=True,allow_unused=True)
        ad=((gu*du).sum() if gu is not None else 0)+(gd*dd).sum()
        step=1e-6
        fp=energy_parts(xy,c,uv+step*du,d+step*dd,h,f)[i]
        fm=energy_parts(xy,c,uv-step*du,d-step*dd,h,f)[i]
        fd=(fp-fm)/(2*step)
        assert abs(float(ad-fd))/max(abs(float(ad)),abs(float(fd)),1.)<1e-5
    assert torch.equal(h,before[0]) and torch.equal(f,before[1])


def test_mass_and_box_residual_signs():
    xy,c,*_=patch();_,det,m=mass_data(xy,c)
    assert torch.all(m>0) and abs(float(m.sum())-1)<1e-14
    d=torch.tensor([0.,1.,.3,.7],dtype=torch.float64)
    gd=torch.tensor([1.,-1.,0.,0.],dtype=torch.float64)
    free=torch.ones(4,dtype=torch.bool)
    assert residuals(torch.zeros((4,2)),gd,d,m,free,1.,1.)[1]==0.
    assert residuals(torch.zeros((4,2)),-gd,d,m,free,1.,1.)[1]>0.


def test_component_sums_and_elastic_history_independence():
    xy,c,u,d,h,f=patch()
    first=energy_parts(xy,c,u,d,h,f)
    second=energy_parts(xy,c,u,d,h*.5,f*.7)
    assert torch.equal(first[0],second[0])
    rows,s,arrays=evaluate(xy,c,u,d,h,f,.12)
    assert abs(rows[-1]['energy']-sum(x['energy'] for x in rows[:-1]))<1e-12
    assert rows[1]['rho_u']==0 and rows[2]['rho_u']==0
