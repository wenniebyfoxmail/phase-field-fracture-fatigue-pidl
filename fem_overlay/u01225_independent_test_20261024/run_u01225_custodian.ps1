<#
Custodian-only launcher for the prepared U0.1225 condition.

This script deliberately has no result-printing path.  It is a bootstrap trust
anchor: before copying it to Windows, the appointed custodian must compare this
file with the reviewed Git content.  The script then verifies every other
payload recorded by SHA256SUMS.txt before it creates a protected root.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$BundleRoot,

    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$CustodyRoot,

    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$MatlabExecutable = "matlab"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# These pins bind the reviewed draft package.  The draft policy below still
# rejects execution because its custody identities are deliberately unassigned.
# Any pre-result identity amendment must regenerate the manifest and update
# both pins under a fresh independent static review.
$ExpectedBundleManifestSha256 = '0870f3cd8b10793962443772aa9bb8c0e4c2b810dc7b8ccf0cc2b5747dd5db2b'
$ExpectedPolicySha256 = '8b636bb667523ec1dc3a2f7ad637849687912f30fff9419f70da208ce03e4387'
$ManifestName = 'SHA256SUMS.txt'
$PolicyName = 'custody_policy.json'
$WrapperName = 'run_u01225_custodian.ps1'

function Stop-Custody([string]$Code) {
    throw [System.InvalidOperationException]::new($Code)
}

function Get-Sha256([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        Stop-Custody 'CUSTODY_EXPECTED_FILE_MISSING'
    }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-CanonicalPath([string]$Path) {
    return [System.IO.Path]::GetFullPath($Path).TrimEnd([char[]]@('\', '/'))
}

function Get-ContainedPath([string]$Root, [string]$Relative) {
    if ([System.IO.Path]::IsPathRooted($Relative) -or
        $Relative -match '(^|[\\/])\.\.([\\/]|$)' -or $Relative -match ':') {
        Stop-Custody 'CUSTODY_INVALID_RELATIVE_PATH'
    }
    $rootCanonical = Get-CanonicalPath $Root
    $candidate = Get-CanonicalPath (Join-Path $rootCanonical $Relative)
    $prefix = $rootCanonical + [System.IO.Path]::DirectorySeparatorChar
    if (-not $candidate.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        Stop-Custody 'CUSTODY_RELATIVE_PATH_ESCAPES_ROOT'
    }
    return $candidate
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

function Test-AssignedIdentity($Value) {
    $text = [string]$Value
    return -not ([string]::IsNullOrWhiteSpace($text) -or $text -match '^__')
}

function ConvertTo-CanonicalPrincipal([string]$Identity) {
    if ($Identity -ieq 'SYSTEM') {
        return 'NT AUTHORITY\SYSTEM'
    }
    return $Identity
}

function Get-VerifiedManifestEntries([string]$Root) {
    $manifest = Join-Path $Root $ManifestName
    if ($ExpectedBundleManifestSha256 -match '^__' -or
        $ExpectedBundleManifestSha256 -notmatch '^[0-9a-f]{64}$') {
        Stop-Custody 'CUSTODY_BUNDLE_HASH_NOT_PINNED'
    }
    if ((Get-Sha256 $manifest) -ne $ExpectedBundleManifestSha256) {
        Stop-Custody 'CUSTODY_BUNDLE_MANIFEST_HASH_MISMATCH'
    }
    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $entries = @()
    foreach ($line in [System.IO.File]::ReadAllLines($manifest)) {
        $match = [System.Text.RegularExpressions.Regex]::Match($line, '^([0-9a-fA-F]{64})  (.+)$')
        if (-not $match.Success) {
            Stop-Custody 'CUSTODY_BUNDLE_MANIFEST_FORMAT'
        }
        $relative = $match.Groups[2].Value.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
        if ($relative -eq $ManifestName -or $relative -eq $WrapperName -or
            -not $seen.Add($relative)) {
            Stop-Custody 'CUSTODY_BUNDLE_MANIFEST_MEMBER'
        }
        $candidate = Get-ContainedPath $Root $relative
        $item = Get-Item -LiteralPath $candidate -Force -ErrorAction Stop
        if ($item.PSIsContainer -or ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
            Stop-Custody 'CUSTODY_BUNDLE_MEMBER_NOT_REGULAR'
        }
        if ((Get-Sha256 $candidate) -ne $match.Groups[1].Value.ToLowerInvariant()) {
            Stop-Custody 'CUSTODY_BUNDLE_MEMBER_HASH_MISMATCH'
        }
        $entries += [PSCustomObject]@{ Relative = $relative; Sha256 = $match.Groups[1].Value.ToLowerInvariant() }
    }
    if ($entries.Count -eq 0) {
        Stop-Custody 'CUSTODY_BUNDLE_MANIFEST_EMPTY'
    }
    return $entries
}

function Get-VerifiedPolicy([string]$Root) {
    if ($ExpectedPolicySha256 -match '^__' -or $ExpectedPolicySha256 -notmatch '^[0-9a-f]{64}$') {
        Stop-Custody 'CUSTODY_POLICY_HASH_NOT_PINNED'
    }
    $policyPath = Join-Path $Root $PolicyName
    if ((Get-Sha256 $policyPath) -ne $ExpectedPolicySha256) {
        Stop-Custody 'CUSTODY_POLICY_HASH_MISMATCH'
    }
    try {
        return ([System.IO.File]::ReadAllText($policyPath) | ConvertFrom-Json)
    }
    catch {
        Stop-Custody 'CUSTODY_POLICY_JSON_INVALID'
    }
}

function Get-VerifiedScoringProtocol([string]$Root, $Policy) {
    $release = $Policy.release
    if ($release.scoring_protocol.relative_path -ne 'scoring_protocol.json' -or
        $release.scoring_protocol.status -ne 'PRECOMMITTED_NO_MODEL_OR_SCORE' -or
        $release.scoring_protocol.sha256 -notmatch '^[0-9a-f]{64}$') {
        Stop-Custody 'CUSTODY_SCORING_PROTOCOL_POLICY_INVALID'
    }
    $protocolPath = Get-ContainedPath $Root $release.scoring_protocol.relative_path
    if ((Get-Sha256 $protocolPath) -ne $release.scoring_protocol.sha256) {
        Stop-Custody 'CUSTODY_SCORING_PROTOCOL_HASH_MISMATCH'
    }
    try {
        $protocol = [System.IO.File]::ReadAllText($protocolPath) | ConvertFrom-Json
    }
    catch {
        Stop-Custody 'CUSTODY_SCORING_PROTOCOL_JSON_INVALID'
    }
    if ($protocol.schema -ne 'fixed_weight_u01225_independent_scoring_protocol_v1' -or
        $protocol.status -ne 'PRECOMMITTED_NO_MODEL_OR_SCORE' -or
        $protocol.candidate.candidate_id -ne 'hard5_u01225_independent_test' -or
        $protocol.candidate.run_id -ne 'hard5_u01225_stage0b_597465a720694a6ea7001a8792de4189' -or
        $protocol.candidate.split -ne 'independent_test' -or
        $protocol.training_started -ne $false -or $protocol.scoring_started -ne $false -or
        $protocol.reporting.development_receives_raw_fields -ne $false -or
        $protocol.reporting.development_receives_event_values -ne $false -or
        $protocol.reporting.allowed_release -ne 'predeclared aggregate score report after isolated scoring' -or
        $protocol.reporting.physical_validation_claim -ne $false -or
        $protocol.evaluation.origins -ne 'all non-alias physical origins in native ordinal order' -or
        $protocol.evaluation.one_step -ne $true -or
        $protocol.evaluation.open_loop_horizon -ne 'min(20, remaining physical transitions)' -or
        $protocol.evaluation.normalizer_fit -ne 'training conditions only' -or
        $protocol.evaluation.selection -ne 'architecture, hyperparameters and checkpoint chosen only on validation' -or
        -not (Test-ExactStringArray $protocol.allowed_predictor_inputs @('committed origin state', 'mesh and material identity', 'prescribed action sequence available at the origin')) -or
        -not (Test-ExactStringArray $protocol.forbidden_predictor_inputs @('future target field', 'target event flag or event time', 'target terminal state', 'target-derived horizon', 'target-derived normalizer', 'cycle number alone')) -or
        -not (Test-ExactStringArray $protocol.comparators @('persistence at the origin state', 'same-branch secant extrapolation from the immediately preceding physical transition when one exists'))) {
        Stop-Custody 'CUSTODY_SCORING_PROTOCOL_BOUNDARY_INVALID'
    }
    return $protocol
}

function Assert-ScoringReleaseWrapper([string]$Root, $Policy) {
    $releaseWrapper = $Policy.release.scoring_release_wrapper
    if ($releaseWrapper.relative_path -ne 'run_u01225_scoring_release.ps1' -or
        $releaseWrapper.status -ne 'PRECOMMITTED_NO_SCORING_RELEASE' -or
        $releaseWrapper.sha256 -notmatch '^[0-9a-f]{64}$') {
        Stop-Custody 'CUSTODY_SCORING_RELEASE_WRAPPER_POLICY_INVALID'
    }
    $wrapperPath = Get-ContainedPath $Root $releaseWrapper.relative_path
    $item = Get-Item -LiteralPath $wrapperPath -Force -ErrorAction Stop
    if ($item.PSIsContainer -or ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -or
        (Get-Sha256 $wrapperPath) -ne $releaseWrapper.sha256) {
        Stop-Custody 'CUSTODY_SCORING_RELEASE_WRAPPER_HASH_MISMATCH'
    }
}

function Get-VerifiedPrelaunchEvidence([string]$Root, $Policy, $Roles) {
    $binding = $Policy.prelaunch_custody_evidence
    if ($binding.relative_path -ne 'prelaunch_custody_evidence.json' -or
        $binding.status -ne 'PRE_RESULT_CUSTODY_EVIDENCE_READY' -or
        $binding.sha256 -notmatch '^[0-9a-f]{64}$') {
        Stop-Custody 'CUSTODY_PRELAUNCH_EVIDENCE_POLICY_INVALID'
    }
    $evidencePath = Get-ContainedPath $Root $binding.relative_path
    if ((Get-Sha256 $evidencePath) -ne $binding.sha256) {
        Stop-Custody 'CUSTODY_PRELAUNCH_EVIDENCE_HASH_MISMATCH'
    }
    try {
        $evidence = [System.IO.File]::ReadAllText($evidencePath) | ConvertFrom-Json
    }
    catch {
        Stop-Custody 'CUSTODY_PRELAUNCH_EVIDENCE_JSON_INVALID'
    }
    $expectedAcl = @($Roles.CustodianIdentity, 'NT AUTHORITY\SYSTEM', 'BUILTIN\Administrators')
    if ($evidence.schema -ne 'fixed_weight_u01225_prelaunch_custody_evidence_v1' -or
        $evidence.evidence_status -ne 'PRE_RESULT_CUSTODY_EVIDENCE_READY' -or
        $evidence.candidate.candidate_id -ne 'hard5_u01225_independent_test' -or
        $evidence.candidate.condition -ne 'U0.1225' -or
        $evidence.candidate.run_id -ne 'hard5_u01225_stage0b_597465a720694a6ea7001a8792de4189' -or
        $evidence.candidate.split -ne 'independent_test' -or
        $evidence.candidate.split_unit -ne 'whole_parameter_condition' -or
        $evidence.pre_result_revision -ne $Policy.pre_result_revision -or
        $evidence.custody_parent.path -ne $Policy.paths.custody_parent_root -or
        (ConvertTo-CanonicalPrincipal ([string]$evidence.custody_parent.expected_owner_identity)) -ne
            (ConvertTo-CanonicalPrincipal ([string]$Roles.ParentOwnerIdentity)) -or
        -not (Test-ExactStringArray $evidence.custody_parent.acl_allows_only $expectedAcl) -or
        $evidence.custody_parent.development_roster_excluded -ne $true -or
        $evidence.role_separation.custodian_identity -ne $Roles.CustodianIdentity -or
        $evidence.role_separation.scorer_identity -ne $Roles.ScorerIdentity -or
        -not (Test-ExactStringArray $evidence.role_separation.development_identities $Roles.DevelopmentIdentities) -or
        $evidence.role_separation.custodian_is_non_administrator -ne $true -or
        $evidence.role_separation.development_identities_are_not_custody_administrators -ne $true -or
        $evidence.process_isolation.development_cannot_observe_custodian_process -ne $true -or
        $evidence.process_isolation.development_cannot_receive_exit_or_elapsed_time_signal -ne $true -or
        $evidence.scoring_release_route.scorer_only_acl_or_transfer_route_established -ne $true -or
        $evidence.scoring_release_route.development_excluded_from_scorer_route -ne $true -or
        $evidence.attestation.made_before_candidate_result_exists -ne $true -or
        $evidence.attestation.reviewed_by_independent_custody_authority -ne $true) {
        Stop-Custody 'CUSTODY_PRELAUNCH_EVIDENCE_BOUNDARY_INVALID'
    }
    return $evidence
}

function Assert-PreResultPolicy($Policy, [string]$RequestedRoot) {
    $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
    if ($Policy.schema -ne 'fixed_weight_u01225_custody_policy_v1' -or
        $Policy.policy_status -ne 'PRE_RESULT_CUSTODY_READY' -or
        $Policy.strict_test_role_status -ne 'STRICT_TEST_CUSTODY_READY' -or
        $Policy.candidate.candidate_id -ne 'hard5_u01225_independent_test' -or
        $Policy.candidate.condition -ne 'U0.1225' -or
        $Policy.candidate.run_id -ne 'hard5_u01225_stage0b_597465a720694a6ea7001a8792de4189' -or
        $Policy.candidate.split -ne 'independent_test' -or
        $Policy.candidate.split_unit -ne 'whole_parameter_condition') {
        Stop-Custody 'CUSTODY_POLICY_NOT_READY'
    }
    if (-not (Test-ExactStringArray $Policy.fixed_split.development_conditions @('U0.11', 'U0.115', 'U0.12', 'U0.13')) -or
        -not (Test-ExactStringArray $Policy.fixed_split.validation_conditions @('U0.125')) -or
        $Policy.fixed_split.independent_test_condition -ne 'U0.1225' -or
        $Policy.fixed_split.no_condition_or_trajectory_slice_may_move_between_splits -ne $true) {
        Stop-Custody 'CUSTODY_FIXED_SPLIT_INVALID'
    }
    $custodianIdentity = [string]$Policy.custody.custodian_identity
    if (-not (Test-AssignedIdentity $custodianIdentity) -or $identity -ne $custodianIdentity) {
        Stop-Custody 'CUSTODY_IDENTITY_NOT_AUTHORISED'
    }
    $development = @($Policy.custody.development_identities | ForEach-Object { [string]$_ })
    $developmentSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    if ($development.Count -eq 0) {
        Stop-Custody 'CUSTODY_DEVELOPMENT_ROSTER_EMPTY'
    }
    foreach ($developmentIdentity in $development) {
        if (-not (Test-AssignedIdentity $developmentIdentity) -or
            -not $developmentSet.Add($developmentIdentity)) {
            Stop-Custody 'CUSTODY_DEVELOPMENT_ROSTER_INVALID'
        }
    }
    $scorerIdentity = [string]$Policy.custody.scorer_identity
    $parentOwnerIdentity = [string]$Policy.custody.custody_parent_owner_identity
    $allowedOwners = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    [void]$allowedOwners.Add((ConvertTo-CanonicalPrincipal $custodianIdentity))
    [void]$allowedOwners.Add('NT AUTHORITY\SYSTEM')
    [void]$allowedOwners.Add('BUILTIN\Administrators')
    $canonicalParentOwner = ConvertTo-CanonicalPrincipal $parentOwnerIdentity
    if ($developmentSet.Contains($custodianIdentity) -or
        -not (Test-AssignedIdentity $scorerIdentity) -or
        $scorerIdentity -eq $custodianIdentity -or
        $developmentSet.Contains($scorerIdentity) -or
        -not (Test-AssignedIdentity $parentOwnerIdentity) -or
        -not $allowedOwners.Contains($canonicalParentOwner) -or
        $developmentSet.Contains($parentOwnerIdentity)) {
        Stop-Custody 'CUSTODY_ROLE_SEPARATION_INVALID'
    }
    if ($Policy.custody.require_non_administrative_custodian -ne $true -or
        $Policy.custody.raw_archive_access -ne 'custodian_only_until_scoring_release' -or
        $Policy.custody.launcher_access -ne 'custodian_only' -or
        $Policy.custody.logs_access -ne 'custodian_only' -or
        $Policy.custody.no_development_identity_may_be_an_administrator_of_the_custody_root -ne $true -or
        $Policy.freeze.training_started -ne $false -or
        $Policy.freeze.new_fem_conditions_allowed -ne $false -or
        $Policy.freeze.retry_or_extension_allowed -ne $false -or
        $Policy.freeze.source_snapshot_mutation_allowed -ne $false -or
        $Policy.freeze.raw_archive_mutation_allowed -ne $false -or
        $Policy.freeze.development_read_of_target_arrays_or_event_values_allowed -ne $false -or
        $Policy.freeze.development_direct_invocation_of_overlay_allowed -ne $false -or
        $Policy.freeze.development_process_observation_allowed -ne $false -or
        $Policy.release.state_before_scoring -ne 'custodian_only' -or
        $Policy.release.development_receipt_before_scoring -ne 'none' -or
        $Policy.release.raw_fields_and_event_values_remain_custodian_or_scorer_only -ne $true -or
        $Policy.paths.archive_root_relative -ne 'archive_root' -or
        $Policy.paths.launcher_relative -ne 'launcher' -or
        $Policy.paths.receipt_relative -ne 'receipts' -or
        $Policy.release.scoring_transfer.scoring_parent_root -ne 'C:\q4runs\fixed_weight_scoring' -or
        $Policy.release.scoring_transfer.scoring_root -ne 'C:\q4runs\fixed_weight_scoring\u01225_independent_test_20261024_v1' -or
        $Policy.release.scoring_transfer.archive_relative -ne 'archive' -or
        $Policy.release.scoring_transfer.release_lock_relative -ne 'scoring_release.lock.json' -or
        $Policy.release.scoring_transfer.status -ne 'PRECOMMITTED_NO_SCORING_RELEASE') {
        Stop-Custody 'CUSTODY_POLICY_BOUNDARY_INVALID'
    }
    $scoringParentOwnerIdentity = [string]$Policy.release.scoring_transfer.scoring_parent_owner_identity
    $allowedScoringOwners = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    [void]$allowedScoringOwners.Add((ConvertTo-CanonicalPrincipal $custodianIdentity))
    [void]$allowedScoringOwners.Add((ConvertTo-CanonicalPrincipal $scorerIdentity))
    [void]$allowedScoringOwners.Add('NT AUTHORITY\SYSTEM')
    [void]$allowedScoringOwners.Add('BUILTIN\Administrators')
    if (-not (Test-AssignedIdentity $scoringParentOwnerIdentity) -or
        -not $allowedScoringOwners.Contains((ConvertTo-CanonicalPrincipal $scoringParentOwnerIdentity)) -or
        $developmentSet.Contains($scoringParentOwnerIdentity)) {
        Stop-Custody 'CUSTODY_SCORING_PARENT_OWNER_INVALID'
    }
    if (-not (Test-ExactStringArray $Policy.release.external_evidence_required_before_strict_test_claim @(
            'pre-result evidence that the custody parent ACL and owner exclude every development identity',
            'pre-result evidence that development cannot observe or receive a timing signal from the custodian process',
            'a scorer-specific access-control or transfer receipt that excludes every development identity',
            'a custodian-signed scoring-release receipt bound to the terminal receipt and scoring protocol hash'))) {
        Stop-Custody 'CUSTODY_RELEASE_BOUNDARY_INVALID'
    }
    $principal = [System.Security.Principal.WindowsPrincipal]::new(
        [System.Security.Principal.WindowsIdentity]::GetCurrent())
    if ($principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Stop-Custody 'CUSTODY_CUSTODIAN_IS_ADMINISTRATOR'
    }
    $expectedParent = 'C:\q4runs\fixed_weight_custody'
    $expectedRoot = Join-Path $expectedParent 'u01225_independent_test_20261024_v1'
    if ((Get-CanonicalPath $RequestedRoot) -ne (Get-CanonicalPath $Policy.paths.custody_root) -or
        (Get-CanonicalPath (Split-Path -LiteralPath $RequestedRoot -Parent)) -ne
            (Get-CanonicalPath $Policy.paths.custody_parent_root) -or
        (Get-CanonicalPath $Policy.paths.custody_parent_root) -ne (Get-CanonicalPath $expectedParent) -or
        (Get-CanonicalPath $Policy.paths.custody_root) -ne (Get-CanonicalPath $expectedRoot)) {
        Stop-Custody 'CUSTODY_ROOT_DOES_NOT_MATCH_POLICY'
    }
    return [PSCustomObject]@{
        CustodianIdentity = $custodianIdentity
        ScorerIdentity = $scorerIdentity
        DevelopmentIdentities = $development
        ParentOwnerIdentity = $parentOwnerIdentity
        ScoringParentOwnerIdentity = $scoringParentOwnerIdentity
    }
}

function Assert-ExclusiveCustodyAcl([string]$Path, [string]$CustodianIdentity, [string]$ExpectedOwnerIdentity, [string[]]$AdditionalAllowedIdentities, [string]$Scope) {
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        Stop-Custody ("CUSTODY_{0}_MISSING" -f $Scope)
    }
    $item = Get-Item -LiteralPath $Path -Force -ErrorAction Stop
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        Stop-Custody ("CUSTODY_{0}_REPARSE_POINT" -f $Scope)
    }
    $acl = Get-Acl -LiteralPath $Path
    if (-not $acl.AreAccessRulesProtected) {
        Stop-Custody ("CUSTODY_{0}_INHERITS_ACCESS" -f $Scope)
    }
    $allowed = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    [void]$allowed.Add((ConvertTo-CanonicalPrincipal $CustodianIdentity))
    [void]$allowed.Add('NT AUTHORITY\SYSTEM')
    [void]$allowed.Add('BUILTIN\Administrators')
    foreach ($additionalIdentity in $AdditionalAllowedIdentities) {
        [void]$allowed.Add((ConvertTo-CanonicalPrincipal ([string]$additionalIdentity)))
    }
    if ((ConvertTo-CanonicalPrincipal ([string]$acl.Owner)) -ne
        (ConvertTo-CanonicalPrincipal $ExpectedOwnerIdentity)) {
        Stop-Custody ("CUSTODY_{0}_OWNER_MISMATCH" -f $Scope)
    }
    $custodianHasFullControl = $false
    foreach ($rule in $acl.Access) {
        $ruleIdentity = ConvertTo-CanonicalPrincipal ([string]$rule.IdentityReference.Value)
        if (-not $allowed.Contains($ruleIdentity) -or
            $rule.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow) {
            Stop-Custody ("CUSTODY_{0}_ACL_NOT_EXCLUSIVE" -f $Scope)
        }
        if ($ruleIdentity -eq (ConvertTo-CanonicalPrincipal $CustodianIdentity) -and
            $rule.FileSystemRights.ToString().Contains('FullControl')) {
            $custodianHasFullControl = $true
        }
    }
    if (-not $custodianHasFullControl) {
        Stop-Custody ("CUSTODY_{0}_CUSTODIAN_ACCESS_MISSING" -f $Scope)
    }
}

function Assert-ProtectedCustodyParent([string]$ParentRoot, [string]$CustodianIdentity, [string]$ExpectedOwnerIdentity) {
    Assert-ExclusiveCustodyAcl -Path $ParentRoot -CustodianIdentity $CustodianIdentity -ExpectedOwnerIdentity $ExpectedOwnerIdentity -AdditionalAllowedIdentities ([string[]]@()) -Scope 'PARENT'
}

function Set-CustodyAcl([string]$Path, [string]$CustodianIdentity) {
    $arguments = @(
        $Path,
        '/inheritance:r',
        '/grant:r',
        ("{0}:(OI)(CI)F" -f $CustodianIdentity),
        'SYSTEM:(OI)(CI)F',
        'BUILTIN\Administrators:(OI)(CI)F'
    )
    & icacls.exe @arguments | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Stop-Custody 'CUSTODY_ACL_APPLICATION_FAILED'
    }
    Assert-ExclusiveCustodyAcl -Path $Path -CustodianIdentity $CustodianIdentity -ExpectedOwnerIdentity $CustodianIdentity -AdditionalAllowedIdentities ([string[]]@()) -Scope 'CHILD'
}

function Write-AtomicUtf8([string]$Path, [string]$Text) {
    $parent = Split-Path -LiteralPath $Path -Parent
    $temporary = Join-Path $parent (([System.Guid]::NewGuid().ToString('N')) + '.tmp')
    [System.IO.File]::WriteAllText($temporary, $Text, [System.Text.UTF8Encoding]::new($false))
    [System.IO.File]::Move($temporary, $Path)
}

function New-AtomicLaunchLock([string]$Path, $Lock) {
    $text = ($Lock | ConvertTo-Json -Depth 8) + [Environment]::NewLine
    $bytes = [System.Text.UTF8Encoding]::new($false).GetBytes($text)
    try {
        $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    }
    catch {
        Stop-Custody 'CUSTODY_LAUNCH_LOCK_ALREADY_EXISTS'
    }
    try {
        $stream.Write($bytes, 0, $bytes.Length)
        $stream.Flush($true)
    }
    finally {
        $stream.Dispose()
    }
}

function Copy-VerifiedPayload([string]$SourceRoot, [string]$DestinationRoot, $Entries) {
    New-Item -ItemType Directory -Path $DestinationRoot -ErrorAction Stop | Out-Null
    Copy-Item -LiteralPath (Join-Path $SourceRoot $ManifestName) -Destination (Join-Path $DestinationRoot $ManifestName) -ErrorAction Stop
    foreach ($entry in $Entries) {
        $source = Get-ContainedPath $SourceRoot $entry.Relative
        $destination = Get-ContainedPath $DestinationRoot $entry.Relative
        New-Item -ItemType Directory -Path (Split-Path -LiteralPath $destination -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -ErrorAction Stop
    }
    Copy-Item -LiteralPath $PSCommandPath -Destination (Join-Path $DestinationRoot $WrapperName) -ErrorAction Stop
    [void](Get-VerifiedManifestEntries $DestinationRoot)
    if ((Get-Sha256 (Join-Path $DestinationRoot $PolicyName)) -ne $ExpectedPolicySha256) {
        Stop-Custody 'CUSTODY_COPIED_POLICY_HASH_MISMATCH'
    }
}

function Write-TerminalReceipt([string]$ReceiptDirectory, [string]$Status, [string]$BundleHash, [string]$PolicyHash, [string]$EvidenceHash, [string]$ScoringProtocolHash, [string]$LockHash, [string]$ArchiveManifestHash, [datetime]$StartedUtc) {
    if (-not (Test-Path -LiteralPath $ReceiptDirectory -PathType Container)) {
        New-Item -ItemType Directory -Path $ReceiptDirectory -ErrorAction Stop | Out-Null
    }
    $receiptPath = Join-Path $ReceiptDirectory 'terminal_receipt.json'
    $sidecarPath = Join-Path $ReceiptDirectory 'terminal_receipt.sha256'
    if ((Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $sidecarPath)) {
        Stop-Custody 'CUSTODY_TERMINAL_RECEIPT_ALREADY_EXISTS'
    }
    $receipt = [ordered]@{
        schema = 'fixed_weight_u01225_custody_terminal_receipt_v1'
        custody_status = $Status
        release_state = 'custodian_only'
        candidate_id = 'hard5_u01225_independent_test'
        split = 'independent_test'
        run_id = 'hard5_u01225_stage0b_597465a720694a6ea7001a8792de4189'
        input_bundle_manifest_sha256 = $BundleHash
        policy_sha256 = $PolicyHash
        prelaunch_custody_evidence_sha256 = $EvidenceHash
        scoring_protocol_sha256 = $ScoringProtocolHash
        launch_lock_sha256 = $LockHash
        archive_manifest_sha256 = $ArchiveManifestHash
        wrapper_read_target_arrays = $false
        public_result_or_event_disclosure = $false
        started_utc = $StartedUtc.ToString('o')
        completed_utc = [DateTime]::UtcNow.ToString('o')
    }
    Write-AtomicUtf8 $receiptPath (($receipt | ConvertTo-Json -Depth 8) + [Environment]::NewLine)
    Write-AtomicUtf8 $sidecarPath ((Get-Sha256 $receiptPath) + '  terminal_receipt.json' + [Environment]::NewLine)
}

$custodyCreated = $false
$lockCreated = $false
$startedUtc = [DateTime]::UtcNow
$bundleHashForReceipt = $null
$policyHashForReceipt = $null
$evidenceHashForReceipt = $null
$scoringProtocolHashForReceipt = $null
$lockHashForReceipt = $null

try {
    $BundleRoot = Get-CanonicalPath $BundleRoot
    $CustodyRoot = Get-CanonicalPath $CustodyRoot
    $entries = Get-VerifiedManifestEntries $BundleRoot
    $policy = Get-VerifiedPolicy $BundleRoot
    [void](Get-VerifiedScoringProtocol $BundleRoot $policy)
    Assert-ScoringReleaseWrapper $BundleRoot $policy
    $roles = Assert-PreResultPolicy $policy $CustodyRoot
    [void](Get-VerifiedPrelaunchEvidence $BundleRoot $policy $roles)
    $bundleHashForReceipt = $ExpectedBundleManifestSha256
    $policyHashForReceipt = $ExpectedPolicySha256
    $evidenceHashForReceipt = [string]$policy.prelaunch_custody_evidence.sha256
    $scoringProtocolHashForReceipt = [string]$policy.release.scoring_protocol.sha256

    $custodyParentRoot = Get-CanonicalPath (Split-Path -LiteralPath $CustodyRoot -Parent)
    Assert-ProtectedCustodyParent $custodyParentRoot $roles.CustodianIdentity $roles.ParentOwnerIdentity
    if (Test-Path -LiteralPath $CustodyRoot) {
        Stop-Custody 'CUSTODY_ROOT_ALREADY_EXISTS'
    }
    New-Item -ItemType Directory -Path $CustodyRoot -ErrorAction Stop | Out-Null
    $custodyCreated = $true
    Set-CustodyAcl $CustodyRoot $roles.CustodianIdentity

    $launcherRoot = Join-Path $CustodyRoot $policy.paths.launcher_relative
    Copy-VerifiedPayload $BundleRoot $launcherRoot $entries
    Set-CustodyAcl $launcherRoot $roles.CustodianIdentity

    $lockPath = Join-Path $CustodyRoot 'launch.lock.json'
    $archiveOutputRoot = Join-Path $CustodyRoot $policy.paths.archive_root_relative
    $lock = [ordered]@{
        schema = 'fixed_weight_u01225_custody_launch_lock_v1'
        state = 'launch_authorized'
        candidate_id = 'hard5_u01225_independent_test'
        run_id = 'hard5_u01225_stage0b_597465a720694a6ea7001a8792de4189'
        output_root = $archiveOutputRoot
        input_bundle_manifest_sha256 = $ExpectedBundleManifestSha256
        policy_sha256 = $ExpectedPolicySha256
        prelaunch_custody_evidence_sha256 = $evidenceHashForReceipt
        scoring_protocol_sha256 = $scoringProtocolHashForReceipt
        strict_test_role_status = 'STRICT_TEST_CUSTODY_READY'
        launched_utc = $startedUtc.ToString('o')
        lock_id = [System.Guid]::NewGuid().ToString('N')
    }
    New-AtomicLaunchLock $lockPath $lock
    $lockCreated = $true
    $lockHashForReceipt = Get-Sha256 $lockPath

    $logs = Join-Path $CustodyRoot 'logs'
    New-Item -ItemType Directory -Path $logs -ErrorAction Stop | Out-Null
    $env:FW_U01225_CUSTODY_LOCK_PATH = $lockPath
    $matlabPath = $launcherRoot.Replace("'", "''")
    $matlabExpression = "addpath('$matlabPath'); run_hard5_u01225_independent_test();"
    $quotedMatlabExpression = '"' + $matlabExpression + '"'
    $startParameters = @{
        FilePath = $MatlabExecutable
        ArgumentList = ('-batch ' + $quotedMatlabExpression)
        WorkingDirectory = $launcherRoot
        RedirectStandardOutput = (Join-Path $logs 'matlab.stdout.log')
        RedirectStandardError = (Join-Path $logs 'matlab.stderr.log')
        Wait = $true
        PassThru = $true
    }
    $process = Start-Process @startParameters

    $sealedArchive = Join-Path $archiveOutputRoot 'hard5_u01225_stage0b'
    $archiveManifest = Join-Path $sealedArchive 'SHA256SUMS.txt'
    if ($process.ExitCode -eq 0 -and (Test-Path -LiteralPath $archiveManifest -PathType Leaf)) {
        Write-TerminalReceipt (Join-Path $CustodyRoot $policy.paths.receipt_relative) 'sealed_unreleased' $bundleHashForReceipt $policyHashForReceipt $evidenceHashForReceipt $scoringProtocolHashForReceipt $lockHashForReceipt (Get-Sha256 $archiveManifest) $startedUtc
        Write-Output 'CUSTODY_TERMINAL_RECORDED'
        exit 0
    }

    Write-TerminalReceipt (Join-Path $CustodyRoot $policy.paths.receipt_relative) 'rejected_unreleased' $bundleHashForReceipt $policyHashForReceipt $evidenceHashForReceipt $scoringProtocolHashForReceipt $lockHashForReceipt '' $startedUtc
    Write-Output 'CUSTODY_TERMINAL_RECORDED'
    # A development caller must not infer an archive outcome from the exit code.
    exit 0
}
catch {
    if ($custodyCreated) {
        try {
            $receiptDirectory = Join-Path $CustodyRoot 'receipts'
            $receiptPath = Join-Path $receiptDirectory 'terminal_receipt.json'
            if (-not (Test-Path -LiteralPath $receiptPath)) {
                Write-TerminalReceipt $receiptDirectory 'rejected_unreleased' $bundleHashForReceipt $policyHashForReceipt $evidenceHashForReceipt $scoringProtocolHashForReceipt $lockHashForReceipt '' $startedUtc
            }
        }
        catch {
            # The permanent root/lock still prevents a retry if even receipt creation fails.
        }
    }
    Write-Output 'CUSTODY_TERMINAL_RECORDED'
    # Once custody root creation began, keep the terminal signal outcome-neutral.
    if ($custodyCreated) {
        exit 0
    }
    exit 1
}
