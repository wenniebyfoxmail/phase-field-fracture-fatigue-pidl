"""NEW artificial receipt fixtures only: no NN/AD/SVD/FEM/physical solve.

Scalar torch values below are bookkeeping for an injected rollback exception;
there is no Module, forward, autograd, producer, or real-source asset access.
"""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch

# Standalone new-fixture command also needs the storage sampler sibling.
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'s04_e011_execution'))
import profiled_hidden_receipts as receipts
import profiled_hidden_e011_runtime as runtime_module
from profiled_hidden_adapter import AdapterStop,Guard,reprofile_check
from profiled_hidden_e011_runtime import Runtime


def algebra(multiplier=1.):
    return SimpleNamespace(fields=2,parameters=1,q=lambda v:np.array([multiplier*v[0],0.]))


def returned(delta,**changes):
    return dict(q=np.array([delta[0],0.]),actual_nn=True,full_current_basis=True,persisted_actual_phi=True,
        frozen_state=True,rolled_back=True,rank=1,head_gradient_inf=1e-12,realization_maxabs=1e-12,**changes)


def events(root):
    return [json.loads(p.read_text()) for p in sorted(root.glob('[0-9]*.json'))]


def array(event,name):
    ref=event['arrays'][name];p=Path(ref['path'])
    assert hashlib.sha256(p.read_bytes()).hexdigest()==ref['sha256']
    return np.load(p,allow_pickle=False)


def test_failed_first_pair_persists_prediction_sides_difference_scale_before_stop(tmp_path):
    root=tmp_path/'audit';rec=receipts.ProfileCheckRecorder(root,{'artificial':True});calls=[]
    def trial(delta):calls.append(delta.copy());return returned(delta)
    with pytest.raises(AdapterStop,match='actual_full_profile_derivative_mismatch'):
        reprofile_check(algebra(2.),trial,[np.array([1.])],rank=1,recorder=rec)
    es=events(root);compare=next(e for e in es if e['event']=='comparison')
    assert len(calls)==2 and [e['event'] for e in es][-2:]==['comparison','check_failed']
    assert compare['data']['error']==1. and compare['data']['scale']==2.
    assert compare['data']['tolerance']==1e-10+1e-4*2.
    assert np.array_equal(array(compare,'FD'),[1.,0.])
    assert np.array_equal(array(compare,'difference'),[1.,0.])
    prediction=next(e for e in es if e['event']=='prediction')
    assert np.array_equal(array(prediction,'Qv'),[2.,0.])
    sides=[e for e in es if e['event']=='side_returned']
    assert [e['data']['side'] for e in sides]==['plus','minus']
    assert np.array_equal(array(sides[0],'q_raw'),[1e-6,0.])
    assert np.array_equal(array(sides[1],'q_raw'),[-1e-6,0.])
    for e in es:
        for name in e['arrays']:
            if e['arrays'][name].get('available'):array(e,name)


def test_invalid_return_keeps_raw_fields_before_original_contract_stop(tmp_path):
    rec=receipts.ProfileCheckRecorder(tmp_path/'audit',{});calls=[]
    def trial(delta):calls.append(1);out=returned(delta);out['rolled_back']=False;return out
    with pytest.raises(AdapterStop,match='unverified_reprofile_rolled_back'):
        reprofile_check(algebra(),trial,[np.ones(1)],rank=1,recorder=rec)
    es=events(rec.folder);side=next(e for e in es if e['event']=='side_returned')
    assert len(calls)==1 and np.array_equal(array(side,'q_raw'),[1e-6,0.])
    assert es[-1]['data']['message']=='unverified_reprofile_rolled_back'


def test_minus_exception_preserves_plus_and_primary_failure(tmp_path):
    rec=receipts.ProfileCheckRecorder(tmp_path/'audit',{})
    def trial(delta):
        if delta[0]<0:raise ValueError('injected minus callback failure')
        return returned(delta)
    with pytest.raises(ValueError,match='injected minus'):
        reprofile_check(algebra(),trial,[np.ones(1)],rank=1,recorder=rec)
    es=events(rec.folder)
    assert len([e for e in es if e['event']=='side_returned'])==1
    assert not any(e['event']=='comparison' for e in es)
    assert es[-1]['data']['position']['side']=='minus'


def test_pass_uses_same_rows_h_order_and_callback_count(tmp_path):
    calls=[]
    def trial(delta):calls.append(delta.copy());return returned(delta)
    plain=reprofile_check(algebra(),trial,[np.ones(1)],rank=1);expected=list(calls);calls.clear()
    rec=receipts.ProfileCheckRecorder(tmp_path/'audit',{})
    recorded=reprofile_check(algebra(),trial,[np.ones(1)],rank=1,recorder=rec)
    assert recorded==plain and len(calls)==4
    assert all(np.array_equal(a,b) for a,b in zip(calls,expected))
    assert [r['h'] for r in recorded]==[1e-6,5e-7]
    assert events(rec.folder)[-1]['event']=='check_passed'


def test_logging_failure_stops_before_trial_and_does_not_mask_primary(tmp_path):
    calls=[]
    def broken(event,data,arrays):
        if event in ['prediction','check_failed']:raise OSError('injected full storage')
    with pytest.raises(OSError,match='injected full storage') as err:
        reprofile_check(algebra(),lambda d:calls.append(d),[np.ones(1)],rank=1,recorder=broken)
    assert calls==[] and 'receipt error' in err.value.profile_receipt_error
    def failure_only(event,data,arrays):
        if event=='check_failed':raise OSError('secondary logging failure')
    with pytest.raises(AdapterStop,match='actual_full_profile_derivative_mismatch') as err:
        reprofile_check(algebra(2.),returned,[np.ones(1)],rank=1,recorder=failure_only)
    assert 'secondary logging failure' in err.value.profile_receipt_error


def test_atomic_array_write_failure_never_commits_event_or_overwrites(tmp_path,monkeypatch):
    rec=receipts.ProfileCheckRecorder(tmp_path/'audit',{})
    def fail(*args,**kwargs):raise OSError('injected array write failure')
    monkeypatch.setattr(receipts.np,'save',fail)
    with pytest.raises(OSError,match='array write'):rec('side_returned',{}, {'q_raw':np.ones(2)})
    assert [e['event'] for e in events(rec.folder)]==['context']
    assert not list(rec.folder.glob('*.tmp'))
    with pytest.raises(FileExistsError):receipts.ProfileCheckRecorder(rec.folder,{})
    path=tmp_path/'receipt.json';receipts.atomic_json(path,{'value':1})
    with pytest.raises(FileExistsError):receipts.atomic_json(path,{'value':2})
    assert json.loads(path.read_text())['value']==1


def test_nonfinite_raw_array_is_saved_without_json_nan_or_admission(tmp_path):
    rec=receipts.ProfileCheckRecorder(tmp_path/'audit',{})
    def trial(delta):out=returned(delta);out['q']=np.array([np.nan,1.]);return out
    with pytest.raises(AdapterStop,match='invalid_actual_reprofile_fields'):
        reprofile_check(algebra(),trial,[np.ones(1)],rank=1,recorder=rec)
    side=next(e for e in events(rec.folder) if e['event']=='side_returned')
    assert np.isnan(array(side,'q_raw')[0]) and side['arrays']['q_raw']['finite'] is False


class IndexStub:
    def detach(self):return self
    def cpu(self):return self
    def numpy(self):return np.array([0,1],dtype=np.int64)


def test_runtime_requires_pre_stop_audit_without_real_objects(tmp_path):
    rt=Runtime.__new__(Runtime);rt.folder=tmp_path/'point';rt.folder.mkdir()
    rt.space={'report':{}};rt.root_rank=1;rt.bridge=SimpleNamespace(slices={'fake':slice(0,1)})
    rt.field=SimpleNamespace(net=BookkeepingState());rt.bridge.head=torch.ones((2,2),dtype=torch.float64)
    rt.problem=SimpleNamespace(fu=IndexStub());rt.point_q=np.zeros(2);rt.profile_verified=False
    rt.guard=Guard({'unused':1},10.);rt.trial=returned
    with pytest.raises(AdapterStop,match='profile_actual_full_profile_derivative_mismatch'):
        rt.verify_profile(algebra(2.),[np.ones(1)])
    assert rt.guard.stopped and not rt.profile_verified
    es=events(rt.folder/'actual_full_profile_audit')
    source=next(e for e in es if e['event']=='source_order')
    assert np.array_equal(array(source,'free_dofs'),[0,1])
    assert any(e['event']=='comparison' for e in es)


class BookkeepingState:
    def __init__(self):self.value=torch.tensor([.5],dtype=torch.float64)
    def state_dict(self):return {'fake':self.value}
    def parameters(self):return [self.value]
    def load_state_dict(self,state):self.value=state['fake'].clone()


def rollback_fixture(tmp_path):
    rt=Runtime.__new__(Runtime);rt.folder=tmp_path;rt.number=0;rt.field=SimpleNamespace(net=BookkeepingState())
    rt.guard=Guard({'unused':1},10.)
    rt.h=SimpleNamespace(snapshot=lambda net:{n:v.clone() for n,v in net.state_dict().items()},
        dump=lambda path,data:path.write_text(json.dumps(data)))
    def fail(delta):rt.field.net.value.add_(1.);raise ValueError('injected before-head failure')
    rt.bridge=SimpleNamespace(zero=torch.zeros(1,dtype=torch.float64),parameter_state=fail,verify_frozen=lambda:None)
    return rt


def test_callback_exception_still_records_verified_rollback_and_source_identity(tmp_path):
    rt=rollback_fixture(tmp_path)
    with pytest.raises(ValueError,match='injected before-head'):rt.trial(np.zeros(1))
    row=json.loads((tmp_path/'trial_001/profile_rollback_audit.json').read_text())
    assert row['rolled_back'] and row['source_network_unchanged'] and row['frozen_state']
    assert len(row['source_before_identity'])==64 and row['primary_error']['message']=='injected before-head failure'
    assert row['rollback_error'] is None and float(rt.field.net.value[0])==.5


def test_rollback_record_io_failure_preserves_original_exception(tmp_path,monkeypatch):
    rt=rollback_fixture(tmp_path)
    def fail(*args,**kwargs):raise OSError('injected rollback audit write failure')
    monkeypatch.setattr(runtime_module,'atomic_json',fail)
    with pytest.raises(ValueError,match='injected before-head') as err:rt.trial(np.zeros(1))
    assert 'rollback audit write failure' in err.value.profile_receipt_error
    assert float(rt.field.net.value[0])==.5


def test_runtime_callback_exception_links_partial_trial_and_rollback_proof(tmp_path):
    rt=Runtime.__new__(Runtime);rt.folder=tmp_path/'point';rt.folder.mkdir()
    rt.space={'report':{}};rt.root_rank=1;rt.bridge=SimpleNamespace(slices={})
    rt.field=SimpleNamespace(net=BookkeepingState());rt.bridge.head=torch.ones((2,2),dtype=torch.float64)
    rt.problem=SimpleNamespace(fu=IndexStub());rt.point_q=np.zeros(2);rt.profile_verified=False;rt.number=0
    rt.guard=Guard({'unused':1},10.)
    def fail(delta):
        rt.number+=1;p=rt.folder/'trial_001';p.mkdir()
        (p/'profile_rollback_audit.json').write_text('{"rolled_back":true}')
        raise ValueError('injected callback failure with saved rollback')
    rt.trial=fail
    with pytest.raises(AdapterStop,match='profile_injected callback failure'):
        rt.verify_profile(algebra(),[np.ones(1)])
    row=json.loads((rt.folder/'actual_full_profile_failure.json').read_text())
    assert row['latest_trial_number']==1 and not row['profile_verified']
    ref=row['latest_trial_files']['profile_rollback_audit.json']
    assert ref['available'] and hashlib.sha256(Path(ref['path']).read_bytes()).hexdigest()==ref['sha256']


def test_legacy_failure_dump_io_does_not_overwrite_callback_exception(tmp_path):
    rt=rollback_fixture(tmp_path)
    def fail(*args,**kwargs):raise OSError('injected legacy failure log error')
    rt.h.dump=fail
    with pytest.raises(ValueError,match='injected before-head') as err:rt.trial(np.zeros(1))
    row=json.loads((tmp_path/'trial_001/profile_rollback_audit.json').read_text())
    assert row['rolled_back'] and 'legacy failure log' in err.value.profile_receipt_error


def test_actual_writer_temp_snapshot_commit_then_sampler_stat(tmp_path,monkeypatch):
    import control
    rec=receipts.ProfileCheckRecorder(tmp_path/'audit',{})
    real_link=receipts.os.link;snapshots=[];present=[]
    def link(src,dst):
        # Capture actual walker names while the writer's own temp still exists.
        snapshot=list(control.os.walk(rec.folder));snapshots.append(snapshot)
        present.append(control.bytes_under(rec.folder))
        return real_link(src,dst)
    monkeypatch.setattr(receipts.os,'link',link)
    rec('side_returned',{},dict(q_raw=np.arange(3.)))
    real_walk=control.os.walk
    assert any('.profile_audit_npy.' in n for walk in snapshots for _,_,files in walk for n in files)
    assert any(n.endswith('.tmp') and '.json.' in n for walk in snapshots for _,_,files in walk for n in files)
    for snapshot in snapshots:
        # All writes have now committed and unlinked: deterministic old race.
        monkeypatch.setattr(control.os,'walk',lambda *args,_snapshot=snapshot,**kwargs:iter(_snapshot))
        assert control.bytes_under(rec.folder)>0
    monkeypatch.setattr(control.os,'walk',real_walk)
    assert present and not list(rec.folder.glob('*.tmp'))


def test_exact_array_temp_policy_counts_existing_and_rejects_other_errors(tmp_path,monkeypatch):
    import control
    temp=tmp_path/'.profile_audit_npy.123.tmp';temp.write_bytes(b'12345')
    assert control.bytes_under(tmp_path)==5
    temp.unlink()
    for name in ['payload.npy','.profile_audit_npy.x.tmp','field.npy.123.tmp','.profile_audit_npy.123.tmp.extra']:
        monkeypatch.setattr(control.os,'walk',lambda *args,_name=name,**kwargs:iter([(str(tmp_path),[],[_name])]))
        with pytest.raises(FileNotFoundError):control.bytes_under(tmp_path)
    temp.write_bytes(b'x');real_stat=Path.stat
    def denied(path,*args,**kwargs):
        if path==temp:raise PermissionError('injected array temp stat denial')
        return real_stat(path,*args,**kwargs)
    monkeypatch.setattr(control.os,'walk',lambda *args,**kwargs:iter([(str(tmp_path),[],[temp.name])]))
    monkeypatch.setattr(Path,'stat',denied)
    with pytest.raises(PermissionError):control.bytes_under(tmp_path)
    monkeypatch.setattr(Path,'stat',real_stat);temp.unlink();temp.symlink_to(tmp_path/'absent')
    with pytest.raises(RuntimeError,match='symlink'):control.bytes_under(tmp_path)
