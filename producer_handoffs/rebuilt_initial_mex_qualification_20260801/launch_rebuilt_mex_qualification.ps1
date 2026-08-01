param(
    [Parameter(Mandatory = $true)][string]$GripfithRoot,
    [Parameter(Mandatory = $true)][string]$ParentRoot,
    [Parameter(Mandatory = $true)][string]$ParentLockPath,
    [Parameter(Mandatory = $true)][string]$OutputRoot,
    [switch]$ProcessGateTestOnly,
    [string]$TestProcessInventoryPath = ''
)

$ErrorActionPreference = 'Stop'
$HandoffDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeLockPath = Join-Path $HandoffDir 'RUNTIME_LOCK.json'
$RuntimeRoot = Join-Path $HandoffDir 'runtime'
$Q2LockPath = Join-Path $HandoffDir 'Q2_INPUT_LOCK.json'
$EvidenceLockPath = Join-Path $HandoffDir 'QUALIFICATION_EVIDENCE_LOCK.json'
$Q1Root = Join-Path $OutputRoot 'Q1'
$Q2Root = Join-Path $OutputRoot 'Q2'
$FamilyReceiptPath = Join-Path $OutputRoot 'FAMILY_QUALIFICATION_RECEIPT.json'

function ConvertTo-MatlabLiteral([string]$Value) {
    return "'" + $Value.Replace('\', '/').Replace("'", "''") + "'"
}

function Invoke-MatlabStage([string]$Name, [string]$Expression) {
    & matlab -batch $Expression
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with MATLAB exit code $LASTEXITCODE."
    }
}

function Assert-NoRunningExperiment([object[]]$Inventory, [string]$Stage) {
    $blocked = @($Inventory | Where-Object {
        $name = [string]$_.name
        $commandLine = [string]$_.command_line
        $name -match '(?i)^matlab(\.exe)?$' -or
        $name -match '(?i)^(abaqus|ansys|comsol|femsolver)(\.exe)?$' -or
        $commandLine -match '(?i)(main_toy_to_road_case|solve_toy_to_road_case|run_q2_parent_cycle1_replay)'
    })
    if ($blocked.Count -gt 0) {
        throw "Refusing qualification $Stage while a MATLAB/FEM experiment is active."
    }
}

function Get-ProcessInventory {
    return @(Get-CimInstance Win32_Process | ForEach-Object {
        [ordered]@{ name = $_.Name; process_id = $_.ProcessId; command_line = $_.CommandLine }
    })
}

if ($ProcessGateTestOnly) {
    if ([string]::IsNullOrWhiteSpace($TestProcessInventoryPath)) {
        throw 'ProcessGateTestOnly requires a controlled process inventory.'
    }
    $controlled = Get-Content -LiteralPath $TestProcessInventoryPath -Raw | ConvertFrom-Json
    Assert-NoRunningExperiment @($controlled.before_q1) 'before Q1'
    Assert-NoRunningExperiment @($controlled.before_q2) 'before Q2'
    Write-Output 'Qualification process gates passed.'
    return
}
if (-not [string]::IsNullOrWhiteSpace($TestProcessInventoryPath)) {
    throw 'Test process inventory is forbidden for production qualification.'
}

if (Test-Path -LiteralPath $OutputRoot) {
    throw "Refusing to overwrite qualification output root: $OutputRoot"
}
Assert-NoRunningExperiment (Get-ProcessInventory) 'before Q1'
[IO.Directory]::CreateDirectory($OutputRoot) | Out-Null
try {
    $addHandoff = "addpath(" + (ConvertTo-MatlabLiteral $HandoffDir) + ")"
    $q1Config = "struct('output_root'," + (ConvertTo-MatlabLiteral $Q1Root) +
        ",'runtime_lock_path'," + (ConvertTo-MatlabLiteral $RuntimeLockPath) +
        ",'runtime_root'," + (ConvertTo-MatlabLiteral $RuntimeRoot) +
        ",'source_root'," + (ConvertTo-MatlabLiteral $GripfithRoot) + ")"
    Invoke-MatlabStage 'Q1 qualification' "$addHandoff;run_q1_initial_mex_qualification($q1Config);"
    if (-not (Test-Path -LiteralPath (Join-Path $Q1Root 'Q1_RECEIPT.json') -PathType Leaf)) {
        throw 'Q1 completed without publishing its passing receipt; Q2 is refused.'
    }
    Assert-NoRunningExperiment (Get-ProcessInventory) 'before Q2'

    $q2Config = "struct('output_root'," + (ConvertTo-MatlabLiteral $Q2Root) +
        ",'parent_root'," + (ConvertTo-MatlabLiteral $ParentRoot) +
        ",'parent_lock_path'," + (ConvertTo-MatlabLiteral $ParentLockPath) +
        ",'runtime_lock_path'," + (ConvertTo-MatlabLiteral $RuntimeLockPath) +
        ",'runtime_root'," + (ConvertTo-MatlabLiteral $RuntimeRoot) +
        ",'source_root'," + (ConvertTo-MatlabLiteral $GripfithRoot) + ")"
    Invoke-MatlabStage 'Q2 qualification' "$addHandoff;run_q2_parent_cycle1_replay($q2Config);"
    if (Test-Path -LiteralPath (Join-Path $Q2Root 'Q2_PARENT_BLOCKER.json') -PathType Leaf) {
        throw 'Q2 parent evidence is blocked; no Q2 solve or family launch is authorized.'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $Q2Root 'Q2_RESULT.json') -PathType Leaf)) {
        throw 'Q2 completed without a passing result; family launch is refused.'
    }
    if (-not (Test-Path -LiteralPath $EvidenceLockPath -PathType Leaf)) {
        throw 'QUALIFICATION_EVIDENCE_LOCK.json is not sealed; family receipt is refused.'
    }

    $validation = "$addHandoff;validate_qualification_receipts(" +
        (ConvertTo-MatlabLiteral $OutputRoot) + ',' +
        (ConvertTo-MatlabLiteral $RuntimeLockPath) + ',' +
        (ConvertTo-MatlabLiteral $RuntimeRoot) + ',' +
        (ConvertTo-MatlabLiteral $GripfithRoot) + ',' +
        (ConvertTo-MatlabLiteral $Q2LockPath) + ',' +
        (ConvertTo-MatlabLiteral $ParentLockPath) + ',' +
        (ConvertTo-MatlabLiteral $ParentRoot) + ',' +
        (ConvertTo-MatlabLiteral $FamilyReceiptPath) + ');'
    Invoke-MatlabStage 'Qualification receipt validation' $validation
} catch {
    throw
}

if (-not (Test-Path -LiteralPath $FamilyReceiptPath -PathType Leaf)) {
    throw 'Qualification validation did not publish its family receipt.'
}
$receiptBytes = [IO.File]::ReadAllBytes($FamilyReceiptPath)
$probePath = Join-Path $OutputRoot '.receipt-create-new-probe'
$stream = [IO.File]::Open($probePath, [IO.FileMode]::CreateNew,
    [IO.FileAccess]::Write, [IO.FileShare]::None)
try {
    $stream.Write($receiptBytes, 0, 0)
} finally {
    $stream.Dispose()
    Remove-Item -LiteralPath $probePath -Force
}
Write-Output "Qualification passed and sealed: $FamilyReceiptPath"
