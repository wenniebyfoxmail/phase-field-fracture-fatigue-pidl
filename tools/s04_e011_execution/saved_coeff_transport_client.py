"""One CPU-only saved attribution SSH, streaming return. No scientific imports."""
from pathlib import Path
import argparse,hashlib,json,os,resource,subprocess,sys,tarfile,time
resource.setrlimit(resource.RLIMIT_CPU,(15,15));START=time.monotonic();C0=time.process_time()
from local_owned_rss_guard import OwnedGuard
ap=argparse.ArgumentParser();ap.add_argument('--case',type=Path,required=True);ap.add_argument('--card',type=Path,required=True);ap.add_argument('--repo',type=Path,required=True);a=ap.parse_args();case=a.case;root=a.repo
# Arm before reading task card/source metadata, and before any SSH child exists.
g=OwnedGuard(510).start();g.tree_limit=(case,512*1024**2);p=None;fds=[];r=dict(status='LOCAL_MONITOR_ARMED_NO_SSH',new_SSH_connections=0,source_private_input_upload=False)
def save():(case/'execution_receipt.json').write_text(json.dumps(r,indent=2)+'\n')
def sha(f):
 h=hashlib.sha256()
 with f.open('rb') as s:
  for b in iter(lambda:s.read(1048576),b''):h.update(b)
 return h.hexdigest()
try:
 assert not (case/'execution_receipt.json').exists();card=json.loads(a.card.read_text());g.end=min(g.end,time.monotonic()+max(.01,card['deadline_epoch']-time.time()-90));signal_seconds=max(.01,g.end-time.monotonic())
 import signal
 signal.setitimer(signal.ITIMER_REAL,signal_seconds)
 source=(root/'tools/s04_e011_analysis/saved_coefficient_attribution.py').read_bytes();assert hashlib.sha256(source).hexdigest()==card['source_script_sha256'];payload=('import json\nCONFIG=json.loads('+repr(json.dumps(card))+')\n').encode()+source
 ssh=['/usr/bin/ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ConnectionAttempts=1','-o','ControlMaster=no','-o','ControlPath=none','gpu-taobo','/usr/bin/python3 -B -']
 gate_r,gate_w=os.pipe();fds=[gate_r,gate_w]
 wrapper="import os,resource,sys;resource.setrlimit(resource.RLIMIT_CPU,(10,10));fd=int(sys.argv[1]);assert os.read(fd,1)==b'1';os.close(fd);os.execv(sys.argv[2],sys.argv[2:])";cmd=[sys.executable,'-B','-c',wrapper,str(gate_r)]+ssh
 assert max(len(x.encode())+1 for x in cmd)<=16384
 r.update(status='SINGLE_SSH_REQUESTED',analysis_id=card['analysis_id'],authority_ref=card['authority_ref'],command=cmd,source_script_sha256=card['source_script_sha256'],stdin_bytes=len(payload),SSH_attempts_requested=1);save()
 network=case/'returned.tar.gz';err=case/'logs/remote.stderr';g.path_limits=[(network,100*1024**2)]
 with network.open('xb') as out,err.open('xb') as stderr:
  p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=out,stderr=stderr,cwd=root,start_new_session=True,pass_fds=(gate_r,))
  os.close(gate_r);fds.remove(gate_r);g.bind(p,[cmd,ssh],root)
  if g.failure:raise RuntimeError('monitor failure before SSH gate')
  os.write(gate_w,b'1');os.close(gate_w);fds.remove(gate_w);r['SSH_gate_opened']=True;save()
  p.communicate(payload,timeout=max(.01,g.end-time.monotonic()))
 if p.returncode:raise RuntimeError('remote/transport returned '+str(p.returncode)+': '+err.read_text(errors='replace')[-3000:])
 assert network.stat().st_size<100*1024**2
 target=case/'retrieved';target.mkdir();unpacked=0
 with tarfile.open(network,mode='r|gz') as tar:
  for member in tar:
   rel=Path(member.name);assert member.isfile() and not rel.is_absolute() and '..' not in rel.parts;unpacked+=member.size;assert unpacked<100*1024**2
   f=target/rel;f.parent.mkdir(parents=True,exist_ok=True)
   with tar.extractfile(member) as src,f.open('xb') as dest:
    while True:
     chunk=src.read(1048576)
     if not chunk:break
     dest.write(chunk)
 manifest=json.loads((target/'output_manifest.json').read_text())
 for row in manifest['files']:
  rel=Path(row['path']);assert not rel.is_absolute() and '..' not in rel.parts;f=target/rel;assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
 if g.failure:raise RuntimeError('monitor failure prevents success: '+g.failure)
 r.update(status='SAVED_ATTRIBUTION_COMPLETE_VERIFIED',new_SSH_connections=1,remote_final=json.loads(err.read_text().splitlines()[-1]),retrieved_files=len(manifest['files']),retrieved_bytes=unpacked,network_bytes=network.stat().st_size,all_selected_SHA_verified=True,full_Phi_transferred=False)
except BaseException as e:
 r.update(status='STOPPED_NO_RETRY',new_SSH_connections='UNKNOWN' if r.get('SSH_gate_opened') else 0,error=type(e).__name__+': '+str(e),remote_state='UNKNOWN_if_SSH_requested_no_reconnect');g.terminate_owned()
finally:
 def final_signal(sig,frame):r.update(status='STOPPED_NO_RETRY',error=g.failure or 'monitor signal during finalization')
 import signal
 signal.signal(signal.SIGTERM,final_signal);signal.signal(signal.SIGALRM,final_signal)
 for fd in fds:os.close(fd)
 if p is not None:
  try:p.wait(timeout=1)
  except subprocess.TimeoutExpired:g.terminate_owned()
 try:g.close()
 except BaseException as e:r.update(status='STOPPED_NO_RETRY',error='monitor close '+str(e));g.terminate_owned()
 if g.failure:r.update(status='STOPPED_NO_RETRY',error=g.failure)
 r.update(monitor=g.report(),client_wall_seconds=time.monotonic()-START,client_total_process_CPU_seconds=resource.getrusage(resource.RUSAGE_SELF).ru_utime+resource.getrusage(resource.RUSAGE_SELF).ru_stime,local_child_CPU_seconds=resource.getrusage(resource.RUSAGE_CHILDREN).ru_utime+resource.getrusage(resource.RUSAGE_CHILDREN).ru_stime);save()
print(json.dumps(r,indent=2));sys.exit(0 if r['status']=='SAVED_ATTRIBUTION_COMPLETE_VERIFIED' else 1)
