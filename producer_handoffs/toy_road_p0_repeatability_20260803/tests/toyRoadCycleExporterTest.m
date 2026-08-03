function tests = toyRoadCycleExporterTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
producerDir = fileparts(fileparts(mfilename('fullpath')));
addpath(producerDir);
testCase.TestData.producerDir = producerDir;
testCase.addTeardown(@() rmpath(producerDir));
end

function testRejectsReorderedOrdinal(testCase)
capture = emptyCapture();
verifyError(testCase, @() captureFixtureSubstep(capture, 2), ...
    'toyRoadP0:InvalidCycleCapture');
end

function testCommitCallbackRunsExactlyOnceAndReturnsPostHistory(testCase)
capture = emptyCapture();
count = java.util.concurrent.atomic.AtomicInteger(0);
[capture, historyPost] = captureFixtureSubstep(capture, 1, count);

verifyEqual(testCase, count.get(), 1);
verifyEqual(testCase, historyPost, historyIncrement());
verifyEqual(testCase, capture.alpha_bar_gp(:,:,1), historyPost);
verifyEqual(testCase, capture.f_alpha_gp(:,:,1), carrara(historyPost));
end

function testRejectsDuplicateAndReplayedCommitToken(testCase)
staleCapture = emptyCapture();
count = java.util.concurrent.atomic.AtomicInteger(0);
[capture, ~] = captureFixtureSubstep(staleCapture, 1, count);

verifyError(testCase, @() captureFixtureSubstep(capture, 1, count), ...
    'toyRoadP0:InvalidCycleCapture');
verifyError(testCase, @() captureFixtureSubstep(staleCapture, 1, count), ...
    'toyRoadP0:InvalidCycleCapture');
verifyEqual(testCase, count.get(), 1);
end

function testFailedCommitConsumesSingleUseToken(testCase)
staleCapture = emptyCapture();
failedCount = java.util.concurrent.atomic.AtomicInteger(0);
[dNode, raw, historyPre] = substepInputs(1);
failingCommit = @(pre, snapshot) failCommit(pre, snapshot, failedCount);
verifyError(testCase, @() capture_toy_road_substep(staleCapture, 1, ...
    dNode, raw, historyPre, failingCommit), 'toyRoadTest:CommitFailure');

retryCount = java.util.concurrent.atomic.AtomicInteger(0);
verifyError(testCase, @() captureFixtureSubstep(staleCapture, 1, retryCount), ...
    'toyRoadP0:InvalidCycleCapture');
verifyEqual(testCase, failedCount.get(), 1);
verifyEqual(testCase, retryCount.get(), 0);
end

function testRawSnapshotExistsBeforeCallbackMutatesSource(testCase)
capture = emptyCapture();
[dNode, rawSource, historyPre] = substepInputs(1);
expectedRaw = rawSource;
callbackCount = 0;

    function historyPost = commitAndMutate(pre, snapshot)
        callbackCount = callbackCount + 1;
        verifyEqual(testCase, snapshot.psi_raw_gp, expectedRaw);
        verifyEqual(testCase, snapshot.history_pre, pre);
        rawSource(:) = 999;
        historyPost = pre + historyIncrement();
    end

[capture, ~] = capture_toy_road_substep(capture, 1, dNode, rawSource, ...
    historyPre, @commitAndMutate);
verifyEqual(testCase, callbackCount, 1);
verifyEqual(testCase, rawSource, 999 * ones(size(rawSource)));
verifyEqual(testCase, capture.psi_raw_gp(:,:,1), expectedRaw);
end

function testInitRejectsReorderedConnectivityWithRefreshedSelfDigest(testCase)
[mesh, state0] = fixtureMeshAndState();
mesh.connectivity(1,:) = mesh.connectivity(1,[2 1 3 4]);
mesh.connectivity_sha256 = connectivitySha256(mesh.connectivity);
verifyError(testCase, @() init_toy_road_cycle_capture( ...
    1, [], state0, mesh, fixtureContract()), 'toyRoadP0:InvalidCycleCapture');
end

function testInitRejectsAlteredNodeCoordinates(testCase)
[mesh, state0] = fixtureMeshAndState();
mesh.node_coords(1,1) = mesh.node_coords(1,1) + 0.125;
verifyError(testCase, @() init_toy_road_cycle_capture( ...
    1, [], state0, mesh, fixtureContract()), 'toyRoadP0:InvalidCycleCapture');
end

function testInitRejectsNondoubleNodeCoordinates(testCase)
[mesh, state0] = fixtureMeshAndState();
mesh.node_coords = single(mesh.node_coords);
verifyError(testCase, @() init_toy_road_cycle_capture( ...
    1, [], state0, mesh, fixtureContract()), 'toyRoadP0:InvalidCycleCapture');
end

function testInitRejectsNonfiniteNodeCoordinates(testCase)
[mesh, state0] = fixtureMeshAndState();
mesh.node_coords(1,1) = NaN;
verifyError(testCase, @() init_toy_road_cycle_capture( ...
    1, [], state0, mesh, fixtureContract()), 'toyRoadP0:InvalidCycleCapture');
end

function testInitRejectsNonQ4Connectivity(testCase)
[mesh, state0] = fixtureMeshAndState();
mesh.connectivity(1,4) = mesh.connectivity(1,3);
mesh.connectivity_sha256 = connectivitySha256(mesh.connectivity);
verifyError(testCase, @() init_toy_road_cycle_capture( ...
    1, [], state0, mesh, fixtureContract()), 'toyRoadP0:InvalidCycleCapture');
end

function testInitRejectsWrongLockedGpOrdering(testCase)
[mesh, state0] = fixtureMeshAndState();
mesh.gp_ordering_id = 'row_permuted_gp_order';
verifyError(testCase, @() init_toy_road_cycle_capture( ...
    1, [], state0, mesh, fixtureContract()), 'toyRoadP0:InvalidCycleCapture');
end

function testSubstepsUseBoundConnectivityAndCanonicalQ4Operator(testCase)
[mesh, state0] = fixtureMeshAndState();
capture = init_toy_road_cycle_capture(1, [], state0, mesh, fixtureContract());
mesh.connectivity = fliplr(mesh.connectivity);
[dNode, raw, historyPre] = substepInputs(1);
[capture, ~] = capture_toy_road_substep(capture, 1, dNode, raw, historyPre, ...
    fixtureCommitCallback(1, java.util.concurrent.atomic.AtomicInteger(0)));

expected = (canonicalQ4ShapeOperator() * ...
    reshape(dNode([1:4; 5:8]), 2, 4).').';
verifyEqual(testCase, capture.d_gp(:,:,1), expected, 'AbsTol', 1e-12);
verifyEqual(testCase, nargin('capture_toy_road_substep'), 6);
end

function testRefusesIncompleteCaptureWithoutPublishing(testCase)
[capture, ~] = captureFixtureSubstep(emptyCapture(), 1);
root = freshRoot(testCase);
verifyError(testCase, @() export_toy_road_cycle_shard( ...
    capture, root, fixtureContract()), 'toyRoadP0:InvalidCycleCapture');
verifyFalse(testCase, isfolder(root));
end

function testInvalidShardIsValidatedBeforeSave(testCase)
capture = filledCaptureWithNonCommutingGpMeans();
capture.psi_raw_gp(1,1,3) = -1;
root = freshRoot(testCase);
verifyError(testCase, @() export_toy_road_cycle_shard( ...
    capture, root, fixtureContract()), 'toyRoadP0:InvalidCycleShard');
verifyFalse(testCase, isfolder(root));
end

function testPeakActiveUsesSimultaneousSubstepFourProduct(testCase)
capture = filledCaptureWithNonCommutingGpMeans();
root = freshRoot(testCase);
shard = export_toy_road_cycle_shard(capture, root, fixtureContract());
verifyEqual(testCase, shard.psi_active_gp(:,:,4), ...
    shard.g_gp(:,:,4).*shard.psi_raw_gp(:,:,4), 'AbsTol', 1e-12);
verifyNotEqual(testCase, mean(shard.psi_active_gp(:,:,4),2), ...
    mean(shard.g_gp(:,:,4),2).*mean(shard.psi_raw_gp(:,:,4),2));
end

function testCycleMaximumRemainsSeparateFromPeakActive(testCase)
capture = filledCaptureWithNonCommutingGpMeans();
capture.psi_raw_gp(1,1,2) = capture.psi_raw_gp(1,1,4) + 10;
root = freshRoot(testCase);
shard = export_toy_road_cycle_shard(capture, root, fixtureContract());
verifyEqual(testCase, shard.psi_raw_cyclemax_gp, ...
    max(shard.psi_raw_gp, [], 3), 'AbsTol', 1e-12);
verifyNotEqual(testCase, shard.psi_raw_cyclemax_gp, shard.psi_raw_gp(:,:,4));
end

function testPublishesExactV73SchemaAndCompactPeakReference(testCase)
capture = filledCaptureWithNonCommutingGpMeans();
root = freshRoot(testCase);
[shard, peak] = export_toy_road_cycle_shard(capture, root, fixtureContract());
path = fullfile(root, 'substeps', 'cycle_0001.mat');

verifyTrue(testCase, isfile(path));
verifyEqual(testCase, fieldnames(shard), requiredShardFields());
verifyEqual(testCase, peak.cycle_shard, 'substeps/cycle_0001.mat');
verifyEqual(testCase, peak.cycle_shard_sha256, fileSha256(path));
verifyEqual(testCase, peak.peak_substep_ordinal, 4);
verifyEqual(testCase, fieldnames(peak.field_slices), ...
    {'field';'substep_dimension';'substep_index'});
verifyFalse(testCase, any(ismember(fieldnames(peak), ...
    {'d_node','d_gp','alpha_bar_gp','f_alpha_gp','psi_raw_gp','g_gp','psi_active_gp'})));
verifyEqual(testCase, h5HeaderOffset(path), 512);
end

function testApprovedReaderRestoresCanonicalShapesTypesAndOrder(testCase)
capture = filledCaptureWithNonCommutingGpMeans();
root = freshRoot(testCase);
export_toy_road_cycle_shard(capture, root, fixtureContract());
assertPythonReader(testCase, root);
end

function testSingleNumericAndStringContractCanonicalizeForReader(testCase)
contract = fixtureContract();
contract.eta = single(contract.eta);
contract.alpha_T = single(contract.alpha_T);
contract.p = single(contract.p);
textFields = {'mesh_sha256','element_ordering_id','gp_ordering_id', ...
    'state_semantics_id','runtime_lock_sha256','family_contract_sha256', ...
    'case_physics_contract_sha256','execution_input_lock_sha256'};
for index = 1:numel(textFields)
    contract.(textFields{index}) = string(contract.(textFields{index}));
end
capture = filledCaptureWithNonCommutingGpMeans(contract);
root = freshRoot(testCase);
shard = export_toy_road_cycle_shard(capture, root, contract);

numericFields = {'cycle','d_node','d_gp','alpha_bar_gp','f_alpha_gp', ...
    'psi_raw_gp','g_gp','psi_active_gp','psi_raw_cyclemax_gp', ...
    'substep_ordinal','load_factor','raw_step_zero_based'};
for index = 1:numel(numericFields)
    verifyClass(testCase, shard.(numericFields{index}), 'double');
end
for index = 1:numel(textFields)
    verifyTrue(testCase, ischar(shard.(textFields{index})) && ...
        isrow(shard.(textFields{index})));
end
assertPythonReader(testCase, root);
end

function testAfterTempCollisionPreservesFirstBytesAndCleansTemp(testCase)
capture = filledCaptureWithNonCommutingGpMeans();
root = freshRoot(testCase);
sentinel = uint8('first-publisher-bytes');
contract = fixtureContract();
contract.test_only_before_publish_hook = ...
    @(finalPath, temporaryPath) createCollision(finalPath, temporaryPath, sentinel);

verifyError(testCase, @() export_toy_road_cycle_shard(capture, root, contract), ...
    'toyRoadP0:PublicationClobber');
finalPath = fullfile(root, 'substeps', 'cycle_0001.mat');
verifyEqual(testCase, readFileBytes(finalPath), sentinel);
verifyEqual(testCase, publishedFiles(root), {'cycle_0001.mat'});
end

function testAfterTempFailureCleansTemporaryFile(testCase)
capture = filledCaptureWithNonCommutingGpMeans();
root = freshRoot(testCase);
contract = fixtureContract();
contract.test_only_before_publish_hook = @injectPublishFailure;

verifyError(testCase, @() export_toy_road_cycle_shard(capture, root, contract), ...
    'toyRoadTest:InjectedPublishFailure');
verifyEmpty(testCase, publishedFiles(root));
end

function capture = emptyCapture(varargin)
contract = fixtureContract();
if nargin == 1
    contract = varargin{1};
end
[mesh, state0] = fixtureMeshAndState();
capture = init_toy_road_cycle_capture(1, [], state0, mesh, contract);
end

function capture = filledCaptureWithNonCommutingGpMeans(varargin)
capture = emptyCapture(varargin{:});
for ordinal = 1:5
    [capture, ~] = captureFixtureSubstep(capture, ordinal);
end
end

function [capture, historyPost] = captureFixtureSubstep(capture, ordinal, varargin)
count = java.util.concurrent.atomic.AtomicInteger(0);
if nargin == 3
    count = varargin{1};
end
[dNode, raw, historyPre] = substepInputs(ordinal);
[capture, historyPost] = capture_toy_road_substep(capture, ordinal, ...
    dNode, raw, historyPre, fixtureCommitCallback(ordinal, count));
end

function callback = fixtureCommitCallback(ordinal, count)
callback = @(historyPre, snapshot) fixtureCommit(historyPre, snapshot, ordinal, count);
end

function historyPost = fixtureCommit(historyPre, snapshot, ordinal, count)
count.incrementAndGet();
assert(snapshot.substep_ordinal == ordinal);
assert(isequal(snapshot.history_pre, historyPre));
historyPost = historyPre + historyIncrement();
end

function historyPost = failCommit(~, ~, count)
historyPost = []; %#ok<NASGU>
count.incrementAndGet();
error('toyRoadTest:CommitFailure', 'Injected commit failure.');
end

function [dNode, raw, historyPre] = substepInputs(ordinal)
dNode = 0.01 * ordinal + (0:7).' * 0.001;
raw = ordinal * [1 3 2 5; 7 4 8 6];
historyPre = (ordinal - 1) * historyIncrement();
end

function value = historyIncrement()
value = [0.10 0.11 0.12 0.13; 0.14 0.15 0.16 0.17];
end

function [mesh, state0] = fixtureMeshAndState()
[nodeCoords, connectivity] = canonicalMeshData();
mesh = struct( ...
    'node_coords', nodeCoords, ...
    'connectivity', connectivity, ...
    'connectivity_sha256', connectivitySha256(connectivity), ...
    'mesh_sha256', meshSha256(nodeCoords, connectivity), ...
    'element_ordering_id', 'q4_connectivity_1_based_v1', ...
    'gp_ordering_id', 'q4_2x2_native_order_v1');
state0 = struct('d_node', zeros(8,1), 'alpha_bar_gp', zeros(2,4));
end

function operator = canonicalQ4ShapeOperator()
a = 1 / sqrt(3);
points = [-a -a; a -a; a a; -a a];
operator = zeros(4,4);
for gp = 1:4
    xi = points(gp,1);
    eta = points(gp,2);
    operator(gp,:) = 0.25 * ...
        [(1-xi)*(1-eta), (1+xi)*(1-eta), ...
         (1+xi)*(1+eta), (1-xi)*(1+eta)];
end
end

function value = carrara(alpha)
value = min(1, (1 - ((alpha - 0.5) ./ (alpha + 0.5))).^2);
end

function contract = fixtureContract()
[nodeCoords, connectivity] = canonicalMeshData();
contract = struct('eta',0,'alpha_T',0.5,'p',2, ...
    'mesh_sha256',meshSha256(nodeCoords, connectivity), ...
    'element_ordering_id','q4_connectivity_1_based_v1', ...
    'gp_ordering_id','q4_2x2_native_order_v1', ...
    'state_semantics_id','five_substep_post_commit_history_v1', ...
    'runtime_lock_sha256',repmat('2',1,64), ...
    'family_contract_sha256',repmat('3',1,64), ...
    'case_physics_contract_sha256',repmat('4',1,64), ...
    'execution_input_lock_sha256',repmat('5',1,64));
end

function [nodeCoords, connectivity] = canonicalMeshData()
nodeCoords = [0 0; 1 0; 1 1; 0 1; 2 0; 3 0; 3 1; 2 1];
connectivity = [1:4; 5:8];
end

function names = requiredShardFields()
names = {'cycle'; 'd_node'; 'd_gp'; 'alpha_bar_gp'; 'f_alpha_gp'; ...
    'psi_raw_gp'; 'g_gp'; 'psi_active_gp'; 'psi_raw_cyclemax_gp'; ...
    'substep_ordinal'; 'load_factor'; 'raw_step_zero_based'; 'branch'; ...
    'mesh_sha256'; 'element_ordering_id'; 'gp_ordering_id'; ...
    'state_semantics_id'; 'runtime_lock_sha256'; 'family_contract_sha256'; ...
    'case_physics_contract_sha256'; 'execution_input_lock_sha256'};
end

function digest = connectivitySha256(connectivity)
payload = sprintf('%dx%d:', size(connectivity,1), size(connectivity,2));
payload = [payload sprintf('%d,', connectivity.')];
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(unicode2native(payload, 'UTF-8'));
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end

function digest = meshSha256(nodeCoords, connectivity)
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(typecast(double(nodeCoords(:)), 'uint8'));
hasher.update(typecast(int64(connectivity(:)), 'uint8'));
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end

function root = freshRoot(testCase)
root = tempname;
testCase.addTeardown(@() removeTree(root));
end

function removeTree(root)
if isfolder(root)
    rmdir(root, 's');
end
end

function createCollision(finalPath, temporaryPath, sentinel)
assert(isfile(temporaryPath), 'Reserved temporary shard must exist before hook.');
fileId = fopen(finalPath, 'wb');
assert(fileId >= 0, 'Cannot create collision fixture.');
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, sentinel, 'uint8');
end

function injectPublishFailure(~, temporaryPath)
assert(isfile(temporaryPath), 'Reserved temporary shard must exist before hook.');
error('toyRoadTest:InjectedPublishFailure', 'Injected after-temp publication failure.');
end

function files = publishedFiles(root)
entries = dir(fullfile(root, 'substeps'));
files = sort({entries(~[entries.isdir]).name});
end

function bytes = readFileBytes(path)
fileId = fopen(path, 'rb');
assert(fileId >= 0, 'Cannot read %s.', path);
cleanup = onCleanup(@() fclose(fileId));
bytes = fread(fileId, Inf, '*uint8').';
end

function digest = fileSha256(path)
bytes = readFileBytes(path);
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(bytes);
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end

function offset = h5HeaderOffset(path)
bytes = readFileBytes(path);
signature = uint8([137 72 68 70 13 10 26 10]);
index = strfind(bytes(1:min(520,numel(bytes))), signature);
assert(~isempty(index), 'MAT file does not contain an HDF5 signature.');
offset = index(1) - 1;
end

function assertPythonReader(testCase, root)
path = fullfile(root, 'substeps', 'cycle_0001.mat');
script = fullfile(root, 'assert_reader.py');
writeReaderAssertion(script);
command = sprintf('%s "%s" "%s" "%s"', pythonCommand(), script, ...
    testCase.TestData.producerDir, path);
[status, output] = system(command);
verifyEqual(testCase, status, 0, sprintf('Approved Python reader failed:\n%s', output));
end

function writeReaderAssertion(path)
lines = [
    "from pathlib import Path"
    "import sys"
    "import numpy as np"
    "sys.path.insert(0, sys.argv[1])"
    "from toy_road_protocol import SHARD_FIELDS, read_mat_struct"
    "shard = read_mat_struct(Path(sys.argv[2]), 'shard')"
    "assert set(shard) == SHARD_FIELDS"
    "numeric = {'cycle','d_node','d_gp','alpha_bar_gp','f_alpha_gp','psi_raw_gp','g_gp','psi_active_gp','psi_raw_cyclemax_gp','substep_ordinal','load_factor','raw_step_zero_based'}"
    "for name in numeric: assert isinstance(shard[name], np.ndarray) and shard[name].dtype == np.float64"
    "assert shard['d_node'].shape == (8,5)"
    "for name in ('d_gp','alpha_bar_gp','f_alpha_gp','psi_raw_gp','g_gp','psi_active_gp'): assert shard[name].shape == (2,4,5)"
    "assert shard['psi_raw_cyclemax_gp'].shape == (2,4)"
    "assert np.array_equal(shard['substep_ordinal'], [[1.,2.,3.,4.,5.]])"
    "assert np.array_equal(shard['load_factor'], [[.25,.5,.75,1.,0.]])"
    "assert np.array_equal(shard['raw_step_zero_based'], [[0.,1.,2.,3.,4.]])"
    "assert list(shard['branch'].reshape(-1)) == ['loading']*4 + ['unloading']"
    "expected = np.empty((2,4,5), dtype=np.float64)"
    "base = np.array([[1.,3.,2.,5.],[7.,4.,8.,6.]])"
    "for step in range(5): expected[:,:,step] = (step+1)*base"
    "assert np.array_equal(shard['psi_raw_gp'], expected)"
    "text = {'mesh_sha256','element_ordering_id','gp_ordering_id','state_semantics_id','runtime_lock_sha256','family_contract_sha256','case_physics_contract_sha256','execution_input_lock_sha256'}"
    "for name in text: assert isinstance(shard[name], str)"
    ];
fileId = fopen(path, 'wb');
assert(fileId >= 0, 'Cannot write %s.', path);
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, unicode2native(char(join(lines, newline) + newline), 'UTF-8'), 'uint8');
end

function command = pythonCommand()
configured = getenv('TOY_ROAD_PYTHON');
if ~isempty(configured)
    command = ['"' configured '"'];
elseif ispc
    command = 'py -3.12';
else
    command = 'python3';
end
end
