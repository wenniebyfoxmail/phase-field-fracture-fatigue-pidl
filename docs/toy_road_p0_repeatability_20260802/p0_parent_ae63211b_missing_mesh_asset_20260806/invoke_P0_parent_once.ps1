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
$FixedSourceRoot = 'C:\q4diag\phase-field-fracture-fatigue-pidl-p0-sealed-ef764a4'
$FixedSourceCommit = 'ef764a4f3f23d82aecad64afed1de98c5dede8bc'
$FixedLauncher = 'C:\q4diag\phase-field-fracture-fatigue-pidl-p0-sealed-ef764a4\producer_handoffs\toy_road_p0_repeatability_20260803\launch_toy_road_family_case.ps1'
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