#!/usr/bin/env python3
"""Prepare a local six-file approval bundle. Never connects or launches."""
import argparse, hashlib, json, subprocess
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build(prior, capture_run, out, root, commit):
    assert not out.exists(), 'Refuse to replace an approval version'
    out.mkdir(parents=True)
    here=Path(__file__).parent/'s04_e011_analysis/constrained_damage'
    for name in ['run_s04_e011_damage_repair.m','e011_damage_solve.m','e011_damage_selftest.m']:
        (out/name).write_bytes((here/name).read_bytes())
    manifest=json.loads((prior/'input_manifest.json').read_text())
    manifest.sort(key=lambda x:(x['cycle'],x['stage']!='baseline'))
    for x in manifest:
        path=capture_run/'retrieved/output'/f"c{x['cycle']}_{x['stage']}"/'projection_capture.mat'
        x['capture_path']=rf"C:\Users\xw436\jobs\E011_PT_20261014_v2\output\c{x['cycle']}_{x['stage']}\projection_capture.mat"
        x['capture_sha256']=sha(path)
        x.pop('direction_reference',None);x.pop('direction_reference_sha256',None)
    (out/'input_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    entry=r'''root='@ROOT@';
source='C:\Users\xw436\jobs\S04_E011_ad749c8_20261005\source';
addpath(fullfile(source,'Sources'));addpath(fullfile(source,'Scripts','fatigue_fracture'));addpath(root);
addpath(genpath(fullfile(source,'Dependencies')));
% MEX resolution is hash-checked in the native runner before any field solve.
self=e011_damage_selftest();
fid=fopen(fullfile(root,'selftest.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(self));fclose(fid);
manifest=jsondecode(fileread(fullfile(root,'input_manifest.json')));
assert(isequal([manifest.cycle],[1 1 83 83]));
assert(strcmp(manifest(1).stage,'baseline') && strcmp(manifest(2).stage,'last_accepted'));
completed=0;c1_pass=true;
try
for k=1:numel(manifest)
 options=manifest(k);
 if options.cycle==83 && ~c1_pass,break;end
 cfg=build_SENS_hard_recovery_loading5_primary_config('C:\Users\xw436\jobs\S04_E011_ad749c8_20261005\reference_bundle\SENS_hard5_u012_eta0_formal_pidl_native_q4_v1');
 cfg.output_identity=sprintf('c%d_%s',options.cycle,options.stage);cfg.requested_cycles=options.cycle;cfg.defer_stop_until_cycle=options.cycle;
 options.work_dir=fullfile(root,'output',cfg.output_identity);options.source_root=source;
 options.mesh_file='C:\Users\xw436\OneDrive - University of Cambridge\griphfith\hard5_u012_q4_t3_unaligned_baseline_handoff_20261005_v1\mesh\native_q4_original.inp';
 options.topology='q4';options.max_cycle=options.cycle;options.validate_only=false;
 result=run_s04_e011_damage_repair(cfg,options);completed=completed+1;disp(jsonencode(result));
 if options.cycle==1,c1_pass=c1_pass && result.arms(2).phase_pass;end
end
catch exception
 failure=struct('identifier',exception.identifier,'message',exception.message,'states_completed',completed,'history_commits',0);
 save(fullfile(root,'repair_failure.mat'),'failure','-v7.3');
 fid=fopen(fullfile(root,'repair_failure.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(failure));fclose(fid);
 rethrow(exception);
end
status='completed';if ~c1_pass,status='c1_negative_c83_skipped';end
fid=fopen(fullfile(root,'repair_finished.json'),'w');assert(fid>=0);fprintf(fid,'%s',jsonencode(struct( ...
 'status',status,'states',completed,'c1_pass',c1_pass,'history_commits',0,'finished_utc',char(datetime('now','TimeZone','UTC')))));fclose(fid);
'''.replace('@ROOT@',root)
    (out/'entry.m').write_text(entry)
    # Check all binaries needed by the solver/selftest resolve as approved.
    binary_checks=manifest[0]['binary_checks']
    resolve='\n'.join(f"assert(strcmpi(which('{b['name']}'),'{b['path']}'));assert(strcmpi(phase_field.audit.sha256_file(which('{b['name']}')),'{b['sha256']}'));" for b in binary_checks)
    entry=(out/'entry.m').read_text().replace('self=e011_damage_selftest();',resolve+'\nself=e011_damage_selftest();')
    (out/'entry.m').write_text(entry)
    checks='\n'.join(f"if((Get-FileHash ($root+'\\{p.name}') -Algorithm SHA256).Hash.ToLower() -ne '{sha(p)}'){{throw 'approved file hash changed: {p.name}'}}" for p in sorted(out.iterdir()))
    launch=r'''param([switch]$StaticReviewed)
if(-not $StaticReviewed){throw 'Review checkcode and exact approval before launch'}
$ErrorActionPreference='Stop'
$root='@ROOT@'
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
@{run_id='pf_s04e011_damage_repair_20261015_v1';commit='@COMMIT@';branch='codex/hard5-q4-t3-2x2-20261005';dirty=$false;producer='CITPC12/citpc12-ssh';account='AD\xw436';pid=$r.ProcessId;command=$cmd;root=$root;started_utc=(Get-Date).ToUniversalTime().ToString('o');method='WMI service isolated process';threads=1;gpu='CPU';history_commits=0}|ConvertTo-Json|Set-Content -Encoding UTF8 ($root+'\launch_receipt.json')
Get-Content ($root+'\launch_receipt.json')
'''.replace('@ROOT@',root).replace('@CHECKS@',checks).replace('@COMMIT@',commit)
    (out/'launch_wmi.ps1').write_text(launch)
    receipt={'status':'prepared_not_sent','account':r'AD\xw436','host':'CITPC12','ssh_alias':'citpc12-ssh','remote_root':root,'source_commit':commit,'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir())]}
    (out.parent/'approval_manifest_v1.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


def main():
    p=argparse.ArgumentParser();p.add_argument('--prior-bundle',type=Path,required=True);p.add_argument('--capture-run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--remote-root',default=r'C:\Users\xw436\jobs\E011_DR_20261015_v1');p.add_argument('--commit',required=True);a=p.parse_args()
    print(json.dumps(build(a.prior_bundle,a.capture_run,a.out,a.remote_root,a.commit),indent=2))
if __name__=='__main__':main()
