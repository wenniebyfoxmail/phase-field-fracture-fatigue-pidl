function publish_toy_road_state_atomic(state, outputPath, atomicMoveFcn)
%PUBLISH_TOY_ROAD_STATE_ATOMIC Publish one immutable v7.3 state shard.

if nargin < 3
    atomicMoveFcn = @localNioAtomicMove;
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

tempPath = [tempname(outputDir) '.tmp.mat'];
tempCleanup = onCleanup(@() localDeleteIfExists(tempPath));
save(tempPath, '-struct', 'state', '-v7.3');
if localPathExists(outputPath)
    error('toyRoad:StatePublishConflict', ...
        'A state shard appeared before atomic publication: %s', outputPath);
end
try
    atomicMoveFcn(tempPath, outputPath);
catch exception
    if localPathExists(outputPath)
        error('toyRoad:StatePublishConflict', ...
            'Atomic publication refused an existing state shard: %s', outputPath);
    end
    if localIsAtomicMoveNotSupported(exception)
        error('toyRoad:AtomicMoveNotSupported', ...
            ['The filesystem rejected required ATOMIC_MOVE publication; ' ...
            'the state shard was not published: %s'], exception.message);
    end
    error('toyRoad:StateWriteFailed', ...
        'Cannot atomically publish state shard: %s', exception.message);
end
if ~isfile(outputPath)
    error('toyRoad:StateWriteFailed', ...
        'Atomic publication returned without creating the state shard: %s', outputPath);
end
end

function localNioAtomicMove(tempPath, outputPath)
sourcePath = java.io.File(tempPath).toPath();
targetPath = java.io.File(outputPath).toPath();
options = javaArray('java.nio.file.CopyOption', 1);
options(1) = java.nio.file.StandardCopyOption.ATOMIC_MOVE;
java.nio.file.Files.move(sourcePath, targetPath, options);
end

function value = localIsAtomicMoveNotSupported(exception)
value = contains(exception.identifier, 'AtomicMoveNotSupportedException') || ...
    contains(exception.message, 'AtomicMoveNotSupportedException');
end

function value = localPathExists(path)
value = isfile(path) || isfolder(path);
end

function localDeleteIfExists(path)
if isfile(path)
    delete(path);
end
end
