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
clear cleanup
end

function localWrite(filePath, value)
fileId = fopen(filePath, 'wb');
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, unicode2native(jsonencode(value), 'UTF-8'), 'uint8');
clear cleanup
end
