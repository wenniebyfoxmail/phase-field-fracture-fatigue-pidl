"""Deterministic mapping/gradient tests only; no optimizer or fit calls."""
import sys,math,copy
from pathlib import Path
import torch,pytest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'source'),str(ROOT/'SENS_tensile')]
from nodal_damage_alignment import NodalDamageAlignment
from field_computation import FieldComputation,NonsmoothSigmoid

XY=torch.tensor([[-.5,0.],[-.25,0.],[0.,0.],[.1,.1],[.2,-.1]],dtype=torch.float32)
R=torch.tensor([1.9,1.7,1.6,-.4,-2.1],dtype=torch.float32)
D=torch.tensor([1.,1.,1.,.4,0.],dtype=torch.float32)
S=NonsmoothSigmoid(2.,1e-3)


def test_initial_fem_field_exact_and_does_not_freeze_free_nodes():
    a=NodalDamageAlignment(XY,mode='fem_initial',initial_damage=D,raw_reference=R)
    assert torch.equal(a(XY,R,S),D)
    changed=R.clone();changed[3]-=.2
    out=a(XY,changed,S)
    assert out[3]<D[3]  # No implicit floor at the initial field.
    assert torch.equal(out[:3],torch.ones(3))
    assert torch.equal(a.initial_damage,D) and torch.equal(a.raw_reference,R)


def test_line_hard_and_gradient_zero_but_free_nodes_learnable():
    a=NodalDamageAlignment(XY,mode='fem_initial',initial_damage=D,raw_reference=R)
    r=R.clone().requires_grad_(True);value=a(XY,r,S)
    g=torch.autograd.grad(value.sum(),r)[0]
    assert torch.equal(g[:3],torch.zeros(3))
    assert torch.allclose(g[3:],torch.full((2,),.25))
    assert list(a.parameters())==[]


def test_hard_line_only_keeps_free_output_and_initial_history():
    a=NodalDamageAlignment(XY,mode='hard_line');out=a(XY,R,S)
    assert torch.equal(out[3:],S(R)[3:]) and torch.equal(out[:3],torch.ones(3))
    h=torch.tensor([.97,.98,.99,.12,-.001]);hcopy=h.clone();hh=a.initial_history(h)
    assert torch.equal(h,hcopy) and torch.equal(hh[:3],torch.ones(3))
    assert torch.equal(hh[3:],h[3:])


def test_anchor_copies_not_mutable_external_views_and_state_roundtrip():
    xy=XY.clone();d=D.clone();r=R.clone()
    a=NodalDamageAlignment(xy,mode='fem_initial',initial_damage=d,raw_reference=r)
    xy.add_(1);d.zero_();r.zero_()
    assert torch.equal(a(XY,R,S),D)
    b=NodalDamageAlignment(XY,mode='fem_initial',initial_damage=D+.0,raw_reference=R+.0)
    b.load_state_dict(copy.deepcopy(a.state_dict()));assert torch.equal(b(XY,R,S),D)
    hard=NodalDamageAlignment(XY,mode='hard_line')
    with pytest.raises((RuntimeError,ValueError)):hard.load_state_dict(a.state_dict())


@pytest.mark.parametrize('inp',[XY.flip(0),XY[:3],XY+1e-4,XY.double(),XY.clone().requires_grad_(True)])
def test_order_subset_coordinates_dtype_and_autodiff_rejected(inp):
    a=NodalDamageAlignment(XY,mode='hard_line')
    with pytest.raises(ValueError):a(inp,R,S)


@pytest.mark.parametrize('d',[D*2,D-2,torch.full_like(D,float('nan')),D[:3],D*0])
def test_invalid_initial_fem_field_rejected(d):
    with pytest.raises(ValueError):NodalDamageAlignment(XY,mode='fem_initial',initial_damage=d,raw_reference=R)


def test_fem_fixed_dofs_and_map_semantics_checked():
    with pytest.raises(ValueError):NodalDamageAlignment(XY,mode='hard_line',expected_crack_mask=torch.zeros(5,dtype=torch.bool))
    with pytest.raises(ValueError):NodalDamageAlignment(XY,mode='fem_initial')
    a=NodalDamageAlignment(XY,mode='hard_line')
    with pytest.raises(ValueError):a(XY,R,torch.sigmoid)


class ToyNet(torch.nn.Module):
    def __init__(self):
        super().__init__();self.p=torch.nn.Parameter(torch.tensor(.3))
    def forward(self,xy):
        x,y=xy.T;return torch.stack((x+self.p,y-self.p,x+2*y+self.p),1)


def field(net,adapter=None):
    return FieldComputation(net,torch.tensor([[-.5,.5],[-.5,.5]]),torch.tensor([.03]),torch.tensor([math.pi/2]),nodal_damage_alignment=adapter)


def test_integration_keeps_uv_and_default_outputs_exact():
    net=ToyNet();base=field(net);raw=net(XY)[:,2].detach()
    default=base.fieldCalculation(XY)
    expected_d=S(raw)
    assert torch.equal(default[2],expected_d)
    a=NodalDamageAlignment(XY,mode='fem_initial',initial_damage=D,raw_reference=raw)
    aligned=field(net,a).fieldCalculation(XY)
    assert torch.equal(default[0],aligned[0]) and torch.equal(default[1],aligned[1])
    assert torch.equal(aligned[2],D)
    torch.autograd.grad(aligned[2][3:].sum(),net.p)
    for old,new in zip(default,base.fieldCalculation(XY)):assert torch.equal(old,new)


def test_direct_network_probe_symmetry_cannot_bypass_mesh_lock():
    from physical_symmetry import physical_symmetry_terms
    net=ToyNet();a=NodalDamageAlignment(XY,mode='fem_initial',initial_damage=D,raw_reference=net(XY)[:,2])
    aligned=field(net,a)
    with pytest.raises(ValueError,match='identical ordered native nodes'):
        physical_symmetry_terms(aligned,XY[3:4],torch.ones(1),.12)
