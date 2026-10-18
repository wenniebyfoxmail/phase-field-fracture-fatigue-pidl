"""Opt-in hard lower/box checks only; no optimizer, fit or FEM solve."""
import copy,sys
from pathlib import Path
import pytest,torch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'source'),str(ROOT/'SENS_tensile')]
from nodal_damage_alignment import NodalDamageAlignment
from field_computation import NonsmoothSigmoid
from q4_quadrature import q4_shape_data,q4_interpolate,q4_gradient


def fixture(dtype=torch.float32,hard=True):
    xy=torch.tensor([[-.5,0.],[0.,0.],[.5,0.],[-.5,.2],[0.,.2],[.5,.2]],dtype=dtype)
    cells=torch.tensor([[0,1,4,3],[1,2,5,4]])
    d0=xy.new_tensor([1.,1.,0.,.4,.7,1.]);r0=xy.new_tensor([1.9,1.6,-2.1,.2,.3,2.])
    a=NodalDamageAlignment(xy,mode='fem_initial',initial_damage=d0,raw_reference=r0,hard_lower_box=hard)
    return xy,cells,d0,r0,a


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_exact_origin_and_explicit_boundary_derivative(dtype):
    xy,cells,d0,r0,a=fixture(dtype);raw=r0.clone().requires_grad_(True)
    value=a(xy,raw,NonsmoothSigmoid());assert torch.equal(value,d0)
    grad=torch.autograd.grad(value.sum(),raw)[0]
    movable=(~a.crack_mask)&(d0<1)
    assert torch.equal(grad[movable],torch.full_like(grad[movable],.25))
    assert torch.count_nonzero(grad[~movable])==0
    assert torch.equal(a.initial_history(d0),d0)


@pytest.mark.parametrize('dtype',[torch.float32,torch.float64])
def test_large_signed_raw_changes_keep_nodal_and_native_Q4_feasible(dtype):
    xy,cells,d0,r0,a=fixture(dtype);s=NonsmoothSigmoid();N,B,w=q4_shape_data(xy,cells)
    lower=q4_interpolate(d0,cells,N)
    for delta in [-1e5,-5.,-1e-3,0.,1e-3,5.,1e5]:
        raw=(r0+delta).requires_grad_(True);value=a(xy,raw,s)
        assert bool(((value>=d0)&(value<=1)).all())
        assert bool((value[a.crack_mask]==1).all())
        gp=q4_interpolate(value,cells,N)
        assert bool(((gp>=lower)&(gp<=1)).all())
        # Spatial energy gradients use the complete projected nodal field.
        objective=q4_gradient(value,cells,B).square().sum()+(w*gp).sum()
        gradient=torch.autograd.grad(objective,raw)[0]
        assert bool(torch.isfinite(gradient).all())
        assert torch.equal(a.initial_damage,d0) and torch.equal(a.raw_reference,r0)


def test_default_old_checkpoint_compatible_and_optin_cannot_be_silent():
    xy,cells,d0,r0,legacy=fixture(hard=False);_,_,_,_,hard=fixture(hard=True)
    old=copy.deepcopy(legacy.state_dict())
    assert old['_extra_state']=={'schema':'sent_nodal_damage_alignment_v1','mode':'fem_initial'}
    restored=fixture(hard=False)[-1];restored.load_state_dict(old)
    perturb=r0-5
    assert torch.equal(restored(xy,perturb,NonsmoothSigmoid()),legacy(xy,perturb,NonsmoothSigmoid()))
    assert bool((legacy(xy,perturb,NonsmoothSigmoid())[~legacy.crack_mask]<d0[~legacy.crack_mask]).any())
    with pytest.raises(ValueError):hard.load_state_dict(old)
    hardstate=copy.deepcopy(hard.state_dict());assert 'constraint' in hardstate['_extra_state']
    restored_hard=fixture(hard=True)[-1];restored_hard.load_state_dict(hardstate)
    assert torch.equal(restored_hard(xy,perturb,NonsmoothSigmoid()),hard(xy,perturb,NonsmoothSigmoid()))
    with pytest.raises(ValueError):legacy.load_state_dict(hardstate)


def test_projection_has_finite_active_and_inactive_raw_gradients():
    xy,cells,d0,r0,a=fixture();raw=r0.clone();raw[2]-=2;raw[3]+=.2;raw[4]+=10;raw.requires_grad_(True)
    out=a(xy,raw,NonsmoothSigmoid());g=torch.autograd.grad(out.sum(),raw)[0]
    assert g[2]==g[4]==g[5]==0
    assert g[3]==.25 and bool(torch.isfinite(g).all())
    assert out[2]==d0[2] and out[4]==out[5]==1


def test_hard_line_mode_and_nonbool_optin_rejected():
    xy,cells,d0,r0,a=fixture()
    with pytest.raises(ValueError):NodalDamageAlignment(xy,mode='hard_line',hard_lower_box=True)
    with pytest.raises(ValueError):NodalDamageAlignment(xy,mode='fem_initial',initial_damage=d0,raw_reference=r0,hard_lower_box='False')


def test_projection_does_not_hide_overflow_from_finite_raw_inputs():
    xy,cells,d0,r0,a=fixture()
    reference=torch.full_like(r0,-3e38)
    bounded=NodalDamageAlignment(xy,mode='fem_initial',initial_damage=d0,raw_reference=reference,hard_lower_box=True)
    raw=torch.full_like(r0,3e38);assert torch.isfinite(raw).all() and torch.isfinite(reference).all()
    with pytest.raises(ValueError,match='finite damage required before hard projection'):
        bounded(xy,raw,NonsmoothSigmoid())
