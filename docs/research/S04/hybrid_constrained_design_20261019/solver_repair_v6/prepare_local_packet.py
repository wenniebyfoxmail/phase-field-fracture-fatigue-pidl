"""Prepare a disabled v6 packet using retained JSON receipts and source bytes.

Standard library only. No SSH, array decode, solver import or enable option.
A future stage receipt, final cost binding and exact independent execution
review remain necessary. Consumed signed records are never rewritten.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

OWNER='docs/research/S04/hybrid_constrained_design_20261019'
V6=OWNER+'/solver_repair_v6'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path,value):
    Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def build(code,retained,out):
    code,retained,out=map(lambda p:Path(p).resolve(),(code,retained,out))
    if out.exists():raise FileExistsError('fresh local packet required')
    snapshot=retained/'status_check_20261020T195435Z/snapshot.json'
    d=json.loads(snapshot.read_text());ledger=d['records']['cost_ledger.json']
    assert d['hostname']=='GPUServer8' and d['records']['terminal.json']['status']=='failed'
    assert all(v is None for v in d['processes'].values())
    controls=[('dispatch_receipt_attempt1.json','local_wall_seconds'),
        ('status_check_20261020T195435Z/query_network_receipt.json','local_wall_seconds'),
        ('status_check_20261020T195435Z/query_receipt.json','local_wall_seconds'),
        ('timeout_diagnosis_20261020/query_receipt.json','wall_seconds')]
    control_facts=[]
    for rel,key in controls:
        doc=json.loads((retained/rel).read_text())
        control_facts.append(dict(receipt=rel,sha256=digest(retained/rel),wall_seconds=doc[key]))
    wall=ledger['total_job_wall_seconds']+sum(x['wall_seconds'] for x in control_facts)
    dispatch=json.loads((retained/'dispatch_receipt_attempt1.json').read_text())
    cpu=ledger['cpu_seconds']+dispatch['local_self_cpu_seconds']
    authority='同意，请按这个优先顺序推进数值求解器修复，复用现有代码，先完成实现、相关测试和必要的独立复审。保持物理接受精度和历史更新规则不变，无误后重跑'
    receipt=dict(schema='hybrid-budget-reconciliation-v1',complete=False,
        preparation_status='R2_TERMINAL_SETTLED_R3_STAGE_AND_FINAL_BINDING_PENDING',
        settled_runs=['pf_hybrid_full_20261019_r1','pf_hybrid_validate_20261020_01',
                      'pf_hybrid_validate_20261020_02','pf_hybrid_complete_20261020_r2'],
        active_or_unknown_runs=[],snapshot_epoch=d['observed_epoch'],
        source_snapshot_sha256=digest(snapshot),old_attributed_processes=d['processes'],
        r2_terminal=d['records']['terminal.json'],r2_cost_ledger=ledger,
        control_facts=control_facts,
        charged=dict(wall_seconds=wall,cpu_seconds=cpu,gpu_seconds=ledger['gpu_seconds'],numerical_seconds=ledger['numerical_seconds']),
        accounting='R2 cumulative study total already contains R1/validation/pre-R2 prep once; do not add those again. Measured local dispatch/query durations charged as separate control work; overlapping calendar wall is conservatively not deducted. R3 staging has not executed and is not recorded as zero actual work.',
        missing_observations=dict(control_cpu_seconds=None,initial_R2_monitor_query_wall_seconds=None,meaning='not measured; not zero. Scientific worker costs are settled; missing historical read-only control observations are disclosed, never reconstructed as actual.'),
        historical_control_reserve_seconds=600,
        reserve_policy='Unmeasured historical control margin, not observed actual work. Subtract600s from outer GNU-timeout usable allowance within original136h; never include in charged actual wall/CPU.',
        remaining_numerical_steps=3600,remaining_training_fits=1,
        authority=dict(quote=authority,scope='one NEW complete 3600-step attempt, same data/producer/physical tolerances; original total resource caps retained; first scientific failure stops, no retry',new_retry_authority=True),
        scientific_attempts=[dict(run='pf_hybrid_full_20261019_r1',accepted_train_A=1,failed_substep=2),
                             dict(run='pf_hybrid_validate_20261020_02',accepted_train_A=1,failed_substep=2,role='bounded diagnostic'),
                             dict(run='pf_hybrid_complete_20261020_r2',accepted_train_A=1,failed_substep=2)],
        synthetic_control_steps='Other artificial supervisor/control checks remain in original linux_validation_result_v1.json; not FEM labels or new physical axes.',
        training_fits_consumed=0,prior_labels_admitted_to_v6=False,
        next_binding='Add actual successful R3 stage receipt/cost, fresh identity/resource check, exact enabled-card and independent execution review; do not change a scientific failure into a mechanical retry.')
    card=copy.deepcopy(json.loads((code/OWNER/'accepted_state_preparation_card_v5.json').read_text())['execution_template'])
    run='pf_hybrid_solver_v6_20261020_r3'
    rel_receipt=V6+'/budget_reconciliation.json'
    out.mkdir(parents=True);stage=out/'code';stage.mkdir()
    # Store the actual retained receipt, not a result inferred from old progress.
    dump(code/V6/'r2_terminal_evidence.json',dict(source_snapshot_sha256=digest(snapshot),hostname=d['hostname'],observed_epoch=d['observed_epoch'],records={k:d['records'][k] for k in ['terminal.json','cost_ledger.json','failure.json','launch_receipt.json','launch_reservation.json','monitor.json']},processes=d['processes'],case_events=d['case_events']))
    dump(code/rel_receipt,receipt)
    card.update(run_id=run,run_root='/mnt/data2/drtao/wennie/'+run,archive_root='/mnt/data2/drtao/pidl_archives/'+run,
        execution_enabled=False,preparation_status='LOCAL_REVIEWABLE_REMOTE_STAGE_BLOCKED_BY_AUTO_APPROVAL',
        numerical_solver_revision='coupled-recycle-v6',historical_control_reserve_seconds=600,prior_terminal_run='pf_hybrid_complete_20261020_r2')
    card['solver']['wall_seconds']=300.
    card['coupling'].update(mode='projected_anderson_monotone',mechanics_solver='recycled_gmres',max_rejections=3)
    card['method_revision']['mechanics']='current K/rhs GMRES with old-LU preconditioner; bounded exact current-LU fallback; final current-K LU/pivot certificate; same policy in all arms'
    card['method_revision']['coupling']='strict fresh-merit improvement for intermediate trials, max3 proposals/rejections; physical acceptance unchanged; complete cache/domain rollback'
    card['method_revision']['reuse']='full exact CSC/free-domain key for exact LU; stale LU used only as preconditioner; no stale exact-key promotion'
    card['method_revision']['accepted_state']='D13 same accepted-state timing; true f_solve and fresh f_commit distinct; immutable old-state history map and CAS unchanged'
    card['stopping_details'].update(substep_solver_deadline_seconds=300,meaning='300s prospective cooperative deadline and Linux pidfd watchdog trigger; original total/phase budgets and cleanup reserves unchanged; no reset of the step clock. Actual elapsed includes cleanup and is reported.')
    card['authority']=copy.deepcopy(receipt['authority'])
    card['authority'].update(new_numerical_execution_authorized=True,remote_action_blocked='auto-review requires user confirmation of exact destination/script/copy before staging; no stage, dispatch or science has occurred')
    card['budget']['remaining_host_hours_after_all_known_prior_runs']=136-(wall+600)/3600
    card['budget_reconciliation']=dict(complete=False,receipt=rel_receipt,receipt_sha256=digest(code/rel_receipt),active_or_unknown_runs=[],remaining_numerical_steps=3600,remaining_training_fits=1,current_remaining_host_hours=136-(wall+600)/3600,current_remaining_gpu_hours=12.,historical_control_reserve_seconds=600,pending='R3 stage actual receipt/cost and final exact execution binding')
    card['prior_costs']=[dict(source=rel_receipt,sha256=digest(code/rel_receipt),lineage=receipt['settled_runs']+['pf_hybrid_r2_dispatch_and_diagnosis_control'],metrics={k:['charged',k] for k in receipt['charged']},cost_only_not_admission=True)]
    dump(code/V6/'execution_card_disabled.json',card)
    prior=json.loads((code/OWNER/'accepted_state_source_manifest_v5.json').read_text())
    files=set(prior['files'])|{OWNER+'/accepted_state_source_manifest_v5.json',OWNER+'/accepted_state_review_v5.md',
        'tests/test_hybrid_solver_repair_v6.py','tools/stage_hybrid_solver_v6.py','tools/receive_hybrid_solver_v6.py'}
    files.update(str(p.relative_to(code)) for p in (code/V6).iterdir() if p.is_file() and p.name not in {'source_manifest.json','execution_review.json','execution_review.md','packet_check.json'})
    for rel in sorted(files):
        target=stage/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(code/rel,target)
    package=dict(schema='hybrid-solver-source-v6',source_commit=subprocess.check_output(['git','-C',str(code),'rev-parse','HEAD'],text=True).strip(),base_owner_commit='edbba209',files={rel:digest(stage/rel) for rel in sorted(files)},scope='disabled local packet; no science, staging or execution review admission')
    package['artifact_id']=hashlib.sha256(json.dumps(package['files'],sort_keys=True,allow_nan=False).encode()).hexdigest()
    dump(out/'source_manifest.json',package);dump(code/V6/'source_manifest.json',package)
    dump(out/'execution_card_disabled.json',card)
    dump(out/'build_receipt.json',dict(source_commit=package['source_commit'],artifact_id=package['artifact_id'],card_sha256=digest(out/'execution_card_disabled.json'),file_count=len(files),source_bytes=sum((stage/p).stat().st_size for p in files),execution_enabled=False,ssh_calls=0,numerical_solves=0,training_updates=0,scientific_arrays_decoded=False,stage_has_not_executed=True))
    return package['artifact_id']


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--retained',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(build(Path(__file__).resolve().parents[5],a.retained,a.out))
