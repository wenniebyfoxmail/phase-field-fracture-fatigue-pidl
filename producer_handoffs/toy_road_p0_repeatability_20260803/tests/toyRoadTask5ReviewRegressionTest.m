function tests = toyRoadTask5ReviewRegressionTest
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

function testNonAuthorizingInjectionCannotReachAnyCallback(testCase)
callbackCount = 0;
request = fixtureRequest(testCase.TestData.root);
dependencies = struct( ...
    'load_parent_mesh',@unexpectedCallback, ...
    'build_recovery_input',@unexpectedCallback, ...
    'build_solver_context',@unexpectedCallback, ...
    'runtime_receipt',@unexpectedCallback, ...
    'solve_family_case',@unexpectedCallback);

    function varargout = unexpectedCallback(varargin)
        varargout = cell(1,nargout); %#ok<NASGU>
        callbackCount = callbackCount + 1;
        error('toyRoadP0:InjectedCallbackReached', ...
            'The non-authorizing path reached an injected callback.');
    end

verifyError(testCase, @() main_toy_road_family_case(request,dependencies), ...
    'toyRoadP0:AuthorizationRejected');
verifyEqual(testCase, callbackCount, 0);
verifyFalse(testCase, isfolder(request.output_root));
end

function testLockedStepHasFiveCompleteIncrementsAndExactFactors(testCase)
warningState = warning;
cleanup = onCleanup(@() warning(warningState));
warning('off','all');
raw = phase_field.fem.solver.step.params( ...
    'n_step',5,'loading','cyclic','discretization','loading', ...
    'uy_final',0.12,'R',0);
verifyEqual(testCase, numel(raw.uy_increment), 4, ...
    'The regression must exercise the locked constructor behavior.');

locked = build_toy_road_five_step_params(0.12);
fields = {'ux_increment','uy_increment','tx_increment','ty_increment'};
for index = 1:numel(fields)
    verifySize(testCase, locked.(fields{index}), [1 5]);
end
verifyEqual(testCase, locked.n_step, 5);
verifyFalse(testCase, locked.line_search);
verifyEqual(testCase, locked.ux_increment, zeros(1,5));
verifyEqual(testCase, locked.tx_increment, zeros(1,5));
verifyEqual(testCase, locked.ty_increment, zeros(1,5));
verifyEqual(testCase, cumsum(locked.uy_increment)/locked.uy_final, ...
    [0.25 0.50 0.75 1.00 0.00], 'AbsTol', 1e-15);
end

function testNestedWritableRootsAreRejected(testCase)
request = fixtureRequest(testCase.TestData.root);
request.output_root = fullfile(request.work_root,'output');

verifyError(testCase, @() reserve_toy_road_writable_roots(request), ...
    'toyRoadP0:FreshRootRequired');
verifyFalse(testCase, isfolder(request.work_root));
end

function testAtomicReservationRejectsDeterministicCreationRace(testCase)
request = fixtureRequest(testCase.TestData.root);
attempts = 0;

    function racingCreator(path)
        attempts = attempts + 1;
        mkdir(path);
        error('toyRoadP0Test:CreationRace', ...
            'A deterministic competing creator won the reservation.');
    end

verifyError(testCase, @() reserve_toy_road_writable_roots( ...
    request,@racingCreator), 'toyRoadP0:FreshRootRequired');
verifyEqual(testCase, attempts, 1);
end

function testRecoveryRejectsReusedSystemHandle(testCase)
shared = ToyRoadP0RecoverySystem(zeros(4,1));
factoryCalls = 0;
input = recoveryInput(@staleFactory);

    function [sys,record] = staleFactory(d)
        factoryCalls = factoryCalls + 1;
        sys = shared;
        record = factoryRecord(factoryCalls,d,sys);
    end

verifyError(testCase, @() recover_toy_road_family_state(input), ...
    'toyRoadP0:StaleRecoverySystem');
verifyEqual(testCase, factoryCalls, 2);
end

function testRecoveryReceiptUsesRecordedFactoryInputsAndOrder(testCase)
factoryInputs = {};
input = recoveryInput(@recordingFactory);

    function [sys,record] = recordingFactory(d)
        factoryInputs{end+1} = d;
        sys = ToyRoadP0RecoverySystem(d);
        record = factoryRecord(numel(factoryInputs),d,sys);
    end

[sys,d,~,~,details] = recover_toy_road_family_state(input);
verifyEqual(testCase, factoryInputs, ...
    {zeros(4,1),[0;0.25;0.75;1]});
verifyNotEqual(testCase, details.system_factory_records(1).system_identity, ...
    details.system_factory_records(2).system_identity);
verifyEqual(testCase, details.system_factory_phase_field, factoryInputs{2});
verifyEqual(testCase, sys.PhaseFieldInput, d);
verifyEqual(testCase, [details.system_factory_records.construction_ordinal], ...
    [1 2]);
end

function testIncompleteStepRejectedBeforeSystemConstruction(testCase)
factoryCalls = 0;
input = recoveryInput(@factory);
input.sol_step_par.uy_increment = input.sol_step_par.uy_increment(1:4);

    function [sys,record] = factory(d)
        factoryCalls = factoryCalls + 1;
        sys = ToyRoadP0RecoverySystem(d);
        record = factoryRecord(factoryCalls,d,sys);
    end

verifyError(testCase, @() recover_toy_road_family_state(input), ...
    'toyRoadP0:InvalidRecoveryInput');
verifyEqual(testCase, factoryCalls, 0);
end

function request = fixtureRequest(root)
request = struct( ...
    'authorization_scope','test_only_non_authorizing', ...
    'authorization_receipt',struct(), ...
    'case_id','P0_parent', ...
    'source_commit',repmat('a',1,40), ...
    'runtime_lock_sha256',repmat('2',1,64), ...
    'family_contract_sha256',repmat('3',1,64), ...
    'case_physics_contract_sha256',repmat('4',1,64), ...
    'execution_input_lock_sha256',repmat('5',1,64), ...
    'output_root',fullfile(root,'output'), ...
    'work_root',fullfile(root,'work'), ...
    'temp_root',fullfile(root,'temp'), ...
    'tmp_root',fullfile(root,'tmp'), ...
    'pref_root',fullfile(root,'pref'), ...
    'cache_root',fullfile(root,'cache'), ...
    'input_assets_root',fullfile(root,'input_assets'));
mkdir(request.input_assets_root);
request.authorization_receipt = struct( ...
    'status','PASS', ...
    'authorization_scope',request.authorization_scope, ...
    'authorized_entrypoint','main_toy_road_family_case', ...
    'case_id',request.case_id, ...
    'source_commit',request.source_commit, ...
    'runtime_lock_sha256',request.runtime_lock_sha256, ...
    'family_contract_sha256',request.family_contract_sha256, ...
    'case_physics_contract_sha256',request.case_physics_contract_sha256, ...
    'execution_input_lock_sha256',request.execution_input_lock_sha256);
end

function input = recoveryInput(factory)
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
    'p_field',zeros(4,1), ...
    'p_field_old',zeros(4,1), ...
    'history_vars_old',zeros(1,4,4), ...
    'num_elem',1, ...
    'num_gauss_pts',4, ...
    'sol_step_par',step, ...
    'sol_par',struct('max_iter_pf',25,'tol_p_field',4e-4), ...
    'system_factory',factory, ...
    'recovery_newton',@controlledRecoveryNewton);
end

function [d,history,residual,failed,details] = controlledRecoveryNewton(varargin)
d = [-1e-8;0.25;0.75;1+1e-8];
history = zeros(1,4,4);
residual = 2e-5;
failed = false;
details = struct('kind','controlled_zero_load');
end

function record = factoryRecord(ordinal,d,sys)
record = struct( ...
    'construction_ordinal',ordinal, ...
    'phase_field',d, ...
    'system_class',class(sys), ...
    'system_identity',sprintf('controlled_system_%d',ordinal));
end

function removeRoot(root)
if isfolder(root)
    rmdir(root,'s');
end
end

function value = handoffDir()
value = fileparts(fileparts(mfilename('fullpath')));
end
