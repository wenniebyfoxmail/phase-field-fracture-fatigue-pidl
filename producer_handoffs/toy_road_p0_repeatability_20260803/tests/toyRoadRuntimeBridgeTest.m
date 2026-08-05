function tests = toyRoadRuntimeBridgeTest
tests = functiontests(localfunctions);
end

function testPathMismatchPersistsTerminalFailureBeforeThrow(testCase)
root = tempname;
mkdir(root);
cleanup = onCleanup(@() rmdir(root, 's'));
lockPath = fullfile(root, 'execution-lock.json');
receiptPath = fullfile(root, 'runtime-measurement.json');

actual = strsplit(path, pathsep);
expected = actual;
expected{1} = fullfile(root, 'deliberately-wrong-prefix');
lock = struct;
lock.protocol_version = 'toy-road-p0-repeatability-v2.1';
lock.authorization_scope = 'production_authorized';
lock.runtime_expectations = struct('matlab', struct( ...
    'absolute_path_order', {expected}));
localWrite(lockPath, lock);

verifyError(testCase, @() run_toy_road_runtime_bridge(lockPath, receiptPath), ...
    'toyRoadP0:RuntimeQualificationFailed');
verifyTrue(testCase, isfile(receiptPath));
receipt = jsondecode(fileread(receiptPath));
verifyEqual(testCase, receipt.status, 'FAIL');
verifyFalse(testCase, receipt.producer_entrypoint_authorized);
verifyEqual(testCase, receipt.first_failed_predicate, 'matlab_path_precedence');
verifyEqual(testCase, receipt.first_mismatch_index, 1);
verifyEqual(testCase, receipt.expected_absolute_path{1}, expected{1});
verifyEqual(testCase, receipt.actual_absolute_path{1}, actual{1});
verifyEqual(testCase, numel(receipt.expected_normalized_path), numel(expected));
verifyEqual(testCase, numel(receipt.actual_normalized_path), numel(actual));
verifyFalse(testCase, isfield(receipt, 'authorized_entrypoint'));
clear cleanup
end

function testValidTwoStageReceiptEntersMainProducer(testCase)
[runtimePath,cleanup] = localInstallChain(testCase, false, false);
setenv('TOY_ROAD_AUTHORIZATION_RECEIPT', runtimePath);
verifyError(testCase, @() main_toy_road_family_case, ...
    'toyRoadP0:MissingInputAsset');
clear cleanup
end

function testLaunchReceiptCannotEnterMainDirectly(testCase)
[~,cleanup,launchPath] = localInstallChain(testCase, false, false);
setenv('TOY_ROAD_AUTHORIZATION_RECEIPT', launchPath);
verifyError(testCase, @() main_toy_road_family_case, ...
    'toyRoadP0:AuthorizationRejected');
clear cleanup
end

function testTamperedUpstreamReceiptHashIsRejected(testCase)
[runtimePath,cleanup,launchPath] = localInstallChain(testCase, true, false);
setenv('TOY_ROAD_AUTHORIZATION_RECEIPT', runtimePath);
launch = jsondecode(fileread(launchPath));
launch.status = 'FAIL';
localWrite(launchPath, launch);
verifyError(testCase, @() main_toy_road_family_case, ...
    'toyRoadP0:AuthorizationRejected');
clear cleanup
end

function testSwappedEntrypointNamesAreRejected(testCase)
[runtimePath,cleanup] = localInstallChain(testCase, false, true);
setenv('TOY_ROAD_AUTHORIZATION_RECEIPT', runtimePath);
verifyError(testCase, @() main_toy_road_family_case, ...
    'toyRoadP0:AuthorizationRejected');
clear cleanup
end

function [runtimePath,cleanup,launchPath] = localInstallChain(testCase, ~, swap)
root = tempname;
mkdir(root);
cleanup = onCleanup(@() localCleanup(root));
values = struct('case_id','P0_parent','source_commit',repmat('a',1,40), ...
    'runtime_lock_sha256',repmat('2',1,64), ...
    'family_contract_sha256',repmat('3',1,64), ...
    'case_physics_contract_sha256',repmat('4',1,64), ...
    'execution_input_lock_sha256',repmat('5',1,64));
launchPath = fullfile(root, 'launch.json');
launch = values;
launch.status = 'PASS';
launch.authorization_scope = 'production_authorized';
launch.authorized_entrypoint = 'run_toy_road_runtime_bridge';
localWrite(launchPath, launch);
runtimePath = fullfile(root, 'runtime.json');
runtime = values;
runtime.status = 'PASS';
runtime.authorization_scope = 'production_authorized';
runtime.authorized_entrypoint = 'main_toy_road_family_case';
runtime.upstream_authorized_entrypoint = 'run_toy_road_runtime_bridge';
if swap
    runtime.authorized_entrypoint = 'run_toy_road_runtime_bridge';
    runtime.upstream_authorized_entrypoint = 'main_toy_road_family_case';
end
runtime.upstream_launch_receipt_path = launchPath;
runtime.upstream_launch_receipt_sha256 = localSha256(launchPath);
localWrite(runtimePath, runtime);
names = {'TOY_ROAD_CASE_ROLE','TOY_ROAD_SOURCE_COMMIT', ...
    'TOY_ROAD_RUNTIME_LOCK_SHA256','TOY_ROAD_FAMILY_CONTRACT_SHA256', ...
    'TOY_ROAD_CASE_PHYSICS_CONTRACT_SHA256', ...
    'TOY_ROAD_EXECUTION_INPUT_LOCK_SHA256'};
data = {values.case_id,values.source_commit,values.runtime_lock_sha256, ...
    values.family_contract_sha256,values.case_physics_contract_sha256, ...
    values.execution_input_lock_sha256};
for index = 1:numel(names), setenv(names{index},data{index}); end
pathNames = {'OUTPUT','WORK','TEMP','TMP','PREF','CACHE'};
for index = 1:numel(pathNames)
    setenv(['TOY_ROAD_' pathNames{index} '_ROOT'],fullfile(root,lower(pathNames{index})));
end
inputRoot = fullfile(root,'input'); mkdir(inputRoot);
setenv('TOY_ROAD_INPUT_ASSETS_ROOT',inputRoot);
testCase.addTeardown(@() localClearEnvironment());
end

function digest = localSha256(filePath)
fileId = fopen(filePath,'rb');
cleanup = onCleanup(@() fclose(fileId));
bytes = fread(fileId,Inf,'*uint8');
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(bytes);
digest = lower(reshape(dec2hex(typecast(hasher.digest(),'uint8'),2).',1,[]));
clear cleanup
end

function localClearEnvironment()
names = {'CASE_ROLE','SOURCE_COMMIT','RUNTIME_LOCK_SHA256', ...
    'FAMILY_CONTRACT_SHA256','CASE_PHYSICS_CONTRACT_SHA256', ...
    'EXECUTION_INPUT_LOCK_SHA256','OUTPUT_ROOT','WORK_ROOT','TEMP_ROOT', ...
    'TMP_ROOT','PREF_ROOT','CACHE_ROOT','INPUT_ASSETS_ROOT', ...
    'AUTHORIZATION_RECEIPT'};
for index = 1:numel(names), setenv(['TOY_ROAD_' names{index}],''); end
end

function localCleanup(root)
localClearEnvironment();
if isfolder(root), rmdir(root,'s'); end
end

function localWrite(filePath, value)
fileId = fopen(filePath, 'wb');
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, unicode2native(jsonencode(value), 'UTF-8'), 'uint8');
clear cleanup
end
