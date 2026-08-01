$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$launcher = Join-Path $root 'launch_rebuilt_mex_qualification.ps1'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) {
    throw 'RED: qualification launcher is missing.'
}
$source = Get-Content -LiteralPath $launcher -Raw
$required = @(
    'Q1', 'Q2', 'FAMILY_QUALIFICATION_RECEIPT.json',
    'run_q1_initial_mex_qualification', 'run_q2_parent_cycle1_replay',
    'validate_qualification_receipts', '[IO.FileMode]::CreateNew'
)
foreach ($token in $required) {
    if (-not $source.Contains($token)) {
        throw "Qualification launcher contract is missing: $token"
    }
}
$q1Index = $source.IndexOf('run_q1_initial_mex_qualification')
$q2Index = $source.IndexOf('run_q2_parent_cycle1_replay')
if ($q1Index -lt 0 -or $q2Index -le $q1Index) {
    throw 'Q1 and Q2 are not strictly ordered.'
}
if (($source | Select-String -Pattern '& matlab' -AllMatches).Matches.Count -ne 1 -or
        ($source | Select-String -Pattern 'Invoke-MatlabStage ' -AllMatches).Matches.Count -lt 3) {
    throw 'Q1, Q2, and receipt validation must use isolated MATLAB processes.'
}
Write-Output 'rebuiltMexQualificationLauncherTest: PASS'
