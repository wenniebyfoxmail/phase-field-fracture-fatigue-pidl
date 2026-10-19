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
from hybrid_producer_common import write_json, append_event, classical_guess, compare_states,object_sha
from hybrid_transaction import StateStore
from hybrid_work_trace import PersistentWorkTrace
from hybrid_guard_client import notify


def marker(out, **values):
    notify("step_start",values["step"])
    write_json(Path(out) / "active_step.json", dict(start_epoch=time(),start_monotonic=perf_counter(), **values))


def trajectory(card, spec, inputs, out, archive):
    backend, old, dofs, bc = load_backend(inputs, read_manifest(Path(inputs)/"inputs.json"))
    settings = SolverSettings(**card["solver"])
    phase = archive / spec["id"]
    phase.mkdir()
    (phase/"states").mkdir()
    store = StateStore(phase/"latest.npz")
    store.initialize(old)
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
                                  return_prediction_context=spec["role"]=="labels",work_observer=trace.call)
        except StepFailure as exc:
            write_json(phase/"failure.json", dict(step=index+1, reason=str(exc), work=exc.work,
                                                 accepted_id=old.fingerprint(), version=old.version))
            raise
        trace.call("durable_commit",lambda:store.commit(proposal))
        io_tick = perf_counter()
        state_path = phase/f"states/state{index+1:04d}.npz"
        trace.call("snapshot_save",lambda:shutil.copy2(store.path, state_path))
        record = dict(step=index+1, cycle=cycle+1, substep=substep+1, load=target,
                      certificate=proposal.certificate, state_file=str(state_path.relative_to(archive)),
                      state_sha256=sha256(state_path), commit_io_seconds=store.last_io_seconds,
                      snapshot_io_seconds=perf_counter()-io_tick,
                      work=proposal.work, f_min=float(proposal.state.fatigue.min()))
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
                          input_accepted_verified=True,output_joint_verified=True,trial_map_verified=True,
                          array_hashes_verified=True,features_origin_verified=True,original_operator_verified=True,
                          trajectory_id=spec['id'],certificate_sha256=object_sha(proposal.certificate),
                          input_predictor_sha256=predictor_hash,label_sha256=sha256(state_path),
                          input_state_file=str((phase/f'states/state{index:04d}.npz').relative_to(archive)),
                          input_state_sha256=sha256(phase/f'states/state{index:04d}.npz'),
                          load_index_in=index,load_index_out=index+1)
        record["total_step_wall_seconds"] = perf_counter()-tick
        trace.call("accepted_event_save",lambda:append_event(phase/"events.jsonl", record))
        notify("step_done",index+1)
        records.append({k:record[k] for k in ("step","state_file","state_sha256","certificate","f_min")})
        previous, old = old, proposal.state
        previous_load, current_load = current_load, target
    summary = dict(completed=True, phase=spec["id"], states=count, wall_seconds=perf_counter()-wall_start,
                   f_min=min(r["f_min"] for r in records), initial_state_id=records[0]["certificate"]["previous_id"],
                   final_state_id=old.fingerprint(), physical_acceptance=True,
                   backend_setup_seconds=backend.setup_seconds,
                   network_setup_seconds=getattr(predictor,"setup_seconds",0.))
    write_json(phase/"summary.json", summary)
    return summary


def analyze(card,inputs,out,archive):
    """Reference scoring after every candidate is frozen; outside online timing."""
    backend,_,_,_=load_backend(inputs,read_manifest(Path(inputs)/'inputs.json'))
    phase=archive/'analysis';phase.mkdir();summary={}
    weights=backend.kin.det_jacobians
    for name in ['test_classical','test_hybrid']:
        rows=[]
        for step in range(1,601):
            reference,refmeta=StateStore(archive/f'test_reference/states/state{step:04d}.npz').load()
            candidate,meta=StateStore(archive/name/f'states/state{step:04d}.npz').load()
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
            prevref,_=StateStore(archive/f'test_reference/states/state{step-1:04d}.npz').load()
            prevcan,_=StateStore(archive/name/f'states/state{step-1:04d}.npz').load()
            r['diagnostics']=compare_diagnostics(backend,candidate,reference,prevcan,prevref)
            r['correction']={k:meta['certificate'][k] for k in ('initialization_source','initial_to_final_damage_rms','initial_to_final_damage_inf')}
            if name=='test_hybrid' and step in (4,304,599,600):
                classic,_=StateStore(archive/f'test_classical/states/state{step:04d}.npz').load()
                plot_fields(backend,[reference,classic,candidate],step,phase/'figures',
                            dict(run=card['run_id'],reference=refmeta['state_id'],candidate=meta['state_id'],source='sealed states; common posthoc only'))
            rows.append(dict(step=step,**r))
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
    backend,_,_,_ = load_backend(inputs, read_manifest(Path(inputs)/"inputs.json"))
    phase=archive/"training";phase.mkdir()
    config=card["training"]
    torch.manual_seed(config["seed"])
    train_rows, validation_rows = [], []
    for phase_id in ("train_A","train_B","validation"):
        if not read_manifest(archive/phase_id/"summary.json").get("completed"):
            raise RuntimeError("incomplete label trajectory")
        for line in (archive/phase_id/"events.jsonl").read_text().splitlines():
            row=json.loads(line)
            if "features_file" in row:
                if (row["certificate"]["passed"] is not True
                        or sha256(archive/row["features_file"])!=row["features_sha256"]
                        or sha256(archive/row["state_file"])!=row["state_sha256"]
                        or sha256(archive/row['input_state_file'])!=row['input_state_sha256']):
                    raise RuntimeError("label identity/acceptance mismatch")
                qualification=qualify_transition(row,physics_id=backend.physics_id,mesh_id=backend.mesh_id,
                                                  settings_id=digest_config(asdict(SolverSettings(**card['solver']))))
                if not qualification['metadata_eligible']:raise RuntimeError('label metadata contract not qualified')
                a,_=StateStore(archive/row['input_state_file']).load()
                b,meta=StateStore(archive/row['state_file']).load()
                if (a.fingerprint()!=row['predecessor_id'] or b.fingerprint()!=row['state_id']
                        or object_sha(meta['certificate'])!=row['certificate_sha256']):
                    raise RuntimeError('accepted predecessor/label certificate chain mismatch')
                (validation_rows if phase_id=="validation" else train_rows).append(row)
    if len(train_rows)!=1200 or len(validation_rows)!=600:
        raise RuntimeError("whole planned label trajectories required; no partial fit")
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
                         train_transitions=len(train_rows),validation_transitions=len(validation_rows),
                         input_rows_sha256=__import__('hybrid_producer_common').object_sha(train_rows+validation_rows),
                         validation_best=best,history=history,wall_seconds=perf_counter()-begin,
                         weights_id=weights_id(frozen),test_opened=False)
    write_json(phase/"training_record.json",training_record)
    summary=dict(completed=True,updates=updates,wall_seconds=perf_counter()-begin,
                 checkpoint_sha256=sha256(phase/"best.pt"),
                 model_manifest=dict(trained=True,training_receipt_sha256=sha256(phase/"training_record.json"),
                                     feature_names=list(FEATURES),physics_id=backend.physics_id,
                                     weights_id=weights_id(frozen)))
    write_json(phase/"receipt.json",summary)
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--card',required=True,type=Path);p.add_argument('--phase',required=True)
    p.add_argument('--inputs',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--archive',required=True,type=Path);args=p.parse_args()
    if platform.system()!='Linux':raise RuntimeError('producer workers are Linux-only; never train/solve on Mac')
    card=read_manifest(args.card);spec=next(x for x in card['phases'] if x['id']==args.phase)
    start=perf_counter()
    if spec['kind']=='trajectory':result=trajectory(card,spec,args.inputs,args.out,args.archive)
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
