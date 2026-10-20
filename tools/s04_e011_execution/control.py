"""E011 local-only producer control primitives. Import has no execution IO.

Reuses hybrid supervisor bytes_under/stop_owned/ready handshake patterns; all
science remains in the immutable ae01bfed adapter and its card.
"""
import hashlib,json,math,os,select,signal,subprocess,time
from pathlib import Path

PHASES=('preflight','candidate','bounded_witness','readout')
SECONDS=(300,1800,600,300)
RESERVE=20  # Inside each existing phase/total cap; never an extension.
FAMILY='S04-E011-PROFILED-HIDDEN-C20-v1'


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def write_json(path,value):
    p=Path(path);tmp=p.with_name(p.name+'.'+str(os.getpid())+'.tmp')
    with tmp.open('w') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)


def bytes_under(path):
    total=0
    for base,dirs,files in os.walk(path,followlinks=False):
        for name in dirs+files:
            if (Path(base)/name).is_symlink():raise RuntimeError('task output symlink forbidden')
        total+=sum((Path(base)/name).stat().st_size for name in files)
    return total


def stop_owned(proc):
    # Pattern from run_hybrid_producer.stop_owned: never signal a foreign PID.
    if proc.poll() is None:
        try:
            if os.getpgid(proc.pid)!=proc.pid:raise RuntimeError('owned process group changed')
            os.killpg(proc.pid,signal.SIGTERM)
        except ProcessLookupError:proc.wait(timeout=10);return
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=10)


def wait_guard_ready(fd):
    if not select.select([fd],[],[],5)[0] or os.read(fd,1)!=b'1':raise RuntimeError('deadline guardian not ready; worker gate closed')


def allowed_phases(scope):
    if scope=='preflight_only':return PHASES[:1]
    if scope=='conditional_full':return PHASES
    raise ValueError('explicit bounded approval scope required')


def validate_authority(authority,authority_sha,authority_path,card,package_sha):
    if digest(authority_path)!=authority_sha:raise RuntimeError('authority bytes differ')
    if (authority.get('approved_by')!='human' or authority.get('activate_closed_package') is not True
        or not isinstance(authority.get('approval_ref'),str) or not authority['approval_ref'].strip()
        or authority.get('family')!=FAMILY or authority.get('run_id')!=card['run_id']
        or authority.get('package_sha256')!=package_sha):raise RuntimeError('exact human authority absent/mismatched')
    revision=card.get('admission_revision')
    if revision and (authority.get('amends_first_stop_package_sha256')!=revision['prior_package_sha256'] or authority.get('amends_first_stop_receipt_sha256')!=revision['prior_stop_receipt_sha256']):raise RuntimeError('explicit first-stop amendment authority absent/mismatched')
    return allowed_phases(authority.get('scope'))


def consume_claim(path,authority_sha,run_id):
    # Whole family, not just a selectable run ID. Consumed BEFORE resource
    # admission, and kept on every failure/timeout; never auto-unlink/retry.
    p=Path(path)
    if p.is_symlink():raise RuntimeError('claim symlink')
    with p.open('x') as f:json.dump(dict(family=FAMILY,run_id=run_id,authority_sha256=authority_sha,pid=os.getpid(),status='consumed'),f);f.flush();os.fsync(f.fileno())


def verify_package(root,manifest):
    root=Path(root).resolve()
    for row in manifest['files']:
        relative=Path(row['path']);p=root/relative
        if relative.is_absolute() or '..' in relative.parts or p.is_symlink() or not p.is_file() or root not in p.resolve().parents:raise RuntimeError('unsafe/missing package member')
        if p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise RuntimeError('package member differs: '+str(relative))
    expected={r['path'] for r in manifest['files'] if Path(r['path']).parts[0]=='code'}
    actual=set()
    for p in (root/'code').rglob('*'):
        if p.is_symlink():raise RuntimeError('code symlink forbidden')
        if p.is_file():actual.add(str(p.relative_to(root)))
    if expected!=actual:raise RuntimeError('extra/missing code outside immutable manifest')
    return True


class Chain:
    """Single ordered authority/phase chain; no resume, skip or budget borrowing."""
    def __init__(self,scope,started,clock=time.monotonic):
        self.names=allowed_phases(scope);self.started=started;self.clock=clock;self.active=None;self.done=[];self.failed=False
    def begin(self,name):
        if self.failed or self.active is not None or len(self.done)>=len(self.names) or name!=self.names[len(self.done)]:raise RuntimeError('phase order/scope violation')
        now=self.clock();i=PHASES.index(name);start=self.started if not self.done else now
        deadline=min(start+SECONDS[i]-RESERVE,self.started+3000-RESERVE)
        if now>=deadline:raise RuntimeError('phase/total budget exhausted before work')
        self.active=dict(name=name,index=i+1,started=start,deadline=deadline);return dict(self.active)
    def finish(self,result):
        if self.failed or self.active is None:raise RuntimeError('no active phase')
        now=self.clock()
        if now>=self.active['deadline']:self.failed=True;raise RuntimeError('late phase completion')
        if result.get('completed') is not True:self.failed=True;raise RuntimeError('phase incomplete')
        if self.active['name']=='preflight' and (result.get('admitted') is not True or result.get('accepted_hidden_updates')!=0 or result.get('root_state_restored') is not True):
            self.failed=True;raise RuntimeError('preflight is not conditional authority')
        row={**self.active,'finished':now,'result':result};self.done.append(row);self.active=None;return row
    def terminal(self):
        if self.failed or self.active is not None or len(self.done)!=len(self.names):raise RuntimeError('missing authorised terminal')
        if self.clock()-self.started>3000:raise RuntimeError('late total terminal')
        return 'PREFLIGHT_ONLY_COMPLETE_NOT_SCIENTIFIC_SUCCESS' if len(self.names)==1 else 'FULL_COMPARISON_COMPLETE'


def drive(scope,started,functions,notify,save,clock=time.monotonic):
    chain=Chain(scope,started,clock)
    try:
        for name in chain.names:
            active=chain.begin(name)
            # Parent has already sent phase1 BEFORE opening the start gate.
            if active['index']!=1:notify(dict(event='step_start',step=active['index'],started=active['started']))
            result=functions[name]()
            row=chain.finish(result)
            save(name,row)  # Receipt IO remains inside the active hard window.
            finished=clock()
            if finished>=row['deadline']:chain.failed=True;raise RuntimeError('late phase receipt IO')
            notify(dict(event='step_done',step=row['index'],finished=finished))
        terminal=chain.terminal();return dict(status=terminal,phases=chain.done)
    except BaseException:
        chain.failed=True;raise


def validate_telemetry(row,now,limits,*,allow_boot=False):
    stamp=row.get('monotonic');rss=row.get('peak_rss_bytes');disk=row.get('peak_task_bytes')
    if not isinstance(stamp,(int,float)) or not math.isfinite(stamp) or not 0<=now-stamp<=10:raise RuntimeError('missing/stale worker telemetry')
    for value,cap in [(rss,limits['host_RSS']),(disk,limits['fresh_root_outputs'])]:
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 or value>cap:raise RuntimeError('host/storage peak limit or unavailable')
    if row.get('error'):raise RuntimeError('worker telemetry failure: '+str(row['error']))
    if row.get('cuda_state')=='boot' and allow_boot:return
    if row.get('cuda_state')!='active':raise RuntimeError('CUDA telemetry unavailable')
    for key,cap in [('peak_cuda_allocated',limits['GPU_allocated']),('peak_cuda_reserved',limits['GPU_reserved'])]:
        value=row.get(key)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0 or value>cap:raise RuntimeError('CUDA peak limit or unavailable')


def seal_outputs(roots,destination,run_id,status,postexit_exclusions=()):
    """Local export manifest on terminal/failure. No network/reconnection."""
    entries=[]
    for label,root in roots.items():
        root=Path(root)
        for p in sorted(root.rglob('*')):
            if p.is_symlink():raise RuntimeError('export symlink forbidden')
            if p.is_file() and p.resolve()!=Path(destination).resolve() and (label,str(p.relative_to(root))) not in postexit_exclusions:entries.append(dict(root=label,path=str(p.relative_to(root)),bytes=p.stat().st_size,sha256=digest(p)))
    locations=[dict(root=label,path=str(Path(destination).resolve().relative_to(Path(root).resolve()))) for label,root in roots.items() if Path(root).resolve() in Path(destination).resolve().parents]
    if len(locations)!=1:raise RuntimeError('manifest must belong to one task root')
    value=dict(run_id=run_id,status=status,entries=entries,manifest_location=locations[0],postexit_exclusions=[dict(root=k,path=v) for k,v in postexit_exclusions],network_transfer_performed=False)
    write_json(destination,value);return value


def verify_retrieval(manifest,roots,outer_return=None):
    seen=set()
    for row in manifest['entries']:
        key=(row['root'],row['path']);relative=Path(row['path']);base=Path(roots[row['root']]).resolve();p=base/relative
        if key in seen or relative.is_absolute() or '..' in relative.parts or p.is_symlink() or base not in p.resolve().parents:raise RuntimeError('unsafe/duplicate retrieved member')
        seen.add(key)
        if not p.is_file() or p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise RuntimeError('retrieval identity failure')
    actual=set()
    for label,root in roots.items():
        for p in Path(root).rglob('*'):
            if p.is_symlink():raise RuntimeError('retrieval symlink forbidden')
            if p.is_file():actual.add((label,str(p.relative_to(root))))
    location=manifest.get('manifest_location');allowed=set()
    if location is not None:
        key=(location['root'],location['path']);p=Path(roots[key[0]])/key[1]
        if p.exists():
            if json.loads(p.read_text())!=manifest:raise RuntimeError('retrieved manifest body differs')
            if outer_return is not None and digest(p)!=outer_return.get('export_manifest_sha256'):raise RuntimeError('producer-return manifest SHA differs')
            allowed.add(key)
    post=manifest.get('postexit_exclusions',[])
    if post:
        if outer_return is None or outer_return.get('run_id')!=manifest['run_id']:raise RuntimeError('postexit receipt required')
        returned={(r['root'],r['path']):r for r in outer_return['postexit_files']}
        if set(returned)!={(r['root'],r['path']) for r in post}:raise RuntimeError('postexit file set differs')
        for key,row in returned.items():
            relative=Path(key[1]);base=Path(roots[key[0]]).resolve();p=base/relative
            if relative.is_absolute() or '..' in relative.parts or p.is_symlink() or base not in p.resolve().parents:raise RuntimeError('unsafe postexit member')
            if not p.is_file() or p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:raise RuntimeError('postexit hash failure')
            allowed.add(key)
    if actual!=seen|allowed:raise RuntimeError('retrieval extra/missing file coverage')
    return dict(verified_entries=len(seen),run_id=manifest['run_id'],transfer_complete=True,scientific_success_inferred=False)
