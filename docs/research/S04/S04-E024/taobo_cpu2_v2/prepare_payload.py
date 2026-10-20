#!/usr/bin/env python3
"""Local bytes-only preparation. No model imports, SSH or scientific execution."""
from pathlib import Path
import hashlib,io,json,shutil,tarfile,time
P=Path('/Users/wenxiaofang/phase-field-fracture-with-pidl')
V=Path(__file__).resolve().parent
D=V.parent
C=P/'local_archive/experiments/S04-E024/physical_field_budget_taobo_cpu2_package_20261020_v2'
CTRL=C/'control'
OLD=P/'local_archive/experiments/S04-E024/physical_field_budget_package_20261020_v1'
CHECK=P/'local_archive/experiments/S04-E024/physical_field_budget_code_ready_v1'
ROOT='/mnt/data2/drtao/wennie/S04-E024-D013-CPU2-18d0e7cb-20261020-v2'
SCIENCE='18d0e7cb1153dc969c1ee0c21c77ada1297b2d89'
TREE='14f6ba5d4b0107e0655f711622ef51268222221e18666f65426bc11e42813c23'
SOURCE_SHA='4682bf96f178c4ca6dc9faf56a9f591cb687077e554240d77a997b818681d7b1'
def read(p):return json.loads(p.read_text())
def write(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while data:=f.read(1024**2):h.update(data)
 return h.hexdigest()
def ident(p):return dict(bytes=p.stat().st_size,sha256=sha(p))
def size(p):return sum(x.stat().st_size for x in p.rglob('*') if x.is_file())
def main():
 start=time.monotonic()
 wire=C/'D013_Taobo_CPU2_18d0e7cb_v2.tar'
 if wire.exists() or (CTRL/'action_manifest.json').exists():raise ValueError('new payload once; do not overwrite final artifacts')
 review=read(V/'deployment_review_r4.json')
 # The independent receipt uses PASS; source hashes are frozen in its files map.
 assert review['verdict']=='PASS'
 for name in ('remote_entry.py','transfer_and_start.py','test_deployment.py'):
  assert sha(V/name)==review['material_sha256'][name]
 for name in ('remote_entry.py','transfer_and_start.py','README_operational.md','deployment_review.md','deployment_review.json','deployment_review_r2.md','deployment_review_r2.json','deployment_review_r3.md','deployment_review_r3.json','deployment_review_r4.md','deployment_review_r4.json'):
  shutil.copyfile(V/name,CTRL/name)
 rows=read(CTRL/'inputs_manifest.json')['files'];assert len(rows)==88
 with (CTRL/'inputs_manifest.tsv').open('w') as f:
  f.write('source_local\tdestination\tbytes\tsha256\troles\n')
  for row in rows:
   path=Path(row['source_local'])
   assert not path.is_symlink() and ident(path)==dict(bytes=row['bytes'],sha256=row['sha256'])
   f.write('\t'.join([row['source_local'],row['destination'],str(row['bytes']),row['sha256'],'; '.join(row['roles'])])+'\n')
 source=OLD/'D013-offline-20261020-v1/D013_source_18d0e7cb.tar.gz'
 assert sha(source)==SOURCE_SHA
 with tarfile.open(source,'r:gz') as tf:
  members=tf.getmembers();assert all(x.isfile() or x.isdir() for x in members)
  source_unpacked=sum(x.size for x in members)
 plan=read(CTRL/'plan.json');plan['stage']='FINAL_PACKAGE_PREPARED_NOT_EXECUTED'
 write(CTRL/'plan.json',plan)
 # Only these metadata/receipt files accompany all88 original inputs.
 names=['remote_entry.py','README_operational.md','plan.json','requirements.json','inputs_manifest.json','inputs_manifest.tsv',
  'authorization.template.json','deployment_review_r4.json','deployment_review_r4.md']
 sources={'package/'+name:CTRL/name for name in names}
 sources.update({'package/receipts/'+p.name:p for p in (CTRL/'receipts').iterdir() if p.is_file()})
 sources['package/science.tar.gz']=source
 sources.update({row['payload_member']:Path(row['source_local']) for row in rows})
 files={name:ident(path) for name,path in sorted(sources.items())}
 payload=dict(package_id=plan['package_id'],science_commit=SCIENCE,science_tree_sha256=TREE,
  input_count=88,input_bytes=sum(x['bytes'] for x in rows),files=files)
 write(CTRL/'payload_manifest.json',payload)
 sources['package/payload_manifest.json']=CTRL/'payload_manifest.json'
 with tarfile.open(wire,'x',format=tarfile.USTAR_FORMAT) as tf:
  for name,path in sorted(sources.items()):
   info=tarfile.TarInfo(name);info.size=path.stat().st_size;info.mode=0o644;info.mtime=0
   with path.open('rb') as f:tf.addfile(info,f)
 wire_id=ident(wire)
 # Freeze all actual local D013 retained archives, including old checks/v1,
 # plus8MiB for final receipts/control/logs. No large duplicate wire/ZIP.
 local_roots=[OLD,CHECK,C]
 observed=sum(size(p) for p in local_roots)
 fixed_local=observed+8*1024**2
 staged_regular=sum(x['bytes'] for x in files.values())+(CTRL/'payload_manifest.json').stat().st_size
 # Wire+extracted members+uncompressed clean source, plus2MiB bootstrap/cache
 # and directory bookkeeping reserve. Runtime supervises actual whole ROOT.
 remote_peak=wire_id['bytes']+staged_regular+source_unpacked+2*1024**2
 assert fixed_local+remote_peak<=1024**3,(fixed_local,remote_peak)
 remote_after_cleanup=staged_regular-source.stat().st_size+source_unpacked+2*1024**2
 control_files={str(p.relative_to(CTRL)):ident(p) for p in sorted(CTRL.rglob('*')) if p.is_file()}
 manifest=dict(package_id=plan['package_id'],status='PREPARED_AWAITING_FINAL_HUMAN_APPROVAL',account='drtao@172.16.100.2',
  owner='Winnie/xw436',preparation_Mac_user='wenxiaofang',remote_host='GPUServer8',remote_root=ROOT,remote_python='/usr/bin/python3',
  science_commit=SCIENCE,science_tree_sha256=TREE,source_tar_sha256=SOURCE_SHA,
  control_bundle_dir=str(CTRL),control_files=control_files,payload_path=str(wire),payload_bytes=wire_id['bytes'],payload_sha256=wire_id['sha256'],
  payload_manifest_sha256=sha(CTRL/'payload_manifest.json'),remote_entry_sha256=sha(CTRL/'remote_entry.py'),
  input_count=88,input_bytes=sum(x['bytes'] for x in rows),wire_regular_member_count=len(sources),
  source_unpacked_bytes=source_unpacked,local_archive_roots=[str(p) for p in local_roots],
  observed_local_archive_bytes=observed,local_control_reserve_bytes=8*1024**2,fixed_local_archive_bytes=fixed_local,
  predicted_remote_peak_bytes=remote_peak,predicted_combined_peak_bytes=fixed_local+remote_peak,
  predicted_combined_after_transport_cleanup_bytes=fixed_local+remote_after_cleanup,
  predicted_science_output_headroom_bytes=1024**3-fixed_local-remote_after_cleanup,
  peak_bookkeeping_reserve_bytes=2*1024**2,archive_cap_bytes=1024**3,
  base_nontraining_charge_seconds=81.93754945798841,prior_nontraining_seconds=71.93754945798841,
  budget=plan['resource_caps'],scope='E024-D013-Taobo-CPU2-v2-12-profiles',
  approved=False,remote_actions_authorized=False,training_authorized=False,
  actions=[
   dict(order=1,kind='SSH',target='drtao@172.16.100.2',argv=['ssh','-F','/dev/null','-o','BatchMode=yes','-o','ConnectTimeout=15','drtao@172.16.100.2',"/usr/bin/python3 -c <shell-quoted exact remote_entry.py bytes> --bootstrap-create"],
    stdin='two-message same-SSH authority/producer-anchor deadline handshake; metadata/resource admission then fresh root claim; no Torch'),
   dict(order=2,kind='SCP',argv=['scp','-F','/dev/null','-o','BatchMode=yes','-o','ConnectTimeout=15',str(wire),'drtao@172.16.100.2:'+ROOT+'/payload.tar']),
   dict(order=3,kind='SSH',target='drtao@172.16.100.2',argv=['ssh','-F','/dev/null','-o','BatchMode=yes','-o','ConnectTimeout=15','drtao@172.16.100.2',"/usr/bin/python3 -c <shell-quoted same exact remote_entry.py bytes> --bootstrap-start"],
    stdin='same action approval plus SAME anchored deadline; full wire/entry hash then conditional detached --run'),
   dict(order=4,kind='CONDITIONAL_PRODUCER',checks='all payload/input88/source clean18/tree/receipts/environment/budget; no old remote input reads',
    temporary_deletions=[ROOT+'/payload.tar',ROOT+'/package/science.tar.gz'],
    command=['/usr/bin/python3',ROOT+'/code/SENS_tensile/run_s04_e024_field_budget.py','--execute-scientific','--project',ROOT+'/project',
     '--out',ROOT+'/project/local_archive/experiments/S04-E024/physical_field_budget_execution_20261020_v2','--expected-commit',SCIENCE,'--approval',ROOT+'/science_approval.json'])],
  stopping='first failure/unknown transport no retry or fallback, no later run; original scientific stops retained',
  deletion_scope='only two verified task-owned transport copies; local immutable wire, original inputs and old archives retained',
  current_environment_status='UNKNOWN_NOT_PROBED')
 write(CTRL/'action_manifest.json',manifest)
 wall=time.monotonic()-start
 write(C/'preparation_build_receipt.json',dict(stage='BYTES_ONLY_PREPARATION',wall_seconds=wall,
  action_manifest_sha256=sha(CTRL/'action_manifest.json'),payload_sha256=wire_id['sha256'],
  science_imports=0,real_Torch_imports=0,scientific_solves=0,SSH_calls=0,SCP_calls=0,true_authorizations_created=0))
 print(json.dumps(dict(payload=wire_id,action_manifest_sha256=sha(CTRL/'action_manifest.json'),
  combined_peak_bytes=fixed_local+remote_peak,science_output_headroom_bytes=manifest['predicted_science_output_headroom_bytes'],build_wall_seconds=wall),indent=2))
if __name__=='__main__':main()
