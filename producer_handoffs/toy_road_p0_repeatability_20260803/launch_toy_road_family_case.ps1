param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('P0_parent','P0R_parent_repeat','T1_initial_defect','T2_material_state','T3_loading_history')]
    [string]$Role,
    [Parameter(Mandatory = $true)][string]$SourceRoot,
    [Parameter(Mandatory = $true)][string]$GripfithRoot,
    [Parameter(Mandatory = $true)][string]$QualificationRoot,
    [Parameter(Mandatory = $true)][string]$InputAssetsRoot,
    [Parameter(Mandatory = $true)][string]$EvidenceRoot,
    [Parameter(Mandatory = $true)][string]$OutputRoot,
    [Parameter(Mandatory = $true)][string]$WorkRoot,
    [Parameter(Mandatory = $true)][string]$TempRoot,
    [Parameter(Mandatory = $true)][string]$TmpRoot,
    [Parameter(Mandatory = $true)][string]$PrefRoot,
    [Parameter(Mandatory = $true)][string]$CacheRoot,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-fA-F]{40}$')]
    [string]$ExpectedSourceCommit,
    [Parameter(Mandatory = $true)][string]$ReceiptPath,
    [Parameter(Mandatory = $true)][string]$ExecutionLockPath,
    [string]$PythonExecutable = 'C:\Users\xw436\AppData\Local\Programs\Python\Python312\python.exe',
    [string]$SuiteSparseRoot = 'C:\SuiteSparse\SuiteSparse-dev',
    [string]$ResumeFrom = '',
    [switch]$PreflightOnly,
    [string]$TestFixturePath = '',
    [string]$TestMeasurementFixturePath = '',
    [string]$TestInvocationRecordPath = '',
    [ValidateRange(0,10000)][int]$TestAdapterDelayMilliseconds = 0
)

$ErrorActionPreference = 'Stop'
$ProtocolVersion = 'toy-road-p0-repeatability-v2.1'
$ApprovedGripfithCommit = '355d4c83fefc2db88c32031a2dd2623b3de85c89'
$ApprovedInitialSha256 = 'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db'
$LegacyInitialSha256 = '589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340'
$MatlabExecutable = 'C:\Program Files\MATLAB\R2025b\bin\matlab.exe'
$ApprovedPythonExecutable = 'C:\Users\xw436\AppData\Local\Programs\Python\Python312\python.exe'
$ApprovedPythonSha256 = '15b41a488c356c0e331facdea6c836a6cec021f12d5fde9844e7ca4a1aa0361a'
$ScriptPath = [IO.Path]::GetFullPath($MyInvocation.MyCommand.Path)
$HandoffDir = Split-Path -Parent $ScriptPath
$ExpectedThreads = [ordered]@{
    OMP_NUM_THREADS = '1'
    MKL_NUM_THREADS = '1'
    OPENBLAS_NUM_THREADS = '1'
    MKL_DYNAMIC = 'FALSE'
}
$StartupPrefRoot = $PrefRoot + '.matlab-startup'
$WritableRoots = [ordered]@{
    output = $OutputRoot
    work = $WorkRoot
    temp = $TempRoot
    tmp = $TmpRoot
    pref = $PrefRoot
    cache = $CacheRoot
    matlab_startup_pref = $StartupPrefRoot
}

function Get-RequiredProperty([object]$Value, [string]$Name, [string]$Label) {
    if ($null -eq $Value) { throw "$Label is missing." }
    if ($Value -is [Collections.IDictionary]) {
        if (-not $Value.Contains($Name)) {
            throw "$Label is missing required provenance field $Name."
        }
        return $Value[$Name]
    }
    $property = $Value.PSObject.Properties[$Name]
    if ($null -eq $property) { throw "$Label is missing required provenance field $Name." }
    return $property.Value
}

function Assert-ExactFields([object]$Value, [string[]]$Names, [string]$Label) {
    if ($null -eq $Value) { throw "$Label is missing." }
    $actual = @($Value.PSObject.Properties.Name | Sort-Object -CaseSensitive)
    $expected = @($Names | Sort-Object -CaseSensitive)
    if (($actual -join "`n") -cne ($expected -join "`n")) {
        throw "$Label schema is incomplete or contains undeclared fields."
    }
}

function Assert-Hex([object]$Value, [int]$Length, [string]$Label) {
    if ([string]$Value -cnotmatch "^[0-9a-f]{$Length}$") {
        throw "$Label is missing or malformed."
    }
}

function Get-Sha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing hash-gated file: $Path"
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-ApprovedPythonIdentity {
    $resolved = [IO.Path]::GetFullPath($PythonExecutable)
    if (-not $resolved.Equals($ApprovedPythonExecutable,
            [StringComparison]::OrdinalIgnoreCase) -or
            -not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
        throw 'Python executable is not the fixed Task 6 protocol runtime.'
    }
    if ((Get-Sha256 $resolved) -cne $ApprovedPythonSha256) {
        throw 'Python executable SHA-256 is not the approved protocol runtime identity.'
    }
    $script:PythonExecutable = $resolved
}

function Write-BytesCreateNew([string]$Path, [byte[]]$Bytes) {
    $parent = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw "Receipt parent must already exist: $parent"
    }
    $stream = $null
    try {
        $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write, [IO.FileShare]::None)
        $stream.Write($Bytes, 0, $Bytes.Length)
        $stream.Flush($true)
    } finally {
        if ($null -ne $stream) { $stream.Dispose() }
    }
}

function ConvertTo-CanonicalObject([object]$Value) {
    if ($null -eq $Value -or $Value -is [string] -or $Value -is [bool] -or
            $Value -is [byte] -or $Value -is [int16] -or $Value -is [int32] -or
            $Value -is [int64] -or $Value -is [single] -or $Value -is [double] -or
            $Value -is [decimal]) {
        return $Value
    }
    if ($Value -is [Collections.IDictionary]) {
        $ordered = [ordered]@{}
        foreach ($name in @($Value.Keys | ForEach-Object { [string]$_ } | Sort-Object -CaseSensitive)) {
            $ordered[$name] = ConvertTo-CanonicalObject $Value[$name]
        }
        return $ordered
    }
    if ($Value -is [Collections.IEnumerable] -and $Value -isnot [string]) {
        return @($Value | ForEach-Object { ConvertTo-CanonicalObject $_ })
    }
    $object = [ordered]@{}
    foreach ($name in @($Value.PSObject.Properties.Name | Sort-Object -CaseSensitive)) {
        $object[$name] = ConvertTo-CanonicalObject $Value.$name
    }
    return $object
}

function ConvertTo-CanonicalJson([object]$Value) {
    return ((ConvertTo-CanonicalObject $Value) | ConvertTo-Json -Depth 30 -Compress)
}

function Write-CanonicalJsonCreateNew([string]$Path, [object]$Value) {
    $json = ConvertTo-CanonicalJson $Value
    $bytes = (New-Object Text.UTF8Encoding($false)).GetBytes($json)
    Write-BytesCreateNew $Path $bytes
    return Get-Sha256 $Path
}

function Resolve-PlainDirectory([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "$Label does not exist: $Path"
    }
    $item = Get-Item -LiteralPath $Path -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "$Label is a forbidden link/reparse point: $Path"
    }
    return $item.FullName
}

function Assert-NoReparsePathChain([string]$Path, [string]$Label) {
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    while ($null -ne $item) {
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "$Label contains a forbidden link/reparse point: $($item.FullName)"
        }
        $parent = Split-Path -Parent $item.FullName
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -ceq $item.FullName) { break }
        $item = Get-Item -LiteralPath $parent -Force -ErrorAction Stop
    }
}

function Assert-CanonicalExecutedSource([string]$ResolvedSource) {
    Assert-NoReparsePathChain $ResolvedSource 'Producer source root'
    Assert-NoReparsePathChain $ScriptPath 'Launcher path'
    $expectedHandoff = [IO.Path]::GetFullPath((Join-Path $ResolvedSource `
        'producer_handoffs\toy_road_p0_repeatability_20260803')).TrimEnd('\','/')
    $actualHandoff = [IO.Path]::GetFullPath($HandoffDir).TrimEnd('\','/')
    if (-not $actualHandoff.Equals($expectedHandoff, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Executed bytes are not inside the canonical sealed handoff under SourceRoot.'
    }
    $expectedLauncher = Join-Path $expectedHandoff 'launch_toy_road_family_case.ps1'
    if (-not $ScriptPath.Equals($expectedLauncher, [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Launcher path is not the canonical sealed SourceRoot entrypoint.'
    }
}

function Get-CanonicalAbsentPath([string]$Path, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($Path)) { throw "$Label path is empty." }
    $full = [IO.Path]::GetFullPath($Path).TrimEnd('\','/')
    if (Test-Path -LiteralPath $full) {
        throw "$Label must be initially absent; path already exists: $full"
    }
    $parent = Split-Path -Parent $full
    if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
        throw "$Label parent must already exist: $parent"
    }
    $parentItem = Get-Item -LiteralPath $parent -Force
    if (($parentItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "$Label parent is a forbidden link/reparse point."
    }
    return $full
}

function Assert-DisjointFreshRoots([Collections.IDictionary]$Roots) {
    $canonical = [ordered]@{}
    foreach ($name in $Roots.Keys) {
        if ([string]::IsNullOrWhiteSpace([string]$Roots[$name])) {
            throw "$name root path is empty."
        }
        $canonical[$name] = [IO.Path]::GetFullPath([string]$Roots[$name]).TrimEnd('\','/')
    }
    $names = @($canonical.Keys)
    for ($leftIndex = 0; $leftIndex -lt $names.Count; $leftIndex++) {
        for ($rightIndex = $leftIndex + 1; $rightIndex -lt $names.Count; $rightIndex++) {
            $left = $canonical[$names[$leftIndex]]
            $right = $canonical[$names[$rightIndex]]
            $separator = [IO.Path]::DirectorySeparatorChar
            if ($left.Equals($right, [StringComparison]::OrdinalIgnoreCase) -or
                    $left.StartsWith($right + $separator, [StringComparison]::OrdinalIgnoreCase) -or
                    $right.StartsWith($left + $separator, [StringComparison]::OrdinalIgnoreCase)) {
                throw "Writable roots must be distinct and non-nested: $left ; $right"
            }
        }
    }
    foreach ($name in $Roots.Keys) {
        Get-CanonicalAbsentPath $canonical[$name] "$name root" | Out-Null
    }
    return $canonical
}

function Invoke-Git([string]$Root, [string[]]$Arguments) {
    $output = & git -C $Root @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Git command failed in $Root`: $($Arguments -join ' ')" }
    return @($output)
}

function Get-CleanGitState([string]$Root) {
    $status = @(Invoke-Git $Root @('status','--porcelain','--untracked-files=all'))
    $commitLines = @(Invoke-Git $Root @('rev-parse','HEAD'))
    $commit = ([string]$commitLines[0]).Trim().ToLowerInvariant()
    return [ordered]@{ commit = $commit; clean = ($status.Count -eq 0) }
}

function Get-ContractSummary {
    Assert-ApprovedPythonIdentity
    $protocolPath = Join-Path $HandoffDir 'toy_road_protocol.py'
    $output = & $PythonExecutable $protocolPath --contract-summary 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Canonical contract validation failed: $($output -join ' ')" }
    $lines = @($output)
    return ([string]$lines[-1] | ConvertFrom-Json)
}

function Get-SourceSealReceipt {
    Assert-ApprovedPythonIdentity
    $protocolPath = Join-Path $HandoffDir 'toy_road_protocol.py'
    $output = & $PythonExecutable $protocolPath --verify-source-manifest $HandoffDir 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Sealed source-manifest verification failed: $($output -join ' ')"
    }
    return ([string]@($output)[-1] | ConvertFrom-Json)
}

function Assert-FinalSourceIdentity([object]$State, [bool]$IsFixture) {
    if ($IsFixture) {
        $finalGitState = $State.source
        if ($null -ne $State.PSObject.Properties['final_source_git']) {
            $finalGitState = $State.final_source_git
        }
    } else {
        $finalGitState = Get-CleanGitState $SourceRoot
    }
    if ($finalGitState.clean -ne $true -or
            [string]$finalGitState.commit -cne $ExpectedSourceCommit.ToLowerInvariant()) {
        throw 'Producer Git HEAD or clean status changed before MATLAB invocation.'
    }
    $finalSourceSeal = Get-SourceSealReceipt
    if ((ConvertTo-CanonicalJson $finalSourceSeal) -cne $SourceSealIdentity) {
        throw 'Sealed producer source identity changed before process invocation.'
    }
}

function Get-LiveExperimentInventory {
    return @(Get-CimInstance Win32_Process | ForEach-Object {
        [ordered]@{ name = $_.Name; process_id = $_.ProcessId; command_line = $_.CommandLine }
    })
}

function Assert-NoResumeInput {
    if (-not [string]::IsNullOrWhiteSpace($ResumeFrom)) {
        throw 'Checkpoint/resume input is forbidden.'
    }
    $resumeVariables = @(Get-ChildItem Env: | Where-Object {
        $_.Name -match '(?i)(checkpoint|resume)' -and
        -not [string]::IsNullOrWhiteSpace([string]$_.Value)
    })
    if ($resumeVariables.Count -gt 0) {
        throw "Checkpoint/resume environment is forbidden: $($resumeVariables.Name -join ', ')"
    }
}

function Assert-NoRunningExperiment([object[]]$Inventory) {
    $blocked = @($Inventory | Where-Object {
        $name = [string](Get-RequiredProperty $_ 'name' 'process inventory row')
        $command = [string](Get-RequiredProperty $_ 'command_line' 'process inventory row')
        $name -match '(?i)^(matlab|octave|octave-cli|abaqus|ansys|comsol|femsolver)(\.exe)?$' -or
        $command -match '(?i)(main_toy_road_family_case|solve_toy_road_family_case)'
    })
    if ($blocked.Count -gt 0) {
        throw 'Refusing launch while a running MATLAB/FEM experiment exists.'
    }
}

function Test-NativeAndJavaHardLinks([string]$Parent) {
    $token = [Guid]::NewGuid().ToString('N')
    $source = Join-Path $Parent ".$token.source"
    $native = Join-Path $Parent ".$token.native"
    $javaTarget = Join-Path $Parent ".$token.java"
    try {
        [IO.File]::WriteAllBytes($source, [byte[]](1,2,3,4))
        New-Item -ItemType HardLink -Path $native -Target $source -ErrorAction Stop | Out-Null
        if ((Get-Sha256 $native) -cne (Get-Sha256 $source)) {
            throw 'Native hard-link identity failed.'
        }
        $sourceLiteral = "'" + $source.Replace('\','/').Replace("'","''") + "'"
        $targetLiteral = "'" + $javaTarget.Replace('\','/').Replace("'","''") + "'"
        $javaBatch = "java.nio.file.Files.createLink(java.io.File($targetLiteral).toPath()," +
            "java.io.File($sourceLiteral).toPath())"
        & $MatlabExecutable -batch $javaBatch 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $javaTarget -PathType Leaf) -or
                (Get-Sha256 $javaTarget) -cne (Get-Sha256 $source)) {
            throw 'Java hard-link identity failed.'
        }
    } catch {
        throw "Required hard-link support failed: $($_.Exception.Message)"
    } finally {
        Remove-Item -LiteralPath $javaTarget,$native,$source -Force -ErrorAction SilentlyContinue
    }
}

function Get-ProductionState([object]$FamilyContract, [object]$ContractSummary) {
    $source = Get-CleanGitState $SourceRoot
    $griphfith = Get-CleanGitState $GripfithRoot
    $runtimeLockPath = Join-Path $SourceRoot 'producer_handoffs\rebuilt_initial_mex_qualification_20260801\RUNTIME_LOCK.json'
    $runtimeRoot = Join-Path $SourceRoot 'producer_handoffs\rebuilt_initial_mex_qualification_20260801'
    $initialPath = Join-Path $runtimeRoot 'runtime\initial.mexw64'
    $runtimeIdentity = $FamilyContract.runtime_identity
    Test-NativeAndJavaHardLinks (Split-Path -Parent $ReceiptPath)
    $pathIdentity = ConvertTo-CanonicalJson $runtimeIdentity.matlab.path_ordering
    $pathBytes = (New-Object Text.UTF8Encoding($false)).GetBytes($pathIdentity)
    $pathHasher = [Security.Cryptography.SHA256]::Create()
    try { $pathHash = ([BitConverter]::ToString($pathHasher.ComputeHash($pathBytes))).Replace('-','').ToLowerInvariant() }
    finally { $pathHasher.Dispose() }
    $runtime = [ordered]@{
        runtime_lock_sha256 = Get-Sha256 $runtimeLockPath
        initial_sha256 = Get-Sha256 $initialPath
        binaries = [ordered]@{
            initial = Get-Sha256 $initialPath
            AMOR = Get-Sha256 (Join-Path $GripfithRoot 'Sources\+phase_field\+mex\+fem\+assembly\+equilibrium\AMOR.mexw64')
            AT1_HISTORY_FATIGUE = Get-Sha256 (Join-Path $GripfithRoot 'Sources\+phase_field\+mex\+fem\+assembly\+pf\AT1_HISTORY_FATIGUE.mexw64')
            cholmod2 = Get-Sha256 (Join-Path $SuiteSparseRoot 'CHOLMOD\MATLAB\cholmod2.mexw64')
        }
        compiler = [ordered]@{
            fortran = [string]$runtimeIdentity.build_provenance.fortran_compiler
            cpp = [string]$runtimeIdentity.build_provenance.cpp_compiler
            linker = [string]$runtimeIdentity.build_provenance.linker
            mex_configuration = [string]$runtimeIdentity.build_provenance.mex_configuration
            build_command_sha256 = Get-Sha256 (Join-Path $runtimeRoot 'build\BUILD_COMMAND.txt')
            build_log_sha256 = Get-Sha256 (Join-Path $runtimeRoot 'build\BUILD_LOG.txt')
            toolchain_sha256 = Get-Sha256 (Join-Path $runtimeRoot 'build\TOOLCHAIN.json')
            source_hashes_sha256 = Get-Sha256 (Join-Path $runtimeRoot 'build\SOURCE_HASHES.json')
        }
        matlab = [ordered]@{
            release = [string]$runtimeIdentity.matlab.release
            version = [string]$runtimeIdentity.matlab.version
            executable_sha256 = Get-Sha256 $MatlabExecutable
            path_sha256 = $pathHash
            blas = [string]$runtimeIdentity.matlab.blas
            lapack = [string]$runtimeIdentity.matlab.lapack
        }
        machine = [ordered]@{
            computer_name = $env:COMPUTERNAME
            cpu_name = ((Get-CimInstance Win32_Processor | Select-Object -First 1).Name).Trim()
            cpu_id = [string](Get-CimInstance Win32_Processor | Select-Object -First 1).ProcessorId
            windows_build = [string](Get-CimInstance Win32_OperatingSystem).BuildNumber
            architecture = [string](Get-CimInstance Win32_OperatingSystem).OSArchitecture
        }
        threads = $ExpectedThreads
        h5py_version = '3.16.0'
        java_hard_link_supported = $true
        native_hard_link_supported = $true
        mesh_sha256_semantics = [string]$runtimeIdentity.mesh_sha256_semantics
    }
    $q1Path = Join-Path $QualificationRoot 'Q1\Q1_RECEIPT.json'
    if (-not (Test-Path -LiteralPath $q1Path -PathType Leaf)) {
        $q1Path = Join-Path $QualificationRoot 'Q1_RECEIPT.json'
    }
    if (-not (Test-Path -LiteralPath $q1Path -PathType Leaf)) {
        $q1 = [ordered]@{ present = $false }
    } else {
        $value = Get-Content -LiteralPath $q1Path -Raw | ConvertFrom-Json
        $q1 = [ordered]@{
            present = $true
            schema_version = [string]$value.schema_version
            passed = [bool]$value.passed
            source_clean = [bool]$value.source_clean
            source_commit = [string]$value.source_commit
            runtime_initial_sha256 = [string]$value.runtime_initial_sha256
            runtime_lock_sha256 = [string]$value.runtime_lock_sha256
            receipt_sha256 = Get-Sha256 $q1Path
            result_sha256 = [string]$value.result_sha256
        }
    }
    $processes = @(Get-LiveExperimentInventory)
    if ($PreflightOnly) {
        $predecessors = @()
        $repeatability = $null
        $familyFailed = $false
    } else {
        $predecessors = @(Get-ProductionPredecessors)
        $repeatability = Get-ProductionRepeatabilityEvidence
        $familyFailed = Test-Path -LiteralPath (Join-Path $EvidenceRoot 'FAMILY_FAILURE.json')
    }
    return [ordered]@{
        authorization_scope = 'production_candidate'
        source = $source
        griphfith = $griphfith
        runtime = $runtime
        q1 = $q1
        contracts = [ordered]@{
            family_contract_sha256 = [string]$ContractSummary.family_contract_sha256
            case_physics_contract_sha256 = [string]$ContractSummary.cases.$Role.case_physics_contract_sha256
            mesh_sha256 = [string]$ContractSummary.cases.$Role.mesh_sha256
            declared_mesh_sha256 = [string]$ContractSummary.cases.$Role.mesh_sha256
        }
        process_inventory = $processes
        family_failed = $familyFailed
        predecessors = $predecessors
        repeatability_evidence = $repeatability
        final_process_inventory = @()
    }
}

function Get-ProductionTerminalEvidence([string]$CaseId) {
    $root = Join-Path $EvidenceRoot $CaseId
    $tokenPath = Join-Path (Split-Path -Parent $ReceiptPath) `
        ('.' + $noClobberId + '.' + $CaseId + '.terminal-auth.json')
    $protocolPath = Join-Path $HandoffDir 'toy_road_protocol.py'
    Assert-ApprovedPythonIdentity
    $output = & $PythonExecutable $protocolPath --authenticate-terminal `
        $root $CaseId $tokenPath 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Predecessor $CaseId terminal package authentication failed: $($output -join ' ')"
    }
    $token = Get-Content -LiteralPath $tokenPath -Raw | ConvertFrom-Json
    $script:AuthenticationTokenPaths += $tokenPath
    return [ordered]@{
        case_id = [string]$token.case_id
        authorization_scope = [string]$token.authorization_scope
        terminal_validation_status = [string]$token.status
        c5_status = [string]$token.status
        runtime_lock_sha256 = [string]$token.runtime_lock_sha256
        family_contract_sha256 = [string]$token.family_contract_sha256
        case_physics_contract_sha256 = [string]$token.case_physics_contract_sha256
        terminal_manifest_sha256 = [string]$token.manifest_sha256
        c5_receipt_sha256 = [string]$token.c5_receipt_sha256
        package_snapshot_sha256 = [string]$token.package_snapshot_sha256
        authentication_receipt_path = $tokenPath
        authentication_receipt_sha256 = Get-Sha256 $tokenPath
    }
}

function Get-ProductionPredecessors {
    switch ($Role) {
        'P0_parent' { return @() }
        'P0R_parent_repeat' { return @(Get-ProductionTerminalEvidence 'P0_parent') }
        'T1_initial_defect' { return @() }
        'T2_material_state' { return @(Get-ProductionTerminalEvidence 'T1_initial_defect') }
        'T3_loading_history' {
            return @(
                (Get-ProductionTerminalEvidence 'T1_initial_defect'),
                (Get-ProductionTerminalEvidence 'T2_material_state')
            )
        }
    }
}

function Get-ProductionRepeatabilityEvidence {
    if ($Role -cne 'T1_initial_defect') { return $null }
    $path = Join-Path $EvidenceRoot 'P0_REPEATABILITY_EVIDENCE_LOCK.json'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        throw 'P0/P0R repeatability evidence is missing before T1.'
    }
    $tokenPath = Join-Path (Split-Path -Parent $ReceiptPath) `
        ('.' + $noClobberId + '.repeatability-auth.json')
    $protocolPath = Join-Path $HandoffDir 'toy_road_protocol.py'
    $p0 = Join-Path $EvidenceRoot 'P0_parent'
    $p0r = Join-Path $EvidenceRoot 'P0R_parent_repeat'
    Assert-ApprovedPythonIdentity
    $output = & $PythonExecutable $protocolPath --authenticate-repeatability `
        $path $p0 $p0r $tokenPath 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "P0/P0R repeatability authentication failed: $($output -join ' ')"
    }
    $token = Get-Content -LiteralPath $tokenPath -Raw | ConvertFrom-Json
    $script:AuthenticationTokenPaths += $tokenPath
    return [ordered]@{
        authorization_scope = [string]$token.authorization_scope
        status = [string]$token.status
        runtime_lock_sha256 = [string]$token.runtime_lock_sha256
        family_contract_sha256 = [string]$token.family_contract_sha256
        p0_manifest_sha256 = [string]$token.p0_manifest_sha256
        p0r_manifest_sha256 = [string]$token.p0r_manifest_sha256
        p0_c5_receipt_sha256 = [string]$token.p0_c5_receipt_sha256
        p0r_c5_receipt_sha256 = [string]$token.p0r_c5_receipt_sha256
        p0_package_snapshot_sha256 = [string]$token.p0_package_snapshot_sha256
        p0r_package_snapshot_sha256 = [string]$token.p0r_package_snapshot_sha256
        authentication_receipt_path = $tokenPath
        authentication_receipt_sha256 = Get-Sha256 $tokenPath
    }
}

function Assert-RuntimeAndStaticContract(
    [object]$State,
    [object]$FamilyContract,
    [object]$ContractSummary
) {
    $source = Get-RequiredProperty $State 'source' 'source provenance'
    if ((Get-RequiredProperty $source 'clean' 'source provenance') -ne $true) {
        throw 'Producer source is dirty; a clean sealed source is required.'
    }
    if ([string](Get-RequiredProperty $source 'commit' 'source provenance') -cne
            $ExpectedSourceCommit.ToLowerInvariant()) {
        throw 'Producer source commit does not match the exact sealed commit.'
    }
    $grip = Get-RequiredProperty $State 'griphfith' 'GRIPHFiTH provenance'
    if ((Get-RequiredProperty $grip 'clean' 'GRIPHFiTH provenance') -ne $true) {
        throw 'GRIPHFiTH source is dirty; clean source is required.'
    }
    if ([string](Get-RequiredProperty $grip 'commit' 'GRIPHFiTH provenance') -cne
            $ApprovedGripfithCommit) {
        throw 'GRIPHFiTH source commit is not the locked commit.'
    }
    $runtime = Get-RequiredProperty $State 'runtime' 'runtime provenance'
    $initial = [string](Get-RequiredProperty $runtime 'initial_sha256' 'runtime provenance')
    if ($initial -ceq $LegacyInitialSha256) {
        throw 'The legacy crashing initial MEX hash is rejected.'
    }
    if ($initial -cne $ApprovedInitialSha256) {
        throw 'Unknown initial MEX hash; only the approved rebuilt binary is accepted.'
    }
    $runtimeIdentity = $FamilyContract.runtime_identity
    if ([string](Get-RequiredProperty $runtime 'runtime_lock_sha256' 'runtime provenance') -cne
            [string]$runtimeIdentity.runtime_lock_sha256) {
        throw 'Runtime lock SHA-256 differs from the family contract.'
    }
    $binaries = Get-RequiredProperty $runtime 'binaries' 'runtime binary provenance'
    foreach ($name in @('initial','AMOR','AT1_HISTORY_FATIGUE','cholmod2')) {
        $actual = [string](Get-RequiredProperty $binaries $name 'runtime binary provenance')
        $expected = [string]$runtimeIdentity.binary_sha256.$name
        Assert-Hex $actual 64 "runtime $name SHA-256"
        if ($actual -cne $expected) { throw "Runtime binary hash mismatch: $name" }
    }
    $compiler = Get-RequiredProperty $runtime 'compiler' 'compiler/build provenance'
    $compilerMap = [ordered]@{
        fortran = 'fortran_compiler'
        cpp = 'cpp_compiler'
        linker = 'linker'
        mex_configuration = 'mex_configuration'
        build_command_sha256 = 'build_command_sha256'
        build_log_sha256 = 'build_log_sha256'
        toolchain_sha256 = 'toolchain_sha256'
        source_hashes_sha256 = 'source_hashes_sha256'
    }
    foreach ($name in $compilerMap.Keys) {
        $actual = [string](Get-RequiredProperty $compiler $name 'compiler/build provenance')
        $expected = [string]$runtimeIdentity.build_provenance.($compilerMap[$name])
        if ($actual -cne $expected) { throw "Compiler/build provenance mismatch: $name" }
    }
    $matlab = Get-RequiredProperty $runtime 'matlab' 'MATLAB provenance'
    foreach ($name in @('release','version','executable_sha256','path_sha256','blas','lapack')) {
        $actual = [string](Get-RequiredProperty $matlab $name 'MATLAB provenance')
        if ([string]::IsNullOrWhiteSpace($actual)) { throw "MATLAB provenance is missing $name." }
    }
    foreach ($pair in @(
        @('release','release'), @('version','version'),
        @('executable_sha256','executable_sha256'), @('blas','blas'), @('lapack','lapack')
    )) {
        if ([string]$matlab.($pair[0]) -cne [string]$runtimeIdentity.matlab.($pair[1])) {
            throw "MATLAB provenance mismatch: $($pair[0])"
        }
    }
    Assert-Hex $matlab.path_sha256 64 'MATLAB path SHA-256'
    if ([string]$matlab.path_sha256 -cne [string]$runtimeIdentity.matlab.path_ordering_sha256) {
        throw 'MATLAB path ordering hash differs from the family runtime lock.'
    }
    $machine = Get-RequiredProperty $runtime 'machine' 'machine/CPU provenance'
    foreach ($name in @('computer_name','cpu_name','cpu_id','windows_build','architecture')) {
        $actual = [string](Get-RequiredProperty $machine $name 'machine/CPU provenance')
        $expected = [string]$runtimeIdentity.machine.$name
        if ($actual.Trim() -cne $expected.Trim()) { throw "Machine/CPU provenance mismatch: $name" }
    }
    $threads = Get-RequiredProperty $runtime 'threads' 'thread provenance'
    foreach ($name in $ExpectedThreads.Keys) {
        if ([string](Get-RequiredProperty $threads $name 'thread provenance') -cne $ExpectedThreads[$name]) {
            throw "Thread provenance mismatch: $name"
        }
    }
    if ([string](Get-RequiredProperty $runtime 'h5py_version' 'runtime provenance') -cne '3.16.0') {
        throw 'Runtime h5py must be exactly 3.16.0.'
    }
    if ((Get-RequiredProperty $runtime 'java_hard_link_supported' 'runtime provenance') -ne $true) {
        throw 'Java hard-link support is required.'
    }
    if ((Get-RequiredProperty $runtime 'native_hard_link_supported' 'runtime provenance') -ne $true) {
        throw 'Native hard-link support is required.'
    }
    if ([string](Get-RequiredProperty $runtime 'mesh_sha256_semantics' 'runtime provenance') -cne
            [string]$runtimeIdentity.mesh_sha256_semantics) {
        throw 'Canonical mesh hash byte semantics mismatch.'
    }
    $q1 = Get-RequiredProperty $State 'q1' 'Q1 provenance'
    if ((Get-RequiredProperty $q1 'present' 'Q1 provenance') -ne $true) {
        throw 'Q1 qualified receipt is missing.'
    }
    foreach ($name in @('schema_version','passed','source_clean','source_commit',
            'runtime_initial_sha256','runtime_lock_sha256','receipt_sha256','result_sha256')) {
        Get-RequiredProperty $q1 $name 'Q1 provenance' | Out-Null
    }
    if ([string]$q1.schema_version -cne 'rebuilt_initial_mex_q1_receipt_v1' -or
            $q1.passed -ne $true -or $q1.source_clean -ne $true -or
            [string]$q1.source_commit -cne $ApprovedGripfithCommit -or
            [string]$q1.runtime_initial_sha256 -cne $ApprovedInitialSha256 -or
            [string]$q1.runtime_lock_sha256 -cne [string]$runtimeIdentity.runtime_lock_sha256 -or
            [string]$q1.receipt_sha256 -cne [string]$runtimeIdentity.q1.receipt_sha256 -or
            [string]$q1.result_sha256 -cne [string]$runtimeIdentity.q1.result_sha256) {
        throw 'Q1 qualified receipt identity or PASS state is invalid.'
    }
    $contracts = Get-RequiredProperty $State 'contracts' 'contract provenance'
    if ([string]$contracts.family_contract_sha256 -cne [string]$ContractSummary.family_contract_sha256 -or
            [string]$contracts.case_physics_contract_sha256 -cne
                [string]$ContractSummary.cases.$Role.case_physics_contract_sha256 -or
            [string]$contracts.declared_mesh_sha256 -cne
                [string]$ContractSummary.cases.$Role.mesh_sha256 -or
            [string]$contracts.mesh_sha256 -cne [string]$contracts.declared_mesh_sha256) {
        throw 'Case-declared mesh or canonical contract identity mismatch.'
    }
    Assert-NoRunningExperiment @($State.process_inventory)
}

function Assert-TerminalPredecessor([object]$Record, [string]$ExpectedRole, [object]$ContractSummary) {
    foreach ($name in @('case_id','authorization_scope','terminal_validation_status','c5_status',
            'runtime_lock_sha256','family_contract_sha256','case_physics_contract_sha256',
            'terminal_manifest_sha256','c5_receipt_sha256','package_snapshot_sha256',
            'authentication_receipt_path','authentication_receipt_sha256')) {
        Get-RequiredProperty $Record $name "predecessor $ExpectedRole" | Out-Null
    }
    if ([string]$Record.authorization_scope -cin @('preflight_only_non_authorizing','test_only_non_authorizing')) {
        throw "Predecessor $ExpectedRole has a non-authorizing preflight/test scope."
    }
    if ([string]$Record.authorization_scope -cne 'production_authorized' -or
            [string]$Record.case_id -cne $ExpectedRole -or
            [string]$Record.terminal_validation_status -cne 'PASS') {
        throw "Predecessor $ExpectedRole failed terminal validation or order identity."
    }
    if ([string]$Record.c5_status -cne 'PASS') {
        throw "Predecessor $ExpectedRole case-local c5 receipt is missing or failed."
    }
    if ([string]$Record.runtime_lock_sha256 -cne [string]$FamilyContract.runtime_identity.runtime_lock_sha256 -or
            [string]$Record.family_contract_sha256 -cne [string]$ContractSummary.family_contract_sha256 -or
            [string]$Record.case_physics_contract_sha256 -cne
                [string]$ContractSummary.cases.$ExpectedRole.case_physics_contract_sha256) {
        throw "Predecessor $ExpectedRole runtime or contract identity changed."
    }
    Assert-Hex $Record.terminal_manifest_sha256 64 "predecessor $ExpectedRole terminal manifest"
    Assert-Hex $Record.c5_receipt_sha256 64 "predecessor $ExpectedRole c5 receipt"
    Assert-Hex $Record.package_snapshot_sha256 64 "predecessor $ExpectedRole package snapshot"
    Assert-Hex $Record.authentication_receipt_sha256 64 `
        "predecessor $ExpectedRole authentication receipt"
}

function Assert-DynamicChain([object]$State, [object]$ContractSummary) {
    if ((Get-RequiredProperty $State 'family_failed' 'family state') -eq $true) {
        throw 'A previous family member failed; the family is stopped.'
    }
    $records = @(Get-RequiredProperty $State 'predecessors' 'predecessor evidence')
    $expected = @(switch ($Role) {
        'P0_parent' { @() }
        'P0R_parent_repeat' { @('P0_parent') }
        'T1_initial_defect' { @() }
        'T2_material_state' { @('T1_initial_defect') }
        'T3_loading_history' { @('T1_initial_defect','T2_material_state') }
    })
    if ($records.Count -ne $expected.Count) {
        throw "Dynamic predecessor chain is incomplete or out of order for $Role."
    }
    for ($index = 0; $index -lt $expected.Count; $index++) {
        Assert-TerminalPredecessor $records[$index] $expected[$index] $ContractSummary
    }
    if ($Role -ceq 'T1_initial_defect') {
        $repeatability = Get-RequiredProperty $State 'repeatability_evidence' 'P0/P0R repeatability evidence'
        foreach ($name in @('authorization_scope','status','runtime_lock_sha256',
                'family_contract_sha256','p0_manifest_sha256','p0r_manifest_sha256',
                'p0_c5_receipt_sha256','p0r_c5_receipt_sha256',
                'p0_package_snapshot_sha256','p0r_package_snapshot_sha256',
                'authentication_receipt_path','authentication_receipt_sha256')) {
            Get-RequiredProperty $repeatability $name 'P0/P0R repeatability evidence' | Out-Null
        }
        if ([string]$repeatability.authorization_scope -cin
                @('preflight_only_non_authorizing','test_only_non_authorizing')) {
            throw 'Preflight/test receipt cannot authorize production repeatability evidence.'
        }
        if ([string]$repeatability.authorization_scope -cne 'production_authorized' -or
                [string]$repeatability.status -cne 'PASS' -or
                [string]$repeatability.runtime_lock_sha256 -cne
                    [string]$FamilyContract.runtime_identity.runtime_lock_sha256 -or
                [string]$repeatability.family_contract_sha256 -cne
                    [string]$ContractSummary.family_contract_sha256) {
            throw 'P0/P0R repeatability evidence is missing, failed, or runtime-replaced.'
        }
        foreach ($name in @('p0_manifest_sha256','p0r_manifest_sha256',
                'p0_c5_receipt_sha256','p0r_c5_receipt_sha256',
                'p0_package_snapshot_sha256','p0r_package_snapshot_sha256',
                'authentication_receipt_sha256')) {
            Assert-Hex $repeatability.$name 64 "repeatability $name hash"
        }
    }
}

function Assert-AuthenticatedEvidenceUnchanged([object]$State) {
    if ([string]$State.authorization_scope -cne 'production_candidate') { return }
    $protocolPath = Join-Path $HandoffDir 'toy_road_protocol.py'
    foreach ($tokenPath in @($script:AuthenticationTokenPaths)) {
        Assert-ApprovedPythonIdentity
        $output = & $PythonExecutable $protocolPath --recheck-authentication $tokenPath 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Authenticated predecessor evidence changed before launch: $($output -join ' ')"
        }
    }
}

function ConvertTo-MatlabLiteral([string]$Value) {
    return "'" + $Value.Replace('\','/').Replace("'","''") + "'"
}

function New-CanonicalMatlabPathContract([string[]]$AbsolutePathOrder) {
    $canonical = @($AbsolutePathOrder | ForEach-Object { [IO.Path]::GetFullPath($_) })
    $commands = @()
    for ($index = $canonical.Count - 1; $index -ge 0; $index--) {
        $commands += 'addpath(' + (ConvertTo-MatlabLiteral $canonical[$index]) + ",'-begin')"
    }
    return [pscustomobject]@{
        absolute_path_order = $canonical
        add_path_commands = $commands
    }
}

Assert-NoResumeInput
Assert-ApprovedPythonIdentity
$resolvedSource = Resolve-PlainDirectory $SourceRoot 'Producer source root'
Assert-CanonicalExecutedSource $resolvedSource
$resolvedGrip = Resolve-PlainDirectory $GripfithRoot 'GRIPHFiTH source root'
Resolve-PlainDirectory $QualificationRoot 'Q1 qualification root' | Out-Null
Resolve-PlainDirectory $InputAssetsRoot 'Input-assets root' | Out-Null
$resolvedEvidence = Resolve-PlainDirectory $EvidenceRoot 'Evidence root'
$canonicalRoots = Assert-DisjointFreshRoots $WritableRoots
if (Test-Path -LiteralPath $ReceiptPath) { throw 'Authorization receipt path already exists.' }
if (Test-Path -LiteralPath $ExecutionLockPath) { throw 'Execution input lock path already exists.' }

$familyPath = Join-Path $HandoffDir 'FAMILY_CONTRACT.json'
$closurePath = Join-Path $HandoffDir 'HISTORICAL_Q2_CLOSURE.json'
if (-not (Test-Path -LiteralPath $familyPath -PathType Leaf) -or
        -not (Test-Path -LiteralPath $closurePath -PathType Leaf)) {
    throw 'Family contract or historical Q2 closure is missing.'
}
$FamilyContract = Get-Content -LiteralPath $familyPath -Raw | ConvertFrom-Json
$closure = Get-Content -LiteralPath $closurePath -Raw | ConvertFrom-Json
if ([string]$closure.verdict -cne 'historical_q2_parent_irrecoverable' -or
        $closure.historical_q2_passed -ne $false -or
        $closure.active_field_backward_equivalence_claimed -ne $false) {
    throw 'Historical Q2 closure is missing, failed, or makes a forbidden active-field claim.'
}
$ContractSummary = Get-ContractSummary
$SourceSealReceipt = Get-SourceSealReceipt
$SourceSealIdentity = ConvertTo-CanonicalJson $SourceSealReceipt
$launchTimestamp = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ')
$noClobberId = [Guid]::NewGuid().ToString('N')
$script:AuthenticationTokenPaths = @()
$isFixture = -not [string]::IsNullOrWhiteSpace($TestFixturePath)
if ($isFixture) {
    if (-not (Test-Path -LiteralPath $TestFixturePath -PathType Leaf)) {
        throw 'Test fixture is missing.'
    }
    Assert-NoReparsePathChain $TestFixturePath 'Test fixture'
    if (-not $PreflightOnly -and (
            [string]::IsNullOrWhiteSpace($TestMeasurementFixturePath) -or
            [string]::IsNullOrWhiteSpace($TestInvocationRecordPath))) {
        throw 'The sealed test adapter requires measurement and invocation-record paths.'
    }
}
if (-not $PreflightOnly -and -not $isFixture -and $Role -ceq 'P0_parent') {
    if ([string]::IsNullOrWhiteSpace(
            [string]$env:TOY_ROAD_P0_ONE_SHOT_AUTHORIZATION_ID) -or
            [string]$env:TOY_ROAD_DEDICATED_PRODUCER_ATTESTED -cne 'true' -or
            [string]$env:TOY_ROAD_DEDICATED_PRODUCER_MACHINE -cne 'CITPC12' -or
            [string]$env:COMPUTERNAME -cne 'CITPC12') {
        throw 'P0_parent requires the sealed one-shot authorization wrapper and dedicated producer attestation.'
    }
}

$overlayRoot = Join-Path (Split-Path -Parent $OutputRoot) `
    ('.toy-road-runtime-overlay-' + $noClobberId)
$overlayLeaf = Join-Path $overlayRoot '+phase_field\+mex\+fem\+assembly\+equilibrium'
$overlayInitial = Join-Path $overlayLeaf 'initial.mexw64'
$paths = @(
    [IO.Path]::GetFullPath($overlayRoot),
    [IO.Path]::GetFullPath($HandoffDir),
    [IO.Path]::GetFullPath((Join-Path $resolvedGrip 'Sources')),
    [IO.Path]::GetFullPath((Join-Path $SuiteSparseRoot 'CHOLMOD\MATLAB')),
    [IO.Path]::GetFullPath((Join-Path $SuiteSparseRoot 'AMD\MATLAB')),
    [IO.Path]::GetFullPath((Join-Path $SuiteSparseRoot 'COLAMD\MATLAB')),
    [IO.Path]::GetFullPath((Join-Path $SuiteSparseRoot 'CCOLAMD\MATLAB')),
    [IO.Path]::GetFullPath((Join-Path $SuiteSparseRoot 'CAMD\MATLAB'))
)
$pathContract = New-CanonicalMatlabPathContract $paths
$paths = @($pathContract.absolute_path_order)
$familyMutex = $null
$familyMutexOwned = $false
$familyMutexMarker = $null
$familyMutexPath = Join-Path $resolvedEvidence '.toy-road-family-execution.mutex'
if (-not $PreflightOnly) {
    try {
        $familyMutexName = 'Local\GRIPHFiTH_ToyRoad_' +
            [string]$ContractSummary.family_contract_sha256
        $createdNew = $false
        $familyMutex = [Threading.Mutex]::new($true, $familyMutexName,
            [ref]$createdNew)
        if (-not $createdNew) {
            $familyMutex.Dispose()
            $familyMutex = $null
            throw 'Another toy-road family launcher holds the family-wide execution mutex.'
        }
        $familyMutexOwned = $true
        $familyMutexMarker = New-Object IO.FileStream($familyMutexPath,
            [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite,
            [IO.FileShare]::None, 4096, [IO.FileOptions]::DeleteOnClose)
    } catch {
        if ($familyMutexOwned -and $null -ne $familyMutex) {
            $familyMutex.ReleaseMutex()
            $familyMutexOwned = $false
        }
        if ($null -ne $familyMutex) {
            $familyMutex.Dispose()
            $familyMutex = $null
        }
        throw 'Another toy-road family launcher holds the family-wide execution mutex.'
    }
}

try {
    if ($isFixture) {
        $State = Get-Content -LiteralPath $TestFixturePath -Raw | ConvertFrom-Json
        if ([string](Get-RequiredProperty $State 'authorization_scope' 'test fixture') -cne
                'test_only_non_authorizing') {
            throw 'Only test_only_non_authorizing fixtures are accepted by the test seam.'
        }
    } else {
        $State = Get-ProductionState $FamilyContract $ContractSummary
    }

    Assert-RuntimeAndStaticContract $State $FamilyContract $ContractSummary
    if (-not $PreflightOnly) { Assert-DynamicChain $State $ContractSummary }

    if ($PreflightOnly) {
        $scope = 'preflight_only_non_authorizing'
        $dynamicStatus = 'not_evaluated_no_execution'
        $entrypoint = ''
    } elseif ($isFixture) {
        $scope = 'test_only_non_authorizing'
        $dynamicStatus = 'passed_test_adapter_non_authorizing'
        $entrypoint = 'sealed_non_matlab_test_adapter'
    } else {
        $scope = 'production_authorized'
        $dynamicStatus = 'passed_predecessor_chain'
        $entrypoint = 'run_toy_road_runtime_bridge'
    }
    $releaseMatch = [regex]::Match([string]$State.runtime.matlab.release,
        '^(?<release>R[0-9]{4}[ab])\s+(?<update>Update\s+[0-9]+)$')
    if (-not $releaseMatch.Success) { throw 'Locked MATLAB release/update label is malformed.' }
    $runtimeExpectations = [ordered]@{
        matlab = [ordered]@{
            release = $releaseMatch.Groups['release'].Value
            update = $releaseMatch.Groups['update'].Value
            version = [string]$State.runtime.matlab.version
            computer = [string]$FamilyContract.runtime_identity.matlab.computer
            executable_sha256 = [string]$State.runtime.matlab.executable_sha256
            blas = [string]$State.runtime.matlab.blas
            lapack = [string]$State.runtime.matlab.lapack
            absolute_path_order = $paths
        }
        binary_sha256 = [ordered]@{
            initial = [string]$State.runtime.binaries.initial
            AMOR = [string]$State.runtime.binaries.AMOR
            AT1_HISTORY_FATIGUE = [string]$State.runtime.binaries.AT1_HISTORY_FATIGUE
            cholmod2 = [string]$State.runtime.binaries.cholmod2
        }
    }
    $lockRequest = [ordered]@{
        authorization_scope = $scope
        role = $Role
        family_contract_sha256 = [string]$ContractSummary.family_contract_sha256
        case_physics_contract_sha256 = [string]$ContractSummary.cases.$Role.case_physics_contract_sha256
        source_commit = $ExpectedSourceCommit.ToLowerInvariant()
        runtime_lock_sha256 = [string]$FamilyContract.runtime_identity.runtime_lock_sha256
        source_manifest_sha256 = [string]$SourceSealReceipt.source_manifest_sha256
        runtime_expectations = $runtimeExpectations
        roots = [ordered]@{
            output = $canonicalRoots.output
            work = $canonicalRoots.work
            temp = $canonicalRoots.temp
            tmp = $canonicalRoots.tmp
            pref = $canonicalRoots.pref
            cache = $canonicalRoots.cache
            matlab_startup_pref = $canonicalRoots.matlab_startup_pref
        }
        launch_timestamp_utc = $launchTimestamp
        no_clobber_receipt_id = $noClobberId
    }
    $lockRequestPath = Join-Path (Split-Path -Parent $ExecutionLockPath) `
        ('.' + $noClobberId + '.execution-lock-request.json')
    try {
        Write-CanonicalJsonCreateNew $lockRequestPath $lockRequest | Out-Null
        $protocolPath = Join-Path $HandoffDir 'toy_road_protocol.py'
        Assert-ApprovedPythonIdentity
        $lockOutput = & $PythonExecutable $protocolPath --emit-execution-lock `
            $lockRequestPath $ExecutionLockPath 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Canonical Python execution-lock emission failed: $($lockOutput -join ' ')"
        }
        $lockReceipt = [string]@($lockOutput)[-1] | ConvertFrom-Json
        $executionDigest = [string](Get-RequiredProperty $lockReceipt `
            'execution_input_lock_sha256' 'canonical execution-lock receipt')
        Assert-Hex $executionDigest 64 'execution input lock SHA-256'
        if ((Get-Sha256 $ExecutionLockPath) -cne $executionDigest) {
            throw 'Canonical execution-lock bytes do not match the Python digest.'
        }
    } finally {
        Remove-Item -LiteralPath $lockRequestPath -Force -ErrorAction SilentlyContinue
    }
    $receipt = [ordered]@{
        schema_version = 'toy_road_launch_authorization_receipt_v1'
        status = 'PASS'
        authorization_scope = $scope
        authorized_entrypoint = $entrypoint
        dynamic_chain_status = $dynamicStatus
        protocol_version = $ProtocolVersion
        case_id = $Role
        source_commit = $ExpectedSourceCommit.ToLowerInvariant()
        source_manifest_sha256 = [string]$SourceSealReceipt.source_manifest_sha256
        runtime_lock_sha256 = [string]$FamilyContract.runtime_identity.runtime_lock_sha256
        family_contract_sha256 = [string]$ContractSummary.family_contract_sha256
        case_physics_contract_sha256 = [string]$ContractSummary.cases.$Role.case_physics_contract_sha256
        execution_input_lock_sha256 = $executionDigest
        q1_receipt_sha256 = [string]$FamilyContract.runtime_identity.q1.receipt_sha256
        initial_mexw64_sha256 = $ApprovedInitialSha256
        launch_timestamp_utc = $launchTimestamp
        no_clobber_receipt_id = $noClobberId
        current_case_c5_status = 'not_evaluated_before_execution'
    }
    Write-CanonicalJsonCreateNew $ReceiptPath $receipt | Out-Null

    if ($PreflightOnly) {
        Write-Output (ConvertTo-CanonicalJson $receipt)
        return
    }

    $initialArtifact = Join-Path $SourceRoot `
        'producer_handoffs\rebuilt_initial_mex_qualification_20260801\runtime\initial.mexw64'
    $runtimeMeasurementPath = Join-Path (Split-Path -Parent $ReceiptPath) `
        ('.' + $noClobberId + '.runtime-measurement.json')
    try {
        [IO.Directory]::CreateDirectory($overlayLeaf) | Out-Null
        if (-not $isFixture) {
            New-Item -ItemType HardLink -Path $overlayInitial -Target $initialArtifact `
                -ErrorAction Stop | Out-Null
            if ((Get-Sha256 $overlayInitial) -cne $ApprovedInitialSha256) {
                throw 'Runtime overlay does not contain the approved rebuilt initial MEX.'
            }
        }
        foreach ($name in $ExpectedThreads.Keys) {
            Set-Item -Path "Env:$name" -Value $ExpectedThreads[$name]
        }
        $env:TEMP = $canonicalRoots.temp
        $env:TMP = $canonicalRoots.tmp
        $env:MATLAB_PREFDIR = $canonicalRoots.matlab_startup_pref
        $env:MCR_CACHE_ROOT = $canonicalRoots.cache
        $env:TOY_ROAD_CASE_ROLE = $Role
        $env:TOY_ROAD_SOURCE_COMMIT = $ExpectedSourceCommit.ToLowerInvariant()
        $env:TOY_ROAD_RUNTIME_LOCK_SHA256 = [string]$FamilyContract.runtime_identity.runtime_lock_sha256
        $env:TOY_ROAD_FAMILY_CONTRACT_SHA256 = [string]$ContractSummary.family_contract_sha256
        $env:TOY_ROAD_CASE_PHYSICS_CONTRACT_SHA256 = [string]$ContractSummary.cases.$Role.case_physics_contract_sha256
        $env:TOY_ROAD_EXECUTION_INPUT_LOCK_SHA256 = $executionDigest
        $env:TOY_ROAD_OUTPUT_ROOT = $canonicalRoots.output
        $env:TOY_ROAD_WORK_ROOT = $canonicalRoots.work
        $env:TOY_ROAD_TEMP_ROOT = $canonicalRoots.temp
        $env:TOY_ROAD_TMP_ROOT = $canonicalRoots.tmp
        $env:TOY_ROAD_PREF_ROOT = $canonicalRoots.pref
        $env:TOY_ROAD_CACHE_ROOT = $canonicalRoots.cache
        $env:TOY_ROAD_INPUT_ASSETS_ROOT = (Resolve-Path -LiteralPath $InputAssetsRoot).Path
        $env:TOY_ROAD_AUTHORIZATION_RECEIPT = [IO.Path]::GetFullPath($ReceiptPath)
        $addPathCommands = @($pathContract.add_path_commands)
        $bridgeCall = 'run_toy_road_runtime_bridge(' +
            (ConvertTo-MatlabLiteral ([IO.Path]::GetFullPath($ExecutionLockPath))) + ',' +
            (ConvertTo-MatlabLiteral ([IO.Path]::GetFullPath($runtimeMeasurementPath))) + ')'
        $batch = (($addPathCommands + $bridgeCall) -join ';') + ';'

        Assert-FinalSourceIdentity $State $isFixture
        Assert-AuthenticatedEvidenceUnchanged $State
        if ($isFixture) {
            Assert-NoRunningExperiment @(
                Get-RequiredProperty $State 'final_process_inventory' 'final process inventory')
        } else {
            Assert-NoRunningExperiment @(Get-LiveExperimentInventory)
        }

        if ($isFixture) {
            Assert-NoReparsePathChain $TestMeasurementFixturePath `
                'Test runtime measurement fixture'
            if (Test-Path -LiteralPath $TestInvocationRecordPath) {
                throw 'Test adapter invocation record must be initially absent.'
            }
            $adapter = Join-Path $HandoffDir 'invoke_toy_road_test_process_adapter.ps1'
            $batchBase64 = [Convert]::ToBase64String(
                (New-Object Text.UTF8Encoding($false)).GetBytes($batch))
            & powershell -NoProfile -ExecutionPolicy Bypass -File $adapter `
                -ExecutionLockPath $ExecutionLockPath `
                -MeasurementFixturePath $TestMeasurementFixturePath `
                -MeasurementReceiptPath $runtimeMeasurementPath `
                -InvocationRecordPath $TestInvocationRecordPath `
                -BatchCommandBase64 $batchBase64 `
                -DelayMilliseconds $TestAdapterDelayMilliseconds
            if ($LASTEXITCODE -ne 0) {
                throw "Sealed non-MATLAB test adapter failed with exit code $LASTEXITCODE."
            }
        } else {
            & $MatlabExecutable -batch $batch
            if ($LASTEXITCODE -ne 0) {
                throw "MATLAB family case failed with exit code $LASTEXITCODE."
            }
        }
        Assert-ApprovedPythonIdentity
        $measurementOutput = & $PythonExecutable (Join-Path $HandoffDir 'toy_road_protocol.py') `
            --validate-runtime-measurement $ExecutionLockPath $runtimeMeasurementPath 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "Runtime measurement receipt validation failed: $($measurementOutput -join ' ')"
        }
        Write-Output (ConvertTo-CanonicalJson $receipt)
    } finally {
        Remove-Item -LiteralPath $overlayRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
} finally {
    if ($null -ne $familyMutexMarker) { $familyMutexMarker.Dispose() }
    if ($familyMutexOwned -and $null -ne $familyMutex) {
        $familyMutex.ReleaseMutex()
    }
    if ($null -ne $familyMutex) { $familyMutex.Dispose() }
    Remove-Item -LiteralPath $familyMutexPath -Force -ErrorAction SilentlyContinue
}
