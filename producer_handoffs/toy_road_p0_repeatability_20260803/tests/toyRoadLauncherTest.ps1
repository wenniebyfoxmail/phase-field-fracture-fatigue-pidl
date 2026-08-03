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
$GripCommit = '355d4c83fefc2db88c32031a2dd2623b3de85c89'
$SourceCommit = 'a' * 40
$RuntimeLockSha = 'a53a1431b6f7a1b56f44f3faccb410ba11a4b9a6ef4f1a16b30258936bd0f8d7'
$FamilySha = '1af62deb41e60cd88853201ff9ee2d4a240975c8bf722453c1268b2c799a4b4d'
$CaseHashes = [ordered]@{
    P0_parent = 'b114c6f0ea46d5320d47f2df745a3480f6aa541874698a370e33cf6884249820'
    P0R_parent_repeat = 'b114c6f0ea46d5320d47f2df745a3480f6aa541874698a370e33cf6884249820'
    T1_initial_defect = '8f13d4b3b8d747b92190925cb28c97713795f398129a3218503afba148004cb4'
    T2_material_state = '489e880dca0a4afba9002a8d91011a35712dadf42a2b1cd59a274345c1dc7fb9'
    T3_loading_history = '543b43bf5142e147e9d26469ba6d30faeed76db58806f3cb66fb5dcd51bfc923'
}
$MeshHashes = [ordered]@{
    P0_parent = 'd9ad5545e42e4d700600a69f18b625f90456253295095fdf644c55b7968b068b'
    P0R_parent_repeat = 'd9ad5545e42e4d700600a69f18b625f90456253295095fdf644c55b7968b068b'
    T1_initial_defect = '1db2b1074fc04b1bd8302f9810ea6f3a72a44485819b215eca8ccea85038a1d4'
    T2_material_state = 'd9ad5545e42e4d700600a69f18b625f90456253295095fdf644c55b7968b068b'
    T3_loading_history = 'd9ad5545e42e4d700600a69f18b625f90456253295095fdf644c55b7968b068b'
}

function New-TestRoots([string]$Name) {
    $base = Join-Path $env:TEMP ("toy-road-task6-$Name-" + [Guid]::NewGuid().ToString('N'))
    [IO.Directory]::CreateDirectory($base) | Out-Null
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
        launch_marker = Join-Path $base 'matlab-launch-marker.txt'
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
                AMOR = '64abee69f2c441730dc2efa4047ac45ab1d1b40e20c4822ed6e992adcd6b19e7'
                AT1_HISTORY_FATIGUE = '53e8fd0b229817b7c14c52a5b6afaa957692f475057b79b9a9a10195ccb92e60'
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
            source_commit = $GripCommit
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
        launch_marker_path = ''
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
    [string]$ResumeFrom = ''
) {
    $roots = New-TestRoots $Role
    try {
        if ($null -ne $ArrangeRoots) { & $ArrangeRoots $roots }
        $Fixture.launch_marker_path = $roots.launch_marker
        $fixturePath = Join-Path $roots.base 'fixture.json'
        Write-Fixture $fixturePath $Fixture
        $arguments = @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $Launcher,
            '-Role', $Role,
            '-SourceRoot', $RepoRoot,
            '-GripfithRoot', $RepoRoot,
            '-QualificationRoot', $RepoRoot,
            '-InputAssetsRoot', $RepoRoot,
            '-EvidenceRoot', $RepoRoot,
            '-OutputRoot', $roots.output,
            '-WorkRoot', $roots.work,
            '-TempRoot', $roots.temp,
            '-TmpRoot', $roots.tmp,
            '-PrefRoot', $roots.pref,
            '-CacheRoot', $roots.cache,
            '-ExpectedSourceCommit', $SourceCommit,
            '-ReceiptPath', $roots.receipt,
            '-ExecutionLockPath', $roots.lock,
            '-PythonExecutable', $Python,
            '-TestFixturePath', $fixturePath
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
        return [ordered]@{
            exit = $exit
            output = $output
            receipt = $receipt
            marker_exists = Test-Path -LiteralPath $roots.launch_marker
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
    if ($Result.marker_exists) { throw 'A rejected fixture reached the process-launch double.' }
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
    if ($result.marker_exists) { throw "Preflight invoked MATLAB for $role." }
    if (-not $result.lock_exists -or
            [string]$result.receipt.execution_input_lock_sha256 -cne [string]$result.lock_sha256) {
        throw "Preflight execution lock is absent or not self-consistent for $role."
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
if (($preflightLockHashes | Select-Object -Unique).Count -ne 5) {
    throw 'The five preflight execution input locks must be launch-unique.'
}
if ($preflightCaseHashes.P0_parent -cne $preflightCaseHashes.P0R_parent_repeat) {
    throw 'P0/P0R preflight case-physics digests must match.'
}

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
            [string]$result.receipt.dynamic_chain_status -cne 'passed_test_double_no_execution' -or
            $result.marker_exists) {
        throw "Controlled production-chain receipt is invalid for $role."
    }
}

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

Write-Output 'toyRoadLauncherTest: PASS'
