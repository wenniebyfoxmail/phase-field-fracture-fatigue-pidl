function tests = toyRoadRecoveryTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
addpath(handoffDir());
testCase.addTeardown(@() rmpath(handoffDir()));
end

function testRecoveryClipsThenRebuildsSystem(testCase)
factoryInputs = {};
input = fixtureInput(@recordingFactory, @recoveryNewton);

    function [sys,record] = recordingFactory(d)
        factoryInputs{end+1} = d;
        [sys,record] = controlledSentinel(numel(factoryInputs),d);
    end
    function [d,history,residual,failed,details] = recoveryNewton(varargin)
        verifyEqual(testCase, varargin{5}, zeros(1,4));
        d = [-1e-8; 0.25; 0.75; 1+1e-8];
        history = 7 * ones(1,4,4);
        residual = 2e-5;
        failed = false;
        details = struct('newton_kind','controlled_zero_load');
    end

[sys,d,dOld,history,details] = recover_toy_road_family_state(input);

verifyEqual(testCase, numel(factoryInputs), 2);
verifyEqual(testCase, factoryInputs{1}, input.p_field);
verifyEqual(testCase, factoryInputs{2}, [0;0.25;0.75;1]);
verifyEqual(testCase, sys.phase_field_input, d);
verifyGreaterThanOrEqual(testCase, min(d), 0);
verifyLessThanOrEqual(testCase, max(d), 1);
verifyEqual(testCase, dOld, d);
verifyEqual(testCase, details.system_factory_phase_field, d);
verifyTrue(testCase, details.system_rebuilt_after_projection);
verifyEqual(testCase, details.operation_order, ...
    {'initial_system','zero_load_recovery','project_damage','rebuild_system','reset_fatigue'});
verifyEqual(testCase, history(:,:,2:3), zeros(size(history,1),4,2));
verifyEqual(testCase, history(:,:,4), ones(size(history,1),4));
verifyEqual(testCase, details.history_vars_before_reset, 7*ones(1,4,4));
end

function testFiveStepContractCheckedBeforeAnyFactoryOrNewtonCall(testCase)
calls = 0;
input = fixtureInput(@factory, @newton);
input.sol_step_par.n_step = 8;

    function [sys,record] = factory(d)
        calls = calls + 1;
        [sys,record] = controlledSentinel(calls,d);
    end
    function varargout = newton(varargin)
        calls = calls + 1;
        varargout = cell(1,5);
    end

verifyError(testCase, @() recover_toy_road_family_state(input), ...
    'toyRoadP0:InvalidRecoveryInput');
verifyEqual(testCase, calls, 0);
end

function testRecoveryRejectsNonconvergenceBeforeRebuild(testCase)
factoryCalls = 0;
input = fixtureInput(@factory, @newton);

    function [sys,record] = factory(d)
        factoryCalls = factoryCalls + 1;
        [sys,record] = controlledSentinel(factoryCalls,d);
    end
    function [d,history,residual,failed,details] = newton(varargin)
        d = zeros(4,1); history = zeros(1,4,4); residual = 1; failed = true;
        details = struct();
    end

verifyError(testCase, @() recover_toy_road_family_state(input), ...
    'toyRoadP0:RecoveryFailed');
verifyEqual(testCase, factoryCalls, 1);
end

function testRecoveryRejectsInvalidOutputWithoutClippingIt(testCase)
factoryCalls = 0;
input = fixtureInput(@factory, @newton);

    function [sys,record] = factory(d)
        factoryCalls = factoryCalls + 1;
        [sys,record] = controlledSentinel(factoryCalls,d);
    end
    function [d,history,residual,failed,details] = newton(varargin)
        d = [0;NaN;0;0]; history = zeros(1,4,4); residual = 0; failed = false;
        details = struct();
    end

verifyError(testCase, @() recover_toy_road_family_state(input), ...
    'toyRoadP0:InvalidRecoveryOutput');
verifyEqual(testCase, factoryCalls, 1);
end

function testControlledValueSentinelIsAcceptedAsDataOnly(testCase)
factoryCalls = 0;
input = fixtureInput(@factory,@newton);
input.system_validation_mode = 'controlled_value_double_v1';

    function [sys,record] = factory(d)
        factoryCalls = factoryCalls + 1;
        [sys,record] = controlledSentinel(factoryCalls,d);
    end
    function [d,history,residual,failed,details] = newton(sys,varargin)
        verifyTrue(testCase,isstruct(sys));
        verifyFalse(testCase,isobject(sys));
        d = [-1e-8;0.25;0.75;1+1e-8];
        history = zeros(1,4,4);
        residual = 2e-5;
        failed = false;
        details = struct('kind','controlled_value_only');
    end

[sys,d,~,~,details] = recover_toy_road_family_state(input);
verifyTrue(testCase,isstruct(sys));
verifyFalse(testCase,isobject(sys));
verifyEqual(testCase,sys.phase_field_input,d);
verifyEqual(testCase,sys.construction_ordinal,2);
verifyEqual(testCase,details.system_factory_phase_field,d);
verifyEqual(testCase,factoryCalls,2);
end

function testProductionModeRejectsNonPhaseFieldSystemHandle(testCase)
input = fixtureInput(@factory,@newton);
input.system_validation_mode = 'production_phase_field_system_v1';

    function [sys,record] = factory(d)
        sys = ToyRoadP0RecoverySystem(d);
        record = factoryRecord(1,d,sys);
    end
    function varargout = newton(varargin)
        varargout = cell(1,5);
    end

verifyError(testCase,@() recover_toy_road_family_state(input), ...
    'toyRoadP0:InvalidRecoverySystem');
end

function input = fixtureInput(factory,newton)
factors = [0.25 0.50 0.75 1.00 0.00];
umax = 0.12;
step = struct( ...
    'n_step',5, ...
    'loading','cyclic', ...
    'discretization','loading', ...
    'uy_final',umax, ...
    'R',0, ...
    'line_search',false, ...
    'ux_increment',zeros(1,5), ...
    'uy_increment',umax*diff([0 factors]), ...
    'tx_increment',zeros(1,5), ...
    'ty_increment',zeros(1,5));
input = struct( ...
    'p_field', zeros(4,1), ...
    'p_field_old', zeros(4,1), ...
    'history_vars_old', zeros(1,4,4), ...
    'num_elem', 1, ...
    'num_gauss_pts', 4, ...
    'sol_step_par', step, ...
    'sol_par', struct('max_iter_pf',25,'tol_p_field',4e-4), ...
    'system_validation_mode','controlled_value_double_v1', ...
    'system_factory', factory, ...
    'recovery_newton', newton);
end

function record = factoryRecord(ordinal,d,sys)
record = struct( ...
    'construction_ordinal',ordinal, ...
    'phase_field',d, ...
    'system_class',class(sys), ...
    'system_identity',sprintf('controlled_system_%d',ordinal));
end

function [system,record] = controlledSentinel(ordinal,d)
system = struct( ...
    'sentinel_kind','toy_road_controlled_system_value_v1', ...
    'construction_ordinal',double(ordinal), ...
    'phase_field_input',d, ...
    'DOFS',double((1:numel(d)).'), ...
    'STIFFNESS_MATRIX',eye(numel(d)));
record = struct( ...
    'construction_ordinal',double(ordinal), ...
    'phase_field',d, ...
    'system_class','toy_road_controlled_system_value_v1', ...
    'system_identity',sprintf('controlled_value_system_%d',ordinal));
end

function value = handoffDir()
value = fileparts(fileparts(mfilename('fullpath')));
end
