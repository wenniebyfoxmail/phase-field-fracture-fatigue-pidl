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
summary = validate_toy_road_terminal_package( ...
    root, "T1_initial_defect", contractPath());
verifyTrue(testCase, summary.is_valid);
verifyEqual(testCase, summary.terminal_cycle, 5);
verifyEqual(testCase, summary.cycle_count, 5);
verifyEqual(testCase, summary.case_id, 'T1_initial_defect');
end

function testAcceptsAlternateNonAuthorizingMetadataScope(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
scope = 'synthetic_review_non_authorizing';
paths = { ...
    fullfile(root, 'qualification', 'C5_NUMERICAL_GATE_RECEIPT.json'), ...
    fullfile(root, 'EVENT_METADATA.json'), ...
    fullfile(root, 'TERMINAL_RESULT.json')};
for index = 1:numel(paths)
    value = jsondecode(fileread(paths{index}));
    value.authorization_scope = scope;
    replaceJson(paths{index}, value);
end
refreshManifestWithScope(root, scope);
summary = validate_toy_road_terminal_package( ...
    root, "T1_initial_defect", contractPath());
verifyTrue(testCase, summary.is_valid);
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
shard = applyContract(shard, contractForExecutionLock(contract, executionDigest()));
save(fullfile(root, 'substeps', 'cycle_0006.mat'), 'shard');
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsWrongCaseLocalMeshHash(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'substeps', 'cycle_0002.mat');
loaded = load(path, 'shard');
loaded.shard.mesh_sha256(1) = '0';
delete(path);
shard = loaded.shard; %#ok<NASGU>
save(path, 'shard');
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
verifyError(testCase, ...
    @() validate_toy_road_terminal_package(root, "T1_initial_defect", contractPath()), ...
    'toyRoadP0:InvalidTerminalPackage');
end

function testRejectsFailedCaseLocalC5Receipt(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'qualification', 'C5_NUMERICAL_GATE_RECEIPT.json');
receipt = jsondecode(fileread(path));
receipt.status = 'FAIL';
replaceJson(path, receipt);
refreshManifest(root);
verifyInvalid(testCase, root);
end

function testRejectsBytesChangedAfterManifestFinalization(testCase)
root = makeTerminalPackage(testCase, "T1_initial_defect");
path = fullfile(root, 'TERMINAL_RESULT.json');
terminal = jsondecode(fileread(path));
terminal.terminal_reason = 'right_censored';
replaceJson(path, terminal);
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

function verifyInvalid(testCase, root)
verifyError(testCase, ...
    @() validate_toy_road_terminal_package(root, "T1_initial_defect", contractPath()), ...
    'toyRoadP0:InvalidTerminalPackage');
end

function root = makeTerminalPackage(testCase, caseId)
fixture = testCase.applyFixture(matlab.unittest.fixtures.TemporaryFolderFixture);
root = fullfile(fixture.Folder, char(caseId));
mkdir(root);
mkdir(fullfile(root, 'substeps'));
mkdir(fullfile(root, 'qualification'));

lockPath = fullfile(root, 'EXECUTION_INPUT_LOCK.json');
writeTextNoClobber(lockPath, executionLockText());
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
traceText = sprintf(['authorization_scope,case_id,cycle,substep_ordinal,' ...
    'stagger_iteration,displacement_residual,projected_phase_kkt,' ...
    'consecutive_stagger_delta,primal_feasibility\n' ...
    'test_only_non_authorizing,%s,5,4,1,1e-5,2e-5,3e-5,0\n'], char(caseId));
writeTextNoClobber(tracePath, traceText);

receipt = struct( ...
    'authorization_scope', 'test_only_non_authorizing', ...
    'case_id', char(caseId), 'cycle', 5, 'substep_ordinal', 4, ...
    'status', 'PASS', 'trace_sha256', fileSha256(tracePath));
writeJsonNoClobber(fullfile(root, 'qualification', ...
    'C5_NUMERICAL_GATE_RECEIPT.json'), receipt);

cycle5Path = fullfile(root, 'substeps', 'cycle_0005.mat');
event = struct( ...
    'authorization_scope', 'test_only_non_authorizing', ...
    'case_id', char(caseId), 'first_hit_cycle', 4, 'confirmed_cycle', 5, ...
    'terminal_cycle', 5, 'peak_substep_ordinal', 4, ...
    'cycle_shard', 'substeps/cycle_0005.mat', ...
    'cycle_shard_sha256', fileSha256(cycle5Path));
writeJsonNoClobber(fullfile(root, 'EVENT_METADATA.json'), event);

terminal = struct( ...
    'authorization_scope', 'test_only_non_authorizing', ...
    'case_id', char(caseId), 'terminal_reason', 'confirmed_penetration', ...
    'terminal_cycle', 5, 'first_hit_cycle', 4, 'confirmed_cycle', 5);
writeJsonNoClobber(fullfile(root, 'TERMINAL_RESULT.json'), terminal);
writeManifestNoClobber(root, contract, caseId, 'test_only_non_authorizing');
end

function path = contractPath()
root = tempname;
mkdir(root);
contract = contractForExecutionLock(fixtureContract(), executionDigest());
path = fullfile(root, 'CONTRACT.mat');
save(path, 'contract');
end

function contract = fixtureContract()
[~, ~, ~, contract] = toyRoadShardFixture(1);
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

function digest = executionDigest()
path = [tempname '.json'];
writeTextNoClobber(path, executionLockText());
cleanup = onCleanup(@() delete(path)); %#ok<NASGU>
digest = fileSha256(path);
end

function value = executionLockText()
value = sprintf(['{"authorization_scope":"test_only_non_authorizing",' ...
    '"fixture_id":"terminal_package_validator"}\n']);
end

function refreshManifest(root)
path = fullfile(root, 'TERMINAL_MANIFEST.json');
old = jsondecode(fileread(path));
refreshManifestWithScope(root, old.authorization_scope);
end

function refreshManifestWithScope(root, scope)
path = fullfile(root, 'TERMINAL_MANIFEST.json');
old = jsondecode(fileread(path));
delete(path);
contract = contractForExecutionLock(fixtureContract(), executionDigest());
writeManifestNoClobber(root, contract, string(old.case_id), scope);
end

function writeManifestNoClobber(root, contract, caseId, scope)
allFiles = dir(fullfile(root, '**', '*'));
allFiles = allFiles(~[allFiles.isdir]);
paths = strings(0, 1);
hashes = strings(0, 1);
for index = 1:numel(allFiles)
    absolute = fullfile(allFiles(index).folder, allFiles(index).name);
    relative = erase(string(absolute), string(root) + filesep);
    relative = replace(relative, '\', '/');
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
manifest = struct( ...
    'authorization_scope', char(scope), ...
    'protocol_version', 'toy-road-p0-repeatability-v2.1-test', ...
    'case_id', char(caseId), 'source_commit', repmat('a', 1, 40), ...
    'exporter_sha256', repmat('6', 1, 64), ...
    'runtime_lock_sha256', contract.runtime_lock_sha256, ...
    'family_contract_sha256', contract.family_contract_sha256, ...
    'case_physics_contract_sha256', contract.case_physics_contract_sha256, ...
    'execution_input_lock_sha256', contract.execution_input_lock_sha256, ...
    'files', files);
writeJsonNoClobber(fullfile(root, 'TERMINAL_MANIFEST.json'), manifest);
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

function writeTextNoClobber(path, value)
if isfile(path)
    error('toyRoadTest:FixtureClobber', 'Fixture path already exists: %s', path);
end
fileId = fopen(path, 'wb');
if fileId < 0
    error('toyRoadTest:FixtureWriteFailed', 'Cannot write fixture: %s', path);
end
cleanup = onCleanup(@() fclose(fileId)); %#ok<NASGU>
fwrite(fileId, unicode2native(char(value), 'UTF-8'), 'uint8');
end

function digest = fileSha256(path)
fileId = fopen(path, 'rb');
if fileId < 0
    error('toyRoadTest:FixtureReadFailed', 'Cannot read fixture: %s', path);
end
cleanup = onCleanup(@() fclose(fileId)); %#ok<NASGU>
bytes = fread(fileId, Inf, '*uint8');
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(bytes);
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end
