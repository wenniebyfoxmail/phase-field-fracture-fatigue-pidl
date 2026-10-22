"""Tiny serialization/acceptance checks only: no NN, FEM or native kernel."""
import importlib.util
from pathlib import Path
import sys

import h5py
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('e036_export',ROOT/'tools/s04_e036_fem/export_window.py')
export=importlib.util.module_from_spec(spec);sys.modules[spec.name]=export;spec.loader.exec_module(export)


def mat(path, data):
    def field(g,k,v):
        if isinstance(v,dict):
            sub=g.create_group(k)
            for name,value in v.items():field(sub,name,value)
        elif isinstance(v,str):
            d=g.create_dataset(k,data=np.array([ord(c) for c in v],dtype=np.uint16)[:,None]);d.attrs['MATLAB_class']=b'char'
        else:
            a=np.atleast_2d(np.asarray(v))
            g.create_dataset(k,data=a.transpose(tuple(reversed(range(a.ndim)))))
    with h5py.File(path,'w') as h:
        for k,v in data.items():field(h,k,v)


def fixture(tmp_path, role='main', residual=0.):
    folder=tmp_path/'native';folder.mkdir()
    n=4;u=np.zeros(8);u[6:]=.02999988;d=np.zeros(4)
    hist=np.zeros((1,4,4));hist[:,:,3]=1
    key=export.state_key('S04_E011_FEM_Q4_C120',1,1);old_key=export.state_key(key['trajectory'],1,0)
    old=dict(u=np.zeros(8),d=d,lower=d,history=hist,version=0,state_key=old_key)
    source=tmp_path/'common.mat';mat(source,dict(common=old))
    material=dict(E=1,ni=.3,Gc=.01,ell=.01,res_stiff=0,alpha_T=.5,p=2,penalty_irrev=421875,penalty_recov=13781.25)
    policy=dict(joint_tol=4e-6 if role=='tightening' else 4e-4,u_tol=1e-8 if role=='tightening' else 1e-6,
                bound_tol=1e-8,active_tol=1e-10,history_tol=1e-10,expected_material=material)
    ru=np.zeros(8);ru[0]=residual;rd=np.ones(4)
    support=dict(nodes=np.array([[0,0],[1,0],[1,1],[0,1.]]),cells=np.array([[0,1,2,3]]),Nxi=np.eye(4),
                 free_u=np.array([0,1,2,3,4,5]),free_d=np.arange(4),bot=np.array([0,1]),top=np.array([2,3]),fixed_d=np.array([],dtype=int))
    metrics=dict(u_free_l2=residual,d_raw_free_l2=2.,d_nodal_box_l2=0.,criterion=residual/policy['u_tol'])
    audit=dict(u=u,d=d,raw=np.zeros((1,4)),ru=ru,rd=rd,policy=policy,joint_pass=1,feasible=1,
               old_version=0,f_solve=hist[:,:,3],f_commit=hist[:,:,3],history234_solve=hist[:,:,1:4],**metrics)
    proposal=dict(u=u,d=d,lower=d,raw=np.zeros((1,4)),history=hist,pre_version=0,version=1)
    mat(folder/'proposal.mat',dict(e036_status='validated_proposal_before_native_assignment',
        e036_audit=audit,e036_proposal=proposal,e036_old=old))
    mat(folder/'step_checkpoint.mat',dict(displ=u,p_field=d,p_field_old=d,history_vars_old=hist,
        SOL_CYCL_VAR=dict(n_cycle=1),i_step_completed=1))
    mat(folder/'readback.mat',dict(readback=dict(status='accepted_step_readback_matches_proposal',
        proposal_sha256=export.sha256(folder/'proposal.mat'),checkpoint_sha256=export.sha256(folder/'step_checkpoint.mat'),
        cycle=1,substep=1,version=1)))
    bind_completion(folder,key)
    return folder,source,support


def bind_completion(folder,key):
    mat(folder/'completion.mat',dict(completion=dict(state_key=key,history_commits=1,version=1,pre_version=0,
        **{n+'_sha256':export.sha256(folder/f) for n,f in [('proposal','proposal.mat'),('checkpoint','step_checkpoint.mat'),('readback','readback.mat')]})))


def row_for(folder):
    return dict(state_key=export.state_key('S04_E011_FEM_Q4_C120',1,1),**{n+'_sha256':export.sha256(folder/f) for n,f in [('proposal','proposal.mat'),('checkpoint','step_checkpoint.mat'),('readback','readback.mat')]})


def test_roundtrip_native_float64(tmp_path):
    folder,source,support=fixture(tmp_path)
    result=export.convert_step(folder,source,'stored_u0',support,'main',tmp_path/'export',row_for(folder))
    with np.load(result['snapshot']['path']) as z:
        assert z['u'].dtype==np.float64 and z['history'].shape==(1,4)
        assert str(z['source_checkpoint_sha256'])==export.sha256(folder/'step_checkpoint.mat')
    import json
    admission=json.loads(Path(result['admission']['path']).read_text())
    assert admission['solver_policy']==dict(u_tol=1e-6,joint_tol=4e-4)
    assert admission['native_residual_reduction']['d_raw_free_l2']==2.


def test_accepted_boolean_cannot_hide_bad_vectors(tmp_path):
    folder,source,support=fixture(tmp_path,residual=1e-4)
    with pytest.raises(ValueError,match='residual fails'):
        export.convert_step(folder,source,'stored_u0',support,'main',tmp_path/'export',row_for(folder))


def test_changed_checkpoint_rejected_even_with_rebound_hash(tmp_path):
    folder,source,support=fixture(tmp_path)
    with h5py.File(folder/'step_checkpoint.mat','a') as h:h['p_field'][0,0]=.1
    bind_completion(folder,export.state_key('S04_E011_FEM_Q4_C120',1,1))
    with pytest.raises(ValueError,match='checkpoint p_field differs'):
        export.convert_step(folder,source,'stored_u0',support,'main',tmp_path/'export',row_for(folder))


def test_wrong_solver_policy_rejected(tmp_path):
    folder,source,support=fixture(tmp_path)
    with pytest.raises(ValueError,match='actual native policy differs'):
        export.convert_step(folder,source,'stored_u0',support,'tightening',tmp_path/'export',row_for(folder))


def reduce(d,lower,rd):
    return export.reduce_residual(np.zeros(2),np.array([d]),np.array([lower]),np.zeros(2),np.array([rd]),
                                  np.arange(2),np.array([0]),4e-4,1e-6)


def test_lower_bound_positive_force_is_valid():
    assert reduce(0,0,100)['d_nodal_box_l2']==0


def test_narrow_noncollapsed_interval_retains_raw():
    with pytest.raises(ValueError,match='residual fails'):reduce(1-5e-11,1-8e-11,1)
    assert reduce(1,1,100)['d_nodal_box_l2']==0


@pytest.mark.parametrize('d,lower',[(-1e-12,0),(1+1e-12,0),(.1,.2)])
def test_physical_and_healing_bounds(d,lower):
    with pytest.raises(ValueError,match='feasibility'):reduce(d,lower,0)


def predecessor_fixture(tmp_path):
    folder,source,support=fixture(tmp_path)
    out=tmp_path/'predecessor';out.mkdir()
    with h5py.File(folder/'proposal.mat','r') as src,h5py.File(out/'native_admission.mat','w') as dst:
        src.copy('e036_audit',dst,name='audit');dst['audit/u'][...]=0
    key=export.state_key('S04_E011_FEM_Q4_C120',1,0)
    u,d,hist=export.source_arrays(source,'stored_u0')
    packet=out/'admitted_predecessor.mat'
    mat(packet,dict(pre=dict(u=u,d=d,lower=d,history=hist,state_key=key,
        admission=dict(accepted=1,native_residual_checked=1,checkpoint_readback_verified=1,
                       predecessor_sha256=export.sha256(source)))))
    mat(out/'admission_report.mat',dict(report=dict(status='admitted_current_native_predecessor',
        packet_sha256=export.sha256(packet),native_solves=0,history_commits=0,
        source=dict(sha256=export.sha256(source)))))
    import json
    npz=tmp_path/'input.npz'
    np.savez(npz,u=u[:4],v=u[4:],damage=d,history=hist[:,:,1],active_driver=hist[:,:,2],f_commit=hist[:,:,3],
        state_key_json=json.dumps(key),source_checkpoint_sha256=export.sha256(source),ordered_mesh_sha256_f32_i64=export.MESH_SHA)
    return out,source,support,npz


def test_admission_export_binds_existing_npz(tmp_path):
    out,source,support,npz=predecessor_fixture(tmp_path)
    ref=export.convert_predecessor(out,source,'stored_u0',npz,support,tmp_path/'admission.json')
    import json
    saved=json.loads(Path(ref['path']).read_text())
    assert saved['predecessor_sha256']==export.sha256(npz)
    assert saved['source_checkpoint']['sha256']==export.sha256(source)


def test_admission_rejects_changed_native_packet(tmp_path):
    out,source,support,npz=predecessor_fixture(tmp_path)
    with h5py.File(out/'admitted_predecessor.mat','a') as h:h['pre/d'][0,0]=.2
    with pytest.raises(ValueError,match='admitted preimage d differs'):
        export.convert_predecessor(out,source,'stored_u0',npz,support,tmp_path/'admission.json')


def test_windows_relocation_stays_inside_root():
    spec=importlib.util.spec_from_file_location('e036_prepare',ROOT/'tools/s04_e036_fem/prepare_stage_b_config.py')
    prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
    assert prep.relative('C:/jobs/A/native/Sources/a.f90','c:/jobs/a')=='native/Sources/a.f90'
    with pytest.raises(ValueError,match='outside'):prep.relative('C:/jobs/A2/a','C:/jobs/A')
    with pytest.raises(ValueError,match='noncanonical'):prep.relative('C:/jobs/A/../x','C:/jobs/A')


def test_substituted_self_consistent_step_is_not_in_original_window(tmp_path):
    folder,source,support=fixture(tmp_path)
    row=row_for(folder)
    # This different valid raw lower-bound reaction leaves the same fields,
    # key, source and acceptance; rebind the local trio exactly as another run.
    with h5py.File(folder/'proposal.mat','a') as h:
        h['e036_audit/rd'][...]=2.
        h['e036_audit/d_raw_free_l2'][...]=4.
    with h5py.File(folder/'readback.mat','a') as h:
        del h['readback/proposal_sha256']
        x=h['readback'].create_dataset('proposal_sha256',data=np.array([ord(c) for c in export.sha256(folder/'proposal.mat')],dtype=np.uint16)[:,None]);x.attrs['MATLAB_class']=b'char'
    bind_completion(folder,export.state_key('S04_E011_FEM_Q4_C120',1,1))
    with pytest.raises(ValueError,match='not bound to completed window row'):
        export.convert_step(folder,source,'stored_u0',support,'main',tmp_path/'export',row)


def test_saved_window_request_and_row_are_verified(tmp_path):
    folder,source,support=fixture(tmp_path);row=row_for(folder);row['history_commits']=1
    path=tmp_path/'window_result.mat'
    request=dict(cycle=1,substeps=[1],role='main')
    mat(path,dict(result=dict(status='completed',history_commits=1,request=request,rows=row)))
    assert export.read_window_rows(path,request,'S04_E011_FEM_Q4_C120')[0]['checkpoint_sha256']==row['checkpoint_sha256']
    with pytest.raises(ValueError,match='request differs'):
        export.read_window_rows(path,dict(cycle=1,substeps=[2],role='main'),'S04_E011_FEM_Q4_C120')


def test_native_multirow_matlab_reference_layout(tmp_path):
    path=tmp_path/'result.mat';trajectory='S04_E011_FEM_Q4_C120'
    request=dict(cycle=1,substeps=[1,2],role='main')
    rows=[dict(state_key=export.state_key(trajectory,1,s),history_commits=1,
               proposal_sha256='a'*64,checkpoint_sha256='b'*64,readback_sha256='c'*64) for s in (1,2)]
    mat(path,dict(result=dict(status='completed',history_commits=2,request=request),r0=rows[0],r1=rows[1]))
    with h5py.File(path,'a') as h:
        saved=h['result'].create_group('rows')
        for name in rows[0]:
            refs=np.empty((2,1),dtype=h5py.ref_dtype)
            for i in range(2):refs[i,0]=h[f'r{i}/{name}'].ref
            saved.create_dataset(name,data=refs)
    actual=export.read_window_rows(path,request,trajectory)
    assert [r['state_key']['substep'] for r in actual]==[1,2]


@pytest.mark.parametrize('failure',[None,'wrong_arm','incomplete','nonfinite'])
def test_oracle_requires_declared_complete_lplus(tmp_path,failure):
    import json
    spec=importlib.util.spec_from_file_location('e036_oracle_prepare',ROOT/'tools/s04_e036_fem/prepare_oracle_candidate.py')
    prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
    key=export.state_key('S04_E011_FEM_Q4_C120',1,2)
    meta=dict(schema='s04_e036_mechanism_fields_v1',state_key=key,arm='Lplus',mapping='legacy',weight_l2=1e-5,
              stage='first_2000',rprop_updates=2000,history_commit_count=0,predecessor_checkpoint_sha256='a'*64,
              network_state_sha256='b'*64,complete_endpoint=True)
    if failure=='wrong_arm':meta['arm']='Czero'
    u=np.zeros(86756,dtype=np.float32);d=u.copy()
    if failure=='nonfinite':d[2]=np.nan
    fields=tmp_path/'fields.npz';np.savez(fields,u=u,v=u,d=d,metadata_json=json.dumps(meta))
    receipt=dict(fields_sha256=export.sha256(fields),bundle_sha256='b'*64,readback_verified=True,
                 endpoint_complete=failure!='incomplete',physical_accepted=False)
    completion=tmp_path/'completion.json';completion.write_text(json.dumps(receipt))
    if failure:
        with pytest.raises(ValueError):prep.read_endpoint(fields,completion,1,2,'a'*64)
    else:
        initial,info=prep.read_endpoint(fields,completion,1,2,'a'*64)
        assert initial['u'].dtype==np.float64 and initial['u'].shape==(173512,1)
        assert initial['complete_endpoint'] and not info['history_fields_consumed']


def test_verified_f1_endpoint_repackages_as_predecessor_without_native(tmp_path):
    folder,source,support=fixture(tmp_path)
    target=export.convert_step(folder,source,'stored_u0',support,'main',tmp_path/'target',row_for(folder))
    pred=export.export_as_predecessor(target,tmp_path/'as_predecessor')
    import json
    a=json.loads(Path(pred['admission']['path']).read_text())
    assert a['schema']=='s04_e036_predecessor_admission_v1' and a['new_native_calls']==0
    assert a['source_checkpoint']['sha256']==export.sha256(folder/'step_checkpoint.mat')
    with np.load(pred['predecessor']['path']) as z,np.load(target['snapshot']['path']) as t:
        assert np.array_equal(z['damage'],t['d']) and z['damage'].dtype==np.float64
        assert np.array_equal(z['history'],t['history']) and 'd' not in z


def oracle_fixture(tmp_path):
    folder,source,support=fixture(tmp_path)
    key=export.state_key('S04_E011_FEM_Q4_C120',1,1)
    raw_u=np.zeros(8);raw_d=np.full(4,-.1);pu=raw_u.copy();pu[6:]=.02999988;pd=np.zeros(4)
    initial=dict(u=raw_u,d=raw_d,source_snapshot_sha256='b'*64,source_completion_sha256='c'*64)
    projection=dict(raw_u=raw_u,raw_d=raw_d,projected_u=pu,projected_d=pd,state_key=key,
        predecessor_checkpoint_sha256=export.sha256(source),source_snapshot_sha256='b'*64,
        source_completion_sha256='c'*64,u_max_abs_change=float(np.max(abs(pu-raw_u))),
        u_l2_change=float(np.linalg.norm(pu-raw_u)),d_max_abs_change=.1,d_l2_change=.2)
    mat(folder/'initial_candidate.mat',dict(initial_fields=initial,projection=projection))
    row=row_for(folder);row.update(initial_candidate_sha256=export.sha256(folder/'initial_candidate.mat'),
        declared_initial_fields_sha256='a'*64,initial_source_snapshot_sha256='b'*64,initial_source_completion_sha256='c'*64)
    mat(folder/'completion.mat',dict(completion=dict(**row,history_commits=1,pre_version=0,version=1,
        initial_candidate='initial_candidate.mat')))
    support['oracle_binding']=dict(initial_fields_sha256='a'*64,initial_source_snapshot_sha256='b'*64,
        initial_source_completion_sha256='c'*64)
    return folder,source,support,row


def test_oracle_initial_record_is_bound_to_original_window(tmp_path):
    folder,source,support,row=oracle_fixture(tmp_path)
    target=export.convert_step(folder,source,'stored_u0',support,'nodal_oracle',tmp_path/'export',row)
    import json
    receipt=json.loads(Path(target['admission']['path']).read_text())
    assert receipt['schema']=='s04_e036_nodal_oracle_admission_v1'
    assert receipt['oracle_source_snapshot_sha256']=='b'*64


def test_self_consistent_oracle_initial_substitution_is_rejected(tmp_path):
    folder,source,support,row=oracle_fixture(tmp_path)
    # Change only the oracle guess/projection; leave the completed window and
    # accepted proposal/checkpoint/readback untouched.
    with h5py.File(folder/'initial_candidate.mat','a') as h:
        h['initial_fields/d'][...]=-.2;h['projection/raw_d'][...]=-.2
        h['projection/d_max_abs_change'][...]=.2;h['projection/d_l2_change'][...]=.4
    with pytest.raises(ValueError,match='not bound to completed window row: initial_candidate'):
        export.convert_step(folder,source,'stored_u0',support,'nodal_oracle',tmp_path/'export',row)


def test_oracle_window_source_must_match_input_authority(tmp_path):
    folder,source,support,row=oracle_fixture(tmp_path)
    support['oracle_binding']['initial_source_snapshot_sha256']='d'*64
    with pytest.raises(ValueError,match='persisted input authority'):
        export.convert_step(folder,source,'stored_u0',support,'nodal_oracle',tmp_path/'export',row)
