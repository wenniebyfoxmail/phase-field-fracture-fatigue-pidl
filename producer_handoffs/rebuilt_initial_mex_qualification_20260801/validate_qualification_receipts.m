function receipt = validate_qualification_receipts(qualificationRoot, ...
        runtimeLockPath, q2LockPath, parentLockPath, outputPath)
%VALIDATE_QUALIFICATION_RECEIPTS Bind passing Q1/Q2 evidence for one family.

if nargin < 5
    outputPath = '';
end
approved = 'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db';
legacy = '589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340';
requireDirectory(qualificationRoot);
runtimeLock = readJson(runtimeLockPath, ...
    'rebuiltMexQualification:MissingProvenance');
requireRuntimeProvenance(runtimeLock);
runtimeLockSha = fileSha256(runtimeLockPath);
q2LockSha = fileSha256(q2LockPath);
parentLockSha = fileSha256(parentLockPath);
runtimeInitial = textField(runtimeLock.runtime, 'initial_sha256', 64, ...
    'rebuiltMexQualification:MissingProvenance');
sourceCommit = textField(runtimeLock.source, 'commit', 40, ...
    'rebuiltMexQualification:MissingProvenance');
if strcmp(runtimeInitial, legacy)
    error('rebuiltMexQualification:LegacyRuntimeRejected', ...
        'The legacy crashing initial MEX is never family eligible.');
elseif ~strcmp(runtimeInitial, approved)
    error('rebuiltMexQualification:UnknownRuntimeRejected', ...
        'The runtime lock does not identify the approved rebuilt MEX.');
end

q1Root = fullfile(qualificationRoot, 'Q1');
q1ReceiptPath = fullfile(q1Root, 'Q1_RECEIPT.json');
q1ResultPath = fullfile(q1Root, 'Q1_RESULT.json');
q1MetricsPath = fullfile(q1Root, 'Q1_METRICS.mat');
if ~isfile(q1ReceiptPath) || ~isfile(q1ResultPath) || ~isfile(q1MetricsPath)
    error('rebuiltMexQualification:MissingQ1', ...
        'The complete Q1 artifact set is required.');
end
q1 = readJson(q1ReceiptPath, 'rebuiltMexQualification:MissingQ1');
q1Result = readJson(q1ResultPath, 'rebuiltMexQualification:MissingQ1');
if ~logicalField(q1, 'passed') || ~logicalField(q1Result, 'passed')
    error('rebuiltMexQualification:Q1NotPassed', 'Q1 did not pass.');
end
requireSchema(q1, 'rebuilt_initial_mex_q1_receipt_v1');
requireSchema(q1Result, 'rebuilt_initial_mex_q1_result_v1');
if ~logicalField(q1, 'source_clean')
    error('rebuiltMexQualification:MissingProvenance', ...
        'Q1 lacks a passing clean-source receipt.');
end
q1Runtime = receiptIdentity(q1);
q1ResultRuntime = receiptIdentity(q1Result);
if ~sameIdentity(q1Runtime, q1ResultRuntime) || ...
        ~strcmp(q1Runtime.runtime_lock_sha256, runtimeLockSha) || ...
        ~strcmp(q1Runtime.runtime_initial_sha256, runtimeInitial) || ...
        ~strcmp(q1Runtime.source_commit, sourceCommit)
    rejectRuntimeIdentity(q1Runtime.runtime_initial_sha256, legacy, approved);
    error('rebuiltMexQualification:IdentityMismatch', ...
        'Q1 is not bound to the selected runtime and source.');
end
if ~strcmp(textField(q1, 'metrics_sha256', 64, ...
        'rebuiltMexQualification:ArtifactMismatch'), fileSha256(q1MetricsPath)) || ...
        ~strcmp(textField(q1, 'result_sha256', 64, ...
        'rebuiltMexQualification:ArtifactMismatch'), fileSha256(q1ResultPath)) || ...
        ~strcmp(textField(q1Result, 'metrics_sha256', 64, ...
        'rebuiltMexQualification:ArtifactMismatch'), fileSha256(q1MetricsPath))
    error('rebuiltMexQualification:ArtifactMismatch', ...
        'A Q1 artifact digest does not match its receipt.');
end

q2Root = fullfile(qualificationRoot, 'Q2');
q2Path = fullfile(q2Root, 'Q2_RESULT.json');
if ~isfile(q2Path)
    error('rebuiltMexQualification:MissingQ2', ...
        'A complete Q2 result is required.');
end
q2 = readJson(q2Path, 'rebuiltMexQualification:MissingQ2');
status = stringField(q2, 'status', 'rebuiltMexQualification:Q2NotPassed');
if status == "blocked"
    error('rebuiltMexQualification:Q2Blocked', ...
        'Q2 is blocked and cannot authorize a family launch.');
end
if status ~= "passed" || ~logicalField(q2, 'passed')
    error('rebuiltMexQualification:Q2NotPassed', ...
        'Q2 did not pass its cycle-one metric gate.');
end
requireSchema(q2, 'rebuilt_initial_mex_q2_result_v2');
if ~isfield(q2, 'blockers') || ~isempty(q2.blockers) || ...
        ~strcmp(stringField(q2, 'stage', ...
        'rebuiltMexQualification:Q2NotPassed'), "cycle1_metric_gate")
    error('rebuiltMexQualification:Q2NotPassed', ...
        'Q2 contains blockers or did not reach the metric gate.');
end
q2Runtime = receiptIdentity(q2);
if ~sameIdentity(q1Runtime, q2Runtime)
    rejectRuntimeIdentity(q2Runtime.runtime_initial_sha256, legacy, approved);
    error('rebuiltMexQualification:IdentityMismatch', ...
        'Q1 and Q2 runtime/source identities differ.');
end
if ~strcmp(textField(q2, 'q2_input_lock_sha256', 64, ...
        'rebuiltMexQualification:IdentityMismatch'), q2LockSha) || ...
        ~strcmp(textField(q2, 'parent_lock_sha256', 64, ...
        'rebuiltMexQualification:IdentityMismatch'), parentLockSha)
    error('rebuiltMexQualification:IdentityMismatch', ...
        'Q2 is not bound to the selected parent locks.');
end
meshSha = textField(q2, 'mesh_ordering_sha256', 64, ...
    'rebuiltMexQualification:IdentityMismatch');
replayMeshSha = textField(q2, 'replay_source_mesh_sha256', 64, ...
    'rebuiltMexQualification:IdentityMismatch');
if ~strcmp(meshSha, replayMeshSha)
    error('rebuiltMexQualification:IdentityMismatch', ...
        'Q2 mesh and replay ordering identities differ.');
end
validateQ2Artifacts(q2, q2Root);

receipt = orderfields(struct( ...
    'schema_version', 'rebuilt_mex_family_qualification_receipt_v1', ...
    'passed', true, 'runtime_lock_sha256', runtimeLockSha, ...
    'runtime_initial_sha256', runtimeInitial, ...
    'source_commit', sourceCommit, ...
    'q1_receipt_sha256', fileSha256(q1ReceiptPath), ...
    'q1_result_sha256', fileSha256(q1ResultPath), ...
    'q2_receipt_sha256', fileSha256(q2Path), ...
    'q2_input_lock_sha256', q2LockSha, ...
    'parent_lock_sha256', parentLockSha, ...
    'parent_cycle1_sha256', textField(q2, 'parent_cycle1_sha256', 64, ...
    'rebuiltMexQualification:IdentityMismatch'), ...
    'parent_reference_id', char(stringField(q2, 'parent_reference_id', ...
    'rebuiltMexQualification:IdentityMismatch')), ...
    'mesh_ordering_sha256', meshSha, ...
    'parent_vtk_mesh_sha256', textField(q2, ...
    'parent_vtk_mesh_sha256', 64, ...
    'rebuiltMexQualification:IdentityMismatch'), ...
    'mask_set_sha256', textField(q2, 'mask_set_sha256', 64, ...
    'rebuiltMexQualification:IdentityMismatch')));
if ~isempty(outputPath)
    publishJsonNoClobber(outputPath, receipt);
end
end

function requireRuntimeProvenance(lock)
required = {'runtime', 'source', 'build'};
if ~isstruct(lock) || ~isscalar(lock) || ~all(isfield(lock, required)) || ...
        ~isstruct(lock.runtime) || ~isstruct(lock.source) || ...
        ~isstruct(lock.build) || ...
        ~all(isfield(lock.build, {'command_sha256', 'log_sha256', ...
        'toolchain_sha256', 'source_hashes_sha256'})) || ...
        ~isfield(lock.source, 'clean_receipt') || ...
        ~isstruct(lock.source.clean_receipt) || ...
        ~isfield(lock.source.clean_receipt, 'is_clean') || ...
        ~isequal(lock.source.clean_receipt.is_clean, true)
    error('rebuiltMexQualification:MissingProvenance', ...
        'Runtime source/build/compiler provenance is incomplete.');
end
names = {'command_sha256', 'log_sha256', 'toolchain_sha256', ...
    'source_hashes_sha256'};
for index = 1:numel(names)
    textField(lock.build, names{index}, 64, ...
        'rebuiltMexQualification:MissingProvenance');
end
end

function identity = receiptIdentity(value)
identity = struct( ...
    'runtime_lock_sha256', textField(value, 'runtime_lock_sha256', 64, ...
    'rebuiltMexQualification:IdentityMismatch'), ...
    'runtime_initial_sha256', textField(value, 'runtime_initial_sha256', 64, ...
    'rebuiltMexQualification:IdentityMismatch'), ...
    'source_commit', textField(value, 'source_commit', 40, ...
    'rebuiltMexQualification:IdentityMismatch'));
end

function value = sameIdentity(left, right)
value = strcmp(left.runtime_lock_sha256, right.runtime_lock_sha256) && ...
    strcmp(left.runtime_initial_sha256, right.runtime_initial_sha256) && ...
    strcmp(left.source_commit, right.source_commit);
end

function rejectRuntimeIdentity(hash, legacy, approved)
if strcmp(hash, legacy)
    error('rebuiltMexQualification:LegacyRuntimeRejected', ...
        'The legacy crashing runtime is rejected.');
elseif ~strcmp(hash, approved)
    error('rebuiltMexQualification:UnknownRuntimeRejected', ...
        'An unknown runtime is rejected.');
end
end

function validateQ2Artifacts(q2, root)
required = {'state', 'terminal', 'metrics', 'parent_masks'};
if ~isfield(q2, 'artifacts') || ~isstruct(q2.artifacts) || ...
        ~all(isfield(q2.artifacts, required))
    error('rebuiltMexQualification:ArtifactMismatch', ...
        'Q2 artifact provenance is incomplete.');
end
for index = 1:numel(required)
    record = q2.artifacts.(required{index});
    relative = char(stringField(record, 'relative_path', ...
        'rebuiltMexQualification:ArtifactMismatch'));
    if isempty(relative) || contains(relative, '..') || ...
            ~isempty(regexp(relative, '^[A-Za-z]:|^[\\/]', 'once'))
        error('rebuiltMexQualification:ArtifactMismatch', ...
            'A Q2 artifact path is unsafe.');
    end
    expected = textField(record, 'sha256', 64, ...
        'rebuiltMexQualification:ArtifactMismatch');
    if ~strcmp(fileSha256(fullfile(root, relative)), expected)
        error('rebuiltMexQualification:ArtifactMismatch', ...
            'A Q2 artifact digest does not match its receipt.');
    end
end
end

function requireSchema(value, expected)
if ~isfield(value, 'schema_version') || ...
        ~strcmp(char(string(value.schema_version)), expected)
    error('rebuiltMexQualification:IdentityMismatch', ...
        'A qualification receipt schema is not approved.');
end
end

function value = logicalField(input, name)
value = isfield(input, name) && islogical(input.(name)) && ...
    isscalar(input.(name)) && input.(name);
end

function value = stringField(input, name, identifier)
if ~isstruct(input) || ~isfield(input, name) || ...
        ~(ischar(input.(name)) || ...
        (isstring(input.(name)) && isscalar(input.(name)))) || ...
        strlength(string(input.(name))) == 0
    error(identifier, 'Required qualification text is absent.');
end
value = string(input.(name));
end

function value = textField(input, name, lengthValue, identifier)
value = char(stringField(input, name, identifier));
if isempty(regexp(value, sprintf('^[0-9a-f]{%d}$', lengthValue), 'once'))
    error(identifier, 'A qualification digest is malformed.');
end
end

function value = readJson(path, identifier)
if ~isfile(path)
    error(identifier, 'A required qualification JSON file is absent.');
end
try
    value = jsondecode(fileread(path));
catch exception
    error(identifier, 'Qualification JSON is malformed: %s', exception.message);
end
end

function requireDirectory(path)
if ~isfolder(path)
    error('rebuiltMexQualification:MissingQ1', ...
        'The qualification root does not exist.');
end
end

function digest = fileSha256(path)
if ~isfile(path)
    error('rebuiltMexQualification:ArtifactMismatch', ...
        'A required qualification artifact is absent.');
end
fileId = fopen(path, 'rb');
cleanup = onCleanup(@() fclose(fileId));
md = java.security.MessageDigest.getInstance('SHA-256');
while true
    bytes = fread(fileId, 1048576, '*uint8');
    if isempty(bytes), break; end
    md.update(bytes);
end
digest = lower(reshape(dec2hex(typecast(md.digest(), 'uint8'), 2).', 1, []));
end

function publishJsonNoClobber(path, value)
if isfile(path) || isfolder(path)
    error('rebuiltMexQualification:OutputExists', ...
        'Refusing to overwrite a qualification receipt.');
end
temporary = [tempname(fileparts(path)), '.json'];
cleanup = onCleanup(@() deleteIfFile(temporary));
fileId = fopen(temporary, 'wb');
if fileId < 0
    error('rebuiltMexQualification:PublicationFailed', ...
        'Unable to create a temporary qualification receipt.');
end
fileCleanup = onCleanup(@() fclose(fileId));
bytes = unicode2native([jsonencode(orderfields(value)), newline], 'UTF-8');
fwrite(fileId, bytes, 'uint8');
clear fileCleanup
try
    java.nio.file.Files.createLink(java.io.File(path).toPath(), ...
        java.io.File(temporary).toPath());
catch exception
    if isfile(path) || isfolder(path)
        error('rebuiltMexQualification:OutputExists', ...
            'Refusing to overwrite a qualification receipt.');
    end
    error('rebuiltMexQualification:PublicationFailed', '%s', exception.message);
end
clear cleanup
deleteIfFile(temporary);
end

function deleteIfFile(path)
if isfile(path), delete(path); end
end
