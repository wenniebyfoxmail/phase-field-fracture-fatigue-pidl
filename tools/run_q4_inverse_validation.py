"""Bounded CPU-only full-path sensitivity validation; no optimization/training.

Controller owns one phase worker at a time and stops the whole study on its
first scientific failure. Source kernels are reused from the bound forward
owner. Every worker is process-group isolated and has Linux parent-death kill.
The controller never retries/resumes a scientific worker.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import signal
import socket
import subprocess
import sys
import time


def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.tmp')
    with temp.open('w') as f:
        json.dump(value,f,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(temp,path)


def append(path,value):
    with Path(path).open('a') as f:
        f.write(json.dumps(value,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
    return h.hexdigest()


def stop_owned(p):
    if p.poll() is None:
        os.killpg(p.pid,signal.SIGTERM)
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5)


def supervise(command,*,cwd,env,output,active,wall_seconds,step_seconds,rss_bytes,
              primary,archive,primary_cap,archive_cap):
    """No scientific semantics: bound only this newly created worker group."""
    import psutil
    start=time.monotonic();reason=None;peak=0;last_disk=0.;last_cpu=0.
    with Path(output).open('x') as log:
        p=subprocess.Popen(command,cwd=cwd,env=env,stdin=subprocess.DEVNULL,
                           stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        owned=psutil.Process(p.pid)
        try:
            while p.poll() is None:
                now=time.monotonic()
                processes=[psutil.Process(os.getpid()),owned]+owned.children(recursive=True)
                rss=0
                for proc in processes:
                    try:rss+=proc.memory_info().rss
                    except psutil.NoSuchProcess:pass
                peak=max(peak,rss)
                try:
                    cpu=owned.cpu_times();last_cpu=cpu.user+cpu.system
                except psutil.NoSuchProcess:pass
                if now-start>wall_seconds:reason='phase wall budget'
                if rss>rss_bytes:reason='owned worker RSS budget'
                if Path(active).exists():
                    state=json.loads(Path(active).read_text())
                    if state.get('computing') and now-state['start_monotonic']>step_seconds:
                        reason='physical/directional substep deadline'
                if now-last_disk>10:
                    last_disk=now
                    for directory,cap in ((primary,primary_cap),(archive,archive_cap)):
                        used=sum(x.stat().st_size for x in Path(directory).rglob('*') if x.is_file())
                        if used>cap:reason='task storage cap'
                        fs=os.statvfs(directory)
                        if fs.f_bavail*fs.f_frsize<4*1024**3:reason='filesystem reserve exhausted'
                if reason:
                    stop_owned(p);break
                time.sleep(.25)
        except BaseException:
            stop_owned(p);raise
        rc=p.wait()
    last_active=json.loads(Path(active).read_text()) if Path(active).exists() else None
    return {'pid':p.pid,'exit_code':rc,'stop_reason':reason,'wall_seconds':time.monotonic()-start,
            'sampled_worker_cpu_seconds':last_cpu,'job_rss_peak_bytes':peak,'last_active':last_active}


def phase_specs(card):
    result=[{'id':'audit','kind':'audit','hours':card['budget']['audit_hours']},
            {'id':'nominal','kind':'forward','hours':card['budget']['nominal_hours'],'log_shift':[0.,0.,0.]}]
    vectors=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.],[1/math.sqrt(3),-1/math.sqrt(3),1/math.sqrt(3)]]
    for i,v in enumerate(vectors):
        for sign in (1,-1):
            result.append({'id':f'direction_{i}_{sign:+d}','kind':'direction','hours':3.,'direction':[sign*x for x in v]})
    for i,v in enumerate(vectors):
        for sign in (1,-1):
            for h in card['study']['log_parameter_steps']:
                result.append({'id':f'perturb_{i}_{sign:+d}_{h:g}','kind':'forward','hours':20.,
                               'direction_id':f'direction_{i}_{sign:+d}','h':h,'log_shift':[sign*h*x for x in v]})
    result.append({'id':'analysis','kind':'analysis','hours':card['budget']['analysis_hours']})
    return result


def control(card_path):
    card=json.loads(Path(card_path).read_text())
    if platform.system()!='Linux' or socket.gethostname()!=card['producer']['expected_hostname']:
        raise RuntimeError('wrong producer; no fallback')
    if card['execution_authorized'] is not True or card['execution_enabled'] is not True:
        raise RuntimeError('task is not enabled')
    if card['producer']['gpu_count']!=0 or card['budget']['gpu_hours']!=0:
        raise RuntimeError('CPU-only study required')
    root=Path(card['run_root']);archive=Path(card['archive_root'])
    start=time.monotonic();epoch=time.time();phase_results=[];status='running';error=None
    with (root/'controller_reservation.json').open('x') as f:
        json.dump({'pid':os.getpid(),'epoch':epoch,'card_sha':sha(card_path)},f);f.flush();os.fsync(f.fileno())
    env=dict(os.environ,Q4_VALIDATION_PARENT_PID=str(os.getpid()),CUDA_VISIBLE_DEVICES='')
    env.update({name:str(card['producer']['cpu_threads']) for name in
                ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')})
    code=Path(__file__).resolve().parents[1]
    try:
        for spec in phase_specs(card):
            used=time.monotonic()-start
            if used>card['budget']['host_hours']*3600-card['budget']['supervision_cleanup_hours']*3600:
                raise RuntimeError('total study budget reserve reached')
            phase=root/'phases'/spec['id'];phase.mkdir(parents=True)
            (archive/spec['id']).mkdir()
            write_json(phase/'spec.json',spec)
            write_json(root/'progress.json',{'status':'running','phase':spec['id'],'controller_pid':os.getpid(),
                       'started_epoch':epoch,'elapsed_seconds':used,'completed_phases':len(phase_results)})
            row=supervise([sys.executable,'-u',str(Path(__file__).resolve()),'--worker','--card',str(card_path),'--phase',spec['id']],
                cwd=code,env=env,output=phase/'worker.log',active=phase/'active.json',
                wall_seconds=min(spec['hours']*3600,card['budget']['host_hours']*3600-used-45),
                step_seconds=card['budget']['directional_step_seconds'] if spec['kind']=='direction' else card['budget']['physical_step_seconds'],
                rss_bytes=card['budget']['rss_gib']*1024**3,primary=root,archive=archive,
                primary_cap=card['budget']['primary_gib']*1024**3,archive_cap=card['budget']['archive_gib']*1024**3)
            row.update(phase=spec['id'],kind=spec['kind'])
            if (phase/'latest.npz').exists():
                try:
                    import numpy as np
                    with np.load(phase/'latest.npz',allow_pickle=False) as saved:
                        metadata=json.loads(str(saved['metadata'].item()))
                    row['last_durable_version']=metadata['identity']['version']
                    row['last_durable_state_id']=metadata['state_id']
                except Exception as exc:row['durable_state_status']='unknown: '+type(exc).__name__
            phase_results.append(row)
            append(root/'cost_ledger.jsonl',row)
            import shutil
            for name in ('worker.log','work.jsonl','iterations.jsonl','failure.json','active.json','states.jsonl','receipts.jsonl'):
                if (phase/name).exists():shutil.copy2(phase/name,archive/spec['id']/name)
            if row['exit_code']!=0 or row['stop_reason']:
                if (phase/'latest.npz').exists():shutil.copy2(phase/'latest.npz',archive/spec['id']/'last_durable.npz')
                raise RuntimeError('first phase failure: '+spec['id']+': '+str(row['stop_reason']))
            receipt=phase/'result.json'
            if not receipt.exists() or json.loads(receipt.read_text()).get('completed') is not True:
                raise RuntimeError('phase returned without completed receipt')
        status='completed'
    except BaseException as exc:
        status='stopped';error=f'{type(exc).__name__}: {exc}'
    finally:
        final={'status':status,'error':error,'controller_pid':os.getpid(),'start_epoch':epoch,
               'wall_seconds':time.monotonic()-start,'phases':phase_results,'scientific_retry':False,'gpu_seconds':0}
        write_json(root/'terminal.json',final);write_json(root/'progress.json',final)
        import shutil
        for name in ('terminal.json','progress.json','cost_ledger.jsonl'):
            if (root/name).exists():shutil.copy2(root/name,archive/name)
    return 0 if status=='completed' else 1


def worker(card_path,phase_id):
    # Install orphan protection before numerical imports or physical work.
    if platform.system()!='Linux':raise RuntimeError('producer worker is Linux-only')
    import ctypes
    expected=int(os.environ['Q4_VALIDATION_PARENT_PID'])
    if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGKILL,0,0,0)!=0 or os.getppid()!=expected:
        raise RuntimeError('cannot bind live controller')
    os.nice(10)
    card=json.loads(Path(card_path).read_text())
    allowed=card['producer'].get('cpu_affinity',sorted(os.sched_getaffinity(0))[:card['producer']['cpu_threads']])
    if len(allowed)>card['producer']['cpu_threads']:raise RuntimeError('CPU affinity exceeds budget')
    os.sched_setaffinity(0,set(allowed))
    import shutil
    import numpy as np
    from dataclasses import replace
    from hybrid_inputs import load_backend,read_manifest,blocked_to_interleaved
    from hybrid_incremental import NativeQ4Backend,SolverSettings,solve_step
    from hybrid_coupled_acceleration import CouplingSettings
    from hybrid_transaction import StateStore
    from hybrid_work_trace import PersistentWorkTrace
    from q4_inverse_derivatives import Material,Q4Residual,ImplicitStep,NonregularBranch
    from q4_inverse_trajectory import SensitivityTape,DirectionalTransitionProblem
    from q4_inverse_sparse import SparseLimits,SparseSensitivityProvider
    from q4_inverse_switch import DirectionalSolver,SwitchLimits
    card=json.loads(Path(card_path).read_text());root=Path(card['run_root']);archive=Path(card['archive_root'])
    phase=root/'phases'/phase_id;spec=json.loads((phase/'spec.json').read_text())
    archived=archive/phase_id;archived.mkdir(exist_ok=True)
    start=time.monotonic();steps=0
    def save(name,value):
        write_json(phase/name,value);shutil.copy2(phase/name,archived/name)
    def active(index,kind,computing=True):
        write_json(phase/'active.json',{'step':index,'kind':kind,'computing':computing,'start_monotonic':time.monotonic(),'steps_completed':steps})
    def copy(path):shutil.copy2(path,archived/path.name)
    def point_observation(backend,state):
        from damage_conditioned_equilibrium import equilibrium_internal_force
        force=equilibrium_internal_force(backend.kin,state.damage,state.displacement,**backend.material)
        y=backend.kin.points[:,1];bottom=np.flatnonzero(y==y.min());ids=2*bottom+1
        return float(-force[ids].sum())
    try:
        backend,old,dofs,bc=load_backend(root/'inputs',read_manifest(root/'inputs/inputs.json'))
        material=dict(read_manifest(root/'inputs/inputs.json')['material'])
        settings=SolverSettings(**card['solver']);coupling=CouplingSettings(**card['coupling'])
        nominal=root/'phases/nominal'
        points=backend.kin.points;span=np.ptp(points,axis=0);sensors=[]
        for x in (.2,.4,.6,.8):
            for y in (.2,.4,.6,.8):
                target=points.min(axis=0)+np.array([x,y])*span
                node=int(np.argmin(np.sum(((points-target)/span)**2,axis=1)))
                sensors.extend([2*node,2*node+1])
        sensors=np.setdiff1d(np.unique(sensors),dofs)
        if spec['kind']=='audit':
            import h5py
            with h5py.File(root/'inputs/common_common_initial.mat') as f:
                common=f['common'];history=np.asarray(common['history']).transpose(2,1,0)
                comparisons={'u':(old.displacement,blocked_to_interleaved(np.asarray(common['u']).ravel())),
                    'd':(old.damage,np.asarray(common['d']).ravel()),'lower':(old.damage,np.asarray(common['lower']).ravel()),
                    'A':(old.accumulated,history[:,:,1]),'q':(old.driver,history[:,:,2]),
                    'f':(old.fatigue,history[:,:,3]),'opaque':(old.opaque,history[:,:,0])}
                errors={k:float(np.max(abs(a-b),initial=0)) for k,(a,b) in comparisons.items()}
            if max(errors.values())>card['initial_audit']['maximum_absolute_difference']:
                raise RuntimeError('prepared/common initial array mismatch; no repair')
            if (np.any(old.displacement!=0) or np.any(old.accumulated!=0) or np.any(old.driver!=0) or np.any(old.fatigue!=1)):
                raise RuntimeError('initial zero-history/fatigue convention mismatch')
            if old.damage.size!=86756 or len(backend.kin.cells)!=86408:
                raise RuntimeError('native mesh shape mismatch')
            save('audit.json',{'initial_absolute_errors':errors,'state0_id':old.fingerprint(),
                 'mesh_id':backend.mesh_id,'physics_id':backend.physics_id,'fresh_initial_reaction':point_observation(backend,old),
                 'legacy_cached_reaction_equivalence':'not required as synthetic target; remains unverified',
                 'recovery_differentiated':False,'displacement_sensor_dofs':sensors.tolist()})
        elif spec['kind']=='forward':
            physical=np.array([material['youngs_modulus'],material['gc'],material['alpha_t']])*np.exp(spec['log_shift'])
            material.update(youngs_modulus=float(physical[0]),gc=float(physical[1]),alpha_t=float(physical[2]))
            backend=NativeQ4Backend(backend.kin,backend.crack,**material)
            old=replace(old,physics_id=backend.physics_id)
            store=StateStore(phase/'latest.npz');store.initialize(old)
            states=phase/'states';states.mkdir();shutil.copy2(store.path,states/'state0000.npz')
            target_archive=archived/'states';target_archive.mkdir();shutil.copy2(states/'state0000.npz',target_archive/'state0000.npz')
            minf=1.
            for index in range(600):
                active(index+1,'physical')
                load=card['study']['load_cycle'][index%5]*card['study']['displacement_scale']
                trace=PersistentWorkTrace(phase/'work.jsonl',phase_id,index+1)
                proposal=solve_step(backend,old,dofs,bc*load,next_load_id=f'{phase_id}:c{index//5+1}:s{index%5+1}:{load:.17g}',
                                   settings=settings,coupling=coupling,work_observer=trace.call,iteration_observer=trace.record_iteration)
                store.commit(proposal);old=proposal.state;steps+=1
                path=states/f'state{index+1:04d}.npz';shutil.copy2(store.path,path);shutil.copy2(path,target_archive/path.name)
                minf=min(minf,float(old.fatigue.min()))
                row={'step':index+1,'cycle':index//5+1,'substep':index%5+1,'load':load,'state_id':old.fingerprint(),
                     'certificate':proposal.certificate,'reaction':point_observation(backend,old),'f_min':float(old.fatigue.min())}
                append(phase/'states.jsonl',row);active(index+1,'io',False)
            copy(phase/'states.jsonl')
            if phase_id=='nominal' and minf>=1.:
                raise RuntimeError('complete nominal path has no f<1 support; no amplitude substitution')
        elif spec['kind']=='direction':
            m=Material(**material);base=np.array([m.youngs_modulus,m.gc,m.alpha_t]);direction=base*np.array(spec['direction'])
            tape=SensitivityTape(old,Q4Residual(backend.kin,m,old).zero_variation(),initial_binding_id=old.fingerprint(),
                                 initialization_policy='fixed_recovered_profile',parameter_direction=direction)
            targets=phase/'tangents';targets.mkdir();archived_tangents=archived/'tangents';archived_tangents.mkdir()
            s=card['sensitivity']
            for index in range(1,601):
                active(index,'directional')
                previous_variation=tape.variation
                new,_=StateStore(nominal/'states'/f'state{index:04d}.npz').load()
                r=Q4Residual(backend.kin,m,tape.state)
                limit=SparseLimits(max_unknowns=3*len(new.damage),max_elements=len(backend.kin.cells),
                    max_matrix_nnz=s['max_matrix_nnz'],max_factor_nnz=s['max_factor_nnz'],
                    max_product_work=s['max_product_work'],chunk_elements=s['chunk_elements'],wall_seconds=60.)
                try:
                    step=ImplicitStep(r,new.displacement,new.damage,dofs,force_tolerance=settings.force_tolerance,damage_tolerance=settings.damage_tolerance)
                except NonregularBranch:
                    problem=DirectionalTransitionProblem(r,new.displacement,new.damage,dofs,force_tolerance=settings.force_tolerance,
                        damage_tolerance=settings.damage_tolerance,force_scale=settings.force_scale,
                        damage_scale=settings.damage_gradient_scale,history_scale=1.)
                    size=len(problem.free_u)+np.count_nonzero(problem.interior|problem.weak_lower|problem.weak_upper)
                    solver=DirectionalSolver(problem,row_scale=np.ones(size)*s['row_scale'],column_scale=np.ones(size)*s['column_scale'],
                        uniqueness_weights=np.ones(size),limits=SwitchLimits(limit,s['max_iterations'],s['max_backtracks']),
                        minimum_monotonicity=s['minimum_monotonicity'],minimum_reciprocal_bound=s['minimum_reciprocal_condition'],
                        uniqueness_method=s['uniqueness_method'])
                    receipt=tape.advance_switch_given(solver,new,expected_load_id=new.load_id,transition_tolerance=settings.fatigue_tolerance,
                        residual_tolerance=s['residual_tolerance'],solution_tolerance=s['solution_tolerance'])
                else:
                    provider=None if step.size==0 else SparseSensitivityProvider(step,row_scale=np.ones(step.size)*s['row_scale'],
                         column_scale=np.ones(step.size)*s['column_scale'],limits=limit)
                    def empty(*a):raise AssertionError('empty system must not invoke a solver')
                    receipt=tape.advance_given(step,new,expected_load_id=new.load_id,transition_tolerance=settings.fatigue_tolerance,
                        solve=empty if provider is None else provider,regularity=None if provider is None else provider.evidence,
                        linear_tolerance=s['linear_tolerance'],minimum_scaled_singular_value=s['minimum_scaled_singular_value'],
                        minimum_reciprocal_condition=s['minimum_reciprocal_condition'])
                    receipt['regularity']=None if provider is None else provider.record
                out=r.directional(new.displacement,new.damage,tape.variation.displacement,tape.variation.damage,
                                  old_variation=previous_variation,parameters=direction,strict=False)
                bottom=2*np.flatnonzero(points[:,1]==points[:,1].min())+1
                reaction=float(-out.force[bottom].sum())
                append(phase/'receipts.jsonl',receipt)
                path=targets/f'direction{index:04d}.npz'
                with path.open('wb') as f:
                    np.savez(f,**vars(tape.variation),fatigue=out.fatigue,reaction=np.array(reaction),
                             sparse_displacement=tape.variation.displacement[sensors])
                shutil.copy2(path,archived_tangents/path.name);steps+=1;active(index,'io',False)
            copy(phase/'receipts.jsonl')
        else:
            # The study never promotes FD agreement alone to the planned claim.
            # Trustworthy nonlinear forward error bounds are a separate required
            # evidence quantity, not manufactured from a small solver residual.
            comparisons=[]
            nominal_rows=[json.loads(line) for line in (nominal/'states.jsonl').read_text().splitlines()]
            for candidate in phase_specs(card):
                if candidate['kind']!='forward' or candidate['id']=='nominal':continue
                errors=[]
                candidate_rows=[json.loads(line) for line in (root/'phases'/candidate['id']/'states.jsonl').read_text().splitlines()]
                for index in range(1,601):
                    base,_=StateStore(nominal/'states'/f'state{index:04d}.npz').load()
                    pert,_=StateStore(root/'phases'/candidate['id']/'states'/f'state{index:04d}.npz').load()
                    with np.load(root/'phases'/candidate['direction_id']/'tangents'/f'direction{index:04d}.npz') as t:
                        row={key:float(np.linalg.norm((getattr(pert,key)-getattr(base,key))/candidate['h']-t[key]))
                             for key in ('displacement','damage','accumulated','driver','fatigue')}
                        row['reaction']=float(abs((candidate_rows[index-1]['reaction']-nominal_rows[index-1]['reaction'])/candidate['h']-t['reaction']))
                        row['sparse_displacement']=float(np.linalg.norm((pert.displacement[sensors]-base.displacement[sensors])/candidate['h']-t['sparse_displacement']))
                    row.update(step=index,h=candidate['h']);errors.append(row)
                write_json(phase/(candidate['id']+'_errors.json'),errors)
                comparisons.append({'path':candidate['id'],'h':candidate['h'],'maximum_error':max(max(row[k] for k in ('displacement','damage','accumulated','driver')) for row in errors)})
                shutil.copy2(phase/(candidate['id']+'_errors.json'),archived/(candidate['id']+'_errors.json'))
            save('comparison.json',{'comparisons':comparisons,'scientific_verdict':'inconclusive',
                  'reason':'trustworthy nonlinear forward field/observation error bounds are not provided by the current forward owner; FD mismatch and branch coverage are reported without a complete-path PASS'})
        save('result.json',{'completed':True,'phase':phase_id,'kind':spec['kind'],'steps':steps,
                           'wall_seconds':time.monotonic()-start,'gpu_seconds':0})
    except BaseException as exc:
        import traceback
        details={'completed':False,'phase':phase_id,'steps_completed':steps,'error':f'{type(exc).__name__}: {exc}',
                 'traceback':traceback.format_exc(),'wall_seconds':time.monotonic()-start}
        if hasattr(exc,'work'):details['work']=exc.work
        if hasattr(exc,'evidence'):details['evidence']=exc.evidence
        save('failure.json',details)
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--card',required=True);p.add_argument('--worker',action='store_true');p.add_argument('--phase')
    args=p.parse_args()
    return worker(args.card,args.phase) if args.worker else control(args.card)


if __name__=='__main__':sys.exit(main())
