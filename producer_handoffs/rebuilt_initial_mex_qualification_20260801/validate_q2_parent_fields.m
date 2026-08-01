function receipt = validate_q2_parent_fields(q2LockPath, parentLockPath, parentRoot, config)
%VALIDATE_Q2_PARENT_FIELDS Validate authoritative parent c1 evidence only.
if nargin < 4
    config = struct;
end
validateSealedEntry(q2LockPath);
validateConfig(config);
q2Lock = readJson(q2LockPath, 'rebuiltMexQ2:InvalidInputLock');
parentLock = readJson(parentLockPath, 'rebuiltMexQ2:InvalidParentLock');
validateQ2Lock(q2Lock);

if isfield(config, 'blocker_output_path') && isfile(config.blocker_output_path)
    error('rebuiltMexQ2:OutputExists', ...
        'The immutable Q2 parent blocker receipt already exists.');
end

function validateSealedEntry(q2LockPath)
if isUnitTestOnlyCall()
    return
end
canonicalLock = fullfile(fileparts(mfilename('fullpath')), 'Q2_INPUT_LOCK.json');
expectedDigest = ...
    'c46af4bd2e091a5749fdb7e3b589b2d45b60dbdbe9252338d153cb3522844b10';
if ~strcmp(normalizePath(q2LockPath), normalizePath(canonicalLock)) || ...
        ~isfile(canonicalLock) || ~strcmp(sha256File(canonicalLock), expectedDigest)
    error('rebuiltMexQ2:UnsealedInputLock', ...
        'Production Q2 validation requires the canonical sealed input lock.');
end
end

function value = isUnitTestOnlyCall()
stack = dbstack('-completenames');
names = {stack.name};
files = cell(size(stack));
for index = 1:numel(stack)
    files{index} = normalizePath(stack(index).file);
end
hasHelper = any(strcmp(names, 'validate_q2_parent_fields_test_only'));
testsRoot = normalizePath(fullfile(fileparts(mfilename('fullpath')), 'tests'));
hasTestCaller = any(startsWith(files, [testsRoot, '/']));
value = hasHelper && hasTestCaller;
end
if ~strcmp(sha256File(parentLockPath), q2Lock.parent_lock_sha256)
    error('rebuiltMexQ2:ParentProvenanceMismatch', ...
        'PARENT_LOCK.json does not match Q2_INPUT_LOCK.json.');
end

replayMeshSha256 = validateParentIdentity(q2Lock.parent, parentLock);
records = flattenSourceRecords(parentLock.source_files);
if isfield(q2Lock.parent, 'required_source_file_count') && ...
        numel(records) ~= q2Lock.parent.required_source_file_count
    error('rebuiltMexQ2:ParentProvenanceMismatch', ...
        'The parent source-file inventory count changed.');
end
validateParentFiles(records, parentRoot);

cyclePath = resolveUnderRoot(parentRoot, q2Lock.parent.cycle1_relative_path);
if ~strcmp(sha256File(cyclePath), q2Lock.parent.cycle1_sha256)
    error('rebuiltMexQ2:ParentProvenanceMismatch', ...
        'The locked parent cycle-1 bytes changed.');
end
cycleRecord = records(strcmp({records.relative_path}, ...
    q2Lock.parent.cycle1_relative_path));
if numel(cycleRecord) ~= 1 || ...
        ~strcmp(cycleRecord.sha256, q2Lock.parent.cycle1_sha256)
    error('rebuiltMexQ2:ParentProvenanceMismatch', ...
        'The parent cycle-1 inventory record is absent or mismatched.');
end

fieldMap = parentLock.state_semantics.field_map;
rejectProhibitedDeclarations(fieldMap, q2Lock.required_field_map);
cycle = load(cyclePath);
n = q2Lock.parent.num_elem;
negativeTolerance = q2Lock.negative_tolerance;
fields = struct;
fields.damage = nativeField(cycle, fieldMap, 'damage', 'damage', ...
    q2Lock.required_field_map.damage, n, negativeTolerance);
fields.history = nativeField(cycle, fieldMap, {'history', 'alpha_bar'}, ...
    'history', q2Lock.required_field_map.history, n, negativeTolerance);
fields.fatigue_degradation = nativeField(cycle, fieldMap, ...
    'fatigue_degradation', 'fatigue degradation', ...
    q2Lock.required_field_map.fatigue_degradation, n, negativeTolerance);
fields.raw = nativeAliasedField(cycle, fieldMap, ...
    q2Lock.required_field_map.raw_driver_aliases, n, negativeTolerance);

blockers = {};
supplementProvenance = struct('used', false);
hasNativeG = declaredNative(fieldMap, 'damage_degradation', ...
    q2Lock.required_field_map.damage_degradation) && ...
    isfield(cycle, q2Lock.required_field_map.damage_degradation);
hasNativeActive = declaredNative(fieldMap, 'active_driver', ...
    q2Lock.required_field_map.active_driver) && ...
    isfield(cycle, q2Lock.required_field_map.active_driver);
if hasNativeG
    fields.damage_degradation = makeField( ...
        cycle.(q2Lock.required_field_map.damage_degradation), ...
        ['native:', q2Lock.required_field_map.damage_degradation], ...
        n, negativeTolerance);
end
if hasNativeActive
    fields.active = makeField(cycle.(q2Lock.required_field_map.active_driver), ...
        ['native:', q2Lock.required_field_map.active_driver], ...
        n, negativeTolerance);
end
if ~hasNativeG || ~hasNativeActive
    [supplementFields, supplementReady, supplementProvenance] = validateSupplement( ...
        q2Lock, config, n, negativeTolerance);
    if supplementReady
        if ~hasNativeG
            fields.damage_degradation = supplementFields.damage_degradation;
        end
        if ~hasNativeActive
            fields.active = supplementFields.active;
        end
    end
end
if ~isfield(fields, 'damage_degradation')
    blockers{end + 1} = ... %#ok<AGROW>
        'blocked_missing_parent_damage_degradation_field';
end
if ~isfield(fields, 'active')
    blockers{end + 1} = ... %#ok<AGROW>
        'blocked_missing_parent_active_field';
end

status = 'ready';
if ~isempty(blockers)
    status = 'blocked';
end
receipt = orderfields(struct( ...
    'schema_version', 'rebuilt_initial_mex_q2_parent_receipt_v1', ...
    'status', status, ...
    'blockers', {blockers}, ...
    'q2_input_lock_sha256', sha256File(q2LockPath), ...
    'parent_lock_sha256', sha256File(parentLockPath), ...
    'parent_cycle1_sha256', sha256File(cyclePath), ...
    'parent_reference_id', char(parentLock.parent_reference_id), ...
    'mesh_ordering_sha256', char(q2Lock.parent.mesh_ordering_sha256), ...
    'replay_mesh_sha256', replayMeshSha256, ...
    'num_elem', n, 'supplement_provenance', supplementProvenance, ...
    'fields', fields));

if strcmp(status, 'blocked') && isfield(config, 'blocker_output_path')
    publishBlocker(config.blocker_output_path, receipt);
end
end

function validateConfig(config)
if ~isstruct(config)
    error('rebuiltMexQ2:InvalidConfig', 'Q2 parent configuration must be a struct.');
end
allowed = {'blocker_output_path', 'supplement_root'};
if ~all(ismember(fieldnames(config), allowed))
    error('rebuiltMexQ2:InvalidConfig', 'Unknown Q2 parent configuration field.');
end
end

function validateQ2Lock(lock)
required = {'schema_version', 'parent_lock_sha256', 'parent', ...
    'required_field_map', 'negative_tolerance', 'supplement', ...
    'prohibited_substitutes'};
requireFields(lock, required, 'rebuiltMexQ2:InvalidInputLock');
if ~strcmp(lock.schema_version, 'rebuilt_initial_mex_q2_input_lock_v1') || ...
        ~isSha256(lock.parent_lock_sha256)
    error('rebuiltMexQ2:InvalidInputLock', 'The Q2 input lock identity is invalid.');
end
requireFields(lock.parent, {'reference_id', 'num_elem', ...
    'mesh_ordering_sha256', 'cycle', 'cycle1_relative_path', ...
    'cycle1_sha256'}, 'rebuiltMexQ2:InvalidInputLock');
requireFields(lock.required_field_map, {'damage', 'history', ...
    'fatigue_degradation', 'raw_driver_aliases', ...
    'damage_degradation', 'active_driver'}, ...
    'rebuiltMexQ2:InvalidInputLock');
if lock.parent.cycle ~= 1 || lock.parent.num_elem < 1 || ...
        fix(lock.parent.num_elem) ~= lock.parent.num_elem || ...
        ~isSha256(lock.parent.mesh_ordering_sha256) || ...
        ~isSha256(lock.parent.cycle1_sha256) || ...
        lock.negative_tolerance ~= 1e-14
    error('rebuiltMexQ2:InvalidInputLock', 'A fixed Q2 identity or tolerance changed.');
end
end

function replayMeshSha256 = validateParentIdentity(expected, parent)
requireFields(parent, {'parent_reference_id', 'mesh', ...
    'state_semantics_id', 'state_semantics', 'source_files'}, ...
    'rebuiltMexQ2:InvalidParentLock');
requireFields(parent.mesh, {'num_elem', 'content_sha256', ...
    'task4_parent_mesh_sha256', 'task4_parent_mesh_sha256_semantics'}, ...
    'rebuiltMexQ2:InvalidParentLock');
requireFields(parent.state_semantics, {'peak_substep_ordinal', 'field_map'}, ...
    'rebuiltMexQ2:InvalidParentLock');
if ~strcmp(parent.parent_reference_id, expected.reference_id) || ...
        parent.mesh.num_elem ~= expected.num_elem || ...
        ~strcmp(parent.mesh.content_sha256, expected.mesh_ordering_sha256)
    error('rebuiltMexQ2:ParentIdentityMismatch', ...
        'Parent reference, element count, or mesh ordering changed.');
end
if ~isSha256(parent.mesh.task4_parent_mesh_sha256) || ...
        ~strcmp(parent.mesh.task4_parent_mesh_sha256_semantics, ...
        'sha256_matlab_column_major_float64_coords_then_int64_connectivity_v1')
    error('rebuiltMexQ2:ParentIdentityMismatch', ...
        'Canonical parent replay mesh identity is absent or changed.');
end
replayMeshSha256 = char(parent.mesh.task4_parent_mesh_sha256);
if isfield(expected, 'state_semantics_id') && ...
        ~strcmp(parent.state_semantics_id, expected.state_semantics_id)
    error('rebuiltMexQ2:ParentIdentityMismatch', 'Parent state semantics changed.');
end
if isfield(expected, 'peak_substep_ordinal') && ...
        parent.state_semantics.peak_substep_ordinal ~= expected.peak_substep_ordinal
    error('rebuiltMexQ2:ParentIdentityMismatch', 'Parent peak substep changed.');
end
end

function rejectProhibitedDeclarations(fieldMap, required)
if isfield(fieldMap, 'active_driver') && ...
        ~strcmp(fieldMap.active_driver, required.active_driver)
    error('rebuiltMexQ2:ProhibitedFieldSubstitute', ...
        'Active must be native psi_active_elem, never fatigue or an element-level product.');
end
if isfield(fieldMap, 'damage_degradation') && ...
        ~strcmp(fieldMap.damage_degradation, required.damage_degradation)
    error('rebuiltMexQ2:ProhibitedFieldSubstitute', ...
        'Damage degradation must be native g_elem.');
end
end

function result = nativeField(cycle, fieldMap, mapKeys, label, requiredName, n, tol)
declared = firstMappedName(fieldMap, mapKeys);
if isempty(declared) || ~strcmp(declared, requiredName) || ~isfield(cycle, requiredName)
    error('rebuiltMexQ2:MissingRequiredParentField', ...
        'The authoritative parent %s field is absent.', label);
end
result = makeField(cycle.(requiredName), ['native:', requiredName], n, tol);
end

function result = nativeAliasedField(cycle, fieldMap, aliases, n, tol)
declared = firstMappedName(fieldMap, 'raw_driver');
aliases = cellstr(aliases);
if isempty(declared) || ~ismember(declared, aliases) || ~isfield(cycle, declared)
    error('rebuiltMexQ2:MissingRequiredParentField', ...
        'The authoritative parent raw driver is absent.');
end
result = makeField(cycle.(declared), ['native:', declared], n, tol);
end

function value = firstMappedName(fieldMap, keys)
if ischar(keys) || isstring(keys)
    keys = cellstr(keys);
end
value = '';
for index = 1:numel(keys)
    if isfield(fieldMap, keys{index})
        value = char(fieldMap.(keys{index}));
        return
    end
end
end

function value = declaredNative(fieldMap, key, expected)
value = isfield(fieldMap, key) && strcmp(fieldMap.(key), expected);
end

function result = makeField(values, source, n, negativeTolerance)
if ~isnumeric(values) || ~isreal(values) || ~isequal(size(values), [n, 1]) || ...
        any(~isfinite(values))
    error('rebuiltMexQ2:InvalidParentField', ...
        'A parent field has invalid shape, type, or finite state.');
end
if any(values < -negativeTolerance)
    error('rebuiltMexQ2:NegativeField', ...
        'A parent field is below the fixed numerical negative tolerance.');
end
result = struct('source', source, 'values', values(:));
end

function [fields, ready, provenance] = validateSupplement(lock, config, n, tol)
fields = struct;
ready = false;
provenance = struct('used', false);
supplement = lock.supplement;
if ~isfield(supplement, 'permitted') || ~supplement.permitted || ...
        ~isfield(config, 'supplement_root')
    return
end
required = {'relative_path', 'sha256', 'parent_reference_id', 'source_id', ...
    'parent_cycle1_sha256', 'mesh_ordering_sha256', 'element_ids_field', ...
    'element_order_sha256', 'num_gauss_points', 'g_field', 'raw_field', ...
    'damage_degradation_semantics', 'active_semantics'};
if ~all(isfield(supplement, required)) || ~isSha256(supplement.sha256) || ...
        ~isSha256(supplement.parent_cycle1_sha256) || ...
        ~isSha256(supplement.mesh_ordering_sha256) || ...
        ~isSha256(supplement.element_order_sha256) || ...
        ~strcmp(supplement.g_field, 'g_gp') || ...
        ~strcmp(supplement.raw_field, 'psi_raw_gp') || ...
        ~strcmp(supplement.element_ids_field, 'element_ids') || ...
        ~strcmp(supplement.damage_degradation_semantics, 'mean_gp(g_gp)') || ...
        ~strcmp(supplement.active_semantics, 'mean_gp(g_gp.*psi_raw_gp)') || ...
        supplement.num_gauss_points < 1
    error('rebuiltMexQ2:InvalidSupplement', ...
        'The optional GP supplement semantics are not sealed and exact.');
end
if ~strcmp(supplement.parent_reference_id, lock.parent.reference_id) || ...
        ~strcmp(supplement.parent_cycle1_sha256, lock.parent.cycle1_sha256) || ...
        ~strcmp(supplement.mesh_ordering_sha256, lock.parent.mesh_ordering_sha256) || ...
        isempty(strtrim(char(supplement.source_id)))
    error('rebuiltMexQ2:SupplementIdentityMismatch', ...
        'The GP supplement is not bound to the exact locked parent identity.');
end
path = resolveUnderRoot(config.supplement_root, supplement.relative_path);
if ~strcmp(sha256File(path), supplement.sha256)
    error('rebuiltMexQ2:ParentProvenanceMismatch', ...
        'The optional parent GP supplement hash changed.');
end
data = load(path);
metadata = {'parent_reference_id', 'source_id', 'parent_cycle1_sha256', ...
    'mesh_ordering_sha256', 'element_ids'};
if ~all(isfield(data, metadata)) || ...
        ~strcmp(char(data.parent_reference_id), supplement.parent_reference_id) || ...
        ~strcmp(char(data.source_id), supplement.source_id) || ...
        ~strcmp(char(data.parent_cycle1_sha256), supplement.parent_cycle1_sha256) || ...
        ~strcmp(char(data.mesh_ordering_sha256), supplement.mesh_ordering_sha256)
    error('rebuiltMexQ2:SupplementIdentityMismatch', ...
        'The GP supplement metadata differs from its sealed parent identity.');
end
elementIds = data.element_ids;
if ~isnumeric(elementIds) || ~isreal(elementIds) || ...
        ~isequal(size(elementIds), [n, 1]) || any(~isfinite(elementIds)) || ...
        any(elementIds ~= fix(elementIds)) || ...
        ~isequal(int64(elementIds), int64((1:n)')) || ...
        ~strcmp(hashInt64Vector(int64(elementIds)), supplement.element_order_sha256)
    error('rebuiltMexQ2:SupplementOrderingMismatch', ...
        'The GP supplement element IDs/order differ from the locked parent ordering.');
end
if ~isfield(data, 'g_gp') || ~isfield(data, 'psi_raw_gp') || ...
        ~isequal(size(data.g_gp), [n, supplement.num_gauss_points]) || ...
        ~isequal(size(data.psi_raw_gp), size(data.g_gp)) || ...
        any(~isfinite(data.g_gp), 'all') || any(~isfinite(data.psi_raw_gp), 'all') || ...
        any(data.g_gp < -tol, 'all') || any(data.psi_raw_gp < -tol, 'all')
    error('rebuiltMexQ2:InvalidSupplement', ...
        'The optional GP fields are malformed or below tolerance.');
end
gElem = mean(data.g_gp, 2);
activeElem = mean(data.g_gp .* data.psi_raw_gp, 2);
fields.damage_degradation = makeField(gElem, ...
    'sealed_gp:mean_gp(g_gp)', n, tol);
fields.active = makeField(activeElem, ...
    'sealed_gp:mean_gp(g_gp.*psi_raw_gp)', n, tol);
provenance = orderfields(struct( ...
    'used', true, ...
    'relative_path', char(supplement.relative_path), ...
    'sha256', char(supplement.sha256), ...
    'parent_reference_id', char(supplement.parent_reference_id), ...
    'source_id', char(supplement.source_id), ...
    'parent_cycle1_sha256', char(supplement.parent_cycle1_sha256), ...
    'mesh_ordering_sha256', char(supplement.mesh_ordering_sha256), ...
    'element_ids_field', char(supplement.element_ids_field), ...
    'element_order_sha256', char(supplement.element_order_sha256), ...
    'element_ids', int64(elementIds(:)), ...
    'num_gauss_points', supplement.num_gauss_points));
ready = true;
end

function digest = hashInt64Vector(values)
md = java.security.MessageDigest.getInstance('SHA-256');
md.update(typecast(int64(values(:)), 'uint8'));
digest = lower(reshape(dec2hex(typecast(md.digest(), 'uint8'), 2).', 1, []));
end

function records = flattenSourceRecords(value)
records = struct('relative_path', {}, 'sha256', {});
if ~isstruct(value)
    return
end
if isscalar(value) && all(isfield(value, {'relative_path', 'sha256'}))
    records = struct('relative_path', char(value.relative_path), ...
        'sha256', char(value.sha256));
    return
end
names = fieldnames(value);
for outer = 1:numel(value)
    for index = 1:numel(names)
        nested = flattenSourceRecords(value(outer).(names{index}));
        records = [records; nested(:)]; %#ok<AGROW>
    end
end
end

function validateParentFiles(records, parentRoot)
if isempty(records) || numel(unique({records.relative_path})) ~= numel(records)
    error('rebuiltMexQ2:ParentProvenanceMismatch', ...
        'The parent source-file inventory is empty or duplicated.');
end
for index = 1:numel(records)
    if ~isSha256(records(index).sha256)
        error('rebuiltMexQ2:ParentProvenanceMismatch', ...
            'A parent source hash is malformed.');
    end
    path = resolveUnderRoot(parentRoot, records(index).relative_path);
    if ~strcmp(sha256File(path), records(index).sha256)
        error('rebuiltMexQ2:ParentProvenanceMismatch', ...
            'A locked parent source file changed.');
    end
end
end

function publishBlocker(path, receipt)
parent = fileparts(path);
if ~isempty(parent) && ~isfolder(parent)
    error('rebuiltMexQ2:InvalidConfig', 'Blocker output parent does not exist.');
end
published = rmfield(receipt, 'fields');
published.field_evidence = fieldEvidence(receipt.fields);
created = java.io.File(path).createNewFile();
if ~created
    error('rebuiltMexQ2:OutputExists', ...
        'The immutable Q2 parent blocker receipt already exists.');
end
fileId = fopen(path, 'w');
if fileId < 0
    delete(path);
    error('rebuiltMexQ2:InvalidConfig', 'Unable to publish the blocker receipt.');
end
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, jsonencode(published, PrettyPrint=true), 'char');
end

function evidence = fieldEvidence(fields)
names = fieldnames(fields);
evidence = struct;
for index = 1:numel(names)
    evidence.(names{index}) = rmfield(fields.(names{index}), 'values');
end
end

function value = readJson(path, identifier)
if ~isfile(path)
    error(identifier, 'A required lock file is absent.');
end
try
    value = jsondecode(fileread(path));
catch exception
    error(identifier, 'A lock file is not valid JSON: %s', exception.message);
end
end

function requireFields(value, names, identifier)
if ~isstruct(value) || ~all(isfield(value, names))
    error(identifier, 'A required lock field is absent.');
end
end

function path = resolveUnderRoot(root, relativePath)
relativePath = char(relativePath);
if isempty(relativePath) || isAbsolute(relativePath) || contains(relativePath, '..')
    error('rebuiltMexQ2:ParentProvenanceMismatch', 'A parent path is unsafe.');
end
root = char(java.io.File(root).getCanonicalPath());
path = char(java.io.File(fullfile(root, relativePath)).getCanonicalPath());
if ~startsWith(lower(strrep(path, '\', '/')), ...
        [lower(strrep(root, '\', '/')), '/']) || ~isfile(path)
    error('rebuiltMexQ2:ParentProvenanceMismatch', ...
        'A locked parent file is absent or escapes its root.');
end
end

function value = isAbsolute(path)
value = ~isempty(regexp(path, '^[A-Za-z]:[\\/]|^[\\/]', 'once'));
end

function path = normalizePath(path)
path = lower(strrep(char(java.io.File(path).getCanonicalPath()), '\', '/'));
end

function value = isSha256(text)
value = (ischar(text) || isstring(text)) && ...
    ~isempty(regexp(char(text), '^[0-9a-f]{64}$', 'once'));
end

function digest = sha256File(path)
fileId = fopen(path, 'rb');
if fileId < 0
    error('rebuiltMexQ2:ParentProvenanceMismatch', 'Unable to read a locked file.');
end
cleanup = onCleanup(@() fclose(fileId));
md = java.security.MessageDigest.getInstance('SHA-256');
while true
    bytes = fread(fileId, 1048576, '*uint8');
    if isempty(bytes)
        break
    end
    md.update(bytes);
end
digest = lower(reshape(dec2hex(typecast(md.digest(), 'uint8'), 2).', 1, []));
end
