param(
    [Parameter(Mandatory = $true)][string]$SharedRepo,
    [Parameter(Mandatory = $true)][string]$GripfithRoot,
    [Parameter(Mandatory = $true)][string]$ParentRoot,
    [Parameter(Mandatory = $true)][string]$OutputParent,
    [Parameter(Mandatory = $true)]
    [ValidateSet('T1_initial_defect','T2_material_state','T3_loading_history')]
    [string]$CaseId,
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-fA-F]{40}$')]
    [string]$ExpectedSourceCommit,
    [switch]$PreflightOnly,
    [string]$TestFixturePath = ''
)

$ErrorActionPreference = 'Stop'
$ExpectedGripfithCommit = '355d4c83fefc2db88c32031a2dd2623b3de85c89'
$HandoffRelative = 'producer_handoffs/toy_to_road_independent_fem_20260731'
$HandoffDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ManifestPath = Join-Path $HandoffDir 'SHA256SUMS.txt'
$OutputRoot = Join-Path $OutputParent $CaseId

function Get-Sha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing hash-gated file: $Path"
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Invoke-Git([string]$Root, [string[]]$Arguments) {
    $output = & git -C $Root @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Git command failed in $Root`: git $($Arguments -join ' ')"
    }
    return @($output)
}

function Assert-CleanGit([string]$Root, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        throw "$Label root does not exist: $Root"
    }
    $dirty = @(Invoke-Git $Root @('status', '--porcelain', '--untracked-files=all'))
    if ($dirty.Count -gt 0) {
        throw "$Label is dirty; immutable launch refused."
    }
}

function Assert-HashRecords(
    [string]$Root,
    [object[]]$Records,
    [string]$Label,
    [switch]$PathsAreAbsolute
) {
    $verified = @()
    foreach ($record in @($Records)) {
        $relative = [string]$record.path
        if ([string]::IsNullOrWhiteSpace($relative)) {
            throw "$Label contains an empty path."
        }
        if ($PathsAreAbsolute) {
            $path = $relative
        } else {
            $path = Join-Path $Root $relative
        }
        $actual = Get-Sha256 $path
        $expected = ([string]$record.sha256).ToLowerInvariant()
        if ($actual -ne $expected) {
            throw "$Label SHA256 mismatch: $relative"
        }
        $verified += [ordered]@{ path = $relative.Replace('\', '/'); sha256 = $actual }
    }
    return @($verified)
}

function Get-ManifestEntries([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Missing source SHA256 manifest: $Path"
    }
    $entries = @()
    foreach ($line in Get-Content -LiteralPath $Path) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        if ($line -notmatch '^([0-9a-fA-F]{64})  ([^\\].*)$') {
            throw "Malformed source SHA256 manifest line: $line"
        }
        $relative = $Matches[2]
        if ([IO.Path]::IsPathRooted($relative) -or $relative -match '(^|/)\.\.(/|$)' -or
                $relative -eq "$HandoffRelative/SHA256SUMS.txt") {
            throw "Unsafe source manifest path: $relative"
        }
        $entries += [ordered]@{
            sha256 = $Matches[1].ToLowerInvariant()
            path = $relative
        }
    }
    $folded = @($entries | ForEach-Object { $_.path.ToLowerInvariant() })
    if (($folded | Select-Object -Unique).Count -ne $folded.Count) {
        throw 'Source manifest has duplicate or case-colliding paths.'
    }
    return @($entries)
}

function Get-ProductionSourcePaths {
    $paths = @()
    $paths += Get-ChildItem -LiteralPath $HandoffDir -Recurse -File -Filter '*.m' |
        ForEach-Object { $_.FullName.Substring((Resolve-Path $SharedRepo).Path.Length + 1).Replace('\', '/') }
    $paths += Get-ChildItem -LiteralPath $HandoffDir -File -Filter '*_LOCK.json' |
        ForEach-Object { $_.FullName.Substring((Resolve-Path $SharedRepo).Path.Length + 1).Replace('\', '/') }
    $paths += @(
        "$HandoffRelative/README.md",
        "$HandoffRelative/launch_toy_road_case.ps1",
        'tests/test_toy_road_fem_handoff.py'
    )
    return @($paths | Sort-Object -Unique)
}

function Assert-SourceManifest([string[]]$RequiredPaths) {
    $entries = @(Get-ManifestEntries $ManifestPath)
    $manifestPaths = @($entries | ForEach-Object { $_.path } | Sort-Object)
    $required = @($RequiredPaths | Sort-Object)
    if (($manifestPaths -join "`n") -cne ($required -join "`n")) {
        throw 'Source manifest coverage differs from the exact sealed source set.'
    }
    foreach ($entry in $entries) {
        $actual = Get-Sha256 (Join-Path $SharedRepo $entry.path)
        if ($actual -ne $entry.sha256) {
            throw "Source SHA256 mismatch: $($entry.path)"
        }
    }
    return Get-Sha256 $ManifestPath
}

function Assert-NoResumeInput {
    $resumeVariables = @(Get-ChildItem Env: | Where-Object {
        $_.Name -match '(?i)(checkpoint|resume)' -and
        -not [string]::IsNullOrWhiteSpace([string]$_.Value)
    })
    if ($resumeVariables.Count -gt 0) {
        throw "Checkpoint/resume input is forbidden: $($resumeVariables.Name -join ', ')"
    }
}

function Assert-NoRunningExperiment([object[]]$Inventory) {
    $blocked = @($Inventory | Where-Object {
        $name = [string]$_.name
        $commandLine = [string]$_.command_line
        $name -match '(?i)^matlab(\.exe)?$' -or
        $name -match '(?i)^(abaqus|ansys|comsol|femsolver)(\.exe)?$' -or
        $commandLine -match '(?i)(main_toy_to_road_case|solve_toy_to_road_case)'
    })
    if ($blocked.Count -gt 0) {
        $descriptions = @($blocked | ForEach-Object {
            "$($_.name) pid=$($_.process_id)"
        })
        throw "Refusing launch while a running MATLAB/FEM experiment exists: $($descriptions -join '; ')"
    }
}

function Assert-HardLinkSupport([bool]$ForceFailure) {
    $token = [Guid]::NewGuid().ToString('N')
    $source = Join-Path $OutputParent ".toy-road-hardlink-preflight-$token.source"
    $target = Join-Path $OutputParent ".toy-road-hardlink-preflight-$token.target"
    try {
        [IO.File]::WriteAllBytes($source, [byte[]](1, 2, 3, 4))
        if ($ForceFailure) {
            throw 'Injected unsupported hard-link preflight.'
        }
        New-Item -ItemType HardLink -Path $target -Target $source -ErrorAction Stop | Out-Null
        if (-not (Test-Path -LiteralPath $target -PathType Leaf) -or
                (Get-Sha256 $target) -ne (Get-Sha256 $source)) {
            throw 'Hard-link identity check failed.'
        }
    } catch {
        throw "Required same-volume output hard-link preflight failed: $($_.Exception.Message)"
    } finally {
        Remove-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $source -Force -ErrorAction SilentlyContinue
    }
}

function ConvertTo-MatlabLiteral([string]$Value) {
    return "'" + $Value.Replace('\', '/').Replace("'", "''") + "'"
}

if (-not [string]::IsNullOrWhiteSpace($TestFixturePath) -and -not $PreflightOnly) {
    throw 'TestFixturePath is permitted only with PreflightOnly; test seams cannot invoke MATLAB.'
}
if (-not (Test-Path -LiteralPath $OutputParent -PathType Container)) {
    throw "Output parent must already exist: $OutputParent"
}
if (Test-Path -LiteralPath $OutputRoot) {
    throw "Refusing to overwrite existing output root: $OutputRoot"
}
Assert-NoResumeInput

$resolvedShared = (Resolve-Path -LiteralPath $SharedRepo).Path
$resolvedHandoff = (Resolve-Path -LiteralPath $HandoffDir).Path
$expectedHandoff = (Join-Path $resolvedShared $HandoffRelative.Replace('/', '\'))
if (-not [IO.Path]::GetFullPath($expectedHandoff).Equals(
        [IO.Path]::GetFullPath($resolvedHandoff), [StringComparison]::OrdinalIgnoreCase)) {
    throw 'The launcher must execute from the selected SharedRepo handoff directory.'
}

Assert-CleanGit $SharedRepo 'Shared repo'
$sourceCommitLines = @(Invoke-Git $SharedRepo @('rev-parse', 'HEAD'))
$sourceCommit = ([string]$sourceCommitLines[0]).Trim().ToLowerInvariant()
if ($sourceCommit -ne $ExpectedSourceCommit.ToLowerInvariant()) {
    throw "Shared repo HEAD is not the exact sealed source commit $ExpectedSourceCommit."
}

$fixture = $null
if (-not [string]::IsNullOrWhiteSpace($TestFixturePath)) {
    $fixture = Get-Content -LiteralPath $TestFixturePath -Raw | ConvertFrom-Json
    $requiredSourcePaths = @($fixture.required_source_paths | ForEach-Object { [string]$_ })
} else {
    $requiredSourcePaths = @(Get-ProductionSourcePaths)
}
$sourceManifestSha256 = Assert-SourceManifest $requiredSourcePaths

$parentLockPath = Join-Path $HandoffDir 'PARENT_LOCK.json'
$caseLockPath = Join-Path $HandoffDir ($CaseId.Substring(0, 2) + '_INPUT_LOCK.json')
$parentLockSha256 = Get-Sha256 $parentLockPath
$caseLockSha256 = Get-Sha256 $caseLockPath
$caseLock = Get-Content -LiteralPath $caseLockPath -Raw | ConvertFrom-Json
if ([string]$caseLock.case_id -cne $CaseId -or
        ([string]$caseLock.parent_lock_sha256).ToLowerInvariant() -ne $parentLockSha256) {
    throw 'Case lock identity or parent lock SHA-256 is invalid.'
}

Assert-CleanGit $GripfithRoot 'GRIPHFiTH producer repo'
$gripCommitLines = @(Invoke-Git $GripfithRoot @('rev-parse', 'HEAD'))
$gripCommit = ([string]$gripCommitLines[0]).Trim().ToLowerInvariant()
if ($null -ne $fixture) {
    $expectedGripCommit = ([string]$fixture.expected_gripfith_commit).ToLowerInvariant()
    $gripSourceRecords = @($fixture.gripfith_sources)
    $runtimeRecords = @($fixture.runtime_files)
    $parentRecords = @($fixture.parent_files)
    $processInventory = @($fixture.process_inventory)
    $forceHardLinkFailure = [bool]$fixture.force_hardlink_failure
} else {
    $expectedGripCommit = $ExpectedGripfithCommit
    $gripSourceRecords = @(
        [ordered]@{ path = 'Scripts/fatigue_fracture/solve_fatigue_fracture.m'; sha256 = 'ae1aa2ff4114c67b166e39b377e08a0d7e28761bb0afa038a388e1eb026e9252' },
        [ordered]@{ path = 'Sources/+phase_field/+fem/+solver/newton_raphson.m'; sha256 = '20afff63d79eeffd3e6a502b996485e47f64a3b550e19b396cd1bf90120ad76d' },
        [ordered]@{ path = 'Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m'; sha256 = 'c9ebc6e87ddc1e6340a6fe077903241656feedea5220488035fb49e3efe55831' },
        [ordered]@{ path = 'Scripts/brittle_fracture/INPUT_SENS_tensile.m'; sha256 = '3cc4ba07cf4b0d5a556457567b719c633e65a3519e1a734ddea00c608c292353' },
        [ordered]@{ path = 'Scripts/fatigue_fracture/init_fatigue_fracture.m'; sha256 = '96365b7f0b6ecf02cd0e2209765310f29122f503b5c2272240f84fb24ea4098d' },
        [ordered]@{ path = 'Sources/+phase_field/System.m'; sha256 = '383fe2566a63652b9287fec3172f4135800e7cb605efcc718e90abf3a54ec5fa' },
        [ordered]@{ path = 'Dependencies/meshes/sens_mesh.m'; sha256 = 'dbf13237939425b61cde93b841ae2c24e7fccd291861df5508a34800bb9f4706' }
    )
    $runtimeRecords = @(
        [ordered]@{ path = (Join-Path $GripfithRoot 'Sources/+phase_field/+mex/+fem/+assembly/+equilibrium/initial.mexw64'); sha256 = '589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340' },
        [ordered]@{ path = (Join-Path $GripfithRoot 'Sources/+phase_field/+mex/+fem/+assembly/+equilibrium/AMOR.mexw64'); sha256 = '64abee69f2c441730dc2efa4047ac45ab1d1b40e20c4822ed6e992adcd6b19e7' },
        [ordered]@{ path = (Join-Path $GripfithRoot 'Sources/+phase_field/+mex/+fem/+assembly/+pf/AT1_HISTORY_FATIGUE.mexw64'); sha256 = '53e8fd0b229817b7c14c52a5b6afaa957692f475057b79b9a9a10195ccb92e60' },
        [ordered]@{ path = 'C:/SuiteSparse/SuiteSparse-dev/CHOLMOD/MATLAB/cholmod2.mexw64'; sha256 = '86a2f15543eda1f7223a1733d935d37e9e2f4f2c2d8db3c4adc2c0f675c27329' }
    )
    $parentRecords = @(
        [ordered]@{ path = 'u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1/initial_state_metadata.mat'; sha256 = '0e0144b63ca93836c515b489b64ae768058588d7f2431d49c0b95607e35916d8' },
        [ordered]@{ path = 'u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1/state0_analysis.mat'; sha256 = '91b8f89ba3a211f08f1b79def5d2d50a973798e988deedc5c5c7e3b64a98ef11' },
        [ordered]@{ path = 'u012/pre_run_lock.mat'; sha256 = '6cc63d42e596ef5a96882a02c3b34bb8257ce83b4db97eaf78770c286a701f37' },
        [ordered]@{ path = 'u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1/psi_fields/cycle_0001.mat'; sha256 = '72925ac353f766475862858befcc611307e71faa392eb774d7ce5aa8a40d74d9' },
        [ordered]@{ path = 'u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1/psi_fields/cycle_0083.mat'; sha256 = 'b0e6a7119b1c265197de88938e5f65d4e7069e199e104812463b3b911b4f77e9' },
        [ordered]@{ path = 'u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1/psi_fields/cycle_0086.mat'; sha256 = '0ce0426012e0d8aa563650e5d45bdee7214d28502378c420593f4b889a317a13' },
        [ordered]@{ path = 'MANIFEST.csv'; sha256 = '0b0152fd18ecb16496c4c8683ed44573bf4721544d1719ad79675668e4d68580' }
    )
    $processInventory = @(Get-CimInstance Win32_Process | ForEach-Object {
        [ordered]@{ name = $_.Name; process_id = $_.ProcessId; command_line = $_.CommandLine }
    })
    $forceHardLinkFailure = $false
}
if ($gripCommit -ne $expectedGripCommit) {
    throw "GRIPHFiTH commit mismatch: expected $expectedGripCommit, found $gripCommit."
}
$gripSourceHashes = Assert-HashRecords $GripfithRoot $gripSourceRecords 'GRIPHFiTH source'
$runtimeHashes = Assert-HashRecords '' $runtimeRecords 'Runtime MEX/SuiteSparse/CHOLMOD' -PathsAreAbsolute
$parentSourceHashes = Assert-HashRecords $ParentRoot $parentRecords 'Parent'

Assert-NoRunningExperiment $processInventory
Assert-HardLinkSupport $forceHardLinkFailure

$env:TOY_ROAD_CASE_ID = $CaseId
$env:TOY_ROAD_OUTPUT_ROOT = $OutputRoot
$env:TOY_ROAD_SOURCE_COMMIT = $sourceCommit
$env:TOY_ROAD_LOCK_SHA256 = $caseLockSha256

$receipt = [ordered]@{
    TOY_ROAD_CASE_ID = $env:TOY_ROAD_CASE_ID
    TOY_ROAD_LOCK_SHA256 = $env:TOY_ROAD_LOCK_SHA256
    TOY_ROAD_OUTPUT_ROOT = $env:TOY_ROAD_OUTPUT_ROOT
    TOY_ROAD_SOURCE_COMMIT = $env:TOY_ROAD_SOURCE_COMMIT
}
if ($PreflightOnly) {
    Write-Output ($receipt | ConvertTo-Json -Compress)
    return
}

$suiteSparseRoot = 'C:/SuiteSparse/SuiteSparse-dev'
$matlabPaths = @(
    $HandoffDir,
    (Join-Path $GripfithRoot 'Sources'),
    "$suiteSparseRoot/CHOLMOD/MATLAB",
    "$suiteSparseRoot/AMD/MATLAB",
    "$suiteSparseRoot/COLAMD/MATLAB",
    "$suiteSparseRoot/CCOLAMD/MATLAB",
    "$suiteSparseRoot/CAMD/MATLAB"
)
$addPath = ($matlabPaths | ForEach-Object {
    "addpath(" + (ConvertTo-MatlabLiteral $_) + ")"
}) -join ';'
$startedUtc = (Get-Date).ToUniversalTime().ToString('o')
& matlab -batch "$addPath;main_toy_to_road_case"
$matlabExit = $LASTEXITCODE
$finishedUtc = (Get-Date).ToUniversalTime().ToString('o')
if ($matlabExit -ne 0) {
    throw "MATLAB case solve failed with exit code $matlabExit."
}
$runResultPath = Join-Path $OutputRoot 'RUN_RESULT.json'
if (-not (Test-Path -LiteralPath $runResultPath -PathType Leaf)) {
    throw 'MATLAB returned successfully without the sole RUN_RESULT.json completion marker.'
}
$runResult = Get-Content -LiteralPath $runResultPath -Raw | ConvertFrom-Json
if (-not [bool]$runResult.complete -or [string]$runResult.status -cne 'complete' -or
        [string]$runResult.case_id -cne $CaseId) {
    throw 'MATLAB returned without a valid complete RUN_RESULT.json marker.'
}

$sourceBranchLines = @(Invoke-Git $SharedRepo @('branch', '--show-current'))
$sourceBranch = ([string]$sourceBranchLines[0]).Trim()
$provenance = [ordered]@{
    schema_version = 'toy_road_producer_provenance_v1'
    case_id = $CaseId
    source_commit = $sourceCommit
    source_branch = $sourceBranch
    source_manifest_sha256 = $sourceManifestSha256
    case_lock_sha256 = $caseLockSha256
    parent_lock_sha256 = $parentLockSha256
    griphfith_commit = $gripCommit
    griphfith_source_hashes = $gripSourceHashes
    runtime_hashes = $runtimeHashes
    parent_source_hashes = $parentSourceHashes
    started_utc = $startedUtc
    finished_utc = $finishedUtc
    matlab_exit_code = $matlabExit
}
$provenanceInput = [IO.Path]::GetTempFileName()
try {
    $json = $provenance | ConvertTo-Json -Depth 8
    [IO.File]::WriteAllText($provenanceInput, $json, (New-Object Text.UTF8Encoding($false)))
    $finalizeCommand = "$addPath;finalize_toy_road_package(" +
        (ConvertTo-MatlabLiteral $OutputRoot) + ',' +
        (ConvertTo-MatlabLiteral $CaseId) + ',' +
        (ConvertTo-MatlabLiteral $provenanceInput) + ')'
    & matlab -batch $finalizeCommand
    $finalizeExit = $LASTEXITCODE
} finally {
    Remove-Item -LiteralPath $provenanceInput -Force -ErrorAction SilentlyContinue
}
if ($finalizeExit -ne 0) {
    throw "MATLAB package finalization failed with exit code $finalizeExit."
}
Write-Host "Immutable toy-road case package finalized: $OutputRoot"
