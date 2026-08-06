function tests = toyRoadSolverControlledTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
addpath(handoffDir());
addpath(fileparts(mfilename('fullpath')));
testCase.addTeardown(@() rmpath(handoffDir()));
testCase.addTeardown(@() rmpath(fileparts(mfilename('fullpath'))));
end

function setup(testCase)
root = tempname;
mkdir(root);
testCase.TestData.root = root;
testCase.addTeardown(@() removeRoot(root));
end

function testThreeStaggersFollowExactGateCommitUnloadOrdering(testCase)
double = ToyRoadP0SolverDouble();
context = double.makeContext(testCase.TestData.root, 'P0_parent');

result = solve_toy_road_family_case(context);

expected = [ ...
    "c5_trace_begin", ...
    "c5_stagger_1_update", ...
    "c5_stagger_1_reassembly_append", ...
    "c5_stagger_2_update", ...
    "c5_stagger_2_reassembly_append", ...
    "c5_stagger_3_update_converged", ...
    "c5_stagger_3_reassembly_append", ...
    "c5_gate_receipt_passed", ...
    "c5_s4_history_committed", ...
    "c5_s5_unload"];
verifyEqual(testCase, double.Trace, expected);
verifyEqual(testCase, result.trace_row_count, 3);
verifyEqual(testCase, result.same_process_reassembly_count, 3);
verifyEqual(testCase, result.c5_stagger_ordinals, 1:3);
verifyEqual(testCase, double.CompletedC5Staggers, 1:3);
verifyEqual(testCase, double.EquilibriumReassemblyCount, 3);
verifyEqual(testCase, double.PhaseReassemblyCount, 3);
verifyEqual(testCase, sum(all(double.HistoryCommitCycleStep == [5 4], 2)), 1);
verifyTrue(testCase, isfile(fullfile(testCase.TestData.root, ...
    'substeps', 'cycle_0005.mat')));
end

function testAllFiveRolesTakeTheIdenticalCaseLocalGatePath(testCase)
roles = {'P0_parent','P0R_parent_repeat','T1_initial_defect', ...
    'T2_material_state','T3_loading_history'};
expected = strings(0,1);
for index = 1:numel(roles)
    root = fullfile(testCase.TestData.root, sprintf('role_%d', index));
    mkdir(root);
    double = ToyRoadP0SolverDouble();
    double.C5StaggerCount = 2;
    result = solve_toy_road_family_case(double.makeContext(root, roles{index}));
    if index == 1
        expected = double.Trace;
    else
        verifyEqual(testCase, double.Trace, expected);
    end
    verifyEqual(testCase, result.case_id, roles{index});
    receipt = jsondecode(fileread(fullfile(root, 'qualification', ...
        'C5_NUMERICAL_GATE_RECEIPT.json')));
    verifyEqual(testCase, receipt.case_id, roles{index});
    verifyEqual(testCase, receipt.trace_row_count, 2);
    verifyEqual(testCase, receipt.reassembly_count, 2);
end
end

function testConvergenceSignalControlsVariableStaggerCounts(testCase)
for count = [1 2 5]
    root = fullfile(testCase.TestData.root, sprintf('count_%d', count));
    mkdir(root);
    double = ToyRoadP0SolverDouble();
    double.C5StaggerCount = count;

    result = solve_toy_road_family_case( ...
        double.makeContext(root, 'T2_material_state'));

    verifyEqual(testCase, result.c5_stagger_ordinals, 1:count);
    verifyEqual(testCase, result.trace_row_count, count);
    verifyEqual(testCase, result.same_process_reassembly_count, count);
    verifyEqual(testCase, double.CompletedC5Staggers, 1:count);
    verifyEqual(testCase, double.EquilibriumReassemblyCount, count);
    verifyEqual(testCase, double.PhaseReassemblyCount, count);
end
end

function testC5ContinuesPastNativeConvergenceUntilDamageFixedPoint(testCase)
double = ToyRoadP0SolverDouble();
double.C5StaggerCount = 5;
double.C5NativeConvergenceAt = 3;

result = solve_toy_road_family_case( ...
    double.makeContext(testCase.TestData.root, 'P0_parent'));

verifyEqual(testCase, double.CompletedC5Staggers, 1:5);
verifyEqual(testCase, result.c5_stagger_ordinals, 1:5);
receipt = jsondecode(fileread(fullfile(testCase.TestData.root, ...
    'qualification', 'C5_NUMERICAL_GATE_RECEIPT.json')));
verifyEqual(testCase, receipt.final_consecutive_stagger_delta, 5e-4, ...
    'AbsTol', 1e-12);
end

function testGateFailurePublishesFailedRunBeforeCommitUnloadOrCycleSix(testCase)
double = ToyRoadP0SolverDouble();
double.C5MetricFailure = 'displacement';
context = double.makeContext(testCase.TestData.root, 'T3_loading_history');
context.cycle_limit = 6;

verifyError(testCase, @() solve_toy_road_family_case(context), ...
    'toyRoadP0:C5GateFailed');

verifyTrue(testCase, double.FailedRunPublished);
failed = jsondecode(fileread(fullfile(testCase.TestData.root, 'RUN_RESULT.json')));
verifyFalse(testCase, failed.complete);
verifyEqual(testCase, failed.error_identifier, 'toyRoadP0:C5GateFailed');
verifyFalse(testCase, any(all(double.HistoryCommitCycleStep == [5 4], 2)));
verifyFalse(testCase, any(double.Trace == "c5_s4_history_committed"));
verifyFalse(testCase, any(double.Trace == "c5_s5_unload"));
verifyFalse(testCase, any(double.CycleStarts == 6));
verifyFalse(testCase, isfile(fullfile(testCase.TestData.root, ...
    'substeps', 'cycle_0005.mat')));
end

function testAppendFailurePublishesFailedRunBeforeCommitUnloadOrCycleSix(testCase)
double = ToyRoadP0SolverDouble();
double.FailReassemblyOrdinal = 2;
context = double.makeContext(testCase.TestData.root, 'T1_initial_defect');
context.cycle_limit = 6;

verifyError(testCase, @() solve_toy_road_family_case(context), ...
    'toyRoadP0:InjectedReassemblyFailure');

verifyTrue(testCase, double.FailedRunPublished);
verifyEqual(testCase, double.PhaseReassemblyCount, 1);
verifyFalse(testCase, any(all(double.HistoryCommitCycleStep == [5 4], 2)));
verifyFalse(testCase, any(double.Trace == "c5_s5_unload"));
verifyFalse(testCase, any(double.CycleStarts == 6));
verifyFalse(testCase, isfile(fullfile(testCase.TestData.root, ...
    'qualification', 'C5_NUMERICAL_GATE_RECEIPT.json')));
end

function testParentReceiptCannotBeInjectedIntoAnyRole(testCase)
roles = {'P0_parent','P0R_parent_repeat','T1_initial_defect', ...
    'T2_material_state','T3_loading_history'};
for index = 1:numel(roles)
    root = fullfile(testCase.TestData.root, sprintf('inject_%d', index));
    mkdir(root);
    double = ToyRoadP0SolverDouble();
    context = double.makeContext(root, roles{index});
    context.parent_c5_receipt = struct('status', 'PASS', 'passed', true);

    verifyError(testCase, @() solve_toy_road_family_case(context), ...
        'toyRoadP0:InvalidSolverContext');
    verifyEmpty(testCase, double.Trace);
    verifyFalse(testCase, isfolder(fullfile(root, 'qualification')));
end
end

function testSolverForcesExactlyFiveSubstepsPerCycle(testCase)
double = ToyRoadP0SolverDouble();
context = double.makeContext(testCase.TestData.root, 'P0R_parent_repeat');
verifyNotEqual(testCase, context.sol_step_template.n_step, 5);

solve_toy_road_family_case(context);

verifyEqual(testCase, double.SubstepStarts, ...
    [repelem((1:5).',5,1) repmat((1:5).',5,1)]);
end

function testRawResidualCanExceedGateThresholdWithoutBeingSubstituted(testCase)
double = ToyRoadP0SolverDouble();
double.C5StaggerCount = 1;
double.C5FinalDelta = 0;
context = double.makeContext(testCase.TestData.root, 'T2_material_state');
original = context.operators.reassemble_phase;
context.operators.reassemble_phase = ...
    @(snapshot,u,d,raw) lowerBoundRawResidual(original, snapshot, u, d, raw);

result = solve_toy_road_family_case(context);

verifyGreaterThan(testCase, result.c5_receipt.final_raw_phase_residual, 1);
verifyLessThanOrEqual(testCase, ...
    result.c5_receipt.final_projected_phase_kkt, 4e-4);
end


function testConfirmedEventStopsAfterThreePostHitCycles(testCase)
double = ToyRoadP0SolverDouble();
double.EventFirstHitCycle = 6;
context = double.makeContext(testCase.TestData.root, 'T1_initial_defect');
context.cycle_limit = 12;

result = solve_toy_road_family_case(context);

verifyEqual(testCase, result.terminal_cycle, 9);
verifyEqual(testCase, result.terminal_reason, 'confirmed');
verifyEqual(testCase, result.event_state.first_hit, 6);
verifyEqual(testCase, result.event_state.confirmed, 9);
verifyEqual(testCase, double.EventCycles, 1:9);
verifyFalse(testCase, any(double.CycleStarts == 10));
verifyFalse(testCase, isfile(fullfile(testCase.TestData.root, ...
    'substeps', 'cycle_0010.mat')));
end

function residual = lowerBoundRawResidual(original, snapshot, u, d, raw)
residual = original(snapshot, u, d, raw);
residual(:) = 0;
residual(1) = 2;
end

function removeRoot(root)
if isfolder(root)
    rmdir(root, 's');
end
end

function value = handoffDir()
value = fileparts(fileparts(mfilename('fullpath')));
end
