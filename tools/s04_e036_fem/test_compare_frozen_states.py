"""Tiny analytic FE arrays only: no optimizer, network or native solver."""
import copy
import hashlib
import json
from pathlib import Path
import sys

import h5py
import numpy as np
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import compare_frozen_states as compare


def analytic_state(strain=0.,damage=0.):
    """One unit square: exact constant-strain forces and integrated N_i=1/4."""
    nodes=np.array([[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]])
    cells=np.array([[0,1,2,3]])
    # Plane-strain Amor: deviatoric energy always active; positive volume only.
    mu=1./2.6; bulk=1./1.2
    raw=mu*(2*strain**2-(2*strain)**2/3)+.5*bulk*max(2*strain,0.)**2
    positive_stress=2*mu*(strain-2*strain/3)+bulk*max(2*strain,0.)
    stress=(1-damage)**2*positive_stress+bulk*min(2*strain,0.)
    active=(1-damage)**2*raw; A=.6+active; f=(1./(A+.5))**2
    penalty=421875. if damage<0 else 0.; recovery=13781.25 if damage<0 else 0.
    phase=(2*raw*(damage-1)+.375*f+(penalty+recovery)*damage)/4
    old=np.zeros((1,4,4));old[:,:,1]=.6;old[:,:,3]=(1./1.1)**2
    history=np.empty_like(old)
    history[:,:,0]=raw;history[:,:,1]=A;history[:,:,2]=active;history[:,:,3]=f
    return dict(nodes=nodes,cells=cells,u=np.r_[strain*nodes[:,0],strain*nodes[:,1]],
                d=np.full(4,damage),old_lower=np.zeros(4),old_history=old,
                raw=np.full((1,4),raw),Ru=.5*stress*np.array([-1.,1.,1.,-1.,-1.,-1.,1.,1.]),
                Rd=np.full(4,phase),trial_history=history,traction=np.zeros(8),
                active_u=np.arange(8),active_d=np.arange(4),fixed_u=np.array([],dtype=int),
                fixed_d=np.array([],dtype=int),fixed_u_values=np.array([],dtype=float),
                fixed_d_values=np.array([],dtype=float))


@pytest.mark.parametrize('strain,damage',[(0.,0.),(.1,.2),(-.1,.2),(.1,-.05),(0.,1.)])
def test_both_assemblies_match_exact_constant_strain_and_bound_reaction(strain,damage):
    state=analytic_state(strain,damage)
    report,fields=compare.compare_arrays(state)
    assert report['passed']
    if strain==damage==0:
        assert fields['energy']['Rd_free'].min()>0
        assert np.array_equal(fields['energy']['Rd_box_free'],np.zeros(4))
    json.dumps(report,allow_nan=False)  # Receipts must serialize the worst index.


@pytest.mark.parametrize('channel',['Ru','Rd','raw','P','A','f'])
def test_native_channel_mismatch_is_retained_and_not_repaired(channel):
    state=analytic_state(.1,.2)
    if channel in ('P','A','f'):
        slot={'P':2,'A':1,'f':3}[channel]
        state['trial_history'][0,0,slot]+=.01
    else:
        state[channel].flat[0]+=.01
    before=copy.deepcopy(state)
    report,_=compare.compare_arrays(state)
    assert not report['passed']
    assert not report['channels']['energy'][channel]['passed']
    for name in ('u','d','old_history','trial_history'):
        np.testing.assert_array_equal(state[name],before[name])


def test_zero_and_large_reference_use_the_predeclared_per_channel_threshold():
    assert compare.compare_channel(np.zeros(2),np.full(2,1e-10))['passed']
    assert not compare.compare_channel(np.zeros(2),np.full(2,1.01e-10))['passed']
    result=compare.compare_channel(np.array([100.,0.]),np.array([100.,9e-7]))
    assert result['passed']
    assert result['threshold']==1e-10+1e-8*100.


def exported_fixture():
    state=analytic_state(.1,.2)
    state['fixed_u']=np.array([0,4]);state['active_u']=np.array([1,2,3,5,6,7])
    state['fixed_u_values']=state['u'][state['fixed_u']].copy()
    state['material']=dict(compare.MATERIAL)
    state['state_key']=dict(cycle=1,substep=4)
    state['predecessor_key']=dict(cycle=1,substep=3)
    state['provenance']=dict(source='synthetic fixture; no native execution')
    compare._imports()
    from run_multicycle_cross_replay import q4_geometry
    N,B,W,_=q4_geometry(np.array([[-1.,-1.],[1.,-1.],[1.,1.],[-1.,1.]]),np.array([[0,1,2,3]]))
    state['quadrature']=dict(Nxi=N.T,dNdxi=B[0].transpose(1,2,0),gauss_W=W[0])
    digest=hashlib.sha256(state['nodes'].astype('<f4').tobytes()+state['cells'].astype('<i8').tobytes()).hexdigest()
    common=dict(schema='s04_e036_common_problem_v1',acceptance_config=compare.POLICY,
                tol_ir=.001,recovery_penalty_coefficient=13781.25,
                ordered_mesh_sha256_f32_i64=digest,fixed_damage_nodes_zero_based=[],fixed_damage_value=1.)
    for name in ('cells','active_u','active_d','fixed_u','fixed_d'):
        state[name]=(state[name]+1).astype(float)
    return state,common


def write_mat(path,state):
    with h5py.File(path,'w') as handle:
        def text(name,value):
            dataset=handle.create_dataset(name,data=np.frombuffer(value.encode('utf-16-le'),dtype='<u2').reshape(-1,1))
            dataset.attrs['MATLAB_class']=np.bytes_('char')
        def numeric(name,value):
            value=np.asarray(value)
            if value.ndim==1:value=value.reshape(-1,1)
            handle.create_dataset(name,data=value.transpose(tuple(reversed(range(value.ndim)))))
        text('schema',compare.SCHEMA)
        for name,value in state.items():
            if name in ('material','state_key','predecessor_key','provenance'):
                text(name+'_json',json.dumps(value))
            elif name=='quadrature':
                for key,array in value.items():numeric('quadrature/'+key,array)
            else:numeric(name,value)


def test_mat_storage_axes_and_blocked_displacement_readback(tmp_path):
    expected,common=exported_fixture();path=tmp_path/'native.mat';write_mat(path,expected)
    actual=compare.validate_state(compare.read_native(path),common,production=False)
    np.testing.assert_array_equal(actual['u'],expected['u'])
    np.testing.assert_array_equal(actual['old_history'],expected['old_history'])
    np.testing.assert_array_equal(actual['cells'],np.array([[0,1,2,3]]))
    assert actual['material']==compare.MATERIAL


def test_unused_legacy_old_slot_one_is_preserved_without_history_reinterpretation(tmp_path):
    state,common=exported_fixture()
    state['old_history'][:,:,0]=np.nan
    path=tmp_path/'legacy.mat';write_mat(path,state)
    actual=compare.validate_state(compare.read_native(path),common,production=False)
    assert np.isnan(actual['old_history'][:,:,0]).all()
    report,_=compare.compare_arrays(actual)
    assert report['passed']
    assert np.isnan(actual['old_history'][:,:,0]).all()


@pytest.mark.parametrize('corrupt,match',[
    (lambda s:s.update(nodes=s['nodes'].astype(np.float32)),'float64 precision'),
    (lambda s:s['active_u'].__setitem__(0,s['fixed_u'][0]),'disjoint complete'),
    (lambda s:s['material'].update(thickness=.5),'unit thickness'),
    (lambda s:s['quadrature']['Nxi'].__setitem__((0,0),99.),'GP order'),
])
def test_identity_and_support_mismatch_stop_before_assembly(corrupt,match):
    state,common=exported_fixture();corrupt(state)
    with pytest.raises(ValueError,match=match):compare.validate_state(state,common,production=False)


def test_native_material_roundoff_allowance_does_not_relax_array_tolerance():
    state,common=exported_fixture()
    state['material']['penalty_irrev']*=1.+5e-13
    compare.validate_state(state,common,production=False)
    assert not compare.compare_channel(np.zeros(1),np.array([1.01e-10]))['passed']
    state['material']['penalty_irrev']=compare.MATERIAL['penalty_irrev']*(1.+2e-12)
    with pytest.raises(ValueError,match='native material'):
        compare.validate_state(state,common,production=False)
    state['material']=dict(compare.MATERIAL,split_type='amor')
    with pytest.raises(ValueError,match='native material'):
        compare.validate_state(state,common,production=False)


@pytest.mark.parametrize('field,index,value',[
    ('d',0,-1e-12),('d',0,1.+1e-12),
    ('old_lower',0,-1e-12),('old_lower',0,1.+1e-12),
    ('old_lower',0,.20000002),
    ('old_history',(0,0,1),-1e-12),('old_history',(0,0,2),-1e-12),
    ('old_history',(0,0,3),0.),('old_history',(0,0,3),1.+1e-12),
    ('trial_history',(0,0,1),-1e-12),('trial_history',(0,0,2),-1e-12),
    ('trial_history',(0,0,3),0.),('trial_history',(0,0,3),1.+1e-12),
])
def test_invalid_physical_preimage_or_export_is_rejected_before_assembly(field,index,value):
    state,common=exported_fixture();state[field][index]=value
    with pytest.raises(ValueError,match='physical domain|requires nonnegative'):
        compare.validate_state(state,common,production=False)


def test_bad_input_failure_is_saved_and_cannot_be_overwritten(tmp_path,monkeypatch):
    path=tmp_path/'not_native.mat';path.write_bytes(b'not an admitted file')
    common=tmp_path/'common.json';common.write_text('{}')
    monkeypatch.setattr(compare,'configure_threads',lambda _:None)
    output=tmp_path/'report'
    report=compare.run(path,'0'*64,common,compare.sha256(common),output)
    assert not report['passed'] and report['error_type']=='ValueError'
    saved=(output/'comparison.json').read_bytes()
    assert b'SHA256 mismatch' in saved
    with pytest.raises(FileExistsError):compare.run(path,'0'*64,common,compare.sha256(common),output)
    assert (output/'comparison.json').read_bytes()==saved


def test_nonfinite_metadata_is_rejected_before_report_serialization():
    with pytest.raises(ValueError,match='nonfinite JSON constant'):
        compare.parse_json('{"untrusted_metric":NaN}')


def test_mac_full_mesh_guard_prevents_numerical_assembly(tmp_path,monkeypatch):
    path=tmp_path/'native.mat';path.write_bytes(b'fixture')
    common=tmp_path/'common.json';common.write_text('{}')
    monkeypatch.setattr(compare,'configure_threads',lambda _:None)
    monkeypatch.setattr(compare.sys,'platform','darwin')
    monkeypatch.setattr(compare,'read_native',lambda _:dict(nodes=np.zeros((65,2))))
    def forbidden(*args,**kwargs):pytest.fail('full mesh assembly must not run on Mac')
    monkeypatch.setattr(compare,'compare_arrays',forbidden)
    report=compare.run(path,compare.sha256(path),common,compare.sha256(common),tmp_path/'report')
    assert not report['passed'] and 'Mac is development-only' in report['error']
