"""Reviewed producer worker: complete trajectories, one fit and fixed evaluation.

Never invoke on Mac. The external supervisor supplies hard time/RAM/storage
caps and owns child termination. Scientific phases do not retry or resume.
"""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import platform
import resource
import shutil
from time import perf_counter, time

if __name__ == '__main__':
    # Even an uncatchable watchdog death must not leave a computing orphan.
    # Bind BEFORE heavy numerical imports; race is closed by checking PPID
    # after installing the Linux parent-death signal.
    if platform.system()!='Linux':raise RuntimeError('producer workers are Linux-only')
    if 'HYBRID_WORKER_AS_BYTES' in os.environ:
        cap=int(os.environ['HYBRID_WORKER_AS_BYTES'])
        if cap!=30*2**30:raise RuntimeError('CPU worker AS partition differs')
        resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
    if 'HYBRID_PHASE_CPU_CORES' in os.environ:
        cores=int(os.environ['HYBRID_PHASE_CPU_CORES'])
        if cores not in (4,16):raise RuntimeError('unexpected phase CPU cap')
        os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:cores]))
    import ctypes
    import signal
    expected=int(os.environ['HYBRID_SUPERVISOR_PID'])
    if ctypes.CDLL(None,use_errno=True).prctl(1,signal.SIGTERM,0,0,0)!=0:
        raise RuntimeError('cannot install parent-death safeguard')
    if os.getppid()!=expected:raise RuntimeError('supervisor changed before worker admission')
    gate=int(os.environ['HYBRID_START_FD'])
    if os.read(gate,1)!=b'1':raise RuntimeError('deadline guardian did not admit worker')
    os.close(gate)

import numpy as np

from hybrid_inputs import load_backend, read_manifest, sha256
from hybrid_incremental import SolverSettings, solve_step, StepFailure
from hybrid_producer_common import write_json, append_event, classical_guess, compare_states,object_sha,lossless_snapshot
from hybrid_transaction import StateStore
from hybrid_work_trace import PersistentWorkTrace
from hybrid_guard_client import notify
from hybrid_coupled_acceleration import CouplingSettings
from hybrid_state_contract import (CONTRACT_ID, FEATURE_TIMING, step_context,
                                   bind_proposal, verify_expected, verify_transition,
                                   verify_comparable)


def coupling_identity(card):return object_sha(asdict(CouplingSettings(**card.get('coupling',{}))))


def verify_label_coupling(row,expected):
    if row.get('coupling_policy_id')!=expected or row['certificate'].get('coupling_policy_id')!=expected:
        raise RuntimeError('label coupling policy differs from complete comparison')


def verify_label_feature_arrays(backend,old,new,z,dofs,values,expected_predictor_hash):
    from hybrid_network import features_for
    recomputed=features_for(backend,old,z['u_pred'],z['psi_pred'],dofs,values)
    pred_hash=__import__('hashlib').sha256(z['u_pred'].tobytes()+z['psi_pred'].tobytes()).hexdigest()
    if (not np.array_equal(z['x'],recomputed.astype(np.float32))
            or not np.array_equal(z['d_old'],old.damage.astype(np.float32))
            or not np.array_equal(z['d_target'],new.damage.astype(np.float32))
            or pred_hash!=expected_predictor_hash):
        raise RuntimeError('label feature/target timing or predictor evidence mismatch')


def marker(out, **values):
    notify("step_start",values["step"])
    write_json(Path(out) / "active_step.json", dict(start_epoch=time(),start_monotonic=perf_counter(), **values))


def trajectory_storage_check(card,out,archive,headroom=False):
    if card.get('schema')not in ('hybrid-cpu-trajectory-v7','hybrid-cpu-trajectory-v8','hybrid-cpu-trajectory-v9','hybrid-cpu-trajectory-v10','hybrid-cpu-trajectory-v11','hybrid-cpu-trajectory-v12','hybrid-execution-card-v1'):return
    # One scan at step boundaries, not every element/operator call. The live
    # supervisor also scans and final completion has an independent last check.
    from run_hybrid_producer import bytes_under
    primary=bytes_under(out);used=bytes_under(archive)
    reserve=128*2**20 if headroom else 0
    if (primary>card['budget']['primary_gib']*2**30-16*2**20
            or used>card['budget']['archive_gib']*2**30-reserve):
        raise RuntimeError('trajectory storage cap/headroom exhausted')


def trajectory(card, spec, inputs, out, archive):
    backend, old, dofs, bc = load_backend(inputs, read_manifest(Path(inputs)/"inputs.json"))
    settings = SolverSettings(**card["solver"])
    coupling=CouplingSettings(**card.get('coupling',{}));coupling_id=coupling_identity(card)
    phase = archive / spec["id"]
    phase.mkdir()
    (phase/"states").mkdir()
    if coupling.mode in ('guarded_vi_newton','guarded_block_newton','joint_projected_trust','box_residual_trust'):
        def save_work_point(tag,point):
            import tempfile
            folder=phase/'unaccepted_work_points';folder.mkdir(exist_ok=True)
            fd,name=tempfile.mkstemp(prefix='.point-',suffix='.npz',dir=folder)
            try:
                metadata=dict(classification='UNACCEPTED_SOLVER_WORK_POINT_NOT_LABEL',
                    tag=tag,outer=point['outer'],m_work=point['m_work'],m_accept=point['m_accept'],
                    parent_id=point['previous_id'],load_id=point['load_id'],
                    f_solve_operation='NA' if point['f_solve'] is None else 'actual_QP',
                    alpha=point.get('alpha'),full_original_QP_map=point.get('full_original_QP_map'),
                    phi=point.get('phi'),damage=point['damage'],force={k:point['force'][k] for k in ('force_inf','force_l2','force_scaled','boundary_inf')})
                with os.fdopen(fd,'wb') as f:
                    fields=dict(u=point['u'],d=point['d'],A=point['q'].accumulated,
                        r=point['q'].driver,f=point['q'].fatigue,psi=point['psi'],
                        metadata=np.array(json.dumps(metadata,allow_nan=False)))
                    if point['f_solve'] is not None:fields['f_solve']=point['f_solve']
                    for key in ('Ru','F'):
                        if key in point:fields[key]=point[key]
                    np.savez_compressed(f,**fields);f.flush();os.fsync(f.fileno())
                os.replace(name,folder/(tag+'.npz'))
            finally:
                if os.path.exists(name):os.unlink(name)
        backend.unaccepted_point_observer=save_work_point
        if coupling.mode in ('guarded_block_newton','joint_projected_trust','box_residual_trust'):
            import warnings
            warnings.simplefilter('error')
            def save_direction(point,info,vectors):
                import tempfile
                folder=phase/'unaccepted_work_points';folder.mkdir(exist_ok=True)
                fd,name=tempfile.mkstemp(prefix='.direction-',suffix='.npz',dir=folder)
                try:
                    metadata=dict(classification='UNACCEPTED_LINEAR_DIRECTION_NOT_LABEL',
                        outer=point['outer'],parent_id=point['previous_id'],load_id=point['load_id'],diagnostics=info)
                    with os.fdopen(fd,'wb') as f:
                        np.savez_compressed(f,**vectors,metadata=np.array(json.dumps(metadata,allow_nan=False)))
                        f.flush();os.fsync(f.fileno())
                    os.replace(name,folder/'last_block_direction.npz')
                finally:
                    if os.path.exists(name):os.unlink(name)
            backend.block_direction_observer=save_direction
        if coupling.mode in ('joint_projected_trust','box_residual_trust'):
            def save_joint_trial(metadata,vectors):
                import tempfile
                folder=phase/'unaccepted_work_points';folder.mkdir(exist_ok=True)
                fd,name=tempfile.mkstemp(prefix='.joint-',suffix='.npz',dir=folder)
                try:
                    with os.fdopen(fd,'wb') as f:
                        np.savez_compressed(f,**vectors,metadata=np.array(json.dumps(dict(metadata,
                            classification='UNACCEPTED_JOINT_TRIAL_BEFORE_EVALUATION_NOT_LABEL'),allow_nan=False)))
                        f.flush();os.fsync(f.fileno())
                    target=('last_mechanical_before_qualification.npz' if metadata.get('kind')=='pivot_qualification' else
                        'last_box_trial_before.npz' if metadata.get('event')=='box_trial_before' else
                        ('last_box_stage_candidate_before_model.npz' if metadata['stage'].endswith('_before_model') else 'last_box_stage_'+metadata['stage']+'.npz') if metadata.get('event')=='box_stage' else 'last_joint_trial_before.npz')
                    os.replace(name,folder/target)
                finally:
                    if os.path.exists(name):os.unlink(name)
            backend.joint_trial_observer=save_joint_trial
            backend.mechanics_workspace.qualification_state_observer=lambda meta,vectors:save_joint_trial(
                dict(meta,parent_id=old.fingerprint(),next_state_index=old.load_index+1),vectors)
            if coupling.mode=='box_residual_trust':
                def save_box_model(point,J,row_weights,D,L):
                    import tempfile
                    folder=phase/'unaccepted_work_points';folder.mkdir(exist_ok=True)
                    fd,name=tempfile.mkstemp(prefix='.box-model-',suffix='.npz',dir=folder)
                    try:
                        metadata=dict(classification='UNACCEPTED_LINEARIZED_MODEL_NOT_LABEL',
                            outer=point['outer'],parent_id=point['previous_id'],load_id=point['load_id'],L_upper=L,
                            save_scope='once per outer subproblem, never every matvec',
                            model_definition='q(p)=.5||r0+diag(w)Jp||²; fixed computed r0=fl(w*originalF)')
                        ue=point['u'][backend.kin.element_dofs]
                        trace_positive=np.column_stack([(lambda strain:(strain[:,0]+strain[:,1])>=0.)(
                            np.einsum('eij,ej->ei',backend.kin.b_matrices[:,j],ue))for j in range(4)])
                        with os.fdopen(fd,'wb')as f:
                            np.savez_compressed(f,J_data=J.data,J_indices=J.indices,J_indptr=J.indptr,
                                J_shape=np.array(J.shape),row_weights=row_weights,D=D,
                                original_F=np.r_[point['Ru'],point['F']],model_r0=row_weights*np.r_[point['Ru'],point['F']],
                                base_u=point['u'],base_d=point['d'],trace_positive=trace_positive,
                                history_loading=point['q'].driver>old.driver,fatigue_active=point['q'].accumulated>backend.alpha_t,
                                trial_A=point['q'].accumulated,trial_driver=point['q'].driver,trial_f=point['q'].fatigue,
                                metadata=np.array(json.dumps(metadata,allow_nan=False)))
                            f.flush();os.fsync(f.fileno())
                        os.replace(name,folder/'last_box_model.npz')
                    finally:
                        if os.path.exists(name):os.unlink(name)
                backend.box_model_observer=save_box_model
    store = StateStore(phase/"latest.npz")
    store.initialize(old, context=step_context(card,spec,old,0,dofs,bc))
    shutil.copy2(store.path, phase/"states/state0000.npz")
    previous, previous_load, current_load = None, 0., 0.
    predictor = None
    if spec["initializer"] == "neural":
        import torch
        from hybrid_network import DamageGraphPredictor, FrozenGraphInterface
        model_dir = archive / "training"
        receipt = read_manifest(model_dir/"receipt.json")
        if receipt.get("completed") is not True:
            raise RuntimeError("training did not complete; cannot evaluate NN")
        if receipt.get('coupling_policy_id')!=coupling_id or receipt['model_manifest'].get('coupling_policy_id')!=coupling_id:
            raise RuntimeError('frozen network coupling provenance differs')
        if receipt.get('state_contract_id')!=CONTRACT_ID or receipt['model_manifest'].get('state_contract_id')!=CONTRACT_ID:
            raise RuntimeError('frozen network field timing provenance differs')
        checkpoint = torch.load(model_dir/"best.pt", map_location="cpu", weights_only=True)
        if sha256(model_dir/"best.pt") != receipt["checkpoint_sha256"]:
            raise RuntimeError("frozen checkpoint changed")
        module = DamageGraphPredictor(len(checkpoint["feature_names"]))
        module.load_state_dict(checkpoint["state_dict"])
        predictor = FrozenGraphInterface(module, backend, manifest=receipt["model_manifest"],
                                         mean=checkpoint["mean"], scale=checkpoint["scale"], device="cuda:0")
    append_event(phase/"events.jsonl", dict(kind="setup", backend_seconds=backend.setup_seconds,
                                           network_seconds=getattr(predictor,"setup_seconds",0.)))
    wall_start = perf_counter()
    count = spec["cycles"] * len(card["base_load_cycle"])
    records = []
    for index in range(count):
        tick = perf_counter()
        trajectory_storage_check(card,out,archive,headroom=True)
        cycle, substep = divmod(index, len(card["base_load_cycle"]))
        target = card["base_load_cycle"][substep] * spec["amplitude_multiplier"]
        marker(out, phase=spec["id"], step=index+1, role="numerical_substep")
        initial = (classical_guess(old, previous, target, current_load, previous_load)
                   if spec["initializer"]=="classical" else None)
        trace=PersistentWorkTrace(phase/"work_trace.jsonl",spec["id"],index+1)
        try:
            proposal = solve_step(backend, old, dofs, bc*target,
                                  next_load_id=f'{spec["id"]}:c{cycle+1}:s{substep+1}:{target:.17g}',
                                  settings=settings, predictor=predictor, classical_initial=initial,
                                  return_prediction_context=spec["role"]=="labels",work_observer=trace.call,
                                  coupling=coupling,iteration_observer=trace.record_iteration)
        except StepFailure as exc:
            write_json(phase/"failure.json", dict(step=index+1, reason=str(exc), work=exc.work,
                                                 accepted_id=old.fingerprint(), version=old.version))
            raise
        proposal = trace.call('bind_field_timing',lambda:bind_proposal(
            proposal,step_context(card,spec,proposal.state,index+1,dofs,bc)))
        trace.call("durable_commit",lambda:store.commit(proposal))
        io_tick = perf_counter()
        state_path = phase/f"states/state{index+1:04d}.npz"
        trace.call("snapshot_save",lambda:(lossless_snapshot(store.path,state_path)
            if card.get('snapshot_storage')=='lossless_npz_deflate1' else shutil.copy2(store.path,state_path)))
        record = dict(step=index+1, cycle=cycle+1, substep=substep+1, load=target,
                      certificate=proposal.certificate, state_file=str(state_path.relative_to(archive)),
                      state_sha256=sha256(state_path), commit_io_seconds=store.last_io_seconds,
                      snapshot_io_seconds=perf_counter()-io_tick,
                      work=proposal.work, f_min=float(proposal.state.fatigue.min()))
        record.update(state_contract_id=CONTRACT_ID, state_contract=proposal.accepted_contract)
        if spec["role"] == "labels":
            from hybrid_network import features_for, FEATURES
            u_pred, psi_pred = proposal.prediction_context
            x = trace.call("label_features",lambda:features_for(backend, old, u_pred, psi_pred, dofs, bc*target))
            fpath = phase/f"features{index+1:04d}.npz"
            trace.call("label_feature_save",lambda:np.savez_compressed(fpath, x=x.astype(np.float32), d_old=old.damage.astype(np.float32),
                                d_target=proposal.state.damage.astype(np.float32),u_pred=u_pred,psi_pred=psi_pred))
            predictor_hash=__import__('hashlib').sha256(u_pred.tobytes()+psi_pred.tobytes()).hexdigest()
            record.update(features_file=str(fpath.relative_to(archive)), features_sha256=sha256(fpath),
                          feature_names=list(FEATURES), predecessor_id=old.fingerprint(),
                          state_id=proposal.state.fingerprint(), mesh_id=backend.mesh_id,
                          physics_id=backend.physics_id, role="numerically_accepted_new_contract_label",
                          settings_id=proposal.certificate['settings_id'],domain='nodal-K-v1',
                          coupling_policy_id=coupling_id,
                          feature_timing=FEATURE_TIMING,
                          input_accepted_verified=True,output_joint_verified=True,trial_map_verified=True,
                          array_hashes_verified=True,features_origin_verified=True,original_operator_verified=True,
                          trajectory_id=spec['id'],certificate_sha256=object_sha(proposal.certificate),
                          input_predictor_sha256=predictor_hash,label_sha256=sha256(state_path),
                          input_state_file=str((phase/f'states/state{index:04d}.npz').relative_to(archive)),
                          input_state_sha256=sha256(phase/f'states/state{index:04d}.npz'),
                          load_index_in=index,load_index_out=index+1)
        record["total_step_wall_seconds"] = perf_counter()-tick
        trace.call("accepted_event_save",lambda:append_event(phase/"events.jsonl", record))
        trace.call('accepted_storage_check',lambda:trajectory_storage_check(card,out,archive))
        notify("step_done",index+1)
        records.append({k:record[k] for k in ("step","state_file","state_sha256","certificate","f_min")})
        previous, old = old, proposal.state
        previous_load, current_load = current_load, target
    summary = dict(completed=True, phase=spec["id"], states=count, wall_seconds=perf_counter()-wall_start,
                   f_min=min(r["f_min"] for r in records), initial_state_id=records[0]["certificate"]["previous_id"],
                   final_state_id=old.fingerprint(), physical_acceptance=True,
                   backend_setup_seconds=backend.setup_seconds,
                   coupling_policy_id=coupling_id,
                   state_contract_id=CONTRACT_ID,
                   network_setup_seconds=getattr(predictor,"setup_seconds",0.))
    write_json(phase/"summary.json", summary)
    return summary


def analyze(card,inputs,out,archive):
    """Reference scoring after every candidate is frozen; outside online timing."""
    backend,_,dofs,bc=load_backend(inputs,read_manifest(Path(inputs)/'inputs.json'))
    phase=archive/'analysis';phase.mkdir();summary={}
    weights=backend.kin.det_jacobians
    for name in ['test_classical','test_hybrid']:
        rows=[]
        for step in range(1,601):
            reference,refmeta=StateStore(archive/f'test_reference/states/state{step:04d}.npz').load()
            candidate,meta=StateStore(archive/name/f'states/state{step:04d}.npz').load()
            for state,metadata,phase_id in ((reference,refmeta,'test_reference'),(candidate,meta,name)):
                spec=next(p for p in card['phases'] if p['id']==phase_id)
                verify_expected(state,metadata,step_context(card,spec,state,step,dofs,bc))
            verify_comparable(candidate,meta,reference,refmeta)
            r=compare_states(backend,candidate,reference)
            r['J']=float(np.sqrt(((r['u_gp_rms']/card['displacement_scale'])**2
                                  +(r['v_gp_rms']/card['displacement_scale'])**2+r['d_gp_rms']**2)/3))
            for key,field in [('A','accumulated'),('r','driver')]:
                norm=float(np.sqrt(np.sum(weights*getattr(reference,field)**2)/weights.sum()))
                r[key+'_relative_rms']=r[key+'_gp_rms']/max(norm,1.e-8)
            nr=np.array(meta['certificate']['mechanics']['reaction_values'])
            rr=np.array(refmeta['certificate']['mechanics']['reaction_values'])
            r['reaction_relative_l2']=float(np.linalg.norm(nr-rr)/max(np.linalg.norm(rr),1.e-8))
            from hybrid_diagnostics import compare_diagnostics,plot_fields
            prevref,prm=StateStore(archive/f'test_reference/states/state{step-1:04d}.npz').load()
            prevcan,pcm=StateStore(archive/name/f'states/state{step-1:04d}.npz').load()
            verify_transition(prevref,prm,reference,refmeta)
            verify_transition(prevcan,pcm,candidate,meta)
            r['diagnostics']=compare_diagnostics(backend,candidate,reference,prevcan,prevref)
            r['correction']={k:meta['certificate'][k] for k in ('initialization_source','initial_to_final_damage_rms','initial_to_final_damage_inf')}
            if name=='test_hybrid' and step in (4,304,599,600):
                classic,cm=StateStore(archive/f'test_classical/states/state{step:04d}.npz').load()
                verify_comparable(classic,cm,reference,refmeta)
                plot_fields(backend,[reference,classic,candidate],step,phase/'figures',
                            dict(run=card['run_id'],reference=refmeta['state_id'],candidate=meta['state_id'],source='sealed states; common posthoc only'))
            rows.append(dict(step=step,physical_key=meta['state_contract']['context']['physical'],
                             state_contract_id=CONTRACT_ID,**r))
        append_event(phase/'comparison.jsonl',dict(candidate=name,rows=rows))
        summary[name]=dict(mean_J=float(np.mean([r['J'] for r in rows])),
                           max_J=max(r['J'] for r in rows),
                           max_A_relative=max(r['A_relative_rms'] for r in rows),
                           max_r_relative=max(r['r_relative_rms'] for r in rows),
                           max_f_rms=max(r['f_gp_rms'] for r in rows),
                           max_reaction_relative=max(r['reaction_relative_l2'] for r in rows),
                           max_nodal_healing=max(r['diagnostics']['candidate']['nodal_healing'] for r in rows),
                           max_negative_damage=max(r['diagnostics']['candidate']['negative_amplitude'] for r in rows),
                           fallback_steps=sum('fallback' in r['correction']['initialization_source'] for r in rows),
                           max_damage_correction=max(r['correction']['initial_to_final_damage_inf'] for r in rows))
    (phase/'README_analysis.md').write_text('Common posthoc sealed-state analysis. comparison.jsonl contains u/v/d,A/r/f,reaction, raw/active full and fixed-window errors, reference diffuse-zone errors, elastic/fracture energy, trace-branch mismatch, d=.5 support/front, own-predecessor healing/negative damage, correction and fallback. Figures selected by fixed steps4,304,599,600; no checkpoint selection or online scoring. GP/field scalars nondimensional; absent fronts/zones reported null. Supplemental diagnostics do not rescue primary quality/speed failures. Figure sidecars state provenance and display interpolation.')
    write_json(phase/'summary.json',dict(completed=True,methods=summary,
                                        scoring_role='post-hoc common evaluation, excluded from CF/CC/CH and charged as study cost'))
    return dict(completed=True,methods=summary)


def fit(card, inputs, out, archive):
    import torch
    from hybrid_network import DamageGraphPredictor, FEATURES, mesh_graph, weights_id
    from audit_hybrid_labels import qualify_transition
    from hybrid_incremental import digest_config
    backend,_,dofs,bc = load_backend(inputs, read_manifest(Path(inputs)/"inputs.json"))
    phase=archive/"training";phase.mkdir()
    config=card["training"]
    torch.manual_seed(config["seed"])
    train_rows, validation_rows = [], []
    for phase_id in ("train_A","train_B","validation"):
        seen_steps=[]
        spec=next(p for p in card['phases'] if p['id']==phase_id)
        if not read_manifest(archive/phase_id/"summary.json").get("completed"):
            raise RuntimeError("incomplete label trajectory")
        for line in (archive/phase_id/"events.jsonl").read_text().splitlines():
            row=json.loads(line)
            if "features_file" in row:
                if row.get('feature_names')!=list(FEATURES):
                    raise RuntimeError('label feature order differs')
                if (row["certificate"]["passed"] is not True
                        or sha256(archive/row["features_file"])!=row["features_sha256"]
                        or sha256(archive/row["state_file"])!=row["state_sha256"]
                        or sha256(archive/row['input_state_file'])!=row['input_state_sha256']):
                    raise RuntimeError("label identity/acceptance mismatch")
                verify_label_coupling(row,coupling_identity(card))
                qualification=qualify_transition(row,physics_id=backend.physics_id,mesh_id=backend.mesh_id,
                                                  settings_id=digest_config(asdict(SolverSettings(**card['solver']))))
                if not qualification['metadata_eligible']:raise RuntimeError('label metadata contract not qualified')
                a,am=StateStore(archive/row['input_state_file']).load()
                b,meta=StateStore(archive/row['state_file']).load()
                verify_transition(a,am,b,meta)
                verify_expected(a,am,step_context(card,spec,a,row['step']-1,dofs,bc))
                verify_expected(b,meta,step_context(card,spec,b,row['step'],dofs,bc))
                if row.get('state_contract') != meta['state_contract']:
                    raise RuntimeError('label event field timing envelope differs from sealed state')
                if (a.fingerprint()!=row['predecessor_id'] or b.fingerprint()!=row['state_id']
                        or object_sha(meta['certificate'])!=row['certificate_sha256']):
                    raise RuntimeError('accepted predecessor/label certificate chain mismatch')
                # Recompute the cheap feature transform from sealed old state
                # and saved common predictor. No future label enters features.
                with np.load(archive/row['features_file'],allow_pickle=False) as z:
                    verify_label_feature_arrays(backend,a,b,z,dofs,
                        bc*meta['state_contract']['context']['physical']['prescribed_load'],row['input_predictor_sha256'])
                seen_steps.append(row['step'])
                (validation_rows if phase_id=="validation" else train_rows).append(row)
        if seen_steps!=list(range(1,601)):
            raise RuntimeError('label trajectory steps missing, duplicated or reordered')
    if len(train_rows)!=1200 or len(validation_rows)!=600:
        raise RuntimeError("whole planned label trajectories required; no partial fit")
    write_json(phase/'qualified_labels.json',dict(qualified_transitions=1800,train_transitions=1200,
        validation_transitions=600,state_contract_id=CONTRACT_ID,coupling_policy_id=coupling_identity(card),
        input_rows_sha256=object_sha(train_rows+validation_rows),test_opened=False,
        qualification='all ordered states, predecessors, exact arrays, common predictor, certificates and field timing checked'))
    total=np.zeros(len(FEATURES));squares=total.copy();n=0
    for row in train_rows:
        with np.load(archive/row["features_file"],allow_pickle=False) as z:
            x=z["x"].astype(float);total+=x.sum(0);squares+=(x*x).sum(0);n+=len(x)
    mean=total/n;scale=np.sqrt(np.maximum(squares/n-mean**2,0.));scale[scale<1.e-8]=1.
    model=DamageGraphPredictor(len(FEATURES)).cuda()
    with torch.no_grad():model.head.weight.zero_();model.head.bias.fill_(.05)
    optimizer=torch.optim.Adam(model.parameters(),lr=config["learning_rate"])
    graph=tuple(a.cuda() for a in mesh_graph(backend.kin.points,backend.kin.cells,backend.length_scale))
    weights=torch.tensor(backend.kin.det_jacobians.copy(),dtype=torch.float32,device="cuda")
    mass=torch.tensor(np.asarray(backend.gp.T@backend.kin.det_jacobians.reshape(-1)),dtype=torch.float32,device="cuda")
    gx=torch.tensor(backend.kin.b_matrices[:,:,0,0::2].copy(),dtype=torch.float32,device="cuda")
    gy=torch.tensor(backend.kin.b_matrices[:,:,1,1::2].copy(),dtype=torch.float32,device="cuda")
    cells=torch.tensor(backend.kin.cells.copy(),dtype=torch.long,device="cuda")

    def loss(row):
        with np.load(archive/row["features_file"],allow_pickle=False) as z:
            x=torch.tensor((z["x"]-mean)/scale,dtype=torch.float32,device="cuda")
            d0=torch.tensor(z["d_old"],device="cuda")
            target=torch.tensor(z["d_target"],device="cuda")
        a=model(x,*graph)
        d=d0+(1-d0)*a.clamp(0,1)
        error=d-target
        ex=torch.einsum("egj,ej->eg",gx,error[cells]);ey=torch.einsum("egj,ej->eg",gy,error[cells])
        return ((mass*error**2).sum()+backend.length_scale**2*(weights*(ex**2+ey**2)).sum())/weights.sum()

    rng=np.random.default_rng(config["seed"])
    order=rng.permutation(len(train_rows));best=float("inf");stale=0;history=[]
    begin=perf_counter();updates=0;end_reason="updates"
    for update in range(1,config["max_updates"]+1):
        if perf_counter()-begin>config["wall_seconds"]-60:
            end_reason="time_cap";break
        if (update-1)%len(train_rows)==0:order=rng.permutation(len(train_rows))
        model.train();optimizer.zero_grad(set_to_none=True)
        value=loss(train_rows[int(order[(update-1)%len(train_rows)])])
        if not torch.isfinite(value):raise RuntimeError("nonfinite supervised loss")
        value.backward();optimizer.step();updates=update
        if update%config["validation_every"]==0 or update==config["max_updates"]:
            model.eval()
            with torch.inference_mode():valid=float(np.mean([loss(row).item() for row in validation_rows]))
            history.append(dict(update=update,validation_loss=valid,train_loss=float(value.item())))
            append_event(phase/"events.jsonl",history[-1])
            if not np.isfinite(valid):raise RuntimeError("nonfinite validation loss")
            if valid<best:
                best=valid;stale=0
                # Own producer checkpoint, basic tensors/lists only. Test unopened.
                torch.save(dict(state_dict={k:v.detach().cpu() for k,v in model.state_dict().items()},
                                mean=mean.tolist(),scale=scale.tolist(),feature_names=list(FEATURES)),phase/"best.pt")
            else:stale+=1
            if stale>=config["patience"]:end_reason="validation_early_stop";break
    if not history or not (phase/"best.pt").exists():
        raise RuntimeError("no validated frozen checkpoint produced")
    checkpoint=torch.load(phase/"best.pt",map_location="cpu",weights_only=True)
    frozen=DamageGraphPredictor(len(FEATURES));frozen.load_state_dict(checkpoint["state_dict"])
    # Attestation is separate from the model manifest to avoid a self hash.
    training_record=dict(completed=True,config=config,updates=updates,end_reason=end_reason,
                         state_contract_id=CONTRACT_ID,feature_timing=FEATURE_TIMING,
                         coupling_policy_id=coupling_identity(card),
                         train_transitions=len(train_rows),validation_transitions=len(validation_rows),
                         input_rows_sha256=__import__('hybrid_producer_common').object_sha(train_rows+validation_rows),
                         validation_best=best,history=history,wall_seconds=perf_counter()-begin,
                         weights_id=weights_id(frozen),test_opened=False)
    write_json(phase/"training_record.json",training_record)
    summary=dict(completed=True,updates=updates,wall_seconds=perf_counter()-begin,
                 state_contract_id=CONTRACT_ID,
                 coupling_policy_id=coupling_identity(card),
                 checkpoint_sha256=sha256(phase/"best.pt"),
                 model_manifest=dict(trained=True,training_receipt_sha256=sha256(phase/"training_record.json"),
                                     feature_names=list(FEATURES),physics_id=backend.physics_id,
                                     coupling_policy_id=coupling_identity(card),
                                     state_contract_id=CONTRACT_ID,feature_timing=FEATURE_TIMING,
                                     weights_id=weights_id(frozen)))
    write_json(phase/"receipt.json",summary)
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--card',required=True,type=Path);p.add_argument('--phase',required=True)
    p.add_argument('--inputs',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--archive',required=True,type=Path);args=p.parse_args()
    if platform.system()!='Linux':raise RuntimeError('producer workers are Linux-only; never train/solve on Mac')
    card=read_manifest(args.card)
    spec=card['plotting_admission'] if args.phase=='plotting_admission' else next(x for x in card['phases'] if x['id']==args.phase)
    start=perf_counter()
    if spec['kind']=='admission':
        from hybrid_plotting_admission import probe_plotting
        try:result=probe_plotting(card['runtime_expected'].get('matplotlib'))
        except Exception as exc:
            write_json(args.out/'plotting_admission_failure.json',dict(phase='plotting_admission',
                       first_cause=str(exc),exception_type=type(exc).__name__,no_project_state_or_training=True))
            raise
    elif spec['kind']=='trajectory':result=trajectory(card,spec,args.inputs,args.out,args.archive)
    elif spec['kind']=='training':result=fit(card,args.inputs,args.out,args.archive)
    elif spec['kind']=='replay':
        from replay_hybrid_native_operators import replay
        result=replay(args.inputs)
        if not result['passed']:raise RuntimeError('native replay did not pass')
    elif spec['kind']=='analysis':result=analyze(card,args.inputs,args.out,args.archive)
    else:raise ValueError('unknown worker phase')
    result['process_wall_seconds']=perf_counter()-start
    use=resource.getrusage(resource.RUSAGE_SELF)
    result['cpu_seconds']=use.ru_utime+use.ru_stime
    result['maximum_rss_kib']=use.ru_maxrss
    write_json(args.out/f"result_{args.phase}.json",result)


if __name__=='__main__':main()
