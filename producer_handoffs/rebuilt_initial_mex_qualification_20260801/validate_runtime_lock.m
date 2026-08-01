function receipt = validate_runtime_lock(lockPath, runtimeRoot, gripfithRoot)
%VALIDATE_RUNTIME_LOCK Fail closed unless the sealed runtime and source agree.

approvedHash = 'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db';
legacyHash = '589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340';

requireFile(lockPath);
requireDirectory(runtimeRoot);
requireDirectory(gripfithRoot);
requireSeparateRoots(runtimeRoot, gripfithRoot);
lock = readJson(lockPath);
requireFields(lock, {'schema_version', 'runtime', 'source', 'build'});
requireEqual(lock.schema_version, 'rebuilt_initial_mex_runtime_lock_v1');
validateLegacyFailure(lock, fileparts(lockPath));
validateQualificationGate(lock);

requireFields(lock.runtime, {'artifact_relative_path', 'initial_sha256', ...
    'legacy_initial_sha256', 'dependencies'});
requireRelativePath(lock.runtime.artifact_relative_path);
requireSha256(lock.runtime.initial_sha256);
requireSha256(lock.runtime.legacy_initial_sha256);
if strcmp(lock.runtime.initial_sha256, legacyHash) || ...
        strcmp(lock.runtime.legacy_initial_sha256, legacyHash) && ...
        strcmp(lock.runtime.initial_sha256, legacyHash)
    error('rebuiltMex:LegacyRuntimeRejected', ...
        'The legacy crashing initial.mexw64 hash is not admissible.');
end
if ~strcmp(lock.runtime.initial_sha256, approvedHash)
    error('rebuiltMex:UnknownRuntimeRejected', ...
        'Only the approved rebuilt initial.mexw64 hash is admissible.');
end
if ~strcmp(lock.runtime.legacy_initial_sha256, legacyHash)
    invalidLock('The lock must preserve the known legacy runtime identity.');
end

artifactPath = resolveRelative(runtimeRoot, lock.runtime.artifact_relative_path);
requireFile(artifactPath);
if ~strcmp(sha256File(artifactPath), lock.runtime.initial_sha256)
    error('rebuiltMex:RuntimeArtifactMismatch', ...
        'The runtime artifact does not match the approved rebuilt hash.');
end

requireFields(lock.source, {'commit', 'clean_receipt', 'source_hashes_relative_path'});
requireGitCommit(lock.source.commit);
if ~strcmp(lock.source.commit, '355d4c83fefc2db88c32031a2dd2623b3de85c89')
    error('rebuiltMex:SourceIdentityMismatch', ...
        'The lock does not name the approved clean GRIPHFiTH source commit.');
end
requireRelativePath(lock.source.source_hashes_relative_path);
validateCleanSource(lock.source.clean_receipt, gripfithRoot, lock.source.commit);

requireFields(lock.build, {'command_relative_path', 'log_relative_path', ...
    'toolchain_relative_path', 'command_sha256', 'log_sha256', ...
    'toolchain_sha256', 'source_hashes_sha256', 'output_directory'});
commandPath = resolveRelative(fileparts(lockPath), lock.build.command_relative_path);
logPath = resolveRelative(fileparts(lockPath), lock.build.log_relative_path);
toolchainPath = resolveRelative(fileparts(lockPath), lock.build.toolchain_relative_path);
requireNonemptyFile(commandPath);
requireNonemptyFile(logPath);
validateFileHash(commandPath, lock.build.command_sha256);
validateFileHash(logPath, lock.build.log_sha256);
validateFileHash(toolchainPath, lock.build.toolchain_sha256);
requireEqual(lock.build.command_sha256, ...
    '201eabd998d4d0bc7ee14b6279c4a358c0ef80af90240134883f0a2cb9a5bff0');
requireEqual(lock.build.log_sha256, ...
    'cf97950c53a2bd109b66169e8b9143784336bc23c5f2234fd091bfafb325fd5b');
validateBuildCommand(commandPath);
validateBuildLog(logPath);
outputDirectory = validateBuildOutputDirectory( ...
    lock.build.output_directory, gripfithRoot);
toolchain = readJson(toolchainPath);
requireFields(toolchain, {'matlab_release', 'matlab_version', 'architecture', ...
    'fortran_compiler', 'cpp_compiler', 'linker', 'mex_configuration'});
toolchainReceipt = validateToolchain(toolchain);

sourceHashesPath = resolveRelative(fileparts(lockPath), lock.source.source_hashes_relative_path);
validateFileHash(sourceHashesPath, lock.build.source_hashes_sha256);
sourceHashes = readJson(sourceHashesPath);
validateSourceHashes(sourceHashes, gripfithRoot, lock.source.commit, commandPath);
dependencyReceipt = validateDependencies(lock.runtime.dependencies, gripfithRoot);

buildReceipt = struct( ...
    'command_sha256', lock.build.command_sha256, ...
    'log_sha256', lock.build.log_sha256, ...
    'output_directory', outputDirectory, ...
    'source_hashes_sha256', lock.build.source_hashes_sha256, ...
    'toolchain_sha256', lock.build.toolchain_sha256);
buildReceipt = orderfields(buildReceipt);

receipt = struct( ...
    'build', buildReceipt, ...
    'dependencies', dependencyReceipt, ...
    'schema_version', 'rebuilt_initial_mex_runtime_receipt_v1', ...
    'lock_sha256', sha256File(lockPath), ...
    'initial_sha256', lock.runtime.initial_sha256, ...
    'legacy_initial_sha256', lock.runtime.legacy_initial_sha256, ...
    'source_commit', lock.source.commit, ...
    'source_clean', true, ...
    'runtime_artifact_path', normalizePath(artifactPath), ...
    'source_hashes_sha256', sha256File(sourceHashesPath), ...
    'toolchain', toolchainReceipt);
receipt = orderfields(receipt);
end

function validateCleanSource(cleanReceipt, gripfithRoot, expectedCommit)
requireFields(cleanReceipt, {'git_status_porcelain', 'is_clean'});
if ~islogical(cleanReceipt.is_clean) || ~cleanReceipt.is_clean || ...
        ~isempty(char(cleanReceipt.git_status_porcelain))
    invalidLock('The clean-source receipt is not clean.');
end

[commitStatus, commit] = system(sprintf('git -C "%s" rev-parse HEAD', gripfithRoot));
if commitStatus ~= 0 || ~strcmp(strtrim(commit), expectedCommit)
    error('rebuiltMex:SourceIdentityMismatch', ...
        'The supplied GRIPHFiTH checkout is not at the locked commit.');
end
[statusStatus, sourceStatus] = system(sprintf( ...
    'git -C "%s" status --porcelain=v1 --untracked-files=all', gripfithRoot));
if statusStatus ~= 0 || ~isempty(strtrim(sourceStatus))
    error('rebuiltMex:SourceIdentityMismatch', ...
        'The supplied GRIPHFiTH checkout is not clean.');
end
end

function validateLegacyFailure(lock, lockRoot)
requireFields(lock, {'legacy_failure'});
legacyFailure = lock.legacy_failure;
requireFields(legacyFailure, {'classification', 'exception_code', ...
    'crash_dump_relative_path', 'crash_dump_sha256'});
requireEqual(legacyFailure.classification, ...
    'blocked_before_cycle1: incompatible_legacy_runtime_binary');
requireEqual(legacyFailure.exception_code, '0xc0000005');
requireRelativePath(legacyFailure.crash_dump_relative_path);
crashPath = resolveRelative(lockRoot, legacyFailure.crash_dump_relative_path);
validateFileHash(crashPath, legacyFailure.crash_dump_sha256);
crashText = fileread(crashPath);
if ~contains(crashText, 'Access violation') || ~contains(crashText, 'initial.mexw64')
    invalidLock('The legacy crash receipt does not identify the rejected runtime failure.');
end
end

function validateQualificationGate(lock)
requireFields(lock, {'qualification'});
qualification = lock.qualification;
requireFields(qualification, {'q1_receipt_relative_path', ...
    'q2_receipt_relative_path', 'required_before_family'});
requireRelativePath(qualification.q1_receipt_relative_path);
requireRelativePath(qualification.q2_receipt_relative_path);
if ~islogical(qualification.required_before_family) || ~qualification.required_before_family
    invalidLock('Q1 and Q2 must be required before a family launch.');
end
end

function validateBuildCommand(commandPath)
commandText = fileread(commandPath);
requiredTokens = { ...
    "mex('-c'", 'COMPFLAGS=$COMPFLAGS /free /fpp', ...
    'types.f90', 'scalar_utils.f90', 'array_utils.f90', ...
    'matrix_utils.f90', 'mex_utils.f90', ...
    "'fem','assembly','equilibrium','initial.f90'", ...
    "'+fem','+assembly','+equilibrium','initial.f90'", ...
    'types.obj', 'scalar_utils.obj', 'array_utils.obj', ...
    'matrix_utils.obj', 'mex_utils.obj', 'initial.obj', ...
    "'-lmwlapack'", "'-lmwblas'", "'-output','initial'", ...
    "'-outdir',bd", "'-outdir',od"};
if count(commandText, 'mex(') ~= 2 || count(commandText, '/free /fpp') ~= 2
    invalidLock('The build command does not preserve the exact two-stage MEX invocation.');
end
for index = 1:numel(requiredTokens)
    if ~contains(commandText, requiredTokens{index})
        invalidLock('The build command is missing required source, flag, or link provenance.');
    end
end
end

function validateBuildLog(logPath)
logText = fileread(logPath);
requiredTokens = { ...
    "Building with 'Intel oneAPI 2025 for Fortran with Microsoft Visual Studio 2022'.", ...
    'Intel(R) Fortran Compiler for applications running on Intel(R) 64, Version 2025.3.2 Build 20260112', ...
    'BUILD_OK bytes=525824'};
if count(logText, 'MEX completed successfully.') ~= 2
    invalidLock('The complete successful output from both MEX stages is absent.');
end
for index = 1:numel(requiredTokens)
    if ~contains(logText, requiredTokens{index})
        invalidLock('The successful MEX build output is incomplete.');
    end
end
end

function outputDirectory = validateBuildOutputDirectory(value, gripfithRoot)
requireNonemptyText(value);
if ~isAbsolutePath(char(value))
    invalidLock('The diagnostic build output directory must be absolute.');
end
outputDirectory = normalizePath(value);
sourceRoot = normalizePath(gripfithRoot);
if strcmp(outputDirectory, sourceRoot) || startsWith(outputDirectory, [sourceRoot '/'])
    invalidLock('The build output directory must remain outside the source checkout.');
end
end

function receipt = validateToolchain(toolchain)
requireEqual(toolchain.matlab_release, 'R2025b Update 5');
requireEqual(toolchain.matlab_version, '25.2.0.3177638');
requireEqual(toolchain.architecture, 'win64');
requireEqual(toolchain.fortran_compiler, ...
    'Intel(R) Fortran Compiler 2025.3.2 Build 20260112 (ifx.exe)');
requireEqual(toolchain.cpp_compiler, ...
    'Microsoft Visual Studio 2022 Community; MSVC 14.44.35207');
requireEqual(toolchain.linker, 'Microsoft Visual Studio 2022 link.exe');
requireEqual(toolchain.mex_configuration, ...
    'Intel oneAPI 2025 for Fortran with Microsoft Visual Studio 2022');
receipt = orderfields(struct( ...
    'architecture', char(toolchain.architecture), ...
    'cpp_compiler', char(toolchain.cpp_compiler), ...
    'fortran_compiler', char(toolchain.fortran_compiler), ...
    'linker', char(toolchain.linker), ...
    'matlab_release', char(toolchain.matlab_release), ...
    'matlab_version', char(toolchain.matlab_version), ...
    'mex_configuration', char(toolchain.mex_configuration)));
end

function validateSourceHashes(sourceHashes, gripfithRoot, expectedCommit, commandPath)
requireFields(sourceHashes, {'schema_version', 'locked_commit', ...
    'consumed_fortran', 'locked_git_tree_inventory'});
requireEqual(sourceHashes.schema_version, 'rebuilt_initial_mex_source_hashes_v1');
requireEqual(sourceHashes.locked_commit, expectedCommit);
validateExactFortranRecords(sourceHashes.consumed_fortran, fileread(commandPath));
validateRecordShape(sourceHashes.locked_git_tree_inventory, ...
    'locked Git tree inventory');

[status, output] = system(sprintf( ...
    'git -C "%s" ls-tree -r --name-only %s', ...
    gripfithRoot, expectedCommit));
if status ~= 0
    error('rebuiltMex:SourceIdentityMismatch', ...
        'Unable to inspect the locked Git tree inventory.');
end
treePaths = nonemptyLines(output);
sourceExtensions = {'.m', '.c', '.cpp', '.h'};
isSource = cellfun(@(path) any(endsWith(path, sourceExtensions)), treePaths);
actualPaths = sort(treePaths(isSource));
lockedPaths = sort({sourceHashes.locked_git_tree_inventory.path});
if numel(actualPaths) ~= numel(lockedPaths) || ~isequal(actualPaths(:), lockedPaths(:))
    error('rebuiltMex:SourceIdentityMismatch', ...
        'The locked source inventory differs from the Git tree.');
end
covered = [sourceHashes.consumed_fortran; sourceHashes.locked_git_tree_inventory];
expectedHashes = gitBlobHashes(gripfithRoot, expectedCommit, {covered.path});
if ~isequal({covered.sha256}, expectedHashes)
    error('rebuiltMex:SourceIdentityMismatch', ...
        'A locked source SHA-256 does not match the expected Git blob.');
end
validateConsumedCheckout(sourceHashes.consumed_fortran, gripfithRoot);
validateCoveredIndexFlags(gripfithRoot, {covered.path});
end

function validateExactFortranRecords(records, commandText)
expectedPaths = { ...
    'Sources/+phase_field/+mex/+fem/+assembly/+equilibrium/initial.f90', ...
    'Sources/+phase_field/+mex/Modules/fem/assembly/equilibrium/initial.f90', ...
    'Sources/+phase_field/+mex/Modules/array_utils.f90', ...
    'Sources/+phase_field/+mex/Modules/matrix_utils.f90', ...
    'Sources/+phase_field/+mex/Modules/mex_utils.f90', ...
    'Sources/+phase_field/+mex/Modules/scalar_utils.f90', ...
    'Sources/+phase_field/+mex/Modules/types.f90'};
expectedHashes = { ...
    '7b01879214121697ee4d2cae4ca33d6b1827630506b187869cc3ed4df18ffa1a', ...
    '841d75a0073a71f5e11650509a68a6f569f908993a7b8edd897d57fd9f833d5b', ...
    'cb34b087ec436b5602a0412e8853c6d060c75057643b12839c63918007751070', ...
    '7598974feff3dd63535a8252fde429a1f3cf213b316fba932dd466590f4b8685', ...
    'eeb012763a8fae176bad78350142e16fc004932798f0d49a21fa8aade0d6f272', ...
    '27c199fe42048095e115b8e8cf1d3593429920c57a0e17910511c96e2e7116ea', ...
    'fa5524117c035d13fa5d366581f30bbdcd430200ae9973a83be43d2ddbd9a409'};
commandFragments = { ...
    "fullfile(base,'Sources','+phase_field','+mex','+fem','+assembly','+equilibrium','initial.f90')", ...
    "fullfile(md,'fem','assembly','equilibrium','initial.f90')", ...
    "fullfile(md,'array_utils.f90')", "fullfile(md,'matrix_utils.f90')", ...
    "fullfile(md,'mex_utils.f90')", "fullfile(md,'scalar_utils.f90')", ...
    "fullfile(md,'types.f90')"};
validateRecordShape(records, 'consumed Fortran');
if numel(records) ~= numel(expectedPaths)
    invalidLock('The consumed Fortran set is not the exact approved seven inputs.');
end
[paths, order] = sort({records.path});
[expectedPaths, expectedOrder] = sort(expectedPaths);
if ~isequal(paths(:), expectedPaths(:)) || ...
        ~isequal({records(order).sha256}.', expectedHashes(expectedOrder).')
    invalidLock('The consumed Fortran paths or hashes are not the approved set.');
end
for index = 1:numel(commandFragments)
    if ~contains(commandText, commandFragments{index})
        invalidLock('A consumed Fortran input is absent from the exact build command.');
    end
end
end

function validateRecordShape(records, label)
if ~isstruct(records) || isempty(records) || ~all(isfield(records, {'path', 'sha256'}))
    invalidLock('The %s record set is malformed.', label);
end
paths = {records.path};
if numel(unique(paths)) ~= numel(paths)
    invalidLock('The %s record set has duplicate paths.', label);
end
for index = 1:numel(records)
    requireRelativePath(records(index).path);
    requireSha256(records(index).sha256);
end
end

function hashes = gitBlobHashes(root, commit, paths)
persistent cachedCommit cachedPaths cachedHashes
if isequal(cachedCommit, commit) && isequal(cachedPaths, paths)
    hashes = cachedHashes;
    return
end
hashes = cell(size(paths));
for index = 1:numel(paths)
    hashes{index} = gitBlobHash(root, commit, paths{index});
end
cachedCommit = commit;
cachedPaths = paths;
cachedHashes = hashes;
end

function hash = gitBlobHash(root, commit, path)
command = javaArray('java.lang.String', 7);
values = {'git', '-C', root, 'cat-file', 'blob', [commit, ':', path], ''};
for index = 1:6
    command(index) = java.lang.String(values{index});
end
command(7) = [];
outputPath = [tempname, '.blob'];
cleanup = onCleanup(@() deleteIfFile(outputPath));
builder = java.lang.ProcessBuilder(command(1:6));
builder.redirectErrorStream(true);
builder.redirectOutput(java.io.File(outputPath));
process = builder.start();
status = process.waitFor();
if status ~= 0
    error('rebuiltMex:SourceIdentityMismatch', ...
        'Unable to read raw Git blob %s.', path);
end
hash = sha256File(outputPath);
end

function deleteIfFile(path)
if isfile(path)
    delete(path);
end
end

function validateConsumedCheckout(records, root)
for index = 1:numel(records)
    filePath = resolveRelative(root, records(index).path);
    requireFile(filePath);
    if ~strcmp(sha256File(filePath), records(index).sha256)
        error('rebuiltMex:SourceIdentityMismatch', ...
            'A consumed Fortran checkout file differs from its raw Git blob.');
    end
end
end

function validateCoveredIndexFlags(root, coveredPaths)
[status, output] = system(sprintf('git -C "%s" ls-files -v', root));
if status ~= 0
    error('rebuiltMex:SourceIdentityMismatch', ...
        'Unable to inspect source index flags.');
end
lines = nonemptyLines(output);
for index = 1:numel(lines)
    line = lines{index};
    if numel(line) < 3 || ~ismember(line(3:end), coveredPaths)
        continue
    end
    flag = line(1);
    if flag == 'S' || (flag >= 'a' && flag <= 'z')
        error('rebuiltMex:SourceIdentityMismatch', ...
            'Covered source uses skip-worktree or assume-unchanged.');
    end
end
end

function receipt = validateDependencies(dependencies, gripfithRoot)
requiredNames = {'AMOR', 'AT1_HISTORY_FATIGUE', 'cholmod2'};
requiredOwners = {'griphfith', 'griphfith', 'absolute'};
requiredPaths = { ...
    'Sources/+phase_field/+mex/+fem/+assembly/+equilibrium/AMOR.mexw64', ...
    'Sources/+phase_field/+mex/+fem/+assembly/+pf/AT1_HISTORY_FATIGUE.mexw64', ...
    'C:/SuiteSparse/SuiteSparse-dev/CHOLMOD/MATLAB/cholmod2.mexw64'};
requiredHashes = { ...
    '64abee69f2c441730dc2efa4047ac45ab1d1b40e20c4822ed6e992adcd6b19e7', ...
    '53e8fd0b229817b7c14c52a5b6afaa957692f475057b79b9a9a10195ccb92e60', ...
    '86a2f15543eda1f7223a1733d935d37e9e2f4f2c2d8db3c4adc2c0f675c27329'};
if ~isstruct(dependencies) || numel(dependencies) ~= numel(requiredNames) || ...
        ~all(isfield(dependencies, {'name', 'owner', 'path', 'sha256'}))
    invalidLock('The runtime dependency set is malformed.');
end
names = {dependencies.name};
if numel(unique(names)) ~= numel(names) || ~isequal(sort(names), sort(requiredNames))
    invalidLock('The runtime dependency names are not the required unique set.');
end
paths = cellfun(@(path) lower(strrep(char(path), '\', '/')), ...
    {dependencies.path}, 'UniformOutput', false);
if numel(unique(paths)) ~= numel(paths)
    invalidLock('The runtime dependency set has duplicate paths.');
end
receipt = repmat(struct('name', '', 'path', '', 'sha256', ''), ...
    numel(requiredNames), 1);
for index = 1:numel(requiredNames)
    dependency = dependencies(strcmp(names, requiredNames{index}));
    requireSha256(dependency.sha256);
    requireEqual(dependency.owner, requiredOwners{index});
    requireEqual(dependency.path, requiredPaths{index});
    if ~strcmp(char(dependency.sha256), requiredHashes{index})
        error('rebuiltMex:RuntimeDependencyMismatch', ...
            'The locked %s dependency hash is not approved.', dependency.name);
    end
    if strcmp(dependency.owner, 'griphfith')
        requireRelativePath(dependency.path);
        filePath = resolveRelative(gripfithRoot, dependency.path);
    elseif strcmp(dependency.owner, 'absolute') && strcmp(dependency.name, 'cholmod2')
        filePath = char(dependency.path);
        if ~isAbsolutePath(filePath)
            invalidLock('The externally installed cholmod2 path must be absolute.');
        end
    else
        invalidLock('The runtime dependency owner is invalid.');
    end
    requireFile(filePath);
    if ~strcmp(sha256File(filePath), dependency.sha256)
        error('rebuiltMex:RuntimeDependencyMismatch', ...
            'The unchanged %s runtime dependency hash does not match.', dependency.name);
    end
    receipt(index) = struct( ...
        'name', char(dependency.name), ...
        'path', normalizePath(filePath), ...
        'sha256', char(dependency.sha256));
end
receipt = orderfields(receipt);
end

function requireSeparateRoots(runtimeRoot, gripfithRoot)
runtimeCanonical = normalizePath(runtimeRoot);
sourceCanonical = normalizePath(gripfithRoot);
if startsWith(runtimeCanonical, [sourceCanonical '/']) || ...
        startsWith(sourceCanonical, [runtimeCanonical '/']) || ...
        strcmp(runtimeCanonical, sourceCanonical)
    invalidLock('The runtime artifact and source checkout identities must be separate.');
end
end

function value = readJson(path)
requireFile(path);
try
    value = jsondecode(fileread(path));
catch exception
    invalidLock('Unable to decode %s: %s', path, exception.message);
end
end

function path = resolveRelative(root, relativePath)
requireRelativePath(relativePath);
path = fullfile(root, strrep(char(relativePath), '/', filesep));
rootCanonical = normalizePath(root);
pathCanonical = normalizePath(path);
if ~startsWith(pathCanonical, [rootCanonical '/'])
    invalidLock('A locked path escapes its declared root.');
end
end

function requireRelativePath(value)
value = char(value);
if isempty(value) || isAbsolutePath(value) || contains(value, '..') || ...
        contains(value, '\\') || startsWith(value, '/')
    invalidLock('A locked relative path is malformed.');
end
end

function value = isAbsolutePath(path)
value = ~isempty(regexp(path, '^[A-Za-z]:[\\/]|^[\\/]', 'once'));
end

function requireFields(value, names)
if ~isstruct(value) || ~all(isfield(value, names))
    invalidLock('A required runtime-lock field is absent.');
end
end

function requireEqual(value, expected)
if ~ischar(value) && ~isstring(value) || ~strcmp(char(value), expected)
    invalidLock('A locked runtime identity is invalid.');
end
end

function requireSha256(value)
if ~ischar(value) && ~isstring(value) || ...
        isempty(regexp(char(value), '^[0-9a-f]{64}$', 'once'))
    invalidLock('A SHA-256 value is malformed.');
end
end

function requireGitCommit(value)
if ~ischar(value) && ~isstring(value) || ...
        isempty(regexp(char(value), '^[0-9a-f]{40}$', 'once'))
    invalidLock('A Git commit identity is malformed.');
end
end

function requireNonemptyText(value)
if ~ischar(value) && ~isstring(value) || isempty(strtrim(char(value)))
    invalidLock('A required provenance text field is absent.');
end
end

function requireFile(path)
if ~isfile(path)
    invalidLock('A required runtime-lock file is absent.');
end
end

function requireDirectory(path)
if ~isfolder(path)
    invalidLock('A required runtime-lock directory is absent.');
end
end

function requireNonemptyFile(path)
requireFile(path);
if dir(path).bytes == 0
    invalidLock('A required provenance file is empty.');
end
end

function validateFileHash(path, expectedHash)
requireSha256(expectedHash);
requireFile(path);
if ~strcmp(sha256File(path), expectedHash)
    invalidLock('A locked provenance file hash does not match.');
end
end

function lines = nonemptyLines(value)
lines = splitlines(string(strtrim(value)));
lines = cellstr(lines(lines ~= ""));
end

function digest = sha256File(path)
fileId = fopen(path, 'rb');
if fileId < 0
    invalidLock('Unable to read a locked file.');
end
cleanup = onCleanup(@() fclose(fileId));
messageDigest = java.security.MessageDigest.getInstance('SHA-256');
while true
    bytes = fread(fileId, 1048576, '*uint8');
    if isempty(bytes)
        break
    end
    messageDigest.update(bytes);
end
digest = lower(reshape(dec2hex(typecast(messageDigest.digest(), 'uint8'), 2).', 1, []));
end

function path = normalizePath(path)
path = char(java.io.File(path).getCanonicalPath());
path = lower(strrep(path, '\', '/'));
end

function invalidLock(message, varargin)
error('rebuiltMex:InvalidRuntimeLock', message, varargin{:});
end
