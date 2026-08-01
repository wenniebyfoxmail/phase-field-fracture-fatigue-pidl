function write_toy_road_json(outputPath, value)
%WRITE_TOY_ROAD_JSON Deterministically publish immutable JSON without clobbering.

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
lockCleanup = onCleanup(@() localDeleteIfExists(lockPath));
if localPathExists(outputPath)
    error('toyRoad:JsonPublishConflict', ...
        'A JSON target appeared while acquiring the publication lock: %s', outputPath);
end

canonicalValue = localCanonicalize(value);
jsonText = [jsonencode(canonicalValue) newline];
jsonBytes = unicode2native(jsonText, 'UTF-8');
tempPath = [tempname(outputDir) '.tmp.json'];
tempCleanup = onCleanup(@() localDeleteIfExists(tempPath));
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

try
    tempJavaPath = java.io.File(tempPath).toPath();
    targetJavaPath = java.io.File(outputPath).toPath();
    java.nio.file.Files.createLink(targetJavaPath, tempJavaPath);
    if ~java.nio.file.Files.isSameFile(tempJavaPath, targetJavaPath)
        error('toyRoad:JsonWriteFailed', ...
            'Published JSON is not linked to the completed temporary file.');
    end
    java.nio.file.Files.delete(tempJavaPath);
catch exception
    if localPathExists(outputPath)
        if strcmp(exception.identifier, 'toyRoad:JsonWriteFailed')
            rethrow(exception);
        end
        error('toyRoad:JsonPublishConflict', ...
            'No-clobber JSON publication refused an existing target: %s', outputPath);
    end
    error('toyRoad:JsonWriteFailed', ...
        'Cannot publish JSON with a same-directory hard link: %s', exception.message);
end
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
