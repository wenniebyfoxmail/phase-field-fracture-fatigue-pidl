function run_toy_road_runtime_bridge(executionLockPath, measurementReceiptPath)
% Measure the exact one-shot runtime before authorizing the producer entrypoint.
lock = localReadJson(executionLockPath, 'execution lock');
localRequire(strcmp(lock.authorization_scope, 'production_authorized'), ...
    'Runtime bridge requires a production-authorized execution lock.');

releaseObject = matlabRelease;
matlabIdentity = struct;
matlabIdentity.release = char(releaseObject.Release);
matlabIdentity.update = localReleaseUpdate(releaseObject.Update);
versionText = version;
matlabIdentity.version = regexp(versionText, '^\S+', 'match', 'once');
matlabIdentity.computer = computer;
matlabIdentity.executable_sha256 = fileSha256( ...
    fullfile(matlabroot, 'bin', 'matlab.exe'));
matlabIdentity.blas = version('-blas');
matlabIdentity.lapack = version('-lapack');

actualPath = strsplit(path, pathsep);
expectedPath = cellstr(string(lock.runtime_expectations.matlab.absolute_path_order));
localRequire(numel(actualPath) >= numel(expectedPath), ...
    'MATLAB path is shorter than the locked path prefix.');
actualPrefix = actualPath(1:numel(expectedPath));
actualPrefix = cellfun(@localCanonicalPath, actualPrefix, 'UniformOutput', false);
expectedPath = cellfun(@localCanonicalPath, expectedPath, 'UniformOutput', false);
localRequire(isequal(actualPrefix, expectedPath), ...
    'Measured absolute MATLAB path precedence differs from the lock.');
matlabIdentity.absolute_path_order = actualPrefix;

binaryIdentity = struct;
binaryIdentity.initial = fileSha256(which( ...
    'phase_field.mex.fem.assembly.equilibrium.initial'));
binaryIdentity.AMOR = fileSha256(which( ...
    'phase_field.mex.fem.assembly.equilibrium.AMOR'));
binaryIdentity.AT1_HISTORY_FATIGUE = fileSha256(which( ...
    'phase_field.mex.fem.assembly.pf.AT1_HISTORY_FATIGUE'));
binaryIdentity.cholmod2 = fileSha256(which('cholmod2'));

matlabFields = {'release', 'update', 'version', 'computer', ...
    'executable_sha256', 'blas', 'lapack'};
for index = 1:numel(matlabFields)
    field = matlabFields{index};
    localRequire(strcmp(matlabIdentity.(field), ...
        lock.runtime_expectations.matlab.(field)), ...
        sprintf('Measured MATLAB identity differs from the lock: %s.', field));
end
binaryFields = {'initial', 'AMOR', 'AT1_HISTORY_FATIGUE', 'cholmod2'};
for index = 1:numel(binaryFields)
    field = binaryFields{index};
    localRequire(strcmp(binaryIdentity.(field), ...
        lock.runtime_expectations.binary_sha256.(field)), ...
        sprintf('Measured binary identity differs from the lock: %s.', field));
end

receipt = struct;
receipt.schema_version = 'toy_road_runtime_measurement_v1';
receipt.protocol_version = lock.protocol_version;
receipt.authorization_scope = lock.authorization_scope;
receipt.status = 'PASS';
receipt.producer_entrypoint_authorized = true;
receipt.execution_input_lock_sha256 = fileSha256(executionLockPath);
receipt.matlab = matlabIdentity;
receipt.binary_sha256 = binaryIdentity;
localWriteJsonCreateNew(measurementReceiptPath, receipt);

main_toy_road_family_case;
end

function value = localReadJson(filePath, label)
localRequire(isfile(filePath), sprintf('%s is missing.', label));
value = jsondecode(fileread(filePath));
localRequire(isstruct(value) && isscalar(value), ...
    sprintf('%s must be one JSON object.', label));
end

function output = localCanonicalPath(input)
output = char(java.io.File(input).getCanonicalPath());
end

function output = localReleaseUpdate(input)
if isnumeric(input) && isscalar(input) && isfinite(input)
    output = sprintf('Update %d', input);
    return
end
output = char(string(input));
if ~startsWith(output, 'Update ')
    output = ['Update ' output];
end
end

function localWriteJsonCreateNew(filePath, value)
localRequire(~isfile(filePath), 'Runtime measurement receipt already exists.');
options = javaArray('java.nio.file.OpenOption', 2);
options(1) = java.nio.file.StandardOpenOption.CREATE_NEW;
options(2) = java.nio.file.StandardOpenOption.WRITE;
stream = java.nio.file.Files.newOutputStream(java.nio.file.Paths.get(filePath, ...
    javaArray('java.lang.String', 0)), options);
cleanup = onCleanup(@() stream.close()); %#ok<NASGU>
bytes = unicode2native(jsonencode(value), 'UTF-8');
stream.write(bytes, 0, numel(bytes));
stream.flush();
end

function localRequire(condition, message)
if ~condition
    error('toyRoadP0:RuntimeQualificationFailed', '%s', message);
end
end

function digest = fileSha256(path)
localRequire(ischar(path) || (isstring(path) && isscalar(path)), ...
    'SHA-256 path must be scalar text.');
path = char(path);
localRequire(isfile(path), ['Cannot hash missing runtime file: ' path]);
fileId = fopen(path, 'rb');
localRequire(fileId >= 0, ['Cannot read runtime file: ' path]);
cleanup = onCleanup(@() fclose(fileId)); %#ok<NASGU>
bytes = fread(fileId, Inf, '*uint8');
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(bytes);
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end
