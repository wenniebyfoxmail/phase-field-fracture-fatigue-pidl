$ErrorActionPreference = 'Stop'
$handoff = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$launcherPath = Join-Path $handoff 'launch_toy_road_case.ps1'
$source = Get-Content -LiteralPath $launcherPath -Raw
[scriptblock]::Create($source) | Out-Null

$required = @(
    '[string]$QualificationRoot',
    'FAMILY_QUALIFICATION_RECEIPT.json',
    'qualification_evidence_lock_sha256',
    'FAMILY_RUNTIME_RECEIPT.json',
    'Assert-FamilySequence',
    'Previous family member failed terminal validation',
    'Family runtime or qualification changed between cases',
    'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db',
    'Legacy crashing initial MEX is rejected',
    'New-RuntimeOverlay',
    '$addPath += ";addpath(" + (ConvertTo-MatlabLiteral $runtimeOverlay.root)',
    "which('phase_field.mex.fem.assembly.equilibrium.initial')",
    'toy_road_launch_receipt_v2'
)
foreach ($token in $required) {
    if (-not $source.Contains($token)) {
        throw "Toy-road launcher qualification contract is missing: $token"
    }
}
if (-not $source.Contains('test_only_non_authorizing') -or
        -not $source.Contains('Test fixtures cannot authorize a family launch') -or
        -not $source.Contains('TestFixturePath is permitted only with PreflightOnly')) {
    throw 'Synthetic qualification fixtures are not confined to non-authorizing preflight.'
}
if ($source.IndexOf('$addPath =') -gt $source.IndexOf('$addPath +=') -or
        -not $source.Contains(",'-begin')")) {
    throw 'Clean Sources must be added before the rebuilt overlay is forced to path begin.'
}
Write-Output 'toyRoadLauncherTest: PASS'
