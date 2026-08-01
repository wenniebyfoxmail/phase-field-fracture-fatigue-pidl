function tests = rebuiltMexQualificationReceiptTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
handoff = fileparts(fileparts(mfilename('fullpath')));
addpath(handoff);
testCase.addTeardown(@() rmpath(handoff));
end

function testCompleteMatchingReceiptsProduceBoundFamilyReceipt(testCase)
fixture = qualificationFixture(testCase);
receipt = validate_qualification_receipts(fixture.root, fixture.runtimeLock, ...
    fixture.q2Lock, fixture.parentLock);

verifyTrue(testCase, receipt.passed);
verifyEqual(testCase, receipt.runtime_initial_sha256, approvedHash());
verifyEqual(testCase, receipt.source_commit, fixture.sourceCommit);
verifyEqual(testCase, receipt.runtime_lock_sha256, fileHash(fixture.runtimeLock));
verifyEqual(testCase, receipt.q1_receipt_sha256, ...
    fileHash(fullfile(fixture.root, 'Q1', 'Q1_RECEIPT.json')));
verifyEqual(testCase, receipt.q2_receipt_sha256, ...
    fileHash(fullfile(fixture.root, 'Q2', 'Q2_RESULT.json')));
verifyEqual(testCase, receipt.parent_lock_sha256, fileHash(fixture.parentLock));
verifyEqual(testCase, receipt.q2_input_lock_sha256, fileHash(fixture.q2Lock));
verifyEqual(testCase, receipt.mesh_ordering_sha256, fixture.meshHash);
end

function testMissingOrFailedQ1FailsClosed(testCase)
fixture = qualificationFixture(testCase);
delete(fullfile(fixture.root, 'Q1', 'Q1_RECEIPT.json'));
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:MissingQ1');

fixture = qualificationFixture(testCase);
mutateJson(fullfile(fixture.root, 'Q1', 'Q1_RECEIPT.json'), ...
    @(value) setfield(value, 'passed', false));
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:Q1NotPassed');
end

function testMissingBlockedOrFailedQ2FailsClosed(testCase)
fixture = qualificationFixture(testCase);
delete(fullfile(fixture.root, 'Q2', 'Q2_RESULT.json'));
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:MissingQ2');

fixture = qualificationFixture(testCase);
mutateJson(fullfile(fixture.root, 'Q2', 'Q2_RESULT.json'), @blockQ2);
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:Q2Blocked');

fixture = qualificationFixture(testCase);
mutateJson(fullfile(fixture.root, 'Q2', 'Q2_RESULT.json'), @failQ2);
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:Q2NotPassed');
end

function testLegacyUnknownAndMismatchedRuntimeFailClosed(testCase)
fixture = qualificationFixture(testCase);
mutateJson(fullfile(fixture.root, 'Q1', 'Q1_RECEIPT.json'), ...
    @(value) setfield(value, 'runtime_initial_sha256', legacyHash()));
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:LegacyRuntimeRejected');

fixture = qualificationFixture(testCase);
mutateJson(fullfile(fixture.root, 'Q1', 'Q1_RECEIPT.json'), ...
    @(value) setfield(value, 'runtime_initial_sha256', repmat('9', 1, 64)));
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:UnknownRuntimeRejected');

fixture = qualificationFixture(testCase);
mutateJson(fullfile(fixture.root, 'Q2', 'Q2_RESULT.json'), ...
    @(value) setfield(value, 'runtime_lock_sha256', repmat('8', 1, 64)));
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:IdentityMismatch');
end

function testSourceParentMeshAndProvenanceMismatchFailClosed(testCase)
fields = {'source_commit', 'parent_lock_sha256', 'mesh_ordering_sha256'};
for index = 1:numel(fields)
    fixture = qualificationFixture(testCase);
    field = fields{index};
    replacement = repmat('7', 1, 64);
    if strcmp(field, 'source_commit')
        replacement = repmat('7', 1, 40);
    end
    mutateJson(fullfile(fixture.root, 'Q2', 'Q2_RESULT.json'), ...
        @(value) setfield(value, field, replacement));
    verifyError(testCase, @() validateFixture(fixture), ...
        'rebuiltMexQualification:IdentityMismatch');
end

fixture = qualificationFixture(testCase);
mutateJson(fixture.runtimeLock, @(value) rmfield(value, 'build'));
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:MissingProvenance');
end

function testArtifactTamperAndNoClobberPublicationFailClosed(testCase)
fixture = qualificationFixture(testCase);
writeBytes(fullfile(fixture.root, 'Q2', 'Q2_METRICS.mat'), uint8('tamper'));
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:ArtifactMismatch');

fixture = qualificationFixture(testCase);
outputPath = fullfile(fixture.root, 'FAMILY_QUALIFICATION_RECEIPT.json');
validate_qualification_receipts(fixture.root, fixture.runtimeLock, ...
    fixture.q2Lock, fixture.parentLock, outputPath);
verifyTrue(testCase, isfile(outputPath));
verifyError(testCase, @() validate_qualification_receipts(fixture.root, ...
    fixture.runtimeLock, fixture.q2Lock, fixture.parentLock, outputPath), ...
    'rebuiltMexQualification:OutputExists');
end

function receipt = validateFixture(fixture)
receipt = validate_qualification_receipts(fixture.root, fixture.runtimeLock, ...
    fixture.q2Lock, fixture.parentLock);
end

function fixture = qualificationFixture(testCase)
folder = matlab.unittest.fixtures.TemporaryFolderFixture;
testCase.applyFixture(folder);
root = fullfile(folder.Folder, char(java.util.UUID.randomUUID));
mkdir(fullfile(root, 'Q1'));
mkdir(fullfile(root, 'Q2'));
sourceCommit = repmat('c', 1, 40);
meshHash = repmat('d', 1, 64);
runtimeLock = fullfile(root, 'RUNTIME_LOCK.json');
q2Lock = fullfile(root, 'Q2_INPUT_LOCK.json');
parentLock = fullfile(root, 'PARENT_LOCK.json');
writeJson(runtimeLock, struct('schema_version', ...
    'rebuilt_initial_mex_runtime_lock_v1', 'runtime', struct( ...
    'initial_sha256', approvedHash()), 'source', struct( ...
    'commit', sourceCommit, 'clean_receipt', struct('is_clean', true)), ...
    'build', struct('command_sha256', repmat('1', 1, 64), ...
    'log_sha256', repmat('2', 1, 64), ...
    'toolchain_sha256', repmat('3', 1, 64), ...
    'source_hashes_sha256', repmat('4', 1, 64))));
writeJson(q2Lock, struct('schema_version', 'q2_lock_fixture'));
writeJson(parentLock, struct('schema_version', 'parent_lock_fixture'));
runtimeHash = fileHash(runtimeLock);
q2LockHash = fileHash(q2Lock);
parentHash = fileHash(parentLock);

writeBytes(fullfile(root, 'Q1', 'Q1_METRICS.mat'), uint8('q1 metrics'));
q1Result = struct('schema_version', 'rebuilt_initial_mex_q1_result_v1', ...
    'passed', true, 'runtime_lock_sha256', runtimeHash, ...
    'runtime_initial_sha256', approvedHash(), 'source_commit', sourceCommit, ...
    'metrics_sha256', fileHash(fullfile(root, 'Q1', 'Q1_METRICS.mat')));
writeJson(fullfile(root, 'Q1', 'Q1_RESULT.json'), q1Result);
q1Receipt = struct('schema_version', ...
    'rebuilt_initial_mex_q1_receipt_v1', 'passed', true, ...
    'runtime_lock_sha256', runtimeHash, ...
    'runtime_initial_sha256', approvedHash(), 'source_commit', sourceCommit, ...
    'source_clean', true, 'metrics_sha256', q1Result.metrics_sha256, ...
    'result_sha256', fileHash(fullfile(root, 'Q1', 'Q1_RESULT.json')));
writeJson(fullfile(root, 'Q1', 'Q1_RECEIPT.json'), q1Receipt);

names = {'Q2_CYCLE1_STATE.mat', 'Q2_CYCLE1_TERMINAL.json', ...
    'Q2_METRICS.mat', 'Q2_PARENT_MASKS.mat'};
for index = 1:numel(names)
    writeBytes(fullfile(root, 'Q2', names{index}), uint8(names{index}));
end
artifacts = struct( ...
    'state', artifact(root, names{1}), ...
    'terminal', artifact(root, names{2}), ...
    'metrics', artifact(root, names{3}), ...
    'parent_masks', artifact(root, names{4}));
q2 = struct('schema_version', 'rebuilt_initial_mex_q2_result_v2', ...
    'status', 'passed', 'passed', true, 'blockers', {{}}, ...
    'stage', 'cycle1_metric_gate', 'runtime_lock_sha256', runtimeHash, ...
    'runtime_initial_sha256', approvedHash(), 'source_commit', sourceCommit, ...
    'q2_input_lock_sha256', q2LockHash, ...
    'parent_lock_sha256', parentHash, ...
    'parent_cycle1_sha256', repmat('5', 1, 64), ...
    'parent_reference_id', 'fixture_parent', ...
    'mesh_ordering_sha256', meshHash, ...
    'replay_source_mesh_sha256', meshHash, ...
    'parent_vtk_mesh_sha256', repmat('6', 1, 64), ...
    'mask_set_sha256', repmat('7', 1, 64), ...
    'family_terminal_eligible', false, 'artifacts', artifacts);
writeJson(fullfile(root, 'Q2', 'Q2_RESULT.json'), q2);
fixture = struct('root', root, 'runtimeLock', runtimeLock, ...
    'q2Lock', q2Lock, 'parentLock', parentLock, ...
    'sourceCommit', sourceCommit, 'meshHash', meshHash);
end

function value = artifact(root, name)
value = struct('relative_path', name, ...
    'sha256', fileHash(fullfile(root, 'Q2', name)));
end

function value = blockQ2(value)
value.status = 'blocked';
value.passed = false;
value.blockers = {'blocked_missing_parent_active_field'};
end

function value = failQ2(value)
value.status = 'failed';
value.passed = false;
end

function mutateJson(path, mutation)
value = jsondecode(fileread(path));
value = mutation(value);
delete(path);
writeJson(path, value);
end

function writeJson(path, value)
writeBytes(path, unicode2native([jsonencode(orderfields(value)), newline], 'UTF-8'));
end

function writeBytes(path, bytes)
fileId = fopen(path, 'wb');
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, bytes, 'uint8');
end

function digest = fileHash(path)
fileId = fopen(path, 'rb');
cleanup = onCleanup(@() fclose(fileId));
md = java.security.MessageDigest.getInstance('SHA-256');
md.update(fread(fileId, Inf, '*uint8'));
digest = lower(reshape(dec2hex(typecast(md.digest(), 'uint8'), 2).', 1, []));
end

function value = approvedHash()
value = 'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db';
end

function value = legacyHash()
value = '589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340';
end
