$ErrorActionPreference = 'Stop'

$TestDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HandoffDir = Split-Path -Parent $TestDir
$RepoRoot = (Resolve-Path (Join-Path $HandoffDir '..\..')).Path
$Launcher = Join-Path $HandoffDir 'launch_toy_road_family_case.ps1'
$Python = 'C:\Users\xw436\AppData\Local\Programs\Python\Python312\python.exe'
$Roles = @(
    'P0_parent',
    'P0R_parent_repeat',
    'T1_initial_defect',
    'T2_material_state',
    'T3_loading_history'
)
$ApprovedInitial = 'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db'
$LegacyInitial = '589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340'
$GripCommit = 'fc19b6017add6b075dd24fa9525a5e8daa99090c'
$Q1GripCommit = '355d4c83fefc2db88c32031a2dd2623b3de85c89'
$SourceCommit = 'a' * 40
$RuntimeLockSha = 'a53a1431b6f7a1b56f44f3faccb410ba11a4b9a6ef4f1a16b30258936bd0f8d7'
$summaryText = & $Python (Join-Path $HandoffDir 'toy_road_protocol.py') --contract-summary
if ($LASTEXITCODE -ne 0) { throw 'Cannot load canonical Task 6 contracts.' }
$ContractSummary = [string]@($summaryText)[-1] | ConvertFrom-Json
$FamilySha = [string]$ContractSummary.family_contract_sha256
$CaseHashes = [ordered]@{}
$MeshHashes = [ordered]@{}
foreach ($role in $Roles) {
    $CaseHashes[$role] = [string]$ContractSummary.cases.$role.case_physics_contract_sha256
    $MeshHashes[$role] = [string]$ContractSummary.cases.$role.mesh_sha256
}

function New-TestRoots([string]$Name) {
    $base = Join-Path $env:TEMP ("toy-road-task6-$Name-" + [Guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($base) | Out-Null
    $evidence = Join-Path $base 'evidence'
    [IO.Directory]::CreateDirectory($evidence) | Out-Null
    return [ordered]@{
        base = $base
        output = Join-Path $base 'output'
        work = Join-Path $base 'work'
        temp = Join-Path $base 'temp'
        tmp = Join-Path $base 'tmp'
        pref = Join-Path $base 'pref'
        cache = Join-Path $base 'cache'
        receipt = Join-Path $base 'receipt.json'
        lock = Join-Path $base 'execution-lock.json'
        evidence = $evidence
        measurement_fixture = Join-Path $base 'runtime-measurement-fixture.json'
        invocation_record = Join-Path $base 'test-adapter-invocation.json'
    }
}

function New-TerminalEvidence([string]$Role) {
    return [ordered]@{
        case_id = $Role
        authorization_scope = 'production_authorized'
        terminal_validation_status = 'PASS'
        c5_status = 'PASS'
        runtime_lock_sha256 = $RuntimeLockSha
        family_contract_sha256 = $FamilySha
        case_physics_contract_sha256 = $CaseHashes[$Role]
        terminal_manifest_sha256 = '2' * 64
        c5_receipt_sha256 = '3' * 64
        package_snapshot_sha256 = '4' * 64
        authentication_receipt_path = 'fixture-only-terminal-auth'
        authentication_receipt_sha256 = '5' * 64
    }
}

function New-Fixture([string]$Role) {
    $predecessors = @()
    $repeatability = $null
    switch ($Role) {
        'P0_parent' { }
        'P0R_parent_repeat' { $predecessors = @(New-TerminalEvidence 'P0_parent') }
        'T1_initial_defect' {
            $repeatability = [ordered]@{
                authorization_scope = 'production_authorized'
                status = 'PASS'
                runtime_lock_sha256 = $RuntimeLockSha
                family_contract_sha256 = $FamilySha
                p0_manifest_sha256 = '4' * 64
                p0r_manifest_sha256 = '5' * 64
                p0_c5_receipt_sha256 = '6' * 64
                p0r_c5_receipt_sha256 = '7' * 64
                p0_package_snapshot_sha256 = '8' * 64
                p0r_package_snapshot_sha256 = '9' * 64
                authentication_receipt_path = 'fixture-only-repeatability-auth'
                authentication_receipt_sha256 = 'a' * 64
            }
        }
        'T2_material_state' { $predecessors = @(New-TerminalEvidence 'T1_initial_defect') }
        'T3_loading_history' {
            $predecessors = @(
                (New-TerminalEvidence 'T1_initial_defect'),
                (New-TerminalEvidence 'T2_material_state')
            )
        }
    }
    return [ordered]@{
        authorization_scope = 'test_only_non_authorizing'
        source = [ordered]@{ commit = $SourceCommit; clean = $true }
        griphfith = [ordered]@{ commit = $GripCommit; clean = $true }
        runtime = [ordered]@{
            runtime_lock_sha256 = $RuntimeLockSha
            initial_sha256 = $ApprovedInitial
            binaries = [ordered]@{
                initial = $ApprovedInitial
                AMOR = 'e200dbb757172c3927bcd72f4f093c5a6b17dab52fcbd72505e34e0434924b9a'
                AT1_HISTORY_FATIGUE = '3d9989b7fcc89ea36f1de196cad86cfcef3406c7365ac82bd6c58280a0cc9298'
                cholmod2 = '86a2f15543eda1f7223a1733d935d37e9e2f4f2c2d8db3c4adc2c0f675c27329'
            }
            compiler = [ordered]@{
                fortran = 'Intel(R) Fortran Compiler 2025.3.2 Build 20260112 (ifx.exe)'
                cpp = 'Microsoft Visual Studio 2022 Community; MSVC 14.44.35207'
                linker = 'Microsoft Visual Studio 2022 link.exe'
                mex_configuration = 'Intel oneAPI 2025 for Fortran with Microsoft Visual Studio 2022'
                build_command_sha256 = '201eabd998d4d0bc7ee14b6279c4a358c0ef80af90240134883f0a2cb9a5bff0'
                build_log_sha256 = 'cf97950c53a2bd109b66169e8b9143784336bc23c5f2234fd091bfafb325fd5b'
                toolchain_sha256 = 'befe373350916d37dbe73df9decf2542c647a8adb09543c515751cfbb3e8fbe0'
                source_hashes_sha256 = '4951e9bb43515c036ec2f100b8c94627d48d88ae5b515d49c3d9bcec09bb7481'
            }
            matlab = [ordered]@{
                release = 'R2025b Update 5'
                version = '25.2.0.3177638'
                executable_sha256 = '322158960d70ea723d7bf6e5bb06f6b058b1489a85624d6c6a2be83be4944c2d'
                path_sha256 = 'aa75710dedad219c037841b5ec40802b0576f4ca1e9cb314285d9ad10ad114ec'
                blas = 'Intel(R) oneAPI Math Kernel Library Version 2024.1-Product Build 20240215 for Intel(R) 64 architecture applications (CNR branch auto)'
                lapack = 'Intel(R) oneAPI Math Kernel Library Version 2024.1-Product Build 20240215 for Intel(R) 64 architecture applications (CNR branch auto) supporting Linear Algebra PACKage (LAPACK 3.11.0)'
            }
            machine = [ordered]@{
                computer_name = $env:COMPUTERNAME
                cpu_name = 'AMD Ryzen 5 5600X 6-Core Processor'
                cpu_id = '178BFBFF00A20F10'
                windows_build = '22631'
                architecture = '64-bit'
            }
            threads = [ordered]@{
                OMP_NUM_THREADS = '1'
                MKL_NUM_THREADS = '1'
                OPENBLAS_NUM_THREADS = '1'
                MKL_DYNAMIC = 'FALSE'
            }
            h5py_version = '3.16.0'
            java_hard_link_supported = $true
            native_hard_link_supported = $true
            mesh_sha256_semantics = 'sha256_matlab_column_major_float64_coords_then_int64_connectivity_v1'
        }
        q1 = [ordered]@{
            present = $true
            schema_version = 'rebuilt_initial_mex_q1_receipt_v1'
            passed = $true
            source_clean = $true
            source_commit = $Q1GripCommit
            runtime_initial_sha256 = $ApprovedInitial
            runtime_lock_sha256 = 'a53a1431b6f7a1b56f44f3faccb410ba11a4b9a6ef4f1a16b30258936bd0f8d7'
            receipt_sha256 = '8fd051e4bf806c9a593297b95377a1fcc434f2b16cba5f67cc9f597b2e54fc36'
            result_sha256 = '21b769af9e7c78b3d3bc45a8fc85671ccf455004c74cddfb29a6beb56499d96a'
        }
        contracts = [ordered]@{
            family_contract_sha256 = $FamilySha
            case_physics_contract_sha256 = $CaseHashes[$Role]
            mesh_sha256 = $MeshHashes[$Role]
            declared_mesh_sha256 = $MeshHashes[$Role]
        }
        process_inventory = @()
        family_failed = $false
        predecessors = $predecessors
        repeatability_evidence = $repeatability
        final_process_inventory = @()
    }
}

function New-MeasurementFixture([object]$Fixture) {
    return [ordered]@{
        matlab = [ordered]@{
            release = 'R2025b'
            update = 'Update 5'
            version = [string]$Fixture.runtime.matlab.version
            computer = 'PCWIN64'
            executable_sha256 = [string]$Fixture.runtime.matlab.executable_sha256
            blas = [string]$Fixture.runtime.matlab.blas
            lapack = [string]$Fixture.runtime.matlab.lapack
        }
        binary_sha256 = $Fixture.runtime.binaries
    }
}

function Write-Fixture([string]$Path, [object]$Fixture) {
    $json = $Fixture | ConvertTo-Json -Depth 20
    [IO.File]::WriteAllText($Path,$json,(New-Object Text.UTF8Encoding($false)))
}

function Invoke-Launcher(
    [string]$Role,
    [object]$Fixture,
    [switch]$Preflight,
    [scriptblock]$ArrangeRoots,
    [string]$ResumeFrom = '',
    [int]$AdapterDelayMilliseconds = 0,
    [scriptblock]$MutateMeasurement,
    [string]$PythonOverride = $Python
) {
    $roots = New-TestRoots $Role
    try {
        if ($null -ne $ArrangeRoots) { & $ArrangeRoots $roots }
        $fixturePath = Join-Path $roots.base 'fixture.json'
        Write-Fixture $fixturePath $Fixture
        $measurementFixture = New-MeasurementFixture $Fixture
        if ($null -ne $MutateMeasurement) { & $MutateMeasurement $measurementFixture }
        Write-Fixture $roots.measurement_fixture $measurementFixture
        $arguments = @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $Launcher,
            '-Role', $Role,
            '-SourceRoot', $RepoRoot,
            '-GripfithRoot', $RepoRoot,
            '-QualificationRoot', $RepoRoot,
            '-InputAssetsRoot', $RepoRoot,
            '-EvidenceRoot', $roots.evidence,
            '-OutputRoot', $roots.output,
            '-WorkRoot', $roots.work,
            '-TempRoot', $roots.temp,
            '-TmpRoot', $roots.tmp,
            '-PrefRoot', $roots.pref,
            '-CacheRoot', $roots.cache,
            '-ExpectedSourceCommit', $SourceCommit,
            '-ReceiptPath', $roots.receipt,
            '-ExecutionLockPath', $roots.lock,
            '-PythonExecutable', $PythonOverride,
            '-TestFixturePath', $fixturePath,
            '-TestMeasurementFixturePath', $roots.measurement_fixture,
            '-TestInvocationRecordPath', $roots.invocation_record,
            '-TestAdapterDelayMilliseconds', $AdapterDelayMilliseconds
        )
        if ($Preflight) { $arguments += '-PreflightOnly' }
        if (-not [string]::IsNullOrEmpty($ResumeFrom)) {
            $arguments += @('-ResumeFrom', $ResumeFrom)
        }
        $priorPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $output = & powershell @arguments 2>&1 | Out-String
            $exit = $LASTEXITCODE
        } finally {
            $ErrorActionPreference = $priorPreference
        }
        $receipt = $null
        if (Test-Path -LiteralPath $roots.receipt -PathType Leaf) {
            $receipt = Get-Content -LiteralPath $roots.receipt -Raw | ConvertFrom-Json
        }
        $lockSha256 = $null
        $lock = $null
        if (Test-Path -LiteralPath $roots.lock -PathType Leaf) {
            $lockSha256 = (Get-FileHash -LiteralPath $roots.lock -Algorithm SHA256).Hash.ToLowerInvariant()
            $lock = Get-Content -LiteralPath $roots.lock -Raw | ConvertFrom-Json
        }
        $invocation = $null
        if (Test-Path -LiteralPath $roots.invocation_record -PathType Leaf) {
            $invocation = Get-Content -LiteralPath $roots.invocation_record -Raw | ConvertFrom-Json
        }
        return [ordered]@{
            exit = $exit
            output = $output
            receipt = $receipt
            invocation = $invocation
            lock_exists = Test-Path -LiteralPath $roots.lock
            lock_sha256 = $lockSha256
            lock = $lock
        }
    } finally {
        Remove-Item -LiteralPath $roots.base -Recurse -Force -ErrorAction SilentlyContinue
    }
}

function Assert-Rejected([object]$Result, [string]$Pattern) {
    if ($Result.exit -eq 0 -or $Result.output -notmatch $Pattern) {
        throw "Expected launcher rejection matching '$Pattern'. Output: $($Result.output)"
    }
    if ($null -ne $Result.invocation) { throw 'A rejected fixture reached the process-launch double.' }
}

if (-not (Test-Path -LiteralPath $Launcher -PathType Leaf)) {
    throw 'Task 6 launcher is missing.'
}

$preflightLockHashes = @()
$preflightCaseHashes = [ordered]@{}
foreach ($role in $Roles) {
    $result = Invoke-Launcher $role (New-Fixture $role) -Preflight
    if ($result.exit -ne 0) { throw "Preflight failed for $role`: $($result.output)" }
    if ($null -eq $result.receipt -or
            [string]$result.receipt.authorization_scope -cne 'preflight_only_non_authorizing' -or
            [string]$result.receipt.dynamic_chain_status -cne 'not_evaluated_no_execution' -or
            [string]$result.receipt.status -cne 'PASS') {
        throw "Preflight receipt fields are invalid for $role."
    }
    if ($null -ne $result.invocation) { throw "Preflight invoked the process adapter for $role." }
    if (-not $result.lock_exists -or
            [string]$result.receipt.execution_input_lock_sha256 -cne [string]$result.lock_sha256) {
        throw "Preflight execution lock is absent or not self-consistent for $role."
    }
    if ([string]$result.lock.authorization_scope -cne
            [string]$result.receipt.authorization_scope) {
        throw "Execution lock does not carry its final authorization scope for $role."
    }
    $rootNames = @($result.lock.writable_roots.PSObject.Properties.Name)
    if ($rootNames.Count -ne 7 -or
            $rootNames -cnotcontains 'matlab_startup_pref' -or
            [string]$result.lock.writable_roots.matlab_startup_pref -ceq
                [string]$result.lock.writable_roots.pref) {
        throw "Preflight execution lock does not isolate MATLAB startup preferences for $role."
    }
    $preflightLockHashes += [string]$result.lock_sha256
    $preflightCaseHashes[$role] = [string]$result.receipt.case_physics_contract_sha256
}

$copiedLauncherRoot = Join-Path $env:TEMP ('toy-road-task6-copied-launcher-' + [Guid]::NewGuid().ToString('N'))
try {
    [IO.Directory]::CreateDirectory($copiedLauncherRoot) | Out-Null
    $copiedLauncher = Join-Path $copiedLauncherRoot 'launch_toy_road_family_case.ps1'
    Copy-Item -LiteralPath $Launcher -Destination $copiedLauncher
    $originalLauncher = $Launcher
    $Launcher = $copiedLauncher
    Assert-Rejected (
        Invoke-Launcher 'P0_parent' (New-Fixture 'P0_parent') -Preflight
    ) 'canonical sealed handoff|SourceRoot.*handoff|executed bytes'
} finally {
    $Launcher = $originalLauncher
    Remove-Item -LiteralPath $copiedLauncherRoot -Recurse -Force -ErrorAction SilentlyContinue
}
if (($preflightLockHashes | Select-Object -Unique).Count -ne 5) {
    throw 'The five preflight execution input locks must be launch-unique.'
}
if ($preflightCaseHashes.P0_parent -cne $preflightCaseHashes.P0R_parent_repeat) {
    throw 'P0/P0R preflight case-physics digests must match.'
}

Assert-Rejected (
    Invoke-Launcher 'P0_parent' (New-Fixture 'P0_parent') -Preflight `
        -PythonOverride 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe'
) 'Python executable|fixed Task 6 protocol runtime'

$staticCases = @(
    @{ name = 'legacy'; pattern = 'legacy|crashing'; mutate = { param($f) $f.runtime.initial_sha256 = $LegacyInitial; $f.runtime.binaries.initial = $LegacyInitial } },
    @{ name = 'unknown'; pattern = 'unknown|approved'; mutate = { param($f) $f.runtime.initial_sha256 = '0' * 64; $f.runtime.binaries.initial = '0' * 64 } },
    @{ name = 'missing-q1'; pattern = 'Q1'; mutate = { param($f) $f.q1.present = $false } },
    @{ name = 'missing-source'; pattern = 'source.*provenance|source.*missing'; mutate = { param($f) $f.source.Remove('commit') } },
    @{ name = 'missing-compiler'; pattern = 'compiler|provenance'; mutate = { param($f) $f.runtime.compiler.Remove('fortran') } },
    @{ name = 'missing-runtime'; pattern = 'runtime binary|provenance'; mutate = { param($f) $f.runtime.binaries.Remove('AMOR') } },
    @{ name = 'missing-machine'; pattern = 'machine|CPU|provenance'; mutate = { param($f) $f.runtime.machine.Remove('cpu_id') } },
    @{ name = 'dirty-source'; pattern = 'clean|dirty'; mutate = { param($f) $f.source.clean = $false } },
    @{ name = 'wrong-source'; pattern = 'source commit|sealed'; mutate = { param($f) $f.source.commit = '0' * 40 } },
    @{ name = 'dirty-griphfith'; pattern = 'GRIPHFiTH.*clean|dirty'; mutate = { param($f) $f.griphfith.clean = $false } },
    @{ name = 'wrong-griphfith'; pattern = 'GRIPHFiTH.*commit'; mutate = { param($f) $f.griphfith.commit = '0' * 40 } },
    @{ name = 'wrong-mesh'; pattern = 'mesh'; mutate = { param($f) $f.contracts.mesh_sha256 = '0' * 64 } },
    @{ name = 'running'; pattern = 'running MATLAB|FEM'; mutate = { param($f) $f.process_inventory = @([ordered]@{ name='MATLAB.exe'; process_id=42; command_line='matlab -batch solve' }) } },
    @{ name = 'h5py'; pattern = 'h5py'; mutate = { param($f) $f.runtime.h5py_version = '3.16.1' } },
    @{ name = 'java-hardlink'; pattern = 'Java.*hard.link'; mutate = { param($f) $f.runtime.java_hard_link_supported = $false } },
    @{ name = 'runtime-hardlink'; pattern = 'hard.link'; mutate = { param($f) $f.runtime.native_hard_link_supported = $false } }
)
foreach ($case in $staticCases) {
    $fixture = New-Fixture 'P0_parent'
    & $case.mutate $fixture
    Assert-Rejected (Invoke-Launcher 'P0_parent' $fixture -Preflight) $case.pattern
}

$shared = Invoke-Launcher 'P0_parent' (New-Fixture 'P0_parent') -Preflight -ArrangeRoots {
    param($roots) $roots.work = $roots.temp
}
Assert-Rejected $shared 'distinct|shared|nested'

$nested = Invoke-Launcher 'P0_parent' (New-Fixture 'P0_parent') -Preflight -ArrangeRoots {
    param($roots) $roots.temp = Join-Path $roots.work 'nested'
}
Assert-Rejected $nested 'distinct|shared|nested'

$nonempty = Invoke-Launcher 'P0_parent' (New-Fixture 'P0_parent') -Preflight -ArrangeRoots {
    param($roots) [IO.Directory]::CreateDirectory($roots.output) | Out-Null; Set-Content (Join-Path $roots.output 'sentinel') 'x'
}
Assert-Rejected $nonempty 'output root|absent|non-empty|exists'

Assert-Rejected (
    Invoke-Launcher 'P0_parent' (New-Fixture 'P0_parent') -Preflight -ResumeFrom 'checkpoint.mat'
) 'resume|checkpoint'

$dynamicSkipped = New-Fixture 'T3_loading_history'
$dynamicSkipped.family_failed = $true
$dynamicSkipped.predecessors = @()
$dynamicSkipped.repeatability_evidence = $null
$dynamicSkippedResult = Invoke-Launcher 'T3_loading_history' $dynamicSkipped -Preflight
if ($dynamicSkippedResult.exit -ne 0 -or
        [string]$dynamicSkippedResult.receipt.dynamic_chain_status -cne 'not_evaluated_no_execution') {
    throw 'Preflight incorrectly evaluated dynamic predecessor evidence.'
}

foreach ($role in $Roles) {
    $result = Invoke-Launcher $role (New-Fixture $role)
    if ($result.exit -ne 0) { throw "Controlled production-chain check failed for $role`: $($result.output)" }
    if ($null -eq $result.receipt -or
            [string]$result.receipt.authorization_scope -cne 'test_only_non_authorizing' -or
            [string]$result.receipt.dynamic_chain_status -cne 'passed_test_adapter_non_authorizing' -or
            $null -eq $result.invocation -or
            [int]$result.invocation.invocation_count -ne 1 -or
            $result.invocation.producer_entrypoint_called -ne $false) {
        throw "Controlled production-chain receipt is invalid for $role."
    }
}

$mutatedMeasurement = Invoke-Launcher 'P0_parent' (New-Fixture 'P0_parent') `
    -MutateMeasurement { param($measurement) $measurement.matlab.blas = 'mutated BLAS' }
Assert-Rejected $mutatedMeasurement 'measurement fixture|differs.*lock|blas'

$finalRace = New-Fixture 'P0_parent'
$finalRace.final_process_inventory = @([ordered]@{
    name = 'MATLAB.exe'; process_id = 43; command_line = 'matlab -batch solve'
})
Assert-Rejected (Invoke-Launcher 'P0_parent' $finalRace) 'running MATLAB|FEM'

$finalDirtySource = New-Fixture 'P0_parent'
$finalDirtySource | Add-Member -NotePropertyName final_source_git -NotePropertyValue `
    ([ordered]@{ commit = $SourceCommit; clean = $false })
Assert-Rejected (Invoke-Launcher 'P0_parent' $finalDirtySource) `
    'Git HEAD|clean status|source identity'

$finalReplacedSource = New-Fixture 'P0_parent'
$finalReplacedSource | Add-Member -NotePropertyName final_source_git -NotePropertyValue `
    ([ordered]@{ commit = '0' * 40; clean = $true })
Assert-Rejected (Invoke-Launcher 'P0_parent' $finalReplacedSource) `
    'Git HEAD|clean status|source identity'

$outOfOrder = New-Fixture 'T2_material_state'
$outOfOrder.predecessors = @()
Assert-Rejected (Invoke-Launcher 'T2_material_state' $outOfOrder) 'predecessor|order|T1'

$failed = New-Fixture 'T2_material_state'
$failed.family_failed = $true
Assert-Rejected (Invoke-Launcher 'T2_material_state' $failed) 'previous family|failed'

$missingC5 = New-Fixture 'T2_material_state'
$missingC5.predecessors[0].c5_status = 'MISSING'
Assert-Rejected (Invoke-Launcher 'T2_material_state' $missingC5) 'c5|C5'

$runtimeReplacement = New-Fixture 'T3_loading_history'
$runtimeReplacement.predecessors[1].runtime_lock_sha256 = '0' * 64
Assert-Rejected (Invoke-Launcher 'T3_loading_history' $runtimeReplacement) 'runtime'

$malformedRepeatabilityBinding = New-Fixture 'T1_initial_defect'
$malformedRepeatabilityBinding.repeatability_evidence.p0_c5_receipt_sha256 = 'not-a-sha256'
Assert-Rejected (
    Invoke-Launcher 'T1_initial_defect' $malformedRepeatabilityBinding
) 'repeatability.*hash|malformed'

$preflightAsPredecessor = New-Fixture 'T2_material_state'
$preflightAsPredecessor.predecessors[0].authorization_scope = 'preflight_only_non_authorizing'
Assert-Rejected (Invoke-Launcher 'T2_material_state' $preflightAsPredecessor) 'non-authorizing|preflight|scope'

$testAsPredecessor = New-Fixture 'T2_material_state'
$testAsPredecessor.predecessors[0].authorization_scope = 'test_only_non_authorizing'
Assert-Rejected (Invoke-Launcher 'T2_material_state' $testAsPredecessor) 'non-authorizing|test|scope'

$currentC5Absent = New-Fixture 'T2_material_state'
if ($null -ne $currentC5Absent.PSObject.Properties['current_c5_receipt']) {
    $currentC5Absent.PSObject.Properties.Remove('current_c5_receipt')
}
$currentResult = Invoke-Launcher 'T2_material_state' $currentC5Absent
if ($currentResult.exit -ne 0) {
    throw "Launcher incorrectly required current-case c5 evidence: $($currentResult.output)"
}

$mutexBase = Join-Path $env:TEMP ('toy-road-task6-mutex-' + [Guid]::NewGuid().ToString('N'))
$firstProcess = $null
try {
    [IO.Directory]::CreateDirectory($mutexBase) | Out-Null
    $runs = @()
    foreach ($ordinal in 1,2) {
        $runRoot = Join-Path $mutexBase "run-$ordinal"
        [IO.Directory]::CreateDirectory($runRoot) | Out-Null
        $evidenceRoot = Join-Path $runRoot 'evidence'
        [IO.Directory]::CreateDirectory($evidenceRoot) | Out-Null
        $fixture = New-Fixture 'P0_parent'
        $fixturePath = Join-Path $runRoot 'fixture.json'
        $measurementPath = Join-Path $runRoot 'measurement.json'
        $invocationPath = Join-Path $runRoot 'invocation.json'
        Write-Fixture $fixturePath $fixture
        Write-Fixture $measurementPath (New-MeasurementFixture $fixture)
        $runs += [ordered]@{
            root = $runRoot
            fixture = $fixturePath
            measurement = $measurementPath
            invocation = $invocationPath
            receipt = Join-Path $runRoot 'receipt.json'
            lock = Join-Path $runRoot 'lock.json'
            stdout = Join-Path $runRoot 'stdout.txt'
            stderr = Join-Path $runRoot 'stderr.txt'
            output = Join-Path $runRoot 'output'
            work = Join-Path $runRoot 'work'
            temp = Join-Path $runRoot 'temp'
            tmp = Join-Path $runRoot 'tmp'
            pref = Join-Path $runRoot 'pref'
            cache = Join-Path $runRoot 'cache'
            evidence = $evidenceRoot
        }
    }
    function Get-MutexLauncherArguments([object]$Run, [int]$Delay) {
        return @(
            '-NoProfile','-ExecutionPolicy','Bypass','-File',$Launcher,
            '-Role','P0_parent','-SourceRoot',$RepoRoot,'-GripfithRoot',$RepoRoot,
            '-QualificationRoot',$RepoRoot,'-InputAssetsRoot',$RepoRoot,
            '-EvidenceRoot',$Run.evidence,'-OutputRoot',$Run.output,
            '-WorkRoot',$Run.work,'-TempRoot',$Run.temp,'-TmpRoot',$Run.tmp,
            '-PrefRoot',$Run.pref,'-CacheRoot',$Run.cache,
            '-ExpectedSourceCommit',$SourceCommit,'-ReceiptPath',$Run.receipt,
            '-ExecutionLockPath',$Run.lock,'-PythonExecutable',$Python,
            '-TestFixturePath',$Run.fixture,
            '-TestMeasurementFixturePath',$Run.measurement,
            '-TestInvocationRecordPath',$Run.invocation,
            '-TestAdapterDelayMilliseconds',$Delay
        )
    }
    $firstProcess = Start-Process -FilePath 'powershell.exe' -WindowStyle Hidden `
        -ArgumentList (Get-MutexLauncherArguments $runs[0] 8000) `
        -RedirectStandardOutput $runs[0].stdout -RedirectStandardError $runs[0].stderr `
        -PassThru
    $mutexPath = Join-Path $runs[0].evidence '.toy-road-family-execution.mutex'
    $deadline = (Get-Date).AddSeconds(30)
    while (-not (Test-Path -LiteralPath $mutexPath) -and
            -not $firstProcess.HasExited -and (Get-Date) -lt $deadline) {
        Start-Sleep -Milliseconds 100
    }
    if (-not (Test-Path -LiteralPath $mutexPath)) {
        throw 'First launcher did not acquire the family-wide mutex.'
    }
    $priorPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $secondOutput = & powershell @(Get-MutexLauncherArguments $runs[1] 0) 2>&1 | Out-String
        $secondExit = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $priorPreference
    }
    if ($secondExit -eq 0 -or $secondOutput -notmatch 'mutex|Another toy-road family launcher') {
        throw "Second launcher did not fail closed on mutex contention: $secondOutput"
    }
    if (Test-Path -LiteralPath $runs[1].invocation) {
        throw 'Contending launcher reached the sealed process adapter.'
    }
    if (-not $firstProcess.WaitForExit(60000)) {
        $firstError = if (Test-Path $runs[0].stderr) {
            Get-Content -LiteralPath $runs[0].stderr -Raw
        } else { '' }
        $firstOutput = if (Test-Path $runs[0].stdout) {
            Get-Content -LiteralPath $runs[0].stdout -Raw
        } else { '' }
        throw "First mutex-holder launcher failed or timed out. stdout=$firstOutput stderr=$firstError"
    }
    $firstInvocation = Get-Content -LiteralPath $runs[0].invocation -Raw | ConvertFrom-Json
    $firstReceipt = Get-Content -LiteralPath $runs[0].receipt -Raw | ConvertFrom-Json
    $firstError = Get-Content -LiteralPath $runs[0].stderr -Raw
    if ([int]$firstInvocation.invocation_count -ne 1 -or
            [string]$firstReceipt.status -cne 'PASS' -or
            -not [string]::IsNullOrWhiteSpace($firstError)) {
        throw 'Mutex-holder did not make exactly one sealed adapter invocation.'
    }
} finally {
    if ($null -ne $firstProcess -and -not $firstProcess.HasExited) {
        Stop-Process -Id $firstProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Remove-Item -LiteralPath $mutexBase -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Output 'toyRoadLauncherTest: PASS'
