#!/usr/bin/env python3
"""Build fixed-strictphase inneru x joint/outeru tolerance snapshot; no launch."""
import argparse,json,hashlib
from pathlib import Path

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def build(prior,out,root,commit):
 assert not out.exists();out.mkdir(parents=True);old=prior/'retrieved'
 for p in old.glob('*.m'):
  if p.name not in ['entry.m','run_s04_e011_s2dj.m']:(out/p.name).write_bytes(p.read_bytes())
 here=Path(__file__).parent/'s04_e011_analysis/s2_u_joint'
 for p in here.glob('*.m'):(out/p.name).write_bytes(p.read_bytes())
 driver=(old/'run_s04_e011_s2dj.m').read_text().replace('run_s04_e011_s2dj','run_s04_e011_s2uj',1).replace('e011_s2dj_case','e011_s2uj_case')
 for oldname,newname in [('P0J0','U0J0'),('P1J1','U1J1'),('P1J0','U1J0'),('P0J1','U0J1')]:driver=driver.replace(oldname,newname)
 driver=driver.replace('[E011_S2DJ_DONE]','[E011_S2UJ_DONE]')
 (out/'run_s04_e011_s2uj.m').write_text(driver)
 previous=json.loads((old/'input_manifest.json').read_text());remote_prior=prior.name.replace('pf_s04e011_s2dj_','C:\\Users\\xw436\\jobs\\E011_S2DJ_')
 staging=[]
 for t in previous['staging'][:4]:
  t=t.copy();p=old/'inputs'/Path(t['target'].replace('\\','/')).name
  assert p.stat().st_size==t['bytes'] and sha(p)==t['sha256']
  t.update(source=remote_prior+'\\inputs\\'+p.name,target=root+'\\inputs\\'+p.name);staging.append(t)
 for role,case in [('anchor00','P1J0'),('anchor11','P1J1'),('scale_reference','P0J0')]:
  p=old/'output/s2dj'/case/'case.mat';staging.append(dict(role=role,source=remote_prior+'\\output\\s2dj\\'+case+'\\case.mat',target=root+'\\inputs\\'+role+'_case.mat',sha256=sha(p),bytes=p.stat().st_size))
 keys=['role','source','target','sha256','bytes'];staging=[{k:t[k] for k in keys} for t in staging]
 assert all(isinstance(t['bytes'],int) and t['bytes']>0 and len(t['sha256'])==64 for t in staging)
 previous.update(staging=staging,source_commit=commit,protocol_revision='S04-E011-S2UJ-r1')
 (out/'input_manifest.json').write_text(json.dumps(previous,indent=2)+'\n')
 oldentry=(old/'entry.m').read_text();entry=oldentry.split('try\n')[0].replace(remote_prior,root)+'try\n'
 entry+='\n'.join(f"assert(strcmpi(phase_field.audit.sha256_file(fullfile(root,'{p.name}')),'{sha(p)}'));" for p in sorted(out.glob('*.m')))+'\n'
 entry+="reviewed_names={"+','.join("'"+p.name+"'" for p in sorted(out.glob('*.m')))+",'entry.m'};\n"
 tail=oldentry[oldentry.index('for q=1:numel(reviewed_names)'):]
 tail=tail.replace('S04-E011-S2DJ-r1','S04-E011-S2UJ-r1').replace("'damage_joint',e011_s2dj_selftest()","'damage_joint',e011_s2dj_selftest(),'u_joint',e011_s2uj_selftest()")
 tail=tail.replace("cfg.output_identity='s2dj'","cfg.output_identity='s2uj'").replace("'output','s2dj'","'output','s2uj'").replace('run_s04_e011_s2dj(cfg,options)','run_s04_e011_s2uj(cfg,options)')
 tail=tail.replace('numel(manifest.staging)==6','numel(manifest.staging)==7').replace('for k=1:6','for k=1:7').replace("'unique_inputs',6","'unique_inputs',7")
 entry+=tail;(out/'entry.m').write_text(entry)
 launch=(old/'launch_wmi.ps1').read_text().replace('$stageRows.Count -ne 6','$stageRows.Count -ne 7').replace('Expected six inputs','Expected seven inputs');start=launch.index("if((Get-FileHash ($root+");end=launch.index('$manifest=')
 checks='\n'.join(f"if((Get-FileHash ($root+'\\{p.name}') -Algorithm SHA256).Hash.ToLower() -ne '{sha(p)}'){{throw 'Snapshot changed: {p.name}'}}" for p in sorted(out.iterdir()))+'\n'
 launch=launch[:start]+checks+launch[end:]
 run_id='pf_s04e011_'+root.rsplit('\\',1)[-1].removeprefix('E011_').lower()
 launch=launch.replace(remote_prior,root).replace(prior.name,run_id).replace(json.loads((old/'input_manifest.json').read_text())['source_commit'],commit)
 assert '$stageRows.Count -ne 7' in launch and '$stageRows.Count -ne 6' not in launch and len(staging)==7 and 'numel(manifest.staging)==7' in entry
 (out/'launch_wmi.ps1').write_text(launch)
 files=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir())]
 return dict(source_commit=commit,remote_root=root,protocol_revision='S04-E011-S2UJ-r1',files=files,staging=staging,bytes=sum(t['bytes'] for t in files),source_prior=str(prior))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--prior',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--root',required=True);ap.add_argument('--commit',required=True);z=ap.parse_args();m=build(z.prior,z.out,z.root,z.commit);(z.out.parent/'package_manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
