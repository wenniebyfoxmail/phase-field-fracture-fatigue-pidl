"""ARTIFICIAL CONTROL FLOW only. Injected helpers are NOT numerical solvers."""
import json
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from profiled_hidden_adapter import AdapterStop
from profiled_hidden_e011_runtime import Runtime,BudgetProxy,WorkProxy,startup_checks,verify_source_assets,binding
from test_profiled_hidden_adapter import mock_bridge,guard


class FakeBudget:
    def __init__(self,folder):self.folder=folder;self.trace=[]
    def begin(self,role,**kw):
        row=dict(role=role);self.trace.append(row);return row


class FakeWork:
    def __init__(self):self.assemblies=0;self.solves=0;self.products=0
    def check(self):pass
    def product(self,role):self.products+=1


class FakeHelpers:
    """Receipts/control-flow simulation; no physical field solve."""
    def __init__(self,b,mode='ok'):self.b=b;self.mode=mode;self.head_calls=0;self.readout_calls=0
    def snapshot(self,net):return {n:v.detach().clone() for n,v in net.state_dict().items()}
    def dump(self,path,data):path.write_text(json.dumps(data,allow_nan=False)+'\n')
    def build_full_space(self,field,p,work):
        r=2 if self.mode=='rank' else 1
        return dict(transform=np.ones((3,r)),phi=torch.zeros(4,r,dtype=torch.float64))
    def persist_space(self,space,path,field):path.mkdir();space['persisted']=True
    def correct_full_head(self,field,p,space,work,budget,path,stage):
        self.head_calls+=1;path.mkdir()
        if self.mode=='throw':raise RuntimeError('injected_head_failure')
        with torch.no_grad():field.net.output_layer.weight[:2].add_(.0001)
        with torch.no_grad():u,v,_=field.fieldCalculation(p.x)
        return dict(hard_failure=False,solver=dict(stop='done')),None,(u,v)
    def persisted_readout(self,field,p,identity,budget,label,space):
        budget.begin(label);self.readout_calls+=1
        with torch.no_grad():u,v,d=field.fieldCalculation(p.x)
        fields={k:a.detach().numpy().copy() for k,a in [('u',u),('v',v),('d',d)]}
        obs=dict(E_el=.5,free_u_l2=.2,reduced_gradient_inf=1e-12 if self.mode!='badhead' else 1.1e-10)
        readouts=budget.folder/'readouts';readouts.mkdir(exist_ok=True)
        np.savez(readouts/(label+'.npz'),**fields)
        return obs,fields,np.array([1e-12,1e-12])
    def linear_realization_error(self,fields,linear):return 0.


def runtime_fixture(tmp_path,mode='ok'):
    b=mock_bridge();g=guard(head_assembly=100,explicit_head_products=100)
    helper=FakeHelpers(b,mode);budget=FakeBudget(tmp_path);work=FakeWork()
    rt=Runtime(b.field,b.problem,b.space,budget,work,tmp_path/'adapter',g,helpers=helper)
    rt.bridge.startup();return rt,helper


def test_real_adapter_control_flow_stops_before_chart_without_source_admission(tmp_path):
    rt,h=runtime_fixture(tmp_path)
    with pytest.raises(AdapterStop,match='missing_triple_source_admission'):rt.form_chart()
    assert h.head_calls==0 and rt.guard.stopped


def test_trial_mutation_is_restored_and_receipt_proves_rollback(tmp_path):
    rt,h=runtime_fixture(tmp_path);before=h.snapshot(rt.field.net)
    out=rt.trial(np.ones_like(rt.bridge.zero.numpy())*.001)
    assert out['rolled_back'] and out['actual_nn'] and out['persisted_actual_phi']
    assert all(torch.equal(v,before[n]) for n,v in rt.field.net.state_dict().items())
    assert any(not torch.equal(v,before[n]) for n,v in out['candidate_state'].items())
    assert (tmp_path/'adapter/trial_001/rollback.json').exists()
    assert h.head_calls==1 and h.readout_calls==1
    rt.root_E=1.;rt.root_Ru=1.
    rt.source_admitted=True;rt.profile_verified=True
    accepted_space=rt.promote(out)
    assert accepted_space is out['candidate_space']
    assert all(torch.equal(v,out['candidate_state'][n]) for n,v in rt.field.net.state_dict().items())


@pytest.mark.parametrize('mode,reason',[('rank','rank_changed'),('throw','injected_head_failure')])
def test_trial_exception_or_rank_change_restores_and_latches(tmp_path,mode,reason):
    rt,h=runtime_fixture(tmp_path,mode);before=h.snapshot(rt.field.net)
    with pytest.raises((AdapterStop,RuntimeError),match=reason):rt.trial(np.ones_like(rt.bridge.zero.numpy())*.001)
    assert all(torch.equal(v,before[n]) for n,v in rt.field.net.state_dict().items())
    assert rt.guard.stopped and (tmp_path/'adapter/trial_001/adapter_failure.json').exists()
    assert h.head_calls==(0 if mode=='rank' else 1)


def test_triple_source_readout_no_rebuild_and_source_unchanged(tmp_path):
    rt,h=runtime_fixture(tmp_path)
    with torch.no_grad():u,v,d=rt.field.fieldCalculation(rt.problem.x)
    rows=startup_checks(rt,{k:a.numpy().copy() for k,a in [('u',u),('v',v),('d',d)]},source_energy=.5)
    assert len(rows)==3 and rt.source_admitted and h.head_calls==0 and h.readout_calls==3
    rt.bridge.verify_frozen()


def test_source_head_miss_stops_first_readout(tmp_path):
    rt,h=runtime_fixture(tmp_path,'badhead')
    with torch.no_grad():u,v,d=rt.field.fieldCalculation(rt.problem.x)
    with pytest.raises(AdapterStop,match='source_triple'):
        startup_checks(rt,{k:a.numpy().copy() for k,a in [('u',u),('v',v),('d',d)]},source_energy=.5)
    assert h.readout_calls==1 and not rt.source_admitted


def test_proxies_count_legacy_head_operations_and_first_stop(tmp_path):
    g=guard(head_assembly=1,explicit_head_products=2);w=WorkProxy(FakeWork(),g);b=BudgetProxy(FakeBudget(tmp_path),g)
    w.assemblies+=1;w.solves+=1;w.product('test');b.begin('test')
    assert g.counts['head_factor']==1 and g.counts['head_triangular_solve']==2 and g.counts['energy_force_field']==1
    with pytest.raises(AdapterStop,match='work_limit_head_assembly'):w.assemblies+=1


def test_promotion_without_profile_check_is_first_stop(tmp_path):
    rt,h=runtime_fixture(tmp_path);out=rt.trial(np.zeros_like(rt.bridge.zero.numpy()))
    with pytest.raises(AdapterStop,match='promotion_missing_source'):rt.promote(out)
    assert rt.guard.stopped


def test_candidate_identity_changed_cannot_be_promoted(tmp_path):
    rt,h=runtime_fixture(tmp_path);out=rt.trial(np.zeros_like(rt.bridge.zero.numpy()))
    rt.root_E=1.;rt.root_Ru=1.;rt.source_admitted=True;rt.profile_verified=True
    before=h.snapshot(rt.field.net)
    out['candidate_state']['output_layer.weight'][0,0]+=.1
    with pytest.raises(AdapterStop,match='identity_changed'):rt.promote(out)
    assert rt.guard.stopped and all(torch.equal(v,before[n]) for n,v in rt.field.net.state_dict().items())


def test_source_hash_binding_checks_artificial_bytes_only(tmp_path):
    f=tmp_path/'artificial.txt';f.write_text('fake asset')
    expected=binding(f);g=guard()
    card=dict(input_bindings=[dict(role='fake',bytes=expected['bytes'],sha256=expected['sha256'])])
    assert len(verify_source_assets(card,{'fake':f},g))==1
    f.write_text('changed')
    with pytest.raises(AdapterStop,match='source_asset_mismatch'):verify_source_assets(card,{'fake':f},g)


def test_artificial_profiled_policy_runs_one_closed_step_and_records_gradients(tmp_path):
    from profiled_hidden_e011_runtime import candidate_direction,one_macrostep
    from profiled_hidden_adapter import reprofile_check
    from test_profiled_hidden_adapter import moving_adapter,actual_profile,receipt
    c,a,g=moving_adapter();records={}
    direction,info=candidate_direction(a,c.array(c.force),np.ones(2),.001,
        recorder=lambda name,**arrays:records.update({name:arrays}))
    ge,gr=a.gradients(c.array(c.force))
    assert ge@direction<0 and gr@direction<0 and np.linalg.norm(a.q(direction))<=.001
    assert 'profile_gradients' in records and 'profile_direction' in records
    class SyntheticRuntime:
        def __init__(self):
            self.chart=c;self.guard=g;self.head_H=np.array([[2+.4**2]]);self.folder=tmp_path
            self.root_E=float(c.point.value.detach());self.root_Ru=float(torch.linalg.vector_norm(c.force));self.n=0
            self.h=SimpleNamespace(dump=lambda p,v:p.write_text(json.dumps(v)+'\n'));self.closed=False;self.promoted=False
        def form_chart(self):return a
        def trial(self,d):
            self.n+=1;folder=tmp_path/str(self.n);folder.mkdir()
            q=actual_profile(.4+d[0]);K=np.diag([2.,1.])
            return {**receipt(q), 'E':float(.5*q@K@q),'Ru':float(np.linalg.norm(K@q)),
                'fixed_state':True,'finite':True,'folder':str(folder)}
        def verify_profile(self,alg,dirs):return reprofile_check(alg,self.trial,dirs,rank=1)
        def promote(self,accepted):self.promoted=True;return 'synthetic-space'
        def close(self):self.closed=True;self.chart.point.close()
    runtime=SyntheticRuntime()
    result=one_macrostep(runtime,None,np.ones(2),.001)
    assert result['status']=='accepted' and runtime.promoted and runtime.closed
    assert result['candidate']['E']<runtime.root_E and result['candidate']['Ru']<runtime.root_Ru


def test_profile_failure_blocks_policy_and_closes_graph(tmp_path):
    from profiled_hidden_e011_runtime import one_macrostep
    from test_profiled_hidden_adapter import moving_adapter
    c,a,g=moving_adapter()
    class SyntheticFailure:
        def __init__(self):
            self.chart=c;self.guard=g;self.head_H=np.array([[2+.4**2]]);self.folder=tmp_path;self.closed=False
            self.h=SimpleNamespace(dump=lambda p,v:None)
        def form_chart(self):return a
        def verify_profile(self,alg,dirs):raise AdapterStop('injected_actual_profile_failure')
        def close(self):self.closed=True;self.chart.point.close()
    runtime=SyntheticFailure()
    with pytest.raises(AdapterStop,match='injected_actual'):one_macrostep(runtime,None,np.ones(2),.001)
    assert runtime.closed and g.stopped
