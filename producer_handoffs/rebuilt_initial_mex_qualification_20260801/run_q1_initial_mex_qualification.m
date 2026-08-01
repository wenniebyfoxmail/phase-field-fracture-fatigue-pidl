function receipt = run_q1_initial_mex_qualification(config)
%RUN_Q1_INITIAL_MEX_QUALIFICATION Run isolated assembly qualification only.

targets = {'Q1_RESULT.json', 'Q1_METRICS.mat', 'Q1_RECEIPT.json'};
if isstruct(config) && isscalar(config) && isfield(config, 'output_root') && ...
        (ischar(config.output_root) || ...
         (isstring(config.output_root) && isscalar(config.output_root)))
    preliminaryRoot = char(config.output_root);
    for index = 1:numel(targets)
        if isfile(fullfile(preliminaryRoot, targets{index})) || ...
                isfolder(fullfile(preliminaryRoot, targets{index}))
            error('rebuiltMexQ1:OutputExists', ...
                'Refusing to overwrite Q1 artifact: %s', targets{index});
        end
    end
end
localRequireConfig(config);
outputRoot = char(config.output_root);
if ~isfolder(outputRoot)
    [created, message] = mkdir(outputRoot);
    if ~created
        error('rebuiltMexQ1:PublicationFailed', ...
            'Unable to create Q1 output root: %s', message);
    end
end

runtimeReceipt = validate_runtime_lock(config.runtime_lock_path, ...
    config.runtime_root, config.source_root);
localRequireRuntimeReceipt(runtimeReceipt);
resolve_q1_initial_runtime(runtimeReceipt, config.runtime_root);
input = build_q1_native_input(config.source_root);
inputSha256 = localHashInput(input);

[referenceValues{1:12}] = assemble_initial_reference_q4( ...
    input.MESH, input.DOFS, input.t, input.QUADRATURE, ...
    input.MAT_CHAR, input.CC, input.field_vars);
reference = cell2struct(referenceValues(:), localOutputNames(), 1);
[candidateValues{1:12}] = initial(input.MESH, input.DOFS, input.t, ...
    input.QUADRATURE, input.MAT_CHAR, input.CC, input.field_vars);
candidate = cell2struct(candidateValues(:), localOutputNames(), 1);
metrics = compare_q1_initial_outputs(reference, candidate, input);

metricsPath = fullfile(outputRoot, 'Q1_METRICS.mat');
localPublishMat(metricsPath, metrics);
metricsSha256 = localFileHash(metricsPath);
result = orderfields(struct('schema_version', 'rebuilt_initial_mex_q1_result_v1', ...
    'passed', true, 'input_sha256', inputSha256, ...
    'runtime_lock_sha256', char(runtimeReceipt.lock_sha256), ...
    'runtime_initial_sha256', char(runtimeReceipt.initial_sha256), ...
    'source_commit', char(runtimeReceipt.source_commit), ...
    'metrics_sha256', metricsSha256));
localPublishJson(fullfile(outputRoot, 'Q1_RESULT.json'), result);

receipt = orderfields(struct( ...
    'schema_version', 'rebuilt_initial_mex_q1_receipt_v1', ...
    'passed', true, 'input_sha256', inputSha256, ...
    'runtime_lock_sha256', char(runtimeReceipt.lock_sha256), ...
    'runtime_initial_sha256', char(runtimeReceipt.initial_sha256), ...
    'source_commit', char(runtimeReceipt.source_commit), ...
    'source_clean', logical(runtimeReceipt.source_clean), ...
    'metrics', metrics, ...
    'metrics_sha256', metricsSha256, ...
    'result_sha256', localFileHash(fullfile(outputRoot, 'Q1_RESULT.json'))));
localPublishJson(fullfile(outputRoot, 'Q1_RECEIPT.json'), receipt);
end

function localRequireConfig(config)
required = {'output_root', 'runtime_lock_path', 'runtime_root', 'source_root'};
if ~isstruct(config) || ~isscalar(config) || ...
        ~isequal(sort(fieldnames(config)), sort(required(:)))
    error('rebuiltMexQ1:InvalidConfig', ...
        'Q1 config is missing required runtime or output fields.');
end
if ~(ischar(config.output_root) || ...
        (isstring(config.output_root) && isscalar(config.output_root))) || ...
        strlength(string(config.output_root)) == 0
    error('rebuiltMexQ1:InvalidConfig', 'output_root must be nonempty text.');
end
end

function localRequireRuntimeReceipt(receipt)
required = {'lock_sha256', 'initial_sha256', 'source_commit', ...
    'source_clean', 'runtime_artifact_path'};
if ~isstruct(receipt) || ~isscalar(receipt) || ~all(isfield(receipt, required)) || ...
        ~receipt.source_clean || ~localSha(receipt.lock_sha256, 64) || ...
        ~localSha(receipt.initial_sha256, 64) || ~localSha(receipt.source_commit, 40)
    error('rebuiltMexQ1:InvalidRuntimeReceipt', ...
        'The validated runtime receipt is incomplete or malformed.');
end
end

function value = localSha(textValue, lengthValue)
value = (ischar(textValue) || (isstring(textValue) && isscalar(textValue))) && ...
    ~isempty(regexp(char(textValue), ...
        sprintf('^[0-9a-fA-F]{%d}$', lengthValue), 'once'));
end

function hash = localHashInput(input)
hasher = java.security.MessageDigest.getInstance('SHA-256');
items = { ...
    'mesh_meta', [input.MESH.num_node input.MESH.num_elem input.MESH.nel ...
        input.MESH.dim input.MESH.tensors]; ...
    'node', input.MESH.node(:, 1:input.MESH.dim); ...
    'elem', input.MESH.elem(:, 1:input.MESH.nel); ...
    'material_id', input.MESH.elem_material_id(:); ...
    'dof_meta', [input.DOFS.num_dof input.DOFS.num_dof_node]; ...
    'thickness', input.t; ...
    'gauss_weights', input.QUADRATURE.gauss_W(:); ...
    'shape_derivatives', input.QUADRATURE.dNdxi; ...
    'shape_functions', input.QUADRATURE.Nxi; ...
    'constitutive', input.CC; ...
    'damage', input.field_vars(:); ...
    'top_nodes', input.top_node_ids(:)};
for index = 1:size(items, 1)
    localHashBytes(hasher, unicode2native(items{index, 1}, 'UTF-8'));
    value = double(items{index, 2});
    localHashBytes(hasher, typecast(uint64(size(value)), 'uint8'));
    localHashBytes(hasher, typecast(value(:), 'uint8'));
end
residualStiffness = [input.MAT_CHAR.res_stiff];
localHashBytes(hasher, typecast(double(residualStiffness(:)), 'uint8'));
hash = localDigestHex(hasher);
end

function localHashBytes(hasher, bytes)
hasher.update(uint8(bytes(:)));
end

function localPublishJson(path, value)
bytes = unicode2native([jsonencode(orderfields(value)), newline], 'UTF-8');
localPublishBytes(path, bytes);
end

function localPublishMat(path, metrics)
temporary = [tempname(fileparts(path)), '.tmp.mat'];
cleanup = onCleanup(@() localDelete(temporary));
save(temporary, 'metrics', '-v7.3');
localHardLink(temporary, path);
clear cleanup
localDelete(temporary);
end

function localPublishBytes(path, bytes)
temporary = [tempname(fileparts(path)), '.tmp'];
fileId = fopen(temporary, 'wb');
if fileId == -1
    error('rebuiltMexQ1:PublicationFailed', 'Unable to create a temporary artifact.');
end
cleanupFile = onCleanup(@() fclose(fileId));
written = fwrite(fileId, bytes, 'uint8');
if written ~= numel(bytes)
    error('rebuiltMexQ1:PublicationFailed', 'Unable to write a complete artifact.');
end
clear cleanupFile
cleanupPath = onCleanup(@() localDelete(temporary));
localHardLink(temporary, path);
clear cleanupPath
localDelete(temporary);
end

function localHardLink(source, target)
try
    java.nio.file.Files.createLink(java.io.File(target).toPath(), ...
        java.io.File(source).toPath());
catch exception
    if isfile(target) || isfolder(target)
        error('rebuiltMexQ1:OutputExists', ...
            'Refusing to overwrite Q1 artifact: %s', target);
    end
    error('rebuiltMexQ1:PublicationFailed', ...
        'Unable to publish Q1 artifact: %s', exception.message);
end
end

function hash = localFileHash(path)
hasher = java.security.MessageDigest.getInstance('SHA-256');
fileId = fopen(path, 'rb');
if fileId == -1
    error('rebuiltMexQ1:PublicationFailed', 'Unable to hash Q1 artifact.');
end
cleanup = onCleanup(@() fclose(fileId));
while true
    bytes = fread(fileId, 8192, '*uint8');
    if isempty(bytes)
        break;
    end
    hasher.update(bytes);
end
hash = localDigestHex(hasher);
end

function hash = localDigestHex(hasher)
hash = lower(reshape(dec2hex(typecast(hasher.digest(), 'uint8'), 2).', 1, []));
end

function localDelete(path)
if isfile(path)
    delete(path);
end
end

function names = localOutputNames()
names = {'K_vect'; 'i_row'; 'j_col'; 'M_vector'; 'i_row_sig'; ...
    'j_col_sig'; 'eps_vector'; 'i_row_eps'; 'j_col_eps'; ...
    'sig0_vector'; 'i_row_pf'; 'j_col_pf'};
end
