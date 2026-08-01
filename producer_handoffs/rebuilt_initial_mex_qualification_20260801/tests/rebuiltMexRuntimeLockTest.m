classdef rebuiltMexRuntimeLockTest < matlab.unittest.TestCase
    methods (Test)
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

    consumedFortran = [ ...
        sourceHash('Sources/+phase_field/+mex/+fem/+assembly/+equilibrium/initial.f90'); ...
        sourceHash('Sources/+phase_field/+mex/Modules/fem/assembly/equilibrium/initial.f90'); ...
        sourceHash('Sources/+phase_field/+mex/Modules/array_utils.f90'); ...
        sourceHash('Sources/+phase_field/+mex/Modules/matrix_utils.f90'); ...
        sourceHash('Sources/+phase_field/+mex/Modules/mex_utils.f90'); ...
        sourceHash('Sources/+phase_field/+mex/Modules/scalar_utils.f90'); ...
        sourceHash('Sources/+phase_field/+mex/Modules/types.f90')];
    sourceHashes = struct( ...
        'schema_version', 'rebuilt_initial_mex_source_hashes_v1', ...
        'locked_commit', '355d4c83fefc2db88c32031a2dd2623b3de85c89', ...
        'consumed_fortran', consumedFortran, ...
        'locked_git_tree_inventory', cleanCheckoutInventory(), ...
        'clean_checkout_inventory', cleanCheckoutInventory());
    writeJson(fullfile(fixtureRoot, 'build', 'SOURCE_HASHES.json'), sourceHashes);

    toolchain = struct( ...
        'matlab_release', 'R2025b Update 5', ...
        'matlab_version', '25.2.0.3177638', ...
        'architecture', 'win64', ...
        'fortran_compiler', ...
            'Intel(R) Fortran Compiler 2025.3.2 Build 20260112 (ifx.exe)', ...
        'cpp_compiler', ...
            'Microsoft Visual Studio 2022 Community; MSVC 14.44.35207', ...
        'linker', 'Microsoft Visual Studio 2022 link.exe', ...
        'mex_configuration', ...
            'Intel oneAPI 2025 for Fortran with Microsoft Visual Studio 2022');
    writeJson(fullfile(fixtureRoot, 'build', 'TOOLCHAIN.json'), toolchain);
    writeText(fullfile(fixtureRoot, 'build', 'BUILD_COMMAND.txt'), ...
        ["src={fullfile(md,'types.f90'),fullfile(md,'scalar_utils.f90')," ...
         "fullfile(md,'array_utils.f90'),fullfile(md,'matrix_utils.f90')," ...
         "fullfile(md,'mex_utils.f90'),fullfile(md,'fem','assembly','equilibrium','initial.f90')};" newline ...
         "mex('-c',['-I' bd],'COMPFLAGS=$COMPFLAGS /free /fpp',src{:},'-outdir',bd);" newline ...
         "objs={fullfile(bd,'types.obj'),fullfile(bd,'scalar_utils.obj')," ...
         "fullfile(bd,'array_utils.obj'),fullfile(bd,'matrix_utils.obj')," ...
         "fullfile(bd,'mex_utils.obj'),fullfile(bd,'initial.obj')};" newline ...
         "wrapper=fullfile(base,'Sources','+phase_field','+mex','+fem','+assembly','+equilibrium','initial.f90');" newline ...
         "mex(['-I' bd],'COMPFLAGS=$COMPFLAGS /free /fpp',wrapper,objs{:}," ...
         "'-lmwlapack','-lmwblas','-output','initial','-outdir',od);"]);
    writeText(fullfile(fixtureRoot, 'build', 'BUILD_LOG.txt'), ...
        ["Building with 'Intel oneAPI 2025 for Fortran with Microsoft Visual Studio 2022'." newline ...
         "Intel(R) Fortran Compiler for applications running on Intel(R) 64, Version 2025.3.2 Build 20260112" newline ...
         "MEX completed successfully." newline ...
         "Building with 'Intel oneAPI 2025 for Fortran with Microsoft Visual Studio 2022'." newline ...
         "MEX completed successfully." newline ...
         "BUILD_OK bytes=525824" newline]);
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

function inventory = cleanCheckoutInventory()
    root = griphfithRoot();
    command = sprintf('git -C "%s" ls-files "*.m" "*.c" "*.cpp" "*.h"', root);
    [status, output] = system(command);
    assert(status == 0, 'rebuiltMexRuntimeLockTest:GitInventory', ...
        'Unable to enumerate the locked clean-source inventory.');
    paths = splitlines(string(strtrim(output)));
    paths = paths(paths ~= "");
    inventory = repmat(struct('path', '', 'sha256', ''), numel(paths), 1);
    for index = 1:numel(paths)
        inventory(index).path = char(strrep(paths(index), '\\', '/'));
        inventory(index).sha256 = fileHash(fullfile(root, paths(index)));
    end
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

function receipt = validateFixture(fixtureRoot)
    receipt = validate_runtime_lock(fullfile(fixtureRoot, 'RUNTIME_LOCK.json'), ...
        fullfile(fixtureRoot, 'runtime'), griphfithRoot());
end

function writeText(path, value)
    fileId = fopen(path, 'w');
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
    value = 'C:/q4diag/initial_mex_rebuild_diag/out/initial.mexw64';
end

function value = griphfithRoot()
    value = 'C:/q4diag/griphfith-f1b-355d4c83';
end

function value = isAbsolutePath(path)
    value = ~isempty(regexp(char(path), '^[A-Za-z]:[\\/]|^[\\/]', 'once'));
end
