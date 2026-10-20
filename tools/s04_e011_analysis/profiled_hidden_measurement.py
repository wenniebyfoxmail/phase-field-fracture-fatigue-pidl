"""One authorized measurement panel, no optimization promotion/history/rollout.

A is unchanged Runtime.trial. B is only the anchored chart's field family.
Imports of real objects happen only inside run(), behind producer start gate.
"""
from pathlib import Path
import json,time

PANEL=[('zero',0.,False),('plus_h',1e-6,True),('minus_h',-1e-6,True),
       ('plus_half',5e-7,True),('minus_half',-5e-7,True),
       ('plus_repeat',1e-6,False),('minus_repeat',-1e-6,False)]


def comparison(np,predicted,plus,minus,h):
    fd=(plus-minus)/(2*h);difference=predicted-fd
    error=float(np.linalg.norm(difference));scale=max(float(np.linalg.norm(predicted)),float(np.linalg.norm(fd)))
    tolerance=1e-10+1e-4*scale
    if not np.isfinite([error,scale,tolerance]).all():raise RuntimeError('nonfinite_measurement_comparison')
    return dict(h=h,error=error,scale=scale,tolerance=tolerance,ratio=error/tolerance,original_gate_passed=error<=tolerance),fd,difference


def chart_components(torch,bridge,features):
    """Use ONLY A's retained feature tensor and original fixed anchored map."""
    with torch.no_grad():
        design=bridge.load*bridge.bubble[:,None]*torch.cat((features,torch.ones((bridge.n,1),device=features.device,dtype=features.dtype)),dim=1)
        phi=bridge.phi+(design-bridge.raw0)@bridge.T
        raw=features@bridge.head[:,:-1].T+bridge.head[:,-1]
        u=(bridge.bubble*raw[:,0]+(bridge.x[:,-1]-bridge.y0)/(bridge.yL-bridge.y0)*torch.cos(bridge.angle))*bridge.load
        v=(bridge.bubble*raw[:,1]+(bridge.x[:,-1]-bridge.y0)/(bridge.yL-bridge.y0)*torch.sin(bridge.angle))*bridge.load
    return phi,u,v


def run(card,root,archive,reporter,started):
    import shutil,sys
    import numpy as np
    import torch
    import run_pidl_persisted_phi_hidden_newton as base
    from profiled_hidden_adapter import Guard
    from profiled_hidden_e011_runtime import Runtime,startup_checks,verify_source_assets,tensor_identity
    from profiled_hidden_receipts import ProfileCheckRecorder,atomic_json,trial_metadata
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1:raise RuntimeError('one CUDA device required')
    # Independent driver UUID check: CUDA logical0 must be physical authorized UUID.
    import ctypes,uuid
    lib=ctypes.CDLL('libcuda.so.1');device=ctypes.c_int();raw=(ctypes.c_ubyte*16)()
    if lib.cuInit(0) or lib.cuDeviceGet(ctypes.byref(device),0) or lib.cuDeviceGetUuid_v2(ctypes.byref(raw),device):raise RuntimeError('CUDA UUID verification failed')
    actual='GPU-'+str(uuid.UUID(bytes=bytes(raw)))
    if actual!=card['producer']['gpu_uuid']:raise RuntimeError('CUDA physical UUID differs')
    torch.cuda.init();device=torch.device('cuda:0')
    import resource,os
    atomic_json(archive/'runtime_versions.json',dict(python=sys.version,torch=torch.__version__,numpy=np.__version__,GPU_UUID=actual,CPU_affinity=sorted(os.sched_getaffinity(0)),RLIMIT_AS=resource.getrlimit(resource.RLIMIT_AS)))
    reporter.cuda=lambda:(torch.cuda.max_memory_allocated(0),torch.cuda.max_memory_reserved(0))
    guard=Guard(card['work_caps'],600.,memory=reporter.ratio,max_bytes=1.);guard.start=started
    inputs=root/'inputs';inputs.mkdir();paths={r['role']:r['source'] for r in card['input_bindings']}
    atomic_json(archive/'source_assets.json',verify_source_assets(card,paths,guard))
    staged={}
    for item in card['input_bindings']:
        src=Path(item['source']);target=inputs/(item['role']+src.suffix)
        if src.is_symlink():raise RuntimeError('input symlink')
        with src.open('rb') as a,target.open('xb') as b:shutil.copyfileobj(a,b,1048576)
        staged[item['role']]=str(target);guard.check()
    verify_source_assets(card,staged,guard)
    p=base.LocalProblem(dict(np.load(staged['input'],allow_pickle=False)),device)
    original=torch.load(staged['original_model'],map_location=device,weights_only=True)
    initial=torch.load(staged['initial_model'],map_location=device,weights_only=True)
    guard.charge('raw_feature_forward');field=base.make_smooth(original,p);field.net.load_state_dict(initial);field.net.requires_grad_(False)
    source=base.snapshot(field.net);source_id=tensor_identity(source)
    head=torch.cat((field.net.output_layer.weight[:2],field.net.output_layer.bias[:2,None]),dim=1).cpu().numpy()
    space=base.load_actual_space(staged['source_phi'],staged['source_transform'],head,device,p.n)
    base.persist_space(space,archive/'initial_basis',field,staged['source_phi'],staged['source_transform'])
    budget=base.phase_budget(archive,'production',started);budget.cap=500;budget.seconds=600.
    work=base.PhaseWork(budget);(archive/'readouts').mkdir()
    for _ in range(4):guard.charge('energy_force_field')
    atomic_json(archive/'native_operator.json',p.contract())
    rt=Runtime(field,p,space,budget,work,archive/'point_0',guard)
    rec=ProfileCheckRecorder(archive/'measurement_audit',dict(science='new measurement only, R2 remains failed',
        source_identity=source_id,actual_GPU_UUID=actual,old_gate='abs1e-10+rel1e-4 L2 free DOFs',B_is_actual_NN=False))
    def observe_trace(tr):p.measurement_trace=tr.detach().clone()
    p.trace_observer=observe_trace
    captured={}
    def observe_features(features):
        if 'features' in captured:raise RuntimeError('extra feature capture')
        captured['features']=features.detach()  # retain already-computed tensor
    work.feature_observer=observe_features
    A={};B={};predicted=None;completed=False;rows=[];pairs_done=set()
    try:
        source_fields=dict(np.load(staged['source_fields'],allow_pickle=False))
        source_full=np.concatenate((source_fields['u'],source_fields['v']))
        startup_checks(rt,source_fields)
        algebra=rt.form_chart();q0=rt.point_q
        v=np.random.default_rng(173).normal(size=algebra.parameters);v/=np.linalg.norm(v)
        rec('source',dict(rank=rt.root_rank,E=rt.root_E,Ru=rt.root_Ru),dict(q0=q0,v=v,
            free_dofs=p.fu.cpu().numpy(),parameter_scales=rt.bridge.scales.cpu().numpy(),captured_head=rt.bridge.head.cpu().numpy(),trace_sign=torch.sign(p.measurement_trace).to(torch.int8).cpu().numpy()))
        predicted=algebra.q(v)  # EXACTLY ONCE; no qt/witness/optimizer policy
        rec('prediction',{},dict(Qv=predicted))
        def save_available_pairs():
            for arm,values,sets in [('A',A,[('h','plus_h','minus_h',1e-6),('half','plus_half','minus_half',5e-7),('repeat','plus_repeat','minus_repeat',1e-6)]),('B',B,[('h','plus_h','minus_h',1e-6),('half','plus_half','minus_half',5e-7)])]:
                for name,plus,minus,h in sets:
                    if (arm,name) in pairs_done or plus not in values or minus not in values:continue
                    row,fd,diff=comparison(np,predicted,values[plus],values[minus],h);row.update(arm=arm,pair=name)
                    rec('comparison',row,dict(FD=fd,difference=diff));rows.append(row);pairs_done.add((arm,name))
        for label,step,do_B in PANEL:
            guard.check();captured.clear();delta=step*v
            rec('side_start',dict(label=label,step=step,arm='A'),dict(delta=delta))
            out=rt.trial(delta)
            rec('side_returned',dict(label=label,arm='A',**trial_metadata(out)),dict(q_raw=out['q'],
                trace_sign=torch.sign(p.measurement_trace).to(torch.int8).cpu().numpy()))
            for key in ['actual_nn','full_current_basis','persisted_actual_phi','frozen_state','fixed_state','rolled_back','finite']:
                if out.get(key) is not True:raise RuntimeError('A_contract_'+key)
            if out['rank']!=rt.root_rank or out['head_gradient_inf']>1e-10 or out['realization_maxabs']>1e-10:raise RuntimeError('A_head_rank_realization_contract')
            A[label]=out['q'].copy();save_available_pairs()
            if do_B:
                f=captured['features'];bridge=rt.bridge
                phi,u,vv=chart_components(torch,bridge,f)
                rec('B_basis',dict(label=label,actual_NN=False,A_feature_trial=out['folder'],source_T='initial_basis/transform.npy'),dict(phi=phi.cpu().numpy()))
                folder=archive/('B_'+label);folder.mkdir();trace_cache={}
                class ChartField(base.ReducedElastic):
                    def value_gradient(self,z):
                        result=super().value_gradient(z)
                        trace_cache[np.asarray(z).tobytes()]=torch.sign(p.measurement_trace).to(torch.int8).cpu().numpy()
                        return result
                reduced=ChartField(p,phi,u,vv);tangent=base.HiddenTangent(reduced,rt.work)
                z0=np.zeros(2*rt.root_rank);e,g=base.evaluated(reduced,rt.budget,z0,'B_'+label+'_initial')
                H,tr=tangent.matrix(z0)
                contract=base.tangent_contract(reduced,tangent,H,tr,z0,rt.budget);atomic_json(folder/'tangent_contract.json',contract)
                last,accepted,solver=base.newton_solve(reduced,tangent,rt.budget,dict(z=z0,value=e,gradient=g),H)
                atomic_json(folder/'solver.json',solver)
                gu=float(np.max(abs(last['gradient'])))
                if base.hard_head_failure(solver['stop']) or not np.isfinite(gu) or gu>1e-10:raise RuntimeError('B_head_not_closed_'+solver['stop'])
                with torch.no_grad():bu,bv=reduced.fields(torch.as_tensor(last['z'],device=device,dtype=torch.float64));full=torch.cat((bu,bv)).cpu().numpy()
                q=full[p.fu.cpu().numpy()];mask=np.ones(2*p.n,dtype=bool);mask[p.fu.cpu().numpy()]=False
                bc=float(np.max(abs(full[mask]-source_full[mask])))
                if not np.isfinite(q).all() or bc>1e-12:raise RuntimeError('B_nonfinite_or_boundary')
                if tensor_identity(field.net.state_dict())!=source_id:raise RuntimeError('B_mutated_source')
                bridge.verify_frozen()
                rec('side_returned',dict(label=label,step=step,arm='B',head_gradient_inf=gu,E=last['value'],
                    rank=rt.root_rank,boundary_maxabs=bc,source_unchanged=True,actual_NN=False,solver_folder=str(folder)),
                    dict(q_raw=q,head_z=last['z'],head_gradient=last['gradient'],trace_sign=trace_cache[last['z'].tobytes()]))
                B[label]=q.copy();save_available_pairs();del reduced,tangent,H,tr,phi,f,u,vv,bu,bv,full
            captured.clear();del out
            rt.eligible_candidates.clear()  # none may be promoted; release trial tensors
            atomic_json(archive/(label+'_progress.json'),dict(A=list(A),B=list(B),counts=guard.counts))
            guard.check()
        repeat=((A['plus_repeat']-A['minus_repeat'])-(A['plus_h']-A['minus_h']))/(2e-6)
        result=dict(status='MEASUREMENT_COMPLETE_NO_OPTIMIZATION',source_identity=source_id,rows=rows,
            fresh_zero_shift_L2=float(np.linalg.norm(A['zero']-q0)),fresh_zero_shift_maxabs=float(np.max(abs(A['zero']-q0))),
            repeat_FD_difference_L2=float(np.linalg.norm(repeat)),Qv_norm=float(np.linalg.norm(predicted)),
            counts=guard.counts,scientific_elapsed_seconds=time.monotonic()-started,A_maps=len(A),B_maps=len(B),
            optimization_updates=0,history_commits=0,rollout=0,capacity_certificate=False,old_R2_outcome_changed=False)
        rec('panel_complete',result,dict(repeat_FD_difference=repeat));atomic_json(archive/'measurement_result.json',result);completed=True
        return result
    finally:
        rt.close();field.net.load_state_dict(source);rt.bridge.verify_frozen()
        atomic_json(archive/'measurement_terminal.json',dict(completed=completed,source_restored=tensor_identity(field.net.state_dict())==source_id,
            A_maps=len(A),B_maps=len(B),completed_pairs=rows,counts=guard.counts,elapsed_seconds=time.monotonic()-started,optimization_updates=0))
