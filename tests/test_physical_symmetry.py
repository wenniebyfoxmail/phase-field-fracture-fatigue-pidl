"""Deterministic field/gradient checks only; never enter fit or an optimizer."""
import importlib.util
import math
import sys
from pathlib import Path
import numpy as np
import pytest
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'SENS_tensile')]
from field_computation import FieldComputation
from physical_symmetry import physical_symmetry_terms
from fit import _compute_symmetry_penalty


class AnalyticNet(torch.nn.Module):
    def __init__(self, kind='even'):
        super().__init__();self.p=torch.nn.Parameter(torch.tensor(.3,dtype=torch.float64));self.kind=kind
    def forward(self, xy):
        x,y=xy.T;zero=x*0
        if self.kind=='zero':return torch.stack((zero,zero,zero),1)
        u=self.p+zero
        if self.kind=='compensated':u=u/((x+.5)**2+(y+.5)**2)
        if self.kind=='perturbed':u=u+self.p*y
        return torch.stack((u,y*(.2+x),zero),1)


def fc(kind='even',anchor=False,load=.12):
    return FieldComputation(AnalyticNet(kind),torch.tensor([[-.5,.5],[-.5,.5]],dtype=torch.float64),
            torch.tensor([load],dtype=torch.float64),torch.tensor([math.pi/2],dtype=torch.float64),
            exact_bc_dict={'enable':anchor,'mode':'fem_anchor'})


P=torch.tensor([[-.2,.11],[.1,.23],[.3,.41]],dtype=torch.float64)
W=torch.tensor([1.,2.,3.],dtype=torch.float64)


def terms(field):return physical_symmetry_terms(field,P,W,.12)


def test_affine_vertical_lifting_and_zero_load():
    for load in [.12,0.]:
        f=fc('zero',load=load);z=terms(f)
        assert max(float(t) for t in z.values())<1e-28
    f=fc('zero');r=P*P.new_tensor([1.,-1.])
    assert torch.mean((f.fieldCalculation(P)[1]+f.fieldCalculation(r)[1]).square())>0


def test_even_raw_anchor_is_not_even_physical_u():
    f=fc(anchor=True)
    assert _compute_symmetry_penalty(f,P,1.,1.,1.).item()<1e-28
    assert terms(f)['u'].item()>.01


def test_compensating_raw_anchor_recovers_even_physical_u():
    f=fc('compensated',anchor=True)
    assert terms(f)['u'].item()<1e-28
    assert _compute_symmetry_penalty(f,P,0.,1.,0.).item()>.01


def test_gradient_matches_finite_difference_and_does_not_mutate_fields():
    f=fc('perturbed',True);before=[p.detach().clone() for p in f.net.parameters()]
    q=sum(terms(f).values());derivative=torch.autograd.grad(q,f.net.p)[0].item()
    def at(x):
        with torch.no_grad():f.net.p.fill_(x)
        return sum(terms(f).values()).item()
    a=before[0].item();h=1e-6
    fd=(at(a+h)-at(a-h))/(2*h);at(a)
    assert abs(derivative-fd)<1e-8
    assert all(torch.equal(a,b) for a,b in zip(before,f.net.parameters()))


def test_weight_normalisation_and_pair_reflection():
    f=fc(anchor=True);a=terms(f)
    for points,weights in [(P,7*W),(-P*P.new_tensor([-1.,1.]),W),
                            (P.repeat(2,1),W.repeat(2))]:
        b=physical_symmetry_terms(f,points,weights,.12)
        assert all(torch.allclose(a[k],b[k],rtol=1e-13,atol=1e-28) for k in a)


@pytest.mark.parametrize('weights,scale',[([-1.,2.,3.],.12),([0.,0.,0.],.12),
    ([1.,float('nan'),1.],.12),([1.,2.],.12),([1.,2.,3.],0.),([1.,2.,3.],float('inf'))])
def test_invalid_weights_and_scale_rejected(weights,scale):
    with pytest.raises(ValueError):physical_symmetry_terms(fc(),P,weights,scale)


def test_unsupported_geometry_load_or_learned_probes_rejected():
    f=fc();f.domain_extrema[1]=torch.tensor([-.4,.5])
    with pytest.raises(ValueError):terms(f)
    f=fc();f.theta=torch.tensor([0.])
    with pytest.raises(ValueError):terms(f)
    with pytest.raises(ValueError):physical_symmetry_terms(fc(),P.clone().requires_grad_(),W,.12)


def test_legacy_default_unchanged_and_physical_requires_explicit_config():
    f=fc('perturbed',True);r=P*P.new_tensor([1.,-1.]);raw=f.net(P);mir=f.net(r)
    expected=2*((f.alpha_constraint(raw[:,2])-f.alpha_constraint(mir[:,2]))**2).mean()+3*((raw[:,0]-mir[:,0])**2).mean()+4*((raw[:,1]+mir[:,1])**2).mean()
    assert torch.equal(_compute_symmetry_penalty(f,P,2.,3.,4.),expected)
    assert torch.equal(_compute_symmetry_penalty(f,P,2.,3.,4.,{'mode':'raw'}),expected)
    with pytest.raises(ValueError):_compute_symmetry_penalty(f,P,2.,3.,4.,{'mode':'physical'})
    cfg=dict(mode='physical',probe_points=P,pair_weights=W,displacement_scale=.12,
             lambda_alpha=2.,lambda_u=3.,lambda_v=4.)
    z=terms(f);assert torch.equal(_compute_symmetry_penalty(f,P,2.,3.,4.,cfg),2*z['alpha']+3*z['u']+4*z['v'])


def test_native_interpolation_affine_patch_and_parity():
    spec=importlib.util.spec_from_file_location('parity_audit',ROOT/'tools/audit_saved_physical_parity.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    xy=np.array([[-.5,-.5],[.5,-.5],[.45,.5],[-.48,.5]])
    q=np.array([[-.1,.1],[.2,.2],[-.1,-.1],[.2,-.2]])
    for cells in [np.array([[0,1,2,3]]),np.array([[0,1,2],[0,2,3]])]:
        p=m.Probe(xy,cells,q);f=2.5*xy[:,0]-1.75*xy[:,1]+.3
        assert np.max(abs(p.value(f)-(2.5*q[:,0]-1.75*q[:,1]+.3)))<1e-14
        assert np.max(abs(p.gradient(f)-[2.5,-1.75]))<1e-14
        z=p.fields(.1*xy[:,0],.12*(xy[:,1]+.5),np.zeros(4),.12)
        assert np.max(abs(z['v_correction']))<1e-14
        assert np.max(abs(z['active'][:2]-z['active'][2:]))<1e-14


def test_saved_error_decomposition_is_orthogonal_not_a_model_update():
    spec=importlib.util.spec_from_file_location('decompose',ROOT/'tools/summarize_saved_error_parity.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    e=np.array([[1.,2.],[-1.,-2.]])
    assert m.components(e,1)['parity_violating_squared_fraction']==1
    assert m.components(e,-1)['parity_violating_squared_fraction']==0
    e=np.array([[1.,3.],[2.,-4.]])
    before=e.copy();r=m.components(e,1)
    assert abs(r['parity_compatible_squared_fraction']+r['parity_violating_squared_fraction']-1)<1e-15
    assert np.array_equal(e,before)
