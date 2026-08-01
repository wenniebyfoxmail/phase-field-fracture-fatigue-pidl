$ErrorActionPreference = 'Stop'
$handoff = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$launcherPath = Join-Path $handoff 'launch_toy_road_case.ps1'
$source = Get-Content -LiteralPath $launcherPath -Raw
[scriptblock]::Create($source) | Out-Null

$required = @(
    '[string]$QualificationRoot',
    'FAMILY_QUALIFICATION_RECEIPT.json',
    'FAMILY_RUNTIME_RECEIPT.json',
    'Assert-FamilySequence',
    'Previous family member failed terminal validation',
    'Family runtime or qualification changed between cases',
    'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db',
    'Legacy crashing initial MEX is rejected',
    'New-RuntimeOverlay',
    '$runtimeOverlay.root,',
    'toy_road_launch_receipt_v2'
)
foreach ($token in $required) {
    if (-not $source.Contains($token)) {
        throw "Toy-road launcher qualification contract is missing: $token"
    }
}
if ($source.IndexOf('$runtimeOverlay.root,') -gt
        $source.IndexOf("(Join-Path `$GripfithRoot 'Sources')")) {
    throw 'The rebuilt runtime overlay is not ordered before clean source paths.'
}
Write-Output 'toyRoadLauncherTest: PASS'
