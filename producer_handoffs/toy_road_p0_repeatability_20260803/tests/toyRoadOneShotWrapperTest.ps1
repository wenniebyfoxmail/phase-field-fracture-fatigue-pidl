$ErrorActionPreference = 'Stop'
$HandoffDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Generator = Join-Path $HandoffDir 'new_toy_road_p0_one_shot_wrapper.ps1'
$Root = Join-Path $env:TEMP ('toy-road-p0-wrapper-' + [Guid]::NewGuid().ToString('N'))

try {
    $source = Join-Path $Root 'source'
    $launcherDir = Join-Path $source `
        'producer_handoffs\toy_road_p0_repeatability_20260803'
    [IO.Directory]::CreateDirectory($launcherDir) | Out-Null
    $fakeLauncher = @'
param(
    [string]$Role, [string]$SourceRoot, [string]$GripfithRoot,
    [string]$QualificationRoot, [string]$InputAssetsRoot,
    [string]$EvidenceRoot, [string]$OutputRoot, [string]$WorkRoot,
    [string]$TempRoot, [string]$TmpRoot, [string]$PrefRoot,
    [string]$CacheRoot, [string]$ExpectedSourceCommit,
    [string]$ReceiptPath, [string]$ExecutionLockPath
)
if ($Role -cne 'P0_parent') { throw 'Role was not fixed to P0_parent.' }
if ($ExpectedSourceCommit -cne $env:TOY_ROAD_TEST_EXPECTED_COMMIT) {
    throw 'Source commit was not fixed by the generated wrapper.'
}
[IO.File]::WriteAllText($env:TOY_ROAD_TEST_MARKER, $Role)
'@
    $launcherPath = Join-Path $launcherDir 'launch_toy_road_family_case.ps1'
    [IO.File]::WriteAllText($launcherPath, $fakeLauncher,
        (New-Object Text.UTF8Encoding($false)))
    & git -C $source init --quiet
    & git -C $source config user.email 'toy-road-test@example.invalid'
    & git -C $source config user.name 'Toy Road Test'
    & git -C $source add .
    & git -C $source commit --quiet -m 'fixture'
    $commit = ([string](& git -C $source rev-parse HEAD)).Trim().ToLowerInvariant()

    $wrapper = Join-Path $Root 'invoke-p0-once.ps1'
    & $Generator -SealedSourceRoot $source -ExpectedSourceCommit $commit `
        -OutputPath $wrapper
    if (-not (Test-Path -LiteralPath $wrapper -PathType Leaf)) {
        throw 'Generator did not create the wrapper.'
    }
    $wrapperText = Get-Content -LiteralPath $wrapper -Raw
    if ($wrapperText -notmatch [regex]::Escape($commit) -or
            $wrapperText -notmatch "FixedRole = 'P0_parent'") {
        throw 'Generated wrapper is not fixed to the sealed commit and P0_parent.'
    }

    $common = @{
        GripfithRoot = $source; QualificationRoot = $source
        InputAssetsRoot = $source; EvidenceRoot = $source
        OutputRoot = (Join-Path $Root 'out'); WorkRoot = (Join-Path $Root 'work')
        TempRoot = (Join-Path $Root 'temp'); TmpRoot = (Join-Path $Root 'tmp')
        PrefRoot = (Join-Path $Root 'pref'); CacheRoot = (Join-Path $Root 'cache')
        ReceiptPath = (Join-Path $Root 'receipt.json')
        ExecutionLockPath = (Join-Path $Root 'lock.json')
    }
    $preflight = Join-Path $Root 'preflight.json'
    [IO.File]::WriteAllText($preflight,
        '{"authorization_scope":"preflight_only_non_authorizing"}')
    try {
        & $wrapper -ExecutionAuthorizationPath $preflight @common
        throw 'Generated wrapper accepted a preflight receipt.'
    } catch {
        if ($_.Exception.Message -notmatch 'preflight') { throw }
    }

    $authorization = Join-Path $Root 'authorization.json'
    [IO.File]::WriteAllText($authorization, (@{
        status = 'P0_PARENT_EXECUTION_AUTHORIZED'
        authorization_scope = 'production_authorized_p0_parent_one_shot'
        role = 'P0_parent'
        source_commit = $commit
        production_execution_authorized = $true
        dedicated_producer_attested = $true
        machine_name = 'CITPC12'
        exclusive_control = 'no_manual_or_agent_matlab_fem'
        authorization_id = 'wrapper-test-authorization'
    } | ConvertTo-Json -Compress))
    $env:TOY_ROAD_TEST_EXPECTED_COMMIT = $commit
    $env:TOY_ROAD_TEST_MARKER = Join-Path $Root 'invoked.txt'
    & $wrapper -ExecutionAuthorizationPath $authorization @common
    if ((Get-Content -LiteralPath $env:TOY_ROAD_TEST_MARKER -Raw) -cne 'P0_parent') {
        throw 'Generated wrapper did not invoke the fixed P0_parent launcher.'
    }
    try {
        & $wrapper -ExecutionAuthorizationPath $authorization @common
        throw 'Generated wrapper allowed authorization reuse.'
    } catch {
        if ($_.Exception.Message -notmatch 'exist|CreateNew|used by another process') {
            throw
        }
    }
    Write-Output 'toyRoadOneShotWrapperTest: PASS'
} finally {
    Remove-Item Env:TOY_ROAD_TEST_EXPECTED_COMMIT -ErrorAction SilentlyContinue
    Remove-Item Env:TOY_ROAD_TEST_MARKER -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $Root -Recurse -Force -ErrorAction SilentlyContinue
}
