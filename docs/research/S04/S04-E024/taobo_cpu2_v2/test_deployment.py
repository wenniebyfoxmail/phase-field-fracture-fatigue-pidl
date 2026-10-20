"""Pure deployment fixtures only. No Torch/science import, SSH or real inputs."""
import importlib.util,sys,io,json,tarfile,hashlib,time,subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest
HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('d013_v2_remote',HERE/'remote_entry.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
spec=importlib.util.spec_from_file_location('d013_v2_client',HERE/'transfer_and_start.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

def auth():
 return dict(user_approved_final_execution=True,remote_actions_authorized=True,training_authorized=False,scope=r.SCOPE,
  package_id=r.PACK,execution_commit=r.SCIENCE,remote_root=str(r.ROOT),user_approval_quote='ARTIFICIAL FIXTURE ONLY',
  **{k:'a'*64 for k in ('payload_sha256','payload_manifest_sha256','remote_entry_sha256','action_manifest_sha256')},
  base_nontraining_charge_seconds=72.,fixed_local_archive_bytes=500_000_000)

@pytest.mark.parametrize('change',[{'user_approved_final_execution':False},{'remote_actions_authorized':False},
 {'training_authorized':True},{'package_id':'v1'},{'remote_root':'/tmp/other'},{'execution_commit':'wrong'},
 {'user_approval_quote':''},{'payload_sha256':None},{'base_nontraining_charge_seconds':0}])
def test_authority_is_exact_and_never_inherited(change):
 a=auth();a.update(change)
 with pytest.raises(r.PackageError):r.validate_auth(a)

def environment():
 return dict(system='Linux',machine='x86_64',host='GPUServer8',user='drtao',implementation='CPython',
  executable='/usr/bin/python3.10',bound_executable='/usr/bin/python3.10',python=[3,10,12],versions=dict(r.REQUIREMENTS))

@pytest.mark.parametrize('key,value',[('system','Darwin'),('host','other'),('user','wenxiaofang'),
 ('machine','arm64'),('python',[3,9,1]),('executable','/opt/conda/bin/python')])
def test_producer_environment_is_not_Mac_or_path_fallback(key,value):
 e=environment();assert r.environment_check(e)==e;e[key]=value
 with pytest.raises(r.PackageError):r.environment_check(e)

def test_dependency_policy_unknown_is_not_a_pass():
 e=environment();e['versions']['scipy']='UNKNOWN'
 with pytest.raises(r.PackageError):r.environment_check(e)

@pytest.mark.parametrize('entry',['remote','client'])
def test_default_cli_has_no_transport_or_science(monkeypatch,entry):
 module=r if entry=='remote' else c
 monkeypatch.setattr(sys,'argv',['fixture'])
 monkeypatch.setattr(module.subprocess,'run',lambda *a,**k:pytest.fail('no transport'))
 monkeypatch.setattr(module.subprocess,'Popen',lambda *a,**k:pytest.fail('no process'))
 with pytest.raises(SystemExit):module.main()

def test_false_client_auth_stops_before_manifest_or_ssh(tmp_path,monkeypatch):
 p=tmp_path/'auth.json';p.write_text('{"user_approved_final_execution":false}')
 monkeypatch.setattr(sys,'argv',['fixture','--authorization',str(p)])
 monkeypatch.setattr(c.subprocess,'run',lambda *a,**k:pytest.fail('no SSH/SCP'))
 with pytest.raises(c.r.PackageError):c.main()

@pytest.mark.parametrize('case',['escape','symlink','duplicate','hash','valid'])
def test_payload_safe_paths_and_hashes(tmp_path,monkeypatch,case):
 monkeypatch.setattr(r,'ROOT',tmp_path/'remote');r.ROOT.mkdir()
 name='project/local_archive/experiments/fixture' if case!='escape' else '../outside'
 data=b'fixture';identity=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
 if case=='hash':identity['sha256']='0'*64
 meta=json.dumps(dict(files={name:identity})).encode()
 wire=tmp_path/'wire.tar'
 with tarfile.open(wire,'w') as tf:
  x=tarfile.TarInfo('package/payload_manifest.json');x.size=len(meta);tf.addfile(x,io.BytesIO(meta))
  x=tarfile.TarInfo(name);x.size=len(data)
  if case=='symlink':x.type=tarfile.SYMTYPE;x.linkname='/tmp/wrong';x.size=0;tf.addfile(x)
  else:tf.addfile(x,io.BytesIO(data))
  if case=='duplicate':tf.addfile(x,io.BytesIO(data))
 a={'payload_manifest_sha256':hashlib.sha256(meta).hexdigest()}
 if case=='valid':r.unpack_payload(wire,a,lambda:None);assert (r.ROOT/name).read_bytes()==data
 else:
  with pytest.raises(r.PackageError):r.unpack_payload(wire,a,lambda:None)

def test_prior_local_and_producer_storage_are_one_budget(tmp_path,monkeypatch):
 monkeypatch.setattr(r,'FIXED_LOCAL_BYTES',100);(tmp_path/'file').write_bytes(b'x'*30)
 assert r.combined_storage((tmp_path,))==130
 child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)'],start_new_session=True)
 with pytest.raises(r.PackageError,match='archive'):
  r.supervise_child(child,(tmp_path,),time.monotonic()+5,cap=120,poll=.01)
 assert child.poll() is not None

def test_prelaunch_deadline_is_cumulative_and_cost_not_reset(tmp_path,monkeypatch):
 monkeypatch.setattr(r,'ROOT',tmp_path);monkeypatch.setattr(r,'FIXED_LOCAL_BYTES',0)
 monkeypatch.setattr(r.resource,'getrusage',lambda *a:SimpleNamespace(ru_maxrss=1024))
 t=time.monotonic();check=r.budget_guard(t,299.99);time.sleep(.02)
 with pytest.raises(r.PackageError,match='deadline'):check()

def test_remote_role_rejection_before_claim(tmp_path,monkeypatch):
 monkeypatch.setattr(r,'ROOT',tmp_path/'not-created')
 a=auth();a['remote_root']=str(r.ROOT)
 monkeypatch.setattr(r,'environment_check',lambda:(_ for _ in ()).throw(r.PackageError('wrong host')))
 monkeypatch.setattr(r,'budget_guard',lambda *a:lambda:None)
 a.update(producer_anchor_monotonic_seconds=1000.,anchor_ack_client_elapsed_seconds=1.)
 with pytest.raises(r.PackageError,match='wrong host'):r.bootstrap(a,'create',create_anchor=1000.)
 assert not r.ROOT.exists()

def test_no_Torch_was_imported_by_deployment_checks():
 assert 'torch' not in sys.modules


def test_delayed_final_delivery_cannot_reset_producer_deadline(tmp_path,monkeypatch):
 a=auth();answer=dict(status='ANCHOR_ONLY_NO_METADATA',root=str(r.ROOT),
  action_manifest_sha256=a['action_manifest_sha256'],anchor_monotonic_seconds=1000.)
 # Producer stamp1000 happened before client ACK receive20s. Deadline1208
 # remains1208 even if the final SSH is delivered after client timeout.
 anchored=c.anchor_authority(a,answer,20.)
 identity=dict(anchor_monotonic_seconds=1000.,authority=a['action_manifest_sha256'])
 pre,global_deadline=r.anchored_deadlines(anchored,identity)
 assert pre==1208. and global_deadline==4028.
 monkeypatch.setattr(r.time,'monotonic',lambda:1210.)
 monkeypatch.setattr(r,'ROOT',tmp_path)
 monkeypatch.setattr(r.resource,'getrusage',lambda *a:SimpleNamespace(ru_maxrss=1024))
 with pytest.raises(r.PackageError,match='deadline'):r.budget_guard(1210.,72.,pre)()


def test_anchor_identity_cannot_change_or_reset():
 a=auth();a.update(producer_anchor_monotonic_seconds=1000.,anchor_ack_client_elapsed_seconds=20.)
 with pytest.raises(r.PackageError,match='anchor'):r.anchored_deadlines(a,dict(anchor_monotonic_seconds=1001.,authority=a['action_manifest_sha256']))
 with pytest.raises(r.PackageError,match='balance'):r.anchored_deadlines(dict(a,anchor_ack_client_elapsed_seconds=229.),dict(anchor_monotonic_seconds=1000.,authority=a['action_manifest_sha256']))


@pytest.mark.parametrize('local,wire,peak',[(700_000_000,400_000_000,400_000_000),(400_000_000,300_000_000,700_000_000)])
def test_combined_archive_rejected_before_any_scp(local,wire,peak):
 with pytest.raises(c.r.PackageError,match='pre-upload'):c.upload_capacity(local,wire,peak)


def test_combined_archive_admission_is_inclusive():
 c.upload_capacity(400_000_000,300_000_000,600_000_000)


def test_create_checks_deadline_before_metadata_or_claim(tmp_path,monkeypatch):
 monkeypatch.setattr(r,'ROOT',tmp_path/'absent')
 a=auth();a.update(remote_root=str(r.ROOT),producer_anchor_monotonic_seconds=1000.,anchor_ack_client_elapsed_seconds=20.)
 monkeypatch.setattr(r.time,'monotonic',lambda:1210.)
 monkeypatch.setattr(r,'environment_check',lambda:pytest.fail('expired handshake may not inspect metadata'))
 with pytest.raises(r.PackageError,match='deadline'):r.bootstrap(a,'create',create_anchor=1000.)
 assert not r.ROOT.exists()


def test_remote_handshake_is_before_metadata_and_root_claim(monkeypatch):
 # CLI artificial EOF after first ACK: no real metadata, directory or Popen.
 monkeypatch.setattr(sys,'argv',['fixture','--bootstrap-create'])
 monkeypatch.setattr(sys,'stdin',io.StringIO(json.dumps(auth())+'\n'))
 monkeypatch.setattr(r,'environment_check',lambda:pytest.fail('no metadata before handshake completes'))
 monkeypatch.setattr(r,'bootstrap',lambda *a,**k:pytest.fail('no claim before second message'))
 with pytest.raises(json.JSONDecodeError):r.main()


def test_kill_requires_exact_owned_cmdline_cwd_and_elapsed(tmp_path):
 child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)'],cwd=tmp_path,start_new_session=True)
 r.bind_owned(child,tmp_path);r.terminate_owned(child)
 assert child.poll() is not None
 assert child.d013_pre_kill[0]['cmdline']==list(child.args)
 assert Path(child.d013_pre_kill[0]['cwd'])==tmp_path
 assert child.d013_pre_kill[0]['elapsed_seconds']>=0


def test_resource_preflight_records_all_required_mounts(monkeypatch):
 monkeypatch.setattr(r.os.path,'ismount',lambda p:True)
 monkeypatch.setattr(r.os,'sched_getaffinity',lambda p:{0,1},raising=False)
 original=Path.read_text
 monkeypatch.setattr(Path,'read_text',lambda p,*a,**k:'MemAvailable: 8388608 kB\n' if str(p)=='/proc/meminfo' else original(p,*a,**k))
 monkeypatch.setattr(r.shutil,'disk_usage',lambda p:SimpleNamespace(free=3*1024**3))
 calls=[]
 def fake_df(command,**k):
  calls.append(command);return SimpleNamespace(returncode=0,stdout='fixture only',stderr='')
 monkeypatch.setattr(r.subprocess,'run',fake_df)
 result=r.resource_check()
 assert calls==[['df','-h','/','/mnt/data2','/mnt/data3']]
 assert result['GPU_queries']==0


@pytest.mark.parametrize('exitcode',[0,3])
def test_parent_exit_never_leaves_owned_worker_alive(tmp_path,monkeypatch,exitcode):
 import psutil
 pidfile=tmp_path/'child_pid'
 program="import os,time,pathlib; pid=os.fork(); pathlib.Path('child_pid').write_text(str(pid)) if pid else None; time.sleep(.15) if pid else time.sleep(10); os._exit("+str(exitcode)+")"
 parent=subprocess.Popen([sys.executable,'-c',program],cwd=tmp_path,start_new_session=True)
 r.bind_owned(parent,tmp_path)
 while not pidfile.exists():time.sleep(.005)
 orphan=int(pidfile.read_text());parent.wait(timeout=2)
 monkeypatch.setattr(r,'FIXED_LOCAL_BYTES',0)
 with pytest.raises(r.PackageError,match='parent exit'):
  r.supervise_child(parent,(tmp_path,),time.monotonic()+5)
 assert any(row['pid']==orphan for row in parent.d013_pre_kill)
 assert not psutil.pid_exists(orphan) or psutil.Process(orphan).status()==psutil.STATUS_ZOMBIE
