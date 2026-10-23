#!/usr/bin/env python3
"""D014 explicitly approved future offline execution. Default CLI cannot run science."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from threadpoolctl import threadpool_limits
from s04_e024_field_budget import (STATES, PROFILES, InvalidEvidence, ResourceStop,
    run_profile, qualify_saved_seed, safe_json)
from s04_e024_field_runtime import (SOURCE, CAPS, PhaseLedger, LocalGuard, sha, write_json,
    validate_approval, worker_context, supervise, peak_rss,code_tree_sha,persist_event,runtime_provenance)


def worker(a):
    check=worker_context(a.out,a.worker_state,a.worker_phase,a.approval,a.expected_commit)
    if a.worker_phase=='render':
        from summarize_s04_e024_field_budget import render
        render(a.out,check);return
    # Deliberately below the complete approval/parent/state gate.
    from s04_e024_field_physics import load_real_adapter
    start=time.monotonic();adapter=load_real_adapter(a.project,a.worker_state,check)
    load_wall=time.monotonic()-start
    if a.worker_phase=='replay':
        from summarize_s04_e024_field_budget import replay_state
        record=replay_state(adapter,a.out,a.worker_state,check,expected_commit=a.expected_commit)
        record.update(provenance=runtime_provenance(),source_commit=a.expected_commit,wall_seconds=time.monotonic()-start,
                      peak_rss_bytes=peak_rss(),code_tree_sha256=code_tree_sha())
        write_json(a.out/'replay'/a.worker_state/'verified.json',record);check();return
    case=a.out/'states'/a.worker_state;case.mkdir(parents=True,exist_ok=False)
    write_json(case/'origin.json',dict(assets=adapter.assets,report=adapter.physical_report(adapter.origin)))
    np.savez_compressed(case/'origin.npz',**adapter.origin)
    np.savez_compressed(case/'geometry.npz',xy=adapter.data['xy'],conn=adapter.data['conn'],damage=adapter.data['damage'],reference_uv=adapter.data['equilibrated_uv'],window=adapter.window,us=adapter.us)
    saved_seed=qualify_saved_seed(adapter,adapter.metrics,adapter.d012_head,check,
        provenance=getattr(adapter,'d012_provenance',None))
    # An exact E023 UV state is a no-correction branch; retain the historical
    # comparator report without permitting it to seed a correction.
    historical_fields=saved_seed['fields']
    if historical_fields is None:
        historical_fields=adapter.realize(adapter.d012_head.astype(adapter.theta.dtype))
        adapter.check_realization(adapter.d012_head.astype(adapter.theta.dtype),historical_fields,adapter.metrics)
    historical=adapter.physical_report(historical_fields)
    profiles={}
    for name,eta,strict in PROFILES:
        check();folder=case/name;folder.mkdir(exist_ok=False)
        events=folder/'events.jsonl'
        with events.open('x') as out:
            def emit(event):
                check();out.write(json.dumps(persist_event(folder,event),allow_nan=False)+'\n');out.flush();check()
            head,fields,counts=run_profile(adapter,adapter.metrics,eta,strict,check,emit,
                saved_seed=saved_seed)
        check()
        initial_head=np.asarray(counts['initialization']['selected']['head'],dtype=adapter.theta.dtype)
        np.savez_compressed(folder/'final.npz',head=head,original_head=adapter.theta,initial_head=initial_head,
                            window=adapter.window,**fields)
        report=adapter.physical_report(fields)
        write_json(folder/'final.json',dict(eta=eta,strict=strict,counts=counts,report=report,
            centre_digest=adapter.metrics.centre_digest,
            relative_head_change=float(np.linalg.norm(head-adapter.theta)/np.linalg.norm(adapter.theta))
                if np.linalg.norm(adapter.theta)>0 else None))
        profiles[name]=counts
    adapter.final_identity();check()
    record=dict(provenance=runtime_provenance(),state=a.worker_state,source_commit=a.expected_commit,code_tree_sha256=code_tree_sha(),
        assets=adapter.assets,profiles=profiles,D012_report=historical,
        seeded_incumbent_protocol=True,saved_seed_qualification=saved_seed['record'],
        wall_seconds=time.monotonic()-start,load_wall_seconds=load_wall,peak_rss_bytes=peak_rss(),
        offline_solver_calls=sum(x['solves'] for x in profiles.values()),
        actual_candidate_trials=sum(x['trials'] for x in profiles.values()),
        NN_optimizer_steps=0,original_checkpoint_writes=0,history_fatigue_damage_updates=0,remote_actions=0,
        strict_portability='original Mac native LR/mass/D/rho exceptions and numerical warnings retained',
        files={str(p.relative_to(case)):sha(p) for p in sorted(case.rglob('*')) if p.is_file()})
    write_json(case/'receipt.json',record);check()


def parent(a):
    preflight_start=time.monotonic()
    approval,nontraining_used=validate_approval(a.approval,a.expected_commit)
    allowed=a.project.resolve()/'local_archive/experiments/S04-E024'
    if a.out.resolve().parent!=allowed or not a.out.name.startswith('physical_field_budget_seeded_incumbent_execution_'):
        raise InvalidEvidence('fresh attributable local_archive output path required')
    a.out.mkdir(parents=True,exist_ok=False)
    ledger=PhaseLedger(nontraining_used);tick=preflight_start;phase='numeric';children=[]
    def charge():
        nonlocal tick
        now=time.monotonic();elapsed=now-tick;tick=now;ledger.charge(phase,elapsed)
    def launch(state,stage):
        charge();remaining=ledger.remaining(phase)
        context=dict(parent_pid=os.getpid(),active_state=state,active_phase=stage,
            phase_deadline=time.monotonic()+remaining,approval_sha256=sha(a.approval))
        write_json(a.out/'execution_context.json',context)
        cmd=[sys.executable,str(Path(__file__).resolve()),'--execute-scientific',
             '--project',str(a.project),'--out',str(a.out),'--expected-commit',a.expected_commit,
             '--approval',str(a.approval),'--worker-state',state,'--worker-phase',stage]
        record=supervise(cmd,SOURCE,a.out,a.out/'logs'/stage/state,remaining)
        children.append(dict(state=state,phase=stage,**record));charge()
    write_json(a.out/'execution_command.json',dict(provenance=runtime_provenance(),command=sys.argv,project=str(a.project.resolve()),source_commit=a.expected_commit,
        code_tree_sha256=code_tree_sha(),approval_sha256=sha(a.approval),approval=approval,
        nontraining_used_seconds=nontraining_used,NN_training=False,CPU_threads=2,GPU_hours=0))
    try:
        for state in STATES:
            launch(state,'numeric')
            r=json.loads((a.out/'states'/state/'receipt.json').read_text())
            if r['state']!=state or r['source_commit']!=a.expected_commit or list(r['profiles'])!=[x[0] for x in PROFILES]:
                raise InvalidEvidence('worker state/profile identity')
            if any(r[k]!=0 for k in ('NN_optimizer_steps','original_checkpoint_writes','history_fatigue_damage_updates','remote_actions')):
                raise InvalidEvidence('worker forbidden mutation')
        charge();phase='replay';tick=time.monotonic()
        for state in STATES:launch(state,'replay')
        from summarize_s04_e024_field_budget import aggregate
        check=LocalGuard(a.out,time.monotonic()+ledger.remaining('replay'))
        aggregate(a.out,a.expected_commit,check);charge()
        phase='render';tick=time.monotonic();launch('all','render');charge()
        write_json(a.out/'execution_exit.json',dict(exit_code=0,stage_used_seconds=ledger.used,
            cumulative_compute_wall_seconds=sum(ledger.used.values()),children=children,
            execution_complete=True,application_validated=False))
    except BaseException as e:
        # Preserve failure, never spawn a later state/profile or switch solver/retry.
        elapsed=time.monotonic()-tick;ledger.used[phase]+=elapsed
        write_json(a.out/'execution_exit.json',dict(exit_code=1,error=type(e).__name__+': '+str(e),
            stage_used_seconds=ledger.used,cumulative_compute_wall_seconds=sum(ledger.used.values()),
            children=children,execution_complete=False,unexecuted_rows='INCOMPLETE_NOT_ZERO_GAIN'))
        raise


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--execute-scientific',action='store_true',help='requires separately approved final execution receipt and Code Ready')
    p.add_argument('--project',type=Path);p.add_argument('--out',type=Path)
    p.add_argument('--expected-commit');p.add_argument('--approval',type=Path)
    p.add_argument('--worker-state',choices=(*STATES,'all'),help=argparse.SUPPRESS)
    p.add_argument('--worker-phase',choices=('numeric','replay','render'),help=argparse.SUPPRESS)
    return p


def main():
    p=parser();a=p.parse_args()
    if not a.execute_scientific:p.error('scientific execution disabled; explicit approved final package is required')
    if any(getattr(a,k) is None for k in ('project','out','expected_commit','approval')):p.error('missing bound execution arguments')
    for key in ('project','out','approval'):setattr(a,key,getattr(a,key).expanduser().resolve())
    if bool(a.worker_state)!=bool(a.worker_phase):p.error('worker context arguments must be paired')
    if a.worker_state and ((a.worker_phase=='render')!=(a.worker_state=='all')):p.error('render-only all-state context')
    with threadpool_limits(limits=2):
        if a.worker_state:worker(a)
        else:parent(a)


if __name__=='__main__':main()
