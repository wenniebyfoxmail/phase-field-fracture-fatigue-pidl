from pathlib import Path
import json,hashlib,shutil,importlib.util
p=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl');w=p/'.codex/worktrees/s04-sampling-multiscale-20261012';d=w/'docs/research/S04/S04-E024';v=d/'taobo_cpu2_v2';c=p/'local_archive/experiments/S04-E024/physical_field_budget_taobo_cpu2_package_20261020_v2';ctrl=c/'control';ctrl.mkdir(exist_ok=True)
old=p/'local_archive/experiments/S04-E024/physical_field_budget_package_20261020_v1/D013-offline-20261020-v1'
def read(x):return json.loads(x.read_text())
def sha(x):return hashlib.sha256(x.read_bytes()).hexdigest()
def write(x,y):x.write_text(json.dumps(y,indent=2)+'\n')
spec=importlib.util.spec_from_file_location('entry',v/'remote_entry.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
base=read(old/'receipts/nontraining.json');assert base['wall_seconds']==71.93754945798841
requirements=dict(python=dict(executable='/usr/bin/python3',implementation='CPython',minimum_inclusive='3.10',maximum_exclusive='3.13'),
 system='Linux',machine='x86_64',host='GPUServer8',account='drtao',versions=r.REQUIREMENTS,
 observed_current=None,observed_current_status='UNKNOWN_NOT_PROBED',
 provenance=dict(torch_numpy='2026-10-17 retrieved producer metadata; not current observation',scipy_matplotlib_psutil_threadpoolctl='proposed exact requirements matching prior reviewed dev API versions; not known installed on Taobo'),
 failure='abort without install, alternate interpreter, Mac fallback, retry or numerical solve')
rows=[]
for row in read(old/'inputs_manifest.json')['files']:
 rel='project/'+row['path'];rows.append(dict(source_local=str(p/row['path']),producer_relative_path=rel,destination=str(r.ROOT/rel),
  payload_member=rel,bytes=row['bytes'],sha256=row['sha256'],roles=row['roles'],source_policy='upload this exact existing local file; do not read old remote inputs'))
inputs=dict(files=rows,file_count=88,total_bytes=sum(x['bytes'] for x in rows),method='all88 carried once in approved tar; source local bytes only',
 pairs=read(old/'inputs_manifest.json')['pairs'],D012='exact three saved NPZ and original manifest included; never refit/re-solve historical heads')
write(ctrl/'inputs_manifest.json',inputs);write(ctrl/'requirements.json',requirements)
plan=read(old/'execution_plan.json');plan.update(package_id=r.PACK,stage='PREPARED_PENDING_FINAL_BINDING_AND_REVIEW',execution_host='Taobo/GPUServer8 producer, CPU2/0GPU; Mac development and transport client only',
 project=str(r.ROOT/'project'),control_root=str(r.ROOT),run_output=str(r.ROOT/'project/local_archive/experiments/S04-E024/physical_field_budget_execution_20261020_v2'),python='/usr/bin/python3',
 environment=requirements,remote_root=str(r.ROOT),input_policy='self-contained88 exact local files; no old remote archive dependency',
 authority='human final action-manifest/payload approval only; closed now',version_routing='v1 Mac retained ON_HOLD, v2 Linux deployment-only; scientific18 unchanged')
plan.pop('launcher_accounting',None);plan['nontraining_accounting']=dict(prior_charged_seconds=71.93754945798841,v2_local_preparation_reserved_seconds=10.,
 base_charged_seconds=81.93754945798841,transport_and_metadata_counted=True,deadline_handshake='same first SSH emits producer monotonic anchor before metadata; client ACK elapsed produces one conservatively early producer deadline; reused through dispatcher and science supervisor',producer_science_handoff_reserved_seconds=5.,phase_cap_seconds=300,no_reset=True)
plan['producer_accounting']=dict(archive_cap_bytes=1024**3,scope='fixed local prepared D013 archives from action manifest plus entire fresh producer root, combined; all transfer copies counted until deleted',
 temporary_copies_removed_after_verification=[str(r.ROOT/'payload.tar'),str(r.ROOT/'package/science.tar.gz')],original_inputs_or_archives_deleted=False,
 CPU2='2 Torch/BLAS/threadpool worker threads, serial states, not a core reservation',GPU_queries=0,environment_current='UNKNOWN until approved conditional metadata admission',
 resource_admission=dict(affinity_cpus_at_least=2,MemAvailable_bytes_at_least=4*1024**3,data2_free_bytes_at_least=2*1024**3,must_mount='/mnt/data2'))
write(ctrl/'plan.json',plan)
checks=dict(base,wall_seconds=81.93754945798841,prior_charged_seconds=71.93754945798841,v2_local_preparation_reserved_seconds=10.,
 wall_seconds_is_conservative_budget_charge=True,scope=base['scope']+'; v2 pure deployment fixtures and byte packaging only, no real Torch imports',
 note='v2 preparation/check/review compute must stay inside reserved10s; transfer/metadata and single producer5s handoff remain inside total300s; same-SSH anchor deadline includes network time; no prior cost reset')
(ctrl/'receipts').mkdir(exist_ok=True);write(ctrl/'receipts/nontraining.json',checks)
for src,dest in [('physical_field_budget_code_ready_review.json','code_ready.json'),('physical_field_budget_code_ready_review.md','code_ready.md'),('physical_field_budget_contract.json','contract.json'),('physical_field_budget_plan.md','plan_scientific.md')]:shutil.copyfile(d/src,ctrl/'receipts'/dest)
write(ctrl/'authorization.template.json',dict(user_approved_final_execution=False,remote_actions_authorized=False,training_authorized=False,scope=r.SCOPE,
 package_id=r.PACK,execution_commit=r.SCIENCE,remote_root=str(r.ROOT),user_approval_quote='',payload_sha256=None,payload_manifest_sha256=None,remote_entry_sha256=None,
 action_manifest_sha256=None,fixed_local_archive_bytes=None,base_nontraining_charge_seconds=81.93754945798841,note='closed template, actual values only after explicit final human approval'))
print('v2 proposed versions/mapping ready; actual environment UNKNOWN;88 local->exact producer paths, no remote access')
