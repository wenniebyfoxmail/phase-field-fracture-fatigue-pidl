#!/usr/bin/env python3
"""Prepare a local nine-file approval bundle. Never connects or launches."""
import argparse, hashlib, json
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build(prior, repair_run, out, root, commit):
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
'''.replace('@ROOT@',root).replace('@CHECKS@',checks).replace('@COMMIT@',commit)
    (out/'launch_wmi.ps1').write_text(launch)
    receipt={'status':'prepared_not_sent','account':r'AD\xw436','host':'CITPC12','ssh_alias':'citpc12-ssh','remote_root':root,'source_commit':commit,'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir())]}
    (out.parent/'approval_manifest_v1.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def main():
    p=argparse.ArgumentParser();p.add_argument('--prior-bundle',type=Path,required=True);p.add_argument('--repair-run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--remote-root',default=r'C:\Users\xw436\jobs\E011_CR_20261015_v1');p.add_argument('--commit',required=True);a=p.parse_args()
    print(json.dumps(build(a.prior_bundle,a.repair_run,a.out,a.remote_root,a.commit),indent=2))
if __name__=='__main__':main()
