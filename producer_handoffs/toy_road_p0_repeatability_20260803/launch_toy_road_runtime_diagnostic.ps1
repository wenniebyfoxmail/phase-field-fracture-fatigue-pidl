param(
    [Parameter(Mandatory = $true)][string]$SourceRoot,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{40}$')][string]$ExpectedSourceCommit,
    [Parameter(Mandatory = $true)][string]$DiagnosticLockPath,
    [Parameter(Mandatory = $true)][string]$TransformationPath,
    [Parameter(Mandatory = $true)][string]$SourceExecutionLockPath,
    [Parameter(Mandatory = $true)][string]$EvidenceRoot,
    [Parameter(Mandatory = $true)][string]$MatlabExecutable,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ApprovedMatlabSha256,
    [Parameter(Mandatory = $true)][string]$PythonExecutable,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ApprovedPythonSha256,
    [switch]$TestOnlyNonAuthorizing,
    [string]$TestSourceIdentityFixturePath = '',
    [string]$TestDiagnosticReceiptFixturePath = '',
    [int]$TestAdapterExitCode = 0
)

$ErrorActionPreference='Stop'
$scriptPath=[IO.Path]::GetFullPath($MyInvocation.MyCommand.Path)
$handoffDir=Split-Path -Parent $scriptPath
$source=[IO.Path]::GetFullPath($SourceRoot)
$evidence=[IO.Path]::GetFullPath($EvidenceRoot)
$inputLock=[IO.Path]::GetFullPath($DiagnosticLockPath)
$inputTransform=[IO.Path]::GetFullPath($TransformationPath)
$sourceLockPath=[IO.Path]::GetFullPath($SourceExecutionLockPath)
$matlab=[IO.Path]::GetFullPath($MatlabExecutable)
$python=[IO.Path]::GetFullPath($PythonExecutable)
$commit=$ExpectedSourceCommit.ToLowerInvariant()
$probe=Join-Path $handoffDir 'run_toy_road_runtime_diagnostic.m'
$protocol=Join-Path $handoffDir 'toy_road_d1_protocol.py'
$adapter=Join-Path $handoffDir 'invoke_toy_road_d1_test_process_adapter.ps1'
$stage='before_evidence_reservation'
$childExit=$null

function Get-Sha256([string]$Path){
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Write-BytesCreateNew([string]$Path,[byte[]]$Bytes){
    $stream=$null
    try{
        $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write,[IO.FileShare]::None)
        $stream.Write($Bytes,0,$Bytes.Length);$stream.Flush($true)
    }finally{if($null -ne $stream){$stream.Dispose()}}
}
function Write-JsonCreateNew([string]$Path,[object]$Value){
    $bytes=(New-Object Text.UTF8Encoding($false)).GetBytes(
        ($Value|ConvertTo-Json -Depth 50 -Compress))
    Write-BytesCreateNew $Path $bytes
}
function Escape-Matlab([string]$Value){return "'"+$Value.Replace("'","''")+"'"}
function Get-ExperimentProcesses {
    return @(Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.Id -ne $PID -and $_.ProcessName -in @('MATLAB','matlab','mpiexec','solver','fem')
    } | ForEach-Object {[ordered]@{name=$_.ProcessName;pid=$_.Id}})
}
function Assert-FileIdentity([string]$Path,[string]$Expected,[string]$Label){
    if(-not (Test-Path -LiteralPath $Path -PathType Leaf)){throw "$Label is missing."}
    if((Get-Sha256 $Path) -cne $Expected.ToLowerInvariant()){
        throw "$Label SHA-256 differs from the approved identity."
    }
}
function Get-ObservedFiles([string]$Root){
    if(-not (Test-Path -LiteralPath $Root -PathType Container)){return @()}
    return @(Get-ChildItem -LiteralPath $Root -File | Sort-Object Name | ForEach-Object {
        [ordered]@{name=$_.Name;sha256=Get-Sha256 $_.FullName}
    })
}

try{
    foreach($path in @($inputLock,$inputTransform,$sourceLockPath,$probe,$protocol,
            $matlab,$python)){
        if(-not (Test-Path -LiteralPath $path -PathType Leaf)){throw "Required D1 input is missing: $path"}
    }
    Assert-FileIdentity $matlab $ApprovedMatlabSha256 'MATLAB executable'
    Assert-FileIdentity $python $ApprovedPythonSha256 'Python executable'
    if(Test-Path -LiteralPath $evidence){throw 'D1 evidence root already exists.'}
    if($TestOnlyNonAuthorizing){
        if([string]::IsNullOrWhiteSpace($TestSourceIdentityFixturePath) -or
                [string]::IsNullOrWhiteSpace($TestDiagnosticReceiptFixturePath)){
            throw 'Test-only launcher requires both sealed fixture paths.'
        }
        $identity=Get-Content -LiteralPath $TestSourceIdentityFixturePath -Raw|ConvertFrom-Json
        if([string]$identity.authorization_scope -cne 'test_only_non_authorizing' -or
                [string]$identity.source_commit -cne $commit -or $identity.source_clean -ne $true){
            throw 'Test-only source identity fixture is invalid.'
        }
    }else{
        if(-not [string]::IsNullOrWhiteSpace($TestSourceIdentityFixturePath) -or
                -not [string]::IsNullOrWhiteSpace($TestDiagnosticReceiptFixturePath) -or
                $TestAdapterExitCode -ne 0){throw 'Test seam is forbidden outside test-only scope.'}
        $head=([string](& git -C $source rev-parse HEAD)).Trim().ToLowerInvariant()
        if($LASTEXITCODE -ne 0 -or $head -cne $commit){throw 'D1 source commit differs.'}
        if(@(& git -C $source status --porcelain --untracked-files=all).Count -ne 0){
            throw 'D1 source checkout must be clean.'
        }
    }
    & $python $protocol --validate-lock $sourceLockPath $inputLock $inputTransform | Out-Null
    if($LASTEXITCODE -ne 0){throw 'D1 source-to-diagnostic lock transformation is invalid.'}
    $before=@(Get-ExperimentProcesses)
    if($before.Count -ne 0){throw 'An existing MATLAB/FEM process blocks D1.'}

    [IO.Directory]::CreateDirectory($evidence)|Out-Null
    $stage='evidence_reserved'
    $lockOut=Join-Path $evidence 'D1_DIAGNOSTIC_LOCK.json'
    $transformOut=Join-Path $evidence 'D1_LOCK_TRANSFORMATION.json'
    Write-BytesCreateNew $lockOut ([IO.File]::ReadAllBytes($inputLock))
    Write-BytesCreateNew $transformOut ([IO.File]::ReadAllBytes($inputTransform))
    $lock=Get-Content -LiteralPath $lockOut -Raw|ConvertFrom-Json
    $transform=Get-Content -LiteralPath $transformOut -Raw|ConvertFrom-Json
    if([string]$lock.authorization_scope -cne 'diagnostic_only_non_authorizing' -or
            $lock.producer_entrypoint_authorized -ne $false){throw 'D1 lock is not diagnostic-only.'}
    if([IO.Path]::GetFullPath([string]$lock.diagnostic_root) -cne $evidence){
        throw 'D1 evidence root differs from the diagnostic lock.'
    }
    foreach($property in $lock.writable_roots.PSObject.Properties){
        $root=[IO.Path]::GetFullPath([string]$property.Value)
        if(Test-Path -LiteralPath $root){throw "D1 writable root already exists: $root"}
        [IO.Directory]::CreateDirectory($root)|Out-Null
    }
    $overlayReplacement=@($transform.replacements | Where-Object {
        [string]$_.field -ceq 'runtime_expectations.matlab.absolute_path_order[0]'})
    if($overlayReplacement.Count -ne 1){throw 'D1 overlay transformation is missing or duplicated.'}
    $oldOverlay=[IO.Path]::GetFullPath([string]$overlayReplacement[0].old)
    $newOverlay=[IO.Path]::GetFullPath([string]$overlayReplacement[0].new)
    if(Test-Path -LiteralPath $newOverlay){throw 'Fresh D1 rebuilt-MEX overlay already exists.'}
    $initialCandidates=@(Get-ChildItem -LiteralPath $oldOverlay -Recurse -File -Filter 'initial.mexw64')
    if($initialCandidates.Count -ne 1){throw 'Approved rebuilt initial.mexw64 source is not unique.'}
    $overlaySource=$initialCandidates[0].FullName
    if((Get-Sha256 $overlaySource) -cne [string]$lock.runtime_expectations.binary_sha256.initial){
        throw 'Approved rebuilt initial.mexw64 source hash differs from lock.'
    }
    $relativeInitial=$overlaySource.Substring($oldOverlay.TrimEnd('\').Length+1)
    $overlayTarget=Join-Path $newOverlay $relativeInitial
    [IO.Directory]::CreateDirectory((Split-Path -Parent $overlayTarget))|Out-Null
    New-Item -ItemType HardLink -Path $overlayTarget -Target $overlaySource | Out-Null
    if((Get-Sha256 $overlayTarget) -cne [string]$lock.runtime_expectations.binary_sha256.initial){
        throw 'Fresh rebuilt-MEX overlay target hash differs from lock.'
    }
    foreach($property in $lock.thread_environment.PSObject.Properties){
        Set-Item -Path "Env:$($property.Name)" -Value ([string]$property.Value)
    }
    $env:TEMP=[string]$lock.writable_roots.temp
    $env:TMP=[string]$lock.writable_roots.tmp
    $env:MATLAB_PREFDIR=[string]$lock.writable_roots.matlab_startup_pref
    $env:MCR_CACHE_ROOT=[string]$lock.writable_roots.cache

    $pathCommands=@()
    $paths=@($lock.runtime_expectations.matlab.absolute_path_order)
    for($index=$paths.Count-1;$index -ge 0;$index--){
        $pathCommands += 'addpath('+(Escape-Matlab ([string]$paths[$index]))+",'-begin')"
    }
    $pathCommands += 'addpath('+(Escape-Matlab $handoffDir)+",'-end')"
    $receiptPath=Join-Path $evidence 'D1_RUNTIME_DIAGNOSTIC.json'
    $probeCall='run_toy_road_runtime_diagnostic('+(Escape-Matlab $lockOut)+','+
        (Escape-Matlab $receiptPath)+')'
    $batch=(($pathCommands+$probeCall)-join ';')+';'
    $utf8=New-Object Text.UTF8Encoding($false)
    $batchPath=Join-Path $evidence 'D1_EXACT_BATCH_COMMAND.txt'
    Write-BytesCreateNew $batchPath $utf8.GetBytes($batch)
    $batchSha=[BitConverter]::ToString(
        [Security.Cryptography.SHA256]::Create().ComputeHash($utf8.GetBytes($batch))).
        Replace('-','').ToLowerInvariant()
    $provenance=[ordered]@{
        schema_version='toy_road_d1_launch_provenance_v1'
        authorization_scope='diagnostic_only_non_authorizing'
        source_commit=$commit;launcher_path=$scriptPath;launcher_sha256=Get-Sha256 $scriptPath
        probe_path=$probe;probe_sha256=Get-Sha256 $probe
        source_execution_lock_path=$sourceLockPath
        source_execution_lock_sha256=Get-Sha256 $sourceLockPath
        diagnostic_lock_sha256=Get-Sha256 $lockOut
        transformation_sha256=Get-Sha256 $transformOut
        overlay_source_path=$overlaySource;overlay_target_path=$overlayTarget
        overlay_initial_sha256=Get-Sha256 $overlayTarget
        matlab_path=$matlab;matlab_sha256=Get-Sha256 $matlab
        python_path=$python;python_sha256=Get-Sha256 $python
        path_construction=$pathCommands;environment=$lock.thread_environment
        thread_setting_source=$lock.thread_setting_source
        batch_sha256=$batchSha;authorization_path_present=$false
        production_output_parameter_present=$false
    }
    Write-JsonCreateNew (Join-Path $evidence 'D1_LAUNCH_PROVENANCE.json') $provenance
    Write-JsonCreateNew (Join-Path $evidence 'D1_PROCESS_BEFORE.json') ([ordered]@{
        schema_version='toy_road_d1_process_inventory_v1';processes=$before;count=$before.Count})
    $stage='before_child_process'
    $stdoutPath=Join-Path $evidence 'MATLAB_STDOUT_STDERR.txt'
    if($TestOnlyNonAuthorizing){
        $invocation=Join-Path ([string]$lock.writable_roots.work) 'D1_TEST_INVOCATION.json'
        $base64=[Convert]::ToBase64String($utf8.GetBytes($batch))
        & powershell -NoProfile -ExecutionPolicy Bypass -File $adapter `
            -BatchCommandBase64 $base64 `
            -DiagnosticReceiptFixturePath $TestDiagnosticReceiptFixturePath `
            -DiagnosticReceiptPath $receiptPath -InvocationRecordPath $invocation `
            -StdoutStderrPath $stdoutPath -ExitCode $TestAdapterExitCode
        $childExit=$LASTEXITCODE
    }else{
        $priorErrorAction=$ErrorActionPreference
        $ErrorActionPreference='Continue'
        try{
            $childOutput=@(& $matlab -batch $batch 2>&1)
            $childExit=$LASTEXITCODE
        }finally{
            $ErrorActionPreference=$priorErrorAction
        }
        $childText=($childOutput|ForEach-Object{[string]$_}) -join "`n"
        Write-BytesCreateNew $stdoutPath $utf8.GetBytes($childText+"`n")
    }
    $stage='after_child_process'
    if(-not (Test-Path -LiteralPath $receiptPath -PathType Leaf)){
        throw 'D1 diagnostic receipt is missing after child exit.'
    }
    $receipt=Get-Content -LiteralPath $receiptPath -Raw|ConvertFrom-Json
    if([string]$receipt.authorization_scope -cne 'diagnostic_only_non_authorizing' -or
            $receipt.producer_invocation_count -ne 0 -or $receipt.fem_cycle_count -ne 0){
        throw 'D1 diagnostic receipt violates the non-production boundary.'
    }
    if([string]$receipt.status -notin @('PASS','FAIL')){
        throw 'D1 diagnostic receipt is not terminal.'
    }
    if($childExit -ne 0 -and [string]$receipt.status -cne 'FAIL'){
        throw "D1 diagnostic child failed without a terminal FAIL receipt: $childExit."
    }
    $after=@(Get-ExperimentProcesses)
    Write-JsonCreateNew (Join-Path $evidence 'D1_PROCESS_AFTER.json') ([ordered]@{
        schema_version='toy_road_d1_process_inventory_v1';processes=$after;count=$after.Count})
    $terminal=[ordered]@{
        schema_version='toy_road_d1_terminal_v1';status='D1_DIAGNOSTIC_EVIDENCE_COMPLETE'
        diagnostic_result=[string]$receipt.status;production_authorized=$false
        authorization_consumed=$false;automatic_retry_performed=$false
        producer_invocation_count=0;fem_cycle_count=0
        matlab_process_count_before=$before.Count;matlab_process_count_after=$after.Count
        child_exit_code=$childExit;production_output_absent=$true
    }
    Write-JsonCreateNew (Join-Path $evidence 'D1_TERMINAL.json') $terminal
    $stage='terminal_written'
    $names=@('D1_DIAGNOSTIC_LOCK.json','D1_EXACT_BATCH_COMMAND.txt',
        'D1_LAUNCH_PROVENANCE.json','D1_LOCK_TRANSFORMATION.json',
        'D1_PROCESS_AFTER.json','D1_PROCESS_BEFORE.json','D1_RUNTIME_DIAGNOSTIC.json',
        'D1_TERMINAL.json','MATLAB_STDOUT_STDERR.txt')
    $lines=@($names|Sort-Object|ForEach-Object{"$(Get-Sha256 (Join-Path $evidence $_))  $_"})
    Write-BytesCreateNew (Join-Path $evidence 'D1_SHA256SUMS.txt') `
        $utf8.GetBytes(($lines -join "`n")+"`n")
    Write-Output ($terminal|ConvertTo-Json -Depth 20 -Compress)
}catch{
    if((Test-Path -LiteralPath $evidence -PathType Container) -and
            -not (Test-Path -LiteralPath (Join-Path $evidence 'D1_TERMINAL.json'))){
        $recovery=[ordered]@{
            schema_version='toy_road_d1_launcher_recovery_v1';status='PARTIAL_FAIL'
            authorization_scope='diagnostic_only_non_authorizing';stage=$stage
            exception_type=$_.Exception.GetType().FullName
            exception_message=$_.Exception.Message
            exception_stack=[string]$_.ScriptStackTrace
            child_exit_code=$childExit;observed_files=@(Get-ObservedFiles $evidence)
            producer_invocation_count=0;fem_cycle_count=0
            automatic_retry_performed=$false
        }
        $recoveryPath=Join-Path $evidence 'D1_LAUNCHER_RECOVERY.json'
        if(-not (Test-Path -LiteralPath $recoveryPath)){
            Write-JsonCreateNew $recoveryPath $recovery
        }
    }
    throw
}
