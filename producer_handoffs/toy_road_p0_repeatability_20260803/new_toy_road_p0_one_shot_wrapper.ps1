param(
    [Parameter(Mandatory = $true)][string]$SealedSourceRoot,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{40}$')][string]$ExpectedSourceCommit,
    [Parameter(Mandatory = $true)][string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$sourceRoot = [IO.Path]::GetFullPath($SealedSourceRoot)
$output = [IO.Path]::GetFullPath($OutputPath)
$commit = $ExpectedSourceCommit.ToLowerInvariant()
$launcher = Join-Path $sourceRoot `
    'producer_handoffs\toy_road_p0_repeatability_20260803\launch_toy_road_family_case.ps1'

$head = ([string](& git -C $sourceRoot rev-parse HEAD)).Trim().ToLowerInvariant()
if ($LASTEXITCODE -ne 0 -or $head -cne $commit) {
    throw 'One-shot wrapper must be generated from the exact sealed source commit.'
}
$status = @(& git -C $sourceRoot status --porcelain --untracked-files=all)
if ($LASTEXITCODE -ne 0 -or $status.Count -ne 0) {
    throw 'One-shot wrapper generation requires a clean sealed source checkout.'
}
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw 'Sealed P0 launcher is missing.'
}
if (Test-Path -LiteralPath $output) {
    throw 'One-shot wrapper output already exists.'
}
$parent = Split-Path -Parent $output
if (-not (Test-Path -LiteralPath $parent -PathType Container)) {
    throw 'One-shot wrapper parent must already exist.'
}

$template = @'
param(
    [Parameter(Mandatory = $true)][string]$ExecutionAuthorizationPath,
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
    [Parameter(Mandatory = $true)][string]$ReceiptPath,
    [Parameter(Mandatory = $true)][string]$ExecutionLockPath
)

$ErrorActionPreference = 'Stop'
$FixedRole = 'P0_parent'
$FixedSourceRoot = '__SOURCE_ROOT__'
$FixedSourceCommit = '__SOURCE_COMMIT__'
$FixedLauncher = '__LAUNCHER__'
$authorizationPath = [IO.Path]::GetFullPath($ExecutionAuthorizationPath)
if (-not (Test-Path -LiteralPath $authorizationPath -PathType Leaf)) {
    throw 'A separate P0 execution authorization is required.'
}
$authorizationText = Get-Content -LiteralPath $authorizationPath -Raw
if ($authorizationText -match 'preflight_only_non_authorizing') {
    throw 'A preflight receipt cannot authorize production execution.'
}
$authorization = $authorizationText | ConvertFrom-Json
if ([string]$authorization.status -cne 'P0_PARENT_EXECUTION_AUTHORIZED' -or
        [string]$authorization.authorization_scope -cne 'production_authorized_p0_parent_one_shot' -or
        [string]$authorization.role -cne $FixedRole -or
        [string]$authorization.source_commit -cne $FixedSourceCommit -or
        $authorization.production_execution_authorized -ne $true -or
        $authorization.dedicated_producer_attested -ne $true -or
        [string]$authorization.machine_name -cne 'CITPC12' -or
        [string]$authorization.exclusive_control -cne 'no_manual_or_agent_matlab_fem' -or
        [string]::IsNullOrWhiteSpace([string]$authorization.authorization_id)) {
    throw 'Execution authorization does not authorize this sealed P0_parent wrapper.'
}
$consumedPath = $authorizationPath + '.consumed'
$consumedBytes = (New-Object Text.UTF8Encoding($false)).GetBytes(
    [string]$authorization.authorization_id + "`n")
$stream = $null
try {
    $stream = [IO.File]::Open($consumedPath, [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write, [IO.FileShare]::None)
    $stream.Write($consumedBytes, 0, $consumedBytes.Length)
    $stream.Flush($true)
} finally {
    if ($null -ne $stream) { $stream.Dispose() }
}

$env:TOY_ROAD_P0_ONE_SHOT_AUTHORIZATION_ID = [string]$authorization.authorization_id
$env:TOY_ROAD_DEDICATED_PRODUCER_ATTESTED = 'true'
$env:TOY_ROAD_DEDICATED_PRODUCER_MACHINE = [string]$authorization.machine_name

& $FixedLauncher -Role $FixedRole -SourceRoot $FixedSourceRoot `
    -GripfithRoot $GripfithRoot -QualificationRoot $QualificationRoot `
    -InputAssetsRoot $InputAssetsRoot -EvidenceRoot $EvidenceRoot `
    -OutputRoot $OutputRoot -WorkRoot $WorkRoot -TempRoot $TempRoot `
    -TmpRoot $TmpRoot -PrefRoot $PrefRoot -CacheRoot $CacheRoot `
    -ExpectedSourceCommit $FixedSourceCommit -ReceiptPath $ReceiptPath `
    -ExecutionLockPath $ExecutionLockPath
if ($LASTEXITCODE -ne 0) {
    throw "Sealed P0_parent launcher failed with exit code $LASTEXITCODE."
}
'@

function Escape-SingleQuoted([string]$Value) {
    return $Value.Replace("'", "''")
}
$content = $template.Replace('__SOURCE_ROOT__', (Escape-SingleQuoted $sourceRoot)).
    Replace('__SOURCE_COMMIT__', $commit).
    Replace('__LAUNCHER__', (Escape-SingleQuoted $launcher))
$bytes = (New-Object Text.UTF8Encoding($false)).GetBytes($content)
$stream = $null
try {
    $stream = [IO.File]::Open($output, [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write, [IO.FileShare]::None)
    $stream.Write($bytes, 0, $bytes.Length)
    $stream.Flush($true)
} finally {
    if ($null -ne $stream) { $stream.Dispose() }
}
