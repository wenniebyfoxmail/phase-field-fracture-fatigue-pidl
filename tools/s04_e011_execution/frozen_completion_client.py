from pathlib import Path
import argparse,base64,csv,hashlib,io,json,shlex,subprocess,tarfile,time
ap=argparse.ArgumentParser();ap.add_argument('--case',type=Path,required=True);case=ap.parse_args().case;receipt=case/'execution_receipt.json';r=json.loads(receipt.read_text());prep=Path(r['package']);card=json.loads((prep/'execution_card.json').read_text());deadline=card['envelope_deadline_epoch'];assert r['mechanical_checks']==0 and not r['producer_started']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
mechanical_started_local=None
def checked(argv):
 sizes=[len(x.encode())+1 for x in argv]
 if max(sizes)>16384 or sum(sizes)>65536:raise RuntimeError('argv exceeds16KiB single/64KiB total')
 with (case/'argv_audit.jsonl').open('a') as stream:stream.write(json.dumps(dict(max_argument_bytes=max(sizes),total_argv_bytes=sum(sizes),command=argv))+'\n')
 return argv
def save():receipt.write_text(json.dumps(r,indent=2)+'\n')
def remaining(cap):
 left=deadline-time.time()
 if left<=30:raise RuntimeError('whole-task time expired; no action')
 return min(cap,left-20)
ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ConnectionAttempts=1','-o','ControlMaster=no','-o','ControlPath=none','gpu-taobo']
probe=r'''import csv,hashlib,io,json,os,pathlib,pwd,shutil,socket,subprocess,sys,time
card=json.load(sys.stdin);started=time.monotonic();root=pathlib.Path(card['run_root']);archive=pathlib.Path(card['archive_root']);claims=root.parent/'.s04_e011_profiled_hidden_claims'
z=dict(started=started,UTC=time.time(),host=socket.gethostname(),user=pwd.getpwuid(os.geteuid()).pw_name,mount=pathlib.Path('/mnt/data2').is_mount(),root_exists=root.exists(),archive_exists=archive.exists(),claim_exists=pathlib.Path(card['family_claim']).exists(),old_return_exists=(claims/(root.name+'.outer_return.json')).exists(),free_disk=shutil.disk_usage('/mnt/data2').free,matching_live=[])
z['GPU']=subprocess.check_output(['nvidia-smi','-i','5','--query-gpu=index,uuid,memory.total,memory.free,utilization.gpu','--format=csv,noheader,nounits'],text=True,timeout=4).strip()
z['apps']=[row for row in csv.reader(io.StringIO(subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,gpu_uuid,used_memory','--format=csv,noheader,nounits'],text=True,timeout=4))) if row[1].strip()==card['producer']['gpu_uuid']]
z['MemAvailable_kb']=int(next(line.split()[1] for line in pathlib.Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))
for p in pathlib.Path('/proc').glob('[0-9]*/cmdline'):
 try:
  if int(p.parent.name)==os.getpid():continue
  args=p.read_bytes().split(bytes([0]));owned=[a.decode(errors='replace') for a in args[:5] if a.startswith(b'/mnt/data2/drtao/wennie/') and b'/s04_e011_execution/' in a]
  if owned:z['matching_live'].append(dict(pid=int(p.parent.name),command=owned))
 except OSError:pass
old=pathlib.Path('/mnt/data2/drtao/wennie/pf_s04e011_profiled_hidden_c20_r2_hq_20261020/export_manifest.json');z['old_R2_manifest_sha256']=hashlib.sha256(old.read_bytes()).hexdigest()
z['inputs']=[]
for item in card['input_bindings']+card['reuse_bindings']:
 p=pathlib.Path(item['source']);assert not p.is_symlink();h=hashlib.sha256()
 with p.open('rb') as stream:
  for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
 z['inputs'].append(dict(role=item['role'],bytes=p.stat().st_size,sha256=h.hexdigest()))
z['finished']=time.monotonic();print(json.dumps(z))
'''
r.update(status='MECHANICAL1_REQUESTED',mechanical_checks=1);save();local_started=time.monotonic()
p=subprocess.run(checked(ssh+['/usr/bin/python3 -B -c '+shlex.quote(probe)]),input=json.dumps(card),capture_output=True,text=True,timeout=remaining(25));(case/'logs/probe.stdout').write_text(p.stdout);(case/'logs/probe.stderr').write_text(p.stderr)
if p.returncode:r.update(status='STOPPED_NO_RETRY_MECHANICAL1',returncode=p.returncode);save();raise SystemExit('first read-only contact failed, no retry')
z=json.loads(p.stdout);z['remote_probe_started_original']=z['started'];z['started']=z['finished']-(time.monotonic()-local_started);r['mechanical1']=z;save();gpu=next(csv.reader([z['GPU']]))
assert z['host']=='GPUServer8' and z['user']=='drtao' and z['mount'] and z['free_disk']>=24*1024**3 and z['MemAvailable_kb']>=32*1024**2
assert not any(z[k] for k in ['root_exists','archive_exists','claim_exists','old_return_exists','matching_live'])
assert z['old_R2_manifest_sha256']=='6b5b2bf65640c02eac6b3a67834e2a3baf53d517748eff128341a4e761870d3b'
assert int(gpu[0])==5 and gpu[1].strip()==card['producer']['gpu_uuid']
if z['apps'] or int(gpu[3])<20480 or int(gpu[4])>=10:
 r.update(status='STOPPED_NOT_STARTED_GPU_BUSY_OR_CAPACITY');save();raise SystemExit('GPU5not safely available; no launch/no waiting')
assert abs(time.time()-z['UTC'])<15
assert len(z['inputs'])==len(card['input_bindings'])+len(card['reuse_bindings'])
for item,got in zip(card['input_bindings']+card['reuse_bindings'],z['inputs']):assert item['role']==got['role'] and item['bytes']==got['bytes'] and item['sha256']==got['sha256']
authority=dict(approved_by='human_delegated_HQ',execute_one_frozen_pair_completion=True,family=card['family'],run_id=card['run_id'],package_sha256=r['package_sha256'],authority_ref=card['authority_ref'],
 verified_direct_human_message='01a15b4c-2e3a-7772-b74b-46f4ab752766',source_HQ_thread='01a14bb9-6cd1-7ee2-9647-5190d786f7ba',prospective_new_measurement=True,old_R2_reopened=False,mechanical_started_monotonic=z['started'],mechanical_checks=2,mechanical_max_seconds=90,mechanical_client_started_epoch=time.time()-(time.monotonic()-local_started),absolute_deadline_epoch=deadline)
a=case/'authority.approved.json';a.write_text(json.dumps(authority,indent=2)+'\n');authsha=sha(a)
oldprep=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl/local_archive/experiments/S04-E011/pidl_residual_branch_package_20261021');oldmap={x['path']:x for x in json.loads((oldprep/'package_manifest.json').read_text())['files']};manifest=json.loads((prep/'package_manifest.json').read_text());delta=[x['path'] for x in manifest['files'] if x['path'] not in oldmap or x['sha256']!=oldmap[x['path']]['sha256']];delta+=['package_manifest.json'];buf=io.BytesIO()
with tarfile.open(fileobj=buf,mode='w:gz') as tar:
 for name in delta:tar.add(prep/name,arcname=name)
 tar.add(a,arcname='authority.approved.json')
blob=buf.getvalue();assert len(blob)<1048576;(case/'approved_delta.tar.gz').write_bytes(blob)
stage=r'''import hashlib,io,json,os,pathlib,pwd,shutil,socket,subprocess,sys,tarfile,time
root=pathlib.Path(ROOT);archive=pathlib.Path(ARCHIVE);base=pathlib.Path('/mnt/data2/drtao/wennie/pf_s04e011_residual_branch_c20_r1_hq_20261021');claims=root.parent/'.s04_e011_profiled_hidden_claims'
assert socket.gethostname()=='GPUServer8' and pwd.getpwuid(os.geteuid()).pw_name=='drtao'
assert 0<=time.monotonic()-MECHSTART<90 and time.time()<DEADLINE-620 and not root.exists() and not archive.exists()
assert hashlib.sha256((base/'package_manifest.json').read_bytes()).hexdigest()=='f2038e42521864581634fc70160dcf0216f35522dc33e362d909e5c57d87bfc3'
raw=sys.stdin.buffer.read(BLOBLEN);assert hashlib.sha256(raw).hexdigest()==BLOBSHA;root.mkdir()
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
 for row in tar.getmembers():
  p=pathlib.Path(row.name);assert not p.is_absolute() and '..' not in p.parts and row.isfile()
 tar.extractall(root)
manifest=json.loads((root/'package_manifest.json').read_text());assert hashlib.sha256((root/'package_manifest.json').read_bytes()).hexdigest()==PKGSHA
for row in manifest['files']:
 p=root/row['path']
 if not p.exists():
  source=base/row['path'];assert not source.is_symlink() and source.stat().st_size==row['bytes'] and hashlib.sha256(source.read_bytes()).hexdigest()==row['sha256'];p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,p)
sys.path.insert(0,str(root/'code/tools/s04_e011_execution'))
from control import verify_package
from frozen_completion_launch import validate
verify_package(root,manifest);card=json.loads((root/'execution_card.json').read_text());authority=json.loads((root/'authority.approved.json').read_text());assert hashlib.sha256((root/'authority.approved.json').read_bytes()).hexdigest()==AUTHSHA;validate(card,authority,PKGSHA)
assert time.monotonic()-MECHSTART<90
out=claims/(root.name+'.bootstrap.stdout');err=claims/(root.name+'.bootstrap.stderr');cmd=['/usr/bin/python3','-B',str(root/'code/tools/s04_e011_execution/frozen_completion_launch.py'),'--package',str(root),'--authority',str(root/'authority.approved.json'),'--authority-sha256',AUTHSHA,'--envelope-deadline',str(DEADLINE)]
assert max(len(x.encode())+1 for x in cmd)<=16384 and sum(len(x.encode())+1 for x in cmd)<=65536
with out.open('xb') as stdout,err.open('xb') as stderr:p=subprocess.Popen(cmd,cwd=root/'code',env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
confirm_deadline=min(time.monotonic()+20,MECHSTART+80)
while time.monotonic()<confirm_deadline and not (root/'launch_receipt.json').exists() and not (root/'controller_terminal.json').exists():time.sleep(.1)
confirmation_failed=not (root/'launch_receipt.json').exists() and not (root/'controller_terminal.json').exists()
if confirmation_failed and p.poll() is None:
 actual=pathlib.Path('/proc')/str(p.pid)
 assert os.readlink(actual/'cwd')==str(root/'code') and actual.joinpath('cmdline').read_bytes().split(bytes([0]))[:-1]==[v.encode() for v in cmd]
 p.terminate();p.wait(timeout=5)
print(json.dumps(dict(confirmation_failed=confirmation_failed,bootstrap_exit=p.poll(),bootstrap_pid=p.pid,root=str(root),archive=str(archive),command=cmd,log=str(root/'worker.log'),stdout=str(out),stderr=str(err),mechanical_seconds=time.monotonic()-MECHSTART,launch_receipt=json.loads((root/'launch_receipt.json').read_text()) if (root/'launch_receipt.json').exists() else None,controller_terminal=json.loads((root/'controller_terminal.json').read_text()) if (root/'controller_terminal.json').exists() else None)))
'''
for key,val in dict(ROOT=repr(card['run_root']),ARCHIVE=repr(card['archive_root']),MECHSTART=repr(z['started']),DEADLINE=repr(deadline),BLOBLEN=str(len(blob)),BLOBSHA=repr(hashlib.sha256(blob).hexdigest()),PKGSHA=repr(r['package_sha256']),AUTHSHA=repr(authsha)).items():stage=stage.replace(key,val)
r.update(status='MECHANICAL2_STAGE_SINGLE_LAUNCH_REQUESTED',mechanical_checks=2,authority_sha256=authsha,delta_files=delta,delta_bytes=len(blob));save()
cmd=ssh+['/usr/bin/python3 -B -c '+shlex.quote(stage)];(case/'logs/stage_command.json').write_text(json.dumps(cmd,indent=2)+'\n')
mechanical_left=90-(time.monotonic()-local_started)
if mechanical_left<=15:raise RuntimeError('insufficient mechanical allowance, no stage')
p=subprocess.run(checked(cmd),input=blob,capture_output=True,timeout=remaining(mechanical_left-5));(case/'logs/stage.stdout').write_bytes(p.stdout);(case/'logs/stage.stderr').write_bytes(p.stderr)
r.update(status='BOOTSTRAP_RESPONSE_RECORDED' if p.returncode==0 else 'UNKNOWN_OR_STAGE_FAILED_NO_RELAUNCH',stage_returncode=p.returncode)
if p.returncode==0:
 launch=json.loads(p.stdout);r.update(producer_started=bool(launch.get('launch_receipt')),bootstrap_started=True,launch=launch,status='STOPPED_NO_LAUNCH_CONFIRMATION_NO_RELAUNCH' if launch['confirmation_failed'] else ('LAUNCH_CONFIRMED' if launch.get('launch_receipt') else 'CONTROLLER_STOPPED_BEFORE_LAUNCH'))
save();print(json.dumps(dict(status=r['status'],stage_returncode=p.returncode,launch=r.get('launch'),stderr=p.stderr.decode()),indent=2))
