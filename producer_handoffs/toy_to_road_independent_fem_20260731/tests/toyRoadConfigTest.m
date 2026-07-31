function tests = toyRoadConfigTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
addpath(lockDir());
testCase.addTeardown(@() rmpath(lockDir()));
end

function testT3AmplitudeChangesOnlyAtLockedBoundaries(testCase)
cfg = build_toy_road_case_config("T3_loading_history", lockDir());
verifyEqual(testCase, cfg.umax_for_cycle([1 30 31 60 61 150]), ...
    [0.108 0.108 0.126 0.126 0.120 0.120], 'AbsTol', 1e-14);
verifyEqual(testCase, cfg.n_step, 5);
verifyEqual(testCase, cfg.censor_cap, 150);
end

function testT1UsesTheLockedInitialDefect(testCase)
cfg = build_toy_road_case_config("T1_initial_defect", lockDir());
verifyEqual(testCase, cfg.initial_defect.tip, [0.125 0.0], 'AbsTol', 1e-14);
verifyEqual(testCase, cfg.physics.Gc, 0.01, 'AbsTol', 1e-14);
end

function testT2UsesTheLockedMaterialState(testCase)
cfg = build_toy_road_case_config("T2_material_state", lockDir());
verifyEqual(testCase, cfg.physics.Gc, 0.008, 'AbsTol', 1e-14);
verifyEqual(testCase, cfg.Pi_ratio, 0.8, 'AbsTol', 1e-14);
end

function testUnknownCaseIdIsRejected(testCase)
verifyError(testCase, ...
    @() build_toy_road_case_config("unknown", lockDir()), ...
    "toyRoad:InvalidInputLock");
end

function testASecondChangedAxisIsRejected(testCase)
tempDir = tempname;
mkdir(tempDir);
cleanup = onCleanup(@() rmdir(tempDir, 's'));
copyRequiredLocks(lockDir(), tempDir);

caseLockPath = fullfile(tempDir, 'T1_INPUT_LOCK.json');
caseLock = jsondecode(fileread(caseLockPath));
caseLock.changed_parent_fields = {'initial_defect', 'material_state'};
writeJson(caseLockPath, caseLock);

verifyError(testCase, ...
    @() build_toy_road_case_config("T1_initial_defect", tempDir), ...
    "toyRoad:InvalidInputLock");
end

function testMismatchedParentHashIsRejected(testCase)
tempDir = tempname;
mkdir(tempDir);
cleanup = onCleanup(@() rmdir(tempDir, 's'));
copyRequiredLocks(lockDir(), tempDir);

caseLockPath = fullfile(tempDir, 'T1_INPUT_LOCK.json');
caseLock = jsondecode(fileread(caseLockPath));
caseLock.parent_lock_sha256 = repmat('0', 1, 64);
writeJson(caseLockPath, caseLock);

verifyError(testCase, ...
    @() build_toy_road_case_config("T1_initial_defect", tempDir), ...
    "toyRoad:InvalidInputLock");
end

function testInvalidCyclesAreRejected(testCase)
cfg = build_toy_road_case_config("T3_loading_history", lockDir());
verifyError(testCase, @() cfg.umax_for_cycle(0), "toyRoad:InvalidCycle");
verifyError(testCase, @() cfg.umax_for_cycle(1.5), "toyRoad:InvalidCycle");
verifyError(testCase, @() cfg.umax_for_cycle(151), "toyRoad:InvalidCycle");
end

function copyRequiredLocks(sourceDir, targetDir)
copyfile(fullfile(sourceDir, 'PARENT_LOCK.json'), targetDir);
copyfile(fullfile(sourceDir, 'FAMILY_INPUT_LOCK.json'), targetDir);
copyfile(fullfile(sourceDir, 'T1_INPUT_LOCK.json'), targetDir);
end

function writeJson(path, value)
fileId = fopen(path, 'w');
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, jsonencode(value), 'char');
end

function value = lockDir()
value = fileparts(fileparts(mfilename('fullpath')));
end
