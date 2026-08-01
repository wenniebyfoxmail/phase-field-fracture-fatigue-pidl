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
verifyEqual(testCase, spy.PreIterContractChecks, 20);
verifyEqual(testCase, spy.StagVarsContractChecks, 20);
verifyEqual(testCase, spy.DisplacementNewtonContractChecks, 20);
verifyEqual(testCase, spy.PhaseNewtonContractChecks, 20);
verifyEqual(testCase, spy.StaggeredPostContractChecks, 20);
verifyEqual(testCase, spy.EquilibriumAssemblyContractChecks, 44);
verifyEqual(testCase, spy.PhaseAssemblyContractChecks, 40);
verifyEqual(testCase, spy.HistoryUpdateContractChecks, 20);
verifyEqual(testCase, spy.StateFlowContractChecks, 20);
verifyEqual(testCase, size(spy.ExportInputs{1}.displ), [12 1]);
verifyEqual(testCase, size(spy.ExportInputs{1}.p_field), [6 1]);
verifyEqual(testCase, size(spy.ExportInputs{1}.history_vars), [2 4 4]);
verifyEqual(testCase, size(spy.ExportInputs{1}.psi_raw_gp), [2 4]);
verifyEqual(testCase, spy.ExportInputs{1}.displ(12), ...
    context.displ(12) + 0.12, 'AbsTol', 1e-14);
verifyEqual(testCase, context.sys.DOFS.non_hom_dirichlet_bc, [2; 12]);
verifyEqual(testCase, context.sys.NODE_BOUNDARIES.disp_X, 2);
verifyEqual(testCase, context.sys.NODE_BOUNDARIES.disp_Y, 6);
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

function testCommittedRunResultSurvivesInjectedPostLinkCleanupFailure(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
spy = ToyRoadSolverDouble();
spy.InjectRunCleanupFailure = true;

result = solve_toy_to_road_case(syntheticContext(outputRoot, spy));

verifyTrue(testCase, result.complete);
verifyTrue(testCase, spy.LastRunPublication.committed);
verifyTrue(testCase, spy.LastRunPublication.cleanup_pending);
runResult = validate_toy_road_run_result( ...
    fullfile(outputRoot, 'RUN_RESULT.json'), 'T2_material_state');
verifyTrue(testCase, runResult.complete);
verifyEqual(testCase, sum(spy.WriteNames == "RUN_RESULT.json"), 1);
verifyFalse(testCase, any(spy.WriteNames == "FAILED_RUN_RESULT.json"));
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
runResult = validate_toy_road_run_result( ...
    fullfile(outputRoot, 'RUN_RESULT.json'), 'T2_material_state');
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

function testMalformedExistingRunResultIsNotAcceptedAsIdempotent(testCase)
[outputRoot, cleanup] = freshOutputRoot(); %#ok<ASGLU>
spy = ToyRoadSolverDouble();
spy.FailNewton = true;
write_toy_road_json(fullfile(outputRoot, 'RUN_RESULT.json'), ...
    struct('complete', true));

verifyError(testCase, @() solve_toy_to_road_case( ...
    syntheticContext(outputRoot, spy)), 'toyRoad:FailurePublicationFailed');
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
dofs = struct('active_dof', [1; 3; 5; 7; 9; 11], ...
    'active_dof_pf', [2; 4; 6], 'num_dof', 12, ...
    'non_hom_dirichlet_bc', [2; 12]);
nodeBoundaries = struct('disp_X', 2, 'disp_Y', 6, ...
    'contract_sentinel', 6201);
iRow = (1:12)';
jCol = (1:12)';
iRowPf = (1:6)';
jColPf = (1:6)';
initialStiffness = sparse(iRow, jCol, 3 + (1:12)' / 100, 12, 12);
matChar = struct('contract_sentinel', 6401);
cc = diag([6501 6502 6503]);
sys = struct( ...
    'MESH', mesh, ...
    'DOFS', dofs, ...
    'NODE_BOUNDARIES', nodeBoundaries, ...
    'GEOM', struct('t', 1.234), ...
    'QUADRATURE', quadrature, ...
    'MAT_CHAR', matChar, ...
    'CC', cc, ...
    'stress_state', struct('as_number', 6601), ...
    'STIFFNESS_MATRIX', struct('i_row', iRow, 'j_col', jCol, ...
        'i_row_pf', iRowPf, 'j_col_pf', jColPf, 'KK', initialStiffness));
history = zeros(2, 4, 4);
history(:, :, 4) = 1.0;
initialDispl = (1:12)' / 10000;
initialPField = zeros(6, 1);
initialPFieldOld = zeros(6, 1);
solPar = struct('tol_displ', 1e-6, 'tol_p_field', 4e-4, ...
    'max_iter_displ', 2, 'max_iter_pf', 2, 'contract_tag', 6701);
solStagPar = struct('tol', 4e-4, 'max_iter', 1, 'contract_tag', 6801);
solStepTemplate = struct('line_search', false, 'contract_tag', 818);
cfg = struct( ...
    'case_id', 'T2_material_state', ...
    'censor_cap', 150, ...
    'n_step', 5, ...
    'umax_for_cycle', @(cycle) spy.umaxForCycle(cycle), ...
    'event_contract', struct('confirmation_cycles', 3, ...
        'event_rule', 'connected_right_boundary_v1'));
assemblyPf = @(varargin) spy.assemblyPf(varargin{:});
assemblyEquilibrium = @(varargin) spy.assemblyEquilibrium(varargin{:});
operators = struct( ...
    'pre_iter_update', @(varargin) spy.preIterUpdate(varargin{:}), ...
    'stag_vars', @(varargin) spy.staggeredVars(varargin{:}), ...
    'newton_raphson', @(varargin) spy.newtonRaphson(varargin{:}), ...
    'stag_post_iter_update', @(varargin) spy.postIterUpdate(varargin{:}), ...
    'export_peak_state', @(varargin) spy.exportPeakState(varargin{:}), ...
    'advance_event', @(varargin) spy.advanceEvent(varargin{:}), ...
    'write_json', @(varargin) spy.writeJson(varargin{:}));
contract = struct( ...
    'mesh', mesh, 'dofs', dofs, 'node_boundaries', nodeBoundaries, ...
    'thickness', 1.234, ...
    'quadrature', quadrature, 'mat_char', matChar, 'cc', cc, ...
    'stress_state_number', 6601, ...
    'active_dof', dofs.active_dof, 'active_dof_pf', dofs.active_dof_pf, ...
    'i_row', iRow, 'j_col', jCol, 'i_row_pf', iRowPf, 'j_col_pf', jColPf, ...
    'initial_stiffness', initialStiffness, ...
    'initial_displ', initialDispl, ...
    'initial_p_field', initialPField, ...
    'initial_p_field_old', initialPFieldOld, ...
    'initial_history', history, ...
    'raw_driver', reshape((1:8) / 10, 2, 4), ...
    'sol_par', solPar, 'sol_stag_par', solStagPar, ...
    'assembly_pf_fh', assemblyPf, ...
    'assembly_equilibrium_fh', assemblyEquilibrium);
spy.configure(contract);
context = struct( ...
    'cfg', cfg, 'output_root', outputRoot, 'sys', sys, ...
    'sol_par', solPar, 'sol_stag_par', solStagPar, ...
    'sol_step_template', solStepTemplate, ...
    'assembly_pf_fh', assemblyPf, ...
    'assembly_equilibrium_fh', assemblyEquilibrium, ...
    'displ', initialDispl, 'p_field', initialPField, ...
    'p_field_old', initialPFieldOld, 'history_vars_old', history, ...
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
