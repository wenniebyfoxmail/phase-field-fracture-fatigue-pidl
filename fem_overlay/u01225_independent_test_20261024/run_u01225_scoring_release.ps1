<#
Custodian-only, one-way scorer handoff for the U0.1225 strict-test archive.

This script does not score, train, inspect a target array, or print an outcome.
It can run only from the custody-protected launcher after a sealed terminal
receipt. It copies the opaque sealed archive into a pre-provisioned scorer root,
then removes the custodian's ordinary ACL grant from that transfer root.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$CustodyRoot,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$ScoringRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ManifestName = 'SHA256SUMS.txt'
$PolicyName = 'custody_policy.json'
$ReleaseScriptName = 'run_u01225_scoring_release.ps1'
$CustodianScriptName = 'run_u01225_custodian.ps1'

function Stop-Release([string]$Code) {
    throw [System.InvalidOperationException]::new($Code)
}

function Get-Sha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Stop-Release 'SCORING_RELEASE_EXPECTED_FILE_MISSING'
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-CanonicalPath([string]$Path) {
    return [System.IO.Path]::GetFullPath($Path).TrimEnd([char[]]@('\', '/'))
}

function Get-ContainedPath([string]$Root, [string]$Relative) {
    if ([System.IO.Path]::IsPathRooted($Relative) -or
        $Relative -match '(^|[\\/])\.\.([\\/]|$)' -or $Relative -match ':') {
        Stop-Release 'SCORING_RELEASE_INVALID_RELATIVE_PATH'
    }
    $rootCanonical = Get-CanonicalPath $Root
    $candidate = Get-CanonicalPath (Join-Path $rootCanonical $Relative)
    $prefix = $rootCanonical + [System.IO.Path]::DirectorySeparatorChar
    if (-not $candidate.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        Stop-Release 'SCORING_RELEASE_RELATIVE_PATH_ESCAPES_ROOT'
    }
    return $candidate
}

function ConvertTo-CanonicalPrincipal([string]$Identity) {
    if ($Identity -ieq 'SYSTEM') {
        return 'NT AUTHORITY\SYSTEM'
    }
    return $Identity
}

function Test-AssignedIdentity($Value) {
    $text = [string]$Value
    return -not ([string]::IsNullOrWhiteSpace($text) -or $text -match '^__')
}

function Test-ExactStringArray($Actual, [string[]]$Expected) {
    $actualValues = @($Actual | ForEach-Object { [string]$_ })
    if ($actualValues.Count -ne $Expected.Count) {
        return $false
    }
    for ($index = 0; $index -lt $Expected.Count; $index += 1) {
        if ($actualValues[$index] -ne $Expected[$index]) {
            return $false
        }
    }
    return $true
}

function Read-Json([string]$Path, [string]$ErrorCode) {
    try {
        return ([System.IO.File]::ReadAllText($Path) | ConvertFrom-Json)
    }
    catch {
        Stop-Release $ErrorCode
    }
}

function Get-VerifiedManifestEntries([string]$Root, [string]$ExpectedManifestHash) {
    $manifestPath = Join-Path $Root $ManifestName
    if ($ExpectedManifestHash -notmatch '^[0-9a-f]{64}$' -or
        (Get-Sha256 $manifestPath) -ne $ExpectedManifestHash) {
        Stop-Release 'SCORING_RELEASE_MANIFEST_HASH_MISMATCH'
    }
    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $entries = @()
    foreach ($line in [System.IO.File]::ReadAllLines($manifestPath)) {
        $match = [System.Text.RegularExpressions.Regex]::Match($line, '^([0-9a-fA-F]{64})  (.+)$')
        if (-not $match.Success) {
            Stop-Release 'SCORING_RELEASE_MANIFEST_FORMAT'
        }
        $relative = $match.Groups[2].Value.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        if ($relative -eq $ManifestName -or $relative -eq $CustodianScriptName -or
            -not $seen.Add($relative)) {
            Stop-Release 'SCORING_RELEASE_MANIFEST_MEMBER'
        }
        $path = Get-ContainedPath $Root $relative
        $item = Get-Item -LiteralPath $path -Force -ErrorAction Stop
        if ($item.PSIsContainer -or ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -or
            (Get-Sha256 $path) -ne $match.Groups[1].Value.ToLowerInvariant()) {
            Stop-Release 'SCORING_RELEASE_MANIFEST_MEMBER_MISMATCH'
        }
        $entries += [PSCustomObject]@{ Relative = $relative; Sha256 = $match.Groups[1].Value.ToLowerInvariant() }
    }
    if ($entries.Count -eq 0 -or -not (@($entries | Where-Object { $_.Relative -eq $ReleaseScriptName }))) {
        Stop-Release 'SCORING_RELEASE_WRAPPER_NOT_MANIFESTED'
    }
    return $entries
}

function Assert-ArchiveManifest([string]$ArchiveRoot, [string]$ExpectedManifestHash, [string]$Scope) {
    $archiveItem = Get-Item -LiteralPath $ArchiveRoot -Force -ErrorAction Stop
    if (-not $archiveItem.PSIsContainer -or
        ($archiveItem.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        Stop-Release ("SCORING_RELEASE_{0}_ARCHIVE_ROOT_INVALID" -f $Scope)
    }
    $rootCanonical = Get-CanonicalPath $ArchiveRoot
    $manifestPath = Get-ContainedPath $rootCanonical 'SHA256SUMS.txt'
    if ($ExpectedManifestHash -notmatch '^[0-9a-f]{64}$' -or
        (Get-Sha256 $manifestPath) -ne $ExpectedManifestHash) {
        Stop-Release ("SCORING_RELEASE_{0}_ARCHIVE_MANIFEST_HASH_MISMATCH" -f $Scope)
    }
    $members = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($line in [System.IO.File]::ReadAllLines($manifestPath)) {
        $match = [System.Text.RegularExpressions.Regex]::Match($line, '^([0-9a-fA-F]{64})  (.+)$')
        if (-not $match.Success) {
            Stop-Release ("SCORING_RELEASE_{0}_ARCHIVE_MANIFEST_FORMAT" -f $Scope)
        }
        $relative = $match.Groups[2].Value.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        if ($relative -eq 'SHA256SUMS.txt' -or -not $members.Add($relative)) {
            Stop-Release ("SCORING_RELEASE_{0}_ARCHIVE_MANIFEST_MEMBER" -f $Scope)
        }
        $memberPath = Get-ContainedPath $rootCanonical $relative
        $member = Get-Item -LiteralPath $memberPath -Force -ErrorAction Stop
        if ($member.PSIsContainer -or
            ($member.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -or
            (Get-Sha256 $memberPath) -ne $match.Groups[1].Value.ToLowerInvariant()) {
            Stop-Release ("SCORING_RELEASE_{0}_ARCHIVE_MEMBER_HASH_MISMATCH" -f $Scope)
        }
    }
    if ($members.Count -eq 0) {
        Stop-Release ("SCORING_RELEASE_{0}_ARCHIVE_MANIFEST_EMPTY" -f $Scope)
    }
    foreach ($reparseItem in @(Get-ChildItem -LiteralPath $rootCanonical -Force -Recurse -Attributes ReparsePoint -ErrorAction Stop)) {
        Stop-Release ("SCORING_RELEASE_{0}_ARCHIVE_REPARSE_MEMBER" -f $Scope)
    }
    foreach ($actualMember in @(Get-ChildItem -LiteralPath $rootCanonical -Force -Recurse -File -ErrorAction Stop)) {
        $relative = $actualMember.FullName.Substring($rootCanonical.Length).TrimStart([char[]]@('\', '/'))
        if ($relative -ne 'SHA256SUMS.txt' -and -not $members.Contains($relative)) {
            Stop-Release ("SCORING_RELEASE_{0}_ARCHIVE_UNMANIFESTED_MEMBER" -f $Scope)
        }
    }
    return [PSCustomObject]@{
        ManifestSha256 = $ExpectedManifestHash
        MemberCount = $members.Count
    }
}

function Assert-ExclusiveAcl([string]$Path, [string[]]$AllowedIdentities, [string]$ExpectedOwnerIdentity, [string[]]$RequiredFullControl, [string]$Scope) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        Stop-Release ("SCORING_RELEASE_{0}_MISSING" -f $Scope)
    }
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        Stop-Release ("SCORING_RELEASE_{0}_REPARSE_POINT" -f $Scope)
    }
    $acl = Get-Acl -LiteralPath $Path
    if (-not $acl.AreAccessRulesProtected) {
        Stop-Release ("SCORING_RELEASE_{0}_INHERITS_ACCESS" -f $Scope)
    }
    $allowed = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($identity in $AllowedIdentities) {
        [void]$allowed.Add((ConvertTo-CanonicalPrincipal ([string]$identity)))
    }
    if ((ConvertTo-CanonicalPrincipal ([string]$acl.Owner)) -ne
        (ConvertTo-CanonicalPrincipal $ExpectedOwnerIdentity)) {
        Stop-Release ("SCORING_RELEASE_{0}_OWNER_MISMATCH" -f $Scope)
    }
    $fullControl = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($rule in $acl.Access) {
        $identity = ConvertTo-CanonicalPrincipal ([string]$rule.IdentityReference.Value)
        if (-not $allowed.Contains($identity) -or
            $rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow) {
            Stop-Release ("SCORING_RELEASE_{0}_ACL_NOT_EXCLUSIVE" -f $Scope)
        }
        if ($rule.FileSystemRights.ToString().Contains('FullControl')) {
            [void]$fullControl.Add($identity)
        }
    }
    foreach ($identity in $RequiredFullControl) {
        if (-not $fullControl.Contains((ConvertTo-CanonicalPrincipal ([string]$identity)))) {
            Stop-Release ("SCORING_RELEASE_{0}_REQUIRED_ACCESS_MISSING" -f $Scope)
        }
    }
}

function Set-TransferAcl([string]$Path, [string]$CustodianIdentity, [string]$ScorerIdentity) {
    $arguments = @(
        $Path,
        '/inheritance:r',
        '/grant:r',
        ("{0}:(OI)(CI)F" -f $CustodianIdentity),
        ("{0}:(OI)(CI)F" -f $ScorerIdentity),
        'SYSTEM:(OI)(CI)F',
        'BUILTIN\Administrators:(OI)(CI)F'
    )
    & icacls.exe @arguments | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Stop-Release 'SCORING_RELEASE_TRANSFER_ACL_APPLICATION_FAILED'
    }
    Assert-ExclusiveAcl -Path $Path -AllowedIdentities @($CustodianIdentity, $ScorerIdentity, 'NT AUTHORITY\SYSTEM', 'BUILTIN\Administrators') -ExpectedOwnerIdentity $CustodianIdentity -RequiredFullControl @($CustodianIdentity, $ScorerIdentity) -Scope 'TRANSFER_ROOT'
}

function Seal-ScorerAcl([string]$Path, [string]$CustodianIdentity, [string]$ScorerIdentity) {
    & icacls.exe $Path '/inheritance:r' '/grant:r' ("{0}:(OI)(CI)F" -f $ScorerIdentity) 'SYSTEM:(OI)(CI)F' 'BUILTIN\Administrators:(OI)(CI)F' '/remove:g' $CustodianIdentity '/T' | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Stop-Release 'SCORING_RELEASE_SCORER_ACL_APPLICATION_FAILED'
    }
    Assert-ExclusiveAcl -Path $Path -AllowedIdentities @($ScorerIdentity, 'NT AUTHORITY\SYSTEM', 'BUILTIN\Administrators') -ExpectedOwnerIdentity $CustodianIdentity -RequiredFullControl @($ScorerIdentity) -Scope 'SCORER_ROOT'
}

function Write-AtomicUtf8([string]$Path, [string]$Text) {
    $parent = Split-Path -LiteralPath $Path -Parent
    $temporary = Join-Path $parent (([System.Guid]::NewGuid().ToString('N')) + '.tmp')
    [System.IO.File]::WriteAllText($temporary, $Text, [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::Move($temporary, $Path)
}

function New-AtomicJson([string]$Path, $Object, [string]$ErrorCode) {
    $text = ($Object | ConvertTo-Json -Depth 10) + [Environment]::NewLine
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($text)
    try {
        $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    }
    catch {
        Stop-Release $ErrorCode
    }
    try {
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    }
    finally {
        $stream.Dispose()
    }
}

function Write-ScoringReleaseReceipt([string]$ReceiptDirectory, [string]$Status, [string]$TerminalReceiptHash, [string]$PolicyHash, [string]$EvidenceHash, [string]$ScoringProtocolHash, [string]$ReleaseLockHash, [string]$SourceArchiveManifestHash, [int]$SourceArchiveMembersVerified, [string]$TransferredArchiveManifestHash, [int]$TransferredArchiveMembersVerified, [datetime]$StartedUtc) {
    if (-not (Test-Path -LiteralPath $ReceiptDirectory -PathType Container)) {
        Stop-Release 'SCORING_RELEASE_RECEIPT_DIRECTORY_MISSING'
    }
    $receiptPath = Join-Path $ReceiptDirectory 'scoring_release_receipt.json'
    $sidecarPath = Join-Path $ReceiptDirectory 'scoring_release_receipt.sha256'
    if ((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $sidecarPath)) {
        Stop-Release 'SCORING_RELEASE_RECEIPT_ALREADY_EXISTS'
    }
    $receipt = [ordered]@{
        schema = 'fixed_weight_u01225_scoring_release_receipt_v1'
        release_status = $Status
        candidate_id = 'hard5_u01225_independent_test'
        split = 'independent_test'
        run_id = 'hard5_u01225_stage0b_597465a720694a6ea7001a8792de4189'
        terminal_receipt_sha256 = $TerminalReceiptHash
        policy_sha256 = $PolicyHash
        prelaunch_custody_evidence_sha256 = $EvidenceHash
        scoring_protocol_sha256 = $ScoringProtocolHash
        scoring_release_lock_sha256 = $ReleaseLockHash
        source_archive_manifest_sha256 = $SourceArchiveManifestHash
        source_archive_members_verified = $SourceArchiveMembersVerified
        transferred_archive_manifest_sha256 = $TransferredArchiveManifestHash
        transferred_archive_members_verified = $TransferredArchiveMembersVerified
        development_receives_raw_fields = $false
        development_receives_event_values = $false
        allowed_subsequent_publication = 'predeclared aggregate score report after isolated scoring'
        started_utc = $StartedUtc.ToString('o')
        completed_utc = [DateTime]::UtcNow.ToString('o')
    }
    Write-AtomicUtf8 $receiptPath (($receipt | ConvertTo-Json -Depth 10) + [Environment]::NewLine)
    Write-AtomicUtf8 $sidecarPath ((Get-Sha256 $receiptPath) + '  scoring_release_receipt.json' + [Environment]::NewLine)
}

$releaseLockCreated = $false
$startedUtc = [DateTime]::UtcNow
$receiptDirectory = $null
$terminalReceiptHash = $null
$policyHash = $null
$evidenceHash = $null
$scoringProtocolHash = $null
$releaseLockHash = $null
$sourceArchiveManifestHash = ''
$sourceArchiveMembersVerified = 0
$transferredArchiveMembersVerified = 0

try {
    $CustodyRoot = Get-CanonicalPath $CustodyRoot
    $ScoringRoot = Get-CanonicalPath $ScoringRoot
    $launcherRoot = Get-ContainedPath $CustodyRoot 'launcher'
    $expectedScriptPath = Get-ContainedPath $launcherRoot $ReleaseScriptName
    if ((Get-CanonicalPath $PSCommandPath) -ne $expectedScriptPath) {
        Stop-Release 'SCORING_RELEASE_EXECUTION_PATH_INVALID'
    }
    $policyPath = Get-ContainedPath $launcherRoot $PolicyName
    $manifestPath = Get-ContainedPath $launcherRoot $ManifestName
    $lockPath = Get-ContainedPath $CustodyRoot 'launch.lock.json'
    $terminalReceiptPath = Get-ContainedPath (Get-ContainedPath $CustodyRoot 'receipts') 'terminal_receipt.json'
    $terminalSidecarPath = Get-ContainedPath (Get-ContainedPath $CustodyRoot 'receipts') 'terminal_receipt.sha256'
    $policy = Read-Json $policyPath 'SCORING_RELEASE_POLICY_JSON_INVALID'
    $launchLock = Read-Json $lockPath 'SCORING_RELEASE_LAUNCH_LOCK_JSON_INVALID'
    $terminalReceipt = Read-Json $terminalReceiptPath 'SCORING_RELEASE_TERMINAL_RECEIPT_JSON_INVALID'
    $policyHash = Get-Sha256 $policyPath
    $manifestHash = Get-Sha256 $manifestPath
    $terminalReceiptHash = Get-Sha256 $terminalReceiptPath
    $sidecar = [System.IO.File]::ReadAllText($terminalSidecarPath).Trim()
    if ($sidecar -ne ($terminalReceiptHash + '  terminal_receipt.json')) {
        Stop-Release 'SCORING_RELEASE_TERMINAL_RECEIPT_SIDECAR_MISMATCH'
    }
    if ($policy.schema -ne 'fixed_weight_u01225_custody_policy_v1' -or
        $policy.policy_status -ne 'PRE_RESULT_CUSTODY_READY' -or
        $policy.strict_test_role_status -ne 'STRICT_TEST_CUSTODY_READY' -or
        $policy.candidate.candidate_id -ne 'hard5_u01225_independent_test' -or
        $policy.candidate.condition -ne 'U0.1225' -or
        $policy.candidate.run_id -ne 'hard5_u01225_stage0b_597465a720694a6ea7001a8792de4189' -or
        $policy.candidate.split -ne 'independent_test' -or
        $policy.candidate.split_unit -ne 'whole_parameter_condition' -or
        $policy.paths.custody_root -ne $CustodyRoot -or
        $policy.paths.launcher_relative -ne 'launcher' -or
        $policy.paths.archive_root_relative -ne 'archive_root' -or
        $policy.paths.receipt_relative -ne 'receipts' -or
        $policy.release.scoring_protocol.relative_path -ne 'scoring_protocol.json' -or
        $policy.release.scoring_protocol.status -ne 'PRECOMMITTED_NO_MODEL_OR_SCORE' -or
        $policy.release.scoring_protocol.sha256 -notmatch '^[0-9a-f]{64}$' -or
        $policy.release.scoring_release_wrapper.relative_path -ne $ReleaseScriptName -or
        $policy.release.scoring_release_wrapper.status -ne 'PRECOMMITTED_NO_SCORING_RELEASE' -or
        $policy.release.scoring_release_wrapper.sha256 -notmatch '^[0-9a-f]{64}$' -or
        $policy.release.scoring_transfer.scoring_parent_root -ne 'C:\q4runs\fixed_weight_scoring' -or
        $policy.release.scoring_transfer.scoring_root -ne 'C:\q4runs\fixed_weight_scoring\u01225_independent_test_20261024_v1' -or
        $policy.release.scoring_transfer.archive_relative -ne 'archive' -or
        $policy.release.scoring_transfer.release_lock_relative -ne 'scoring_release.lock.json' -or
        $policy.release.scoring_transfer.status -ne 'PRECOMMITTED_NO_SCORING_RELEASE') {
        Stop-Release 'SCORING_RELEASE_POLICY_BOUNDARY_INVALID'
    }
    $custodianIdentity = [string]$policy.custody.custodian_identity
    $scorerIdentity = [string]$policy.custody.scorer_identity
    $development = @($policy.custody.development_identities | ForEach-Object { [string]$_ })
    if (-not (Test-AssignedIdentity $custodianIdentity) -or
        -not (Test-AssignedIdentity $scorerIdentity) -or
        $custodianIdentity -eq $scorerIdentity -or
        $development.Count -eq 0 -or
        ($development -contains $custodianIdentity) -or
        ($development -contains $scorerIdentity) -or
        [System.Security.Principal.WindowsIdentity]::GetCurrent().Name -ne $custodianIdentity) {
        Stop-Release 'SCORING_RELEASE_ROLE_SEPARATION_INVALID'
    }
    $principal = [System.Security.Principal.WindowsPrincipal]::new([System.Security.Principal.WindowsIdentity]::GetCurrent())
    if ($principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Stop-Release 'SCORING_RELEASE_CUSTODIAN_IS_ADMINISTRATOR'
    }
    if ((Get-Sha256 $expectedScriptPath) -ne $policy.release.scoring_release_wrapper.sha256) {
        Stop-Release 'SCORING_RELEASE_WRAPPER_HASH_MISMATCH'
    }
    [void](Get-VerifiedManifestEntries $launcherRoot $launchLock.input_bundle_manifest_sha256)
    $protocolPath = Get-ContainedPath $launcherRoot $policy.release.scoring_protocol.relative_path
    if ((Get-Sha256 $protocolPath) -ne $policy.release.scoring_protocol.sha256) {
        Stop-Release 'SCORING_RELEASE_PROTOCOL_HASH_MISMATCH'
    }
    $scoringProtocolHash = [string]$policy.release.scoring_protocol.sha256
    $evidencePath = Get-ContainedPath $launcherRoot $policy.prelaunch_custody_evidence.relative_path
    if ($policy.prelaunch_custody_evidence.relative_path -ne 'prelaunch_custody_evidence.json' -or
        $policy.prelaunch_custody_evidence.status -ne 'PRE_RESULT_CUSTODY_EVIDENCE_READY' -or
        $policy.prelaunch_custody_evidence.sha256 -notmatch '^[0-9a-f]{64}$' -or
        (Get-Sha256 $evidencePath) -ne $policy.prelaunch_custody_evidence.sha256) {
        Stop-Release 'SCORING_RELEASE_EVIDENCE_HASH_MISMATCH'
    }
    $evidenceHash = [string]$policy.prelaunch_custody_evidence.sha256
    if ($launchLock.schema -ne 'fixed_weight_u01225_custody_launch_lock_v1' -or
        $launchLock.state -ne 'launch_authorized' -or
        $launchLock.candidate_id -ne 'hard5_u01225_independent_test' -or
        $launchLock.run_id -ne 'hard5_u01225_stage0b_597465a720694a6ea7001a8792de4189' -or
        $launchLock.output_root -ne (Get-ContainedPath $CustodyRoot 'archive_root') -or
        $launchLock.input_bundle_manifest_sha256 -ne $manifestHash -or
        $launchLock.policy_sha256 -ne $policyHash -or
        $launchLock.prelaunch_custody_evidence_sha256 -ne $evidenceHash -or
        $launchLock.scoring_protocol_sha256 -ne $scoringProtocolHash -or
        $launchLock.strict_test_role_status -ne 'STRICT_TEST_CUSTODY_READY') {
        Stop-Release 'SCORING_RELEASE_LAUNCH_LOCK_BINDING_INVALID'
    }
    if ($terminalReceipt.schema -ne 'fixed_weight_u01225_custody_terminal_receipt_v1' -or
        $terminalReceipt.custody_status -ne 'sealed_unreleased' -or
        $terminalReceipt.release_state -ne 'custodian_only' -or
        $terminalReceipt.candidate_id -ne 'hard5_u01225_independent_test' -or
        $terminalReceipt.split -ne 'independent_test' -or
        $terminalReceipt.run_id -ne 'hard5_u01225_stage0b_597465a720694a6ea7001a8792de4189' -or
        $terminalReceipt.input_bundle_manifest_sha256 -ne $manifestHash -or
        $terminalReceipt.policy_sha256 -ne $policyHash -or
        $terminalReceipt.prelaunch_custody_evidence_sha256 -ne $evidenceHash -or
        $terminalReceipt.scoring_protocol_sha256 -ne $scoringProtocolHash -or
        $terminalReceipt.launch_lock_sha256 -ne (Get-Sha256 $lockPath) -or
        $terminalReceipt.wrapper_read_target_arrays -ne $false -or
        $terminalReceipt.public_result_or_event_disclosure -ne $false -or
        $terminalReceipt.archive_manifest_sha256 -notmatch '^[0-9a-f]{64}$') {
        Stop-Release 'SCORING_RELEASE_TERMINAL_RECEIPT_BINDING_INVALID'
    }
    $sourceArchive = Get-ContainedPath (Get-ContainedPath $CustodyRoot 'archive_root') 'hard5_u01225_stage0b'
    $sourceArchiveValidation = Assert-ArchiveManifest $sourceArchive ([string]$terminalReceipt.archive_manifest_sha256) 'SOURCE'
    $sourceArchiveManifestHash = [string]$sourceArchiveValidation.ManifestSha256
    $sourceArchiveMembersVerified = [int]$sourceArchiveValidation.MemberCount
    if ($ScoringRoot -ne (Get-CanonicalPath $policy.release.scoring_transfer.scoring_root) -or
        (Get-CanonicalPath (Split-Path -LiteralPath $ScoringRoot -Parent)) -ne
            (Get-CanonicalPath $policy.release.scoring_transfer.scoring_parent_root)) {
        Stop-Release 'SCORING_RELEASE_ROOT_DOES_NOT_MATCH_POLICY'
    }
    $scoringParent = Get-CanonicalPath (Split-Path -LiteralPath $ScoringRoot -Parent)
    $scoringOwner = [string]$policy.release.scoring_transfer.scoring_parent_owner_identity
    $allowedOwners = @($custodianIdentity, $scorerIdentity, 'NT AUTHORITY\SYSTEM', 'BUILTIN\Administrators')
    $canonicalAllowedOwners = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    foreach ($allowedOwner in $allowedOwners) {
        [void]$canonicalAllowedOwners.Add((ConvertTo-CanonicalPrincipal ([string]$allowedOwner)))
    }
    if (-not (Test-AssignedIdentity $scoringOwner) -or
        -not $canonicalAllowedOwners.Contains((ConvertTo-CanonicalPrincipal $scoringOwner))) {
        Stop-Release 'SCORING_RELEASE_PARENT_OWNER_POLICY_INVALID'
    }
    Assert-ExclusiveAcl -Path $scoringParent -AllowedIdentities $allowedOwners -ExpectedOwnerIdentity $scoringOwner -RequiredFullControl @($custodianIdentity, $scorerIdentity) -Scope 'SCORING_PARENT'
    if (Test-Path -LiteralPath $ScoringRoot) {
        Stop-Release 'SCORING_RELEASE_ROOT_ALREADY_EXISTS'
    }
    $receiptDirectory = Get-ContainedPath $CustodyRoot 'receipts'
    $releaseLockPath = Get-ContainedPath $CustodyRoot $policy.release.scoring_transfer.release_lock_relative
    $releaseLock = [ordered]@{
        schema = 'fixed_weight_u01225_scoring_release_lock_v1'
        state = 'release_authorized'
        candidate_id = 'hard5_u01225_independent_test'
        run_id = 'hard5_u01225_stage0b_597465a720694a6ea7001a8792de4189'
        terminal_receipt_sha256 = $terminalReceiptHash
        policy_sha256 = $policyHash
        prelaunch_custody_evidence_sha256 = $evidenceHash
        scoring_protocol_sha256 = $scoringProtocolHash
        source_archive_manifest_sha256 = $sourceArchiveManifestHash
        release_id = [System.Guid]::NewGuid().ToString('N')
        released_utc = $startedUtc.ToString('o')
    }
    New-AtomicJson $releaseLockPath $releaseLock 'SCORING_RELEASE_LOCK_ALREADY_EXISTS'
    $releaseLockCreated = $true
    $releaseLockHash = Get-Sha256 $releaseLockPath

    New-Item -ItemType Directory -Path $ScoringRoot -ErrorAction Stop | Out-Null
    Set-TransferAcl $ScoringRoot $custodianIdentity $scorerIdentity
    $destinationArchive = Get-ContainedPath $ScoringRoot $policy.release.scoring_transfer.archive_relative
    Copy-Item -LiteralPath $sourceArchive -Destination $destinationArchive -Recurse -ErrorAction Stop
    $destinationArchiveValidation = Assert-ArchiveManifest $destinationArchive $sourceArchiveManifestHash 'TRANSFERRED'
    $transferredArchiveMembersVerified = [int]$destinationArchiveValidation.MemberCount
    if ($transferredArchiveMembersVerified -ne $sourceArchiveMembersVerified) {
        Stop-Release 'SCORING_RELEASE_TRANSFERRED_ARCHIVE_MEMBER_COUNT_MISMATCH'
    }
    Seal-ScorerAcl $ScoringRoot $custodianIdentity $scorerIdentity
    Write-ScoringReleaseReceipt $receiptDirectory 'scorer_release_completed' $terminalReceiptHash $policyHash $evidenceHash $scoringProtocolHash $releaseLockHash $sourceArchiveManifestHash $sourceArchiveMembersVerified $sourceArchiveManifestHash $transferredArchiveMembersVerified $startedUtc
    Write-Output 'SCORING_RELEASE_RECORDED'
    exit 0
}
catch {
    if ($releaseLockCreated -and $null -ne $receiptDirectory) {
        try {
            $receiptPath = Join-Path $receiptDirectory 'scoring_release_receipt.json'
            if (-not (Test-Path -LiteralPath $receiptPath)) {
                Write-ScoringReleaseReceipt $receiptDirectory 'scorer_release_rejected' $terminalReceiptHash $policyHash $evidenceHash $scoringProtocolHash $releaseLockHash $sourceArchiveManifestHash $sourceArchiveMembersVerified '' $transferredArchiveMembersVerified $startedUtc
            }
        }
        catch {
            # The permanent release lock still prevents a retry if receipt creation fails.
        }
    }
    Write-Output 'SCORING_RELEASE_RECORDED'
    if ($releaseLockCreated) {
        exit 0
    }
    exit 1
}
