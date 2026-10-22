"""Tiny synthetic Q4 quadrature and nodal-force checks, not a project solve."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

sys.path[:0] = [str(Path(__file__).resolve().parents[1] / 'source'),
                str(Path(__file__).resolve().parents[1] / 'tools/s04_e036')]
from compute_energy import compute_energy
from material_properties import MaterialProperties
from pff_model import PFFModel
from q4_quadrature import q4_shape_data
from native_q4_diagnostics import energy_and_reaction, native_readout, physical_gap, weighted_error


def _problem():
    x = torch.tensor([[0.,0.],[1.,0.],[1.,1.],[0.,1.]],dtype=torch.float64)
    cells = torch.tensor([[0,1,2,3]])
    shape, deriv, weights = q4_shape_data(x,cells)
    return SimpleNamespace(native_x=x,cells=cells,native_shape=shape,native_dshape=deriv,
        native_weights=weights,native_area=weights.sum(1),mat=MaterialProperties(1.,.3,1.,.01),
        model=PFFModel('AT1','volumetric',.001,residual_stiffness=0.),
        penalty=dict(enable=True,mode='fem_gp_q4',spatial_integration='native_q4_gp4',recovery_penalty_coefficient=13781.25),
        fatigue=dict(fatigue_on=True,loading_type='cyclic',accum_type='carrara',degrad_type='asymptotic',alpha_T=.5))


def _fields(problem, damage=.2):
    x,y=problem.native_x.T
    return dict(u=.02*x+.04*y,v=.1*y,d=torch.full_like(x,damage))


def test_gp_weighting_precedes_square_reduction_and_vector_components_sum():
    w=torch.tensor([[1.,3.]],dtype=torch.float64)
    value=torch.tensor([[0.,2.]],dtype=torch.float64)
    result=weighted_error(value,torch.zeros_like(value),w,.5)
    assert result['absolute_rms']==pytest.approx(3.**.5)
    assert result['normalized_rms']==pytest.approx(2*3.**.5)
    assert result['signed_integral_difference']==6.
    vector=torch.tensor([[[3.,4.],[3.,4.]]],dtype=torch.float64)
    assert weighted_error(vector,torch.zeros_like(vector),w,1.)['absolute_rms']==5.
    with pytest.raises(ValueError,match='weights'):
        weighted_error(value,torch.zeros_like(value),-w,1.)


@pytest.mark.parametrize('damage', [.2,-.02])
def test_independent_readout_energy_matches_training_native_assembly(damage):
    problem=_problem();fields=_fields(problem,damage)
    old=torch.full_like(fields['d'],.3)
    f=torch.tensor([[.3,.4,.6,.8]],dtype=torch.float64,requires_grad=True)
    actual=energy_and_reaction(problem,fields,old,f)
    expected=compute_energy(problem.native_x,fields['u'],fields['v'],fields['d'],old,
        problem.mat,problem.model,problem.native_area,problem.cells,f_fatigue=f.detach(),
        irreversibility_penalty_cfg=problem.penalty)
    assert actual['energy']['elastic']==pytest.approx(float(expected[0]),rel=1e-13)
    assert actual['energy']['fracture']==pytest.approx(float(expected[1]),rel=1e-13)
    assert actual['energy']['penalty_total']==pytest.approx(float(expected[2]),rel=1e-13)
    assert actual['energy']['total']==pytest.approx(float(sum(expected)),rel=1e-13)
    assert f.grad is None


def test_assembled_reaction_has_analytic_signed_force_and_unit_thickness():
    p=_problem();fields=_fields(p)
    result=energy_and_reaction(p,fields,torch.zeros(4,dtype=torch.float64),torch.ones((1,4),dtype=torch.float64))
    expected_x=.8**2*p.mat.mat_mu*.04
    expected_y=.8**2*(p.mat.mat_lmbda*.12+2*p.mat.mat_mu*.1)
    assert result['reaction']['top_xy']==pytest.approx([expected_x,expected_y],rel=1e-12)
    assert result['reaction']['bottom_xy']==pytest.approx([-expected_x,-expected_y],rel=1e-12)
    assert result['reaction']['top_plus_bottom_xy']==pytest.approx([0.,0.],abs=1e-15)
    assert result['reaction']['all_nodes_force_sum_xy']==pytest.approx([0.,0.],abs=1e-15)
    # Uniformly perturb both top nodal v values at fixed d/f. This is the
    # actual load-direction directional derivative, not a 2E/U estimate.
    eps=1e-6
    totals=[]
    for sign in (-1,1):
        changed={k:v.clone() for k,v in fields.items()}
        changed['v'][[2,3]]+=sign*eps
        totals.append(energy_and_reaction(p,changed,torch.zeros(4,dtype=torch.float64),
                                         torch.ones((1,4),dtype=torch.float64))['energy']['total'])
    assert (totals[1]-totals[0])/(2*eps)==pytest.approx(expected_y,rel=1e-8)


def test_raw_at_full_damage_and_old_history_remain_well_defined_immutable():
    p=_problem();fields=_fields(p,1.)
    old=dict(damage=torch.zeros(4,dtype=torch.float64),history=torch.full((1,4),.8,dtype=torch.float64),
             active_driver=torch.zeros((1,4),dtype=torch.float64))
    original={k:v.clone() for k,v in old.items()}
    fs=torch.ones((1,4),dtype=torch.float64)
    read=native_readout(p,fields,old,fs,old['history'],(1/(old['history']+.5))**2)
    # Partition-of-unity rounding can leave g(1) at O(machine-epsilon^2).
    assert torch.all(read['gp']['raw']>0) and torch.all(read['gp']['active'].abs()<1e-30)
    assert torch.equal(read['gp']['history'],old['history'])
    assert read['summary']['f_solve']['energy']['fracture']>read['summary']['fresh_f_commit']['energy']['fracture']
    for name in old: assert torch.equal(old[name],original[name])
    error=physical_gap(p,read,read)
    assert all(v['absolute_rms']==0 for v in error['native_gp_errors'].values())
    assert error['same_old_state_exact'] is True


def test_physical_gradient_scales_are_fixed_and_not_reference_error_floors():
    p=_problem();fields=_fields(p)
    old=dict(damage=torch.zeros(4,dtype=torch.float64),history=torch.zeros((1,4),dtype=torch.float64),
             active_driver=torch.zeros((1,4),dtype=torch.float64))
    ones=torch.ones((1,4),dtype=torch.float64)
    read=native_readout(p,fields,old,ones,old['history'],ones)
    other=dict(read,gp={k:v.clone() for k,v in read['gp'].items()})
    other['gp']['grad_u']+=torch.tensor([.12,0.],dtype=torch.float64)
    other['gp']['grad_d']+=torch.tensor([100.,0.],dtype=torch.float64)
    result=physical_gap(p,other,read)
    assert result['native_gp_errors']['grad_u']['absolute_rms']==pytest.approx(.12)
    assert result['native_gp_errors']['grad_u']['normalized_rms']==pytest.approx(1.)
    assert result['native_gp_errors']['grad_d']['absolute_rms']==pytest.approx(100.)
    assert result['native_gp_errors']['grad_d']['normalized_rms']==pytest.approx(1.)
