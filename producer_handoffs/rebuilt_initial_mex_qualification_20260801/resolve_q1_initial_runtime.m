function resolvedPath = resolve_q1_initial_runtime(runtimeReceipt, runtimeRoot)
%RESOLVE_Q1_INITIAL_RUNTIME Resolve only the approved locked initial binary.

approvedHash = 'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db';
if ~isstruct(runtimeReceipt) || ~isscalar(runtimeReceipt) || ...
        ~all(isfield(runtimeReceipt, {'runtime_artifact_path', 'initial_sha256'})) || ...
        ~(ischar(runtimeRoot) || (isstring(runtimeRoot) && isscalar(runtimeRoot))) || ...
        ~isfolder(runtimeRoot)
    error('rebuiltMexQ1:InvalidRuntimeReceipt', ...
        'The Q1 runtime receipt or runtime root is invalid.');
end
runtimeRoot = char(runtimeRoot);
expectedPath = fullfile(runtimeRoot, 'initial.mexw64');
receiptPath = char(runtimeReceipt.runtime_artifact_path);
if ~localSamePath(receiptPath, expectedPath)
    error('rebuiltMexQ1:RuntimeResolutionMismatch', ...
        'The runtime receipt does not name the locked runtime-root artifact.');
end
if ~isfile(expectedPath) || ...
        ~strcmpi(char(runtimeReceipt.initial_sha256), approvedHash) || ...
        ~strcmp(localFileHash(expectedPath), approvedHash)
    error('rebuiltMexQ1:RuntimeArtifactMismatch', ...
        'The Q1 runtime artifact does not match the approved rebuilt hash.');
end

addpath(runtimeRoot, '-begin');
clear initial
rehash
resolvedPath = which('initial');
if isempty(resolvedPath) || ~localSamePath(resolvedPath, expectedPath)
    error('rebuiltMexQ1:RuntimeResolutionMismatch', ...
        'MATLAB did not resolve the approved rebuilt initial binary.');
end
resolvedPath = char(java.io.File(resolvedPath).getCanonicalPath());
end

function hash = localFileHash(path)
hasher = java.security.MessageDigest.getInstance('SHA-256');
fileId = fopen(path, 'rb');
if fileId == -1
    error('rebuiltMexQ1:RuntimeArtifactMismatch', ...
        'Unable to read the Q1 runtime artifact.');
end
cleanup = onCleanup(@() fclose(fileId));
while true
    bytes = fread(fileId, 8192, '*uint8');
    if isempty(bytes)
        break;
    end
    hasher.update(bytes);
end
hash = lower(reshape(dec2hex(typecast(hasher.digest(), 'uint8'), 2).', 1, []));
end

function value = localSamePath(left, right)
left = char(java.io.File(left).getCanonicalPath());
right = char(java.io.File(right).getCanonicalPath());
value = strcmpi(left, right);
end
