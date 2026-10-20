#!/usr/bin/env python3
"""D013 Linux/GPUServer8 CPU2 deployment only. No scientific imports here."""
import argparse
from datetime import datetime,timezone
import getpass,hashlib,json,math,os,platform,resource,signal,shutil,subprocess,sys,tarfile,time
from pathlib import Path
from importlib import metadata
ROOT=Path('/mnt/data2/drtao/wennie/S04-E024-D013-CPU2-18d0e7cb-20261020-v2')
PYTHON='/usr/bin/python3'
PACK='D013-Taobo-CPU2-20261020-v2'
SCOPE='E024-D013-Taobo-CPU2-v2-12-profiles'
SCIENCE_SCOPE='E024-D013-physical-field-budget-12-profiles'
SCIENCE='18d0e7cb1153dc969c1ee0c21c77ada1297b2d89'
TREE='14f6ba5d4b0107e0655f711622ef51268222221e18666f65426bc11e42813c23'
CONTRACT='8bc35175839dc69ee4fcab618903a5043401d871f45cdfc104c88f6527834236'
THREAD_ENV={k:'2' for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS')}
THREAD_ENV.update(CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PYTHONOPTIMIZE='0')
REQUIREMENTS={'numpy':'1.24.4','torch':'2.7.0+cu126','scipy':'1.14.1','matplotlib':'3.9.2','psutil':'6.0.0','threadpoolctl':'3.5.0'}
HANDOFF=5.
class PackageError(ValueError):pass


def read(path):
    def invalid(s):raise PackageError('nonfinite JSON literal: '+s)
    return json.loads(Path(path).read_text(),parse_constant=invalid)

def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')

def sha(path,check=lambda:None):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while data:=f.read(1024*1024):check();h.update(data)
    return h.hexdigest()

def files_under(root):return sum(p.stat().st_size for p in root.rglob('*') if p.is_file())

def safe_extract(archive,target,check=lambda:None):
    """Only regular files/directories; no links or paths outside fresh source."""
    target=Path(target)
    with tarfile.open(archive,'r:gz') as tf:
        total=0
        for member in tf:
            check();parts=Path(member.name).parts
            if not parts or parts[0]!='source' or Path(member.name).is_absolute() or '..' in parts:
                raise PackageError('unsafe source member')
            if not (member.isfile() or member.isdir()):raise PackageError('source links/devices forbidden')
            total+=member.size
            if total>512*1024**2:raise PackageError('unpacked source exceeds512MiB')
            dest=target/member.name
            if member.isdir():dest.mkdir(parents=True,exist_ok=True)
            else:
                dest.parent.mkdir(parents=True,exist_ok=True)
                with tf.extractfile(member) as src,dest.open('xb') as out:
                    while data:=src.read(1024*1024):check();out.write(data)
                dest.chmod(member.mode & 0o777)

def code_tree(source,check=lambda:None):
    check();files=subprocess.check_output(['git','-C',str(source),'ls-files','SENS_tensile','scripts','tests'],text=True,timeout=getattr(check,'timeout',lambda:15.)()).splitlines()
    files=[p for p in files if p.endswith('.py')]+[
        'docs/research/S04/S04-E024/physical_field_budget_plan.md',
        'docs/research/S04/S04-E024/physical_field_budget_contract.json']
    return hashlib.sha256(json.dumps({p:sha(source/p,check) for p in sorted(files)},sort_keys=True).encode()).hexdigest()

def source_admission(source,check=lambda:None):
    check();head=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True,timeout=getattr(check,'timeout',lambda:15.)()).strip()
    check();dirty=subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True,timeout=getattr(check,'timeout',lambda:15.)())
    check()
    if head!=SCIENCE or dirty or code_tree(source,check)!=TREE:raise PackageError('source HEAD/clean/tree mismatch')

def bind_owned(child,cwd):
    """Identity of this exact fresh Popen; shared username alone is never proof."""
    import psutil
    try:
        proc=psutil.Process(child.pid)
        actual=dict(cmdline=proc.cmdline(),cwd=proc.cwd(),create_time=proc.create_time())
    except psutil.NoSuchProcess:return None
    if actual['cmdline']!=list(child.args) or Path(actual['cwd']).resolve()!=Path(cwd).resolve() or os.getpgid(child.pid)!=child.pid:
        raise PackageError('owned process cmdline/cwd/session mismatch; no kill')
    child.d013_identity=actual
    return actual


def owned_group_snapshot(child):
    """Only fresh session/group members, unique cwd, creation time and cmdline.
    Session persists with orphaned workers after its original leader exits.
    No username-based attribution, no probing other groups' command lines.
    """
    import psutil
    expected=getattr(child,'d013_identity',None)
    if expected is None:raise PackageError('missing own PID/session identity; refuse kill')
    members=[]
    for proc in psutil.process_iter(['pid']):
        try:
            if os.getpgid(proc.pid)!=child.pid or os.getsid(proc.pid)!=child.pid:continue
            if proc.status()==psutil.STATUS_ZOMBIE:continue
            actual=dict(cmdline=proc.cmdline(),cwd=proc.cwd(),create_time=proc.create_time())
            elapsed=time.time()-actual['create_time']
            if not actual['cmdline'] or actual['cwd']!=expected['cwd'] or actual['create_time']<expected['create_time'] or elapsed<0:
                raise PackageError('session member cmdline/elapsed/cwd mismatch; refuse kill')
            if proc.pid==child.pid and actual!=expected:raise PackageError('leader identity changed; refuse kill')
            # Re-read immediately so a PID replacement cannot inherit the check.
            if actual!=dict(cmdline=proc.cmdline(),cwd=proc.cwd(),create_time=proc.create_time()):
                raise PackageError('session member identity changed; refuse kill')
            members.append(dict(**actual,pid=proc.pid,elapsed_seconds=elapsed))
        except (psutil.NoSuchProcess,ProcessLookupError):continue
    return members


def terminate_owned(child):
    """Check every surviving task-session member, including orphaned workers."""
    import psutil
    members=owned_group_snapshot(child)
    if not members:return
    child.d013_pre_kill=members
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:return
    psutil.wait_procs([psutil.Process(row['pid']) for row in members if psutil.pid_exists(row['pid'])],timeout=2)
    # Leader may already be reaped; verify the surviving session again before KILL.
    survivors=owned_group_snapshot(child)
    if survivors:
        child.d013_pre_escalation=survivors
        try:os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    try:child.wait(timeout=2)
    except subprocess.TimeoutExpired:raise PackageError('own leader did not exit after cleanup')


def supervise_child(child,roots,deadline,cap=1024**3,poll=.1):
    """Watch only our new session/group; combine package/control/output archive."""
    import psutil
    observed=0;peak_archive=0;begin=time.monotonic();stop=None
    if not hasattr(child,'d013_identity'):bind_owned(child,Path.cwd())
    try:
        while child.poll() is None:
            if time.monotonic()>=deadline:raise PackageError('global3120s cumulative deadline')
            size=combined_storage(roots);peak_archive=max(peak_archive,size)
            if size>cap:raise PackageError('combined1GiB archive cap')
            try:
                process=psutil.Process(child.pid)
                for proc in [process]+process.children(recursive=True):
                    try:observed=max(observed,proc.memory_info().rss)
                    except psutil.NoSuchProcess:pass
            except psutil.NoSuchProcess:pass
            if observed>3*1024**3:raise PackageError('owned process RSS cap')
            time.sleep(min(poll,max(.001,deadline-time.monotonic())))
        size=combined_storage(roots);peak_archive=max(peak_archive,size)
        if size>cap or time.monotonic()>=deadline:raise PackageError('combined archive/global cap at completion')
        if child.returncode:raise PackageError('scientific parent exit '+str(child.returncode))
        if owned_group_snapshot(child):raise PackageError('parent exited with live owned workers')
    except BaseException as e:
        stop=str(e)
        terminate_owned(child)
        raise
    finally:
        # Kept by caller even on failure; parent science files remain untouched.
        child.d013_supervision=dict(stop=stop,wall_seconds=time.monotonic()-begin,
            observed_max_process_rss_bytes=observed,observed_combined_archive_bytes=peak_archive,
            exit_code=child.poll(),pid=child.pid,pre_kill_identity=getattr(child,'d013_pre_kill',None))
    return child.d013_supervision

def combined_storage(roots):return sum(files_under(p) for p in roots)+FIXED_LOCAL_BYTES
FIXED_LOCAL_BYTES=0


def read_json_text(value):
    return json.loads(value,parse_constant=lambda x:(_ for _ in ()).throw(PackageError('nonfinite JSON')))


def finite_number(value,name):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
        raise PackageError('invalid nonnegative '+name)
    return float(value)


def validate_auth(a):
    if a.get('user_approved_final_execution') is not True or a.get('remote_actions_authorized') is not True:
        raise PackageError('explicit final-version human approval required')
    if a.get('training_authorized') is not False or a.get('scope')!=SCOPE or a.get('package_id')!=PACK:
        raise PackageError('authority scope')
    if a.get('execution_commit')!=SCIENCE or a.get('remote_root')!=str(ROOT):raise PackageError('source/root authority')
    if not isinstance(a.get('user_approval_quote'),str) or not a['user_approval_quote'].strip():raise PackageError('human quote absent')
    for name in ('payload_sha256','payload_manifest_sha256','remote_entry_sha256','action_manifest_sha256'):
        h=a.get(name)
        if not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):raise PackageError('unbound '+name)
    finite_number(a['base_nontraining_charge_seconds'],'base charge')
    if a['base_nontraining_charge_seconds']<71.93754945798841:raise PackageError('previous cost cannot reset')
    if type(a['fixed_local_archive_bytes']) is not int or not 0<a['fixed_local_archive_bytes']<1024**3:
        raise PackageError('local archive charge')


def environment_check(actual=None):
    """Metadata policy, not a claim that this server currently meets it."""
    if actual is None:
        actual=dict(system=platform.system(),machine=platform.machine(),host=platform.node(),user=getpass.getuser(),
            executable=str(Path(sys.executable).resolve()),bound_executable=str(Path(PYTHON).resolve()),
            python=list(sys.version_info[:3]),implementation=platform.python_implementation(),
            versions={k:metadata.version(k) for k in REQUIREMENTS})
    if any(actual[k]!=v for k,v in dict(system='Linux',machine='x86_64',host='GPUServer8',user='drtao',implementation='CPython').items()):
        raise PackageError('producer host/account/platform mismatch')
    if actual['executable']!=actual['bound_executable'] or not (3,10)<=(tuple(actual['python'][:2]))<(3,13):
        raise PackageError('bound /usr/bin/python3 or supported CPython3.10..3.12 missing')
    if actual['versions']!=REQUIREMENTS:raise PackageError('dependency mismatch: no install/fallback')
    if not __debug__:raise PackageError('Python -O forbidden')
    return actual


def resource_check(check=lambda:None):
    if not os.path.ismount('/mnt/data2'):raise PackageError('data2 mount missing')
    affinity=sorted(os.sched_getaffinity(0))
    mem={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if len(line.split())>=2 and line.split()[1].isdigit()}
    check()
    disks=subprocess.run(['df','-h','/','/mnt/data2','/mnt/data3'],capture_output=True,text=True,
        timeout=getattr(check,'timeout',lambda:15.)())
    check()
    free=shutil.disk_usage('/mnt/data2').free
    if len(affinity)<2 or mem.get('MemAvailable',0)<4*1024**3 or free<2*1024**3:raise PackageError('CPU affinity/memory/disk admission')
    return dict(affinity_cpu_count=len(affinity),MemAvailable_bytes=mem['MemAvailable'],data2_free_bytes=free,
        loadavg=list(os.getloadavg()),reservation=False,GPU_queries=0,
        df_h=dict(paths=['/','/mnt/data2','/mnt/data3'],returncode=disks.returncode,stdout=disks.stdout,stderr=disks.stderr),
        note='data3 missing is recorded; data2 must be mounted, never fall back to root/home')


def budget_guard(start,used,deadline=None):
    deadline=start+300-used if deadline is None else deadline
    last=[-math.inf]
    def check():
        now=time.monotonic()
        if now>=deadline:raise PackageError('prelaunch300s cumulative deadline')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>3*1024**3:raise PackageError('deployment RSS cap')
        if now-last[0]>=.1:
            last[0]=now
            if combined_storage((ROOT,))>1024**3:raise PackageError('combined local+producer1GiB cap')
        if time.monotonic()>=deadline:raise PackageError('prelaunch deadline after storage check')
    check.timeout=lambda:min(15.,max(.001,deadline-time.monotonic()))
    return check


def anchored_deadlines(a,identity):
    """Anchor event precedes client ACK reception: this bound is early, never late.
    Both timestamps below live on this same producer's monotonic clock. Client
    elapsed at ACK receipt deliberately overcharges all transit before the ACK.
    """
    anchor=finite_number(identity['anchor_monotonic_seconds'],'producer anchor')
    if a.get('producer_anchor_monotonic_seconds')!=anchor or identity['authority']!=a['action_manifest_sha256']:
        raise PackageError('producer anchor/action mismatch')
    elapsed=finite_number(a.get('anchor_ack_client_elapsed_seconds'),'client ACK elapsed')
    base=a['base_nontraining_charge_seconds']
    if base+elapsed>=300:raise PackageError('no anchored prelaunch balance')
    return anchor+300-base-elapsed,anchor+3120-base-elapsed


def bootstrap(a,mode,create_anchor=None):
    """Only reachable after the approved client calls exact frozen SSH stdin code."""
    start=time.monotonic();validate_auth(a)
    global FIXED_LOCAL_BYTES
    FIXED_LOCAL_BYTES=a['fixed_local_archive_bytes']
    used=a['base_nontraining_charge_seconds']+finite_number(a.get('transport_charge_seconds',0),'transport charge')
    identity=read(ROOT/'bootstrap_identity.json') if mode=='start' else dict(
        anchor_monotonic_seconds=finite_number(create_anchor,'create handshake anchor'),authority=a['action_manifest_sha256'])
    deadline=anchored_deadlines(a,identity)[0]
    guard=budget_guard(start,used,deadline)
    guard();env=environment_check();guard();resources=resource_check(guard);guard()
    if mode=='create':
        if ROOT.exists() or ROOT.is_symlink():raise PackageError('fresh producer root required')
        ROOT.mkdir(mode=0o700)
        (ROOT/'DISPATCH_ONCE').mkdir()
        anchor=create_anchor
        write(ROOT/'bootstrap_identity.json',dict(environment=env,resources=resources,
            utc=datetime.now(timezone.utc).isoformat(),scope='metadata only, no Torch import',authority=a['action_manifest_sha256'],
            anchor_monotonic_seconds=anchor))
        print(json.dumps(dict(status='FRESH_ROOT_CLAIMED_NOT_SCIENCE',root=str(ROOT),
            anchor_monotonic_seconds=anchor,action_manifest_sha256=a['action_manifest_sha256'])),flush=True)
        return
    if not (ROOT/'DISPATCH_ONCE').is_dir() or (ROOT/'entry.py').exists() or (ROOT/'authorization.json').exists():
        raise PackageError('start once; no reused/ambiguous dispatch')
    wire=ROOT/'payload.tar'
    if wire.is_symlink() or sha(wire,guard)!=a['payload_sha256']:raise PackageError('uploaded payload SHA')
    with tarfile.open(wire,'r:') as tf:
        members=[m for m in tf.getmembers() if m.name=='package/remote_entry.py']
        if len(members)!=1 or not members[0].isfile() or members[0].size>100000:raise PackageError('entry member schema')
        entry=tf.extractfile(members[0]).read()
    if hashlib.sha256(entry).hexdigest()!=a['remote_entry_sha256']:raise PackageError('entry SHA')
    write(ROOT/'authorization.json',a)
    with (ROOT/'entry.py').open('xb') as f:f.write(entry)
    guard()
    envp=os.environ.copy();envp.update(THREAD_ENV)
    envp.update(TMPDIR=str(ROOT/'cache/tmp'),XDG_CACHE_HOME=str(ROOT/'cache/xdg'),MPLCONFIGDIR=str(ROOT/'cache/mpl'),
        TORCH_HOME=str(ROOT/'cache/torch'),TORCH_EXTENSIONS_DIR=str(ROOT/'cache/extensions'))
    for name in ('PYTHONPATH','PYTHONHOME'):envp.pop(name,None)
    for name in ('TMPDIR','XDG_CACHE_HOME','MPLCONFIGDIR','TORCH_HOME','TORCH_EXTENSIONS_DIR'):Path(envp[name]).mkdir(parents=True,exist_ok=True)
    write(ROOT/'SPAWN_CLAIM.json',dict(status='SPAWN_PENDING_NO_RETRY',argv=[PYTHON,str(ROOT/'entry.py'),'--run'],authority=a['action_manifest_sha256']))
    with (ROOT/'dispatcher_stdout.log').open('x') as out,(ROOT/'dispatcher_stderr.log').open('x') as err:
        guard()
        child=subprocess.Popen([PYTHON,str(ROOT/'entry.py'),'--run'],cwd=ROOT,env=envp,stdout=out,stderr=err,start_new_session=True)
    identity=bind_owned(child,ROOT)
    write(ROOT/'dispatcher_pid.json',dict(identity=identity,pid=child.pid,status='DISPATCHED_NOT_COMPLETED',cwd=str(ROOT),host=platform.node()))
    print(json.dumps(dict(status='DISPATCHED_NOT_COMPLETED',pid=child.pid,root=str(ROOT))))


def unpack_payload(wire,a,check):
    """Self-contained88 inputs: no old producer roots read or copied."""
    with tarfile.open(wire,'r:') as tf:
        meta=tf.getmember('package/payload_manifest.json')
        if not meta.isfile() or meta.size>200000:raise PackageError('manifest schema')
        raw=tf.extractfile(meta).read()
        if hashlib.sha256(raw).hexdigest()!=a['payload_manifest_sha256']:raise PackageError('payload manifest hash')
        manifest=json.loads(raw,parse_constant=lambda x:(_ for _ in ()).throw(PackageError('nonfinite manifest')))
        expected=manifest['files'];members=tf.getmembers()
        if len({m.name for m in members})!=len(members) or {m.name for m in members}!=set(expected)|{'package/payload_manifest.json'}:
            raise PackageError('payload file set/duplicates')
        for member in members:
            check();name=member.name;dest=ROOT/name
            if not member.isfile() or Path(name).is_absolute() or '..' in Path(name).parts or not dest.resolve().is_relative_to(ROOT.resolve()):
                raise PackageError('unsafe member')
            if name=='package/payload_manifest.json':identity=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            else:identity=expected[name]
            if member.size!=identity['bytes']:raise PackageError('payload member bytes')
            dest.parent.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256()
            with tf.extractfile(member) as src,dest.open('xb') as out:
                while data:=src.read(1024**2):check();digest.update(data);out.write(data)
            if digest.hexdigest()!=identity['sha256']:raise PackageError('payload member SHA')
    return manifest


def run_science():
    start=time.monotonic();a=read(ROOT/'authorization.json');validate_auth(a)
    global FIXED_LOCAL_BYTES
    FIXED_LOCAL_BYTES=a['fixed_local_archive_bytes']
    used=a['base_nontraining_charge_seconds']+finite_number(a['transport_charge_seconds'],'transport charge')
    prelaunch_deadline,global_deadline=anchored_deadlines(a,read(ROOT/'bootstrap_identity.json'))
    guard=budget_guard(start,used,prelaunch_deadline);child=None;spawn_attempted=False
    try:
        guard();env=environment_check();guard()
        if (ROOT/'RUNTIME_ONCE').exists():raise PackageError('runtime cannot restart')
        (ROOT/'RUNTIME_ONCE').mkdir()
        wire=ROOT/'payload.tar'
        if sha(wire,guard)!=a['payload_sha256']:raise PackageError('wire changed after bootstrap')
        unpack_payload(wire,a,guard)
        package=ROOT/'package';plan=read(package/'plan.json');inputs=read(package/'inputs_manifest.json')
        if plan['science_commit']!=SCIENCE or plan['science_tree_sha256']!=TREE or len(inputs['files'])!=88:
            raise PackageError('plan/input identity')
        for row in inputs['files']:
            path=ROOT/row['producer_relative_path']
            if path.stat().st_size!=row['bytes'] or sha(path,guard)!=row['sha256']:raise PackageError('staged input identity')
        source_tar=package/'science.tar.gz';safe_extract(source_tar,ROOT,guard)
        (ROOT/'source').rename(ROOT/'code');source=ROOT/'code';source_admission(source,guard)
        # Explicitly approved disposal of two exact task-owned transport copies.
        # Original inputs and retained local immutable payload are never removed.
        removed=[dict(path=str(q),bytes=q.stat().st_size,sha256=sha(q,guard)) for q in (wire,source_tar)]
        wire.unlink();source_tar.unlink();write(ROOT/'transport_copies_removed.json',removed)
        code=read(package/'receipts/code_ready.json');checks=read(package/'receipts/nontraining.json')
        if code['verdict']!='CODE_READY_PASS' or code['source_commit']!=SCIENCE or code['code_tree_sha256']!=TREE:
            raise PackageError('reused scientific CodeReady identity')
        if checks['verdict']!='NONTRAINING_CHECKS_PASS' or checks['code_tree_sha256']!=TREE or checks['wall_seconds']!=a['base_nontraining_charge_seconds']:
            raise PackageError('base nontraining identity')
        for key in ('real_model_or_FEM_forward_count','NN_optimizer_steps'):
            if checks[key]!=0:raise PackageError('nontraining scope')
        guard();handoff_start=time.monotonic();elapsed=handoff_start-start
        remaining=prelaunch_deadline-handoff_start
        if remaining<=HANDOFF:raise PackageError('no scientific handoff balance')
        conservative_charge=300-remaining+HANDOFF
        runtime_check=dict(checks,wall_seconds=conservative_charge,transport_charge_seconds=a['transport_charge_seconds'],
            producer_anchored_prelaunch_deadline=prelaunch_deadline,producer_anchored_global_deadline=global_deadline,
            producer_prelaunch_seconds=elapsed,scientific_handoff_reserved_seconds=HANDOFF,
            wall_seconds_is_conservative_budget_charge=True,producer_environment=env,
            note='Linux admission not yet scientific success; original Mac LR/mass/D/rho exceptions retained')
        cp=ROOT/'nontraining_runtime.json';write(cp,runtime_check)
        approval=dict(a,scope=SCIENCE_SCOPE,contract_sha256=CONTRACT,
            code_ready=dict(path=str(package/'receipts/code_ready.json'),sha256=sha(package/'receipts/code_ready.json',guard)),
            nontraining=dict(path=str(cp),sha256=sha(cp,guard)))
        ap=ROOT/'science_approval.json';write(ap,approval)
        project=ROOT/'project';output=project/'local_archive/experiments/S04-E024/physical_field_budget_execution_20261020_v2'
        (output.parent).mkdir(parents=True,exist_ok=True)
        if output.exists():raise PackageError('fresh scientific output required')
        command=[PYTHON,str(source/'SENS_tensile/run_s04_e024_field_budget.py'),'--execute-scientific','--project',str(project),
            '--out',str(output),'--expected-commit',SCIENCE,'--approval',str(ap)]
        write(ROOT/'SCIENCE_SPAWN_CLAIM.json',dict(status='PENDING_NO_RETRY',command=command,source=SCIENCE))
        guard()
        if time.monotonic()-handoff_start>=HANDOFF:raise PackageError('scientific handoff exhausted before spawn')
        with (ROOT/'science_stdout.log').open('x') as out,(ROOT/'science_stderr.log').open('x') as err:
            spawn_attempted=True
            child=subprocess.Popen(command,cwd=source,env=os.environ.copy(),stdout=out,stderr=err,start_new_session=True)
        identity=bind_owned(child,source)
        write(ROOT/'science_pid.json',dict(identity=identity,pid=child.pid,command=command,cwd=str(source),host=platform.node(),utc=datetime.now(timezone.utc).isoformat()))
        guard()
        if time.monotonic()-handoff_start>=HANDOFF:raise PackageError('scientific handoff exhausted')
        record=supervise_child(child,(ROOT,),global_deadline)
        write(ROOT/'supervision_exit.json',dict(**record,execution_complete=True,scientific_success_not_inferred=True))
    except BaseException as e:
        if child is not None and hasattr(child,'d013_identity'):terminate_owned(child)
        write(ROOT/'execution_failure.json',dict(error=type(e).__name__+': '+str(e),spawned_or_ambiguous=spawn_attempted,
            wall_seconds=time.monotonic()-start,no_retry=True,supervision=None if child is None else getattr(child,'d013_supervision',None)))
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    mode=p.add_mutually_exclusive_group();mode.add_argument('--bootstrap-create',action='store_true');mode.add_argument('--bootstrap-start',action='store_true');mode.add_argument('--run',action='store_true')
    args=p.parse_args()
    if not any(vars(args).values()):p.error('closed authority; explicitly approved producer action required')
    if args.run:run_science()
    elif args.bootstrap_create:
        # Before metadata imports/queries or filesystem claims, exchange an
        # anchor and its early deadline on this SAME SSH. Lost ACK => no second
        # message, no root claim, no science. No UTC clock assumptions.
        original=read_json_text(sys.stdin.readline());validate_auth(original)
        anchor=time.monotonic()
        print(json.dumps(dict(status='ANCHOR_ONLY_NO_METADATA',root=str(ROOT),
            action_manifest_sha256=original['action_manifest_sha256'],anchor_monotonic_seconds=anchor)),flush=True)
        updated=read_json_text(sys.stdin.readline())
        if any(updated.get(k)!=value for k,value in original.items()):raise PackageError('handshake changed approved authority')
        bootstrap(updated,'create',create_anchor=anchor)
    else:bootstrap(json.load(sys.stdin),'start')

if __name__=='__main__':main()
