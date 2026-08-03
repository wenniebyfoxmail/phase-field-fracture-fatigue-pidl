function tests = toyRoadDriverContractTest
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

function testControlledInjectionCannotEnterProductionDriver(testCase)
request = fixtureRequest(testCase.TestData.root, 'P0_parent');
dependencies = fixtureDependencies();

verifyError(testCase, @() main_toy_road_family_case(request,dependencies), ...
    'toyRoadP0:AuthorizationRejected');
verifyFalse(testCase, isfolder(request.output_root));
verifyFalse(testCase, isfolder(request.work_root));
end

function testControlledHarnessRejectsExecutableReceiptBeforeDispatch(testCase)
request = fixtureRequest(testCase.TestData.root, 'P0_parent');
request.authorization_receipt.authorized_entrypoint = ...
    'run_toy_road_controlled_driver_harness';
marker = fullfile(testCase.TestData.root,'malicious_receipt_reached');
request.authorization_receipt.status = ...
    ToyRoadP0MaliciousReceiptValue(marker);

verifyError(testCase, @() run_toy_road_controlled_driver_harness(request), ...
    'toyRoadP0:ControlledHarnessRejected');
verifyFalse(testCase,isfile(marker));
verifyNoWritableRoots(testCase,request);
end

function testControlledHarnessRequiresExactValueOnlySchemas(testCase)
request = fixtureRequest(testCase.TestData.root, 'P0_parent');
request.authorization_receipt.authorized_entrypoint = ...
    'run_toy_road_controlled_driver_harness';
request.authorization_receipt.unexpected = 'not_allowed';

verifyError(testCase, @() run_toy_road_controlled_driver_harness(request), ...
    'toyRoadP0:ControlledHarnessRejected');
verifyNoWritableRoots(testCase,request);

request = fixtureRequest(testCase.TestData.root, 'P0_parent');
request.authorization_receipt.authorized_entrypoint = ...
    'run_toy_road_controlled_driver_harness';
request.unexpected = 'not_allowed';
verifyError(testCase, @() run_toy_road_controlled_driver_harness(request), ...
    'toyRoadP0:ControlledHarnessRejected');
verifyNoWritableRoots(testCase,request);
end

function testControlledSystemShadowCannotRunOnSuccessfulHarness(testCase)
request = fixtureRequest(testCase.TestData.root, 'P0_parent');
request.authorization_receipt.authorized_entrypoint = ...
    'run_toy_road_controlled_driver_harness';
shadowRoot = fullfile(fileparts(mfilename('fullpath')), ...
    'fixtures','controlled_system_shadow');
marker = fullfile(testCase.TestData.root,'shadow_system_reached');
oldMarker = getenv('TOY_ROAD_SHADOW_SYSTEM_MARKER');
warningState = warning;
cleanup = onCleanup(@() restoreShadowPath( ...
    shadowRoot,oldMarker,warningState));
warning('off','all');
setenv('TOY_ROAD_SHADOW_SYSTEM_MARKER',marker);
addpath(shadowRoot,'-begin');
clear('ToyRoadP0LocalControlledSystem');

[result,observations] = run_toy_road_controlled_driver_harness(request);

verifyTrue(testCase,result.complete);
verifyEqual(testCase,observations.solver_invocation_count,1);
verifyFalse(testCase,isfile(marker));
verifyTrue(testCase,isfolder(request.output_root));
clear cleanup
end

function testSealedControlledHarnessExecutesSuccessfulDriverCore(testCase)
request = fixtureRequest(testCase.TestData.root, 'P0_parent');
request.authorization_receipt.authorized_entrypoint = ...
    'run_toy_road_controlled_driver_harness';

[result,observations] = run_toy_road_controlled_driver_harness(request);

verifyTrue(testCase, result.complete);
verifyEqual(testCase, result.case_id, request.case_id);
verifyFalse(testCase,containsExecutable(observations));
verifyEqual(testCase,observations.solver_invocation_count,1);
verifyEqual(testCase,numel(observations.factory_inputs),2);
verifyEqual(testCase,observations.factory_inputs{1},zeros(4,1));
verifyEqual(testCase,observations.factory_inputs{2},[0;0.25;0.75;1]);

entries = dir(request.output_root);
entries = entries(~ismember({entries.name},{'.','..'}));
verifyFalse(testCase, any([entries.isdir]));
verifyEqual(testCase, sort({entries.name}), sort({ ...
    'INPUT_SNAPSHOT.json','mesh_geometry.mat','state0_analysis.mat', ...
    'RUNTIME_RECEIPT.json'}));

snapshot = jsondecode(fileread(fullfile( ...
    request.output_root,'INPUT_SNAPSHOT.json')));
verifyEqual(testCase, snapshot.case_id, request.case_id);
verifyEqual(testCase, snapshot.runtime_lock_sha256,request.runtime_lock_sha256);
verifyEqual(testCase, snapshot.family_contract_sha256, ...
    request.family_contract_sha256);
verifyEqual(testCase, snapshot.case_physics_contract_sha256, ...
    request.case_physics_contract_sha256);
verifyEqual(testCase, snapshot.execution_input_lock_sha256, ...
    request.execution_input_lock_sha256);
verifyTrue(testCase, snapshot.fresh_state0);
verifyFalse(testCase, snapshot.resume_allowed);

statePayload = load(fullfile(request.output_root,'state0_analysis.mat'));
verifyEqual(testCase, statePayload.state0.d_node,[0;0.25;0.75;1]);
verifyEqual(testCase, statePayload.state0.d_node_old, ...
    statePayload.state0.d_node);
verifyEqual(testCase, statePayload.state0.alpha_bar_gp,zeros(1,4));
verifyEqual(testCase, statePayload.state0.history_vars(:,:,2:3), ...
    zeros(1,4,2));
verifyEqual(testCase, statePayload.state0.history_vars(:,:,4),ones(1,4));

context = observations.bound_context;
verifyEqual(testCase, context.authorization_scope,'test_only_non_authorizing');
verifyEqual(testCase, context.case_id,request.case_id);
verifyEqual(testCase, context.output_root,request.output_root);
verifyEqual(testCase, context.state0.d_node,statePayload.state0.d_node);
verifyEqual(testCase, context.state0.alpha_bar_gp,zeros(1,4));
verifyEqual(testCase, context.contract.eta,0);
verifyEqual(testCase, context.contract.runtime_lock_sha256, ...
    request.runtime_lock_sha256);
verifyEqual(testCase, context.contract.family_contract_sha256, ...
    request.family_contract_sha256);
verifyEqual(testCase, context.contract.case_physics_contract_sha256, ...
    request.case_physics_contract_sha256);
verifyEqual(testCase, context.contract.execution_input_lock_sha256, ...
    request.execution_input_lock_sha256);
verifyEqual(testCase, context.sol_step_template.n_step,5);
verifyEqual(testCase, ...
    cumsum(context.sol_step_template.uy_increment) / ...
    context.sol_step_template.uy_final,[.25 .5 .75 1 0], ...
    'AbsTol',1e-15);
end

function verifyNoWritableRoots(testCase,request)
writeFields = {'output_root','work_root','temp_root','tmp_root', ...
    'pref_root','cache_root'};
for index = 1:numel(writeFields)
    verifyFalse(testCase,isfolder(request.(writeFields{index})));
end
end

function restoreShadowPath(shadowRoot,oldMarker,warningState)
if contains(path,[shadowRoot pathsep]) || endsWith(path,shadowRoot)
    rmpath(shadowRoot);
end
clear('ToyRoadP0LocalControlledSystem');
setenv('TOY_ROAD_SHADOW_SYSTEM_MARKER',oldMarker);
warning(warningState);
end

function testControlledHarnessRejectsArbitraryOperatorsAndProductionScope(testCase)
request = fixtureRequest(testCase.TestData.root, 'P0_parent');
request.authorization_receipt.authorized_entrypoint = ...
    'run_toy_road_controlled_driver_harness';
operatorReached = false;

    function result = productionLikeOperator(varargin)
        operatorReached = true;
        result = struct('complete',true);
    end

verifyError(testCase, @() run_toy_road_controlled_driver_harness( ...
    request,@productionLikeOperator), 'MATLAB:TooManyInputs');
verifyFalse(testCase, operatorReached);
verifyFalse(testCase, isfolder(request.output_root));

wrongClass = ToyRoadP0RecoverySystem(zeros(4,1));
verifyError(testCase, @() run_toy_road_controlled_driver_harness( ...
    request,wrongClass), 'MATLAB:TooManyInputs');
verifyFalse(testCase, isfolder(request.output_root));

request.authorization_scope = 'production_authorized';
request.authorization_receipt.authorization_scope = 'production_authorized';
verifyError(testCase, @() run_toy_road_controlled_driver_harness( ...
    request), 'toyRoadP0:ControlledHarnessRejected');
verifyFalse(testCase, isfolder(request.output_root));

verifyError(testCase, @() run_toy_road_driver_core(request,struct()), ...
    'MATLAB:UndefinedFunction');
end

function testPathShadowCannotForgeSealedControlledIdentity(testCase)
request = fixtureRequest(testCase.TestData.root, 'P0_parent');
request.authorization_receipt.authorized_entrypoint = ...
    'run_toy_road_controlled_driver_harness';
forged = ToyRoadP0ForgedSealedAdapter();
shadowRoot = fullfile(fileparts(mfilename('fullpath')), ...
    'fixtures','isa_shadow');
warningState = warning;
warning('off','all');
addpath(shadowRoot,'-begin');
clear('isa');
isaMarker = fullfile(testCase.TestData.root,'forged_isa_reached');
operatorMarker = fullfile(testCase.TestData.root,'forged_operator_reached');
oldIsaMarker = getenv('TOY_ROAD_FORGED_ISA_MARKER');
oldOperatorMarker = getenv('TOY_ROAD_FORGED_OPERATOR_MARKER');
setenv('TOY_ROAD_FORGED_ISA_MARKER',isaMarker);
setenv('TOY_ROAD_FORGED_OPERATOR_MARKER',operatorMarker);

exception = [];
try
    run_toy_road_controlled_driver_harness(request,forged);
catch caught
    exception = caught;
end
rmpath(shadowRoot);
clear('isa');
warning(warningState);
setenv('TOY_ROAD_FORGED_ISA_MARKER',oldIsaMarker);
setenv('TOY_ROAD_FORGED_OPERATOR_MARKER',oldOperatorMarker);

verifyNotEmpty(testCase,exception);
verifyEqual(testCase,exception.identifier,'MATLAB:TooManyInputs');
verifyFalse(testCase,isfile(isaMarker));
verifyFalse(testCase,isfile(operatorMarker));
writeFields = {'output_root','work_root','temp_root','tmp_root', ...
    'pref_root','cache_root'};
for index = 1:numel(writeFields)
    verifyFalse(testCase,isfolder(request.(writeFields{index})));
end
end

function found = containsExecutable(value)
found = builtin('isa',value,'function_handle') || isobject(value);
if found
    return
end
if isstruct(value)
    names = fieldnames(value);
    found = any(cellfun(@(name) containsExecutable(value.(name)),names));
elseif iscell(value)
    found = any(cellfun(@containsExecutable,value));
end
end

function testAuthorizationMismatchStopsBeforeCreatingRoots(testCase)
request = fixtureRequest(testCase.TestData.root, 'P0_parent');
request.authorization_receipt.case_id = 'P0R_parent_repeat';

verifyError(testCase, @() main_toy_road_family_case( ...
    request, fixtureDependencies()), 'toyRoadP0:AuthorizationRejected');
verifyFalse(testCase, isfolder(request.output_root));
verifyFalse(testCase, isfolder(request.work_root));
end

function testPreflightScopeCannotRunDriver(testCase)
request = fixtureRequest(testCase.TestData.root, 'T1_initial_defect');
request.authorization_scope = 'preflight_only_non_authorizing';
request.authorization_receipt.authorization_scope = ...
    'preflight_only_non_authorizing';

verifyError(testCase, @() main_toy_road_family_case( ...
    request, fixtureDependencies()), 'toyRoadP0:AuthorizationRejected');
verifyFalse(testCase, isfolder(request.output_root));
end

function testReusedOrAliasedWritableRootsFailClosed(testCase)
request = fixtureRequest(testCase.TestData.root, 'P0_parent');
mkdir(request.work_root);
verifyError(testCase, @() reserve_toy_road_writable_roots(request), ...
    'toyRoadP0:FreshRootRequired');
verifyFalse(testCase, isfolder(request.output_root));

rmdir(request.work_root);
request.temp_root = request.cache_root;
verifyError(testCase, @() reserve_toy_road_writable_roots(request), ...
    'toyRoadP0:FreshRootRequired');
verifyFalse(testCase, isfolder(request.output_root));
end

function testResumeOrCheckpointInjectionIsRejected(testCase)
request = fixtureRequest(testCase.TestData.root, 'P0R_parent_repeat');
request.resume_root = fullfile(testCase.TestData.root, 'p0_output');

verifyError(testCase, @() main_toy_road_family_case( ...
    request, fixtureDependencies()), 'toyRoadP0:AuthorizationRejected');
verifyFalse(testCase, isfolder(request.output_root));
end

function testDriverRequiresAllProvenanceAndDigests(testCase)
request = rmfield(fixtureRequest(testCase.TestData.root, 'T2_material_state'), ...
    'execution_input_lock_sha256');

verifyError(testCase, @() main_toy_road_family_case( ...
    request, fixtureDependencies()), 'toyRoadP0:AuthorizationRejected');
end

function testEntrypointDeclaresProductionEnvironmentContract(testCase)
source = fileread(fullfile(handoffDir(), 'main_toy_road_family_case.m'));
required = {'TOY_ROAD_CASE_ROLE','TOY_ROAD_SOURCE_COMMIT', ...
    'TOY_ROAD_RUNTIME_LOCK_SHA256','TOY_ROAD_FAMILY_CONTRACT_SHA256', ...
    'TOY_ROAD_CASE_PHYSICS_CONTRACT_SHA256', ...
    'TOY_ROAD_EXECUTION_INPUT_LOCK_SHA256','TOY_ROAD_OUTPUT_ROOT', ...
    'TOY_ROAD_WORK_ROOT','TOY_ROAD_TEMP_ROOT','TOY_ROAD_TMP_ROOT', ...
    'TOY_ROAD_PREF_ROOT','TOY_ROAD_CACHE_ROOT', ...
    'TOY_ROAD_INPUT_ASSETS_ROOT','TOY_ROAD_AUTHORIZATION_RECEIPT'};
for index = 1:numel(required)
    verifyNotEmpty(testCase, strfind(source, required{index}));
end
verifyNotEmpty(testCase, strfind(source, 'solve_toy_road_family_case'));
verifyEmpty(testCase, strfind(source, 'toy_to_road_independent_fem_20260731'));
verifyNotEmpty(testCase, strfind(source, ...
    'sys.CC,d,snapshot.d_lb,raw'));
end

function request = fixtureRequest(root, role)
request = struct( ...
    'authorization_scope', 'test_only_non_authorizing', ...
    'authorization_receipt', struct(), ...
    'case_id', role, ...
    'source_commit', repmat('a',1,40), ...
    'runtime_lock_sha256', repmat('2',1,64), ...
    'family_contract_sha256', repmat('3',1,64), ...
    'case_physics_contract_sha256', repmat('4',1,64), ...
    'execution_input_lock_sha256', repmat('5',1,64), ...
    'output_root', fullfile(root, ['output_' role]), ...
    'work_root', fullfile(root, ['work_' role]), ...
    'temp_root', fullfile(root, ['temp_' role]), ...
    'tmp_root', fullfile(root, ['tmp_' role]), ...
    'pref_root', fullfile(root, ['pref_' role]), ...
    'cache_root', fullfile(root, ['cache_' role]), ...
    'input_assets_root', fullfile(root, 'input_assets'));
if ~isfolder(request.input_assets_root)
    mkdir(request.input_assets_root);
end
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

function dependencies = fixtureDependencies()
dependencies = struct( ...
    'load_parent_mesh', @loadParentMesh, ...
    'build_recovery_input', @buildRecoveryInput, ...
    'build_solver_context', @buildSolverContext, ...
    'runtime_receipt', @runtimeReceipt, ...
    'solve_family_case', @solve_toy_road_family_case);
end

function mesh = loadParentMesh(~)
mesh = struct( ...
    'node_coords', [-.5 -.5; .5 -.5; .5 .5; -.5 .5], ...
    'connectivity', [1 2 3 4]);
end

function input = buildRecoveryInput(~,~)
input = struct( ...
    'p_field', zeros(4,1), ...
    'p_field_old', zeros(4,1), ...
    'history_vars_old', zeros(1,4,4), ...
    'num_elem', 1, 'num_gauss_pts', 4, ...
    'sol_step_par', struct('n_step',5,'line_search',false), ...
    'sol_par', struct('max_iter_pf',25,'tol_p_field',4e-4), ...
    'system_factory', @systemFactory, ...
    'recovery_newton', @recoveryNewton);
end

function sys = systemFactory(d)
sys = struct('phase_field_input',d);
end

function [d,history,residual,failed,details] = recoveryNewton(varargin)
d = 0.1*ones(4,1);
history = 9*ones(1,4,4);
residual = 1e-5;
failed = false;
details = struct('kind','controlled');
end

function context = buildSolverContext(~,~,request)
double = ToyRoadP0SolverDouble();
context = double.makeContext(request.output_root, request.case_id);
end

function receipt = runtimeReceipt(request)
receipt = struct( ...
    'status','PASS', ...
    'authorization_scope',request.authorization_scope, ...
    'case_id',request.case_id, ...
    'source_commit',request.source_commit, ...
    'runtime_lock_sha256',request.runtime_lock_sha256);
end

function removeRoot(root)
if isfolder(root)
    rmdir(root,'s');
end
end

function value = handoffDir()
value = fileparts(fileparts(mfilename('fullpath')));
end
