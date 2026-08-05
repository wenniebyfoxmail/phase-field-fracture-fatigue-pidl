param(
    [Parameter(Mandatory = $true)][string]$SourceExecutionLockPath,
    [Parameter(Mandatory = $true)][string]$RelocationPath,
    [Parameter(Mandatory = $true)][string]$DiagnosticLockPath,
    [Parameter(Mandatory = $true)][string]$TransformationPath,
    [Parameter(Mandatory = $true)][string]$PythonExecutable,
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F]{64}$')][string]$ApprovedPythonSha256
)

$ErrorActionPreference = 'Stop'
$scriptPath = [IO.Path]::GetFullPath($MyInvocation.MyCommand.Path)
$handoffDir = Split-Path -Parent $scriptPath
$protocol = Join-Path $handoffDir 'toy_road_d1_protocol.py'
$python = [IO.Path]::GetFullPath($PythonExecutable)
$sourceLock = [IO.Path]::GetFullPath($SourceExecutionLockPath)
$relocation = [IO.Path]::GetFullPath($RelocationPath)
$diagnostic = [IO.Path]::GetFullPath($DiagnosticLockPath)
$transformation = [IO.Path]::GetFullPath($TransformationPath)

foreach ($entry in @(
        @{ Path = $python; Label = 'Python executable' },
        @{ Path = $protocol; Label = 'D1 protocol' },
        @{ Path = $sourceLock; Label = 'source execution lock' },
        @{ Path = $relocation; Label = 'diagnostic relocation' }
    )) {
    if (-not (Test-Path -LiteralPath $entry.Path -PathType Leaf)) {
        throw "$($entry.Label) is missing."
    }
}
if ((Get-FileHash -LiteralPath $python -Algorithm SHA256).Hash.ToLowerInvariant() -cne
        $ApprovedPythonSha256.ToLowerInvariant()) {
    throw 'Python executable SHA-256 differs from the approved identity.'
}
if (Test-Path -LiteralPath $diagnostic) {
    throw 'D1 diagnostic lock output already exists.'
}
if (Test-Path -LiteralPath $transformation) {
    throw 'D1 transformation output already exists.'
}
if ((Split-Path -Parent $diagnostic) -cne (Split-Path -Parent $transformation)) {
    throw 'D1 lock and transformation must share one evidence directory.'
}

$output = & $python $protocol --derive-lock $sourceLock $relocation `
    $diagnostic $transformation 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "D1 diagnostic lock derivation failed: $($output -join ' ')"
}
Write-Output ([string]@($output)[-1])
