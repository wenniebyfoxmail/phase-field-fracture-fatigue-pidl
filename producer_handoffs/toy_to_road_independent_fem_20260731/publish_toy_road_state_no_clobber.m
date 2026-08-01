function publish_toy_road_state_no_clobber(state, outputPath, createLinkFcn)
%PUBLISH_TOY_ROAD_STATE_NO_CLOBBER Atomically publish one immutable shard.
% The completed v7.3 temp file is in the target directory. Creating a hard
% link atomically exposes that complete file at the target name and cannot
% replace an existing directory entry. Removing the temp name afterward
% leaves the target linked to the same file content.

if nargin < 3
    createLinkFcn = @localCreateHardLink;
end

outputDir = fileparts(outputPath);
if ~isfolder(outputDir)
    [created, message] = mkdir(outputDir);
    if ~created
        error('toyRoad:StateWriteFailed', ...
            'Cannot create state output directory: %s', message);
    end
end

if localPathExists(outputPath)
    error('toyRoad:StateOutputExists', ...
        'Refusing to overwrite existing state shard: %s', outputPath);
end
lockPath = [outputPath '.publish.lock'];
try
    lockFile = java.io.File(lockPath);
    lockCreated = lockFile.createNewFile();
catch exception
    error('toyRoad:StateWriteFailed', ...
        'Cannot create state publication lock: %s', exception.message);
end
if ~lockCreated
    error('toyRoad:StatePublishConflict', ...
        'Another publisher owns the state publication lock: %s', lockPath);
end
lockCleanup = onCleanup(@() localDeleteIfExists(lockPath));
if localPathExists(outputPath)
    error('toyRoad:StatePublishConflict', ...
        'A state shard appeared while acquiring the publication lock: %s', outputPath);
end

% tempname(outputDir) makes the hard-link source same-directory/same-volume.
tempPath = [tempname(outputDir) '.tmp.mat'];
tempCleanup = onCleanup(@() localDeleteIfExists(tempPath));
save(tempPath, '-struct', 'state', '-v7.3');
if localPathExists(outputPath)
    error('toyRoad:StatePublishConflict', ...
        'A state shard appeared before no-clobber publication: %s', outputPath);
end
try
    createLinkFcn(tempPath, outputPath);
catch exception
    if localPathExists(outputPath)
        error('toyRoad:StatePublishConflict', ...
            'No-clobber publication refused an existing state shard: %s', outputPath);
    end
    if localIsUnsupportedHardLink(exception)
        error('toyRoad:HardLinkNotSupported', ...
            ['The filesystem rejected required same-volume hard-link ' ...
            'publication; the state shard was not published: %s'], ...
            exception.message);
    end
    error('toyRoad:StateWriteFailed', ...
        'Cannot publish state shard with a hard link: %s', exception.message);
end

tempJavaPath = java.io.File(tempPath).toPath();
targetJavaPath = java.io.File(outputPath).toPath();
try
    if ~java.nio.file.Files.isSameFile(tempJavaPath, targetJavaPath)
        error('toyRoad:StateWriteFailed', ...
            'Published target is not the completed temporary state file.');
    end
    java.nio.file.Files.delete(tempJavaPath);
catch exception
    if strcmp(exception.identifier, 'toyRoad:StateWriteFailed')
        rethrow(exception);
    end
    error('toyRoad:StateWriteFailed', ...
        'Cannot remove the temporary hard-link name: %s', exception.message);
end
end

function localCreateHardLink(tempPath, outputPath)
targetJavaPath = java.io.File(outputPath).toPath();
tempJavaPath = java.io.File(tempPath).toPath();
java.nio.file.Files.createLink(targetJavaPath, tempJavaPath);
end

function value = localIsUnsupportedHardLink(exception)
value = contains(exception.identifier, 'UnsupportedOperationException') || ...
    contains(exception.message, 'UnsupportedOperationException');
end

function value = localPathExists(path)
value = isfile(path) || isfolder(path);
end

function localDeleteIfExists(path)
if isfile(path)
    delete(path);
end
end
