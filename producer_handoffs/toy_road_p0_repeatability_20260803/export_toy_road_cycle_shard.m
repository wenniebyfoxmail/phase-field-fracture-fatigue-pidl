function [shard, peakMetadata] = export_toy_road_cycle_shard(capture, outputRoot, contract)
%EXPORT_TOY_ROAD_CYCLE_SHARD Validate and exclusively publish one MAT v7.3 shard.

localRequireComplete(capture);
localRequireText(outputRoot, 'outputRoot must be nonempty scalar text.');
canonical = localCanonicalContract(contract);
localRequire(strcmp(capture.mesh_sha256, canonical.mesh_sha256) && ...
    strcmp(capture.element_ordering_id, canonical.element_ordering_id) && ...
    strcmp(capture.gp_ordering_id, canonical.gp_ordering_id), ...
    'capture mesh identities do not match the export contract.');

dNode = double(capture.d_node);
dGp = double(capture.d_gp);
alphaBarGp = double(capture.alpha_bar_gp);
fAlphaGp = double(capture.f_alpha_gp);
psiRawGp = double(capture.psi_raw_gp);
gGp = (1 - dGp).^2 + canonical.eta;
psiActiveGp = gGp .* psiRawGp;
shard = struct( ...
    'cycle', double(capture.cycle), ...
    'd_node', dNode, ...
    'd_gp', dGp, ...
    'alpha_bar_gp', alphaBarGp, ...
    'f_alpha_gp', fAlphaGp, ...
    'psi_raw_gp', psiRawGp, ...
    'g_gp', gGp, ...
    'psi_active_gp', psiActiveGp, ...
    'psi_raw_cyclemax_gp', max(psiRawGp, [], 3), ...
    'substep_ordinal', double(1:5), ...
    'load_factor', double([.25 .5 .75 1 0]), ...
    'raw_step_zero_based', double(5 * (capture.cycle - 1) + (0:4)), ...
    'branch', {{'loading','loading','loading','loading','unloading'}}, ...
    'mesh_sha256', canonical.mesh_sha256, ...
    'element_ordering_id', canonical.element_ordering_id, ...
    'gp_ordering_id', canonical.gp_ordering_id, ...
    'state_semantics_id', canonical.state_semantics_id, ...
    'runtime_lock_sha256', canonical.runtime_lock_sha256, ...
    'family_contract_sha256', canonical.family_contract_sha256, ...
    'case_physics_contract_sha256', canonical.case_physics_contract_sha256, ...
    'execution_input_lock_sha256', canonical.execution_input_lock_sha256);

validate_toy_road_cycle_shard(shard, capture.previous, capture.state0, canonical);

root = char(outputRoot);
substepsDir = fullfile(root, 'substeps');
finalName = sprintf('cycle_%04d.mat', capture.cycle);
finalPath = fullfile(substepsDir, finalName);
localCreateDirectory(root);
localCreateDirectory(substepsDir);

temporaryPath = localCreateReservedTemporary(substepsDir);
cleanup = onCleanup(@() localDeleteIfPresent(temporaryPath));
save(temporaryPath, 'shard', '-v7.3');
cycleShardSha256 = localFileSha256(temporaryPath);
localInvokeTestOnlyBeforePublishHook(contract, finalPath, temporaryPath);
localPublishExclusiveHardLink(temporaryPath, finalPath);
localDeleteIfPresent(temporaryPath);
clear cleanup

fieldNames = {'d_node','d_gp','alpha_bar_gp','f_alpha_gp', ...
    'psi_raw_gp','g_gp','psi_active_gp'};
substepDimensions = num2cell([2 3 3 3 3 3 3]);
fieldSlices = struct('field', fieldNames, ...
    'substep_dimension', substepDimensions, ...
    'substep_index', repmat({4}, 1, numel(fieldNames)));
peakMetadata = struct( ...
    'cycle_shard', ['substeps/' finalName], ...
    'cycle_shard_sha256', cycleShardSha256, ...
    'peak_substep_ordinal', 4, ...
    'field_slices', fieldSlices);
end

function canonical = localCanonicalContract(contract)
required = {'eta','alpha_T','p','mesh_sha256','element_ordering_id', ...
    'gp_ordering_id','state_semantics_id','runtime_lock_sha256', ...
    'family_contract_sha256','case_physics_contract_sha256', ...
    'execution_input_lock_sha256'};
localRequire(isstruct(contract) && isscalar(contract) && all(isfield(contract, required)), ...
    'contract is missing required exporter fields.');
numeric = {'eta','alpha_T','p'};
for index = 1:numel(numeric)
    value = contract.(numeric{index});
    localRequire(isnumeric(value) && isreal(value) && isscalar(value) && isfinite(value), ...
        'contract numeric fields must be finite real scalars.');
    canonical.(numeric{index}) = double(value);
end
text = required(4:end);
for index = 1:numel(text)
    canonical.(text{index}) = localCanonicalText(contract.(text{index}));
end
end

function value = localCanonicalText(value)
valid = (ischar(value) && isrow(value)) || (isstring(value) && isscalar(value));
localRequire(valid, 'contract identities must be scalar character or string text.');
value = char(value);
localRequire(isrow(value), 'canonical contract identities must be character rows.');
end

function localRequireComplete(capture)
required = {'cycle','previous','state0','commit_state','next_substep_ordinal', ...
    'mesh_sha256','element_ordering_id','gp_ordering_id','d_node','d_gp', ...
    'alpha_bar_gp','f_alpha_gp','psi_raw_gp'};
valid = isstruct(capture) && isscalar(capture) && all(isfield(capture, required)) && ...
    isequal(capture.next_substep_ordinal, 6);
if valid
    valid = capture.commit_state.get() == 6;
    arrays = {'d_node','d_gp','alpha_bar_gp','f_alpha_gp','psi_raw_gp'};
    for index = 1:numel(arrays)
        value = capture.(arrays{index});
        valid = valid && isa(value, 'double') && isreal(value) && ...
            all(isfinite(value), 'all');
    end
end
if ~valid
    error('toyRoadP0:InvalidCycleCapture', ...
        'All five single-commit substep slices are required before export.');
end
end

function localCreateDirectory(path)
if isfolder(path)
    return;
end
[created, message] = mkdir(path);
if ~created
    error('toyRoadP0:PublicationFailed', 'Cannot create output directory: %s', message);
end
end

function temporaryPath = localCreateReservedTemporary(directory)
try
    directoryPath = java.io.File(directory).toPath();
    attributes = javaArray('java.nio.file.attribute.FileAttribute', 0);
    temporary = java.nio.file.Files.createTempFile( ...
        directoryPath, '.cycle_', '.mat', attributes);
    temporaryPath = char(temporary.toString());
catch exception
    error('toyRoadP0:PublicationFailed', ...
        'Cannot atomically reserve temporary shard: %s', exception.message);
end
end

function localPublishExclusiveHardLink(temporaryPath, finalPath)
try
    temporary = java.io.File(temporaryPath).toPath();
    destination = java.io.File(finalPath).toPath();
    java.nio.file.Files.createLink(destination, temporary);
catch exception
    if isfile(finalPath) || isfolder(finalPath)
        error('toyRoadP0:PublicationClobber', ...
            'Cycle shard destination already exists: %s', finalPath);
    end
    error('toyRoadP0:PublicationFailed', ...
        'Cannot exclusively publish cycle shard: %s', exception.message);
end
end

function localInvokeTestOnlyBeforePublishHook(contract, finalPath, temporaryPath)
if ~isfield(contract, 'test_only_before_publish_hook')
    return;
end
hook = contract.test_only_before_publish_hook;
localRequire(isa(hook, 'function_handle'), 'test-only publication hook must be callable.');
details = functions(hook);
expectedTestFile = fullfile('tests', 'toyRoadCycleExporterTest.m');
localRequire(isfield(details, 'file') && endsWith(details.file, expectedTestFile), ...
    'publication hook is restricted to the Task 3 test file.');
hook(finalPath, temporaryPath);
end

function localRequireText(value, message)
valid = (ischar(value) && isrow(value) && ~isempty(value)) || ...
    (isstring(value) && isscalar(value) && strlength(value) > 0);
if ~valid
    error('toyRoadP0:InvalidCycleCapture', message);
end
end

function digest = localFileSha256(path)
fileId = fopen(path, 'rb');
if fileId < 0
    error('toyRoadP0:PublicationFailed', 'Cannot hash temporary shard: %s', path);
end
cleanup = onCleanup(@() fclose(fileId));
bytes = fread(fileId, Inf, '*uint8');
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(bytes);
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end

function localDeleteIfPresent(path)
if isfile(path)
    delete(path);
end
end

function localRequire(condition, message)
if ~condition
    error('toyRoadP0:InvalidCycleCapture', message);
end
end
