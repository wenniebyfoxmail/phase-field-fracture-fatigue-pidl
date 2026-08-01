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

[metrics, inputSha256, runtimeReceipt] = ...
    recompute_q1_initial_qualification_metrics(config.runtime_lock_path, ...
    config.runtime_root, config.source_root);
localRequireRuntimeReceipt(runtimeReceipt);

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
