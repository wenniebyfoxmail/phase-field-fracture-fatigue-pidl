function publication = write_toy_road_json(outputPath, value, operations)
%WRITE_TOY_ROAD_JSON Deterministically publish immutable JSON without clobbering.

if nargin < 3
    operations = struct();
end
operations = localResolveOperations(operations);
publication = struct( ...
    'committed', false, ...
    'cleanup_pending', false, ...
    'cleanup_error_identifier', "", ...
    'cleanup_error_message', "", ...
    'cleanup_pending_paths', strings(0, 1));

if ~(ischar(outputPath) || (isstring(outputPath) && isscalar(outputPath))) || ...
        strlength(string(outputPath)) == 0
    error('toyRoad:InvalidJsonOutput', 'outputPath must be nonempty text.');
end
outputPath = char(outputPath);
outputDir = fileparts(outputPath);
if isempty(outputDir)
    outputDir = pwd;
end
if ~isfolder(outputDir)
    error('toyRoad:InvalidJsonOutput', ...
        'The JSON output directory must already exist: %s', outputDir);
end
if localPathExists(outputPath)
    error('toyRoad:JsonOutputExists', ...
        'Refusing to overwrite existing JSON: %s', outputPath);
end

lockPath = [outputPath '.publish.lock'];
try
    lockCreated = java.io.File(lockPath).createNewFile();
catch exception
    error('toyRoad:JsonWriteFailed', ...
        'Cannot create JSON publication lock: %s', exception.message);
end
if ~lockCreated
    error('toyRoad:JsonPublishConflict', ...
        'Another writer owns the JSON publication lock: %s', lockPath);
end
if localPathExists(outputPath)
    localBestEffortDelete(lockPath);
    error('toyRoad:JsonPublishConflict', ...
        'A JSON target appeared while acquiring the publication lock: %s', outputPath);
end

try
    canonicalValue = localCanonicalize(value);
    jsonText = [jsonencode(canonicalValue) newline];
    jsonBytes = unicode2native(jsonText, 'UTF-8');
    tempPath = [tempname(outputDir) '.tmp.json'];
    fileId = fopen(tempPath, 'wb');
    if fileId == -1
        error('toyRoad:JsonWriteFailed', ...
            'Cannot create temporary JSON in %s.', outputDir);
    end
    fileCleanup = onCleanup(@() localCloseIfOpen(fileId));
    written = fwrite(fileId, jsonBytes, 'uint8');
    if written ~= numel(jsonBytes)
        error('toyRoad:JsonWriteFailed', ...
            'Failed to write complete JSON bytes for %s.', outputPath);
    end
    clear fileCleanup
    operations.before_link(outputPath, tempPath);
catch exception
    if exist('tempPath', 'var')
        localBestEffortDelete(tempPath);
    end
    localBestEffortDelete(lockPath);
    rethrow(exception);
end

try
    tempJavaPath = java.io.File(tempPath).toPath();
    targetJavaPath = java.io.File(outputPath).toPath();
    java.nio.file.Files.createLink(targetJavaPath, tempJavaPath);
catch exception
    localBestEffortDelete(tempPath);
    localBestEffortDelete(lockPath);
    if localPathExists(outputPath)
        error('toyRoad:JsonPublishConflict', ...
            'No-clobber JSON publication refused an existing target: %s', outputPath);
    end
    error('toyRoad:JsonWriteFailed', ...
        'Cannot publish JSON with a same-directory hard link: %s', exception.message);
end

% Files.createLink is the publication linearization point. Nothing below may
% turn the now-visible immutable target into a publication failure.
publication.committed = true;
publication = localPostCommitCleanup(publication, tempPath, lockPath, operations);
end

function operations = localResolveOperations(overrides)
if ~isstruct(overrides) || ~isscalar(overrides)
    error('toyRoad:InvalidJsonOperations', ...
        'JSON publication operations must be a scalar struct.');
end
operations = struct( ...
    'before_link', @(varargin) [], ...
    'delete_temp', @localDeleteIfExists, ...
    'delete_lock', @localDeleteIfExists);
names = fieldnames(overrides);
for index = 1:numel(names)
    name = names{index};
    if ~isfield(operations, name) || ~isa(overrides.(name), 'function_handle')
        error('toyRoad:InvalidJsonOperations', ...
            'Unknown or invalid JSON publication operation: %s.', name);
    end
    operations.(name) = overrides.(name);
end
end

function publication = localPostCommitCleanup(publication, tempPath, lockPath, operations)
paths = {tempPath, lockPath};
cleanupFunctions = {operations.delete_temp, operations.delete_lock};
for index = 1:numel(paths)
    try
        cleanupFunctions{index}(paths{index});
    catch exception
        if strlength(publication.cleanup_error_identifier) == 0
            publication.cleanup_error_identifier = string(exception.identifier);
            publication.cleanup_error_message = string(exception.message);
        end
    end
end
pending = cellfun(@localPathExists, paths);
publication.cleanup_pending = any(pending);
publication.cleanup_pending_paths = string(paths(pending)).';
end

function value = localCanonicalize(value)
if isstruct(value)
    value = orderfields(value);
    names = fieldnames(value);
    for elementIndex = 1:numel(value)
        for fieldIndex = 1:numel(names)
            name = names{fieldIndex};
            value(elementIndex).(name) = localCanonicalize(value(elementIndex).(name));
        end
    end
elseif iscell(value)
    for index = 1:numel(value)
        value{index} = localCanonicalize(value{index});
    end
end
end

function value = localPathExists(path)
value = isfile(path) || isfolder(path);
end

function localCloseIfOpen(fileId)
if fileId ~= -1
    fclose(fileId);
end
end

function localDeleteIfExists(path)
if isfile(path)
    delete(path);
end
end

function localBestEffortDelete(path)
try
    localDeleteIfExists(path);
catch
end
end
