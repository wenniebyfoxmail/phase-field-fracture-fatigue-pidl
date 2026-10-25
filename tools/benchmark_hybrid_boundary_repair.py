"""One paired frozen-R10 LS benchmark on Taobo; no new physical solve or fit."""
import os
import resource
from pathlib import Path
import signal
import socket
import sys
from time import perf_counter,process_time

if __name__=='__main__':
    if socket.gethostname()!='GPUServer8':raise RuntimeError('frozen project model benchmark is producer-only')
    os.environ['CUDA_VISIBLE_DEVICES']=''
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:4]))
    resource.setrlimit(resource.RLIMIT_AS,(30*2**30,30*2**30))
    def deadline(sig,frame):raise RuntimeError('300s saved-model benchmark cap')
    signal.signal(signal.SIGALRM,deadline);signal.alarm(300)

import json
import numpy as np
from scipy import sparse
from hybrid_inputs import sha256,read_manifest
from hybrid_producer_common import write_json,verify_package
from hybrid_box_residual_subproblem import Model,Budget,solve_box_model


def main():
    wall=perf_counter();cpu=process_time()
    root=Path(sys.argv[1]).resolve();old=Path('/mnt/data2/drtao/wennie/pf_hybrid_d21_complete_20261025_r10')
    archive=Path('/mnt/data2/drtao/pidl_archives')/old.name
    result_path=root/'boundary_benchmark.json'
    if result_path.exists():raise FileExistsError('one fixed benchmark; preserve prior result')
    package=read_manifest(root/'source_manifest.json');verify_package(root/'code',package)
    card=read_manifest(root/'execution_card.json')
    if card.get('boundary_repair')!='projected_path_v1':raise RuntimeError('wrong repair policy')
    terminal=read_manifest(old/'terminal.json')
    if terminal['status']!='failed':raise RuntimeError('R10 not terminal')
    folder=archive/'train_A/unaccepted_work_points';modelpath=folder/'last_box_model.npz'
    directionpath=folder/'last_block_direction.npz'
    statepath=old.parent/'pf_hybrid_solver_v6_20261020_r3/inputs/state0.npz'
    meshpath=statepath.with_name('mesh.npz')
    with np.load(modelpath,allow_pickle=False) as z:
        J=sparse.csc_matrix((z['J_data'],z['J_indices'],z['J_indptr']),shape=tuple(z['J_shape']))
        F=z['original_F'];w=z['row_weights'];D=z['D'];base=dict(u=z['base_u'],d=z['base_d']);meta=json.loads(str(z['metadata']))
    with np.load(meshpath,allow_pickle=False) as z:
        dofs=z['bc_dofs'];crack=z['crack'].astype(bool)
    with np.load(statepath,allow_pickle=False) as z:lower=z['damage']
    free=np.flatnonzero(~np.isin(np.arange(len(base['u'])),dofs));values=base['u'][dofs].copy()
    with np.load(directionpath,allow_pickle=False) as z:
        keys=z.files
        # block_direction evidence stores the original free-u/d Newton vector.
        vectors={k:z[k] for k in keys if k!='metadata'}
    if not {'delta_u_free','delta_damage','free_dofs'}<=set(vectors):raise RuntimeError('saved direction keys differ: '+str(keys))
    if not np.array_equal(free,vectors['free_dofs']):raise RuntimeError('saved free DOF ordering differs')
    newton=np.r_[vectors['delta_u_free'],vectors['delta_damage']]
    if J.shape!=(len(F),len(free)+len(lower)) or newton.shape!=D.shape:
        raise RuntimeError('saved original free-u/d ordering differs')
    summaries={};events={}
    for label,solver in [('original','active_face_cg'),('projected','active_face_projected_cg')]:
        steps=[]
        def observe(name,p,best,info):
            if name=='Krylov_before_model':steps.append({k:info[k]for k in ('iteration','alpha','alpha_cg','alpha_bound','free_components')})
        budget=Budget(actions=100,updates=16);model=Model(J,F,w,D,budget)
        tick=perf_counter()
        point=solve_box_model(model,base,free,dofs,values,lower,crack,.1,newton,solver=solver,
                              stage_observer=observe,krylov_steps=8)
        summaries[label]={k:point.get(k)for k in ('pred_lower','pred_upper','model_value','cauchy_pred_lower',
            'selection','krylov_status','krylov_iterations','actual_TR_norm','action_count_upper','subproblem_updates')}
        summaries[label].update(wall_seconds=perf_counter()-tick,feasible=True,
            Cauchy_protected=point['pred_lower']>=point['cauchy_pred_lower'])
        events[label]=steps
    passed=(summaries['projected']['pred_lower']>summaries['original']['pred_upper']
        and all(r['Cauchy_protected']and r['actual_TR_norm']<=.1 and r['action_count_upper']<=100
                and r['subproblem_updates']<=16 for r in summaries.values()))
    report=dict(schema='d21-boundary-fixed-benchmark-v1',passed=bool(passed),artifact_id=package['artifact_id'],
        source_commit=package['source_commit'],source_model=str(modelpath),source_model_sha256=sha256(modelpath),
        source_direction_sha256=sha256(directionpath),model_metadata=meta,shape=list(J.shape),nnz=J.nnz,
        original=summaries['original'],projected=summaries['projected'],events=events,
        new_FEM_states=0,training_updates=0,GPU_seconds=0,wall_seconds=perf_counter()-wall,
        cpu_seconds=process_time()-cpu,maximum_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        scope='same frozen originalLS model only; not physical convergence or qualified labels')
    write_json(result_path,report);print(json.dumps(report),flush=True)
    if not passed:raise SystemExit(2)


if __name__=='__main__':main()
