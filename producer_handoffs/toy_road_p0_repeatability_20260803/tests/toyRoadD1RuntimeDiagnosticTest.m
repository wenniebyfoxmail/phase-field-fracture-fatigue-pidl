function tests = toyRoadD1RuntimeDiagnosticTest
tests = functiontests(localfunctions);
end

function testExactFixturePasses(testCase)
[lock, measured] = localFixture(testCase.TestData.root);
receiptPath = fullfile(testCase.TestData.root,'pass.json');
lockPath = localWriteLock(testCase.TestData.root,'pass-lock.json',lock);
run_toy_road_runtime_diagnostic(lockPath,receiptPath,measured);
receipt = jsondecode(fileread(receiptPath));
verifyEqual(testCase,receipt.status,'PASS');
verifyEqual(testCase,receipt.producer_invocation_count,0);
verifyEqual(testCase,receipt.fem_cycle_count,0);
end

function testDuplicateReceiptPreservesBytes(testCase)
[lock, measured] = localFixture(testCase.TestData.root);
receiptPath = fullfile(testCase.TestData.root,'duplicate.json');
sentinel = uint8('unchanged');
localWriteBytes(receiptPath,sentinel);
lockPath = localWriteLock(testCase.TestData.root,'duplicate-lock.json',lock);
verifyError(testCase,@() run_toy_road_runtime_diagnostic( ...
    lockPath,receiptPath,measured),'MATLAB:Java:GenericException');
verifyEqual(testCase,localReadBytes(receiptPath),sentinel);
end

function testPathMismatchNamesPredicate(testCase)
[lock, measured] = localFixture(testCase.TestData.root);
measured.matlab.absolute_path_order{1} = fullfile(testCase.TestData.root,'wrong');
receiptPath = fullfile(testCase.TestData.root,'path-fail.json');
lockPath = localWriteLock(testCase.TestData.root,'path-lock.json',lock);
verifyError(testCase,@() run_toy_road_runtime_diagnostic( ...
    lockPath,receiptPath,measured),'toyRoadD1:PredicateFailed');
receipt = jsondecode(fileread(receiptPath));
verifyEqual(testCase,receipt.first_failed_predicate,'matlab_path_prefix');
verifyEqual(testCase,receipt.path_diagnostic.first_path_mismatch_index,1);
verifyEqual(testCase,receipt.predicates(end).name,'matlab_path_prefix');
verifyFalse(testCase,receipt.predicates(end).pass);
verifyEqual(testCase,receipt.matlab_exception.identifier,'toyRoadD1:PredicateFailed');
end

function testBinaryHashMismatchNamesPredicate(testCase)
[lock, measured] = localFixture(testCase.TestData.root);
measured.binaries.initial.sha256 = repmat('f',1,64);
receiptPath = fullfile(testCase.TestData.root,'binary-fail.json');
lockPath = localWriteLock(testCase.TestData.root,'binary-lock.json',lock);
verifyError(testCase,@() run_toy_road_runtime_diagnostic( ...
    lockPath,receiptPath,measured),'toyRoadD1:PredicateFailed');
receipt = jsondecode(fileread(receiptPath));
verifyEqual(testCase,receipt.first_failed_predicate,'binary_initial_sha256');
verifyEqual(testCase,receipt.binary_diagnostic.initial.sha256,repmat('f',1,64));
verifyEqual(testCase,receipt.predicates(end).name,'binary_initial_sha256');
verifyFalse(testCase,receipt.predicates(end).pass);
end

function testMissingBinaryRecordsResolutionFailure(testCase)
[lock, measured] = localFixture(testCase.TestData.root);
measured.binaries.initial.which_all = {};
measured.binaries.initial.selected_path = '';
measured.binaries.initial.readable = false;
measured.binaries.initial.sha256 = '';
receiptPath = fullfile(testCase.TestData.root,'missing-binary.json');
lockPath = localWriteLock(testCase.TestData.root,'missing-lock.json',lock);
verifyError(testCase,@() run_toy_road_runtime_diagnostic( ...
    lockPath,receiptPath,measured),'toyRoadD1:PredicateFailed');
receipt = jsondecode(fileread(receiptPath));
verifyEqual(testCase,receipt.first_failed_predicate,'binary_initial_resolved');
end

function setup(testCase)
root = tempname;
mkdir(root);
testCase.TestData.root = root;
setenv('TOY_ROAD_D1_TEST_ONLY','true');
end

function teardown(testCase)
setenv('TOY_ROAD_D1_TEST_ONLY','');
if isfolder(testCase.TestData.root)
    rmdir(testCase.TestData.root,'s');
end
end

function [lock, measured] = localFixture(root)
paths = {fullfile(root,'overlay'),fullfile(root,'handoff')};
matlabIdentity = struct('release','R2025b','update','Update 5', ...
    'version','25.2.0','computer','PCWIN64','executable_sha256',repmat('1',1,64), ...
    'blas','BLAS','lapack','LAPACK','absolute_path_order',{paths}, ...
    'path_raw',strjoin(paths,pathsep));
binaryHashes = struct('initial',repmat('2',1,64),'AMOR',repmat('3',1,64), ...
    'AT1_HISTORY_FATIGUE',repmat('4',1,64),'cholmod2',repmat('5',1,64));
lock = struct('schema_version','toy_road_runtime_diagnostic_lock_v1', ...
    'authorization_scope','diagnostic_only_non_authorizing', ...
    'producer_entrypoint_authorized',false, ...
    'runtime_expectations',struct('matlab',rmfield(matlabIdentity,'path_raw'), ...
    'binary_sha256',binaryHashes));
measured = struct('matlab',matlabIdentity,'binaries',struct);
names = fieldnames(binaryHashes);
for index = 1:numel(names)
    name = names{index};
    selected = fullfile(root,[name '.mexw64']);
    measured.binaries.(name) = struct('which_all',{{selected}}, ...
        'selected_path',selected,'readable',true,'sha256',binaryHashes.(name));
end
end

function path = localWriteLock(root,name,value)
path = fullfile(root,name);
localWriteBytes(path,unicode2native(jsonencode(value),'UTF-8'));
end

function localWriteBytes(path,bytes)
fileId = fopen(path,'wb');
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId,bytes,'uint8');
end

function bytes = localReadBytes(path)
fileId = fopen(path,'rb');
cleanup = onCleanup(@() fclose(fileId));
bytes = fread(fileId,Inf,'*uint8').';
end
