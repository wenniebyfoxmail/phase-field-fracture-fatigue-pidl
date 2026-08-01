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
    'validate_qualification_receipts', '[IO.FileMode]::CreateNew',
    'QUALIFICATION_EVIDENCE_LOCK.json',
    'Assert-NoRunningExperiment', 'before_q1', 'before_q2'
)
foreach ($token in $required) {
    if (-not $source.Contains($token)) {
        throw "Qualification launcher contract is missing: $token"
    }
}
$q1Index = $source.LastIndexOf('run_q1_initial_mex_qualification')
$q2Index = $source.LastIndexOf('run_q2_parent_cycle1_replay')
if ($q1Index -lt 0 -or $q2Index -le $q1Index) {
    throw 'Q1 and Q2 are not strictly ordered.'
}
if (($source | Select-String -Pattern '& matlab' -AllMatches).Matches.Count -ne 1 -or
        ($source | Select-String -Pattern 'Invoke-MatlabStage ' -AllMatches).Matches.Count -lt 3) {
    throw 'Q1, Q2, and receipt validation must use isolated MATLAB processes.'
}

function Invoke-GateFixture([object]$BeforeQ1, [object]$BeforeQ2) {
    $fixturePath = Join-Path $env:TEMP ("qualification-process-" + [Guid]::NewGuid() + '.json')
    @{ before_q1 = @($BeforeQ1); before_q2 = @($BeforeQ2) } |
        ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $fixturePath -Encoding UTF8
    try {
        $oldPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $launcher `
            -GripfithRoot 'C:\unused' -ParentRoot 'C:\unused' `
            -ParentLockPath 'C:\unused' -OutputRoot 'C:\unused' `
            -ProcessGateTestOnly -TestProcessInventoryPath $fixturePath 2>&1
        $exitCode = $LASTEXITCODE
        $ErrorActionPreference = $oldPreference
        return [ordered]@{ exit = $exitCode; output = ($output -join "`n") }
    } finally {
        $ErrorActionPreference = 'Stop'
        Remove-Item -LiteralPath $fixturePath -Force -ErrorAction SilentlyContinue
    }
}

$matlab = @{ name = 'MATLAB.exe'; process_id = 4242; command_line = 'matlab -batch other_experiment' }
$beforeQ1 = Invoke-GateFixture $matlab @()
if ($beforeQ1.exit -eq 0 -or -not $beforeQ1.output.Contains('before Q1')) {
    throw 'Existing MATLAB/FEM process was not rejected before Q1.'
}
$beforeQ2 = Invoke-GateFixture @() $matlab
if ($beforeQ2.exit -eq 0 -or -not $beforeQ2.output.Contains('before Q2')) {
    throw 'Existing MATLAB/FEM process was not rejected before Q2.'
}
$finishedQ1 = Invoke-GateFixture @() @()
if ($finishedQ1.exit -ne 0) {
    throw 'A finished Q1 process was incorrectly treated as active before Q2.'
}
Write-Output 'rebuiltMexQualificationLauncherTest: PASS'
