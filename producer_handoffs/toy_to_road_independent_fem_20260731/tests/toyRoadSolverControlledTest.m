function tests = toyRoadSolverControlledTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
addpath(handoffDir());
addpath(fileparts(mfilename('fullpath')));
testCase.addTeardown(@() rmpath(handoffDir()));
testCase.addTeardown(@() rmpath(fileparts(mfilename('fullpath'))));
end

function testControlledOperatorsExerciseRealFiveStepSolverAndNativeExporter(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
spy = ToyRoadSolverDouble();
context = syntheticContext(outputRoot, spy);

result = solve_toy_to_road_case(context);

verifyEqual(testCase, result.terminal_cycle, 4);
verifyEqual(testCase, string(result.terminal_reason), "confirmed");
verifyEqual(testCase, spy.UmaxCycles, 1:4);
verifyEqual(testCase, spy.StepOrdinals, repmat(1:5, 1, 4));
verifyEqual(testCase, spy.LoadFactorsObserved, ...
    repmat([0.25 0.5 0.75 1.0 0.0], 1, 4), 'AbsTol', 1e-14);
verifyEqual(testCase, spy.ExportStepCounts, [4 9 14 19]);
verifyEqual(testCase, spy.EventCycles, 1:4);
verifyEqual(testCase, unique(spy.NewtonArgumentCounts), 17);
verifyEqual(testCase, unique(spy.PostArgumentCounts), 11);
verifyEqual(testCase, size(spy.ExportInputs{1}.displ), [12 1]);
verifyEqual(testCase, size(spy.ExportInputs{1}.p_field), [6 1]);
verifyEqual(testCase, size(spy.ExportInputs{1}.history_vars), [2 4 4]);
verifyEqual(testCase, size(spy.ExportInputs{1}.psi_raw_gp), [2 4]);
for cycle = 1:4
    exportAt = find(spy.Trace == "export_" + cycle, 1);
    eventAt = find(spy.Trace == "event_" + cycle, 1);
    unloadAt = find(spy.Trace == "step_5" & (1:numel(spy.Trace)) > exportAt, 1);
    verifyLessThan(testCase, exportAt, eventAt);
    verifyLessThan(testCase, eventAt, unloadAt);
end

state = load(fullfile(outputRoot, 'states', 'cycle_0001.mat'));
verifySize(testCase, state.d_node, [6 1]);
verifyEqual(testCase, string(state.mesh_sha256), ...
    toy_road_mesh_sha256(context.sys.MESH.node, context.sys.MESH.elem));
event = jsondecode(fileread(fullfile(outputRoot, 'EVENT_METADATA.json')));
verifyFalse(testCase, isfield(event, 'complete'));
verifyEqual(testCase, event.first_hit, 1);
verifyEqual(testCase, event.confirmed, 4);
verifyEqual(testCase, spy.WriteNames(end), "RUN_RESULT.json");
end

function testControlledOperatorsRightCensorAtCycle150(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
spy = ToyRoadSolverDouble();
spy.DamageMode = 'no_hit';
spy.UseNativeExporter = false;

result = solve_toy_to_road_case(syntheticContext(outputRoot, spy));

verifyEqual(testCase, result.terminal_cycle, 150);
verifyEqual(testCase, string(result.terminal_reason), "right_censored");
verifyEqual(testCase, spy.UmaxCycles, 1:150);
verifyEqual(testCase, numel(spy.StepOrdinals), 750);
verifyEqual(testCase, spy.StepOrdinals(end - 4:end), 1:5);
end

function testCaughtSolverFailurePublishesExplicitFailedRunLast(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
spy = ToyRoadSolverDouble();
spy.FailNewton = true;

verifyError(testCase, @() solve_toy_to_road_case( ...
    syntheticContext(outputRoot, spy)), 'toyRoad:InjectedSolverFailure');

event = jsondecode(fileread(fullfile(outputRoot, 'EVENT_METADATA.json')));
runResult = jsondecode(fileread(fullfile(outputRoot, 'RUN_RESULT.json')));
verifyEqual(testCase, string(event.status), "failed");
verifyFalse(testCase, isfield(event, 'complete'));
verifyFalse(testCase, runResult.complete);
verifyEqual(testCase, string(runResult.status), "failed");
verifyEqual(testCase, spy.WriteNames(end), "RUN_RESULT.json");
end

function testFailurePublicationErrorIsCombinedAndNotSwallowed(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
spy = ToyRoadSolverDouble();
spy.FailNewton = true;
spy.FailAllWrites = true;

verifyError(testCase, @() solve_toy_to_road_case( ...
    syntheticContext(outputRoot, spy)), 'toyRoad:FailurePublicationFailed');
verifyFalse(testCase, isfile(fullfile(outputRoot, 'RUN_RESULT.json')));
end

function testRunResultFailureCannotLeaveContradictoryCompleteMarker(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
spy = ToyRoadSolverDouble();
spy.FailRunWritesRemaining = 1;

verifyError(testCase, @() solve_toy_to_road_case( ...
    syntheticContext(outputRoot, spy)), 'toyRoad:InjectedPublicationFailure');

event = jsondecode(fileread(fullfile(outputRoot, 'EVENT_METADATA.json')));
runResult = jsondecode(fileread(fullfile(outputRoot, 'RUN_RESULT.json')));
verifyFalse(testCase, isfield(event, 'complete'));
verifyFalse(testCase, runResult.complete);
verifyEqual(testCase, string(runResult.status), "failed");
end

function context = syntheticContext(outputRoot, spy)
coords = [0 -1; 0.5 -1; 0.5 0; 0 0; 0.5 1; 0 1];
connectivity = [1 2 3 4; 4 3 5 6];
gauss = 1 / sqrt(3) * [-1 -1; 1 -1; 1 1; -1 1];
mesh = struct('node', coords, 'elem', connectivity, 'nel', 4, ...
    'num_node', 6, 'num_elem', 2);
quadrature = struct('gauss_pts', gauss, 'gauss_W', ones(4, 1), ...
    'num_gauss_pts', 4);
sys = struct( ...
    'MESH', mesh, ...
    'DOFS', struct('active_dof', (1:12)', 'active_dof_pf', (1:6)'), ...
    'GEOM', struct('t', 1.0), ...
    'QUADRATURE', quadrature, ...
    'MAT_CHAR', struct(), ...
    'CC', zeros(3), ...
    'stress_state', struct('as_number', 1), ...
    'STIFFNESS_MATRIX', struct('i_row', 1, 'j_col', 1, ...
        'i_row_pf', 1, 'j_col_pf', 1, 'KK', speye(12)));
history = zeros(2, 4, 4);
history(:, :, 4) = 1.0;
cfg = struct( ...
    'case_id', 'T2_material_state', ...
    'censor_cap', 150, ...
    'n_step', 5, ...
    'umax_for_cycle', @(cycle) spy.umaxForCycle(cycle), ...
    'event_contract', struct('confirmation_cycles', 3, ...
        'event_rule', 'connected_right_boundary_v1'));
operators = struct( ...
    'pre_iter_update', @(varargin) spy.preIterUpdate(varargin{:}), ...
    'stag_vars', @(varargin) spy.staggeredVars(varargin{:}), ...
    'newton_raphson', @(varargin) spy.newtonRaphson(varargin{:}), ...
    'stag_post_iter_update', @(varargin) spy.postIterUpdate(varargin{:}), ...
    'export_peak_state', @(varargin) spy.exportPeakState(varargin{:}), ...
    'advance_event', @(varargin) spy.advanceEvent(varargin{:}), ...
    'write_json', @(varargin) spy.writeJson(varargin{:}));
context = struct( ...
    'cfg', cfg, 'output_root', outputRoot, 'sys', sys, ...
    'sol_par', struct('tol_displ', 1e-6, 'tol_p_field', 4e-4, ...
        'max_iter_displ', 2, 'max_iter_pf', 2), ...
    'sol_stag_par', struct('tol', 4e-4, 'max_iter', 1), ...
    'sol_step_template', struct('line_search', false), ...
    'assembly_pf_fh', @(varargin) spy.assemblyPf(varargin{:}), ...
    'assembly_equilibrium_fh', @(varargin) spy.assemblyEquilibrium(varargin{:}), ...
    'displ', zeros(12, 1), 'p_field', zeros(6, 1), ...
    'p_field_old', zeros(6, 1), 'history_vars_old', history, ...
    'top_node_ids', [5 6], 'bottom_node_ids', [1 2], ...
    'operators', operators);
end

function [outputRoot, cleanup] = freshOutputRoot()
outputRoot = tempname;
mkdir(outputRoot);
cleanup = onCleanup(@() rmdir(outputRoot, 's'));
end

function value = handoffDir()
value = fileparts(fileparts(mfilename('fullpath')));
end
