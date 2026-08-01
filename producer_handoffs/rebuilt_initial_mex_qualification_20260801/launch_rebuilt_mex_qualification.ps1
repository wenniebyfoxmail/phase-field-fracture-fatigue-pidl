param(
    [Parameter(Mandatory = $true)][string]$GripfithRoot,
    [Parameter(Mandatory = $true)][string]$ParentRoot,
    [Parameter(Mandatory = $true)][string]$ParentLockPath,
    [Parameter(Mandatory = $true)][string]$OutputRoot
)

$ErrorActionPreference = 'Stop'
$HandoffDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeLockPath = Join-Path $HandoffDir 'RUNTIME_LOCK.json'
$RuntimeRoot = Join-Path $HandoffDir 'runtime'
$Q2LockPath = Join-Path $HandoffDir 'Q2_INPUT_LOCK.json'
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

if (Test-Path -LiteralPath $OutputRoot) {
    throw "Refusing to overwrite qualification output root: $OutputRoot"
}
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

    $validation = "$addHandoff;validate_qualification_receipts(" +
        (ConvertTo-MatlabLiteral $OutputRoot) + ',' +
        (ConvertTo-MatlabLiteral $RuntimeLockPath) + ',' +
        (ConvertTo-MatlabLiteral $Q2LockPath) + ',' +
        (ConvertTo-MatlabLiteral $ParentLockPath) + ',' +
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
