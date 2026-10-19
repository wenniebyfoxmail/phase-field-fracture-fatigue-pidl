"""D013 synthetic-only checks. Never load a real endpoint or train a network."""
import copy
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'SENS_tensile'))
from s04_e024_field_budget import (Metrics, Quadratics, GUARDS, PROFILES, InvalidEvidence,
    ResourceStop, ratio_norm, solve_proxy, run_profile, safe_json, quantize_head)
from s04_e024_field_physics import FieldAdapter
from s04_e024_field_runtime import PhaseLedger,supervise,write_json,validate_approval,persist_event
from summarize_s04_e024_field_budget import replay_profile


class ScalarAdapter:
    """Known affine fields, artificial one-coordinate feature, no model/FEM data."""
    def __init__(self,dtype=np.float64,centre=1.):
        self.theta=np.array([[centre,0]],dtype=dtype);self.centre=centre;self.calls=0
        self.origin=self.realize(self.theta)
        reference=self.fields(1.)
        self.metrics=Metrics(self.origin,reference,{r:np.ones(1) for r in ('full','damage','background','inside_background')},
                            {r:np.ones((1,1)) for r in ('full','damage','background','inside_background')})
    def fields(self,u):return dict(uv=np.array([[u,0.]]),strain=np.array([[[u,0.,0.]]]),driver=np.array([[u]]),force=np.array([10.-u]))
    def realize(self,head):self.calls+=1;return self.fields(float(head[0,0])-self.centre)
    def check_identity(self):pass
    def check_realization(self,head,f,metrics):return {'synthetic_only':True}
    def physical_report(self,f):return self.metrics.report(f)
    def proxy(self,f,metrics,check=lambda:None):
        pack=Quadratics.empty(2);u=f['uv'][0,0];x=np.array([1.,0.]);h=np.outer(x,x)
        for i in range(13):
            residual=(10-u) if i==4 else (u-1.)
            j=-x if i==4 else x
            pack.c[i]=residual**2;pack.b[i]=residual*j;pack.h[i]=h
        for i in range(13,17):
            pack.c[i]=u*u;pack.b[i]=u*x;pack.h[i]=h
        return pack


def fixed_direction(value):
    def solver(pack,metrics,eta,strict,check):
        return np.array([value,0.]),dict(feasible=True,success=False,scope='artificial witness, not optimizer')
    return solver


def save_profile(tmp,adapter,eta=.1,strict=True,solver=solve_proxy):
    tmp.mkdir();events=[]
    def emit(e):events.append(persist_event(tmp,e))
    head,f,counts=run_profile(adapter,adapter.metrics,eta,strict,lambda:None,emit,solver)
    (tmp/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    np.savez_compressed(tmp/'final.npz',head=head,original_head=adapter.theta,**f)
    write_json(tmp/'final.json',dict(eta=eta,strict=strict,counts=counts,report=adapter.physical_report(f),centre_digest=adapter.metrics.centre_digest))
    return head,f,counts,events


def test_all13_actual_guards_strict_and_diagnostic_separation():
    a=ScalarAdapter();ev=a.metrics.evaluate(a.origin)
    assert len(ev['guards'])==13
    for i,k in enumerate(GUARDS):
        bad=copy.deepcopy(ev);bad['guards'][k]+=1.
        assert k in a.metrics.violations(bad,.3,True)
        assert (k in a.metrics.violations(bad,.3,False))==(i<7)


def test_zero_scales_are_exact_no_epsilon_and_vector_force_change():
    assert ratio_norm(0.,0.)==0 and np.isinf(ratio_norm(1e-100,0.))
    a=ScalarAdapter();f=copy.deepcopy(a.origin)
    # Force rotation preserves its norm; budget uses the vector difference.
    orig={**a.origin,'force':np.array([10.,0.])};ref=a.metrics.reference
    m=Metrics(orig,ref,a.metrics.node_weights,a.metrics.gp_weights)
    f['force']=np.array([0.,10.]);ev=m.evaluate(f)
    assert ev['guards']['weak_squared']==m.ceilings[4]
    assert ev['budget_components']['force_change']==pytest.approx(np.sqrt(2))
    assert 'physical_budget' in m.violations(ev,1.,True)
    with pytest.raises(InvalidEvidence):ratio_norm(-1.,0.)


def test_exact_UV_origin_bypasses_any_optimizer_or_new_forward():
    a=ScalarAdapter();m=Metrics(a.origin,a.origin,a.metrics.node_weights,a.metrics.gp_weights)
    calls=a.calls
    def forbidden(*args):pytest.fail('unexpected solve')
    h,f,c=run_profile(a,m,.3,True,lambda:None,lambda e:None,forbidden)
    assert c['stop']=='NO_CORRECTION_ALREADY_EXACT' and c['solves']==0 and a.calls==calls
    np.testing.assert_array_equal(h,a.theta)


def test_cumulative_budget_never_moves_and_no_two_percent_cap(tmp_path):
    a=ScalarAdapter();head,f,c,events=save_profile(tmp_path/'p',a,solver=fixed_direction(.08))
    # First .08 step is >2% of the original head, yet passes the physical radius.
    assert events[1]['accepted'] and events[1]['relative_head_change']>.02
    assert f['uv'][0,0]<=.1 and a.metrics.evaluate(f)['budget_q']<=.1
    assert any('physical_budget' in e.get('failures',[]) for e in events)
    # Every rejected outer candidate is still measured from u0=0, never its incumbent.
    assert any(e.get('actual',{}).get('budget_q',0)>.1 for e in events)


def test_genuine_solver_profile_passes_independent_no_optimizer_replay(tmp_path):
    a=ScalarAdapter();head,f,c,events=save_profile(tmp_path/'p',a)
    replay=replay_profile(ScalarAdapter(),tmp_path/'p',.1,True)
    assert replay['trials']==c['trials'] and replay['accepted_steps']==c['accepted_steps']


def test_raw_actual_strain_can_reject_an_affine_good_head():
    class BadRaw(ScalarAdapter):
        def realize(self,head):
            f=super().realize(head)
            if float(head[0,0])!=self.centre:f['strain'][:]=100.
            return f
    a=BadRaw();events=[]
    h,f,c=run_profile(a,a.metrics,.1,True,lambda:None,events.append,fixed_direction(.08))
    assert c['accepted_steps']==0 and c['trials']==9 and c['stop']=='ALL_NINE_REJECTED'
    assert all('strain_background' in e['failures'] for e in events if e['kind']=='trial')
    np.testing.assert_array_equal(h,a.theta)


def test_dtype_quantization_controls_prediction_and_actual_acceptance():
    a=ScalarAdapter(np.float32,1e8);events=[]
    h,f,c=run_profile(a,a.metrics,.3,True,lambda:None,events.append,fixed_direction(.1))
    assert c['accepted_steps']==0
    assert all(e['predicted_reduction']==0. for e in events if e['kind']=='trial')
    assert h.dtype==np.float32
    with pytest.raises(InvalidEvidence):quantize_head([np.inf],np.float32)


@pytest.mark.parametrize('tamper',['centre','guard','accepted','order','head','counts','model'])
def test_replay_rejects_coherent_looking_trajectory_tampering(tmp_path,tamper):
    a=ScalarAdapter();folder=tmp_path/'p';_,_,_,events=save_profile(folder,a)
    if tamper in ('centre','counts'):
        f=json.loads((folder/'final.json').read_text())
        if tamper=='centre':f['centre_digest']['uv']='0'*64
        else:f['counts']['solves']+=1
        write_json(folder/'final.json',f)
    else:
        e=next(e for e in events if e['kind']=='trial')
        if tamper=='guard':e['actual']['guards']['strain_full']*=.9
        if tamper=='accepted':e['accepted']=not e['accepted']
        if tamper=='order':e['k']+=1
        if tamper=='head':e['head'][0][0]+=.01
        if tamper=='model':events[0]['model_sha256']['h']='0'*64
        (folder/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in events))
    with pytest.raises((InvalidEvidence,AssertionError)):replay_profile(ScalarAdapter(),folder,.1,True)


def test_resource_stop_propagates_without_next_trial_or_solver():
    a=ScalarAdapter();before=a.calls;calls=[]
    def check():calls.append(1);raise ResourceStop('test deadline')
    with pytest.raises(ResourceStop):run_profile(a,a.metrics,.3,True,check,lambda e:None,fixed_direction(.1))
    assert a.calls==before and len(calls)==1
    ledger=PhaseLedger(10.);ledger.charge('numeric',1800.)
    with pytest.raises(ResourceStop):ledger.remaining('numeric')
    with pytest.raises(ResourceStop):ledger.remaining('replay')
    fresh=PhaseLedger();assert fresh.remaining('replay')==900.
    with pytest.raises(ResourceStop):fresh.charge('replay',901.)


def test_parent_watchdog_interrupts_only_owned_blocking_child(tmp_path):
    start=time.monotonic()
    with pytest.raises(ResourceStop):supervise([sys.executable,'-c','import time; time.sleep(5)'],Path.cwd(),tmp_path,tmp_path/'log',.15)
    r=json.loads((tmp_path/'log/exit.json').read_text())
    assert time.monotonic()-start<3 and r['exit_code'] is not None and 'deadline' in r['stop']


def test_scientific_cli_off_and_approval_missing_before_any_loader(monkeypatch):
    import run_s04_e024_field_budget as runner
    monkeypatch.setattr(sys,'argv',['runner'])
    with pytest.raises(SystemExit) as e:runner.main()
    assert e.value.code==2
    with pytest.raises((InvalidEvidence,FileNotFoundError)):validate_approval(Path('/not-an-approved-receipt'), 'x')


def native_fixture():
    xy=np.array([[x,y] for y in np.linspace(-.5,.5,4) for x in np.linspace(-.5,.5,4)])
    conn=np.array([[4*j+i,4*j+i+1,4*j+i+5,4*j+i+4] for j in range(3) for i in range(3)])
    damage=np.zeros(16);damage[[2,3,10,15]]=[.8,.7,.6,.9];damage[5]=.05
    phi=np.zeros((16,3));phi[5]=np.array([.3,-.2,1.])*[.7,2.,.4] # non-unit fixed D
    theta=np.array([[.001,-.002],[.002,.001],[.001,.003]])
    base=np.stack([.01*xy[:,0]**2,.02*xy[:,1]],axis=1)
    raw=lambda h:base+phi@h
    target=raw(theta+np.array([[.004,.001],[-.001,.002],[.003,.001]]));target[2,0]+=.002
    data=dict(xy=xy,conn=conn,damage=damage,mass=np.ones(16),equilibrated_uv=target,energy_scale=1.)
    signs=np.array([[-1,-1],[1,-1],[1,1],[-1,1]]);a=1/np.sqrt(3)
    shape=np.array([(1+signs[:,0]*x)*(1+signs[:,1]*y)/4 for x,y in [(a,a),(-a,a),(a,-a),(-a,-a)]])
    gd=np.einsum('en,gn->eg',damage[conn],shape);gxy=np.einsum('enb,gn->egb',xy[conn],shape)
    window=np.zeros(16);window[5]=1.
    return FieldAdapter(data,base,theta,phi,raw,window,np.array([-.2,-.2]),np.array([.2,.2]),1.,gd,gxy)


def test_chunked13_plus4_native_grams_match_every_direct_column_and_Jacobian():
    from s04_e024_head_cone import elastic_driver
    a=native_fixture();m=a.metrics;f=a.origin;pack=a.proxy(f,m)
    n=a.theta.size;velocity=[]
    for j in range(n):
        v=np.zeros_like(f['uv']);v[:,j%2]=a.phi[:,j//2];velocity.append(v)
    _,stress=elastic_driver(a.mech,f['uv'],a.gp_damage)
    je=np.stack([a.mech.strains(v) for v in velocity])
    jf=np.stack([(a.force_scale*a.mech.dual(a.mech.force(v,tangent=True))).ravel() for v in velocity])
    jp=np.einsum('ega,iega->ieg',stress,je)
    p=np.linspace(-1e-4,2e-4,n)
    predicted=dict(uv=f['uv']+np.einsum('i,inj->nj',p,velocity),
        strain=f['strain']+np.einsum('i,iega->ega',p,je),
        driver=f['driver']+np.einsum('i,ieg->eg',p,jp),force=f['force']+np.einsum('i,ij->j',p,jf))
    ev=m.evaluate(predicted);expected=np.r_[list(ev['guards'].values()),ev['changes_sq']]
    np.testing.assert_allclose(pack.values(p),expected,rtol=2e-10,atol=1e-20)
    for i in range(n):
        e=np.eye(n)[i]*1e-6
        fd=(pack.values(p+e)-pack.values(p-e))/2e-6
        np.testing.assert_allclose(pack.jacobian(p)[:,i],fd,rtol=1e-6,atol=1e-10)
    # Force constant includes all original free rows, not just tangent support.
    assert pack.c[4]==pytest.approx(np.sum(f['force']**2),rel=1e-14)
    a.check_realization(a.theta,a.origin,m);a.final_identity()


def test_full568_known_solution_near_null_and_degenerate_coordinates():
    n=568;pack=Quadratics.empty(n);h=np.eye(n);h[-1,-1]=0.;h[-2,-2]=1e-16
    pack.c[:13]=1.;pack.b[:13,0]=-1.;pack.h[:13]=h;pack.h[13:]=h
    metrics=SimpleNamespace(ceilings=np.ones(13),scales_sq=np.ones(4))
    start=time.monotonic();p,info=solve_proxy(pack,metrics,.3,True)
    assert info['feasible'] and info['preconditioner']['all_coordinates_retained']==568
    assert p[0]==pytest.approx(.3,abs=2e-6)
    np.testing.assert_allclose(p[1:],0,atol=1e-8)

    from s04_e024_field_runtime import peak_rss
    wall=time.monotonic()-start
    print('SYNTHETIC568_WALL_SECONDS',wall,'ITERATIONS',info['iterations'],'WALL_PER_ITER_INCLUDING_SETUP',wall/max(1,info['iterations']),'PEAK_RSS_BYTES',peak_rss())
    assert info['preconditioner']['rank_rtol_1e12']==566


def test_pure_algebra_nonfinite_and_empty_regions_stop():
    a=ScalarAdapter();bad=copy.deepcopy(a.origin);bad['uv'][0,0]=np.nan
    with pytest.raises(InvalidEvidence):a.metrics.evaluate(bad)
    weights=dict(a.metrics.node_weights);weights['damage']=np.zeros(1)
    with pytest.raises(InvalidEvidence):Metrics(a.origin,a.metrics.reference,weights,a.metrics.gp_weights)


def test_indefinite_proxy_stops_before_solver():
    a=ScalarAdapter();p=a.proxy(a.origin,a.metrics);p.h[8,1,1]=-1.
    with pytest.raises(InvalidEvidence,match='nonconvex'):solve_proxy(p,a.metrics,.3,True)


def test_zero_error_guard_no_fuzzy_physical_admission():
    a=ScalarAdapter();origin=copy.deepcopy(a.origin);reference=copy.deepcopy(a.metrics.reference)
    reference['driver']=origin['driver'].copy()
    m=Metrics(origin,reference,a.metrics.node_weights,a.metrics.gp_weights)
    f=copy.deepcopy(origin);f['driver']+=1e-12
    ev=m.evaluate(f)
    assert 'driver_background' in m.violations(ev,.3,True)
    assert np.isinf(ev['budget_components']['driver_change'])


def test_all12_synthetic_profiles_replayed_aggregated_and_rendered(tmp_path):
    from summarize_s04_e024_field_budget import replay_state,aggregate,render
    from s04_e024_field_budget import STATES
    from s04_e024_field_runtime import sha
    for state in STATES:
        adapter=native_fixture();adapter.assets={'synthetic_only':True,'state':state};adapter.d012_head=adapter.theta.copy()
        case=tmp_path/'states'/state;case.mkdir(parents=True)
        np.savez_compressed(case/'origin.npz',**adapter.origin)
        np.savez_compressed(case/'geometry.npz',xy=adapter.data['xy'],conn=adapter.data['conn'],damage=adapter.data['damage'],reference_uv=adapter.data['equilibrated_uv'],window=adapter.window,us=adapter.us)
        profiles={}
        for name,eta,strict in PROFILES:
            _,_,counts,_=save_profile(case/name,adapter,eta,strict);profiles[name]=counts
        meta=dict(state=state,source_commit='fixture',assets=adapter.assets,profiles=profiles,
            D012_report=adapter.physical_report(adapter.realize(adapter.d012_head)),
            NN_optimizer_steps=0,original_checkpoint_writes=0,history_fatigue_damage_updates=0,remote_actions=0,
            offline_solver_calls=sum(x['solves'] for x in profiles.values()),actual_candidate_trials=sum(x['trials'] for x in profiles.values()),
            files={str(p.relative_to(case)):sha(p) for p in case.rglob('*') if p.is_file()})
        write_json(case/'receipt.json',meta)
        fresh=native_fixture();fresh.assets=adapter.assets;fresh.d012_head=adapter.theta.copy()
        record=replay_state(fresh,tmp_path,state,lambda:None,expected_commit='fixture')
        record['source_commit']='fixture';write_json(tmp_path/'replay'/state/'verified.json',record)
    receipt=aggregate(tmp_path,'fixture')
    assert receipt['profiles']==12 and receipt['new_replay_optimizations']==0
    assert len((tmp_path/'summary/regions.csv').read_text().splitlines())==49
    render(tmp_path)
    assert len(list((tmp_path/'summary/figures').glob('*.png')))==5
    for png in (tmp_path/'summary/figures').glob('*.png'):
        note=png.with_suffix('.md').read_text()
        assert 'ARTIFICIAL UNIT FIXTURE ONLY' in note and 'How to read' in note and 'Limitations' in note
    # Missing coverage is never filled with a zero-gain row.
    (tmp_path/'replay/c83s4/verified.json').unlink()
    with pytest.raises(InvalidEvidence,match='INCOMPLETE'):aggregate(tmp_path,'fixture')


def test_approval_checks_exact_receipt_hash_scope_and_zero_training(tmp_path,monkeypatch):
    import s04_e024_field_runtime as rt
    from s04_e024_field_budget import CONTRACT_SHA
    monkeypatch.setattr(rt,'validate_source',lambda *args:None)
    monkeypatch.setattr(rt,'code_tree_sha',lambda *args:'synthetic_tree')
    code=tmp_path/'code.json';checks=tmp_path/'checks.json'
    write_json(code,dict(verdict='CODE_READY_PASS',code_tree_sha256='synthetic_tree'))
    write_json(checks,dict(verdict='NONTRAINING_CHECKS_PASS',code_tree_sha256='synthetic_tree',
        real_model_or_FEM_forward_count=0,NN_optimizer_steps=0,wall_seconds=10.))
    approval=dict(user_approved_final_execution=True,scope='E024-D013-physical-field-budget-12-profiles',
        execution_commit='synthetic_commit',contract_sha256=CONTRACT_SHA,
        code_ready=dict(path=str(code),sha256=rt.sha(code)),nontraining=dict(path=str(checks),sha256=rt.sha(checks)))
    path=tmp_path/'approval.json';write_json(path,approval)
    assert rt.validate_approval(path,'synthetic_commit')[1]==10.
    bad=json.loads(checks.read_text());bad['NN_optimizer_steps']=1;write_json(checks,bad)
    approval['nontraining']['sha256']=rt.sha(checks);write_json(path,approval)
    with pytest.raises(InvalidEvidence,match='scope'):rt.validate_approval(path,'synthetic_commit')
    approval['user_approved_final_execution']=False;write_json(path,approval)
    with pytest.raises(InvalidEvidence,match='user-approved'):rt.validate_approval(path,'synthetic_commit')


def test_storage_cap_blocks_spawn_instead_of_launching_and_then_stopping(tmp_path,monkeypatch):
    import s04_e024_field_runtime as rt
    (tmp_path/'owned.bin').write_bytes(b'X'*1000)
    monkeypatch.setattr(rt.subprocess,'Popen',lambda *a,**k:pytest.fail('must stop before spawn'))
    with pytest.raises(ResourceStop,match='pre-spawn'):rt.supervise([sys.executable,'-c','pass'],Path.cwd(),tmp_path,tmp_path/'log',10,storage_cap=100)


@pytest.mark.parametrize('dtype_name',['float32','float64'])
def test_exact_raw_helper_tiny_Torch_nonunit_D_BC_window_and_no_mutation(dtype_name):
    import torch
    from torch import nn
    from s04_e024_field_physics import raw_network_forward
    from s04_e018_global_local import compact_window
    dtype=getattr(torch,dtype_name)
    class Residual(nn.Module):
        def __init__(self):
            super().__init__();self.output_layer=nn.Linear(3,2,dtype=dtype)
        def encode(self,x):return torch.stack([x[:,0],x[:,1],x[:,0]*x[:,1]],1)
    class Tiny(nn.Module):
        def __init__(self):
            super().__init__();self.residual=Residual()
            for k,v in dict(local_center=[.02,.01],local_scale=[.4,.3],
                lower=[-.1,-.2],upper=[.1,.2],head_scale=[.2,1.3,2.,.7]).items():
                self.register_buffer(k,torch.tensor(v,dtype=dtype))
    model=Tiny();model.requires_grad_(False)
    before={k:v.clone() for k,v in model.state_dict().items()}
    xy=np.array([[0.,-.5],[0.,.5],[.4,0.],[0.,0.],[.05,.1]],dtype=dtype_name)
    base=np.arange(10,dtype=dtype_name).reshape(5,2)*.01
    head=np.arange(8,dtype=dtype_name).reshape(4,2)*.03
    actual=raw_network_forward(model,xy,base,head,chunk=2)
    x=torch.tensor(xy,dtype=dtype)
    with torch.no_grad():
        h=model.residual.encode((x-model.local_center)/model.local_scale)
        raw=(h*model.head_scale[:-1])@torch.tensor(head[:-1])+torch.tensor(head[-1])*model.head_scale[-1]
        expected=base+((((x[:,1]+.5)*(.5-x[:,1]))[:,None]*compact_window(x,model.lower,model.upper))*raw).numpy()
    np.testing.assert_allclose(actual,expected,rtol=1e-6 if dtype_name=='float32' else 1e-14,atol=1e-15)
    np.testing.assert_array_equal(actual[:3],base[:3])
    assert all(torch.equal(v,before[k]) for k,v in model.state_dict().items())
    assert all(p.grad is None and not p.requires_grad for p in model.parameters())
    with pytest.raises(InvalidEvidence,match='dtype/layout'):
        raw_network_forward(model,xy,base,head.astype('float64' if dtype_name=='float32' else 'float32'))


def test_full_transform_persisted_and_replay_rejects_tamper(tmp_path):
    folder=tmp_path/'p';_,_,_,events=save_profile(folder,ScalarAdapter())
    solver=events[0];path=folder/solver['info']['preconditioner_transform_file']['path']
    assert np.load(path,allow_pickle=False).shape==(2,2)
    path.write_bytes(path.read_bytes()+b'tampered')
    with pytest.raises(InvalidEvidence,match='transform file identity'):
        replay_profile(ScalarAdapter(),folder,.1,True)


def test_owned_child_CPU_visibility_and_provenance(tmp_path):
    record=supervise([sys.executable,'-c',"import os; assert os.environ['CUDA_VISIBLE_DEVICES']==''"],
        Path.cwd(),tmp_path,tmp_path/'log',10)
    assert record['exit_code']==0
    provenance=record['provenance']
    assert provenance['host'] and provenance['utc'] and provenance['versions']['numpy']
