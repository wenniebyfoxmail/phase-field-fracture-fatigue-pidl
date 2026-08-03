function summary = validate_toy_road_terminal_package(root, case_id, contract_path)
%VALIDATE_TOY_ROAD_TERMINAL_PACKAGE Validate one closed immutable case package.

try
    summary = localValidate(root, case_id, contract_path);
catch exception
    if strcmp(exception.identifier, 'toyRoadP0:InvalidTerminalPackage')
        rethrow(exception);
    end
    error('toyRoadP0:InvalidTerminalPackage', '%s', exception.message);
end
end

function summary = localValidate(root, caseId, contractPath)
root = localExistingFolder(root, 'root');
caseId = localText(caseId, 'case_id');
contractPath = localExistingFile(contractPath, 'contract_path');
loadedContract = load(contractPath, 'contract');
localRequire(isfield(loadedContract, 'contract') && ...
    isstruct(loadedContract.contract) && isscalar(loadedContract.contract), ...
    'contract_path must contain one scalar contract struct.');
contract = loadedContract.contract;
requiredContract = {'mesh_sha256', 'element_ordering_id', 'gp_ordering_id', ...
    'state_semantics_id', 'runtime_lock_sha256', 'family_contract_sha256', ...
    'case_physics_contract_sha256', 'execution_input_lock_sha256'};
localRequireFields(contract, requiredContract, 'contract');

manifestPath = fullfile(root, 'TERMINAL_MANIFEST.json');
manifest = localReadJson(manifestPath, 'terminal manifest');
requiredManifest = {'authorization_scope', 'protocol_version', 'case_id', ...
    'source_commit', 'exporter_sha256', 'runtime_lock_sha256', ...
    'family_contract_sha256', 'case_physics_contract_sha256', ...
    'execution_input_lock_sha256', 'files'};
localRequireFields(manifest, requiredManifest, 'terminal manifest');
localRequire(strcmp(localText(manifest.case_id, 'manifest case_id'), caseId), ...
    'Terminal manifest case_id does not match the requested case.');
authorizationScope = localText(manifest.authorization_scope, ...
    'manifest authorization_scope');
localRequire(localCanonicalGitCommit(manifest.source_commit), ...
    'Manifest source_commit must be canonical lowercase hexadecimal text.');
localRequire(localCanonicalSha(manifest.exporter_sha256), ...
    'Manifest exporter_sha256 is not canonical SHA-256 text.');
localRequireIdentity(manifest, contract, requiredContract(5:8));

[manifestPaths, manifestHashes] = localManifestEntries(manifest.files);
actualPaths = localPackageFiles(root);
localRequire(isequal(manifestPaths, sort(manifestPaths)) && ...
    numel(unique(manifestPaths)) == numel(manifestPaths), ...
    'Terminal manifest paths must be sorted and unique.');
localRequire(isequal(manifestPaths, actualPaths), ...
    'Terminal manifest does not exactly close over package files.');
for index = 1:numel(manifestPaths)
    localRequire(strcmp(fileSha256(localFromRelative(root, manifestPaths(index))), ...
        manifestHashes(index)), 'Package bytes do not match the terminal manifest.');
end

requiredPaths = [ ...
    "EXECUTION_INPUT_LOCK.json"; "STATE0.mat"; "EVENT_METADATA.json"; ...
    "TERMINAL_RESULT.json"; "qualification/C5_STAGGER_TRACE.csv"; ...
    "qualification/C5_NUMERICAL_GATE_RECEIPT.json"];
localRequire(all(ismember(requiredPaths, manifestPaths)), ...
    'Terminal package is missing a required case-local artifact.');

executionPath = fullfile(root, 'EXECUTION_INPUT_LOCK.json');
executionDigest = fileSha256(executionPath);
localRequire(strcmp(executionDigest, localText( ...
    manifest.execution_input_lock_sha256, 'manifest execution digest')) && ...
    strcmp(executionDigest, localText( ...
    contract.execution_input_lock_sha256, 'contract execution digest')), ...
    'Execution-lock digest is inconsistent with its own manifest or contract.');

tracePath = fullfile(root, 'qualification', 'C5_STAGGER_TRACE.csv');
receiptPath = fullfile(root, 'qualification', 'C5_NUMERICAL_GATE_RECEIPT.json');
receipt = localReadJson(receiptPath, 'c5 receipt');
localRequireFields(receipt, {'authorization_scope', 'case_id', 'cycle', ...
    'substep_ordinal', 'status', 'trace_sha256'}, 'c5 receipt');
localRequire(strcmp(localText(receipt.authorization_scope, ...
    'c5 authorization_scope'), authorizationScope) && ...
    strcmp(localText(receipt.case_id, 'c5 case_id'), caseId) && ...
    localIntegerEquals(receipt.cycle, 5) && ...
    localIntegerEquals(receipt.substep_ordinal, 4) && ...
    strcmp(localText(receipt.status, 'c5 status'), 'PASS') && ...
    strcmp(localText(receipt.trace_sha256, 'c5 trace_sha256'), ...
    fileSha256(tracePath)), ...
    'Case-local c5 trace or PASS receipt is invalid.');

event = localReadJson(fullfile(root, 'EVENT_METADATA.json'), 'event metadata');
terminal = localReadJson(fullfile(root, 'TERMINAL_RESULT.json'), 'terminal result');
localRequireFields(event, {'authorization_scope', 'case_id', 'first_hit_cycle', ...
    'confirmed_cycle', 'terminal_cycle', 'peak_substep_ordinal', ...
    'cycle_shard', 'cycle_shard_sha256'}, 'event metadata');
localRequireFields(terminal, {'authorization_scope', 'case_id', ...
    'terminal_reason', 'terminal_cycle', 'first_hit_cycle', ...
    'confirmed_cycle'}, 'terminal result');
localRequire(strcmp(localText(event.case_id, 'event case_id'), caseId) && ...
    strcmp(localText(terminal.case_id, 'terminal case_id'), caseId), ...
    'Event or terminal case_id is not case-local.');
localRequire(strcmp(localText(event.authorization_scope, ...
    'event authorization_scope'), authorizationScope) && ...
    strcmp(localText(terminal.authorization_scope, ...
    'terminal authorization_scope'), authorizationScope), ...
    'Event, terminal and manifest authorization scopes are inconsistent.');
localRequire(localSameScalar(event.first_hit_cycle, terminal.first_hit_cycle) && ...
    localSameScalar(event.confirmed_cycle, terminal.confirmed_cycle) && ...
    localSameScalar(event.terminal_cycle, terminal.terminal_cycle) && ...
    localIntegerEquals(event.peak_substep_ordinal, 4), ...
    'Event metadata and terminal result are inconsistent.');
terminalCycle = terminal.terminal_cycle;
localRequire(localPositiveInteger(terminalCycle) && terminalCycle >= 5, ...
    'Terminal cycle must be an integer at or after the case-local c5 gate.');

cyclePaths = manifestPaths(startsWith(manifestPaths, "substeps/cycle_") & ...
    endsWith(manifestPaths, ".mat"));
cycleNumbers = zeros(numel(cyclePaths), 1);
for index = 1:numel(cyclePaths)
    token = regexp(char(cyclePaths(index)), ...
        '^substeps/cycle_([0-9]{4})\.mat$', 'tokens', 'once');
    localRequire(~isempty(token), 'Cycle shard path is not canonical.');
    cycleNumbers(index) = str2double(token{1});
end
localRequire(isequal(cycleNumbers, (1:terminalCycle).'), ...
    'Cycle shards must be exactly consecutive from c1 through terminal.');

state = load(fullfile(root, 'STATE0.mat'), 'state0');
localRequire(isfield(state, 'state0') && isstruct(state.state0) && ...
    isscalar(state.state0), 'STATE0.mat must contain one scalar state0 struct.');
previous = [];
maxIdentityError = 0;
minimumDamageDelta = Inf;
minimumAlphaDelta = Inf;
for cycle = 1:terminalCycle
    cyclePath = fullfile(root, 'substeps', sprintf('cycle_%04d.mat', cycle));
    loaded = load(cyclePath, 'shard');
    localRequire(isfield(loaded, 'shard') && isstruct(loaded.shard) && ...
        isscalar(loaded.shard), 'Every cycle MAT must contain one scalar shard.');
    metrics = validate_toy_road_cycle_shard( ...
        loaded.shard, previous, state.state0, contract);
    maxIdentityError = max(maxIdentityError, metrics.identity_max_abs_error);
    minimumDamageDelta = min(minimumDamageDelta, ...
        metrics.damage_history_min_delta);
    minimumAlphaDelta = min(minimumAlphaDelta, metrics.alpha_history_min_delta);
    previous = loaded.shard;
end

eventCyclePath = localText(event.cycle_shard, 'event cycle_shard');
expectedEventPath = sprintf('substeps/cycle_%04d.mat', event.confirmed_cycle);
localRequire(strcmp(eventCyclePath, expectedEventPath) && ...
    strcmp(localText(event.cycle_shard_sha256, 'event shard digest'), ...
    fileSha256(localFromRelative(root, string(eventCyclePath)))), ...
    'Event metadata does not byte-identify its cycle peak shard.');

summary = struct( ...
    'is_valid', true, 'case_id', caseId, ...
    'terminal_cycle', terminalCycle, 'cycle_count', numel(cycleNumbers), ...
    'manifest_sha256', fileSha256(manifestPath), ...
    'c5_receipt_sha256', fileSha256(receiptPath), ...
    'identity_max_abs_error', maxIdentityError, ...
    'damage_history_min_delta', minimumDamageDelta, ...
    'alpha_history_min_delta', minimumAlphaDelta);
end

function [paths, hashes] = localManifestEntries(files)
localRequire(isstruct(files) && ~isempty(files), ...
    'Terminal manifest files must be a nonempty struct array.');
paths = strings(numel(files), 1);
hashes = strings(numel(files), 1);
for index = 1:numel(files)
    localRequireFields(files(index), {'path', 'sha256'}, 'manifest file entry');
    paths(index) = string(localText(files(index).path, 'manifest path'));
    hashes(index) = string(localText(files(index).sha256, 'manifest sha256'));
    localRequire(~startsWith(paths(index), "/") && ...
        ~contains(paths(index), "\") && ~contains(paths(index), "..") && ...
        localCanonicalSha(hashes(index)), 'Manifest file entry is not canonical.');
end
end

function paths = localPackageFiles(root)
entries = dir(fullfile(root, '**', '*'));
entries = entries(~[entries.isdir]);
paths = strings(0, 1);
for index = 1:numel(entries)
    absolute = fullfile(entries(index).folder, entries(index).name);
    relative = erase(string(absolute), string(root) + filesep);
    relative = replace(relative, '\', '/');
    if relative ~= "TERMINAL_MANIFEST.json"
        paths(end + 1, 1) = relative; %#ok<AGROW>
    end
end
paths = sort(paths);
end

function path = localFromRelative(root, relative)
parts = split(relative, '/');
path = root;
for index = 1:numel(parts)
    path = fullfile(path, char(parts(index)));
end
end

function localRequireIdentity(manifest, contract, names)
for index = 1:numel(names)
    name = names{index};
    localRequire(localCanonicalSha(manifest.(name)) && ...
        localCanonicalSha(contract.(name)) && ...
        strcmp(localText(manifest.(name), name), ...
        localText(contract.(name), name)), ...
        'Manifest identity %s does not match the contract.', name);
end
end

function value = localReadJson(path, label)
path = localExistingFile(path, label);
value = jsondecode(fileread(path));
localRequire(isstruct(value) && isscalar(value), '%s must be one JSON object.', label);
end

function path = localExistingFolder(path, label)
path = localText(path, label);
localRequire(isfolder(path), '%s must name an existing folder.', label);
end

function path = localExistingFile(path, label)
path = localText(path, label);
localRequire(isfile(path), '%s must name an existing file.', label);
end

function value = localText(value, label)
isText = (ischar(value) && isrow(value)) || (isstring(value) && isscalar(value));
localRequire(isText && strlength(string(value)) > 0, '%s must be scalar text.', label);
value = char(value);
end

function localRequireFields(value, names, label)
for index = 1:numel(names)
    localRequire(isfield(value, names{index}), ...
        '%s is missing required field %s.', label, names{index});
end
end

function value = localCanonicalSha(input)
isText = (ischar(input) && isrow(input)) || ...
    (isstring(input) && isscalar(input));
value = isText && ~isempty(regexp(char(input), '^[0-9a-f]{64}$', 'once'));
end

function value = localCanonicalGitCommit(input)
isText = (ischar(input) && isrow(input)) || ...
    (isstring(input) && isscalar(input));
value = isText && ~isempty(regexp(char(input), '^[0-9a-f]{40}$', 'once'));
end

function value = localIntegerEquals(input, expected)
value = localPositiveInteger(input) && input == expected;
end

function value = localPositiveInteger(input)
value = isnumeric(input) && isreal(input) && isscalar(input) && ...
    isfinite(input) && input >= 1 && input == floor(input);
end

function value = localSameScalar(left, right)
value = isnumeric(left) && isnumeric(right) && isscalar(left) && ...
    isscalar(right) && isequaln(left, right);
end

function digest = fileSha256(path)
fileId = fopen(path, 'rb');
localRequire(fileId >= 0, 'Cannot read package file: %s', path);
cleanup = onCleanup(@() fclose(fileId)); %#ok<NASGU>
bytes = fread(fileId, Inf, '*uint8');
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(bytes);
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end

function localRequire(condition, message, varargin)
if ~condition
    error('toyRoadP0:InvalidTerminalPackage', message, varargin{:});
end
end
