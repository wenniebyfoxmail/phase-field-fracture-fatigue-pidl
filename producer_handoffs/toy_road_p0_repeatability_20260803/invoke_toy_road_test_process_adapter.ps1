param(
    [Parameter(Mandatory = $true)][string]$ExecutionLockPath,
    [Parameter(Mandatory = $true)][string]$MeasurementFixturePath,
    [Parameter(Mandatory = $true)][string]$MeasurementReceiptPath,
    [Parameter(Mandatory = $true)][string]$InvocationRecordPath,
    [Parameter(Mandatory = $true)][string]$BatchCommandBase64,
    [ValidateRange(0,10000)][int]$DelayMilliseconds = 0
)

$ErrorActionPreference = 'Stop'

function Read-PlainJson([string]$Path, [string]$Label) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Label is missing."
    }
    $item = Get-Item -LiteralPath $Path -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "$Label must not be a link or reparse point."
    }
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Write-NewJson([string]$Path, [object]$Value) {
    $bytes = (New-Object Text.UTF8Encoding($false)).GetBytes(
        ($Value | ConvertTo-Json -Depth 30 -Compress))
    $stream = $null
    try {
        $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew,
            [IO.FileAccess]::Write, [IO.FileShare]::None)
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    } finally {
        if ($null -ne $stream) { $stream.Dispose() }
    }
}

function Get-FileSha256([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

$lock = Read-PlainJson $ExecutionLockPath 'Execution lock'
if ([string]$lock.authorization_scope -cne 'test_only_non_authorizing') {
    throw 'The sealed test adapter accepts only test_only_non_authorizing locks.'
}
$fixture = Read-PlainJson $MeasurementFixturePath 'Runtime measurement fixture'
foreach ($name in @('release','update','version','computer','executable_sha256','blas','lapack')) {
    if ([string]$fixture.matlab.$name -cne [string]$lock.runtime_expectations.matlab.$name) {
        throw "Runtime measurement fixture differs from the lock: $name"
    }
}
foreach ($name in @('initial','AMOR','AT1_HISTORY_FATIGUE','cholmod2')) {
    if ([string]$fixture.binary_sha256.$name -cne
            [string]$lock.runtime_expectations.binary_sha256.$name) {
        throw "Runtime binary measurement fixture differs from the lock: $name"
    }
}

try {
    $batch = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($BatchCommandBase64))
} catch {
    throw 'Batch command is not valid sealed UTF-8 base64 data.'
}
$bridgeMatches = [regex]::Matches($batch, 'run_toy_road_runtime_bridge\s*\(')
if ($bridgeMatches.Count -ne 1 -or $batch -match '(?<!run_toy_road_runtime_bridge;)main_toy_road_family_case\s*[;(]') {
    throw 'Test adapter requires exactly one runtime bridge and no direct producer call.'
}
$pathMatches = [regex]::Matches($batch, "addpath\('(?<path>(?:''|[^'])*)','-begin'\)")
if ($pathMatches.Count -ne 8) {
    throw 'Batch command does not contain the eight explicit -begin path operations.'
}
$simulated = New-Object Collections.Generic.List[string]
foreach ($match in $pathMatches) {
    $value = $match.Groups['path'].Value.Replace("''", "'").Replace('/', '\')
    $simulated.Insert(0, [IO.Path]::GetFullPath($value).TrimEnd('\','/'))
}
$expectedPaths = @($lock.runtime_expectations.matlab.absolute_path_order | ForEach-Object {
    [IO.Path]::GetFullPath([string]$_).TrimEnd('\','/')
})
if (($simulated -join "`n") -cne ($expectedPaths -join "`n")) {
    throw 'Generated MATLAB command has the wrong final absolute path precedence.'
}

$measurement = [ordered]@{
    schema_version = 'toy_road_runtime_measurement_v1'
    protocol_version = [string]$lock.protocol_version
    authorization_scope = 'test_only_non_authorizing'
    status = 'PASS'
    producer_entrypoint_authorized = $false
    execution_input_lock_sha256 = Get-FileSha256 $ExecutionLockPath
    matlab = [ordered]@{
        release = [string]$fixture.matlab.release
        update = [string]$fixture.matlab.update
        version = [string]$fixture.matlab.version
        computer = [string]$fixture.matlab.computer
        executable_sha256 = [string]$fixture.matlab.executable_sha256
        blas = [string]$fixture.matlab.blas
        lapack = [string]$fixture.matlab.lapack
        absolute_path_order = @($simulated)
    }
    binary_sha256 = $fixture.binary_sha256
}
Write-NewJson $MeasurementReceiptPath $measurement
$batchBytes = (New-Object Text.UTF8Encoding($false)).GetBytes($batch)
$hasher = [Security.Cryptography.SHA256]::Create()
try {
    $batchSha256 = ([BitConverter]::ToString($hasher.ComputeHash($batchBytes))).Replace('-','').ToLowerInvariant()
} finally {
    $hasher.Dispose()
}
Write-NewJson $InvocationRecordPath ([ordered]@{
    schema_version = 'toy_road_test_process_adapter_record_v1'
    authorization_scope = 'test_only_non_authorizing'
    status = 'PASS'
    invocation_count = 1
    runtime_bridge_call_count = 1
    producer_entrypoint_called = $false
    batch_sha256 = $batchSha256
    absolute_path_order = @($simulated)
    measurement_receipt_sha256 = Get-FileSha256 $MeasurementReceiptPath
})
if ($DelayMilliseconds -gt 0) {
    Start-Sleep -Milliseconds $DelayMilliseconds
}
