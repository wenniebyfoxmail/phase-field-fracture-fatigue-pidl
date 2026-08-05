param(
    [Parameter(Mandatory = $true)][string]$BatchCommandBase64,
    [Parameter(Mandatory = $true)][string]$DiagnosticReceiptFixturePath,
    [Parameter(Mandatory = $true)][string]$DiagnosticReceiptPath,
    [Parameter(Mandatory = $true)][string]$InvocationRecordPath,
    [Parameter(Mandatory = $true)][string]$StdoutStderrPath,
    [int]$ExitCode = 0
)

$ErrorActionPreference = 'Stop'
$batch = (New-Object Text.UTF8Encoding($false)).GetString(
    [Convert]::FromBase64String($BatchCommandBase64))
if (([regex]::Matches($batch,'run_toy_road_runtime_diagnostic\s*\(')).Count -ne 1) {
    throw 'D1 adapter requires exactly one diagnostic probe call.'
}
$forbidden = @('main_'+'toy_road_family_case','solve_'+'toy_road_family_case',
    'recover_'+'toy_road_family_state')
foreach ($name in $forbidden) {
    if ($batch.Contains($name)) { throw 'D1 adapter rejected a non-diagnostic batch.' }
}

function Write-CreateNew([string]$Path,[byte[]]$Bytes) {
    $stream=$null
    try {
        $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write,[IO.FileShare]::None)
        $stream.Write($Bytes,0,$Bytes.Length)
        $stream.Flush($true)
    } finally { if($null -ne $stream){$stream.Dispose()} }
}

$utf8=New-Object Text.UTF8Encoding($false)
$batchSha=[BitConverter]::ToString(
    [Security.Cryptography.SHA256]::Create().ComputeHash($utf8.GetBytes($batch))).
    Replace('-','').ToLowerInvariant()
$record=[ordered]@{
    schema_version='toy_road_d1_test_adapter_invocation_v1'
    authorization_scope='test_only_non_authorizing'
    invocation_count=1
    diagnostic_invocation_count=1
    producer_invocation_count=0
    fem_cycle_count=0
    batch_sha256=$batchSha
}
Write-CreateNew $InvocationRecordPath $utf8.GetBytes(
    ($record|ConvertTo-Json -Depth 10 -Compress))
Write-CreateNew $StdoutStderrPath $utf8.GetBytes(
    "D1 test adapter invocation; no MATLAB process started.`n")
if($ExitCode -ne 0){exit $ExitCode}
if(-not (Test-Path -LiteralPath $DiagnosticReceiptFixturePath -PathType Leaf)){
    throw 'D1 diagnostic receipt fixture is missing.'
}
Write-CreateNew $DiagnosticReceiptPath ([IO.File]::ReadAllBytes($DiagnosticReceiptFixturePath))
exit 0
