function tests = toyRoadTerminalPackageValidatorTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
validatorDir = fileparts(fileparts(mfilename('fullpath')));
addpath(validatorDir);
testCase.addTeardown(@() rmpath(validatorDir));
end

function testAcceptsCompleteImmutableTerminalPackage(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
summary = validatePackage(root);
verifyTrue(testCase, summary.is_valid);
verifyEqual(testCase, summary.terminal_cycle, 5);
verifyEqual(testCase, summary.cycle_count, 5);
verifyEqual(testCase, summary.case_id, 'T1_initial_defect');
end

function testAcceptsAlternateNonAuthorizingMetadataScope(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect", ...
    "synthetic_review_non_authorizing");
verifyTrue(testCase, validatePackage(root).is_valid);
end

function testRejectsMissingCycle(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
delete(fullfile(root, 'substeps', 'cycle_0003.mat'));
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsExtraCycle(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
[shard, ~, ~, contract] = toyRoadShardFixture(6);
shard = applyContract(shard, contractForRoot(contract, root));
save(fullfile(root, 'substeps', 'cycle_0006.mat'), 'shard');
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsWrongCaseLocalMeshHash(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'substeps', 'cycle_0002.mat');
loaded = load(path, 'shard');
loaded.shard.mesh_sha256(1) = '0';
replaceMat(path, 'shard', loaded.shard);
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsMismatchedEventMetadata(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'EVENT_METADATA.json');
event = jsondecode(fileread(path));
event.confirmed_cycle = 4;
replaceJson(path, event);
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsEarlyTwoCycleConfirmation(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
replaceFirstHit(root, 3);
verifyInvalid(testCase, root);
end

function testRejectsLateFourCycleConfirmation(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
replaceFirstHit(root, 1);
verifyInvalid(testCase, root);
end

function testRejectsTerminalCycleMismatch(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'TERMINAL_RESULT.json');
terminal = jsondecode(fileread(path));
terminal.terminal_cycle = 4;
replaceJson(path, terminal);
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testEveryCaseRequiresOwnC5Trace(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
delete(fullfile(root, 'qualification', 'C5_STAGGER_TRACE.csv'));
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testEveryCaseRequiresOwnC5Receipt(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
delete(fullfile(root, 'qualification', 'C5_NUMERICAL_GATE_RECEIPT.json'));
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsFailedCaseLocalC5Receipt(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'qualification', 'C5_NUMERICAL_GATE_RECEIPT.json');
receipt = jsondecode(fileread(path));
receipt.status = 'FAIL';
receipt.passed = false;
replaceJson(path, receipt);
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsIncompleteC5TraceColumns(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'qualification', 'C5_STAGGER_TRACE.csv');
text = fileread(path);
text = erase(text, 'raw_phase_residual,');
writeReplacementText(path, text);
refreshC5ReceiptAndManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsFalseC5RowAndReassemblyCounts(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'qualification', 'C5_NUMERICAL_GATE_RECEIPT.json');
receipt = jsondecode(fileread(path));
receipt.trace_row_count = 3;
receipt.reassembly_count = 3;
replaceJson(path, receipt);
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsFalseC5FinalMetric(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'qualification', 'C5_NUMERICAL_GATE_RECEIPT.json');
receipt = jsondecode(fileread(path));
receipt.final_projected_phase_kkt = 1e-5;
replaceJson(path, receipt);
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsFalseC5Threshold(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'qualification', 'C5_NUMERICAL_GATE_RECEIPT.json');
receipt = jsondecode(fileread(path));
receipt.projected_phase_kkt_threshold = 1e-2;
replaceJson(path, receipt);
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsSkippedStaggerOrdinal(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
replaceC5Ordinals(root, [1; 3], [1; 2]);
verifyInvalid(testCase, root);
end

function testRejectsDuplicatedStaggerOrdinal(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
replaceC5Ordinals(root, [1; 1], [1; 2]);
verifyInvalid(testCase, root);
end

function testRejectsReorderedStaggerOrdinal(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
replaceC5Ordinals(root, [2; 1], [1; 2]);
verifyInvalid(testCase, root);
end

function testRejectsFractionalStaggerOrdinal(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
replaceC5Ordinals(root, [1; 1.5], [1; 2]);
verifyInvalid(testCase, root);
end

function testRejectsSkippedReassemblyOrdinal(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
replaceC5Ordinals(root, [1; 2], [1; 3]);
verifyInvalid(testCase, root);
end

function testRejectsBytesChangedAfterManifestFinalization(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'TERMINAL_RESULT.json');
writeReplacementText(path, [fileread(path) ' ']);
verifyInvalid(testCase, root);
end

function testRejectsExecutionLockDigestInconsistentWithManifest(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'TERMINAL_MANIFEST.json');
manifest = jsondecode(fileread(path));
manifest.execution_input_lock_sha256 = repmat('9', 1, 64);
replaceJson(path, manifest);
verifyInvalid(testCase, root);
end

function testRejectsExecutionLockForAnotherCase(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'EXECUTION_INPUT_LOCK.json');
lock = jsondecode(fileread(path));
lock.case_id = 'T2_other_case';
replaceJson(path, lock);
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsManifestMissingCanonicalIdentity(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'TERMINAL_MANIFEST.json');
manifest = rmfield(jsondecode(fileread(path)), 'mesh_sha256');
replaceJson(path, manifest);
verifyInvalid(testCase, root);
end

function testRejectsManifestExtraField(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'TERMINAL_MANIFEST.json');
manifest = jsondecode(fileread(path));
manifest.unexpected = 'forbidden';
replaceJson(path, manifest);
verifyInvalid(testCase, root);
end

function testRejectsWrongProtocolValueOrType(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'TERMINAL_MANIFEST.json');
manifest = jsondecode(fileread(path));
manifest.protocol_version = 21;
replaceJson(path, manifest);
verifyInvalid(testCase, root);
end

function testRejectsShardMissingCanonicalField(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'substeps', 'cycle_0002.mat');
loaded = load(path, 'shard');
loaded.shard = rmfield(loaded.shard, 'psi_active_gp');
replaceMat(path, 'shard', loaded.shard);
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsShardExtraField(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'substeps', 'cycle_0002.mat');
loaded = load(path, 'shard');
loaded.shard.unexpected_gp = zeros(size(loaded.shard.d_gp));
replaceMat(path, 'shard', loaded.shard);
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsCaseFoldedManifestCollision(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'TERMINAL_MANIFEST.json');
manifest = jsondecode(fileread(path));
duplicate = manifest.files(1);
duplicate.path = lower(duplicate.path);
if strcmp(duplicate.path, manifest.files(1).path)
    duplicate.path = upper(duplicate.path);
end
manifest.files(end + 1) = duplicate;
[~, order] = sort(string({manifest.files.path}));
manifest.files = manifest.files(order);
replaceJson(path, manifest);
verifyInvalid(testCase, root);
end

function testRejectsFileSymlinkWhenSupported(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'EVENT_METADATA.json');
outside = fullfile(fileparts(root), 'outside-event.json');
copyfile(path, outside);
delete(path);
created = createFileSymlink(path, outside);
assumeTrue(testCase, created, 'File symlink creation is unavailable.');
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsRootJunctionOrSymlinkWhenSupported(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
alias = fullfile(fileparts(root), 'package-alias');
created = createDirectoryLink(alias, root);
assumeTrue(testCase, created, 'Directory link creation is unavailable.');
verifyError(testCase, @() validate_toy_road_terminal_package( ...
    alias, "T1_initial_defect", contractPath(root)), ...
    'toyRoadP0:InvalidTerminalPackage');
end

function summary = validatePackage(root)
summary = validate_toy_road_terminal_package( ...
    root, "T1_initial_defect", contractPath(root));
end

function verifyInvalid(testCase, root)
verifyError(testCase, @() validatePackage(root), ...
    'toyRoadP0:InvalidTerminalPackage');
end

function root = makeTerminalPackage(testCase, caseId, scope)
if nargin < 3
    scope = "test_only_non_authorizing";
end
fixture = testCase.applyFixture(matlab.unittest.fixtures.TemporaryFolderFixture);
root = fullfile(fixture.Folder, char(caseId));
mkdir(root);
mkdir(fullfile(root, 'substeps'));
mkdir(fullfile(root, 'qualification'));

lockPath = fullfile(root, 'EXECUTION_INPUT_LOCK.json');
lock = fixtureExecutionLock(scope, caseId, fixtureContract(), root);
writeJsonNoClobber(lockPath, lock);
contract = contractForExecutionLock(fixtureContract(), fileSha256(lockPath));

[~, ~, state0, ~] = toyRoadShardFixture(1);
saveNoClobber(fullfile(root, 'STATE0.mat'), 'state0', state0);
for cycle = 1:5
    [shard, ~, ~, ~] = toyRoadShardFixture(cycle);
    shard = applyContract(shard, contract);
    saveNoClobber(fullfile(root, 'substeps', sprintf('cycle_%04d.mat', cycle)), ...
        'shard', shard);
end

tracePath = fullfile(root, 'qualification', 'C5_STAGGER_TRACE.csv');
traceText = sprintf([ ...
    'authorization_scope,case_id,cycle,substep_ordinal,stagger_iteration,' ...
    'reassembly_ordinal,displacement_residual,raw_phase_residual,' ...
    'projected_phase_kkt,consecutive_stagger_delta,primal_feasibility\n' ...
    '%s,%s,5,4,1,1,0.0002,0.0008,0.0003,0.0008,1e-13\n' ...
    '%s,%s,5,4,2,2,1e-05,0.0006,2e-05,3e-05,0\n'], ...
    char(scope), char(caseId), char(scope), char(caseId));
writeTextNoClobber(tracePath, traceText);
writeJsonNoClobber(fullfile(root, 'qualification', ...
    'C5_NUMERICAL_GATE_RECEIPT.json'), completeReceipt(scope, caseId, tracePath));

cycle5Path = fullfile(root, 'substeps', 'cycle_0005.mat');
event = struct('authorization_scope', char(scope), 'case_id', char(caseId), ...
    'first_hit_cycle', 2, 'confirmed_cycle', 5, 'terminal_cycle', 5, ...
    'peak_substep_ordinal', 4, 'cycle_shard', 'substeps/cycle_0005.mat', ...
    'cycle_shard_sha256', fileSha256(cycle5Path));
writeJsonNoClobber(fullfile(root, 'EVENT_METADATA.json'), event);
terminal = struct('authorization_scope', char(scope), 'case_id', char(caseId), ...
    'terminal_reason', 'confirmed_penetration', 'terminal_cycle', 5, ...
    'first_hit_cycle', 2, 'confirmed_cycle', 5);
writeJsonNoClobber(fullfile(root, 'TERMINAL_RESULT.json'), terminal);
writeManifestNoClobber(root, contract, caseId, scope);
end

function receipt = completeReceipt(scope, caseId, tracePath)
receipt = struct('authorization_scope', char(scope), 'case_id', char(caseId), ...
    'cycle', 5, 'substep_ordinal', 4, 'status', 'PASS', 'passed', true, ...
    'trace_sha256', fileSha256(tracePath), 'trace_row_count', 2, ...
    'reassembly_count', 2, 'final_stagger_iteration', 2, ...
    'final_reassembly_ordinal', 2, 'final_displacement_residual', 1e-5, ...
    'final_raw_phase_residual', 6e-4, 'final_projected_phase_kkt', 2e-5, ...
    'final_consecutive_stagger_delta', 3e-5, 'final_primal_feasibility', 0, ...
    'displacement_residual_threshold', 4e-4, ...
    'projected_phase_kkt_threshold', 4e-4, ...
    'consecutive_stagger_delta_threshold', 1e-3, ...
    'primal_feasibility_threshold', 1e-12);
end

function path = contractPath(root)
contract = contractForRoot(fixtureContract(), root);
path = [tempname '.mat'];
save(path, 'contract');
end

function contract = fixtureContract()
[~, ~, ~, contract] = toyRoadShardFixture(1);
end

function lock = fixtureExecutionLock(scope, caseId, contract, root)
matlabIdentity = struct('release', 'R2025b', 'update', 'Update 5', ...
    'version', '25.2.0.3177638', 'computer', 'PCWIN64', ...
    'executable_sha256', repmat('a', 1, 64), 'blas', 'fixture BLAS', ...
    'lapack', 'fixture LAPACK', 'absolute_path_order', {{ ...
    fullfile(root, 'runtime-overlay'), fullfile(root, 'producer-handoff'), ...
    fullfile(root, 'griphfith-sources'), fullfile(root, 'suitesparse-cholmod'), ...
    fullfile(root, 'suitesparse-amd'), fullfile(root, 'suitesparse-colamd'), ...
    fullfile(root, 'suitesparse-ccolamd'), fullfile(root, 'suitesparse-camd')}});
runtimeExpectations = struct('matlab', matlabIdentity, 'binary_sha256', struct( ...
    'initial', repmat('b', 1, 64), 'AMOR', repmat('c', 1, 64), ...
    'AT1_HISTORY_FATIGUE', repmat('d', 1, 64), ...
    'cholmod2', repmat('e', 1, 64)));
writableRoots = struct('output', fullfile(root, 'output'), ...
    'work', fullfile(root, 'work'), 'temp', fullfile(root, 'temp'), ...
    'tmp', fullfile(root, 'tmp'), 'pref', fullfile(root, 'pref'), ...
    'cache', fullfile(root, 'cache'), ...
    'matlab_startup_pref', fullfile(root, 'matlab-startup-pref'));
lock = struct('schema_version', 'toy_road_execution_input_lock_v1', ...
    'protocol_version', 'toy-road-p0-repeatability-v2.1', ...
    'authorization_scope', char(scope), 'case_id', char(caseId), ...
    'family_contract_sha256', contract.family_contract_sha256, ...
    'case_physics_contract_sha256', contract.case_physics_contract_sha256, ...
    'source_commit', repmat('a', 1, 40), ...
    'runtime_lock_sha256', contract.runtime_lock_sha256, ...
    'source_manifest_sha256', repmat('f', 1, 64), ...
    'runtime_expectations', runtimeExpectations, ...
    'writable_roots', writableRoots, ...
    'launch_timestamp_utc', '2026-08-03T12:00:00.0000000Z', ...
    'no_clobber_receipt_id', 'terminal-package-validator', ...
    'resume_allowed', false);
end

function contract = contractForRoot(contract, root)
contract = contractForExecutionLock(contract, ...
    fileSha256(fullfile(root, 'EXECUTION_INPUT_LOCK.json')));
end

function contract = contractForExecutionLock(contract, digest)
contract.execution_input_lock_sha256 = char(digest);
end

function shard = applyContract(shard, contract)
fields = {'mesh_sha256', 'element_ordering_id', 'gp_ordering_id', ...
    'state_semantics_id', 'runtime_lock_sha256', 'family_contract_sha256', ...
    'case_physics_contract_sha256', 'execution_input_lock_sha256'};
for index = 1:numel(fields)
    shard.(fields{index}) = contract.(fields{index});
end
end

function refreshC5ReceiptAndManifest(root)
receiptPath = fullfile(root, 'qualification', 'C5_NUMERICAL_GATE_RECEIPT.json');
receipt = jsondecode(fileread(receiptPath));
receipt.trace_sha256 = fileSha256(fullfile(root, 'qualification', ...
    'C5_STAGGER_TRACE.csv'));
replaceJson(receiptPath, receipt);
refreshManifest(root);
end

function replaceFirstHit(root, firstHit)
eventPath = fullfile(root, 'EVENT_METADATA.json');
event = jsondecode(fileread(eventPath));
event.first_hit_cycle = firstHit;
replaceJson(eventPath, event);
terminalPath = fullfile(root, 'TERMINAL_RESULT.json');
terminal = jsondecode(fileread(terminalPath));
terminal.first_hit_cycle = firstHit;
replaceJson(terminalPath, terminal);
refreshManifest(root);
end

function replaceC5Ordinals(root, stagger, reassembly)
tracePath = fullfile(root, 'qualification', 'C5_STAGGER_TRACE.csv');
trace = readtable(tracePath, 'TextType', 'string', ...
    'VariableNamingRule', 'preserve');
trace.stagger_iteration = stagger;
trace.reassembly_ordinal = reassembly;
delete(tracePath);
writetable(trace, tracePath);
receiptPath = fullfile(root, 'qualification', ...
    'C5_NUMERICAL_GATE_RECEIPT.json');
receipt = jsondecode(fileread(receiptPath));
receipt.trace_sha256 = fileSha256(tracePath);
receipt.trace_row_count = height(trace);
receipt.reassembly_count = height(trace);
receipt.final_stagger_iteration = stagger(end);
receipt.final_reassembly_ordinal = reassembly(end);
replaceJson(receiptPath, receipt);
refreshManifest(root);
end

function refreshManifest(root)
path = fullfile(root, 'TERMINAL_MANIFEST.json');
manifest = jsondecode(fileread(path));
manifest.files = manifestEntries(root);
replaceJson(path, manifest);
end

function writeManifestNoClobber(root, contract, caseId, scope)
manifest = struct('authorization_scope', char(scope), ...
    'protocol_version', 'toy-road-p0-repeatability-v2.1', ...
    'case_id', char(caseId), 'source_commit', repmat('a', 1, 40), ...
    'mesh_sha256', contract.mesh_sha256, ...
    'element_ordering_id', contract.element_ordering_id, ...
    'gp_ordering_id', contract.gp_ordering_id, ...
    'state_semantics_id', contract.state_semantics_id, ...
    'runtime_lock_sha256', contract.runtime_lock_sha256, ...
    'family_contract_sha256', contract.family_contract_sha256, ...
    'case_physics_contract_sha256', contract.case_physics_contract_sha256, ...
    'physical_input_sha256', repmat('5', 1, 64), ...
    'solver_sha256', repmat('6', 1, 64), ...
    'recovery_sha256', repmat('7', 1, 64), ...
    'exporter_sha256', repmat('8', 1, 64), ...
    'numerical_gate_contract_sha256', repmat('9', 1, 64), ...
    'event_contract_sha256', repmat('0', 1, 64), ...
    'execution_input_lock_sha256', contract.execution_input_lock_sha256, ...
    'files', manifestEntries(root));
writeJsonNoClobber(fullfile(root, 'TERMINAL_MANIFEST.json'), manifest);
end

function files = manifestEntries(root)
allFiles = dir(fullfile(root, '**', '*'));
allFiles = allFiles(~[allFiles.isdir]);
paths = strings(0, 1);
hashes = strings(0, 1);
for index = 1:numel(allFiles)
    absolute = fullfile(allFiles(index).folder, allFiles(index).name);
    relative = replace(erase(string(absolute), string(root) + filesep), '\', '/');
    if relative == "TERMINAL_MANIFEST.json"
        continue;
    end
    paths(end + 1, 1) = relative; %#ok<AGROW>
    hashes(end + 1, 1) = string(fileSha256(absolute)); %#ok<AGROW>
end
[paths, order] = sort(paths);
hashes = hashes(order);
files = repmat(struct('path', '', 'sha256', ''), numel(paths), 1);
for index = 1:numel(paths)
    files(index).path = char(paths(index));
    files(index).sha256 = char(hashes(index));
end
end

function replaceMat(path, name, value)
delete(path);
saveNoClobber(path, name, value);
end

function saveNoClobber(path, name, value)
if isfile(path)
    error('toyRoadTest:FixtureClobber', 'Fixture path already exists: %s', path);
end
payload = struct();
payload.(name) = value;
save(path, '-struct', 'payload');
end

function writeJsonNoClobber(path, value)
writeTextNoClobber(path, [jsonencode(value) newline]);
end

function replaceJson(path, value)
delete(path);
writeJsonNoClobber(path, value);
end

function writeReplacementText(path, value)
delete(path);
writeTextNoClobber(path, value);
end

function writeTextNoClobber(path, value)
if isfile(path)
    error('toyRoadTest:FixtureClobber', 'Fixture path already exists: %s', path);
end
fileId = fopen(path, 'wb');
if fileId < 0
    error('toyRoadTest:FixtureWriteFailed', 'Cannot write fixture: %s', path);
end
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, unicode2native(char(value), 'UTF-8'), 'uint8');
end

function created = createFileSymlink(linkPath, targetPath)
if ispc
    command = sprintf('cmd /c mklink "%s" "%s" >nul 2>&1', linkPath, targetPath);
else
    command = sprintf('ln -s "%s" "%s"', targetPath, linkPath);
end
created = system(command) == 0;
end

function created = createDirectoryLink(linkPath, targetPath)
if ispc
    command = sprintf('cmd /c mklink /J "%s" "%s" >nul 2>&1', linkPath, targetPath);
else
    command = sprintf('ln -s "%s" "%s"', targetPath, linkPath);
end
created = system(command) == 0;
end

function digest = fileSha256(path)
fileId = fopen(path, 'rb');
if fileId < 0
    error('toyRoadTest:FixtureReadFailed', 'Cannot read fixture: %s', path);
end
cleanup = onCleanup(@() fclose(fileId));
bytes = fread(fileId, Inf, '*uint8');
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(bytes);
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end
