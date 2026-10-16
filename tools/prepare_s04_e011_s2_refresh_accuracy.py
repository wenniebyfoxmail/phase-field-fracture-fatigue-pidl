#!/usr/bin/env python3
"""Build same-origin R/A factorial snapshot locally; never launch."""
import argparse,json,hashlib
from pathlib import Path

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def build(prior,out,root,commit):
 assert not out.exists();out.mkdir(parents=True);old=prior/'retrieved'
 names=['e011_original_step.m','e011_coupled_solve.m','e011_displacement_solve.m','e011_damage_solve.m','e011_raw_equivalence.m','e011_damage_selftest.m','e011_coupled_selftest.m','e011_commit_selftest.m','e011_commit_once.m','e011_persist_once.m','e011_s2i_fatal.m']
 for name in names:(out/name).write_bytes((old/name).read_bytes())
 here=Path(__file__).parent/'s04_e011_analysis/s2_refresh_accuracy'
 for p in here.glob('*.m'):(out/p.name).write_bytes(p.read_bytes())
 fresh=(old/'e011_displacement_solve.m').read_text().replace('e011_displacement_solve(','e011_s2ra_fresh_u(',1)
 assert fresh.count('if value<=tol')==1
 fresh=fresh.replace('if value<=tol','if value<tol')
 (out/'e011_s2ra_fresh_u.m').write_text(fresh)
 s=(old/'run_s04_e011_s2i.m').read_text().split('assert(string(options.topology)')[0].replace('run_s04_e011_s2i','run_s04_e011_s2ra',1)
 s+='''
assert(string(options.topology)=="q4" && ~SOL_STEP_PAR.line_search);
m=options.manifest;z=load(m.staging(1).target,'node_coords','connectivity','free_dof_u','free_dof_d');
assert(isequal(z.node_coords,sys.MESH.node(:,1:2)) && isequal(z.connectivity,sys.MESH.elem(:,1:4)));
assert(isequal(z.free_dof_u,sys.DOFS.active_dof) && isequal(z.free_dof_d,sys.DOFS.active_dof_pf));clear z
z=load(m.staging(3).target,'proposed');pre=z.proposed;z=load(m.staging(4).target,'proposed');other=z.proposed;clear z
start=struct('u',pre.u,'d',max(pre.d,other.d));assert(pre.version==1 && other.version==1);
par=struct('step',SOL_STEP_PAR);
ref=load(m.staging(5).target,'current');
[r00,predictor,cache]=e011_s2ra_case([0 0],pre,start,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,'R0A0'),ref,[],[]);
assert(r00.reference.pass);
ref=load(m.staging(6).target,'current');
[r11,~,~]=e011_s2ra_case([1 1],pre,start,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,'R1A1'),ref,cache,predictor);
assert(r11.reference.pass);clear ref
[r10,~,~]=e011_s2ra_case([1 0],pre,start,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,'R1A0'),[],cache,predictor);
[r01,~,~]=e011_s2ra_case([0 1],pre,start,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,'R0A1'),[],cache,predictor);
result=struct('status','completed','history_commits',0,'recovery_calls',0,'shared_setup_initial_assemblies',1, ...
 'cases',struct('R0A0',r00,'R1A1',r11,'R1A0',r10,'R0A1',r01),'source_commit',m.source_commit,'cycle',1,'substep',2);
fid=fopen(fullfile(work_dir,'result.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(result));fclose(fid);
fprintf('[E011_S2RA_DONE] cases=4 history_commits=0\\n');
end
function invalidConfig(message)
error('E011:InvalidConfig','%s',message);
end
'''
 (out/'run_s04_e011_s2ra.m').write_text(s)
 manifest=json.loads((old/'input_manifest.json').read_text());oldroot=prior.name.replace('pf_s04e011_s2i_','E011_S2I_')
 remote_prior='C:\\Users\\xw436\\jobs\\'+oldroot
 staging=[]
 for i,item in enumerate(manifest['staging'][:4]):
  item=item.copy();p=old/'inputs'/Path(item['target'].replace('\\','/')).name
  item['source']=remote_prior+'\\inputs\\'+p.name;item['target']=root+'\\inputs\\'+p.name
  assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256'];staging.append(item)
 for name,case in [('anchor00','100'),('anchor11','110')]:
  p=old/'output/s2i'/case/'case.mat'
  staging.append(dict(role=name,source=remote_prior+'\\output\\s2i\\'+case+'\\case.mat',target=root+'\\inputs\\'+name+'_case.mat',bytes=p.stat().st_size,sha256=sha(p)))
 keys=['role','source','target','sha256','bytes'];staging=[{k:item[k] for k in keys} for item in staging]
 assert all(list(item)==keys and isinstance(item['bytes'],int) and item['bytes']>0 and len(item['sha256'])==64 and all(ch in '0123456789abcdef' for ch in item['sha256']) for item in staging)
 manifest.update(staging=staging,source_commit=commit,protocol_revision='S04-E011-S2RA-r1')
 (out/'input_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 previous=(old/'entry.m').read_text();entry=previous.split('try\n')[0].replace(remote_prior,root)+'try\n'
 entry+='\n'.join(f"assert(strcmpi(phase_field.audit.sha256_file(fullfile(root,'{p.name}')),'{sha(p)}'));" for p in sorted(out.glob('*.m')))+'\n'
 entry+="reviewed_names={"+','.join("'"+p.name+"'" for p in sorted(out.glob('*.m')))+",'entry.m'};\n"
 tail=previous[previous.index('for q=1:numel(reviewed_names)'):]
 tail=tail.replace('S04-E011-S2I-r1','S04-E011-S2RA-r1').replace("'isolation',e011_s2i_selftest()","'refresh_accuracy',e011_s2ra_selftest()")
 tail=tail.replace("cfg.output_identity='s2i'","cfg.output_identity='s2ra'").replace("'output','s2i'","'output','s2ra'").replace('run_s04_e011_s2i(cfg,options)','run_s04_e011_s2ra(cfg,options)')
 entry+=tail;(out/'entry.m').write_text(entry)
 launch=(old/'launch_wmi.ps1').read_text();begin=launch.index("if((Get-FileHash ($root+");end=launch.index('$manifest=')
 checks='\n'.join(f"if((Get-FileHash ($root+'\\{p.name}') -Algorithm SHA256).Hash.ToLower() -ne '{sha(p)}'){{throw 'Snapshot changed: {p.name}'}}" for p in sorted(out.iterdir()))+'\n'
 launch=launch[:begin]+checks+launch[end:]
 run_id='pf_s04e011_'+root.rsplit('\\',1)[-1].removeprefix('E011_').lower()
 launch=launch.replace(remote_prior,root).replace(prior.name,run_id).replace(json.loads((old/'input_manifest.json').read_text())['source_commit'],commit)
 (out/'launch_wmi.ps1').write_text(launch)
 files=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir())]
 return dict(source_commit=commit,remote_root=root,protocol_revision='S04-E011-S2RA-r1',files=files,staging=staging,bytes=sum(x['bytes'] for x in files),source_prior=str(prior))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--prior',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--root',required=True);ap.add_argument('--commit',required=True);z=ap.parse_args();m=build(z.prior,z.out,z.root,z.commit);(z.out.parent/'package_manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
