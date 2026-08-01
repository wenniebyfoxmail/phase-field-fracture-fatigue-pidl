classdef rebuiltMexRuntimeLockTest < matlab.unittest.TestCase
    methods (Test)
        function testValidatesCommittedProductionPackage(testCase)
            root = handoffRoot();
            receipt = validate_runtime_lock(fullfile(root, 'RUNTIME_LOCK.json'), ...
                fullfile(root, 'runtime'), griphfithRoot());

            verifyEqual(testCase, receipt.initial_sha256, approvedInitialHash());
            verifyEqual(testCase, receipt.lock_sha256, ...
                fileHash(fullfile(root, 'RUNTIME_LOCK.json')));
            verifyEqual(testCase, receipt.build.command_sha256, ...
                '201eabd998d4d0bc7ee14b6279c4a358c0ef80af90240134883f0a2cb9a5bff0');
            verifyEqual(testCase, receipt.build.log_sha256, ...
                'cf97950c53a2bd109b66169e8b9143784336bc23c5f2234fd091bfafb325fd5b');
            verifyEqual(testCase, receipt.source_commit, lockedSourceCommit());
            verifyTrue(testCase, receipt.source_clean);
        end

        function testAcceptsOnlyApprovedRuntimeWithCompleteProvenance(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);

            receipt = validate_runtime_lock( ...
                fullfile(fixtureRoot, 'RUNTIME_LOCK.json'), ...
                fullfile(fixtureRoot, 'runtime'), griphfithRoot());

            verifyEqual(testCase, receipt.initial_sha256, ...
                'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db');
            verifyEqual(testCase, receipt.source_commit, ...
                '355d4c83fefc2db88c32031a2dd2623b3de85c89');
            verifyTrue(testCase, receipt.source_clean);
            verifyEqual(testCase, {receipt.dependencies.name}, ...
                {'AMOR', 'AT1_HISTORY_FATIGUE', 'cholmod2'});
            verifyTrue(testCase, all(arrayfun( ...
                @(record) isAbsolutePath(record.path), receipt.dependencies)));
            verifyEqual(testCase, receipt.toolchain.mex_configuration, ...
                'Intel oneAPI 2025 for Fortran with Microsoft Visual Studio 2022');
            verifyTrue(testCase, isAbsolutePath(receipt.build.output_directory));
        end

        function testRejectsLegacyInitialRuntime(testCase)
            fixtureRoot = makeRuntimeFixture(testCase, 'initial_sha256', ...
                '589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340');

            verifyError(testCase, @() validate_runtime_lock( ...
                fullfile(fixtureRoot, 'RUNTIME_LOCK.json'), ...
                fullfile(fixtureRoot, 'runtime'), griphfithRoot()), ...
                'rebuiltMex:LegacyRuntimeRejected');
        end

        function testRejectsUnknownInitialRuntime(testCase)
            fixtureRoot = makeRuntimeFixture(testCase, 'initial_sha256', repmat('a', 1, 64));

            verifyError(testCase, @() validate_runtime_lock( ...
                fullfile(fixtureRoot, 'RUNTIME_LOCK.json'), ...
                fullfile(fixtureRoot, 'runtime'), griphfithRoot()), ...
                'rebuiltMex:UnknownRuntimeRejected');
        end

        function testRejectsMissingBuildCommandOrLog(testCase)
            names = {'BUILD_COMMAND.txt', 'BUILD_LOG.txt'};
            for index = 1:numel(names)
                fixtureRoot = makeRuntimeFixture(testCase);
                delete(fullfile(fixtureRoot, 'build', names{index}));

                verifyError(testCase, @() validateFixture(fixtureRoot), ...
                    'rebuiltMex:InvalidRuntimeLock');
            end
        end

        function testRejectsSemanticallyIncompleteBuildCommand(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            commandPath = fullfile(fixtureRoot, 'build', 'BUILD_COMMAND.txt');
            writeText(commandPath, 'mex(''-c'',''COMPFLAGS=$COMPFLAGS /free'')');
            updateLockedBuildHash(fixtureRoot, 'command_sha256', commandPath);

            verifyError(testCase, @() validateFixture(fixtureRoot), ...
                'rebuiltMex:InvalidRuntimeLock');
        end

        function testRejectsIncompleteSuccessfulBuildLog(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            logPath = fullfile(fixtureRoot, 'build', 'BUILD_LOG.txt');
            writeText(logPath, 'Build claimed successful without compiler output.');
            updateLockedBuildHash(fixtureRoot, 'log_sha256', logPath);

            verifyError(testCase, @() validateFixture(fixtureRoot), ...
                'rebuiltMex:InvalidRuntimeLock');
        end

        function testRejectsBuildCommandMutationWithAllTokensPresent(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            commandPath = fullfile(fixtureRoot, 'build', 'BUILD_COMMAND.txt');
            appendText(commandPath, [newline, '% unauthorized command mutation']);
            updateLockedBuildHash(fixtureRoot, 'command_sha256', commandPath);

            verifyError(testCase, @() validateFixture(fixtureRoot), ...
                'rebuiltMex:InvalidRuntimeLock');
        end

        function testRejectsBuildLogMutationWithAllTokensPresent(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            logPath = fullfile(fixtureRoot, 'build', 'BUILD_LOG.txt');
            appendText(logPath, [newline, 'unauthorized log mutation']);
            updateLockedBuildHash(fixtureRoot, 'log_sha256', logPath);

            verifyError(testCase, @() validateFixture(fixtureRoot), ...
                'rebuiltMex:InvalidRuntimeLock');
        end

        function testRejectsMissingCompilerIdentity(testCase)
            fields = {'fortran_compiler', 'cpp_compiler', 'linker', ...
                'mex_configuration'};
            for index = 1:numel(fields)
                fixtureRoot = makeRuntimeFixture(testCase);
                toolchainPath = fullfile(fixtureRoot, 'build', 'TOOLCHAIN.json');
                toolchain = jsondecode(fileread(toolchainPath));
                toolchain = rmfield(toolchain, fields{index});
                writeJson(toolchainPath, toolchain);
                updateLockedBuildHash(fixtureRoot, 'toolchain_sha256', toolchainPath);

                verifyError(testCase, @() validateFixture(fixtureRoot), ...
                    'rebuiltMex:InvalidRuntimeLock');
            end
        end

        function testRejectsChangedCompilerIdentity(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            toolchainPath = fullfile(fixtureRoot, 'build', 'TOOLCHAIN.json');
            toolchain = jsondecode(fileread(toolchainPath));
            toolchain.fortran_compiler = 'Unknown nonempty compiler';
            writeJson(toolchainPath, toolchain);
            updateLockedBuildHash(fixtureRoot, 'toolchain_sha256', toolchainPath);

            verifyError(testCase, @() validateFixture(fixtureRoot), ...
                'rebuiltMex:InvalidRuntimeLock');
        end

        function testRejectsMissingCleanSourceReceipt(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            lockPath = fullfile(fixtureRoot, 'RUNTIME_LOCK.json');
            lock = jsondecode(fileread(lockPath));
            lock.source = rmfield(lock.source, 'clean_receipt');
            writeJson(lockPath, lock);

            verifyError(testCase, @() validate_runtime_lock( ...
                lockPath, fullfile(fixtureRoot, 'runtime'), griphfithRoot()), ...
                'rebuiltMex:InvalidRuntimeLock');
        end

        function testRejectsNonCleanSourceReceipt(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            lockPath = fullfile(fixtureRoot, 'RUNTIME_LOCK.json');
            lock = jsondecode(fileread(lockPath));
            lock.source.clean_receipt.is_clean = false;
            lock.source.clean_receipt.git_status_porcelain = ' M Sources/changed.m';
            writeJson(lockPath, lock);

            verifyError(testCase, @() validateFixture(fixtureRoot), ...
                'rebuiltMex:InvalidRuntimeLock');
        end

        function testRejectsChangedSourceCommit(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            lockPath = fullfile(fixtureRoot, 'RUNTIME_LOCK.json');
            lock = jsondecode(fileread(lockPath));
            lock.source.commit = repmat('b', 1, 40);
            writeJson(lockPath, lock);

            verifyError(testCase, @() validate_runtime_lock( ...
                lockPath, fullfile(fixtureRoot, 'runtime'), griphfithRoot()), ...
                'rebuiltMex:SourceIdentityMismatch');
        end

        function testRejectsChangedUnmodifiedRuntimeDependencies(testCase)
            dependencyNames = {'AMOR', 'AT1_HISTORY_FATIGUE', 'cholmod2'};
            for index = 1:numel(dependencyNames)
                fixtureRoot = makeRuntimeFixture(testCase);
                lockPath = fullfile(fixtureRoot, 'RUNTIME_LOCK.json');
                lock = jsondecode(fileread(lockPath));
                dependencyIndex = find(strcmp({lock.runtime.dependencies.name}, dependencyNames{index}));
                lock.runtime.dependencies(dependencyIndex).sha256 = repmat('c', 1, 64);
                writeJson(lockPath, lock);

                verifyError(testCase, @() validate_runtime_lock( ...
                    lockPath, fullfile(fixtureRoot, 'runtime'), griphfithRoot()), ...
                    'rebuiltMex:RuntimeDependencyMismatch');
            end
        end

        function testRejectsMissingUnmodifiedRuntimeDependencies(testCase)
            dependencyNames = {'AMOR', 'AT1_HISTORY_FATIGUE', 'cholmod2'};
            for index = 1:numel(dependencyNames)
                fixtureRoot = makeRuntimeFixture(testCase);
                lockPath = fullfile(fixtureRoot, 'RUNTIME_LOCK.json');
                lock = jsondecode(fileread(lockPath));
                keep = ~strcmp({lock.runtime.dependencies.name}, dependencyNames{index});
                lock.runtime.dependencies = lock.runtime.dependencies(keep);
                writeJson(lockPath, lock);

                verifyError(testCase, @() validateFixture(fixtureRoot), ...
                    'rebuiltMex:InvalidRuntimeLock');
            end
        end

        function testRejectsDuplicateDependencyPaths(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            lockPath = fullfile(fixtureRoot, 'RUNTIME_LOCK.json');
            lock = jsondecode(fileread(lockPath));
            lock.runtime.dependencies(2).path = lock.runtime.dependencies(1).path;
            lock.runtime.dependencies(2).sha256 = lock.runtime.dependencies(1).sha256;
            writeJson(lockPath, lock);

            verifyError(testCase, @() validateFixture(fixtureRoot), ...
                'rebuiltMex:InvalidRuntimeLock');
        end

        function testRejectsDuplicateOrMalformedSourcePaths(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            sourceHashesPath = fullfile(fixtureRoot, 'build', 'SOURCE_HASHES.json');
            sourceHashes = jsondecode(fileread(sourceHashesPath));
            sourceHashes.consumed_fortran(end + 1) = sourceHashes.consumed_fortran(1);
            writeJson(sourceHashesPath, sourceHashes);
            updateLockedBuildHash(fixtureRoot, 'source_hashes_sha256', sourceHashesPath);

            verifyError(testCase, @() validateFixture(fixtureRoot), ...
                'rebuiltMex:InvalidRuntimeLock');
        end

        function testRejectsMissingOrExtraFortranInputs(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            sourceHashesPath = fullfile(fixtureRoot, 'build', 'SOURCE_HASHES.json');
            sourceHashes = jsondecode(fileread(sourceHashesPath));
            sourceHashes.consumed_fortran(end) = [];
            writeJson(sourceHashesPath, sourceHashes);
            updateLockedBuildHash(fixtureRoot, 'source_hashes_sha256', sourceHashesPath);
            verifyError(testCase, @() validateFixture(fixtureRoot), ...
                'rebuiltMex:InvalidRuntimeLock');

            fixtureRoot = makeRuntimeFixture(testCase);
            sourceHashesPath = fullfile(fixtureRoot, 'build', 'SOURCE_HASHES.json');
            sourceHashes = jsondecode(fileread(sourceHashesPath));
            sourceHashes.consumed_fortran(end + 1) = sourceHash( ...
                'Sources/+phase_field/+mex/Modules/system_factors.f90');
            writeJson(sourceHashesPath, sourceHashes);
            updateLockedBuildHash(fixtureRoot, 'source_hashes_sha256', sourceHashesPath);
            verifyError(testCase, @() validateFixture(fixtureRoot), ...
                'rebuiltMex:InvalidRuntimeLock');
        end

        function testRejectsArchiveConvertedHashInPlaceOfRawBlobHash(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            sourceHashesPath = fullfile(fixtureRoot, 'build', 'SOURCE_HASHES.json');
            sourceHashes = jsondecode(fileread(sourceHashesPath));
            target = find(strcmp({sourceHashes.locked_git_tree_inventory.path}, ...
                'Sources/+phase_field/System.m'));
            sourceHashes.locked_git_tree_inventory(target).sha256 = ...
                '89846dbbd57ef72f5fe068376ab67ff5ce915d269f455a531c3fdb1747632305';
            writeJson(sourceHashesPath, sourceHashes);
            updateLockedBuildHash(fixtureRoot, 'source_hashes_sha256', sourceHashesPath);

            verifyError(testCase, @() validateFixture(fixtureRoot), ...
                'rebuiltMex:SourceIdentityMismatch');
        end

        function testValidationIgnoresAmbientAutocrlf(testCase)
            sourceRoot = makeSourceFixture(testCase);
            fixtureRoot = makeRuntimeFixture(testCase);
            settings = {'true', 'false'};
            for index = 1:numel(settings)
                runGit(sourceRoot, sprintf('config core.autocrlf %s', ...
                    settings{index}));
                receipt = validateFixture(fixtureRoot, sourceRoot);
                verifyEqual(testCase, receipt.source_commit, lockedSourceCommit());
                verifyTrue(testCase, receipt.source_clean);
            end
        end

        function testAcceptsRawConsumedBytesAndRejectsConvertedBytes(testCase)
            sourceRoot = makeSourceFixture(testCase);
            fixtureRoot = makeRuntimeFixture(testCase);
            relativePath = ...
                'Sources/+phase_field/+mex/Modules/types.f90';
            sourcePath = fullfile(sourceRoot, relativePath);
            rawHash = gitBlobHash(sourceRoot, lockedSourceCommit(), relativePath);
            verifyEqual(testCase, fileHash(sourcePath), rawHash);
            validateFixture(fixtureRoot, sourceRoot);

            runGit(sourceRoot, 'config core.autocrlf true');
            convertLfToCrlf(sourcePath);
            verifyNotEqual(testCase, fileHash(sourcePath), rawHash);
            runGit(sourceRoot, sprintf( ...
                'update-index --assume-unchanged -- "%s"', relativePath));
            verifyEmpty(testCase, strtrim(runGit(sourceRoot, ...
                'status --porcelain=v1 --untracked-files=all')));
            try
                validateFixture(fixtureRoot, sourceRoot);
                verifyFail(testCase, 'Converted consumed bytes were accepted.');
            catch exception
                verifyEqual(testCase, exception.identifier, ...
                    'rebuiltMex:SourceIdentityMismatch');
                verifySubstring(testCase, exception.message, ...
                    'consumed Fortran checkout file differs');
            end
        end

        function testRejectsUntrackedCoveredSource(testCase)
            sourceRoot = makeSourceFixture(testCase);
            fixtureRoot = makeRuntimeFixture(testCase);
            validateFixture(fixtureRoot, sourceRoot);
            writeText(fullfile(sourceRoot, 'Sources', 'untracked_source.m'), 'x = 1;');

            verifyError(testCase, @() validateFixture(fixtureRoot, sourceRoot), ...
                'rebuiltMex:SourceIdentityMismatch');
        end

        function testRejectsAssumeUnchangedAndSkipWorktreeFlags(testCase)
            flags = {'--assume-unchanged', '--skip-worktree'};
            path = 'Sources/+phase_field/System.m';
            for index = 1:numel(flags)
                sourceRoot = makeSourceFixture(testCase);
                fixtureRoot = makeRuntimeFixture(testCase);
                validateFixture(fixtureRoot, sourceRoot);
                runGit(sourceRoot, sprintf('update-index %s -- "%s"', ...
                    flags{index}, path));

                verifyError(testCase, @() validateFixture(fixtureRoot, sourceRoot), ...
                    'rebuiltMex:SourceIdentityMismatch');
            end
        end

        function testRejectsChangedLockedGitTreeInventory(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            sourceHashesPath = fullfile(fixtureRoot, 'build', 'SOURCE_HASHES.json');
            sourceHashes = jsondecode(fileread(sourceHashesPath));
            sourceHashes.locked_git_tree_inventory(1).sha256 = repmat('d', 1, 64);
            writeJson(sourceHashesPath, sourceHashes);
            updateLockedBuildHash(fixtureRoot, 'source_hashes_sha256', sourceHashesPath);

            verifyError(testCase, @() validateFixture(fixtureRoot), ...
                'rebuiltMex:SourceIdentityMismatch');
        end

        function testRejectsMalformedSha256(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            lockPath = fullfile(fixtureRoot, 'RUNTIME_LOCK.json');
            lock = jsondecode(fileread(lockPath));
            lock.build.command_sha256 = 'not-a-sha256';
            writeJson(lockPath, lock);

            verifyError(testCase, @() validateFixture(fixtureRoot), ...
                'rebuiltMex:InvalidRuntimeLock');
        end

        function testRejectsBuildOutputInsideSourceCheckout(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            lockPath = fullfile(fixtureRoot, 'RUNTIME_LOCK.json');
            lock = jsondecode(fileread(lockPath));
            lock.build.output_directory = fullfile(griphfithRoot(), 'build');
            writeJson(lockPath, lock);

            verifyError(testCase, @() validateFixture(fixtureRoot), ...
                'rebuiltMex:InvalidRuntimeLock');
        end

        function testRejectsRuntimeSourceIdentityConflation(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);

            verifyError(testCase, @() validate_runtime_lock( ...
                fullfile(fixtureRoot, 'RUNTIME_LOCK.json'), ...
                griphfithRoot(), griphfithRoot()), ...
                'rebuiltMex:InvalidRuntimeLock');
        end

        function testRejectsMissingLegacyFailureOrQualificationGate(testCase)
            fixtureRoot = makeRuntimeFixture(testCase);
            lockPath = fullfile(fixtureRoot, 'RUNTIME_LOCK.json');
            lock = jsondecode(fileread(lockPath));
            lock = rmfield(lock, 'legacy_failure');
            writeJson(lockPath, lock);

            verifyError(testCase, @() validate_runtime_lock( ...
                lockPath, fullfile(fixtureRoot, 'runtime'), griphfithRoot()), ...
                'rebuiltMex:InvalidRuntimeLock');
        end
    end
end

function fixtureRoot = makeRuntimeFixture(testCase, varargin)
    parser = inputParser;
    addParameter(parser, 'initial_sha256', ...
        'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db');
    parse(parser, varargin{:});

    fixture = matlab.unittest.fixtures.TemporaryFolderFixture;
    testCase.applyFixture(fixture);
    fixtureRoot = fixture.Folder;
    mkdir(fullfile(fixtureRoot, 'runtime'));
    mkdir(fullfile(fixtureRoot, 'build'));
    copyfile(approvedInitialPath(), fullfile(fixtureRoot, 'runtime', 'initial.mexw64'));

    provenanceFiles = {'SOURCE_HASHES.json', 'TOOLCHAIN.json', ...
        'BUILD_COMMAND.txt', 'BUILD_LOG.txt'};
    for index = 1:numel(provenanceFiles)
        copyfile(fullfile(handoffRoot(), 'build', provenanceFiles{index}), ...
            fullfile(fixtureRoot, 'build', provenanceFiles{index}));
    end
    writeText(fullfile(fixtureRoot, 'build', 'LEGACY_CRASH_DUMP.txt'), ...
        'Access violation in the legacy initial.mexw64 runtime.');

    dependencies = [ ...
        runtimeDependency('AMOR', ...
            'Sources/+phase_field/+mex/+fem/+assembly/+equilibrium/AMOR.mexw64'); ...
        runtimeDependency('AT1_HISTORY_FATIGUE', ...
            'Sources/+phase_field/+mex/+fem/+assembly/+pf/AT1_HISTORY_FATIGUE.mexw64'); ...
        struct('name', 'cholmod2', 'owner', 'absolute', ...
            'path', 'C:/SuiteSparse/SuiteSparse-dev/CHOLMOD/MATLAB/cholmod2.mexw64', ...
            'sha256', fileHash('C:/SuiteSparse/SuiteSparse-dev/CHOLMOD/MATLAB/cholmod2.mexw64'))];
    lock = struct( ...
        'schema_version', 'rebuilt_initial_mex_runtime_lock_v1', ...
        'runtime', struct( ...
            'artifact_relative_path', 'initial.mexw64', ...
            'initial_sha256', parser.Results.initial_sha256, ...
            'legacy_initial_sha256', '589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340', ...
            'dependencies', dependencies), ...
        'legacy_failure', struct( ...
            'classification', 'blocked_before_cycle1: incompatible_legacy_runtime_binary', ...
            'exception_code', '0xc0000005', ...
            'crash_dump_relative_path', 'build/LEGACY_CRASH_DUMP.txt', ...
            'crash_dump_sha256', fileHash(fullfile(fixtureRoot, 'build', 'LEGACY_CRASH_DUMP.txt'))), ...
        'source', struct( ...
            'commit', '355d4c83fefc2db88c32031a2dd2623b3de85c89', ...
            'clean_receipt', struct('git_status_porcelain', '', 'is_clean', true), ...
            'source_hashes_relative_path', 'build/SOURCE_HASHES.json'), ...
        'build', struct( ...
            'command_relative_path', 'build/BUILD_COMMAND.txt', ...
            'log_relative_path', 'build/BUILD_LOG.txt', ...
            'toolchain_relative_path', 'build/TOOLCHAIN.json', ...
            'command_sha256', fileHash(fullfile(fixtureRoot, 'build', 'BUILD_COMMAND.txt')), ...
            'log_sha256', fileHash(fullfile(fixtureRoot, 'build', 'BUILD_LOG.txt')), ...
            'toolchain_sha256', fileHash(fullfile(fixtureRoot, 'build', 'TOOLCHAIN.json')), ...
            'source_hashes_sha256', fileHash(fullfile(fixtureRoot, 'build', 'SOURCE_HASHES.json')), ...
            'output_directory', 'C:/q4diag/initial_mex_rebuild_diag/out'), ...
        'qualification', struct( ...
            'q1_receipt_relative_path', 'Q1_RECEIPT.json', ...
            'q2_receipt_relative_path', 'Q2_RECEIPT.json', ...
            'required_before_family', true));
    writeJson(fullfile(fixtureRoot, 'RUNTIME_LOCK.json'), lock);
end

function dependency = runtimeDependency(name, relativePath)
    dependency = struct('name', name, 'owner', 'griphfith', ...
        'path', relativePath, 'sha256', fileHash(fullfile(griphfithRoot(), relativePath)));
end

function record = sourceHash(relativePath)
    record = struct('path', relativePath, ...
        'sha256', fileHash(fullfile(griphfithRoot(), relativePath)));
end

function writeJson(path, value)
    writeText(path, [jsonencode(value), newline]);
end

function updateLockedBuildHash(fixtureRoot, fieldName, artifactPath)
    lockPath = fullfile(fixtureRoot, 'RUNTIME_LOCK.json');
    lock = jsondecode(fileread(lockPath));
    lock.build.(fieldName) = fileHash(artifactPath);
    writeJson(lockPath, lock);
end

function receipt = validateFixture(fixtureRoot, sourceRoot)
    if nargin < 2
        sourceRoot = griphfithRoot();
    end
    receipt = validate_runtime_lock(fullfile(fixtureRoot, 'RUNTIME_LOCK.json'), ...
        fullfile(fixtureRoot, 'runtime'), sourceRoot);
end

function writeText(path, value)
    fileId = fopen(path, 'w');
    cleanup = onCleanup(@() fclose(fileId));
    fprintf(fileId, '%s', value);
end

function appendText(path, value)
    fileId = fopen(path, 'a');
    cleanup = onCleanup(@() fclose(fileId));
    fprintf(fileId, '%s', value);
end

function hash = fileHash(path)
    messageDigest = java.security.MessageDigest.getInstance('SHA-256');
    messageDigest.update(readBytes(path));
    hash = lower(reshape(dec2hex(typecast(messageDigest.digest(), 'uint8'), 2)', 1, []));
end

function bytes = readBytes(path)
    fileId = fopen(path, 'rb');
    cleanup = onCleanup(@() fclose(fileId));
    bytes = fread(fileId, Inf, '*uint8');
end

function value = approvedInitialPath()
    value = fullfile(handoffRoot(), 'runtime', 'initial.mexw64');
end

function value = griphfithRoot()
    value = getenv('GRIPHFITH_SOURCE_ROOT');
    if isempty(value)
        value = 'C:/q4diag/griphfith-f1b-355d4c83';
    end
    assert(isfolder(value), 'rebuiltMexRuntimeLockTest:MissingSourceRoot', ...
        'Set GRIPHFITH_SOURCE_ROOT to the locked clean source checkout.');
end

function value = handoffRoot()
    value = fileparts(fileparts(mfilename('fullpath')));
end

function value = approvedInitialHash()
    value = 'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db';
end

function value = lockedSourceCommit()
    value = '355d4c83fefc2db88c32031a2dd2623b3de85c89';
end

function sourceRoot = makeSourceFixture(testCase)
    fixture = matlab.unittest.fixtures.TemporaryFolderFixture;
    testCase.applyFixture(fixture);
    sourceRoot = fullfile(fixture.Folder, 'griphfith');
    [status, output] = system(sprintf( ...
        'git clone --quiet --shared --no-checkout "%s" "%s"', ...
        griphfithRoot(), sourceRoot));
    assert(status == 0, 'rebuiltMexRuntimeLockTest:GitClone', '%s', output);
    runGit(sourceRoot, 'config core.autocrlf false');
    runGit(sourceRoot, sprintf('checkout --quiet %s', lockedSourceCommit()));
    dependencyPaths = { ...
        'Sources/+phase_field/+mex/+fem/+assembly/+equilibrium/AMOR.mexw64', ...
        'Sources/+phase_field/+mex/+fem/+assembly/+pf/AT1_HISTORY_FATIGUE.mexw64'};
    for index = 1:numel(dependencyPaths)
        destination = fullfile(sourceRoot, dependencyPaths{index});
        if ~isfolder(fileparts(destination))
            mkdir(fileparts(destination));
        end
        copyfile(fullfile(griphfithRoot(), dependencyPaths{index}), destination);
    end
end

function output = runGit(root, arguments)
    [status, output] = system(sprintf('git -C "%s" %s', root, arguments));
    assert(status == 0, 'rebuiltMexRuntimeLockTest:GitCommand', '%s', output);
end

function hash = gitBlobHash(root, commit, relativePath)
    command = javaArray('java.lang.String', 7);
    values = {'git', '-C', root, 'cat-file', 'blob', ...
        [commit, ':', relativePath], ''};
    for index = 1:6
        command(index) = java.lang.String(values{index});
    end
    command(7) = [];
    builder = java.lang.ProcessBuilder(command(1:6));
    builder.redirectErrorStream(true);
    outputPath = [tempname, '.blob'];
    cleanup = onCleanup(@() deleteIfFile(outputPath));
    builder.redirectOutput(java.io.File(outputPath));
    process = builder.start();
    status = process.waitFor();
    assert(status == 0, 'rebuiltMexRuntimeLockTest:GitBlob', ...
        'Unable to read raw Git blob %s.', relativePath);
    bytes = readBytes(outputPath);
    messageDigest = java.security.MessageDigest.getInstance('SHA-256');
    messageDigest.update(bytes);
    hash = lower(reshape(dec2hex(typecast(messageDigest.digest(), 'uint8'), 2)', 1, []));
end

function deleteIfFile(path)
    if isfile(path)
        delete(path);
    end
end

function convertLfToCrlf(path)
    bytes = readBytes(path).';
    converted = zeros(1, numel(bytes) + nnz(bytes == 10), 'uint8');
    outputIndex = 1;
    for inputIndex = 1:numel(bytes)
        if bytes(inputIndex) == 10
            converted(outputIndex) = 13;
            outputIndex = outputIndex + 1;
        end
        converted(outputIndex) = bytes(inputIndex);
        outputIndex = outputIndex + 1;
    end
    fileId = fopen(path, 'wb');
    cleanup = onCleanup(@() fclose(fileId));
    fwrite(fileId, converted, 'uint8');
end

function value = isAbsolutePath(path)
    value = ~isempty(regexp(char(path), '^[A-Za-z]:[\\/]|^[\\/]', 'once'));
end
