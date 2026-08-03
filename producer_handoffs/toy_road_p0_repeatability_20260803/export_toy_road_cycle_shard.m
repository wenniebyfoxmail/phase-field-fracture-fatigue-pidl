function [shard, peakMetadata] = export_toy_road_cycle_shard(capture, outputRoot, contract)
%EXPORT_TOY_ROAD_CYCLE_SHARD Validate and atomically publish one MAT v7.3 shard.

localRequireComplete(capture);
localRequireText(outputRoot, 'outputRoot must be nonempty scalar text.');

gGp = (1 - capture.d_gp).^2 + contract.eta;
psiActiveGp = gGp .* capture.psi_raw_gp;
shard = struct( ...
    'cycle', capture.cycle, ...
    'd_node', capture.d_node, ...
    'd_gp', capture.d_gp, ...
    'alpha_bar_gp', capture.alpha_bar_gp, ...
    'f_alpha_gp', capture.f_alpha_gp, ...
    'psi_raw_gp', capture.psi_raw_gp, ...
    'g_gp', gGp, ...
    'psi_active_gp', psiActiveGp, ...
    'psi_raw_cyclemax_gp', max(capture.psi_raw_gp, [], 3), ...
    'substep_ordinal', 1:5, ...
    'load_factor', [.25 .5 .75 1 0], ...
    'raw_step_zero_based', 5 * (capture.cycle - 1) + (0:4), ...
    'branch', {{'loading','loading','loading','loading','unloading'}}, ...
    'mesh_sha256', contract.mesh_sha256, ...
    'element_ordering_id', contract.element_ordering_id, ...
    'gp_ordering_id', contract.gp_ordering_id, ...
    'state_semantics_id', contract.state_semantics_id, ...
    'runtime_lock_sha256', contract.runtime_lock_sha256, ...
    'family_contract_sha256', contract.family_contract_sha256, ...
    'case_physics_contract_sha256', contract.case_physics_contract_sha256, ...
    'execution_input_lock_sha256', contract.execution_input_lock_sha256);

validate_toy_road_cycle_shard(shard, capture.previous, capture.state0, contract);

root = char(outputRoot);
substepsDir = fullfile(root, 'substeps');
finalName = sprintf('cycle_%04d.mat', capture.cycle);
finalPath = fullfile(substepsDir, finalName);
if isfile(finalPath) || isfolder(finalPath)
    error('toyRoadP0:PublicationClobber', ...
        'Cycle shard destination already exists: %s', finalPath);
end
if ~isfolder(root)
    [created, message] = mkdir(root);
    localRequirePublication(created, message);
end
if ~isfolder(substepsDir)
    [created, message] = mkdir(substepsDir);
    localRequirePublication(created, message);
end

temporaryPath = [tempname(substepsDir) '.mat'];
cleanup = onCleanup(@() localDeleteIfPresent(temporaryPath));
save(temporaryPath, 'shard', '-v7.3');
cycleShardSha256 = localFileSha256(temporaryPath);
if isfile(finalPath) || isfolder(finalPath)
    error('toyRoadP0:PublicationClobber', ...
        'Cycle shard destination already exists: %s', finalPath);
end
[published, message] = movefile(temporaryPath, finalPath);
if ~published
    if isfile(finalPath) || isfolder(finalPath)
        error('toyRoadP0:PublicationClobber', ...
            'Cycle shard destination already exists: %s', finalPath);
    end
    error('toyRoadP0:PublicationFailed', ...
        'Cannot atomically publish cycle shard: %s', message);
end
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

function localRequireComplete(capture)
required = {'cycle','previous','state0','next_substep_ordinal','d_node','d_gp', ...
    'alpha_bar_gp','f_alpha_gp','psi_raw_gp'};
valid = isstruct(capture) && isscalar(capture) && all(isfield(capture, required)) && ...
    isequal(capture.next_substep_ordinal, 6);
if valid
    arrays = {'d_node','d_gp','alpha_bar_gp','f_alpha_gp','psi_raw_gp'};
    for index = 1:numel(arrays)
        value = capture.(arrays{index});
        valid = valid && isa(value, 'double') && isreal(value) && ...
            all(isfinite(value), 'all');
    end
end
if ~valid
    error('toyRoadP0:InvalidCycleCapture', ...
        'All five immutable substep slices are required before export.');
end
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

function localRequirePublication(created, message)
if ~created
    error('toyRoadP0:PublicationFailed', 'Cannot create output directory: %s', message);
end
end

function localDeleteIfPresent(path)
if isfile(path)
    delete(path);
end
end
