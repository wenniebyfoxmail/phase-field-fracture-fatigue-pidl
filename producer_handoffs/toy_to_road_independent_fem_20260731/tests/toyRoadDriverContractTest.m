function tests = toyRoadDriverContractTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
addpath(handoffDir());
testCase.TestData.handoffDir = handoffDir();
end

function testDriverRequiresEveryEnvironmentVariable(testCase)
names = {'TOY_ROAD_CASE_ID', 'TOY_ROAD_OUTPUT_ROOT', ...
    'TOY_ROAD_SOURCE_COMMIT', 'TOY_ROAD_LOCK_SHA256'};
oldValues = cellfun(@getenv, names, 'UniformOutput', false);
cleanup = onCleanup(@() restoreEnvironment(names, oldValues));

for missingIndex = 1:numel(names)
    setenv(names{1}, 'T2_material_state');
    setenv(names{2}, tempname);
    setenv(names{3}, '0123456789abcdef');
    setenv(names{4}, repmat('a', 1, 64));
    setenv(names{missingIndex}, '');
    verifyError(testCase, @() main_toy_to_road_case(), ...
        'toyRoad:MissingEnvironment');
end
end

function testDriverRefusesAnyExistingOutputRoot(testCase)
names = {'TOY_ROAD_CASE_ID', 'TOY_ROAD_OUTPUT_ROOT', ...
    'TOY_ROAD_SOURCE_COMMIT', 'TOY_ROAD_LOCK_SHA256'};
oldValues = cellfun(@getenv, names, 'UniformOutput', false);
cleanup = onCleanup(@() restoreEnvironment(names, oldValues));
outputRoot = tempname;
mkdir(outputRoot);
rootCleanup = onCleanup(@() rmdir(outputRoot, 's'));

setenv(names{1}, 'T2_material_state');
setenv(names{2}, outputRoot);
setenv(names{3}, '0123456789abcdef');
setenv(names{4}, repmat('a', 1, 64));
verifyError(testCase, @() main_toy_to_road_case(), 'toyRoad:OutputExists');
end

function testJsonWriterIsDeterministicAndNoClobber(testCase)
outputDir = tempname;
mkdir(outputDir);
cleanup = onCleanup(@() rmdir(outputDir, 's'));
firstPath = fullfile(outputDir, 'first.json');
secondPath = fullfile(outputDir, 'second.json');

first = struct('zeta', 3, 'alpha', struct('y', 2, 'x', 1));
second = struct('alpha', struct('x', 1, 'y', 2), 'zeta', 3);
lastwarn('');
write_toy_road_json(firstPath, first);
write_toy_road_json(secondPath, second);
[warningMessage, ~] = lastwarn;

verifyEqual(testCase, readBytes(firstPath), readBytes(secondPath));
verifyEmpty(testCase, warningMessage);
verifyEqual(testCase, jsondecode(fileread(firstPath)).alpha.x, 1);
verifyError(testCase, @() write_toy_road_json(firstPath, first), ...
    'toyRoad:JsonOutputExists');
verifyEmpty(testCase, dir(fullfile(outputDir, '*.tmp.json')));
verifyEmpty(testCase, dir(fullfile(outputDir, '*.publish.lock')));
end

function testJsonWriterPreLinkFailureIsFailClosedAndPropagates(testCase)
outputDir = tempname;
mkdir(outputDir);
cleanup = onCleanup(@() rmdir(outputDir, 's'));
outputPath = fullfile(outputDir, 'pre_link.json');
operations = struct('before_link', @throwPreLinkFailure);

verifyError(testCase, @() write_toy_road_json( ...
    outputPath, struct('complete', true), operations), ...
    'toyRoad:InjectedPreLinkFailure');
verifyFalse(testCase, isfile(outputPath));
verifyEmpty(testCase, dir(fullfile(outputDir, '*.tmp.json')));
verifyEmpty(testCase, dir(fullfile(outputDir, '*.publish.lock')));
end

function testJsonWriterPostLinkCleanupFailureReturnsCommittedSuccess(testCase)
outputDir = tempname;
mkdir(outputDir);
cleanup = onCleanup(@() rmdir(outputDir, 's'));
outputPath = fullfile(outputDir, 'RUN_RESULT.json');
payload = struct('case_id', 'T2_material_state', 'complete', true, ...
    'status', 'complete', 'terminal_cycle', 4, ...
    'terminal_reason', 'confirmed', ...
    'terminal_state_file', 'states/cycle_0004.mat');
operations = struct('delete_temp', @throwPostLinkCleanupFailure);

publication = write_toy_road_json(outputPath, payload, operations);

verifyTrue(testCase, publication.committed);
verifyTrue(testCase, publication.cleanup_pending);
verifyEqual(testCase, publication.cleanup_error_identifier, ...
    "toyRoad:InjectedPostLinkCleanupFailure");
verifyTrue(testCase, isfile(outputPath));
verifyEqual(testCase, jsondecode(fileread(outputPath)), payload);
verifyNotEmpty(testCase, dir(fullfile(outputDir, '*.tmp.json')));
verifyEmpty(testCase, dir(fullfile(outputDir, '*.publish.lock')));
end

function testActualDriverAndSolverSatisfyLockedContract(testCase)
[mainText, solverText] = productionTexts();
verifyEmpty(testCase, contractViolations(mainText, solverText));
end

function testDriverPreservesParentImportedGeometryForMaterialConstruction(testCase)
[mainText, ~] = productionTexts();

verifyNotEmpty(testCase, regexp(mainText, ...
    '\[MESH, GEOM\] = specimen\.external\.gmsh_import\([^;]+;', 'once'));
verifyEmpty(testCase, regexp(mainText, '\<GEOM\.(L|B)\s*=', 'once'));
verifyNotEmpty(testCase, regexp(mainText, ...
    'phase_field\.init\.material_characteristic\(\s*\.\.\.\s*GEOM\.L, dissFct,', ...
    'once'));

parentImportedL = 0.0;
caseGc = [0.01 0.008 0.01];
penaltyRecov = (caseGc / 0.01) .* ...
    (9 * ((parentImportedL / 0.01) - 2)) / (64 * 1e-3);
verifyEqual(testCase, penaltyRecov, [-281.25 -225 -281.25], ...
    'AbsTol', 1e-14);
end

function testDriverUsesRecoveryHelperWithProductionDefaultsOnly(testCase)
mainText = readTextOrEmpty(fullfile(handoffDir(), 'main_toy_to_road_case.m'));
recoveryText = readTextOrEmpty(fullfile( ...
    handoffDir(), 'recover_toy_road_initial_state.m'));

verifyTrue(testCase, contains(mainText, ...
    'recover_toy_road_initial_state(recoveryInput);'));
verifyTrue(testCase, contains(recoveryText, ...
    "'system_factory', @phase_field.System"));
verifyTrue(testCase, contains(recoveryText, ...
    "'newton_raphson', @phase_field.fem.solver.newton_raphson"));
verifyFalse(testCase, contains(mainText, "'operators',"));
end

function testRunResultIsSoleCompletionMarkerAndLauncherDoesNotSwallow(testCase)
[mainText, solverText] = productionTexts();

verifyEqual(testCase, countToken(mainText + newline + solverText, ...
    "'complete', true"), 1);
verifyEmpty(testCase, regexp(mainText, 'catch\s*(\r?\n)\s*end', 'once'));
verifyTrue(testCase, contains(mainText, "'toyRoad:FailurePublicationFailed'"));
verifyTrue(testCase, contains(mainText, 'addCause(combined, exception)'));
verifyTrue(testCase, contains(mainText, 'addCause(combined, publicationException)'));
end

function testContractRejectsMissingEnvironmentRequirement(testCase)
[mainText, solverText] = productionTexts();
badMain = replace(mainText, 'TOY_ROAD_LOCK_SHA256', 'REMOVED_LOCK_VARIABLE');
verifyNotEmpty(testCase, contractViolations(badMain, solverText));
end

function testContractRejectsSavedStateLanguage(testCase)
[mainText, solverText] = productionTexts();
badSolver = solverText + newline + "% resume from checkpoint";
verifyNotEmpty(testCase, contractViolations(mainText, badSolver));
end

function testContractRejectsWrongToleranceOrCadence(testCase)
[mainText, solverText] = productionTexts();
badTolerance = replace(mainText, "'tol_displ', 1e-6", ...
    "'tol_displ', 1e-5");
badCadence = replace(solverText, ...
    'loadFactors = [0.25 0.5 0.75 1.0 0.0];', ...
    'loadFactors = [0.5 1.0 0.0];');
verifyNotEmpty(testCase, contractViolations(badTolerance, solverText));
verifyNotEmpty(testCase, contractViolations(mainText, badCadence));
end

function testContractRejectsRepeatedAmplitudeEvaluation(testCase)
[mainText, solverText] = productionTexts();
badSolver = solverText + newline + ...
    "cycleUmaxAgain = context.cfg.umax_for_cycle(cycle);";
verifyNotEmpty(testCase, contractViolations(mainText, badSolver));
end

function testContractRejectsPeakExportBeforeConvergence(testCase)
[mainText, solverText] = productionTexts();
badSolver = "exportedState = operators.export_peak_state(exportInput, " + ...
    "context.output_root);" + newline + solverText;
verifyNotEmpty(testCase, contractViolations(mainText, badSolver));
end

function testContractRejectsPeakExportAfterUnload(testCase)
[mainText, solverText] = productionTexts();
badSolver = replace(solverText, 'if iStep == peakOrdinal', ...
    'if iStep == numel(loadFactors)');
verifyNotEmpty(testCase, contractViolations(mainText, badSolver));
end

function testContractRejectsFirstHitStopping(testCase)
[mainText, solverText] = productionTexts();
badSolver = replace(solverText, ...
    'stopAfterCycle = ~isnan(eventState.confirmed) || cycle == context.cfg.censor_cap;', ...
    'stopAfterCycle = ~isnan(eventState.first_hit) || cycle == context.cfg.censor_cap;');
verifyNotEmpty(testCase, contractViolations(mainText, badSolver));
end

function testContractRejectsExporterMutationOfPhysicalState(testCase)
[mainText, solverText] = productionTexts();
badSolver = solverText + newline + 'p_field = exportedState.d_node;';
verifyNotEmpty(testCase, contractViolations(mainText, badSolver));
end

function testContractRejectsStaleRecoveryFieldAtSystemRebuild(testCase)
[mainText, solverText] = productionTexts();
badMain = replace(mainText, ...
    'input.stress_state, pField, input.diss_fct);', ...
    'input.stress_state, input.p_field, input.diss_fct);');
verifyNotEmpty(testCase, contractViolations(badMain, solverText));
end

function violations = contractViolations(mainText, solverText)
violations = strings(0, 1);
requiredEnvironment = ["TOY_ROAD_CASE_ID", "TOY_ROAD_OUTPUT_ROOT", ...
    "TOY_ROAD_SOURCE_COMMIT", "TOY_ROAD_LOCK_SHA256"];
for name = requiredEnvironment
    if ~contains(mainText, name)
        violations(end + 1) = "missing_environment_" + name; %#ok<AGROW>
    end
end

combined = lower(mainText + newline + solverText);
if ~isempty(regexp(combined, '\<(checkpoint|resume)\>', 'once'))
    violations(end + 1) = "saved_state_language";
end

requiredMain = [ ...
    "'E', 1.0", "'ni', 0.3", "'Gc', cfg.physics.Gc", ...
    "'ell', 0.01", "'res_stiff', 0.0", "'alpha_T', 0.5", "'p', 2.0", ...
    "phase_field.StressState.PlaneStrain", ...
    "'tol_displ', 1e-6", "'tol_p_field', 4e-4", ...
    "phase_field.fem.solver.stag.params('tol', 4e-4", ...
    "'line_search', false", ...
    "phase_field.fem.solver.cycl_jump.params('cycl_jump', false)", ...
    "irrev = 'HISTORY'", "splitType = 'AMOR'", "dissFct = 'AT1'", ...
    "recover_toy_road_initial_state(recoveryInput);", ...
    "'system_factory', @phase_field.System", ...
    "'newton_raphson', @phase_field.fem.solver.newton_raphson", ...
    "input.stress_state, pField, input.diss_fct);"];
for token = requiredMain
    if ~contains(mainText, token)
        violations(end + 1) = "missing_main_token_" + token; %#ok<AGROW>
    end
end

if countToken(mainText, 'operators.system_factory(') ~= 2
    violations(end + 1) = "system_not_rebuilt";
end
recoveryAt = firstPosition(mainText, 'operators.newton_raphson(');
clipAt = firstPosition(mainText, 'pField = min(max(recoveredField, 0.0), 1.0);');
systemAt = lastPosition(mainText, 'operators.system_factory(');
resetAt = firstPosition(mainText, 'historyVars(:, :, 2:3) = 0.0;');
fatigueAt = firstPosition(mainText, 'historyVars(:, :, 4) = 1.0;');
if ~(recoveryAt < clipAt && clipAt < systemAt && systemAt < resetAt && resetAt < fatigueAt)
    violations(end + 1) = "recovery_clip_rebuild_reset_order";
end
if ~contains(mainText, "if strcmp(cfg.case_id, 'T1_initial_defect')") || ...
        countToken(mainText, 'apply_t1_mesh_transfer(') ~= 1
    violations(end + 1) = "t1_mesh_transfer_scope";
end

requiredSolver = [ ...
    "loadFactors = [0.25 0.5 0.75 1.0 0.0];", ...
    "peakOrdinal = 4;", ...
    "rawStep = 5 * (cycle - 1) + peakOrdinal;", ...
    "for iStep = 1:numel(loadFactors)", ...
    "if iStep == peakOrdinal", ...
    "exportedState = operators.export_peak_state(exportInput, context.output_root);", ...
    "eventState = operators.advance_event(eventState,", ...
    "relativeStateFile = exportedState.cycle_index.file;", ...
    "stopAfterCycle = ~isnan(eventState.confirmed) || cycle == context.cfg.censor_cap;", ...
    "'pre_iter_update', @phase_field.fem.solver.step.pre_iter_update", ...
    "'stag_vars', @phase_field.fem.solver.stag.vars", ...
    "'newton_raphson', @phase_field.fem.solver.newton_raphson", ...
    "'stag_post_iter_update', @phase_field.fem.solver.stag.post_iter_update", ...
    "'export_peak_state', @export_toy_road_peak_state", ...
    "'advance_event', @advance_toy_road_event", ...
    "'write_json', @write_toy_road_json"];
for token = requiredSolver
    if ~contains(solverText, token)
        violations(end + 1) = "missing_solver_token_" + token; %#ok<AGROW>
    end
end
if countToken(solverText, 'context.cfg.umax_for_cycle(cycle)') ~= 1
    violations(end + 1) = "umax_call_count";
end
convergenceAt = firstPosition(solverText, 'if ~stagConverged');
exportAt = firstPosition(solverText, ...
    'exportedState = operators.export_peak_state(exportInput, context.output_root);');
eventAt = firstPosition(solverText, 'eventState = operators.advance_event(eventState,');
if ~(convergenceAt < exportAt && exportAt < eventAt)
    violations(end + 1) = "peak_export_order";
end
if ~isempty(regexp(solverText, ...
        '(displ|p_field|p_field_old|history_vars_old)\s*=\s*exportedState', 'once'))
    violations(end + 1) = "exporter_mutates_physics";
end
if contains(solverText, "sprintf('states/cycle_") || ...
        contains(solverText, "sprintf(""states/cycle_")
    violations(end + 1) = "independent_state_filename";
end
end

function [mainText, solverText] = productionTexts()
mainText = readTextOrEmpty(fullfile(handoffDir(), 'main_toy_to_road_case.m'));
mainText = mainText + newline + readTextOrEmpty(fullfile( ...
    handoffDir(), 'recover_toy_road_initial_state.m'));
solverText = readTextOrEmpty(fullfile(handoffDir(), 'solve_toy_to_road_case.m'));
end

function value = readTextOrEmpty(path)
if isfile(path)
    value = string(fileread(path));
else
    value = "";
end
end

function count = countToken(text, token)
count = numel(strfind(char(text), char(token)));
end

function position = firstPosition(text, token)
positions = strfind(char(text), char(token));
if isempty(positions)
    position = inf;
else
    position = positions(1);
end
end

function position = lastPosition(text, token)
positions = strfind(char(text), char(token));
if isempty(positions)
    position = -inf;
else
    position = positions(end);
end
end

function restoreEnvironment(names, values)
for index = 1:numel(names)
    setenv(names{index}, values{index});
end
end

function value = readBytes(path)
fileId = fopen(path, 'rb');
cleanup = onCleanup(@() fclose(fileId));
value = fread(fileId, Inf, '*uint8');
end

function value = handoffDir()
value = fileparts(fileparts(mfilename('fullpath')));
end

function throwPreLinkFailure(varargin)
error('toyRoad:InjectedPreLinkFailure', 'Injected before hard-link commit.');
end

function throwPostLinkCleanupFailure(varargin)
error('toyRoad:InjectedPostLinkCleanupFailure', ...
    'Injected after hard-link commit.');
end
