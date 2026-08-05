$ErrorActionPreference = 'Stop'
$TestDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HandoffDir = Split-Path -Parent $TestDir
$RepoRoot = Split-Path -Parent (Split-Path -Parent $HandoffDir)
$Launcher = Join-Path $HandoffDir 'launch_toy_road_runtime_diagnostic.ps1'
$Adapter = Join-Path $HandoffDir 'invoke_toy_road_d1_test_process_adapter.ps1'
$Python = ([string](& py -3 -c "import sys;print(sys.executable)")).Trim()
$PythonSha = (Get-FileHash $Python -Algorithm SHA256).Hash.ToLowerInvariant()

function Write-Utf8Json([string]$Path,[object]$Value) {
    $bytes = (New-Object Text.UTF8Encoding($false)).GetBytes(
        ($Value | ConvertTo-Json -Depth 30 -Compress))
    [IO.File]::WriteAllBytes($Path,$bytes)
}

function New-Fixture([string]$Root) {
    $paths = @((Join-Path $Root 'overlay'),$HandoffDir)
    $lock = [ordered]@{
        schema_version = 'toy_road_runtime_diagnostic_lock_v1'
        authorization_scope = 'diagnostic_only_non_authorizing'
        producer_entrypoint_authorized = $false
        source_commit = 'eeda43d9faef01622731e877c5048a78f3c5003a'
        source_manifest_sha256 = ('1' * 64)
        source_execution_lock_sha256 = ('2' * 64)
        runtime_expectations = [ordered]@{
            matlab = [ordered]@{
                absolute_path_order = $paths
                release = 'R2025b'; update = 'Update 5'; version = '25.2.0'
                computer = 'PCWIN64'; executable_sha256 = ('3' * 64)
                blas = 'BLAS'; lapack = 'LAPACK'
            }
            binary_sha256 = [ordered]@{
                initial=('4'*64); AMOR=('5'*64)
                AT1_HISTORY_FATIGUE=('6'*64); cholmod2=('7'*64)
            }
        }
        thread_environment = [ordered]@{
            OMP_NUM_THREADS='1'; MKL_NUM_THREADS='1'
            OPENBLAS_NUM_THREADS='1'; MKL_DYNAMIC='FALSE'
        }
        thread_setting_source = [ordered]@{
            path='producer_handoffs/toy_road_p0_repeatability_20260803/launch_toy_road_family_case.ps1'
            source_commit='eeda43d9faef01622731e877c5048a78f3c5003a'
            sha256='03d415ad96a484e9a98565fced0d6b8d2f90ffb781d48192a445d19ed5d5e728'
            settings=[ordered]@{OMP_NUM_THREADS='1';MKL_NUM_THREADS='1';OPENBLAS_NUM_THREADS='1';MKL_DYNAMIC='FALSE'}
        }
        diagnostic_root = (Join-Path $Root 'evidence')
        writable_roots = [ordered]@{
            work=(Join-Path $Root 'work');temp=(Join-Path $Root 'temp')
            tmp=(Join-Path $Root 'tmp');pref=(Join-Path $Root 'pref')
            cache=(Join-Path $Root 'cache')
            matlab_startup_pref=(Join-Path $Root 'matlab-pref')
        }
    }
    $transform = [ordered]@{
        schema_version='toy_road_runtime_lock_transformation_v1'
        source_execution_lock_sha256=('2'*64)
        diagnostic_lock_sha256=('8'*64)
        replacements=@()
        unchanged_fields_sha256_before=('9'*64)
        unchanged_fields_sha256_after=('9'*64)
        thread_setting_source=$lock.thread_setting_source
        authorization_artifact_read=$false
        production_output_root_present=$false
    }
    $receipt = [ordered]@{
        schema_version='toy_road_runtime_diagnostic_v1';status='PASS'
        authorization_scope='diagnostic_only_non_authorizing'
        producer_entrypoint_authorized=$false;predicates=@()
        first_failed_predicate=$null;producer_invocation_count=0
        fem_cycle_count=0;completed_predicate_count=24
    }
    $sourceIdentity = [ordered]@{
        authorization_scope='test_only_non_authorizing'
        source_commit=$lock.source_commit
        source_clean=$true
    }
    $lockPath=Join-Path $Root 'input-lock.json'
    $transformPath=Join-Path $Root 'input-transform.json'
    $receiptPath=Join-Path $Root 'measurement.json'
    $identityPath=Join-Path $Root 'source-identity.json'
    Write-Utf8Json $lockPath $lock
    Write-Utf8Json $transformPath $transform
    Write-Utf8Json $receiptPath $receipt
    Write-Utf8Json $identityPath $sourceIdentity
    return [ordered]@{lock=$lockPath;transform=$transformPath;measurement=$receiptPath;identity=$identityPath;evidence=$lock.diagnostic_root}
}

function Invoke-Fixture([int]$AdapterExitCode=0) {
    $root=Join-Path $env:TEMP ('toy-road-d1-launcher-'+[Guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($root) | Out-Null
    $fixture=New-Fixture $root
    $fakeMatlab=Join-Path $root 'matlab.exe'
    [IO.File]::WriteAllBytes($fakeMatlab,[byte[]](1,2,3))
    $matlabSha=(Get-FileHash $fakeMatlab -Algorithm SHA256).Hash.ToLowerInvariant()
    $arguments=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$Launcher,
        '-SourceRoot',$RepoRoot,'-ExpectedSourceCommit','eeda43d9faef01622731e877c5048a78f3c5003a',
        '-DiagnosticLockPath',$fixture.lock,'-TransformationPath',$fixture.transform,
        '-EvidenceRoot',$fixture.evidence,'-MatlabExecutable',$fakeMatlab,
        '-ApprovedMatlabSha256',$matlabSha,'-PythonExecutable',$Python,
        '-ApprovedPythonSha256',$PythonSha,'-TestOnlyNonAuthorizing',
        '-TestSourceIdentityFixturePath',$fixture.identity,
        '-TestDiagnosticReceiptFixturePath',$fixture.measurement,
        '-TestAdapterExitCode',$AdapterExitCode)
    $prior=$ErrorActionPreference
    $ErrorActionPreference='Continue'
    try{
        $output=& powershell @arguments 2>&1 | Out-String
        $exit=$LASTEXITCODE
    }finally{$ErrorActionPreference=$prior}
    return [ordered]@{exit=$exit;output=$output;root=$root;evidence=$fixture.evidence}
}

if(-not (Test-Path $Launcher -PathType Leaf)){throw 'D1 launcher is missing.'}
if(-not (Test-Path $Adapter -PathType Leaf)){throw 'D1 test adapter is missing.'}
$launcherText=Get-Content $Launcher -Raw
foreach($forbidden in @('ExecutionAuthorizationPath','AuthorizationId','ProductionOutputRoot','main_toy_road_family_case','solve_toy_road_family_case')){
    if($launcherText.Contains($forbidden)){throw "Forbidden launcher surface: $forbidden"}
}

$pass=Invoke-Fixture
try {
    if($pass.exit -ne 0){throw "PASS fixture failed: $($pass.output)"}
    $files=@(Get-ChildItem $pass.evidence -File)
    if($files.Count -ne 10){throw "Complete package has $($files.Count) files, expected 10."}
    $sums=Get-Content (Join-Path $pass.evidence 'D1_SHA256SUMS.txt')
    if($sums.Count -ne 9){throw "Checksum file has $($sums.Count) entries."}
    $terminal=Get-Content (Join-Path $pass.evidence 'D1_TERMINAL.json') -Raw | ConvertFrom-Json
    if($terminal.producer_invocation_count -ne 0 -or $terminal.fem_cycle_count -ne 0 -or
            $terminal.production_authorized -ne $false){throw 'Terminal non-production fields are invalid.'}
    $batch=Get-Content (Join-Path $pass.evidence 'D1_EXACT_BATCH_COMMAND.txt') -Raw
    if(([regex]::Matches($batch,'run_toy_road_runtime_diagnostic\s*\(')).Count -ne 1 -or
            $batch -match 'main_toy_road_family_case|solve_toy_road_family_case'){
        throw 'Exact batch is not diagnostic-only.'
    }
} finally {Remove-Item $pass.root -Recurse -Force -ErrorAction SilentlyContinue}

$crash=Invoke-Fixture 17
try {
    if($crash.exit -eq 0){throw 'Crash fixture unexpectedly passed.'}
    if(-not (Test-Path (Join-Path $crash.evidence 'D1_LAUNCHER_RECOVERY.json'))){
        throw 'Crash fixture lacks launcher recovery evidence.'
    }
    if(Test-Path (Join-Path $crash.evidence 'D1_TERMINAL.json')){
        throw 'Crash fixture fabricated a terminal record.'
    }
} finally {Remove-Item $crash.root -Recurse -Force -ErrorAction SilentlyContinue}

Write-Output 'toyRoadD1LauncherTest: PASS'
