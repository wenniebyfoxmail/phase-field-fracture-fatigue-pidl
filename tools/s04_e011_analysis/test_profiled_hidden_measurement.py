"""New bounded panel/control/resource fixtures; no real NN, source or solver."""
import time,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'s04_e011_execution'))
from profiled_hidden_measurement import PANEL,comparison,chart_components
from measure_launch import validate


def test_authorized_panel_exactly_seven_fresh_A_and_four_feature_reuse_B():
    assert len(PANEL)==7 and sum(row[2] for row in PANEL)==4
    assert [row[1] for row in PANEL]==[0.,1e-6,-1e-6,5e-7,-5e-7,1e-6,-1e-6]
    assert PANEL[-2][1]==PANEL[1][1] and PANEL[-1][1]==PANEL[2][1]


def test_derivative_mismatch_is_observation_not_authorization_to_optimize():
    row,fd,diff=comparison(np,np.array([2.,0.]),np.array([1e-6,0.]),np.array([-1e-6,0.]),1e-6)
    assert np.array_equal(fd,[1.,0.]) and np.array_equal(diff,[1.,0.])
    assert not row['original_gate_passed'] and row['error']==1. and row['scale']==2.
    assert row['tolerance']==1e-10+1e-4*2
    with pytest.raises(RuntimeError,match='nonfinite'):comparison(np,np.array([np.nan]),np.ones(1),np.zeros(1),1e-6)


def test_chart_uses_saved_Phi_anchor_fixed_T_and_original_boundary():
    t=lambda a:torch.tensor(a,dtype=torch.float64)
    f=t([[.1,.2],[.3,.4],[.5,.6]]);f0=f-.001
    b=SimpleNamespace(n=3,x=t([[0,-.5],[0,0],[0,.5]]),y0=t(-.5),yL=t(.5),load=t(.12),angle=t(np.pi/2),bubble=t([0,.25,0]),T=t([[1.,.2],[.3,1.],[.1,.2]]),head=t([[.1,.2,.3],[.4,.5,.6]]))
    b.raw0=b.load*b.bubble[:,None]*torch.cat((f0,torch.ones(3,1,dtype=torch.float64)),1)
    # Actual stored Phi intentionally differs from reconstructed D0T0.
    b.phi=b.raw0@b.T+t([[0,0],[1e-8,-2e-8],[0,0]])
    phi,u,v=chart_components(torch,b,f)
    D=b.load*b.bubble[:,None]*torch.cat((f,torch.ones(3,1,dtype=torch.float64)),1)
    assert torch.equal(phi,b.phi+(D-b.raw0)@b.T)
    assert not torch.equal(phi,D@b.T)
    assert u[0]==v[0]==0 and abs(float(u[-1]))<1e-16 and v[-1]==b.load
    zero,_,_=chart_components(torch,b,f0);assert torch.equal(zero,b.phi)


def fixture():
    G=1024**3
    card=dict(mode='measurement_only',execution_enabled=False,run_id='new_measurement',family='F',envelope_deadline_epoch=100.,measurement_seconds=600,envelope_seconds=1800,
        work_caps=dict(energy_force_field=500,head_assembly=50,svd=7),resource_limits_bytes=dict(host_RSS=16*G,GPU_allocated=16*G,GPU_reserved=16*G,fresh_root_outputs=8*G))
    auth=dict(approved_by='human_delegated_HQ',execute_one_measurement=True,package_sha256='sha',run_id='new_measurement',family='F',authority_ref='verified human and HQ scope')
    return card,auth


def test_exact_authority_caps_and_expiry_without_launch():
    card,auth=fixture();validate(card,auth,'sha',now=0.)
    with pytest.raises(RuntimeError,match='authority'):validate(card,{**auth,'run_id':'oldR2'},'sha',now=0.)
    with pytest.raises(RuntimeError,match='expired'):validate(card,auth,'sha',now=100.)
    card['work_caps']['svd']=8
    with pytest.raises(RuntimeError,match='work caps'):validate(card,auth,'sha',now=0.)


def test_resource_limit_change_is_not_silently_admitted():
    card,auth=fixture();card['resource_limits_bytes']['GPU_reserved']+=1
    with pytest.raises(RuntimeError,match='resource envelope'):validate(card,auth,'sha',now=0.)


def test_outer_pidfd_is_armed_before_controller_gate_without_real_process(tmp_path,monkeypatch):
    import json
    import measure_launch as module
    events=[];commands=[]
    monkeypatch.setattr(module.sys,'platform','linux')
    monkeypatch.setattr(module.os,'sched_getaffinity',lambda pid:set(range(8)),raising=False)
    monkeypatch.setattr(module.os,'sched_setaffinity',lambda pid,cpus:None,raising=False)
    monkeypatch.setattr(module.signal,'signal',lambda *a:None)
    monkeypatch.setattr(module.signal,'setitimer',lambda *a:None)
    class FakeProcess:
        def __init__(self,cmd,**kw):
            self.pid=1234+len(commands);self.returncode=0;commands.append(cmd)
            if '--report' in cmd:
                Path(cmd[cmd.index('--report')+1]).write_text(json.dumps(dict(reason=None)))
                events.append('guardian_created')
            else:events.append('controller_blocked')
        def poll(self):return 0
        def wait(self,timeout=None):return 0
    monkeypatch.setattr(module.subprocess,'Popen',FakeProcess)
    monkeypatch.setattr(module,'wait_guard_ready',lambda fd:events.append('guardian_ready'))
    old_write=module.os.write
    def write(fd,data):
        if data==b'1':
            assert events[-1]=='guardian_ready';events.append('controller_gate_open')
        return old_write(fd,data)
    monkeypatch.setattr(module.os,'write',write)
    module.outer(tmp_path,'/artificial/authority','fake',time.time()+1800)
    assert events==['controller_blocked','guardian_created','guardian_ready','controller_gate_open']
    assert '--controller' in commands[0] and '--worker' in commands[1]
    receipt=json.loads((tmp_path/'outer_launch_receipt.json').read_text())
    assert receipt['guardian_armed_before_hash_or_model'] is True
