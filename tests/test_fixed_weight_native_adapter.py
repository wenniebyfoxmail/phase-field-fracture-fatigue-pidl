"""Source-aware adaptation tests, no scientific solve or training."""
from dataclasses import replace
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
import pytest
import torch

sys.path[:0] = [str(Path(__file__).resolve().parents[1]/'source'),
               str(Path(__file__).resolve().parents[1]/'scripts')]
from fixed_weight_contract import (Mesh,Material,StateKey,RecoveredInitialKey,
    RecoveredInitialState,adapt_decoded_stage0a,SEMANTICS)
from fixed_weight_native_adapter import (adapt_native,precision_bound_row,PRODUCER,BINARY_LOADS)
from validate_fixed_weight_native_archives import validate_sequence


def fixture(initial=False):
    xy=np.array([[0.,0.],[1.,0.],[1.,1.],[0.,1.]])
    mesh=Mesh(torch.from_numpy(xy),torch.tensor([[0,1,2,3]]),'mesh')
    material=Material(1.,.3,.01,.01,.5,2.,0.,1.)
    u=np.zeros_like(xy);d=np.array([1.,.1,0.,0.]);history=np.zeros((1,4,4))
    if initial:
        key=RecoveredInitialKey('run','condition','reference','mesh',1,0,0,'initial',0.)
    else:
        key=StateKey('run','condition','reference','mesh',1,1,1,'load',.1)
        u[2:,1]=.1
        history[...,1]=31.74907345088553
    history[...,3]=np.minimum(1.,(1.-(history[...,1]-.5)/(history[...,1]+.5))**2.)
    decoded=SimpleNamespace(logical_cycle=key.cycle,logical_substep=key.substep,
        source_state_key=f'c{key.cycle:04d}_s{key.substep:02d}',imposed_displacement=key.load,
        u_node=u,d_node=d,history_gp=history,strain_en_undgr_gp=np.zeros((1,4)),
        strain_en_degr_gp=np.zeros((1,4)),payload_sha256='test-fixture')
    kwargs=dict(archive='hard5_u0115_stage0b',source_commit=PRODUCER,
        source_timing=key.timing,native_shape=np.zeros((4,4)),native_derivative=np.zeros((4,2,4)))
    return decoded,key,mesh,material,kwargs


def test_source_f_is_validated_before_stable_factor_is_derived_and_raw_is_unchanged():
    raw,key,mesh,mat,kwargs=fixture()
    before=[a.copy() for a in (raw.u_node,raw.d_node,raw.history_gp)]
    state,receipt=adapt_native(raw,key,mesh,mat,**kwargs)
    assert receipt['raw_f_stable_max_relative_error']>8*np.finfo(float).eps
    assert receipt['raw_f_source_max_relative_error']<=8*np.finfo(float).eps
    assert all(np.array_equal(a,b) for a,b in zip(before,(raw.u_node,raw.d_node,raw.history_gp)))
    assert np.array_equal(state.history.numpy(),raw.history_gp[...,:3])
    with pytest.raises(ValueError,match='fatigue factor'):
        adapt_decoded_stage0a(raw,key,mesh,mat,source_timing=key.timing,source_semantics=SEMANTICS)
    raw.history_gp[...,3]=0.
    with pytest.raises(ValueError,match='raw f'):
        adapt_native(raw,key,mesh,mat,**kwargs)


def test_native_recovery_keeps_timing_and_old_adapter_rejects_it():
    raw,key,mesh,mat,kwargs=fixture(True)
    state,_=adapt_native(raw,key,mesh,mat,**kwargs)
    assert isinstance(state,RecoveredInitialState) and state.key.timing=='pre_cycle_committed'
    with pytest.raises(ValueError):
        adapt_decoded_stage0a(raw,key,mesh,mat,source_timing=key.timing,source_semantics=SEMANTICS)
    raw.history_gp[...,1]=1.
    with pytest.raises(ValueError):adapt_native(raw,key,mesh,mat,**kwargs)


@pytest.mark.parametrize('bad',['source','load','timing','alias','negative','float32'])
def test_native_adapter_rejects_unexplained_or_unbound_inputs(bad):
    raw,key,mesh,mat,kwargs=fixture()
    if bad=='source':kwargs['source_commit']='wrong'
    if bad=='load':raw.imposed_displacement=np.nextafter(key.load,np.inf)
    if bad=='timing':kwargs['source_timing']='pre_cycle_committed'
    if bad=='alias':raw.source_state_key='c0000_s05'
    if bad=='negative':raw.history_gp[0,0,0]=raw.strain_en_undgr_gp[0,0]=-1e-100
    if bad=='float32':mesh=replace(mesh,xy=mesh.xy.float())
    with pytest.raises(ValueError):adapt_native(raw,key,mesh,mat,**kwargs)


def test_csv_token_mapping_does_not_edit_index_or_relax_scalar_comparison():
    row={'substep':'1','imposed_displacement':'0.028749885'}
    schedule=BINARY_LOADS['hard5_u0115_stage0b']
    bound=precision_bound_row(row,archive='hard5_u0115_stage0b',schedule=schedule)
    assert row['imposed_displacement']=='0.028749885'
    assert float(bound['imposed_displacement'])==schedule[0]
    assert float(row['imposed_displacement'])!=float(bound['imposed_displacement'])
    with pytest.raises(ValueError,match='token'):
        precision_bound_row({**row,'imposed_displacement':'0.0287498851'},archive='hard5_u0115_stage0b',schedule=schedule)
    with pytest.raises(ValueError,match='schedule'):
        precision_bound_row(row,archive='hard5_u0115_stage0b',schedule=[.028749885,*schedule[1:]])


def test_sequence_rejects_missing_intermediate_and_bad_alias():
    rows=[]
    for c in (1,2):
        for s in range(6):
            key=f'c{c:04d}_s{s:02d}';alias=s==0 and c>1
            source='c0001_s05' if alias else key
            rows.append(dict(state_key=key,cycle=str(c),substep=str(s),source_state_key=source,
                is_alias=str(int(alias)),timing='pre_cycle_committed' if s==0 else 'post_history_commit',
                converged='1',nominal_load_factor=str([0,.25,.5,.75,1,0][s]),
                payload_file=source+'.mat',payload_sha256=source,imposed_displacement='0'))
    assert len(validate_sequence(rows,2))==11
    with pytest.raises(ValueError,match='coverage'):validate_sequence(rows[:3]+rows[4:],2)
    rows[6]['payload_sha256']='bad'
    with pytest.raises(ValueError,match='alias'):validate_sequence(rows,2)
