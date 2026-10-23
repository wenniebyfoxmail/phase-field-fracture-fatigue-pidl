"""Explicit user-approved D013 resource-only runtime amendment; fail closed.
Original source18 bytes/algorithms remain unchanged. Every scientific Python
process records this overlay; time/RSS/archive ceilings are absent, not physics
or identity checks. Applied only after the approval-bound launcher admits it.
"""
import os,sys,json,hashlib,math,time
from pathlib import Path
try:
    here=Path(__file__).resolve()
    digest=hashlib.sha256(here.read_bytes()).hexdigest()
    if os.environ.get('D013_RESOURCE_POLICY_SHA256')!=digest:raise RuntimeError('resource-policy SHA mismatch')
    authority=Path(os.environ['D013_RESOURCE_POLICY_APPROVAL'])
    approved=json.loads(authority.read_text())
    if approved.get('user_approved_final_execution') is not True or approved.get('resource_limits_removed') is not True:
        raise RuntimeError('explicit unrestricted-resource approval absent')
    source=Path(os.environ['D013_SOURCE_SENS']).resolve()
    sys.path.insert(0,str(source))
    import s04_e024_field_runtime as r
    # Loader's old2GiB callback is resource accounting only, not field identity.
    import diagnose_s04_e020_features as legacy
    legacy.CAP=math.inf
    r.CAPS={k:math.inf for k in r.CAPS};r.RSS_CAP=math.inf;r.STORAGE_CAP=math.inf
    class NoResourceCeiling:
        def __init__(self,root,deadline=None,**kw):self.root=Path(root);self.deadline=None
        def __call__(self):return None
    class MeasuredPhases:
        def __init__(self,nontraining_used=0.):
            if not math.isfinite(nontraining_used) or nontraining_used<0:raise r.InvalidEvidence('nonfinite prior cost')
            self.used=dict(nontraining=float(nontraining_used),numeric=0.,replay=0.,render=0.);self.stopped=False
        def remaining(self,phase):
            if self.stopped or phase not in self.used:raise r.InvalidEvidence('invalid phase state')
            return math.inf
        def charge(self,phase,seconds):
            if phase not in self.used or not math.isfinite(seconds) or seconds<0:raise r.InvalidEvidence('invalid phase cost')
            self.used[phase]+=seconds
    r.LocalGuard=NoResourceCeiling;r.PhaseLedger=MeasuredPhases
    original_provenance=r.runtime_provenance
    def provenance():
        v=original_provenance();v['resource_policy']=dict(user_requested_no_resource_limits=True,overlay_sha256=digest,
            original_science_commit='18d0e7cb1153dc969c1ee0c21c77ada1297b2d89',time_limit_seconds=None,RSS_limit_bytes=None,
            archive_limit_bytes=None,legacy_loader_RSS_limit_bytes=None,CPU_configuration_threads=2,GPU_used=False,
            physics_and_identity_guards_unchanged=True)
        return v
    r.runtime_provenance=provenance
    def context(root,state,phase,approval,expected):
        root=Path(root);c=json.loads((root/'execution_context.json').read_text())
        if os.getppid()!=c['parent_pid'] or phase not in ('numeric','replay','render'):raise r.InvalidEvidence('worker parent/phase')
        if state!=c['active_state'] or phase!=c['active_phase']:raise r.InvalidEvidence('worker state/phase order')
        if c['approval_sha256']!=r.sha(approval):raise r.InvalidEvidence('worker approval identity')
        r.validate_approval(approval,expected)
        return NoResourceCeiling(root)
    r.worker_context=context
    def supervise(command,cwd,out_root,log_dir,seconds,rss_cap=None,storage_cap=None):
        import psutil
        log_dir=Path(log_dir);log_dir.mkdir(parents=True,exist_ok=True)
        start=time.monotonic();record=dict(command=command,timeout_seconds=None,provenance=provenance())
        r.write_json(log_dir/'command.json',record)
        env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',VECLIB_MAXIMUM_THREADS='2',NUMEXPR_NUM_THREADS='2')
        observed=0;stop=None
        with (log_dir/'stdout.log').open('w') as stdout,(log_dir/'stderr.log').open('w') as stderr:
            child=r.subprocess.Popen(command,cwd=cwd,stdout=stdout,stderr=stderr,env=env)
            try:
                while child.poll() is None:
                    try:observed=max(observed,psutil.Process(child.pid).memory_info().rss)
                    except psutil.NoSuchProcess:pass
                    time.sleep(.1)
                if child.returncode:raise r.ResourceStop('owned child exit '+str(child.returncode))
            except BaseException as e:
                stop=str(e)
                if child.poll() is None:
                    child.terminate()
                    try:child.wait(timeout=2)
                    except r.subprocess.TimeoutExpired:child.kill();child.wait()
                raise
            finally:
                record.update(pid=child.pid,exit_code=child.poll(),stop=stop,wall_seconds=time.monotonic()-start,observed_child_rss_bytes=observed)
                r.write_json(log_dir/'exit.json',record)
        return record
    r.supervise=supervise
except BaseException as error:
    print('D013 resource policy admission failed: '+repr(error),file=sys.stderr,flush=True)
    os._exit(78)
