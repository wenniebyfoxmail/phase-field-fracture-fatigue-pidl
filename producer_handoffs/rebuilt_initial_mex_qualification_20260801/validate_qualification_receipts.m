function receipt = validate_qualification_receipts(qualificationRoot, ...
        runtimeLockPath, runtimeRoot, sourceRoot, q2LockPath, ...
        parentLockPath, outputPath)
%VALIDATE_QUALIFICATION_RECEIPTS Semantically validate and bind Q1/Q2 evidence.

if nargin < 7, outputPath = ''; end
handoff = fileparts(mfilename('fullpath'));
requireCanonical(runtimeLockPath, fullfile(handoff, 'RUNTIME_LOCK.json'), ...
    'rebuiltMexQualification:NoncanonicalRuntimeLock');
requireCanonical(q2LockPath, fullfile(handoff, 'Q2_INPUT_LOCK.json'), ...
    'rebuiltMexQualification:IdentityMismatch');
requireCanonical(runtimeRoot, fullfile(handoff, 'runtime'), ...
    'rebuiltMexQualification:IdentityMismatch');
if ~isfolder(qualificationRoot)
    error('rebuiltMexQualification:MissingQ1', ...
        'The qualification root does not exist.');
end

runtime = validate_runtime_lock(runtimeLockPath, runtimeRoot, sourceRoot);
requireRuntimeReceipt(runtime);
runtimeLockSha = fileSha256(runtimeLockPath);
q2LockSha = fileSha256(q2LockPath);
parentLockSha = fileSha256(parentLockPath);

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
requireSchema(q1, 'rebuilt_initial_mex_q1_receipt_v1');
requireSchema(q1Result, 'rebuilt_initial_mex_q1_result_v1');
if ~trueLogical(q1, 'passed') || ~trueLogical(q1Result, 'passed')
    error('rebuiltMexQualification:Q1NotPassed', 'Q1 did not pass.');
end
if ~trueLogical(q1, 'source_clean')
    error('rebuiltMexQualification:MissingProvenance', ...
        'Q1 lacks a passing clean-source receipt.');
end
requireIdentity(q1, runtime, runtimeLockSha);
requireIdentity(q1Result, runtime, runtimeLockSha);
requireSameText(q1, q1Result, 'input_sha256', 64);
if ~strcmp(textField(q1, 'metrics_sha256', 64), fileSha256(q1MetricsPath)) || ...
        ~strcmp(textField(q1Result, 'metrics_sha256', 64), ...
        fileSha256(q1MetricsPath)) || ...
        ~strcmp(textField(q1, 'result_sha256', 64), fileSha256(q1ResultPath))
    artifactMismatch('A Q1 artifact digest does not match its receipt.');
end
q1Metrics = loadSingleVariable(q1MetricsPath, 'metrics');
validateQ1Metrics(q1Metrics);
if ~isfield(q1, 'metrics') || ~semanticEqual(q1.metrics, q1Metrics)
    metricMismatch('Q1 embedded metrics differ from Q1_METRICS.mat.');
end

q2Root = fullfile(qualificationRoot, 'Q2');
q2Path = fullfile(q2Root, 'Q2_RESULT.json');
if ~isfile(q2Path)
    error('rebuiltMexQualification:MissingQ2', ...
        'A complete Q2 result is required.');
end
q2 = readJson(q2Path, 'rebuiltMexQualification:MissingQ2');
status = stringField(q2, 'status');
if status == "blocked"
    error('rebuiltMexQualification:Q2Blocked', ...
        'Q2 is blocked and cannot authorize a family launch.');
end
if status ~= "passed" || ~trueLogical(q2, 'passed')
    error('rebuiltMexQualification:Q2NotPassed', 'Q2 did not pass.');
end
requireSchema(q2, 'rebuilt_initial_mex_q2_result_v2');
if ~isfield(q2, 'blockers') || ~isempty(q2.blockers) || ...
        stringField(q2, 'stage') ~= "cycle1_metric_gate" || ...
        ~isfield(q2, 'family_terminal_eligible') || ...
        ~isequal(q2.family_terminal_eligible, false)
    error('rebuiltMexQualification:Q2NotPassed', ...
        'Q2 contains blockers or did not reach the metric gate.');
end
requireIdentity(q2, runtime, runtimeLockSha);
if ~strcmp(textField(q2, 'q2_input_lock_sha256', 64), q2LockSha) || ...
        ~strcmp(textField(q2, 'parent_lock_sha256', 64), parentLockSha)
    identityMismatch('Q2 is not bound to the selected parent locks.');
end
meshSha = textField(q2, 'mesh_ordering_sha256', 64);
if ~strcmp(meshSha, textField(q2, 'replay_source_mesh_sha256', 64))
    identityMismatch('Q2 mesh and replay ordering identities differ.');
end

paths = validateArtifactRecords(q2, q2Root);
q2Metrics = loadSingleVariable(paths.metrics, 'metrics');
q2Masks = loadSingleVariable(paths.parent_masks, 'mask_artifact');
q2State = loadMatStruct(paths.state);
q2Terminal = readJson(paths.terminal, ...
    'rebuiltMexQualification:ArtifactIdentityMismatch');
validateQ2Metrics(q2Metrics, q2);
validateQ2Masks(q2Masks, q2);
validateQ2State(q2State, q2);
validateQ2Terminal(q2Terminal, q2);
if ~isfield(q2, 'metrics') || ~semanticEqual(q2.metrics, q2Metrics)
    metricMismatch('Q2 embedded metrics differ from Q2_METRICS.mat.');
end

receipt = orderfields(struct( ...
    'schema_version', 'rebuilt_mex_family_qualification_receipt_v1', ...
    'passed', true, 'runtime_lock_sha256', runtimeLockSha, ...
    'runtime_initial_sha256', char(runtime.initial_sha256), ...
    'source_commit', char(runtime.source_commit), ...
    'q1_receipt_sha256', fileSha256(q1ReceiptPath), ...
    'q1_result_sha256', fileSha256(q1ResultPath), ...
    'q2_receipt_sha256', fileSha256(q2Path), ...
    'q2_input_lock_sha256', q2LockSha, ...
    'parent_lock_sha256', parentLockSha, ...
    'parent_cycle1_sha256', textField(q2, 'parent_cycle1_sha256', 64), ...
    'parent_reference_id', char(stringField(q2, 'parent_reference_id')), ...
    'mesh_ordering_sha256', meshSha, ...
    'parent_vtk_mesh_sha256', ...
        textField(q2, 'parent_vtk_mesh_sha256', 64), ...
    'mask_set_sha256', textField(q2, 'mask_set_sha256', 64)));
if ~isempty(outputPath), publishJsonNoClobber(outputPath, receipt); end
end

function requireRuntimeReceipt(value)
required = {'lock_sha256','initial_sha256','source_commit','source_clean', ...
    'build','dependencies','toolchain','source_hashes_sha256'};
if ~isstruct(value) || ~isscalar(value) || ~all(isfield(value, required)) || ...
        ~isequal(value.source_clean, true) || ...
        ~strcmp(value.initial_sha256, ...
        'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db')
    error('rebuiltMexQualification:MissingProvenance', ...
        'Canonical runtime validation did not return complete provenance.');
end
end

function requireIdentity(value, runtime, lockSha)
if ~strcmp(textField(value, 'runtime_lock_sha256', 64), lockSha) || ...
        ~strcmp(textField(value, 'runtime_initial_sha256', 64), ...
        runtime.initial_sha256) || ...
        ~strcmp(textField(value, 'source_commit', 40), runtime.source_commit)
    identityMismatch('A qualification artifact has a different runtime/source identity.');
end
end

function validateQ1Metrics(metrics)
requireExactFields(metrics, {'schema_version','passed','output_shapes', ...
    'index_outputs','stiffness','numerical_outputs','probe'});
requireSchema(metrics, 'rebuilt_initial_mex_q1_metrics_v1');
if ~trueLogical(metrics, 'passed'), metricMismatch('Q1 metrics are not passing.'); end
shapeNames = {'K_vect','i_row','j_col','M_vector','i_row_sig','j_col_sig', ...
    'eps_vector','i_row_eps','j_col_eps','sig0_vector','i_row_pf','j_col_pf'};
if ~isstruct(metrics.output_shapes) || ...
        ~all(isfield(metrics.output_shapes, shapeNames))
    metricMismatch('Q1 output shape contract is incomplete.');
end
for k = 1:numel(shapeNames)
    shape = metrics.output_shapes.(shapeNames{k});
    if ~isnumeric(shape) || numel(shape) ~= 2 || any(shape < 1) || ...
            any(shape ~= fix(shape))
        metricMismatch('Q1 output shape contract is invalid.');
    end
end
indexNames = {'i_row','j_col','i_row_sig','j_col_sig', ...
    'i_row_eps','j_col_eps','i_row_pf','j_col_pf'};
indices = metrics.index_outputs;
if ~isstruct(indices) || numel(indices) ~= 8 || ...
        ~isequal({indices.name}, indexNames) || ...
        ~all(arrayfun(@(x) isequal(x.exact, true), indices))
    metricMismatch('Q1 index-output equality contract failed.');
end
stiffness = metrics.stiffness;
if ~isstruct(stiffness) || stiffness.threshold ~= 1e-12 || ...
        stiffness.relative_frobenius > stiffness.threshold || ...
        ~finiteNonnegative(stiffness.relative_frobenius) || ...
        ~finiteNonnegative(stiffness.max_absolute)
    metricMismatch('Q1 stiffness threshold identity failed.');
end
names = {'M_vector','eps_vector','sig0_vector'};
numerical = metrics.numerical_outputs;
if ~isstruct(numerical) || numel(numerical) ~= 3 || ...
        ~isequal({numerical.name}, names)
    metricMismatch('Q1 numerical-output contract is incomplete.');
end
for k = 1:3
    item = numerical(k);
    expectedThreshold = 1e-12;
    if item.identically_zero, expectedThreshold = 1e-14; end
    if item.threshold ~= expectedThreshold || ...
            ~finiteNonnegative(item.max_absolute) || ...
            (item.identically_zero && item.max_absolute > item.threshold) || ...
            (~item.identically_zero && (~finiteNonnegative(item.relative_l2) || ...
            item.relative_l2 > item.threshold))
        metricMismatch('Q1 numerical threshold identity failed.');
    end
end
probe = metrics.probe;
if ~strcmp(probe.name, 'deterministic_internal_force_probe') || ...
        probe.top_y_value ~= 0.03 || probe.threshold ~= 1e-12 || ...
        ~finiteNonnegative(probe.relative_l2) || ...
        probe.relative_l2 > probe.threshold || ...
        ~finiteNonnegative(probe.max_absolute)
    metricMismatch('Q1 deterministic internal-force probe contract failed.');
end
end

function paths = validateArtifactRecords(q2, root)
names = {'state','terminal','metrics','parent_masks'};
expected = {'Q2_CYCLE1_STATE.mat','Q2_CYCLE1_TERMINAL.json', ...
    'Q2_METRICS.mat','Q2_PARENT_MASKS.mat'};
if ~isfield(q2, 'artifacts') || ~isstruct(q2.artifacts) || ...
        ~all(isfield(q2.artifacts, names))
    artifactMismatch('Q2 artifact provenance is incomplete.');
end
paths = struct;
for k = 1:4
    record = q2.artifacts.(names{k});
    requireExactFields(record, {'relative_path','sha256','bytes'}, ...
        strcmp(names{k}, 'parent_masks'));
    relative = char(stringField(record, 'relative_path'));
    if ~strcmp(relative, expected{k})
        artifactMismatch('A Q2 artifact path is not canonical.');
    end
    path = fullfile(root, relative); details = dir(path);
    if isempty(details) || details.bytes ~= record.bytes || ...
            ~strcmp(fileSha256(path), textField(record, 'sha256', 64))
        artifactMismatch('A Q2 artifact hash or size does not match its receipt.');
    end
    paths.(names{k}) = path;
end
if ~strcmp(textField(q2.artifacts.parent_masks, 'mask_set_sha256', 64), ...
        textField(q2, 'mask_set_sha256', 64))
    artifactMismatch('Q2 mask artifact identity differs from the result.');
end
end

function validateQ2Metrics(metrics, q2)
requireExactFields(metrics, {'schema_version','passed','parent_cycle1_sha256', ...
    'mask_set_sha256','log_transform','fields'});
requireSchema(metrics, 'rebuilt_initial_mex_q2_metrics_v1');
if ~trueLogical(metrics, 'passed') || ...
        ~strcmp(metrics.parent_cycle1_sha256, q2.parent_cycle1_sha256) || ...
        ~strcmp(metrics.mask_set_sha256, q2.mask_set_sha256) || ...
        ~strcmp(metrics.log_transform, 'log10(max(q,0)+1e-14)')
    metricMismatch('Q2 metric identity or transform is invalid.');
end
names = {'damage','history','fatigue_degradation','raw', ...
    'damage_degradation','active'};
if ~isstruct(metrics.fields) || ~all(isfield(metrics.fields, names))
    metricMismatch('Q2 field metrics are incomplete.');
end
for k = 1:numel(names)
    item = metrics.fields.(names{k});
    if ~trueLogical(item, 'passed') || item.outside_absolute_mae > 1e-12 || ...
            item.outside_absolute_max_error > 1e-10
        metricMismatch('A Q2 field failed its absolute gate.');
    end
    if strcmp(names{k}, 'damage')
        if item.mae > 0.002 || item.rmse > 0.005 || ...
                ~validCorrelation(item.correlation, 0.995)
            metricMismatch('Q2 damage metric thresholds failed.');
        end
    elseif strcmp(names{k}, 'fatigue_degradation')
        if item.absolute_mae > 1e-12 || item.absolute_max_error > 1e-10 || ...
                ~strcmp(char(item.correlation), 'not_applicable_zero_variance')
            metricMismatch('Q2 fatigue metric thresholds failed.');
        end
    elseif ~item.absolute_only
        if item.log10_mae > 0.05 || item.log10_rmse > 0.10 || ...
                ~validCorrelation(item.log10_correlation, 0.99)
            metricMismatch('Q2 log metric thresholds failed.');
        end
    end
end
end

function validateQ2Masks(masks, q2)
requireSchema(masks, 'rebuilt_initial_mex_q2_parent_masks_v2');
if masks.log_floor ~= 1e-14 || masks.negative_tolerance ~= 1e-14 || ...
        masks.outside_absolute_mae_limit ~= 1e-12 || ...
        masks.outside_absolute_max_error_limit ~= 1e-10 || ...
        masks.variance_tolerance ~= 1e-14 || ...
        ~strcmp(masks.mask_set_sha256, q2.mask_set_sha256) || ...
        ~strcmp(masks.parent_cycle1_sha256, q2.parent_cycle1_sha256) || ...
        ~strcmp(masks.parent_lock_sha256, q2.parent_lock_sha256) || ...
        ~strcmp(masks.q2_input_lock_sha256, q2.q2_input_lock_sha256) || ...
        ~strcmp(masks.replay_source_mesh_sha256, q2.replay_source_mesh_sha256) || ...
        ~strcmp(masks.parent_vtk_mesh_sha256, q2.parent_vtk_mesh_sha256)
    identityMismatch('Q2 mask thresholds or identities differ from the result.');
end
end

function validateQ2State(state, q2)
required = {'schema_version','cycle','peak_substep_ordinal','element_ids', ...
    'connectivity','d_elem','alpha_bar_elem','f_alpha_elem','psi_raw_elem', ...
    'g_elem','psi_active_elem','active_semantics','element_ordering', ...
    'runtime_lock_sha256','runtime_initial_sha256','source_commit', ...
    'q2_input_lock_sha256','parent_lock_sha256','parent_cycle1_sha256', ...
    'mask_set_sha256','mesh_ordering_sha256','replay_source_mesh_sha256', ...
    'parent_vtk_mesh_sha256','family_terminal_eligible'};
if ~isstruct(state) || ~all(isfield(state, required)) || ...
        ~strcmp(state.schema_version, 'rebuilt_initial_mex_q2_cycle1_state_v1') || ...
        state.cycle ~= 1 || state.peak_substep_ordinal ~= 4 || ...
        ~strcmp(state.active_semantics, 'mean_gp(g_gp.*psi_raw_gp)') || ...
        ~strcmp(state.element_ordering, 'native_mesh_element_row_order_1_based_v1') || ...
        ~isequal(state.family_terminal_eligible, false)
    artifactIdentityMismatch('Q2 state schema or semantics are invalid.');
end
n = numel(state.element_ids);
fields = {'d_elem','alpha_bar_elem','f_alpha_elem','psi_raw_elem', ...
    'g_elem','psi_active_elem'};
if ~isa(state.element_ids, 'int64') || ...
        ~isequal(state.element_ids(:), int64((1:n)')) || ...
        size(state.connectivity,1) ~= n
    artifactIdentityMismatch('Q2 state element ordering is invalid.');
end
for k = 1:numel(fields)
    value = state.(fields{k});
    if ~isnumeric(value) || ~isequal(size(value), [n 1]) || ...
            any(~isfinite(value))
        artifactIdentityMismatch('Q2 state field shape is invalid.');
    end
end
crossIdentity(state, q2);
end

function validateQ2Terminal(value, q2)
required = {'schema_version','status','cycle','peak_substep_ordinal', ...
    'rebuild_sys_after_recovery','family_terminal_eligible','state_file'};
if ~isstruct(value) || ~all(isfield(value, required)) || ...
        ~strcmp(value.schema_version, 'rebuilt_initial_mex_q2_cycle1_terminal_v1') || ...
        ~strcmp(value.status, 'q2_cycle1_diagnostic_complete') || ...
        value.cycle ~= 1 || value.peak_substep_ordinal ~= 4 || ...
        ~isequal(value.rebuild_sys_after_recovery, false) || ...
        ~isequal(value.family_terminal_eligible, false) || ...
        ~strcmp(value.state_file, 'Q2_CYCLE1_STATE.mat')
    artifactIdentityMismatch('Q2 terminal schema or semantics are invalid.');
end
crossIdentity(value, q2);
end

function crossIdentity(value, q2)
names = {'runtime_lock_sha256','runtime_initial_sha256','source_commit', ...
    'q2_input_lock_sha256','parent_lock_sha256','parent_cycle1_sha256', ...
    'mask_set_sha256','mesh_ordering_sha256','replay_source_mesh_sha256', ...
    'parent_vtk_mesh_sha256'};
for k = 1:numel(names)
    if ~isfield(value, names{k}) || ...
            ~strcmp(char(value.(names{k})), char(q2.(names{k})))
        artifactIdentityMismatch('A Q2 artifact identity differs from Q2_RESULT.');
    end
end
end

function value = loadSingleVariable(path, name)
try
    info = whos('-file', path);
    if numel(info) ~= 1 || ~strcmp(info.name, name)
        invalidMat('MAT artifact variable schema is invalid.');
    end
    loaded = load(path, name);
    value = loaded.(name);
catch exception
    if strcmp(exception.identifier, 'rebuiltMexQualification:InvalidMatArtifact')
        rethrow(exception);
    end
    invalidMat('Unable to parse MAT artifact: %s', exception.message);
end
end

function value = loadMatStruct(path)
try
    info = whos('-file', path);
    if isempty(info), invalidMat('MAT state has no variables.'); end
    value = load(path);
catch exception
    if strcmp(exception.identifier, 'rebuiltMexQualification:InvalidMatArtifact')
        rethrow(exception);
    end
    invalidMat('Unable to parse MAT state: %s', exception.message);
end
end

function requireExactFields(value, names, allowMaskIdentity)
if nargin < 3, allowMaskIdentity = false; end
actual = sort(fieldnames(value)); expected = sort(names(:));
if allowMaskIdentity, expected = sort([expected; {'mask_set_sha256'}]); end
if ~isstruct(value) || ~isscalar(value) || ~isequal(actual, expected)
    artifactMismatch('An artifact record or metric schema is not exact.');
end
end

function requireSameText(left, right, name, lengthValue)
if ~strcmp(textField(left,name,lengthValue), textField(right,name,lengthValue))
    identityMismatch('Q1 input identities differ.');
end
end

function value = validCorrelation(value, threshold)
if ischar(value) || (isstring(value) && isscalar(value))
    value = strcmp(char(value), 'not_applicable_zero_variance');
    return
end
value = isnumeric(value) && isscalar(value) && isfinite(value) && value >= threshold;
end

function value = semanticEqual(left, right)
value = strcmp(jsonencode(canonicalize(left)), jsonencode(canonicalize(right)));
end

function value = canonicalize(value)
if isstruct(value)
    value = orderfields(value);
    names = fieldnames(value);
    for element = 1:numel(value)
        for field = 1:numel(names)
            name = names{field};
            value(element).(name) = canonicalize(value(element).(name));
        end
    end
elseif iscell(value)
    for index = 1:numel(value), value{index} = canonicalize(value{index}); end
end
end

function value = finiteNonnegative(value)
value = isnumeric(value) && isscalar(value) && isfinite(value) && value >= 0;
end

function requireCanonical(actual, expected, identifier)
if ~strcmpi(char(java.io.File(actual).getCanonicalPath()), ...
        char(java.io.File(expected).getCanonicalPath()))
    error(identifier, 'A canonical qualification path was replaced.');
end
end

function requireSchema(value, expected)
if ~isstruct(value) || ~isscalar(value) || ~isfield(value,'schema_version') || ...
        ~strcmp(char(value.schema_version), expected)
    identityMismatch('A qualification schema is not approved.');
end
end

function value = trueLogical(input, name)
value = isfield(input,name) && islogical(input.(name)) && ...
    isscalar(input.(name)) && input.(name);
end

function value = stringField(input, name)
if ~isstruct(input) || ~isfield(input,name) || ...
        ~(ischar(input.(name)) || (isstring(input.(name)) && isscalar(input.(name)))) || ...
        strlength(string(input.(name))) == 0
    identityMismatch('Required qualification text is absent.');
end
value = string(input.(name));
end

function value = textField(input, name, lengthValue)
value = char(stringField(input,name));
if isempty(regexp(value,sprintf('^[0-9a-f]{%d}$',lengthValue),'once'))
    identityMismatch('A qualification digest is malformed.');
end
end

function value = readJson(path, identifier)
if ~isfile(path), error(identifier,'Required qualification JSON is absent.'); end
try
    value = jsondecode(fileread(path));
catch exception
    error(identifier,'Qualification JSON is malformed: %s',exception.message);
end
end

function digest = fileSha256(path)
if ~isfile(path), artifactMismatch('A required artifact is absent.'); end
fileId=fopen(path,'rb'); cleanup=onCleanup(@() fclose(fileId));
md=java.security.MessageDigest.getInstance('SHA-256');
while true
    bytes=fread(fileId,1048576,'*uint8'); if isempty(bytes),break,end
    md.update(bytes);
end
digest=lower(reshape(dec2hex(typecast(md.digest(),'uint8'),2).',1,[]));
end

function publishJsonNoClobber(path,value)
if isfile(path)||isfolder(path)
    error('rebuiltMexQualification:OutputExists','Refusing to overwrite receipt.');
end
temporary=[tempname(fileparts(path)),'.json']; cleanup=onCleanup(@() deleteIfFile(temporary));
fileId=fopen(temporary,'wb'); fileCleanup=onCleanup(@() fclose(fileId));
fwrite(fileId,unicode2native([jsonencode(orderfields(value)),newline],'UTF-8'),'uint8');
clear fileCleanup
try
    java.nio.file.Files.createLink(java.io.File(path).toPath(),java.io.File(temporary).toPath());
catch exception
    if isfile(path)||isfolder(path)
        error('rebuiltMexQualification:OutputExists','Refusing to overwrite receipt.');
    end
    error('rebuiltMexQualification:PublicationFailed','%s',exception.message);
end
clear cleanup; deleteIfFile(temporary);
end

function deleteIfFile(path)
if isfile(path),delete(path);end
end

function artifactMismatch(message)
error('rebuiltMexQualification:ArtifactMismatch','%s',message);
end
function artifactIdentityMismatch(message)
error('rebuiltMexQualification:ArtifactIdentityMismatch','%s',message);
end
function identityMismatch(message)
error('rebuiltMexQualification:IdentityMismatch','%s',message);
end
function metricMismatch(message)
error('rebuiltMexQualification:MetricContractMismatch','%s',message);
end
function invalidMat(message,varargin)
error('rebuiltMexQualification:InvalidMatArtifact',message,varargin{:});
end
