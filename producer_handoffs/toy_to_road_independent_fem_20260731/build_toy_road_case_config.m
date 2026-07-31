function cfg = build_toy_road_case_config(case_id, lock_dir)
%BUILD_TOY_ROAD_CASE_CONFIG Validate a sealed single-axis FEM case input.

if ~(ischar(case_id) || (isstring(case_id) && isscalar(case_id)))
    error('toyRoad:InvalidInputLock', 'case_id must be a text scalar.');
end
if ~(ischar(lock_dir) || (isstring(lock_dir) && isscalar(lock_dir)))
    error('toyRoad:InvalidInputLock', 'lock_dir must be a text scalar.');
end

caseId = char(case_id);
lockDir = char(lock_dir);

try
    [caseFile, axis] = localCaseFile(caseId);
    parentPath = fullfile(lockDir, 'PARENT_LOCK.json');
    parentHash = localFileSha256(parentPath);
    parent = localReadJson(parentPath);
    family = localReadJson(fullfile(lockDir, 'FAMILY_INPUT_LOCK.json'));
    caseLock = localReadJson(fullfile(lockDir, caseFile));

    localValidateParent(parent);
    localEnsure(parentHash == string(family.parent_lock_sha256), ...
        'FAMILY_INPUT_LOCK.json does not match PARENT_LOCK.json.');
    localEnsure(isequal(family.fixed_parent_fields, parent), ...
        'FAMILY_INPUT_LOCK.json changes a fixed parent field.');
    localEnsure(family.censor_cap == 150, 'Family censor cap must be 150.');

    localEnsure(string(caseLock.case_id) == string(caseId), ...
        'Case lock case_id does not match the requested case.');
    localEnsure(string(caseLock.family_id) == string(family.family_id), ...
        'Case lock family_id does not match FAMILY_INPUT_LOCK.json.');
    localEnsure(string(caseLock.parent_lock_sha256) == parentHash, ...
        'Case lock does not match PARENT_LOCK.json.');
    localEnsure(string(caseLock.primary_variation_axis) == string(axis), ...
        'Case lock primary variation axis is invalid.');
    localEnsure(caseLock.censor_cap == 150, 'Case censor cap must be 150.');

    changed = localStringList(caseLock.changed_parent_fields);
    allowed = localStringList(caseLock.allowed_changed_parent_fields);
    localEnsure(isequal(changed, {axis}) && isequal(allowed, {axis}), ...
        'Exactly one allowed changed parent field is required.');
    localEnsure(isequal(caseLock.parent_candidate_diff.parent.(axis), ...
        family.axis_baselines.(axis)), ...
        'Case parent side does not match the family baseline.');
    localEnsure(isequal(caseLock.parent_candidate_diff.candidate, caseLock.candidate), ...
        'Case candidate does not match its machine-readable diff.');

    localValidateCandidate(caseLock.candidate, axis);
    cfg = localMakeConfig(parent, family, caseLock, caseId, axis);
catch caught
    if startsWith(caught.identifier, 'toyRoad:')
        rethrow(caught);
    end
    error('toyRoad:InvalidInputLock', '%s', caught.message);
end
end

function [caseFile, axis] = localCaseFile(caseId)
switch caseId
    case 'T1_initial_defect'
        caseFile = 'T1_INPUT_LOCK.json';
        axis = 'initial_defect';
    case 'T2_material_state'
        caseFile = 'T2_INPUT_LOCK.json';
        axis = 'material_state';
    case 'T3_loading_history'
        caseFile = 'T3_INPUT_LOCK.json';
        axis = 'loading_history';
    otherwise
        error('toyRoad:InvalidInputLock', 'Unknown case_id: %s.', caseId);
end
end

function value = localReadJson(path)
value = jsondecode(fileread(path));
end

function digest = localFileSha256(path)
fileId = fopen(path, 'rb');
localEnsure(fileId ~= -1, 'Unable to read PARENT_LOCK.json.');
cleanup = onCleanup(@() fclose(fileId));
hasher = java.security.MessageDigest.getInstance('SHA-256');
while true
    bytes = fread(fileId, 8192, '*uint8');
    if isempty(bytes)
        break;
    end
    hasher.update(bytes);
end
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(string(reshape(dec2hex(digestBytes, 2).', 1, [])));
end

function localValidateParent(parent)
localEnsure(strcmp(parent.schema_version, 'toy_to_road_parent_lock_v1'), ...
    'Parent schema version is invalid.');
localEnsure(strcmp(parent.physical_source_package_id, ...
    'Hard5_eta0_5step_Umax_011_012_013_20260729'), ...
    'Physical source package is invalid.');
localEnsure(strcmp(parent.physical_source_role, ...
    'consumed_physical_bytes_and_windows_paths'), ...
    'Physical source role is invalid.');
localEnsure(strcmp(parent.authoritative_analysis_bundle.role, ...
    'consumed_mac_analysis_bundle_contract'), ...
    'Analysis bundle role is invalid.');
localEnsure(strcmp(parent.authoritative_analysis_bundle.bundle_id, ...
    'bundle::hard5_eta0_u012_5step_20260729'), ...
    'Analysis bundle ID is invalid.');
localEnsure(parent.event.first_hit == 83 && parent.event.confirmed == 86, ...
    'Parent event contract is invalid.');
localEnsure(parent.physics.n_substeps == 5 && parent.numerics.right_censor_cap == 150, ...
    'Parent numerical contract is invalid.');
localEnsure(~parent.immutable_policy.latent_fem_fields_are_direct_road_sensors && ...
    ~parent.immutable_policy.pidl_network_training_authorized && ...
    strcmp(parent.immutable_policy.claim_scope, 'synthetic_whole_trajectory_loto_only') && ...
    ~parent.immutable_policy.road_validation_authorized, ...
    'Parent immutable policy is invalid.');
end

function localValidateCandidate(candidate, axis)
switch axis
    case 'initial_defect'
        localEnsure(isequal(reshape(candidate.initial_defect.tip, 1, []), [0.125 0.0]), ...
            'T1 initial defect tip is invalid.');
    case 'material_state'
        localEnsure(candidate.material_state.Gc == 0.008 && ...
            candidate.material_state.Pi_ratio == 0.8, ...
            'T2 material state is invalid.');
    case 'loading_history'
        blocks = candidate.loading_history.blocks;
        localEnsure(isequal(blocks, [1 30 0.108; 31 60 0.126; 61 150 0.120]), ...
            'T3 loading blocks are invalid.');
    otherwise
        error('toyRoad:InvalidInputLock', 'Unknown candidate axis.');
end
end

function cfg = localMakeConfig(parent, family, caseLock, caseId, axis)
cfg = struct();
cfg.case_id = caseId;
cfg.parent_reference_id = parent.parent_reference_id;
cfg.physical_source_package_id = parent.physical_source_package_id;
cfg.physical_source_role = parent.physical_source_role;
cfg.authoritative_analysis_bundle = parent.authoritative_analysis_bundle;
cfg.immutable_policy = parent.immutable_policy;
cfg.physics = parent.physics;
cfg.initial_defect = family.axis_baselines.initial_defect;
cfg.initial_defect.tip = reshape(cfg.initial_defect.tip, 1, []);
cfg.Pi_ratio = family.axis_baselines.material_state.Pi_ratio;
cfg.loading_history = family.axis_baselines.loading_history;
cfg.n_step = parent.physics.n_substeps;
cfg.censor_cap = caseLock.censor_cap;
cfg.event_contract = struct( ...
    'first_hit', parent.event.first_hit, ...
    'confirmed', parent.event.confirmed, ...
    'event_rule', parent.numerics.event_rule, ...
    'confirmation_cycles', parent.numerics.confirmation_cycles);

switch axis
    case 'initial_defect'
        cfg.initial_defect = caseLock.candidate.initial_defect;
        cfg.initial_defect.tip = reshape(cfg.initial_defect.tip, 1, []);
    case 'material_state'
        cfg.physics.Gc = caseLock.candidate.material_state.Gc;
        cfg.Pi_ratio = caseLock.candidate.material_state.Pi_ratio;
    case 'loading_history'
        cfg.loading_history = caseLock.candidate.loading_history;
end

blocks = cfg.loading_history.blocks;
cfg.umax_for_cycle = @(cycles) localUmaxForCycle(cycles, blocks, cfg.censor_cap);
end

function umax = localUmaxForCycle(cycles, blocks, censorCap)
if ~isnumeric(cycles) || ~isreal(cycles) || any(~isfinite(cycles), 'all') || ...
        any(cycles ~= floor(cycles), 'all') || any(cycles < 1, 'all') || ...
        any(cycles > censorCap, 'all')
    error('toyRoad:InvalidCycle', ...
        'Cycle values must be finite integers in the closed interval 1:150.');
end

umax = zeros(size(cycles));
for index = 1:numel(cycles)
    blockIndex = find(cycles(index) >= blocks(:, 1) & cycles(index) <= blocks(:, 2), 1);
    if isempty(blockIndex)
        error('toyRoad:InvalidInputLock', 'Loading blocks do not cover a requested cycle.');
    end
    umax(index) = blocks(blockIndex, 3);
end
end

function values = localStringList(value)
if ischar(value)
    values = {value};
elseif isstring(value)
    values = cellstr(value(:))';
elseif iscell(value) && all(cellfun(@ischar, value))
    values = reshape(value, 1, []);
else
    error('toyRoad:InvalidInputLock', 'Changed-field lists must contain text values.');
end
end

function localEnsure(condition, message)
if ~condition
    error('toyRoad:InvalidInputLock', '%s', message);
end
end
