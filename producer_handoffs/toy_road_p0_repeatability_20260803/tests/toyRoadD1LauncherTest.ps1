$ErrorActionPreference = 'Stop'
$TestDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HandoffDir = Split-Path -Parent $TestDir
$RepoRoot = Split-Path -Parent (Split-Path -Parent $HandoffDir)
$Launcher = Join-Path $HandoffDir 'launch_toy_road_runtime_diagnostic.ps1'
$Adapter = Join-Path $HandoffDir 'invoke_toy_road_d1_test_process_adapter.ps1'
$Protocol = Join-Path $HandoffDir 'toy_road_d1_protocol.py'
$Python = ([string](& py -3 -c "import sys;print(sys.executable)")).Trim()
$PythonSha = (Get-FileHash $Python -Algorithm SHA256).Hash.ToLowerInvariant()

function Write-Utf8Json([string]$Path,[object]$Value) {
    $bytes = (New-Object Text.UTF8Encoding($false)).GetBytes(
        ($Value | ConvertTo-Json -Depth 30 -Compress))
    [IO.File]::WriteAllBytes($Path,$bytes)
}

function New-Fixture([string]$Root,[string]$Status='PASS') {
    $oldOverlay=Join-Path $Root 'quarantine\old-overlay'
    $initialSource=Join-Path $oldOverlay '+phase_field\+mex\+fem\+assembly\+equilibrium\initial.mexw64'
    [IO.Directory]::CreateDirectory((Split-Path -Parent $initialSource))|Out-Null
    [IO.File]::WriteAllBytes($initialSource,[byte[]](9,8,7,6))
    $initialSha=(Get-FileHash $initialSource -Algorithm SHA256).Hash.ToLowerInvariant()
    $sourceLock = [ordered]@{
        schema_version = 'toy_road_execution_input_lock_v1'
        protocol_version='toy-road-p0-repeatability-v2.1'
        authorization_scope='production_authorized';case_id='P0_parent'
        source_commit = 'eeda43d9faef01622731e877c5048a78f3c5003a'
        source_manifest_sha256=('1'*64);runtime_lock_sha256=('2'*64)
        family_contract_sha256=('3'*64);case_physics_contract_sha256=('4'*64)
        launch_timestamp_utc='2026-08-04T13:17:28Z';no_clobber_receipt_id='fixture'
        resume_allowed=$false
        runtime_expectations = [ordered]@{
            matlab = [ordered]@{
                absolute_path_order = @($oldOverlay,$HandoffDir)
                release = 'R2025b'; update = 'Update 5'; version = '25.2.0'
                computer = 'PCWIN64'; executable_sha256 = ('3' * 64)
                blas = 'BLAS'; lapack = 'LAPACK'
            }
            binary_sha256 = [ordered]@{
                initial=$initialSha; AMOR=('5'*64)
                AT1_HISTORY_FATIGUE=('6'*64); cholmod2=('7'*64)
            }
        }
        writable_roots=[ordered]@{
            output=(Join-Path $Root 'quarantine\output');work=(Join-Path $Root 'quarantine\work')
            temp=(Join-Path $Root 'quarantine\temp');tmp=(Join-Path $Root 'quarantine\tmp')
            pref=(Join-Path $Root 'quarantine\pref');cache=(Join-Path $Root 'quarantine\cache')
            matlab_startup_pref=(Join-Path $Root 'quarantine\matlab-pref')
        }
    }
    $diagnosticRoot=Join-Path $Root 'evidence'
    $threadSource=[ordered]@{
            path='producer_handoffs/toy_road_p0_repeatability_20260803/launch_toy_road_family_case.ps1'
            source_commit='eeda43d9faef01622731e877c5048a78f3c5003a'
            sha256='03d415ad96a484e9a98565fced0d6b8d2f90ffb781d48192a445d19ed5d5e728'
            settings=[ordered]@{OMP_NUM_THREADS='1';MKL_NUM_THREADS='1';OPENBLAS_NUM_THREADS='1';MKL_DYNAMIC='FALSE'}
    }
    $relocation=[ordered]@{
        diagnostic_root=$diagnosticRoot;old_overlay=$oldOverlay
        new_overlay=(Join-Path $diagnosticRoot 'overlay')
        writable_roots=[ordered]@{
            work=(Join-Path $diagnosticRoot 'work');temp=(Join-Path $diagnosticRoot 'temp')
            tmp=(Join-Path $diagnosticRoot 'tmp');pref=(Join-Path $diagnosticRoot 'pref')
            cache=(Join-Path $diagnosticRoot 'cache')
            matlab_startup_pref=(Join-Path $diagnosticRoot 'matlab-pref')
        }
        quarantine_roots=@((Join-Path $Root 'quarantine'));thread_source=$threadSource
    }
    $predicateNames=@('diagnostic_lock_schema','diagnostic_authorization_scope',
        'producer_entrypoint_not_authorized','matlab_path_length','matlab_path_prefix',
        'matlab_release','matlab_update','matlab_version','matlab_computer',
        'matlab_executable_sha256','matlab_blas','matlab_lapack',
        'binary_initial_resolved','binary_initial_readable','binary_initial_sha256',
        'binary_AMOR_resolved','binary_AMOR_readable','binary_AMOR_sha256',
        'binary_AT1_HISTORY_FATIGUE_resolved','binary_AT1_HISTORY_FATIGUE_readable',
        'binary_AT1_HISTORY_FATIGUE_sha256','binary_cholmod2_resolved',
        'binary_cholmod2_readable','binary_cholmod2_sha256')
    $limit=if($Status -ceq 'FAIL'){10}else{23}
    $predicates=@(for($i=0;$i -le $limit;$i++){
        [ordered]@{ordinal=$i+1;name=$predicateNames[$i];expected='expected'
            measured_raw='measured';measured_normalized='measured'
            pass=($Status -ceq 'PASS' -or $i -lt $limit);measured_at_utc='2026-08-05T10:00:00.000Z'}
    })
    $firstFailed=$null
    $matlabException=@{}
    if($Status -ceq 'FAIL'){
        $firstFailed=$predicateNames[$limit]
        $matlabException=[ordered]@{identifier='toyRoadD1:PredicateFailed'
            message='fixture failure';stack=@();extended_report='fixture failure'}
    }
    $receipt = [ordered]@{
        schema_version='toy_road_runtime_diagnostic_v1';status=$Status
        authorization_scope='diagnostic_only_non_authorizing'
        producer_entrypoint_authorized=$false;predicates=$predicates
        first_failed_predicate=$firstFailed
        producer_invocation_count=0;fem_cycle_count=0;completed_predicate_count=$predicates.Count
        matlab_exception=$matlabException
    }
    $sourceIdentity = [ordered]@{
        authorization_scope='test_only_non_authorizing'
        source_commit=$sourceLock.source_commit
        source_clean=$true
    }
    $sourcePath=Join-Path $Root 'source-lock.json'
    $relocationPath=Join-Path $Root 'relocation.json'
    $lockPath=Join-Path $Root 'input-lock.json'
    $transformPath=Join-Path $Root 'input-transform.json'
    $receiptPath=Join-Path $Root 'measurement.json'
    $identityPath=Join-Path $Root 'source-identity.json'
    Write-Utf8Json $sourcePath $sourceLock
    Write-Utf8Json $relocationPath $relocation
    & $Python $Protocol --derive-lock $sourcePath $relocationPath $lockPath $transformPath | Out-Null
    if($LASTEXITCODE -ne 0){throw 'Fixture lock derivation failed.'}
    Write-Utf8Json $receiptPath $receipt
    Write-Utf8Json $identityPath $sourceIdentity
    return [ordered]@{source=$sourcePath;lock=$lockPath;transform=$transformPath;measurement=$receiptPath;identity=$identityPath;evidence=$diagnosticRoot}
}

function Invoke-Fixture([int]$AdapterExitCode=0,[string]$Status='PASS') {
    $root=Join-Path $env:TEMP ('toy-road-d1-launcher-'+[Guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($root) | Out-Null
    $fixture=New-Fixture $root $Status
    $fakeMatlab=Join-Path $root 'matlab.exe'
    [IO.File]::WriteAllBytes($fakeMatlab,[byte[]](1,2,3))
    $matlabSha=(Get-FileHash $fakeMatlab -Algorithm SHA256).Hash.ToLowerInvariant()
    $arguments=@('-NoProfile','-ExecutionPolicy','Bypass','-File',$Launcher,
        '-SourceRoot',$RepoRoot,'-ExpectedSourceCommit','eeda43d9faef01622731e877c5048a78f3c5003a',
        '-DiagnosticLockPath',$fixture.lock,'-TransformationPath',$fixture.transform,
        '-SourceExecutionLockPath',$fixture.source,
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

$fail=Invoke-Fixture 17 'FAIL'
try {
    if($fail.exit -ne 0){throw "Terminal FAIL fixture did not complete: $($fail.output)"}
    $files=@(Get-ChildItem $fail.evidence -File)
    if($files.Count -ne 10){throw "Terminal FAIL package has $($files.Count) files."}
    $terminal=Get-Content (Join-Path $fail.evidence 'D1_TERMINAL.json') -Raw|ConvertFrom-Json
    if($terminal.diagnostic_result -cne 'FAIL' -or $terminal.child_exit_code -ne 17){
        throw 'Terminal FAIL package lost its diagnostic result or child exit code.'
    }
    if(Test-Path (Join-Path $fail.evidence 'D1_LAUNCHER_RECOVERY.json')){
        throw 'Terminal FAIL package was incorrectly classified as a crash.'
    }
} finally {Remove-Item $fail.root -Recurse -Force -ErrorAction SilentlyContinue}

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
