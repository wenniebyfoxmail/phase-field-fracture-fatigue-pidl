#!/usr/bin/env python3
"""Prepare one Stage A comparison job from an actual frozen native report.

Metadata/file hashes only: no MATLAB/MAT loading, assembly, SSH or launch.
Copy an explicit single-label authority; never infer or grant execution rights.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import math
from pathlib import Path, PureWindowsPath
import re

PYTHON = r'C:\Users\xw436\Python310\python.exe'
COMPARATOR = 'compare_code_01/tools/s04_e036_fem/compare_frozen_states.py'
COMPARATOR_SHA = '438e874d5363e25609d216e9d4c38b86e21bf36bd4cab1fba556c855a25ce869'
COMMON = 'compare_code_01/docs/research/S04/S04-E036/common_problem_q4.json'
COMMON_SHA = 'c0d198763e4b127342fd788c5db7f868c1743679c5629e364d877eba71bfb79f'
COMPARE_MANIFEST_SHA = '625a5deef4e8898dc34d623b6da258322b3b63a125048628c1b82ed19f3fbc58'


def load_tools():
    path = Path(__file__).with_name('prepare_stage_a_job.py')
    spec = importlib.util.spec_from_file_location('e036_comparison_job_text_tools', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # stdlib-only; generate/finalize are not called.
    return module, module.load_generator()


def generate(args):
    j, g = load_tools()
    if not re.fullmatch('[a-z0-9_]+', args.label):
        raise ValueError('one explicit fresh label is required')
    if not re.fullmatch('[a-f0-9]{64}', args.native_result_sha256) or g.sha(args.native_result) != args.native_result_sha256:
        raise ValueError('actual retrieved native report hash differs')
    report, cfg, authority = map(g.read, (args.native_result, args.native_config, args.authority_file))
    finished, supervisor = map(g.read, (args.native_finished, args.native_supervisor))
    root = j.windows(cfg['run_root'])

    def in_root(value):
        path = PureWindowsPath(value)
        if not path.is_absolute() or '..' in path.parts:
            raise ValueError('absolute task path without traversal required')
        relative = path.relative_to(PureWindowsPath(root))
        if not relative.parts:
            raise ValueError('file/output path must be below task root')
        return str(path)

    if g.sha(args.native_config) != report.get('config_sha256') or report.get('authority_sha256') != cfg.get('authority_sha256'):
        raise ValueError('native report does not bind this exact native config/authority')
    if cfg.get('execution_approved') is not True or not re.fullmatch('[a-z0-9_]+', cfg.get('watchdog_id', '')):
        raise ValueError('native config has no explicit approved task identity')
    if cfg['watchdog_id'] == args.label:
        raise ValueError('comparison needs a fresh label distinct from native export')
    native_authority = report.get('authority', {})
    native_authority_sha = cfg.get('authority_sha256', '')
    if not isinstance(native_authority, dict) or not native_authority.get('authority_id') or not re.fullmatch('[a-f0-9]{64}', native_authority_sha):
        raise ValueError('native report lacks a bound authority identity')
    if (finished.get('label') != cfg['watchdog_id'] or type(finished.get('exit_code')) is not int or
            finished['exit_code'] != 0 or finished.get('stop_reason') != 'exited' or
            finished.get('job_object_closed') is not True or finished.get('wrapper_error', '') is not None or
            finished.get('authority_id') != native_authority['authority_id'] or
            finished.get('authority_sha256') != native_authority_sha):
        raise ValueError('native watchdog did not prove a successful terminal exit')
    policy_scopes = {'MachinePolicy', 'UserPolicy', 'CurrentUser', 'LocalMachine'}
    before, after = supervisor.get('global_policies_before'), supervisor.get('global_policies_after')
    if (supervisor.get('schema') != 'e036-stage-a-supervisor-v1' or supervisor.get('label') != cfg['watchdog_id'] or
            supervisor.get('stop_reason') != 'completed' or type(supervisor.get('watchdog_exit_code')) is not int or
            supervisor['watchdog_exit_code'] != 0 or supervisor.get('watchdog_stopped') is not True or
            supervisor.get('failure', '') is not None or supervisor.get('global_policy_unchanged') is not True or
            not isinstance(before, dict) or set(before) != policy_scopes or before != after or
            supervisor.get('authority_sha256') != native_authority_sha or
            supervisor.get('watchdog_sha256') != g.sha(Path(__file__).with_name('stage_a_watchdog_v4.ps1'))):
        raise ValueError('native supervisor did not prove successful completion with unchanged global policies')
    for key, expected in dict(cycle=args.cycle, substep=4, native_solves=0, assemblies_u=1, assemblies_d=1).items():
        if type(report.get(key)) not in (int, float) or report[key] != expected:
            raise ValueError('native report physical/scope field differs: ' + key)
    if report.get('driver_mode') != f'frozen_c{args.cycle}':
        raise ValueError('only the matching frozen native mode is accepted')
    native_output = in_root(cfg['output_dir'])
    if PureWindowsPath(native_output) != PureWindowsPath(root, 'output', cfg['watchdog_id']):
        raise ValueError('native output directory differs from its task label')
    input_path = in_root(report['path'])
    if PureWindowsPath(input_path) != PureWindowsPath(native_output, f'native_c{args.cycle:04d}_s04.mat'):
        raise ValueError('native MAT path does not match this exact cycle export')
    if not re.fullmatch('[a-f0-9]{64}', report.get('sha256', '')):
        raise ValueError('native MAT digest is missing')

    required = {'schema', 'authority_id', 'stage', 'run_root', 'producer_hostname', 'allowed_labels',
                'authorized_at_utc', 'human_authorization_ref', 'max_compute_threads',
                'global_deadline_utc', 'per_job_wall_seconds', 'arm_wall_seconds'}
    if not required <= authority.keys() or authority['schema'] != 'e036-stage-a-authority-v1' or authority['stage'] != 'A':
        raise ValueError('explicit Stage A authority required')
    if (PureWindowsPath(authority['run_root']) != PureWindowsPath(root) or
            authority['producer_hostname'].upper() != 'CITPC12' or authority['allowed_labels'] != [args.label] or
            not authority['authority_id'] or not authority['human_authorization_ref']):
        raise ValueError('authority must bind this task and exactly one comparison label')
    threads, wall = authority['max_compute_threads'], authority['per_job_wall_seconds']
    if type(threads) is not int or not 1 <= args.threads <= threads <= 4:
        raise ValueError('comparison threads must remain within the explicit 1..4 authority')
    if type(wall) not in (int, float) or not math.isfinite(wall) or wall <= 0:
        raise ValueError('finite positive per-job hang guard required')
    now = dt.datetime.now(dt.timezone.utc)
    for key in ('authorized_at_utc', 'global_deadline_utc'):
        value = authority[key]
        if key == 'global_deadline_utc' and value is None:
            continue
        if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', value):
            raise ValueError('authority time must use explicit whole UTC seconds')
        stamp = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        if (key == 'authorized_at_utc' and stamp > now + dt.timedelta(minutes=1)) or (key == 'global_deadline_utc' and stamp <= now):
            raise ValueError('authority time is not currently usable')

    if g.sha(args.compare_manifest) != COMPARE_MANIFEST_SHA:
        raise ValueError('require the complete recorded compare_code_01 manifest')
    compare = g.read(args.compare_manifest)
    if compare.get('schema') != 'e036-comparison-source-v1':
        raise ValueError('expected existing comparison source manifest')
    records = {}
    for item in compare['files']:
        path = g.checked_rel(item['path'])
        if not path.startswith('compare_code_01/') or path.lower() in records or not re.fullmatch('[a-f0-9]{64}', item['sha256']):
            raise ValueError('invalid/duplicate comparison source record')
        if g.sha(args.compare_directory / path) != item['sha256']:
            raise ValueError('local comparison source differs: ' + path)
        records[path.lower()] = item
    if records.get(COMPARATOR.lower(), {}).get('sha256') != COMPARATOR_SHA or records.get(COMMON.lower(), {}).get('sha256') != COMMON_SHA:
        raise ValueError('comparison code/common problem differs from the reviewed binding')
    launcher_rel = 'code_04/tools/s04_e036_fem/stage_a_launcher.ps1'
    if PureWindowsPath(cfg['code_root']) != PureWindowsPath(root, 'code_04'):
        raise ValueError('this continuation uses the existing code_04 launcher')
    launchers = [r for r in g.read(args.prepare_manifest)['files'] if r['path'] == launcher_rel]
    if len(launchers) != 1 or launchers[0]['sha256'] != g.sha(Path(__file__).with_name('stage_a_launcher.ps1')):
        raise ValueError('preparation manifest must bind the reviewed launcher')
    controls = [r for r in g.read(args.control_deployment)['files']
                if r['path'] == 'control_04/stage_a_compare_watchdog_v5.ps1']
    if len(controls) != 1:
        raise ValueError('one explicit control_04 comparison v5 binding required')
    watchdog = controls[0]
    if g.sha(args.control_directory / watchdog['path']) != watchdog['sha256'] or watchdog['sha256'] != g.sha(Path(__file__).with_name('stage_a_compare_watchdog_v5.ps1')):
        raise ValueError('comparison watchdog differs from reviewed/deployed bytes')

    args.output.mkdir(parents=False, exist_ok=False)
    deploy = args.output / 'deploy'; deploy.mkdir()
    files = []

    def add_file(name, value):
        g.write(deploy / name, value)
        files.append(dict(path=name, sha256=g.sha(deploy / name), bytes=(deploy / name).stat().st_size, reuse_if_identical=False))

    authority_name = args.label + '_authority.json'
    with (deploy / authority_name).open('xb') as stream:
        stream.write(args.authority_file.read_bytes())
    files.append(dict(path=authority_name, sha256=g.sha(deploy / authority_name), bytes=(deploy / authority_name).stat().st_size, reuse_if_identical=False))
    authority_sha = g.sha(deploy / authority_name)
    argv_name = args.label + '_arguments.json'
    output = j.windows(PureWindowsPath(root, 'output', args.label))
    argv = ['--input', input_path, '--input-sha256', report['sha256'],
            '--common-problem', j.windows(PureWindowsPath(root, COMMON)), '--common-problem-sha256', COMMON_SHA,
            '--output', output, '--threads', str(args.threads), '--wall-seconds', str(wall)]
    add_file(argv_name, argv)
    dependencies = [dict(path=j.windows(PureWindowsPath(root, item['path'])), sha256=item['sha256']) for item in records.values()]
    dependencies += [dict(path=j.windows(PureWindowsPath(root, item['path'])), sha256=item['sha256']) for item in files]
    dependencies += [dict(path=j.windows(PureWindowsPath(root, watchdog['path'])), sha256=watchdog['sha256']),
                     dict(path=j.windows(PureWindowsPath(root, launcher_rel)), sha256=launchers[0]['sha256']),
                     dict(path=input_path, sha256=report['sha256']),
                     dict(path=j.windows(PureWindowsPath(native_output, 'native_driver_result.json')), sha256=args.native_result_sha256),
                     dict(path=j.windows(PureWindowsPath(root, cfg['watchdog_id'] + '_config.json')), sha256=report['config_sha256']),
                     dict(path=j.windows(PureWindowsPath(root, 'logs', cfg['watchdog_id'] + '_finished.json')), sha256=g.sha(args.native_finished)),
                     dict(path=j.windows(PureWindowsPath(root, 'logs', cfg['watchdog_id'] + '_supervisor_finished.json')), sha256=g.sha(args.native_supervisor)),
                     dict(path=in_root(cfg['authority_file']), sha256=cfg['authority_sha256'])]
    prefix = root + '\\logs\\' + args.label
    preflight_name = args.label + '_preflight.ps1'
    preflight = """$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$root=__ROOT__; $prefix=__PREFIX__
$dependencies=__DEPS__|ConvertFrom-Json
foreach($item in $dependencies){
 if(-not(Test-Path -LiteralPath $item.path -PathType Leaf)){throw ('Missing dependency: '+$item.path)}
 if((Get-FileHash -LiteralPath $item.path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $item.sha256){throw ('Dependency changed: '+$item.path)}
}
$a=Get-Content -LiteralPath __AUTHORITY__ -Raw|ConvertFrom-Json
if($a.schema -cne 'e036-stage-a-authority-v1' -or $a.stage -cne 'A' -or @($a.allowed_labels).Count -ne 1 -or @($a.allowed_labels)[0] -cne __LABEL__){throw 'Wrong comparison authority'}
if(Test-Path -LiteralPath __OUTPUT__){throw 'Comparison output already exists'}
if(-not(Test-Path -LiteralPath __PYTHON__ -PathType Leaf)){throw 'Bound Python310 executable missing'}
foreach($suffix in @('_launch_request.json','_launch_receipt.json','_launcher_stdout.log','_launcher_stderr.log','_supervisor_attempt.json','_supervisor_started.json','_supervisor_finished.json','_watchdog_stdout.log','_watchdog_stderr.log','_attempt.json','_started.json','_finished.json','_identity_observation.json')){
 if(Test-Path -LiteralPath ($prefix+$suffix)){throw ('Attempt already consumed: '+$suffix)}
}
$busy=@(Get-CimInstance Win32_Process|Where-Object{$_.Name -match '^(MATLAB|ifx|link|python)\\.exe$'}|Select-Object ProcessId,Name,CreationDate,CommandLine)
$free=[int64](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory*1024
$disk=[int64](Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace
[pscustomobject]@{scope='read-only comparison launch preflight';label=__LABEL__;dependencies_verified=$dependencies.Count;free_memory=$free;disk_free=$disk;processes=$busy}|ConvertTo-Json -Depth 5
if($free -lt 16GB -or $disk -lt 10GB -or $busy.Count -gt 0){throw 'Producer resource conflict; no launch'}
"""
    replacements = {'__ROOT__': j.ps(root), '__PREFIX__': j.ps(prefix), '__DEPS__': j.ps(json.dumps(dependencies, separators=(',', ':'))),
                    '__AUTHORITY__': j.ps(root + '\\' + authority_name), '__LABEL__': j.ps(args.label), '__OUTPUT__': j.ps(output), '__PYTHON__': j.ps(PYTHON)}
    for key, value in replacements.items():
        preflight = preflight.replace(key, value)
    add_file(preflight_name, preflight)
    launcher_args = [r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe', '-NoProfile', '-NonInteractive',
                     '-ExecutionPolicy', 'Bypass', '-File', j.windows(PureWindowsPath(root, launcher_rel)),
                     '-Root', root, '-Label', args.label, '-Entry', j.windows(PureWindowsPath(root, COMPARATOR)),
                     '-AuthorityFile', root + '\\' + authority_name, '-AuthoritySha256', authority_sha,
                     '-WatchdogFile', j.windows(PureWindowsPath(root, watchdog['path'])), '-WatchdogSha256', watchdog['sha256'],
                     '-Kind', 'Python', '-PythonExecutable', PYTHON, '-ArgumentsFile', root + '\\' + argv_name]
    command = r'C:\Windows\System32\cmd.exe /d /s /c "' + ' '.join(map(j.command_quote, launcher_args))
    command += ' 1>' + j.command_quote(prefix + '_launcher_stdout.log') + ' 2>' + j.command_quote(prefix + '_launcher_stderr.log') + '"'
    launch_name = 'launch_' + args.label + '.ps1'
    launch = """$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$root=__ROOT__; $prefix=__PREFIX__; $check=__PREFLIGHT__
if((Get-FileHash -LiteralPath $check -Algorithm SHA256).Hash.ToLowerInvariant() -cne __PREFLIGHT_SHA__){throw 'Preflight source changed'}
& ([ScriptBlock]::Create([IO.File]::ReadAllText($check)))
function Write-NewJson([string]$path,$value){
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($value|ConvertTo-Json -Depth 8))
 $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
}
$command=__COMMAND__
Write-NewJson ($prefix+'_launch_request.json') @{label=__LABEL__;utc=[DateTime]::UtcNow.ToString('o');command=$command;authority_sha256=__AUTH_SHA__}
$result=$null
try{
 $result=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$command;CurrentDirectory=$root}
 $receipt=@{label=__LABEL__;utc=[DateTime]::UtcNow.ToString('o');return_value=$result.ReturnValue;cmd_pid=$result.ProcessId;scope='creation receipt only; comparison outcome requires child records'}
 Write-NewJson ($prefix+'_launch_receipt.json') $receipt
 $receipt|ConvertTo-Json
 if($result.ReturnValue -ne 0){throw 'WMI creation failed; preserve attempt, do not relaunch this label'}
}catch{
 $original=$_
 if($null -eq $result){try{Write-NewJson ($prefix+'_launch_receipt.json') @{label=__LABEL__;status='creation_outcome_unknown';error=$original.Exception.ToString();retry_permitted=$false}}catch{}}
 throw $original
}
"""
    replacements = {'__ROOT__': j.ps(root), '__PREFIX__': j.ps(prefix), '__PREFLIGHT__': j.ps(root + '\\' + preflight_name),
                    '__PREFLIGHT_SHA__': j.ps(g.sha(deploy / preflight_name)), '__COMMAND__': j.ps(command),
                    '__LABEL__': j.ps(args.label), '__AUTH_SHA__': j.ps(authority_sha)}
    for key, value in replacements.items():
        launch = launch.replace(key, value)
    add_file(launch_name, launch)
    deployment_name = args.label + '_deployment.json'
    g.write(deploy / deployment_name, dict(schema='e036-comparison-job-deployment-v1', files=files))
    stage = """param([Parameter(Mandatory=$true)][string]$PayloadDirectory)
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$root=__ROOT__; $manifest=Join-Path $PayloadDirectory __DEPLOYMENT__
if((Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant() -cne __DEPLOYMENT_SHA__){throw 'Deployment manifest changed'}
$items=(Get-Content -LiteralPath $manifest -Raw|ConvertFrom-Json).files
foreach($f in $items){
 $src=Join-Path $PayloadDirectory $f.path; $dest=Join-Path $root $f.path
 if((Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash.ToLowerInvariant() -cne $f.sha256){throw ('Staged bytes differ: '+$f.path)}
 if(Test-Path -LiteralPath $dest){throw ('Destination already exists: '+$f.path)}
}
foreach($f in $items){
 $src=Join-Path $PayloadDirectory $f.path; $dest=Join-Path $root $f.path
 [IO.File]::Copy($src,$dest,$false)
 if((Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLowerInvariant() -cne $f.sha256){throw ('Readback differs: '+$f.path)}
}
[pscustomobject]@{status='staged_only_no_process_started';label=__LABEL__;files=$items.Count}|ConvertTo-Json
"""
    for key, value in {'__ROOT__': j.ps(root), '__DEPLOYMENT__': j.ps(deployment_name),
                       '__DEPLOYMENT_SHA__': j.ps(g.sha(deploy / deployment_name)), '__LABEL__': j.ps(args.label)}.items():
        stage = stage.replace(key, value)
    g.write(deploy / ('stage_' + args.label + '.ps1'), stage)
    receipt = g.archive(deploy, args.label + '_job_payload.zip')
    receipt.update(scope='local metadata preparation only; no comparison, native solve, training, SSH or launch',
                   label=args.label, cycle=args.cycle, input=input_path, input_sha256=report['sha256'],
                   native_report_sha256=args.native_result_sha256, native_config_sha256=g.sha(args.native_config),
                   native_finished_sha256=g.sha(args.native_finished), native_supervisor_sha256=g.sha(args.native_supervisor),
                   authority_sha256=authority_sha, arguments=argv, dependencies=dependencies,
                   comparison_manifest_sha256=g.sha(args.compare_manifest), prepare_manifest_sha256=g.sha(args.prepare_manifest),
                   control_deployment_sha256=g.sha(args.control_deployment), generator_sha256=g.sha(__file__),
                   helper_sha256={name:g.sha(Path(__file__).with_name(name)) for name in ('prepare_stage_a_job.py', 'prepare_native_payload.py')},
                   deployment_manifest=deployment_name, preflight=preflight_name, launch=launch_name)
    g.write(args.output / 'job_receipt.json', receipt)
    print(json.dumps(receipt, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('native-result', 'native-config', 'native-finished', 'native-supervisor', 'authority-file', 'compare-manifest', 'compare-directory',
                 'prepare-manifest', 'control-deployment', 'control-directory', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--native-result-sha256', required=True)
    parser.add_argument('--cycle', type=int, choices=(1, 20, 60, 83), required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--threads', type=int, choices=range(1, 5), default=1)
    generate(parser.parse_args())


if __name__ == '__main__':
    main()
