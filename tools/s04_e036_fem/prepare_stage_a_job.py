#!/usr/bin/env python3
"""Generate local Stage A native deployment/preflight/launch files; launch nothing.

Consumes actual successful preparation receipts through prepare_native_payload.
The supplied preparation config determines every code/build/result root. No
Stage B or training mode is provided. All generated directories/files are new.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace


def load_generator():
    path = Path(__file__).with_name('prepare_native_payload.py')
    spec = importlib.util.spec_from_file_location('e036_local_native_payload', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # stdlib-only module; finalize is text/metadata work.
    return module


def ps(value):
    return "'" + str(value).replace("'", "''") + "'"


def windows(value):
    return str(PureWindowsPath(value))


def command_quote(value):
    value = str(value)
    if any(c in value for c in '"\x00\r\n%!*?<>|&^') or value.endswith('\\'):
        raise ValueError('unsafe command argument')
    return '"' + value + '"'


def generate(args):
    g = load_generator()
    cfg = g.read(args.prepare_config)
    root = windows(cfg['run_root'])
    # The successful preparation may be 03, 04, or another explicit attempt.
    # Never infer its success or substitute a previous build directory.
    control = g.read(args.control_deployment)
    controls = [r for r in control['files']
                if PureWindowsPath(r['path']).name == 'stage_a_watchdog_v4.ps1']
    if len(controls) != 1:
        raise ValueError('one exact native v4 watchdog binding is required')
    watchdog = controls[0]
    watchdog_rel = g.checked_rel(watchdog['path'])
    if g.sha(args.control_directory / watchdog_rel) != watchdog['sha256']:
        raise ValueError('local v4 control bytes differ from deployment record')
    if watchdog['sha256'] != g.sha(Path(__file__).with_name('stage_a_watchdog_v4.ps1')):
        raise ValueError('control deployment does not contain the reviewed current v4 source')
    prepare_manifest = g.read(args.prepare_manifest)
    launcher_rel = g.relative(cfg['code_root'], cfg['run_root']) + '/tools/s04_e036_fem/stage_a_launcher.ps1'
    launchers = [r for r in prepare_manifest['files'] if r['path'] == launcher_rel]
    if len(launchers) != 1:
        raise ValueError('successful preparation manifest must bind its launcher')
    launcher = launchers[0]
    overlay_name, overlay, overlay_receipt, importer_repair = g.overlay_support(args.support, root)

    args.output.mkdir(parents=False, exist_ok=False)
    # Preserve the standalone finalizer output and ZIP as separate, immutable
    # local artifacts; construct the launch payload in another fresh directory.
    finalize_args = SimpleNamespace(**vars(args))
    finalize_args.output = args.output / 'native_payload'
    with redirect_stdout(io.StringIO()):
        g.finalize(finalize_args)
    native = finalize_args.output
    job_cfg = g.read(native / (args.label + '_config.json'))
    deploy = args.output / 'deploy'
    deploy.mkdir()
    files = []

    def copy_file(source, relative, reuse=False):
        relative = g.checked_rel(relative)
        dest = deploy / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as stream:
            stream.write(Path(source).read_bytes())
        files.append(dict(path=relative, sha256=g.sha(dest), bytes=dest.stat().st_size,
                          reuse_if_identical=reuse))

    for path in sorted(native.iterdir()):
        if path.is_file():
            copy_file(path, path.name)
    for relative in sorted(overlay_receipt['files']):
        copy_file(overlay / relative, overlay_name + '/' + relative, reuse=True)
    copy_file(overlay / 'overlay_receipt.json', overlay_name + '/overlay_receipt.json', reuse=True)
    if importer_repair is not None:
        copy_file(overlay / g.IMPORTER_PATH, overlay_name + '/' + g.IMPORTER_PATH, reuse=True)

    prefix = root + '\\logs\\' + args.label
    authority = root + '\\' + args.label + '_authority.json'
    entry = root + '\\' + args.label + '_entry.m'
    preflight_name = args.label + '_preflight.ps1'
    launch_name = 'launch_' + args.label + '.ps1'
    dependency_records = [dict(path=windows(root + '\\' + r['path']), sha256=r['sha256'])
                          for r in files]
    dependency_records += [
        dict(path=windows(root + '\\' + watchdog_rel), sha256=watchdog['sha256']),
        dict(path=windows(root + '\\' + launcher_rel), sha256=launcher['sha256']),
        dict(path=windows(job_cfg['prepare_result_path']), sha256=job_cfg['prepare_result_sha256']),
        dict(path=windows(job_cfg['build_root']) + '\\completion.json', sha256=job_cfg['build_completion_sha256']),
        dict(path=windows(job_cfg['build_root']) + '\\build_receipt.json', sha256=g.sha(args.build_receipt)),
    ]
    dependency_records += [dict(path=windows(r['path']), sha256=r['sha256'])
                           for r in job_cfg['runtime_bindings']]
    for record in g.read(args.build_receipt)['source_records']:
        dependency_records.extend(dict(path=windows(record[key]), sha256=record['sha256'])
                                  for key in ('source_path', 'staged_path'))
    unique = {}
    for record in dependency_records:
        key = record['path'].lower()
        if key in unique and unique[key]['sha256'] != record['sha256']:
            raise ValueError('conflicting runtime dependency hashes')
        unique[key] = record
    dependency_records = list(unique.values())
    dependencies_json = json.dumps(dependency_records, separators=(',', ':'))
    preflight = """$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$root=__ROOT__; $prefix=__PREFIX__
function Verify-Hash([string]$path,[string]$expected) {
 if(-not(Test-Path -LiteralPath $path -PathType Leaf)){throw ('Missing dependency: '+$path)}
 if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -cne $expected){throw ('Dependency changed: '+$path)}
}
$dependencies=__DEPS__|ConvertFrom-Json
foreach($item in $dependencies){Verify-Hash $item.path $item.sha256}
$manifest=Get-Content -LiteralPath __MANIFEST__ -Raw|ConvertFrom-Json
foreach($item in $manifest.files){Verify-Hash (Join-Path $root $item.path) $item.sha256}
$a=Get-Content -LiteralPath __AUTHORITY__ -Raw|ConvertFrom-Json
if($a.schema -cne 'e036-stage-a-authority-v1' -or $a.stage -cne 'A' -or @($a.allowed_labels).Count -ne 1 -or @($a.allowed_labels)[0] -cne __LABEL__){throw 'Wrong attempt authority'}
if(Test-Path -LiteralPath __OUTPUT__){throw 'Native job output already exists'}
if(Test-Path -LiteralPath ($prefix+'_arms')){throw 'Arm receipt directory already exists'}
foreach($suffix in @('_launch_request.json','_launch_receipt.json','_launcher_stdout.log','_launcher_stderr.log','_supervisor_attempt.json','_supervisor_started.json','_supervisor_finished.json','_watchdog_stdout.log','_watchdog_stderr.log','_attempt.json','_started.json','_finished.json','_identity_observation.json')) {
 if(Test-Path -LiteralPath ($prefix+$suffix)){throw ('Attempt already consumed: '+$suffix)}
}
$busy=@(Get-CimInstance Win32_Process|Where-Object{$_.Name -match '^(MATLAB|ifx|link|python)\\.exe$'}|Select-Object ProcessId,Name,CreationDate,CommandLine)
$free=[int64](Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory*1024
$disk=[int64](Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").FreeSpace
[pscustomobject]@{scope='read-only Stage A launch preflight';label=__LABEL__;source_files_verified=$manifest.files.Count;dependency_files_verified=$dependencies.Count;free_memory=$free;disk_free=$disk;processes=$busy}|ConvertTo-Json -Depth 5
if($free -lt 16GB -or $disk -lt 10GB -or $busy.Count -gt 0){throw 'Producer resource conflict; no launch'}
"""
    replacements = {'__ROOT__': ps(root), '__PREFIX__': ps(prefix), '__DEPS__': ps(dependencies_json),
                    '__MANIFEST__': ps(windows(job_cfg['manifest_path'])), '__AUTHORITY__': ps(authority),
                    '__LABEL__': ps(args.label), '__OUTPUT__': ps(windows(job_cfg['output_dir']))}
    for key, value in replacements.items():
        preflight = preflight.replace(key, value)
    g.write(deploy / preflight_name, preflight)
    files.append(dict(path=preflight_name, sha256=g.sha(deploy / preflight_name),
                      bytes=(deploy / preflight_name).stat().st_size, reuse_if_identical=False))

    launcher_args = [r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe',
                     '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File',
                     windows(root + '\\' + launcher_rel), '-Root', root, '-Label', args.label,
                     '-Entry', entry, '-AuthorityFile', authority,
                     '-AuthoritySha256', job_cfg['authority_sha256'],
                     '-WatchdogFile', windows(root + '\\' + watchdog_rel),
                     '-WatchdogSha256', watchdog['sha256'], '-Kind', 'Matlab']
    if args.mode == 'disabled':
        launcher_args.append('-RequireArms')
    command = r'C:\Windows\System32\cmd.exe /d /s /c "' + ' '.join(map(command_quote, launcher_args))
    command += ' 1>' + command_quote(prefix + '_launcher_stdout.log')
    command += ' 2>' + command_quote(prefix + '_launcher_stderr.log') + '"'
    launch = """$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$root=__ROOT__; $prefix=__PREFIX__; $check=__PREFLIGHT__
if((Get-FileHash -LiteralPath $check -Algorithm SHA256).Hash.ToLowerInvariant() -cne __PREFLIGHT_SHA__){throw 'Preflight source changed'}
& ([ScriptBlock]::Create([IO.File]::ReadAllText($check)))
function Write-NewJson([string]$path,$value) {
 $bytes=[Text.UTF8Encoding]::new($false).GetBytes(($value|ConvertTo-Json -Depth 8))
 $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
}
$command=__COMMAND__
Write-NewJson ($prefix+'_launch_request.json') @{label=__LABEL__;utc=[DateTime]::UtcNow.ToString('o');command=$command;authority_sha256=__AUTH_SHA__}
$result=$null
try {
 $result=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$command;CurrentDirectory=$root}
 $receipt=@{label=__LABEL__;utc=[DateTime]::UtcNow.ToString('o');return_value=$result.ReturnValue;cmd_pid=$result.ProcessId;scope='creation receipt only; scientific outcome requires child records'}
 Write-NewJson ($prefix+'_launch_receipt.json') $receipt
 $receipt|ConvertTo-Json
 if($result.ReturnValue -ne 0){throw 'WMI creation failed; preserve attempt, do not relaunch this label'}
} catch {
 $original=$_
 if($null -eq $result){try{Write-NewJson ($prefix+'_launch_receipt.json') @{label=__LABEL__;status='creation_outcome_unknown';error=$original.Exception.ToString();retry_permitted=$false}}catch{}}
 throw $original
}
"""
    replacements = {'__ROOT__': ps(root), '__PREFIX__': ps(prefix), '__LABEL__': ps(args.label),
                    '__PREFLIGHT__': ps(root + '\\' + preflight_name),
                    '__PREFLIGHT_SHA__': ps(g.sha(deploy / preflight_name)),
                    '__COMMAND__': ps(command), '__AUTH_SHA__': ps(job_cfg['authority_sha256'])}
    for key, value in replacements.items():
        launch = launch.replace(key, value)
    g.write(deploy / launch_name, launch)
    files.append(dict(path=launch_name, sha256=g.sha(deploy / launch_name),
                      bytes=(deploy / launch_name).stat().st_size, reuse_if_identical=False))
    deployment_name = args.label + '_deployment.json'
    g.write(deploy / deployment_name, dict(schema='e036-native-job-deployment-v1', files=files))
    stage = """param([Parameter(Mandatory=$true)][string]$PayloadDirectory)
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$root=__ROOT__; $manifest=Join-Path $PayloadDirectory __DEPLOYMENT__
if((Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant() -cne __DEPLOYMENT_SHA__){throw 'Deployment manifest changed'}
$items=(Get-Content -LiteralPath $manifest -Raw|ConvertFrom-Json).files
foreach($f in $items){
 $src=Join-Path $PayloadDirectory $f.path; $dest=Join-Path $root $f.path
 if((Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash.ToLowerInvariant() -cne $f.sha256){throw ('Staged bytes differ: '+$f.path)}
 if(Test-Path -LiteralPath $dest){
  if(-not $f.reuse_if_identical -or (Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLowerInvariant() -cne $f.sha256){throw ('Destination exists or differs: '+$f.path)}
 }
}
foreach($f in $items){
 $src=Join-Path $PayloadDirectory $f.path; $dest=Join-Path $root $f.path
 if(-not(Test-Path -LiteralPath $dest)){
  [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($dest))|Out-Null
  [IO.File]::Copy($src,$dest,$false)
 }
 if((Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLowerInvariant() -cne $f.sha256){throw ('Readback differs: '+$f.path)}
}
[pscustomobject]@{status='staged_only_no_process_started';label=__LABEL__;files=$items.Count}|ConvertTo-Json
"""
    for key, value in {'__ROOT__': ps(root), '__DEPLOYMENT__': ps(deployment_name),
                       '__DEPLOYMENT_SHA__': ps(g.sha(deploy / deployment_name)),
                       '__LABEL__': ps(args.label)}.items():
        stage = stage.replace(key, value)
    g.write(deploy / ('stage_' + args.label + '.ps1'), stage)
    receipt = g.archive(deploy, args.label + '_job_payload.zip')
    receipt.update(scope='local text preparation only; no SSH, launch, MATLAB, FE assembly or training',
                   mode=args.mode, label=args.label, code_root=cfg['code_root'], build_root=cfg['build_root'],
                   prepare_result_path=job_cfg['prepare_result_path'], generator_sha256=g.sha(__file__),
                   native_generator_sha256=g.sha(Path(__file__).with_name('prepare_native_payload.py')),
                   watchdog_path=root + '\\' + watchdog_rel, watchdog_sha256=watchdog['sha256'],
                   deployment_manifest=deployment_name, preflight=preflight_name, launch=launch_name,
                   dependencies=dependency_records)
    g.write(args.output / 'job_receipt.json', receipt)
    print(json.dumps(receipt, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('support', 'inventory', 'snapshot-receipt', 'prepare-config', 'prepare-result',
                 'build-receipt', 'build-completion', 'prepare-manifest', 'authority-file',
                 'control-deployment', 'control-directory', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--mode', choices=('disabled', 'frozen_c1', 'frozen_c20', 'frozen_c60', 'frozen_c83'), required=True)
    generate(parser.parse_args())


if __name__ == '__main__':
    main()
