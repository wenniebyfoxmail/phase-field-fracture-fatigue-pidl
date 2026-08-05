function run_toy_road_runtime_diagnostic(diagnosticLockPath, receiptPath, varargin)
% Record runtime predicates without entering any numerical producer.
receipt = localInitialReceipt();
localWriteCreateNew(receiptPath, receipt);
currentPredicate = 'diagnostic_initialization';
try
    lock = localReadJson(diagnosticLockPath, 'diagnostic lock');
    if isempty(varargin)
        measured = localMeasureRuntime(lock);
    else
        localRequire(numel(varargin) == 1 && isstruct(varargin{1}) && ...
            isscalar(varargin{1}) && strcmp(getenv('TOY_ROAD_D1_TEST_ONLY'), 'true'), ...
            'toyRoadD1:TestAdapterRejected', ...
            'Measurement fixture is accepted only in test-only scope.');
        localRequire(~localContainsFunctionHandle(varargin{1}), ...
            'toyRoadD1:TestAdapterRejected', ...
            'Measurement fixture must contain data only.');
        measured = varargin{1};
    end

    [receipt, currentPredicate] = localAppend(receipt, receiptPath, ...
        'diagnostic_lock_schema', 'toy_road_runtime_diagnostic_lock_v1', ...
        lock.schema_version, char(string(lock.schema_version)), ...
        strcmp(lock.schema_version, 'toy_road_runtime_diagnostic_lock_v1'));
    [receipt, currentPredicate] = localAppend(receipt, receiptPath, ...
        'diagnostic_authorization_scope', 'diagnostic_only_non_authorizing', ...
        lock.authorization_scope, char(string(lock.authorization_scope)), ...
        strcmp(lock.authorization_scope, 'diagnostic_only_non_authorizing'));
    [receipt, currentPredicate] = localAppend(receipt, receiptPath, ...
        'producer_entrypoint_not_authorized', false, ...
        lock.producer_entrypoint_authorized, lock.producer_entrypoint_authorized, ...
        isequal(lock.producer_entrypoint_authorized, false));

    expectedPath = cellstr(string(lock.runtime_expectations.matlab.absolute_path_order));
    actualPath = cellstr(string(measured.matlab.absolute_path_order));
    receipt.path_diagnostic = localPathDiagnostic(expectedPath, actualPath, ...
        measured.matlab.path_raw);
    [receipt, currentPredicate] = localAppend(receipt, receiptPath, ...
        'matlab_path_length', numel(expectedPath), numel(actualPath), ...
        numel(actualPath), numel(actualPath) >= numel(expectedPath));
    pathPass = isempty(receipt.path_diagnostic.first_path_mismatch_index);
    [receipt, currentPredicate] = localAppend(receipt, receiptPath, ...
        'matlab_path_prefix', expectedPath, actualPath(1:min(end,numel(expectedPath))), ...
        receipt.path_diagnostic.index_comparisons, pathPass);

    matlabFields = {'release','update','version','computer', ...
        'executable_sha256','blas','lapack'};
    matlabPredicate = {'matlab_release','matlab_update','matlab_version', ...
        'matlab_computer','matlab_executable_sha256','matlab_blas','matlab_lapack'};
    for index = 1:numel(matlabFields)
        field = matlabFields{index};
        expected = lock.runtime_expectations.matlab.(field);
        raw = measured.matlab.(field);
        normalized = char(string(raw));
        [receipt, currentPredicate] = localAppend(receipt, receiptPath, ...
            matlabPredicate{index}, expected, raw, normalized, ...
            strcmp(char(string(expected)), normalized));
    end

    binaryNames = {'initial','AMOR','AT1_HISTORY_FATIGUE','cholmod2'};
    receipt.binary_diagnostic = struct;
    for index = 1:numel(binaryNames)
        name = binaryNames{index};
        binary = measured.binaries.(name);
        receipt.binary_diagnostic.(name) = binary;
        selected = char(string(binary.selected_path));
        [receipt, currentPredicate] = localAppend(receipt, receiptPath, ...
            ['binary_' name '_resolved'], true, binary.which_all, selected, ...
            ~isempty(selected));
        [receipt, currentPredicate] = localAppend(receipt, receiptPath, ...
            ['binary_' name '_readable'], true, binary.readable, ...
            binary.readable, isequal(binary.readable, true));
        expected = lock.runtime_expectations.binary_sha256.(name);
        measuredSha = char(string(binary.sha256));
        [receipt, currentPredicate] = localAppend(receipt, receiptPath, ...
            ['binary_' name '_sha256'], expected, binary.sha256, measuredSha, ...
            strcmp(expected, measuredSha));
    end

    receipt.status = 'PASS';
    receipt.first_failed_predicate = [];
    receipt.completed_predicate_count = numel(receipt.predicates);
    localAtomicReplace(receiptPath, receipt);
catch exception
    receipt.status = 'FAIL';
    if strcmp(currentPredicate, 'diagnostic_initialization')
        receipt.first_failed_predicate = 'diagnostic_internal_error';
    else
        receipt.first_failed_predicate = currentPredicate;
    end
    receipt.matlab_exception = struct( ...
        'identifier', exception.identifier, ...
        'message', exception.message, ...
        'stack', localStack(exception.stack), ...
        'extended_report', getReport(exception, 'extended', 'hyperlinks', 'off'));
    receipt.completed_predicate_count = numel(receipt.predicates);
    localAtomicReplace(receiptPath, receipt);
    rethrow(exception)
end
end

function receipt = localInitialReceipt()
receipt = struct;
receipt.schema_version = 'toy_road_runtime_diagnostic_v1';
receipt.status = 'IN_PROGRESS';
receipt.authorization_scope = 'diagnostic_only_non_authorizing';
receipt.producer_entrypoint_authorized = false;
receipt.predicates = repmat(struct('ordinal',0,'name','','expected',[], ...
    'measured_raw',[],'measured_normalized',[],'pass',false, ...
    'measured_at_utc',''), 0, 1);
receipt.first_failed_predicate = [];
receipt.producer_invocation_count = 0;
receipt.fem_cycle_count = 0;
receipt.path_diagnostic = struct;
receipt.binary_diagnostic = struct;
receipt.matlab_exception = struct;
receipt.completed_predicate_count = 0;
end

function [receipt, name] = localAppend(receipt, receiptPath, name, expected, raw, normalized, passed)
row = struct('ordinal',numel(receipt.predicates)+1,'name',name, ...
    'expected',expected,'measured_raw',raw,'measured_normalized',normalized, ...
    'pass',logical(passed),'measured_at_utc',localUtcNow());
receipt.predicates(end+1,1) = row;
receipt.completed_predicate_count = numel(receipt.predicates);
if ~passed
    receipt.first_failed_predicate = name;
end
localAtomicReplace(receiptPath, receipt);
if ~passed
    error('toyRoadD1:PredicateFailed', 'D1 runtime predicate failed: %s', name);
end
end

function measured = localMeasureRuntime(lock)
releaseObject = matlabRelease;
measured = struct;
measured.matlab = struct;
measured.matlab.release = char(releaseObject.Release);
measured.matlab.update = localReleaseUpdate(releaseObject.Update);
versionText = version;
measured.matlab.version = regexp(versionText, '^\S+', 'match', 'once');
measured.matlab.computer = computer;
measured.matlab.executable_sha256 = localFileSha256(fullfile(matlabroot,'bin','matlab.exe'));
measured.matlab.blas = version('-blas');
measured.matlab.lapack = version('-lapack');
measured.matlab.path_raw = path;
measured.matlab.absolute_path_order = cellfun(@localCanonicalPath, ...
    strsplit(path,pathsep), 'UniformOutput', false);
names = {'initial','AMOR','AT1_HISTORY_FATIGUE','cholmod2'};
symbols = {'phase_field.mex.fem.assembly.equilibrium.initial', ...
    'phase_field.mex.fem.assembly.equilibrium.AMOR', ...
    'phase_field.mex.fem.assembly.pf.AT1_HISTORY_FATIGUE','cholmod2'};
measured.binaries = struct;
for index = 1:numel(names)
    allPaths = which(symbols{index}, '-all');
    if ischar(allPaths)
        allPaths = cellstr(allPaths);
    end
    if isempty(allPaths)
        selected = '';
        readable = false;
        digest = '';
    else
        allPaths = cellfun(@localCanonicalPath, allPaths, 'UniformOutput', false);
        selected = allPaths{1};
        readable = isfile(selected) && localReadable(selected);
        if readable
            digest = localFileSha256(selected);
        else
            digest = '';
        end
    end
    measured.binaries.(names{index}) = struct('which_all',{allPaths}, ...
        'selected_path',selected,'readable',readable,'sha256',digest);
end
localRequire(isfield(lock,'runtime_expectations'), ...
    'toyRoadD1:InvalidLock', 'Diagnostic lock lacks runtime expectations.');
end

function diagnostic = localPathDiagnostic(expected, actual, raw)
comparisons = repmat(struct('index',0,'expected','','actual','','pass',false), ...
    numel(expected), 1);
firstMismatch = [];
for index = 1:numel(expected)
    expectedValue = localCanonicalPath(expected{index});
    if index <= numel(actual)
        actualValue = localCanonicalPath(actual{index});
    else
        actualValue = '';
    end
    passed = strcmpi(expectedValue, actualValue);
    comparisons(index) = struct('index',index,'expected',expectedValue, ...
        'actual',actualValue,'pass',passed);
    if ~passed && isempty(firstMismatch)
        firstMismatch = index;
    end
end
diagnostic = struct('actual_path_raw',raw, ...
    'expected_path',{cellfun(@localCanonicalPath,expected,'UniformOutput',false)}, ...
    'actual_path',{cellfun(@localCanonicalPath,actual,'UniformOutput',false)}, ...
    'index_comparisons',comparisons, ...
    'extra_actual_entries',{actual(numel(expected)+1:end)}, ...
    'first_path_mismatch_index',firstMismatch);
end

function value = localReadJson(path, label)
localRequire(isfile(path), 'toyRoadD1:MissingInput', [label ' is missing.']);
value = jsondecode(fileread(path));
localRequire(isstruct(value) && isscalar(value), ...
    'toyRoadD1:InvalidInput', [label ' must be one JSON object.']);
end

function localWriteCreateNew(path, value)
options = javaArray('java.nio.file.OpenOption', 2);
options(1) = java.nio.file.StandardOpenOption.CREATE_NEW;
options(2) = java.nio.file.StandardOpenOption.WRITE;
stream = java.nio.file.Files.newOutputStream(java.nio.file.Paths.get(path, ...
    javaArray('java.lang.String',0)), options);
cleanup = onCleanup(@() stream.close());
bytes = unicode2native(jsonencode(value), 'UTF-8');
stream.write(bytes,0,numel(bytes));
stream.flush();
end

function localAtomicReplace(path, value)
parent = char(java.nio.file.Paths.get(path,javaArray('java.lang.String',0)).getParent());
temporary = fullfile(parent, ['.D1_RUNTIME_DIAGNOSTIC.json.' char(java.util.UUID.randomUUID()) '.tmp']);
localWriteCreateNew(temporary, value);
source = java.nio.file.Paths.get(temporary,javaArray('java.lang.String',0));
target = java.nio.file.Paths.get(path,javaArray('java.lang.String',0));
options = javaArray('java.nio.file.CopyOption',2);
options(1) = java.nio.file.StandardCopyOption.ATOMIC_MOVE;
options(2) = java.nio.file.StandardCopyOption.REPLACE_EXISTING;
java.nio.file.Files.move(source,target,options);
end

function output = localStack(input)
output = repmat(struct('file','','name','','line',0),numel(input),1);
for index = 1:numel(input)
    output(index) = struct('file',input(index).file, ...
        'name',input(index).name,'line',input(index).line);
end
end

function passed = localContainsFunctionHandle(value)
if isa(value,'function_handle')
    passed = true;
elseif isstruct(value)
    passed = any(structfun(@localContainsFunctionHandle,value));
elseif iscell(value)
    passed = any(cellfun(@localContainsFunctionHandle,value));
else
    passed = false;
end
end

function output = localCanonicalPath(input)
output = char(java.io.File(char(input)).getCanonicalPath());
end

function passed = localReadable(path)
fileId = fopen(path,'rb');
passed = fileId >= 0;
if passed
    fclose(fileId);
end
end

function digest = localFileSha256(path)
fileId = fopen(path,'rb');
localRequire(fileId >= 0, 'toyRoadD1:UnreadableRuntime', ...
    ['Cannot read runtime file: ' path]);
cleanup = onCleanup(@() fclose(fileId));
bytes = fread(fileId,Inf,'*uint8');
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(bytes);
raw = typecast(hasher.digest(),'uint8');
digits = '0123456789abcdef';
values = double(reshape(raw,1,[]));
encoded = [digits(floor(values/16)+1); digits(mod(values,16)+1)];
digest = builtin('reshape',encoded,1,[]);
end

function output = localReleaseUpdate(input)
if isnumeric(input) && isscalar(input) && isfinite(input)
    output = sprintf('Update %d',input);
else
    output = char(string(input));
    if ~startsWith(output,'Update ')
        output = ['Update ' output];
    end
end
end

function output = localUtcNow()
output = char(datetime('now','TimeZone','UTC', ...
    'Format','yyyy-MM-dd''T''HH:mm:ss.SSSXXX'));
end

function localRequire(condition, identifier, message)
if ~condition
    error(identifier,'%s',message);
end
end
