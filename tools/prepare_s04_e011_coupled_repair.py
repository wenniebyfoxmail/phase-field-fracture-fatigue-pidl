#!/usr/bin/env python3
"""Prepare a local nine-file approval bundle. Never connects or launches."""
import argparse, hashlib, json
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build(prior, repair_run, out, root, commit, version=1, predecessor_root=None, dependency_lock=None):
    assert version in [1,2,3] and root.endswith(f'_v{version}'), 'Version/root mismatch'
    assert not out.exists(), 'Refuse to replace an approval version'
    out.mkdir(parents=True)
    here=Path(__file__).parent/'s04_e011_analysis'
    for name in ['run_s04_e011_coupled_repair.m','e011_displacement_solve.m','e011_coupled_solve.m','e011_coupled_selftest.m']:
        (out/name).write_bytes((here/'coupled_repair'/name).read_bytes())
    for name in ['e011_damage_solve.m','e011_damage_selftest.m']:
        (out/name).write_bytes((here/'constrained_damage'/name).read_bytes())
    manifest=json.loads((prior/'input_manifest.json').read_text())
    manifest.sort(key=lambda x:(x['cycle'],x['stage']!='baseline'))
    for x in manifest:
        path=repair_run/'retrieved/output'/f"c{x['cycle']}_{x['stage']}"/'constrained/damage_repair.mat'
        x['prior_repair_path']=rf"C:\Users\xw436\jobs\E011_DR_20261015_v1\output\c{x['cycle']}_{x['stage']}\constrained\damage_repair.mat"
        x['prior_repair_sha256']=sha(path)
        if predecessor_root:
            x['predecessor_original_path']=x['predecessor']
            leaf=x['predecessor'].replace('\\\\','\\').split('\\')[-1]
            x['predecessor']=predecessor_root.rstrip('\\')+'\\'+leaf
    if version==3:
        assert dependency_lock and predecessor_root, 'v3 requires the verified full input lock and backup root'
        def normal(path):return path.replace('\\\\','\\')
        by_source={normal(v['path']):v for v in dependency_lock['files']}
        mesh=dependency_lock['mesh'];targets={}
        for x in manifest:
            x['staging']=[]
            for role,hkey in [('input_state','input_sha256'),('capture_path','capture_sha256'),('prior_repair_path','prior_repair_sha256'),('predecessor','predecessor_sha256')]:
                source=normal(x[role]);v=by_source[source];assert v['sha256']==x[hkey]
                target=root+'\\inputs\\'+v['sha256'][:16]+'_'+source.split('\\')[-1]
                assert target not in targets or targets[target]==source
                targets[target]=source;x[role]=target
                x['staging'].append(dict(role=role,source=source,target=target,sha256=v['sha256'],bytes=v['bytes']))
            target=root+'\\inputs\\'+mesh['sha256'][:16]+'_native_q4_original.inp'
            x['mesh_file']=target
            x['staging'].append(dict(role='mesh',source=normal(mesh['path']),target=target,sha256=mesh['sha256'],bytes=mesh['bytes']))
        assert len(targets)==14
    (out/'input_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    entry=r'''root='@ROOT@';
source='C:\Users\xw436\jobs\S04_E011_ad749c8_20261005\source';
addpath(fullfile(source,'Sources'));addpath(fullfile(source,'Scripts','fatigue_fracture'));addpath(root);
addpath(genpath(fullfile(source,'Dependencies')));
% No native field solve before all static/algebra checks.
completed=0;c1_pass=true;
try
self=struct('damage',e011_damage_selftest(),'coupled',e011_coupled_selftest());
fid=fopen(fullfile(root,'selftest.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(self));fclose(fid);
manifest=jsondecode(fileread(fullfile(root,'input_manifest.json')));
assert(isequal([manifest.cycle],[1 1 83 83]));
assert(isequal(string({manifest.stage}),["baseline" "last_accepted" "baseline" "last_accepted"]));
for k=1:numel(manifest)
 options=manifest(k);
 if options.cycle==83 && ~c1_pass,break;end
 cfg=build_SENS_hard_recovery_loading5_primary_config('C:\Users\xw436\jobs\S04_E011_ad749c8_20261005\reference_bundle\SENS_hard5_u012_eta0_formal_pidl_native_q4_v1');
 cfg.output_identity=sprintf('c%d_%s',options.cycle,options.stage);cfg.requested_cycles=options.cycle;cfg.defer_stop_until_cycle=options.cycle;
 options.work_dir=fullfile(root,'output',cfg.output_identity);options.source_root=source;
 options.mesh_file='C:\Users\xw436\OneDrive - University of Cambridge\griphfith\hard5_u012_q4_t3_unaligned_baseline_handoff_20261005_v1\mesh\native_q4_original.inp';
 options.topology='q4';options.max_cycle=options.cycle;options.validate_only=false;
 result=run_s04_e011_coupled_repair(cfg,options);completed=completed+1;disp(jsonencode(result));
 if options.cycle==1,c1_pass=c1_pass && result.joint_pass;end
end
catch exception
 failure=struct('identifier',exception.identifier,'message',exception.message,'states_completed',completed,'history_commits',0);
 save(fullfile(root,'coupled_failure.mat'),'failure','-v7.3');
 fid=fopen(fullfile(root,'coupled_failure.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(failure));fclose(fid);
 rethrow(exception);
end
status='completed';if ~c1_pass,status='c1_negative_c83_skipped';end
fid=fopen(fullfile(root,'coupled_finished.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(struct( ...
 'status',status,'states',completed,'c1_pass',c1_pass,'history_commits',0,'finished_utc',char(datetime('now','TimeZone','UTC')))));fclose(fid);
'''.replace('@ROOT@',root)
    helper_checks='\n'.join(f"assert(strcmpi(phase_field.audit.sha256_file(fullfile(root,'{p.name}')),'{sha(p)}'));" for p in sorted(out.glob('*.m')))
    entry=entry.replace("self=struct(",helper_checks+"\nself=struct(")
    static="reviewed_names="+"{"+','.join("'"+p.name+"'" for p in sorted(out.glob('*.m')))+",'entry.m'};\nfor q=1:numel(reviewed_names),cc=checkcode(fullfile(root,reviewed_names{q}),'-id');disp(cc);for j=1:numel(cc),assert(ismember(string(cc(j).id),{'NASGU','MSNU'}),'E011:StaticCheck','Unexpected checkcode finding');end;end\n"
    entry=entry.replace("self=struct(",static+"self=struct(")
    if version==3:
        old_mesh_line=next(line for line in entry.splitlines() if line.startswith(" options.mesh_file="))
        entry=entry.replace(old_mesh_line," assert(strcmp(options.mesh_file,options.staging(5).target));")
        io=r"""% This is the actual MATLAB worker: all input I/O precedes native callbacks.
mesh_item=manifest(1).staging(5);assert(strcmp(mesh_item.role,'mesh'));
assert(strcmpi(phase_field.audit.sha256_file(mesh_item.target),mesh_item.sha256));
assert(startsWith(strtrim(fileread(mesh_item.target)),'*HEADING'));
[io_mesh,~]=specimen.external.abaqus_import(mesh_item.target,'t',1.0);
assert(io_mesh.num_node==86756 && io_mesh.num_elem==86408 && io_mesh.nel==4);
io_seen={};io_rows=struct('role',{},'path',{},'sha256',{},'bytes',{},'read',{});
for iq=1:numel(manifest)
 state=manifest(iq);
 for ir=1:numel(state.staging)
  item=state.staging(ir);if ismember(item.target,io_seen),continue;end
  assert(isfile(item.target));item_info=dir(item.target);assert(item_info.bytes==item.bytes);
  assert(strcmpi(phase_field.audit.sha256_file(item.target),item.sha256));
  read_mode='full_load';
  if strcmp(item.role,'mesh')
   read_mode='fileread_and_native_mesh_import';
  elseif strcmp(item.role,'capture_path')
   header=whos('-file',item.target);assert(~isempty(header));read_mode='mat_header';
  else
   probe=load(item.target);
   if strcmp(item.role,'predecessor')
    assert(isfield(probe,'request28_snapshot'));
    assert(probe.request28_snapshot.cycle==state.cycle && probe.request28_snapshot.substep==3);
    assert(isequal(io_mesh.node(:,1:2),probe.request28_snapshot.node_coords));
    assert(isequal(io_mesh.elem(:,1:4),probe.request28_snapshot.connectivity));
   elseif strcmp(item.role,'prior_repair_path')
    assert(strcmp(probe.arm.mode,'constrained') && probe.arm.phase_pass && probe.arm.history_commits==0);
   else
    assert(isfield(probe,'frozen') && (isfield(probe,'candidate') || isfield(probe,'converged')));
   end
   clear probe
  end
  io_seen{end+1}=item.target; %#ok<SAGROW>
  io_rows(end+1)=struct('role',item.role,'path',item.target,'sha256',item.sha256,'bytes',item.bytes,'read',read_mode); %#ok<SAGROW>
 end
end
assert(numel(io_seen)==15);
for ic=1:numel(manifest(1).source_checks)
 sc=manifest(1).source_checks(ic);source_file=fullfile(source,sc.path);
 assert(strcmpi(phase_field.audit.sha256_file(source_file),sc.sha256));
 assert(~isempty(fileread(source_file)));
end
% Exercise the actual config/reference entry point for all four cases, no solve.
for iq=1:numel(manifest)
 check_cfg=build_SENS_hard_recovery_loading5_primary_config('C:\Users\xw436\jobs\S04_E011_ad749c8_20261005\reference_bundle\SENS_hard5_u012_eta0_formal_pidl_native_q4_v1');
 assert(check_cfg.res_stiff==0 && check_cfg.n_step==5);
end
fid=fopen(fullfile(root,'io_preflight.json'),'w');assert(fid>=0);
fprintf(fid,'%s',jsonencode(struct('status','passed','unique_inputs',15,'native_field_solves',0,'rows',io_rows)));fclose(fid);
clear io_mesh check_cfg
"""
        entry=entry.replace('for k=1:numel(manifest)',io+'\nfor k=1:numel(manifest)',1)
    (out/'entry.m').write_text(entry)
    # Check all binaries needed by the solver/selftest resolve as approved.
    binary_checks=manifest[0]['binary_checks']
    resolve='\n'.join(f"assert(strcmpi(which('{b['name']}'),'{b['path']}'));assert(strcmpi(phase_field.audit.sha256_file(which('{b['name']}')),'{b['sha256']}'));" for b in binary_checks)
    entry=(out/'entry.m').read_text().replace("self=struct('damage'",resolve+"\nself=struct('damage'")
    (out/'entry.m').write_text(entry)
    checks='\n'.join(f"if((Get-FileHash ($root+'\\{p.name}') -Algorithm SHA256).Hash.ToLower() -ne '{sha(p)}'){{throw 'approved file hash changed: {p.name}'}}" for p in sorted(out.iterdir()))
    launch=r'''param([switch]$StaticReviewed)
if(-not $StaticReviewed){throw 'Review checkcode and exact approval before launch'}
$ErrorActionPreference='Stop'
$root='@ROOT@'
if($env:COMPUTERNAME -ne 'CITPC12'){throw 'unexpected producer host'}
if((& whoami).Trim().ToLower() -ne 'ad\xw436'){throw 'unexpected producer account'}
foreach($marker in @('coupled_failure.json','coupled_finished.json','selftest.json','matlab.log','stdout.log','stderr.log')){
 if(Test-Path ($root+'\'+$marker)){throw ('existing attempt marker '+$marker+'; never relaunch')}
}
if(Test-Path ($root+'\launch_receipt.json')){throw 'duplicate receipt'}
if(Test-Path ($root+'\output')){throw 'existing output; never relaunch'}
$existing=Get-CimInstance Win32_Process|Where-Object { $_.Name -match 'MATLAB' }
if($existing){throw 'MATLAB process present; do not launch'}
if((Get-PSDrive C).Free -lt 10GB){throw 'insufficient disk'}
if((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory -lt 6291456){throw 'insufficient memory'}
@CHECKS@
$cmd='"C:\Windows\System32\cmd.exe" /d /s /c ""C:\Program Files\MATLAB\R2025b\bin\matlab.exe" -singleCompThread -batch "run(''@ROOT@\entry.m'')" -logfile "@ROOT@\matlab.log" > "@ROOT@\stdout.log" 2> "@ROOT@\stderr.log""'
$r=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$cmd;CurrentDirectory=$root}
if($r.ReturnValue -ne 0){throw ('WMI creation failed '+$r.ReturnValue)}
@{run_id='pf_s04e011_coupled_repair_20261015_v1';commit='@COMMIT@';branch='codex/hard5-q4-t3-2x2-20261005';dirty=$false;producer='CITPC12/citpc12-ssh';account='AD\xw436';pid=$r.ProcessId;command=$cmd;root=$root;started_utc=(Get-Date).ToUniversalTime().ToString('o');method='WMI service isolated process';threads=1;gpu='CPU';history_commits=0}|ConvertTo-Json|Set-Content -Encoding UTF8 ($root+'\launch_receipt.json')
Get-Content ($root+'\launch_receipt.json')
'''.replace('@ROOT@',root).replace('@CHECKS@',checks).replace('@COMMIT@',commit).replace('pf_s04e011_coupled_repair_20261015_v1',f'pf_s04e011_coupled_repair_20261015_v{version}')
    if version>=2:
        admissions=r'''$states=Get-Content ($root+'\input_manifest.json') -Raw|ConvertFrom-Json
$seen=@{}
foreach($state in $states){
 foreach($pair in @(@('input_state','input_sha256'),@('capture_path','capture_sha256'),@('prior_repair_path','prior_repair_sha256'),@('predecessor','predecessor_sha256'))){
  $p=[string]$state.($pair[0]);$expected=[string]$state.($pair[1])
  if($seen.ContainsKey($p)){if($seen[$p] -ne $expected){throw 'Conflicting input hashes'};continue}
  if(!(Test-Path -LiteralPath $p)){throw ('Missing locked input '+$p)}
  if((Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLower() -ne $expected){throw ('Input hash changed '+$p)}
  $seen[$p]=$expected
 }
}
'''
        launch=launch.replace('$cmd=',admissions+'$cmd=',1)
    if version==3:
        stage=r"""$states=Get-Content ($root+'\input_manifest.json') -Raw|ConvertFrom-Json
$stageSeen=@{};$stageRows=@()
$inputRoot=$root+'\inputs'
if(!(Test-Path $inputRoot)){$null=New-Item -ItemType Directory $inputRoot}
foreach($state in $states){foreach($item in $state.staging){
 if($stageSeen.ContainsKey($item.target)){if($stageSeen[$item.target] -ne $item.sha256){throw 'Staging hash conflict'};continue}
 if(!$item.target.StartsWith($inputRoot+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Staging outside own inputs'}
 if(!(Test-Path -LiteralPath $item.source)){throw ('Missing staging source '+$item.source)}
 $sourceInfo=Get-Item -LiteralPath $item.source
 if($sourceInfo.Length -ne $item.bytes){throw 'Staging source size changed'}
 if((Get-FileHash -LiteralPath $item.source -Algorithm SHA256).Hash.ToLower() -ne $item.sha256){throw 'Staging source hash changed'}
 if(!(Test-Path -LiteralPath $item.target)){
  $partial=$item.target+'.partial'
  $inputStream=[IO.File]::OpenRead($item.source)
  try{
   $outputStream=[IO.File]::Open($partial,[IO.FileMode]::Create,[IO.FileAccess]::Write,[IO.FileShare]::None)
   try{$inputStream.CopyTo($outputStream,1048576);$outputStream.Flush($true)}finally{$outputStream.Dispose()}
  }finally{$inputStream.Dispose()}
  if((Get-Item -LiteralPath $partial).Length -ne $item.bytes -or (Get-FileHash -LiteralPath $partial -Algorithm SHA256).Hash.ToLower() -ne $item.sha256){throw 'Staging partial mismatch'}
  Move-Item -LiteralPath $partial -Destination $item.target
 }
 if((Get-Item -LiteralPath $item.target).Length -ne $item.bytes -or (Get-FileHash -LiteralPath $item.target -Algorithm SHA256).Hash.ToLower() -ne $item.sha256){throw 'Staged input mismatch'}
 if(([int](Get-Item -LiteralPath $item.target).Attributes -band 0x00441400) -ne 0){throw 'Staged file retains reparse/offline/recall attributes'}
 if((Get-FileHash -LiteralPath $item.source -Algorithm SHA256).Hash.ToLower() -ne $item.sha256){throw 'Source changed during copy'}
 $stageSeen[$item.target]=$item.sha256
 $stageRows+=@{role=$item.role;source=$item.source;target=$item.target;bytes=$item.bytes;sha256=$item.sha256;attributes=[int](Get-Item -LiteralPath $item.target).Attributes}
}}
if($stageRows.Count -ne 15){throw 'Expected15 unique staged inputs'}
@{status='verified';unique_inputs=15;files=$stageRows}|ConvertTo-Json -Depth 4|Set-Content -Encoding UTF8 ($root+'\staging_receipt.json')
"""
        launch=launch.replace("$states=Get-Content",stage+"$states=Get-Content",1)
        final_resources=r'''$competing=Get-CimInstance Win32_Process|Where-Object {$_.Name -match 'MATLAB'}
if($competing){throw 'MATLAB appeared during staging; no launch'}
if((Get-PSDrive C).Free -lt 10GB){throw 'Disk below limit after staging'}
if((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory -lt 6291456){throw 'RAM below limit after staging'}
'''
        launch=launch.replace('$cmd=',final_resources+'$cmd=',1)
    (out/'launch_wmi.ps1').write_text(launch)
    receipt={'status':'prepared_not_sent','account':r'AD\xw436','host':'CITPC12','ssh_alias':'citpc12-ssh','remote_root':root,'source_commit':commit,'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir())]}
    (out.parent/f'approval_manifest_v{version}.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def main():
    p=argparse.ArgumentParser();p.add_argument('--prior-bundle',type=Path,required=True);p.add_argument('--repair-run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--remote-root',default=r'C:\Users\xw436\jobs\E011_CR_20261015_v1');p.add_argument('--commit',required=True);p.add_argument('--version',type=int,default=1,choices=[1,2,3]);p.add_argument('--predecessor-root');p.add_argument('--dependency-lock',type=Path);a=p.parse_args()
    print(json.dumps(build(a.prior_bundle,a.repair_run,a.out,a.remote_root,a.commit,a.version,a.predecessor_root,json.loads(a.dependency_lock.read_text()) if a.dependency_lock else None),indent=2))
if __name__=='__main__':main()
