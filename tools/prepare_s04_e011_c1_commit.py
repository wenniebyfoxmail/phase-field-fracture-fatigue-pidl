#!/usr/bin/env python3
"""Prepare an exact local approval bundle for one c1 sequence; no network/launch."""
import argparse,hashlib,json
from pathlib import Path
from prepare_s04_e011_endpoint_baseline import unique_before


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def original_step(solver):
    start='        for i_stag = 1:SOL_STAG_PAR.max_iter\n';end='            if stag_converged\n'
    assert solver.count(start)==solver.count(end)==1
    loop=solver.split(start)[1].split(end)[0]
    return '''function out=e011_original_step(sys,assembly_equilibrium_fh,assembly_pf_fh,displ,p_field,p_field_old,history_vars_old,res_displ,D_RHS_tract,par,work_dir,counts_fh,i_step)
%E011_ORIGINAL_STEP Exact frozen original numerical loop, pre-commit return.
SOL_PAR=par.inner;SOL_STAG_PAR=par.stag;SOL_STEP_PAR=par.step;CRACK_PAR=par.crack;
SOL_CYCL_VAR=struct('n_cycle',1);example_name=char(work_dir);
SOL_STAG_VAR=phase_field.fem.solver.stag.vars(SOL_STAG_PAR);
regularize_pf_newton=true;damage_upper_bound=1;
native_q4_capture=struct('enabled',false);
res_displ_0=norm(res_displ(sys.DOFS.active_dof,1));
frozen_lower=p_field_old;frozen_history=history_vars_old;
trace=[];native_accepted=false;
try
for i_stag=1:SOL_STAG_PAR.max_iter
'''+loop+'''
 assert(isequaln(p_field_old,frozen_lower) && isequaln(history_vars_old,frozen_history));
 row=struct('outer',i_stag,'cached_d',res_pf,'fresh_u',SOL_STAG_VAR.normal_res_displ(i_stag), ...
  'cached_sum',SOL_STAG_VAR.normal_res_displ(i_stag)+res_pf,'native_accepted',stag_converged);
 observed=counts_fh();row.native_u_calls=observed.u;row.native_d_calls=observed.d;
 if isempty(trace),trace=row;else,trace(end+1)=row;end %#ok<AGROW>
 save(fullfile(work_dir,'original_progress.mat'),'displ','p_field','strain_en_undgr','trace','i_stag','-v7.3');
 if stag_converged,native_accepted=true;break;end
end
assert(native_accepted,'E011:OriginalOuterCap','Original staggered cap exhausted');
out=struct('u',displ,'d',p_field,'raw',strain_en_undgr,'trace',trace, ...
 'completed_outer',i_stag,'native_accepted',native_accepted, ...
 'native_returned_trial_history234',history_vars_new(:,:,2:4));
catch ex
 save(fullfile(work_dir,'original_failure.mat'),'displ','p_field','p_field_old','history_vars_old','trace','i_stag','-v7.3');
 rethrow(ex);
end
end
'''


def driver(base_driver,recovery_driver):
    marker='\n\nassert(string(options.topology)=="q4");'
    assert base_driver.count(marker)==1
    prefix=base_driver.split(marker)[0].replace('run_s04_e011_coupled_repair(cfg, options)','run_s04_e011_c1_commit(cfg, options)',1)
    init='init_fatigue_fracture\n'
    assert prefix.count(init)==1
    prefix=prefix.replace(init,'''% Explicit placeholders; frozen native init overwrites all before use.
p_field=[];p_field_old=[];history_vars_old=[];
init_fatigue_fracture
assert(isequal(size(p_field),[sys.MESH.num_node,1]));
assert(isequal(size(p_field_old),size(p_field)));
assert(isequal(size(history_vars_old),[sys.MESH.num_elem,sys.QUADRATURE.num_gauss_pts,4]));
''')
    return prefix+'''
assert(options.max_cycle==1 && isequal(cfg.requested_cycles,1) && string(options.topology)=="q4");
assert(cfg.displacement_tol==1e-6 && cfg.pf_tol==4e-4 && cfg.staggered_tol==4e-4);
assert(cfg.max_iter_staggered==1000 && cfg.max_iter_phase==250 && cfg.max_iter_displacement==250);
strain_en_undgr=zeros(sys.MESH.num_elem,sys.QUADRATURE.num_gauss_pts);
[p_field,p_field_old,history_vars_old,recovery_calls,res_pf_recovery]=e011_shared_recovery(sys,assembly_pf_fh,p_field,p_field_old,history_vars_old,SOL_PAR,damage_upper_bound);
'''+'''
assert(all(displ==0) && all(strain_en_undgr==0,'all'));
assert(all(history_vars_old(:,:,2:3)==0,'all') && all(history_vars_old(:,:,4)==1,'all'));
z=load(options.state0_file);assert(isequal(z.state0_node(:,1:2),sys.MESH.node(:,1:2)));
state0_maxerr=max(abs(z.state0_p_field-p_field));assert(state0_maxerr<=1e-10,'E011:RecoveryRegression','Recovery does not reproduce original state0');
common=struct('u',displ,'d',p_field,'lower',p_field_old,'raw',strain_en_undgr,'history',history_vars_old,'version',0);
% Keep the EXACT initial predictor tangent from the original System setup:
% original recovery is phase-only and does not refresh KK. Do not rebuild it.
initial_KK=sys.STIFFNESS_MATRIX.KK;
common_meta=struct('recovery_phase_calls',recovery_calls,'recovery_cached_residual',res_pf_recovery, ...
'state0_maxerr',state0_maxerr, ...
 'initialization_resets',1,'shared_setup_initial_assemblies',1,'cycle',1,'version',0,'source_commit',options.source_commit, ...
 'initial_KK_timing','Original System stiffness cache at first access, based on constructor hard precrack');
node_coords=sys.MESH.node(:,1:2);connectivity=sys.MESH.elem(:,1:4);
free_dof_u=sys.DOFS.active_dof;free_dof_d=sys.DOFS.active_dof_pf;
save(fullfile(work_dir,'common_initial.mat'),'common','common_meta','initial_KK','node_coords','connectivity','free_dof_u','free_dof_d','-v7.3');
par=struct('inner',SOL_PAR,'stag',SOL_STAG_PAR,'step',SOL_STEP_PAR,'crack',CRACK_PAR);
refs=options.references;
original=e011_c1_arm('original',common,initial_KK,sys,assembly_equilibrium_fh,assembly_pf_fh,par,refs,fullfile(work_dir,'original'));
assert(original.steps==5 && original.history_commits==5 && all([original.rows.reference_pass]));
repaired=e011_c1_arm('repaired',common,initial_KK,sys,assembly_equilibrium_fh,assembly_pf_fh,par,refs,fullfile(work_dir,'repaired'));
assert(repaired.steps==5 && repaired.history_commits==5 && repaired.all_precommit_joint_pass);
result=struct('status','completed','original',original,'repaired',repaired, ...
 'recovery_phase_calls',recovery_calls,'initialization_resets',1, ...
 'history_commits',10,'scope','one synthetic c1 loading-unloading paired numerical diagnostic');
save(fullfile(work_dir,'c1_result.mat'),'result','common_meta','-v7.3');
fid=fopen(fullfile(work_dir,'c1_result.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(result));fclose(fid);
fprintf('[E011_C1_SEQUENCE_DONE] original_commits=5 repaired_commits=5 resets=1\\n');

end
function invalidConfig(message)
error('E011:InvalidConfig','%s',message);
end
'''



def shared_recovery(recovery_driver):
    recovery=unique_before(recovery_driver,'\ninitial_state_metadata = buildInitialMetadata').split('\nstrain_en_undgr = zeros(sys.MESH.num_elem, sys.QUADRATURE.num_gauss_pts);')[1]
    recovery='\nstrain_en_undgr = zeros(sys.MESH.num_elem, sys.QUADRATURE.num_gauss_pts);'+recovery
    assert recovery.count('    assembly_pf_fh, sys,')==1
    recovery=recovery.replace('    assembly_pf_fh, sys,','    @counted, sys,')
    return """function [p_field,p_field_old,history_vars_old,calls,res_pf_recovery]=e011_shared_recovery(sys,native_pf,p_field,p_field_old,history_vars_old,SOL_PAR,damage_upper_bound)
%E011_SHARED_RECOVERY Exact original recovery; isolated from script workspace.
calls=0;
"""+recovery+"""
 function [kv,r,aux,h]=counted(varargin)
  assert(calls<250,'E011:RecoveryBudget','Recovery phase cap');calls=calls+1;
  [kv,r,aux,h]=native_pf(varargin{:});
 end
end
"""


def build(source_root,prior,reference_root,mesh,out,remote_root,commit,inventory):
    assert not out.exists() and remote_root.endswith('E011_C1_20261016_v2')
    out.mkdir(parents=True)
    here=Path(__file__).parent/'s04_e011_analysis';native=json.loads((prior/'input_manifest.json').read_text())[0]
    source_ids={x['path']:x['sha256'] for x in native['source_checks']}
    for item in inventory['source_files']:
        assert hashlib.sha256(item['text'].encode()).hexdigest()==item['sha256']
        native['source_checks'].append({k:item[k] for k in ['path','sha256']})
        native['binary_checks'].append(dict(name={
            'Sources/+phase_field/System.m':'phase_field.System',
            'Sources/+phase_field/+init/stiffness_matrix.m':'phase_field.init.stiffness_matrix',
            'Sources/+phase_field/+fem/+solver/+step/pre_iter_update.m':'phase_field.fem.solver.step.pre_iter_update'}[item['path']],
            path=r'C:\Users\xw436\jobs\S04_E011_ad749c8_20261005\source'+'\\'+item['path'].replace('/','\\'),sha256=item['sha256']))
    native['binary_checks'].append(inventory['initial_binary'])
    paths=['Scripts/fatigue_fracture/run_SENS_hard_recovery_native_q4_capture.m','Scripts/fatigue_fracture/solve_fatigue_fracture.m']
    for p in paths:assert sha(source_root/p)==source_ids[p]
    (out/'e011_original_step.m').write_text(original_step((source_root/paths[1]).read_text()))
    (out/'e011_shared_recovery.m').write_text(shared_recovery((source_root/paths[0]).read_text()))
    (out/'run_s04_e011_c1_commit.m').write_text(driver((here/'coupled_repair/run_s04_e011_coupled_repair.m').read_text(),(source_root/paths[0]).read_text()))
    for folder,names in [('c1_commit',['e011_c1_arm.m','e011_commit_once.m','e011_commit_selftest.m','e011_persist_once.m']),('coupled_repair',['e011_coupled_solve.m','e011_displacement_solve.m','e011_coupled_selftest.m']),('constrained_damage',['e011_damage_solve.m','e011_damage_selftest.m'])]:
        for name in names:(out/name).write_bytes((here/folder/name).read_bytes())
    remote_reference=r'C:\Users\xw436\OneDrive - University of Cambridge\griphfith\S04_E011_raw_outputs_ad749c8_20261005_backup_20261015\S04_E011_FEM_Q4_C120'
    staging=[]
    for role,path,remote in [('state0',reference_root/'state0_analysis.mat',remote_reference+r'\state0_analysis.mat'),('metadata',reference_root/'initial_state_metadata.mat',remote_reference+r'\initial_state_metadata.mat'),('mesh',mesh,r'C:\Users\xw436\jobs\E011_CR_20261015_v3\inputs\0e6db55abde58802_native_q4_original.inp')]+[(f'substep{k}',reference_root/f'request28_post_commit/c0001_s{k:03d}_post_commit.mat',remote_reference+fr'\request28_post_commit\c0001_s{k:03d}_post_commit.mat') for k in range(1,6)]:
        h=sha(path);staging.append(dict(role=role,source=remote,target=remote_root+'\\inputs\\'+h[:16]+'_'+path.name,sha256=h,bytes=path.stat().st_size,local_reference=str(path)))
    assert len(staging)==8
    manifest=dict(source_checks=native['source_checks'],binary_checks=native['binary_checks'],staging=[{k:v for k,v in x.items() if k!='local_reference'} for x in staging],source_commit=commit)
    (out/'input_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    helper_checks='\n'.join(f"assert(strcmpi(phase_field.audit.sha256_file(fullfile(root,'{p.name}')),'{sha(p)}'));" for p in sorted(out.glob('*.m')))
    names="{"+','.join("'"+p.name+"'" for p in sorted(out.glob('*.m')))+",'entry.m'}"
    entry=r'''root='@ROOT@';
source='C:\Users\xw436\jobs\S04_E011_ad749c8_20261005\source';
addpath(fullfile(source,'Sources'));addpath(fullfile(source,'Scripts','fatigue_fracture'));addpath(root);
addpath(genpath(fullfile(source,'Dependencies')));
try
@HELPERS@
reviewed_names=@NAMES@;
for q=1:numel(reviewed_names)
 cc=checkcode(fullfile(root,reviewed_names{q}),'-id');disp(cc);
 for j=1:numel(cc),assert(ismember(string(cc(j).id),{'NASGU','MSNU'}),'E011:StaticCheck','Unexpected static finding');end
end
manifest=jsondecode(fileread(fullfile(root,'input_manifest.json')));
for k=1:numel(manifest.source_checks)
 sc=manifest.source_checks(k);assert(strcmpi(phase_field.audit.sha256_file(fullfile(source,sc.path)),sc.sha256));
 assert(~isempty(fileread(fullfile(source,sc.path))));
end
for k=1:numel(manifest.binary_checks)
 bc=manifest.binary_checks(k);assert(strcmpi(which(bc.name),bc.path));
 assert(strcmpi(phase_field.audit.sha256_file(which(bc.name)),bc.sha256));
end
self=struct('damage',e011_damage_selftest(),'coupled',e011_coupled_selftest(),'commit',e011_commit_selftest(fullfile(root,'selftest_tmp')));
fid=fopen(fullfile(root,'selftest.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(self));fclose(fid);
assert(numel(manifest.staging)==8);
for k=1:8
 item=manifest.staging(k);info=dir(item.target);assert(isscalar(info) && info.bytes==item.bytes);
 assert(strcmpi(phase_field.audit.sha256_file(item.target),item.sha256));
 if strcmp(item.role,'mesh')
  assert(startsWith(strtrim(fileread(item.target)),'*HEADING'));
  [io_mesh,~]=specimen.external.abaqus_import(item.target,'t',1.0);
  assert(io_mesh.num_node==86756 && io_mesh.num_elem==86408 && io_mesh.nel==4);
 else
  probe=load(item.target);assert(~isempty(fieldnames(probe)));clear probe
 end
end
for k=4:8
 z=load(manifest.staging(k).target,'request28_snapshot');assert(z.request28_snapshot.cycle==1 && z.request28_snapshot.substep==k-3);
 assert(isequal(io_mesh.node(:,1:2),z.request28_snapshot.node_coords));
 assert(isequal(io_mesh.elem(:,1:4),z.request28_snapshot.connectivity));
end
z=load(manifest.staging(1).target);assert(isequal(z.state0_node(:,1:2),io_mesh.node(:,1:2)));clear z io_mesh
cfg=build_SENS_hard_recovery_loading5_primary_config('C:\Users\xw436\jobs\S04_E011_ad749c8_20261005\reference_bundle\SENS_hard5_u012_eta0_formal_pidl_native_q4_v1');
cfg.output_identity='c1_commit';cfg.requested_cycles=1;cfg.defer_stop_until_cycle=1;
assert(cfg.n_step==5 && cfg.res_stiff==0 && cfg.reset_fatigue_after_recovery);
fid=fopen(fullfile(root,'io_preflight.json'),'w');assert(fid>=0);
fprintf(fid,'%s',jsonencode(struct('status','passed','unique_inputs',8,'native_field_solves',0,'staging',manifest.staging)));fclose(fid);
options=struct('work_dir',fullfile(root,'output','c1_commit'),'source_root',source, ...
 'mesh_file',manifest.staging(3).target,'topology','q4','max_cycle',1,'validate_only',false, ...
 'source_checks',manifest.source_checks,'binary_checks',manifest.binary_checks, ...
 'state0_file',manifest.staging(1).target,'references',manifest.staging(4:8),'source_commit',manifest.source_commit);
result=run_s04_e011_c1_commit(cfg,options);
fid=fopen(fullfile(root,'sequence_finished.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(result));fclose(fid);
catch exception
 failure=struct('identifier',exception.identifier,'message',exception.message, ...
  'status','stopped_no_retry','partial_commits','inspect per-arm failure and durable accepted_commit.mat files');
 fid=fopen(fullfile(root,'sequence_failure.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(failure));fclose(fid);
 rethrow(exception);
end
'''.replace('@ROOT@',remote_root).replace('@HELPERS@',helper_checks).replace('@NAMES@',names)
    (out/'entry.m').write_text(entry)
    checks='\n'.join(f"if((Get-FileHash ($root+'\\{p.name}') -Algorithm SHA256).Hash.ToLower() -ne '{sha(p)}'){{throw 'Approved file changed: {p.name}'}}" for p in sorted(out.iterdir()))
    launch=r'''param([switch]$PackageReviewed)
$ErrorActionPreference='Stop'
$root='@ROOT@'
if(-not $PackageReviewed){throw 'Exact package human approval and local review required; entry performs Windows checks before native solves'}
if($env:COMPUTERNAME -ne 'CITPC12' -or (& whoami).Trim().ToLower() -ne 'ad\xw436'){throw 'Wrong host/account'}
foreach($name in @('sequence_finished.json','sequence_failure.json','selftest.json','io_preflight.json','launch_receipt.json','matlab.log','stdout.log','stderr.log','output')){
 if(Test-Path ($root+'\'+$name)){throw ('Existing attempt marker; never relaunch: '+$name)}
}
if(Get-CimInstance Win32_Process|Where-Object {$_.Name -match 'MATLAB'}){throw 'MATLAB present; no disturbance'}
if((Get-PSDrive C).Free -lt 10GB -or (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory -lt 6291456){throw 'Insufficient disk/RAM'}
@CHECKS@
$manifest=Get-Content ($root+'\input_manifest.json') -Raw|ConvertFrom-Json
$inputRoot=$root+'\inputs';if(!(Test-Path $inputRoot)){$null=New-Item -ItemType Directory $inputRoot}
$stageRows=@()
foreach($item in $manifest.staging){
 if(!$item.target.StartsWith($inputRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Input target outside own root'}
 if((Get-Item -LiteralPath $item.source).Length -ne $item.bytes -or (Get-FileHash -LiteralPath $item.source -Algorithm SHA256).Hash.ToLower() -ne $item.sha256){throw 'Source input changed'}
 if(!(Test-Path -LiteralPath $item.target)){
  $partial=$item.target+'.partial';$inputStream=[IO.File]::OpenRead($item.source)
  try{$outputStream=[IO.File]::Open($partial,[IO.FileMode]::Create,[IO.FileAccess]::Write,[IO.FileShare]::None)
   try{$inputStream.CopyTo($outputStream,1048576);$outputStream.Flush($true)}finally{$outputStream.Dispose()}
  }finally{$inputStream.Dispose()}
  if((Get-Item -LiteralPath $partial).Length -ne $item.bytes -or (Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLower() -ne $item.sha256){throw 'Partial input mismatch'}
  Move-Item -LiteralPath $partial -Destination $item.target
 }
 if((Get-Item -LiteralPath $item.target).Length -ne $item.bytes -or (Get-FileHash -LiteralPath $item.target -Algorithm SHA256).Hash.ToLower() -ne $item.sha256){throw 'Staged input mismatch'}
 if(([int](Get-Item -LiteralPath $item.target).Attributes -band 0x00441400) -ne 0){throw 'Reparse/offline/recall input refused'}
 if((Get-FileHash -LiteralPath $item.source -Algorithm SHA256).Hash.ToLower() -ne $item.sha256){throw 'Source changed while staging'}
 $stageRows+=@{source=$item.source;target=$item.target;bytes=$item.bytes;sha256=$item.sha256}
}
if($stageRows.Count -ne 8){throw 'Expected eight inputs'}
@{status='verified';files=$stageRows}|ConvertTo-Json -Depth 4|Set-Content -Encoding UTF8 ($root+'\staging_receipt.json')
if(Get-CimInstance Win32_Process|Where-Object {$_.Name -match 'MATLAB'}){throw 'MATLAB appeared; no launch'}
if((Get-PSDrive C).Free -lt 10GB -or (Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory -lt 6291456){throw 'Resources changed; no launch'}
$cmd='"C:\Windows\System32\cmd.exe" /d /s /c ""C:\Program Files\MATLAB\R2025b\bin\matlab.exe" -singleCompThread -batch "run(''@ROOT@\entry.m'')" -logfile "@ROOT@\matlab.log" > "@ROOT@\stdout.log" 2> "@ROOT@\stderr.log""'
$r=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$cmd;CurrentDirectory=$root}
if($r.ReturnValue -ne 0){throw ('WMI launch failed: '+$r.ReturnValue)}
@{run_id='pf_s04e011_c1_commit_20261016_v2';commit='@COMMIT@';branch='codex/hard5-q4-t3-2x2-20261005';dirty=$false;producer='CITPC12/citpc12-ssh';account='AD\xw436';pid=$r.ProcessId;command=$cmd;root=$root;started_utc=(Get-Date).ToUniversalTime().ToString('o');threads=1;gpu='CPU';method='WMI isolated process'}|ConvertTo-Json|Set-Content -Encoding UTF8 ($root+'\launch_receipt.json')
Get-Content ($root+'\launch_receipt.json')
'''.replace('@ROOT@',remote_root).replace('@CHECKS@',checks).replace('@COMMIT@',commit)
    (out/'launch_wmi.ps1').write_text(launch)
    files=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(out.iterdir())]
    assert len(files)==15
    receipt=dict(status='prepared_not_sent',account=r'AD\xw436',host='CITPC12',ssh_alias='citpc12-ssh',remote_root=remote_root,source_commit=commit,files=files,files_total_bytes=sum(x['bytes'] for x in files),input_copies=staging,input_copy_bytes=sum(x['bytes'] for x in staging))
    (out.parent/'approval_manifest_v2.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def main():
    p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--prior-bundle',type=Path,required=True);p.add_argument('--reference-root',type=Path,required=True);p.add_argument('--mesh',type=Path,required=True);p.add_argument('--inventory',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--remote-root',default=r'C:\Users\xw436\jobs\E011_C1_20261016_v2');p.add_argument('--commit',required=True);a=p.parse_args()
    print(json.dumps(build(a.source_root,a.prior_bundle,a.reference_root,a.mesh,a.out,a.remote_root,a.commit,json.loads(a.inventory.read_text())),indent=2))
if __name__=='__main__':main()
