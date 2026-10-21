"""Artificial FE fields only: no NN construction/training or FEM solve."""
from pathlib import Path
import sys
import numpy as np
import pytest
import torch
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'source'), str(ROOT/'tools/s04_e011_analysis')]
from cyclic_acceptance import (AcceptancePolicy, assess_nodal_residuals, nodal_box_residual,
    make_final_residual_check, ordered_mesh_digest, common_damage_mask, install_sent_common_problem)
from compute_energy import compute_energy, get_psi_plus_per_elem
from fatigue_history import update_fatigue_history, compute_fatigue_degrad
from material_properties import MaterialProperties
from pff_model import PFFModel
from q4_quadrature import q4_shape_data
from tri3_quadrature import tri3_shape_data

POLICY = dict(mode='nodal_box_kkt',joint_tol=4e-4,u_tol=1e-6,bounds_tol=1e-8,
              active_tol=1e-10,bc_tol=5e-8,history_atol=2e-6,history_rtol=2e-6)

def case(kind='q4', zero=False):
    points = torch.tensor([[0.,0.],[1.,0.],[1.,1.],[0.,1.]],dtype=torch.float64)
    if kind == 'tri3': points = points[:3]
    n = len(points); cells = torch.arange(n).reshape(1,n)
    shape, B, weights = (q4_shape_data if kind=='q4' else tri3_shape_data)(points,cells)
    mat = MaterialProperties(1.,.3,1.,.01); pff = PFFModel('AT1','volumetric',.001)
    cfg = dict(enable=True,mode='fem_gp_q4' if n==4 else 'fem_gp_tri3',
               spatial_integration='native_q4_gp4' if n==4 else 'native_tri3_gp3',recovery_penalty_coefficient=13781.25)
    fat = dict(accum_type='carrara',loading_type='cyclic',degrad_type='asymptotic',alpha_T=.5,
               history_storage='q4_gp4' if n==4 else 'tri3_gp3',
               history_driver_reduction=dict(enable=True,mode='native_q4_gp4' if n==4 else 'native_tri3_gp3'))
    u=.6*points[:,0];v=.3*points[:,1];d=torch.linspace(.1,.3,n,dtype=torch.float64)
    if zero:u=torch.zeros(n,dtype=torch.float64);v=u.clone();d=u.clone()
    oldd=torch.zeros_like(d);A=torch.full((1,n),.6,dtype=torch.float64);r=torch.zeros_like(A)
    active=get_psi_plus_per_elem(points,u,v,d,mat,pff,weights.sum(1),cells,history_driver_reduction_dict=fat['history_driver_reduction'])
    trial=update_fatigue_history(A,active,r,fat);f=compute_fatigue_degrad(trial,fat)
    state=dict(u=u,v=v,d=d,old_damage=oldd,old_history=A,old_active_driver=r,
               active_driver=active,trial_history=trial,f_solve=f.clone(),f_commit=f.clone(),state_token='fixed')
    return points,cells,weights.sum(1),mat,pff,cfg,fat,state,shape,B,weights

def callback(c,free=None):
    pts,con,area,mat,pff,cfg,fat,s,*_=c;n=len(pts)
    free=torch.ones(n,dtype=torch.bool) if free is None else free
    return make_final_residual_check(pts,con,area,mat,pff,free_u_mask=free,free_v_mask=free,
        free_d_mask=free,prescribed_u=s['u'],prescribed_v=s['v'],prescribed_d=s['d'],
        config=POLICY,fatigue_dict=fat,irreversibility_penalty_cfg=cfg)

@pytest.mark.parametrize('kind',['q4','tri3'])
def test_at1_lower_reaction_accepted_and_stale_history_rejected(kind):
    c=case(kind,True);s=c[7];check=callback(c)
    result=check(s)
    assert result['accepted'] and result['fresh_current_state'] and result['state_token']=='fixed'
    assert result['metrics']['phase_raw_l2']>0
    assert result['metrics']['phase_box_kkt_l2']==0
    old=s['old_history'].clone()
    bad=dict(s,trial_history=s['trial_history']+.01)
    assert not check(bad)['accepted']
    assert torch.equal(s['old_history'],old)
    assert all(x.grad is None for x in (s['u'],s['v'],s['d']))

@pytest.mark.parametrize('kind',['q4','tri3'])
def test_callback_matches_independent_native_equation_assembly(kind):
    # Same analytic weak-form witness for Q4 and T3; no differentiation through f.
    from audit_phase_tangent import assemble
    from localize_endpoint_tight import mechanics_force
    c=case(kind);pts,cells,area,mat,pff,cfg,fat,s,N,B,W=c
    n=len(pts);cn=cells.numpy();bn=B.numpy()
    from compute_energy import raw_strain_energy_density
    gu=torch.einsum('en,egdn->egd',s['u'][cells],B)
    gv=torch.einsum('en,egdn->egd',s['v'][cells],B)
    raw=raw_strain_energy_density(gu[...,0],gv[...,1],.5*(gu[...,1]+gv[...,0]),mat,pff)
    history=np.zeros((1,n,4));history[:,:,1]=s['old_history'].numpy();history[:,:,2]=s['old_active_driver'].numpy()
    rd,meta=assemble(s['d'].numpy(),raw.numpy(),s['old_damage'].numpy(),history,cn,N.numpy(),bn,W.numpy(),n)
    ru=mechanics_force(np.r_[s['u'].numpy(),s['v'].numpy()],s['d'].numpy(),cn,N.numpy(),bn,W.numpy(),n)
    result=callback(c)(s)['metrics']
    np.testing.assert_allclose(result['phase_raw_l2'],np.linalg.norm(rd),rtol=1e-12,atol=1e-13)
    np.testing.assert_allclose(result['u_residual_l2'],np.linalg.norm(ru),rtol=1e-12,atol=1e-13)
    assert result['fresh_history_consistent']


def test_bound_signs_narrow_interval_and_infeasibility():
    d=torch.tensor([0.,1.,.5,1.,1.-5e-11],dtype=torch.float64)
    lower=torch.tensor([0.,0.,0.,1.,1.-1e-10],dtype=torch.float64)
    g=torch.tensor([3.,-2.,4.,9.,7.],dtype=torch.float64)
    torch.testing.assert_close(nodal_box_residual(d,g,lower,torch.ones_like(d),1e-10),torch.tensor([0.,0.,4.,0.,7.],dtype=torch.float64))
    m=torch.ones(1,dtype=torch.bool);z=torch.zeros(1,dtype=torch.float64)
    opts=dict(u_force=z,v_force=z,d_force=z,lower=z,free_u=m,free_v=m,free_d=m,bc_error=0,policy=POLICY)
    assert not assess_nodal_residuals(damage=z-.001,**opts)['accepted']
    assert not assess_nodal_residuals(damage=z+1.01,**opts)['accepted']
    assert not assess_nodal_residuals(damage=z-1e-9,**opts)['accepted']
    assert not assess_nodal_residuals(damage=z+1+1e-9,**opts)['accepted']
    opts['bc_error']=.01
    assert not assess_nodal_residuals(damage=z,**opts)['accepted']


def test_prescribed_damage_reaction_excluded_but_value_checked():
    c=case();s=c[7];check=callback(c,torch.zeros(4,dtype=torch.bool))
    assert check(s)['accepted']
    assert not check(dict(s,d=s['d']+.001))['accepted']


def test_policy_explicit_nonfinite_and_zero_tolerances_rejected():
    with pytest.raises(TypeError): AcceptancePolicy.from_dict({})
    for key in ('joint_tol','u_tol'):
        with pytest.raises(ValueError): AcceptancePolicy.from_dict({**POLICY,key:0})
    with pytest.raises(ValueError): AcceptancePolicy.from_dict({**POLICY,'bounds_tol':float('nan')})


def test_material_and_mesh_bind_fail_closed():
    c=case();pts,con,_,mat,pff,cfg,*_=c
    conf=dict(ordered_mesh_sha256_f32_i64=ordered_mesh_digest(pts,con),fixed_damage_nodes_zero_based=[0],fixed_damage_value=1.)
    assert common_damage_mask(pts,con,conf).tolist()==[True,False,False,False]
    with pytest.raises(ValueError): common_damage_mask(pts.flip(0),con,conf)
    with pytest.raises(ValueError): common_damage_mask(pts,con,{**conf,'fixed_damage_nodes_zero_based':[0,0]})
    class Capture:
        def set_fixed_damage_boundary(self,*args):self.args=args
    sink=Capture()
    kw=dict(inp=pts,T_conn=con,field_comp=sink,matprop=mat,pffmodel=pff,irreversibility_penalty_cfg=cfg,config=conf,
            fatigue_dict={**c[6],'history_driver_mode':'current_active'})
    install_sent_common_problem(**kw)
    assert sink.args[-1]==1
    pff.tol_ir=.005
    with pytest.raises(ValueError,match='MAT_CHAR'):install_sent_common_problem(**kw)


def test_fixed_phase_mapping_preserves_free_values_and_blocks_boundary_gradient():
    # Dummy raw-field provider: no neural network is constructed or trained.
    sys.path.insert(0,str(ROOT/'SENS_tensile'))
    from field_computation import FieldComputation
    p=case()[0]
    raw=torch.tensor([[0.,0.,-.5],[.1,.2,.4],[.2,.1,.3],[0.,0.,-.8]],dtype=torch.float64,requires_grad=True)
    field=FieldComputation(net=lambda _:raw,domain_extrema=torch.tensor([[0.,1.],[0.,1.]]),
                           lmbda=torch.tensor([.12]),theta=torch.tensor([np.pi/2]))
    before=field.fieldCalculation(p)
    mask=torch.tensor([True,False,False,False])
    field.set_fixed_damage_boundary(p,mask,1.)
    after=field.fieldCalculation(p)
    assert torch.equal(before[0],after[0]) and torch.equal(before[1],after[1])
    assert torch.equal(before[2][~mask],after[2][~mask]) and after[2][0]==1
    grad=torch.autograd.grad(after[2].sum(),raw)[0]
    assert grad[0,2]==0 and (grad[1:,2]>0).all()
    with pytest.raises(ValueError,match='ordered full mesh'):field.fieldCalculation(p.flip(0))
