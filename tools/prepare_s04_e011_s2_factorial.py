#!/usr/bin/env python3
"""Build local c1s2 controlled diagnostic snapshot; no network/solve."""
import argparse,hashlib,json
from pathlib import Path

def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def build(prior,out,root,commit):
 assert not out.exists();out.mkdir(parents=True)
 old=prior/'retrieved';oldmanifest=json.loads((old/'input_manifest.json').read_text());here=Path(__file__).parent/'s04_e011_analysis'
 names=['e011_original_step.m','e011_coupled_solve.m','e011_displacement_solve.m','e011_damage_solve.m','e011_raw_equivalence.m','e011_damage_selftest.m','e011_coupled_selftest.m','e011_commit_selftest.m','e011_commit_once.m','e011_persist_once.m']
 for name in names:(out/name).write_bytes((old/name).read_bytes())
 (out/'e011_s2x_case.m').write_bytes((here/'s2_factorial/e011_s2x_case.m').read_bytes())
 driver=(old/'run_s04_e011_c1_commit.m').read_text().split('assert(options.max_cycle==1')[0].replace('run_s04_e011_c1_commit','run_s04_e011_s2x',1)
 driver+='''
assert(string(options.topology)=="q4" && cfg.displacement_tol==1e-6 && cfg.pf_tol==4e-4 && cfg.staggered_tol==4e-4);
assert(cfg.max_iter_staggered==1000 && cfg.max_iter_phase==250 && cfg.max_iter_displacement==250);
m=options.manifest;common=load(m.staging(1).target,'node_coords','connectivity','free_dof_u','free_dof_d');
assert(isequal(common.node_coords,sys.MESH.node(:,1:2)) && isequal(common.connectivity,sys.MESH.elem(:,1:4)));
assert(isequal(common.free_dof_u,sys.DOFS.active_dof) && isequal(common.free_dof_d,sys.DOFS.active_dof_pf));
a=load(m.staging(3).target,'proposed');b=load(m.staging(4).target,'proposed');
preO=a.proposed;preR=b.proposed;clear a b
assert(preO.version==1 && preR.version==1 && isequal(preO.lower,preO.d) && isequal(preR.lower,preR.d));
refO=load(m.staging(5).target,'candidate','proof','out');refR=load(m.staging(6).target,'candidate','proof','out');
par=struct('inner',SOL_PAR,'stag',SOL_STAG_PAR,'step',SOL_STEP_PAR,'crack',CRACK_PAR);
startO=struct('u',preO.u,'d',preO.d);startR=struct('u',preR.u,'d',preR.d);
anchorOO=e011_s2x_case('original',preO,startO,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,'anchor_OO'),refO,[],[]);
anchorRR=e011_s2x_case('repaired',preR,startR,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,'anchor_RR'),refR,[],[]);
clear refO refR
warm=struct('u',preO.u,'d',max(preO.d,preR.d));
assert(all(warm.d>=preO.lower & warm.d>=preR.lower));
[OO,predictor,cache]=e011_s2x_case('original',preO,warm,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,'C_OO'),[],[],[]);
[RO,~,~]=e011_s2x_case('repaired',preO,warm,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,'C_RO'),[],cache,predictor);
[OR,~,~]=e011_s2x_case('original',preR,warm,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,'C_OR'),[],cache,predictor);
[RR,~,~]=e011_s2x_case('repaired',preR,warm,sys,assembly_equilibrium_fh,assembly_pf_fh,par,fullfile(work_dir,'C_RR'),[],cache,predictor);
result=struct('status','completed','cases',struct('anchor_OO',anchorOO,'anchor_RR',anchorRR,'C_OO',OO,'C_RO',RO,'C_OR',OR,'C_RR',RR),'history_commits',0,'recovery_calls',0,'shared_setup_initial_assemblies',1,'cycle',1,'substep',2,'source_commit',m.source_commit,'scope','synthetic c1s2 diagnostic; no accepted state advances');
fid=fopen(fullfile(work_dir,'result.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(result));fclose(fid);
fprintf('[E011_S2X_DONE] cases=6 history_commits=0\\n');
end
function invalidConfig(message)
error('E011:InvalidConfig','%s',message);
end
'''
 (out/'run_s04_e011_s2x.m').write_text(driver)
 oldroot=r'C:\Users\xw436\jobs\E011_C1_20261016_v4_r1'
 paths=[('common',old/'output/c1_commit/common_initial.mat',oldroot+r'\output\c1_commit\common_initial.mat'),('mesh',old/'inputs/0e6db55abde58802_0e6db55abde58802_native_q4_original.inp',oldroot+r'\inputs\0e6db55abde58802_0e6db55abde58802_native_q4_original.inp')]
 for arm,s,role in [('original',1,'O1'),('repaired',1,'R1'),('original',2,'O2'),('repaired',2,'R2')]:
  paths.append((role,old/f'output/c1_commit/{arm}/s{s}/accepted_commit.mat',oldroot+fr'\output\c1_commit\{arm}\s{s}\accepted_commit.mat'))
 staging=[dict(role=role,source=remote,target=root+'\\inputs\\'+role+'_'+p.name,sha256=sha(p),bytes=p.stat().st_size) for role,p,remote in paths]
 manifest={k:oldmanifest[k] for k in ['source_checks','binary_checks']};manifest.update(staging=staging,source_commit=commit,protocol_revision='S04-E011-S2X-r1')
 (out/'input_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 entry=(old/'entry.m').read_text().split('try\n')[0].replace(oldroot,root)+'try\n'
 entry+='\n'.join(f"assert(strcmpi(phase_field.audit.sha256_file(fullfile(root,'{p.name}')),'{sha(p)}'));" for p in sorted(out.glob('*.m')))+'\n'
 entry+="reviewed_names={"+','.join("'"+p.name+"'" for p in sorted(out.glob('*.m')))+",'entry.m'};\n"
 entry+='''for q=1:numel(reviewed_names)
 cc=checkcode(fullfile(root,reviewed_names{q}),'-id');disp(cc);
 for j=1:numel(cc),assert(ismember(string(cc(j).id),{'NASGU','MSNU'}),'E011:StaticCheck','Unexpected static finding');end
end
manifest=jsondecode(fileread(fullfile(root,'input_manifest.json')));
assert(strcmp(manifest.protocol_revision,'S04-E011-S2X-r1') && isstruct(manifest.binary_checks) && numel(manifest.binary_checks)==10);
for k=1:numel(manifest.source_checks)
 sc=manifest.source_checks(k);assert(strcmpi(phase_field.audit.sha256_file(fullfile(source,sc.path)),sc.sha256));assert(~isempty(fileread(fullfile(source,sc.path))));
end
for k=1:numel(manifest.binary_checks)
 bc=manifest.binary_checks(k);assert(strcmpi(which(bc.name),bc.path));assert(strcmpi(phase_field.audit.sha256_file(which(bc.name)),bc.sha256));
end
self=struct('damage',e011_damage_selftest(),'coupled',e011_coupled_selftest(),'commit',e011_commit_selftest(fullfile(root,'selftest_tmp')),'raw',e011_raw_equivalence());
fid=fopen(fullfile(root,'selftest.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(self));fclose(fid);
assert(numel(manifest.staging)==6);
for k=1:6
 item=manifest.staging(k);info=dir(item.target);assert(isscalar(info) && info.bytes==item.bytes);assert(strcmpi(phase_field.audit.sha256_file(item.target),item.sha256));
 if strcmp(item.role,'mesh')
  assert(startsWith(strtrim(fileread(item.target)),'*HEADING'));[io_mesh,~]=specimen.external.abaqus_import(item.target,'t',1.0);
  assert(io_mesh.num_node==86756 && io_mesh.num_elem==86408 && io_mesh.nel==4);
 else
  probe=load(item.target);assert(~isempty(fieldnames(probe)));clear probe
 end
end
z=load(manifest.staging(1).target,'node_coords','connectivity');assert(isequal(z.node_coords,io_mesh.node(:,1:2)) && isequal(z.connectivity,io_mesh.elem(:,1:4)));clear z io_mesh
cfg=build_SENS_hard_recovery_loading5_primary_config('C:\\Users\\xw436\\jobs\\S04_E011_ad749c8_20261005\\reference_bundle\\SENS_hard5_u012_eta0_formal_pidl_native_q4_v1');
cfg.output_identity='s2x';cfg.requested_cycles=1;cfg.defer_stop_until_cycle=1;
fid=fopen(fullfile(root,'io_preflight.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(struct('status','passed','unique_inputs',6,'native_field_solves',0)));fclose(fid);
options=struct('work_dir',fullfile(root,'output','s2x'),'source_root',source,'mesh_file',manifest.staging(2).target,'topology','q4','max_cycle',1,'validate_only',false,'source_checks',manifest.source_checks,'binary_checks',manifest.binary_checks,'manifest',manifest);
result=run_s04_e011_s2x(cfg,options);
fid=fopen(fullfile(root,'sequence_finished.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(result));fclose(fid);
catch exception
failure=struct('status','stopped_no_retry','identifier',exception.identifier,'message',exception.message,'history_commits',0);
fid=fopen(fullfile(root,'sequence_failure.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(failure));fclose(fid);rethrow(exception);
end
'''
 (out/'entry.m').write_text(entry)
 # Reuse tested detached staging/launch, replace complete immutable file checks.
 launch=(old/'launch_wmi.ps1').read_text();start=launch.index("if((Get-FileHash ($root+");end=launch.index('$manifest=')
 checks='\n'.join(f"if((Get-FileHash ($root+'\\{p.name}') -Algorithm SHA256).Hash.ToLower() -ne '{sha(p)}'){{throw 'Snapshot file changed: {p.name}'}}" for p in sorted(out.iterdir()))+'\n'
 launch=launch[:start]+checks+launch[end:]
 launch=launch.replace(oldroot,root).replace('pf_s04e011_c1_commit_20261016_v4_r1','pf_s04e011_s2x_20261016_v1').replace('67942510c38c420c9ebc343e88b781a018cd1c7b',commit).replace('$stageRows.Count -ne 8','$stageRows.Count -ne 6').replace('Expected eight inputs','Expected six inputs').replace('Exact package human approval and local review required; entry performs Windows checks before native solves','Task authorization and exact local review required; entry checks before native solves')
 (out/'launch_wmi.ps1').write_text(launch)
 files=[dict(name=p.name,sha256=sha(p),bytes=p.stat().st_size) for p in sorted(out.iterdir())]
 return dict(source_commit=commit,remote_root=root,files=files,staging=staging,source_prior=str(prior),protocol_revision='S04-E011-S2X-r1',bytes=sum(x['bytes'] for x in files))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--prior',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--remote-root',required=True);ap.add_argument('--commit',required=True);args=ap.parse_args()
 m=build(args.prior,args.out,args.remote_root,args.commit);(args.out.parent/'package_manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(m,indent=2))
