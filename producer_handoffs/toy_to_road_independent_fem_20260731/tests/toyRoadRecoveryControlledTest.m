function tests = toyRoadRecoveryControlledTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
addpath(handoffDir());
addpath(fileparts(mfilename('fullpath')));
testCase.addTeardown(@() rmpath(handoffDir()));
testCase.addTeardown(@() rmpath(fileparts(mfilename('fullpath'))));
end

function testRecoveryUsesExactNewtonContractClipsRebuildsAndResets(testCase)
[input, recoveryDouble, operators] = syntheticRecoveryContract();

[sys, pField, pFieldOld, history, residual, details] = ...
    recover_toy_road_initial_state(input, operators);

expectedClipped = [0; 0.2; 0.6; 1; 0; 1];
verifyEqual(testCase, recoveryDouble.Trace, ...
    ["factory_initial" "newton" "factory_clipped"]);
verifyEqual(testCase, recoveryDouble.NewtonCallCount, 1);
verifyEqual(testCase, recoveryDouble.FactoryDamageInputs{1}, input.p_field);
verifyEqual(testCase, recoveryDouble.FactoryDamageInputs{2}, expectedClipped);
verifyTrue(testCase, sys == recoveryDouble.Systems{2});
verifyFalse(testCase, sys == recoveryDouble.Systems{1});
verifyEqual(testCase, sys.damage_at_construction, expectedClipped);
verifyEqual(testCase, pField, expectedClipped);
verifyEqual(testCase, pFieldOld, expectedClipped);
verifyEqual(testCase, residual, recoveryDouble.RecoveryResidual);
verifyEqual(testCase, details.initial_residual, recoveryDouble.InitialResidual);
verifyEqual(testCase, details.coupling_vars, recoveryDouble.CouplingOutput);
verifyEqual(testCase, details.history_vars_before_reset, ...
    recoveryDouble.RecoveredHistory);
verifyFalse(testCase, details.non_converged);
verifySize(testCase, details.coupling_vars, [6 1]);
verifySize(testCase, details.history_vars_before_reset, [2 4 4]);
verifyEqual(testCase, history(:, :, 1), ...
    recoveryDouble.RecoveredHistory(:, :, 1));
verifyEqual(testCase, history(:, :, 2:3), zeros(2, 4, 2));
verifyEqual(testCase, history(:, :, 4), ones(2, 4));
end

function testRecoveryRejectsFactoryThatReturnsStaleInitialSystem(testCase)
[input, recoveryDouble, operators] = syntheticRecoveryContract();
recoveryDouble.ReuseInitialSystem = true;

verifyError(testCase, @() recover_toy_road_initial_state(input, operators), ...
    'toyRoad:StaleRecoverySystem');
verifyEqual(testCase, recoveryDouble.Trace, ...
    ["factory_initial" "newton" "factory_clipped"]);
end

function testRecoveryRejectsInvalidNewtonOutputShape(testCase)
[input, recoveryDouble, operators] = syntheticRecoveryContract();
recoveryDouble.InvalidRecoveredFieldShape = true;

verifyError(testCase, @() recover_toy_road_initial_state(input, operators), ...
    'toyRoad:InvalidRecoveryOutput');
verifyEqual(testCase, recoveryDouble.Trace, ["factory_initial" "newton"]);
end

function testRecoveryPropagatesNonConvergenceBeforeRebuild(testCase)
[input, recoveryDouble, operators] = syntheticRecoveryContract();
recoveryDouble.ReturnNonConverged = true;

verifyError(testCase, @() recover_toy_road_initial_state(input, operators), ...
    'toyRoad:RecoveryFailed');
verifyEqual(testCase, recoveryDouble.Trace, ["factory_initial" "newton"]);
end

function [input, recoveryDouble, operators] = syntheticRecoveryContract()
mesh = struct('num_node', 6, 'num_elem', 2, 'contract_sentinel', 7101);
quadrature = struct('num_gauss_pts', 4, 'contract_sentinel', 7201);
dofs = struct('active_dof_pf', [2; 4; 6], 'contract_sentinel', 7301);
stiffness = struct('i_row_pf', (11:16)', 'j_col_pf', (21:26)', ...
    'contract_sentinel', 7401);
initialHistory = zeros(2, 4, 4);
assemblyPf = @syntheticAssemblyPf;
contract = struct( ...
    'mat_char', struct('contract_sentinel', 7501), ...
    'geom', struct('L', 0.0, 'B', 0.0, 't', 1.0, ...
        'contract_sentinel', 7601), ...
    'quadrature', quadrature, ...
    'dofs', dofs, ...
    'node_boundaries', struct('contract_sentinel', 7701), ...
    'sol_step_par', struct('line_search', false, 'contract_sentinel', 7801), ...
    'mesh', mesh, ...
    'stress_state', struct('as_number', 7901), ...
    'diss_fct', 'AT1', ...
    'assembly_pf_fh', assemblyPf, ...
    'sol_par', struct('max_iter_pf', 250, 'tol_p_field', 4e-4), ...
    'initial_p_field', [1; 0; 0; 1; 0; 0], ...
    'initial_p_field_old', zeros(6, 1), ...
    'initial_history', initialHistory, ...
    'zero_raw_driver', zeros(2, 4), ...
    'stiffness_matrix', stiffness);
recoveryDouble = ToyRoadRecoveryDouble(contract);
operators = struct( ...
    'system_factory', @(varargin) recoveryDouble.systemFactory(varargin{:}), ...
    'newton_raphson', @(varargin) recoveryDouble.newtonRaphson(varargin{:}));
input = rmfield(contract, {'zero_raw_driver', 'stiffness_matrix'});
input.p_field = input.initial_p_field;
input.p_field_old = input.initial_p_field_old;
input.history_vars_old = input.initial_history;
input = rmfield(input, {'initial_p_field', 'initial_p_field_old', 'initial_history'});
end

function varargout = syntheticAssemblyPf(varargin)
varargout = cell(1, max(nargout, 1));
end

function value = handoffDir()
value = fileparts(fileparts(mfilename('fullpath')));
end
