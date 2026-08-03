function trace = begin_toy_road_c5_trace(entryInput, outputRoot)
%BEGIN_TOY_ROAD_C5_TRACE Snapshot c5/s4 entry state and reserve its trace.

required = {'authorization_scope','case_id','cycle','substep_ordinal', ...
    'evidence_method','d_lb','d_prev_stag','history_pre','active_u_dofs', ...
    'active_d_dofs','traction','reassemble_equilibrium','reassemble_phase'};
localRequireExactFields(entryInput, required);
authorizationScope = localCsvText(entryInput.authorization_scope, ...
    'authorization_scope');
caseId = localCaseId(entryInput.case_id);
localRequire(localIntegerEquals(entryInput.cycle, 5) && ...
    localIntegerEquals(entryInput.substep_ordinal, 4), ...
    'the numerical gate is restricted to physical c5/substep 4.');
evidenceMethod = localText(entryInput.evidence_method, 'evidence_method');
localRequire(strcmp(evidenceMethod, 'same_process_post_update_reassembly_v1'), ...
    'the c5 gate must use same-process post-update reassembly.');

dLb = entryInput.d_lb;
dPrevious = entryInput.d_prev_stag;
localRequire(localFiniteDoubleColumn(dLb) && ...
    localFiniteDoubleColumn(dPrevious) && isequal(size(dLb), size(dPrevious)), ...
    'd_lb and d_prev_stag must be matching finite double columns.');
localRequire(all(dLb >= 0) && all(dLb <= 1) && ...
    max(abs(dPrevious - dLb), [], 'all') <= 1e-12, ...
    'the accepted entry damage must equal the bounded lower-bound state.');
historyPre = entryInput.history_pre;
localRequire(isa(historyPre, 'double') && isreal(historyPre) && ...
    ~isempty(historyPre) && all(isfinite(historyPre), 'all'), ...
    'history_pre must be a nonempty finite double array.');
activeU = localActiveDofs(entryInput.active_u_dofs, Inf, 'active_u_dofs');
activeD = localActiveDofs(entryInput.active_d_dofs, numel(dLb), ...
    'active_d_dofs');
traction = entryInput.traction;
localRequire(localFiniteDoubleColumn(traction), ...
    'traction must be a nonempty finite double column.');
localRequire(isa(entryInput.reassemble_equilibrium, 'function_handle') && ...
    isa(entryInput.reassemble_phase, 'function_handle'), ...
    'both same-process reassembly operators must be callable.');
localRequireText(outputRoot, 'outputRoot must be nonempty scalar text.');
root = char(outputRoot);
localRequire(isfolder(root), 'outputRoot must already exist.');

qualification = fullfile(root, 'qualification');
localCreateDirectory(qualification);
tracePath = fullfile(qualification, 'C5_STAGGER_TRACE.csv');
receiptPath = fullfile(qualification, 'C5_NUMERICAL_GATE_RECEIPT.json');
header = ['authorization_scope,case_id,cycle,substep_ordinal,' ...
    'stagger_iteration,reassembly_ordinal,displacement_residual,' ...
    'raw_phase_residual,projected_phase_kkt,' ...
    'consecutive_stagger_delta,primal_feasibility' newline];
localCreateExclusiveText(tracePath, header);

snapshot = struct( ...
    'd_lb', dLb, ...
    'd_entry', dPrevious, ...
    'history_pre', historyPre, ...
    'active_u_dofs', activeU, ...
    'active_d_dofs', activeD, ...
    'traction', traction);
trace = struct( ...
    'authorization_scope', authorizationScope, ...
    'case_id', caseId, ...
    'cycle', 5, ...
    'substep_ordinal', 4, ...
    'evidence_method', evidenceMethod, ...
    'snapshot', snapshot, ...
    'reassemble_equilibrium', entryInput.reassemble_equilibrium, ...
    'reassemble_phase', entryInput.reassemble_phase, ...
    'trace_path', tracePath, ...
    'receipt_path', receiptPath, ...
    'trace_sha256', localFileSha256(tracePath), ...
    'trace_row_count', 0, ...
    'same_process_reassembly_count', 0, ...
    'stagger_ordinals', zeros(1,0), ...
    'd_prev_stag', dPrevious, ...
    'last_row_converged', false, ...
    'lifecycle_state', java.util.concurrent.atomic.AtomicInteger(0));
end

function localRequireExactFields(value, required)
localRequire(isstruct(value) && isscalar(value) && ...
    isequal(sort(fieldnames(value)), sort(required(:))), ...
    'entry_input must contain exactly the c5 gate fields.');
end

function dofs = localActiveDofs(dofs, maximum, label)
localRequire(isa(dofs, 'double') && iscolumn(dofs) && ~isempty(dofs) && ...
    all(isfinite(dofs)) && all(dofs == floor(dofs)) && all(dofs >= 1) && ...
    all(dofs <= maximum) && numel(unique(dofs)) == numel(dofs), ...
    '%s must be unique positive double integer indices.', label);
end

function value = localCaseId(value)
value = localCsvText(value, 'case_id');
roles = {'P0_parent','P0R_parent_repeat','T1_initial_defect', ...
    'T2_material_state','T3_loading_history'};
localRequire(any(strcmp(value, roles)), 'case_id is not a locked family role.');
end

function value = localCsvText(value, label)
value = localText(value, label);
localRequire(~isempty(value) && ~any(contains(value, {',', newline, char(13)})), ...
    '%s cannot be empty or contain CSV delimiters.', label);
end

function value = localText(value, label)
valid = (ischar(value) && isrow(value)) || ...
    (isstring(value) && isscalar(value) && ~ismissing(value));
localRequire(valid, '%s must be scalar text.', label);
value = char(value);
end

function localRequireText(value, message)
valid = (ischar(value) && isrow(value) && ~isempty(value)) || ...
    (isstring(value) && isscalar(value) && strlength(value) > 0);
localRequire(valid, message);
end

function value = localFiniteDoubleColumn(value)
value = isa(value, 'double') && isreal(value) && iscolumn(value) && ...
    ~isempty(value) && all(isfinite(value));
end

function value = localIntegerEquals(actual, expected)
value = isa(actual, 'double') && isscalar(actual) && isfinite(actual) && ...
    actual == expected;
end

function localCreateDirectory(path)
if isfolder(path)
    return;
end
localRequire(~isfile(path), 'qualification path is not a directory.');
[created, message] = mkdir(path);
if ~created
    error('toyRoadP0:PublicationFailed', ...
        'Cannot create qualification directory: %s', message);
end
end

function localCreateExclusiveText(path, content)
if isfile(path) || isfolder(path)
    error('toyRoadP0:PublicationClobber', ...
        'Refusing to overwrite c5 trace destination: %s', path);
end
try
    created = java.io.File(path).createNewFile();
catch exception
    error('toyRoadP0:PublicationFailed', ...
        'Cannot reserve c5 trace destination: %s', exception.message);
end
if ~created
    error('toyRoadP0:PublicationClobber', ...
        'Refusing to overwrite c5 trace destination: %s', path);
end
committed = java.util.concurrent.atomic.AtomicBoolean(false);
cleanup = onCleanup(@() localDeleteUncommitted(path, committed));
fileId = fopen(path, 'wb');
if fileId < 0
    error('toyRoadP0:PublicationFailed', 'Cannot open c5 trace: %s', path);
end
bytes = unicode2native(content, 'US-ASCII');
count = fwrite(fileId, bytes, 'uint8');
closeStatus = fclose(fileId);
if count ~= numel(bytes) || closeStatus ~= 0
    error('toyRoadP0:PublicationFailed', 'Cannot write c5 trace header: %s', path);
end
committed.set(true);
clear cleanup
end

function localDeleteUncommitted(path, committed)
if ~committed.get() && isfile(path)
    delete(path);
end
end

function digest = localFileSha256(path)
fileId = fopen(path, 'rb');
if fileId < 0
    error('toyRoadP0:PublicationFailed', 'Cannot hash c5 trace: %s', path);
end
cleanup = onCleanup(@() fclose(fileId));
bytes = fread(fileId, Inf, '*uint8');
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(bytes);
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end

function localRequire(condition, message, varargin)
if ~condition
    error('toyRoadP0:InvalidC5Input', message, varargin{:});
end
end
