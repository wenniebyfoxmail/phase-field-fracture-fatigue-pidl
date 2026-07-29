param(
    [Parameter(Mandatory = $true)][string]$SharedRepo,
    [Parameter(Mandatory = $true)][string]$GripfithRoot,
    [Parameter(Mandatory = $true)][string]$OutputParent
)

$ErrorActionPreference = 'Stop'
$HandoffDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$HashFile = Join-Path $HandoffDir 'SHA256SUMS.txt'
$LockFile = Join-Path $HandoffDir 'INPUT_LOCK.json'
$Lock = Get-Content $LockFile -Raw | ConvertFrom-Json

foreach ($line in Get-Content $HashFile) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $parts = $line -split '\s+', 2
    $expected = $parts[0].ToLowerInvariant()
    $relative = $parts[1].Trim()
    $path = Join-Path $HandoffDir $relative
    if (-not (Test-Path $path -PathType Leaf)) { throw "Missing locked input: $path" }
    $actual = (Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $expected) { throw "SHA256 mismatch for $relative" }
}

$sourceCommit = (git -C $SharedRepo rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve shared-repo commit.' }
$dirty = git -C $SharedRepo status --porcelain
if ($dirty) { throw 'Shared repo is dirty; F1b requires an immutable checkout.' }

$gripCommit = (git -C $GripfithRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve GRIPHFiTH producer commit.' }
$gripDirty = git -C $GripfithRoot status --porcelain
if ($gripDirty) { throw 'GRIPHFiTH producer repo is dirty; F1b requires immutable solver sources.' }

$gripFiles = [ordered]@{
    'Scripts/fatigue_fracture/solve_fatigue_fracture.m' = $Lock.solver_provenance.base_solver_snapshot_sha256
    'Sources/+phase_field/+fem/+solver/newton_raphson.m' = $Lock.solver_provenance.base_newton_snapshot_sha256
    'Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m' = $Lock.solver_provenance.base_staggered_post_update_sha256
    'Scripts/brittle_fracture/INPUT_SENS_tensile.m' = $Lock.solver_provenance.base_input_sens_sha256
    'Scripts/fatigue_fracture/init_fatigue_fracture.m' = $Lock.solver_provenance.base_init_fatigue_sha256
}
foreach ($relative in $gripFiles.Keys) {
    $path = Join-Path $GripfithRoot $relative
    if (-not (Test-Path $path -PathType Leaf)) { throw "Missing GRIPHFiTH source: $path" }
    $actual = (Get-FileHash $path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actual -ne $gripFiles[$relative]) { throw "GRIPHFiTH source hash mismatch: $relative" }
}

$shortCommit = $sourceCommit.Substring(0, 12)
$caseId = "F1b_exactPi_dimensional_v2_20260729_$shortCommit"
$outputRoot = Join-Path $OutputParent $caseId
if (Test-Path $outputRoot) { throw "Refusing to overwrite existing output root: $outputRoot" }

$env:F1B_OUTPUT_ROOT = $outputRoot
$env:F1B_SOURCE_COMMIT = $sourceCommit
$env:F1B_INPUT_LOCK_SHA256 = (Get-FileHash $LockFile -Algorithm SHA256).Hash.ToLowerInvariant()

$handoffMatlab = $HandoffDir.Replace('\', '/')
$fatigueDir = (Join-Path $GripfithRoot 'Scripts/fatigue_fracture').Replace('\', '/')
$matlabCommand = "addpath('$handoffMatlab'); cd('$fatigueDir'); main_F1b_exact_pi_dimensional"

$started = (Get-Date).ToUniversalTime().ToString('o')
& matlab -batch $matlabCommand
$matlabExit = $LASTEXITCODE
$finished = (Get-Date).ToUniversalTime().ToString('o')
if ($matlabExit -ne 0) { throw "MATLAB F1b solve failed with exit code $matlabExit" }
if (-not (Test-Path $outputRoot -PathType Container)) { throw 'MATLAB did not create the locked output root.' }

$provenance = [ordered]@{
    analysis = 'F1b_exact_pi_solver_invariance_v2'
    fresh_fem_solve = $true
    source_commit = $sourceCommit
    source_branch = (git -C $SharedRepo branch --show-current).Trim()
    gripfith_commit = $gripCommit
    gripfith_branch = (git -C $GripfithRoot branch --show-current).Trim()
    gripfith_sources_clean = $true
    shared_repo = (Resolve-Path $SharedRepo).Path
    gripfith_root = (Resolve-Path $GripfithRoot).Path
    handoff_dir = (Resolve-Path $HandoffDir).Path
    input_lock_sha256 = $env:F1B_INPUT_LOCK_SHA256
    output_root = (Resolve-Path $outputRoot).Path
    started_utc = $started
    finished_utc = $finished
    matlab_exit_code = $matlabExit
}
$provenance | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 (Join-Path $outputRoot 'F1B_PRODUCER_PROVENANCE.json')
Write-Host "F1b fresh solve completed: $outputRoot"
