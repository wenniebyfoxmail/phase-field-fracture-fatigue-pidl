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

function testRejectsDuplicateOrdinal(testCase)
capture = captureFixtureSubstep(emptyCapture(), 1);
verifyError(testCase, @() captureFixtureSubstep(capture, 1), ...
    'toyRoadP0:InvalidCycleCapture');
end

function testCapturesRawPreMutationAndPostCommitHistory(testCase)
capture = emptyCapture();
[dNode, raw, historyPre, historyPost, exportedHistory, fAlpha, ...
    connectivity, shapeFunctions] = substepInputs(1);
expectedRaw = raw;
expectedPost = historyPost;
expectedFatigue = fAlpha;

capture = capture_toy_road_substep(capture, 1, dNode, raw, ...
    historyPre, historyPost, exportedHistory, fAlpha, connectivity, shapeFunctions);
expectedDGp = (shapeFunctions * reshape(dNode(connectivity), 2, 4).').';
raw(:) = 999;
historyPost(:) = 999;
exportedHistory(:) = 999;
fAlpha(:) = 999;

verifyEqual(testCase, capture.psi_raw_gp(:,:,1), expectedRaw);
verifyEqual(testCase, capture.d_gp(:,:,1), expectedDGp, 'AbsTol', 1e-12);
verifyEqual(testCase, capture.alpha_bar_gp(:,:,1), expectedPost);
verifyEqual(testCase, capture.f_alpha_gp(:,:,1), expectedFatigue);
verifyNotEqual(testCase, capture.psi_raw_gp(:,:,1), raw);
verifyNotEqual(testCase, capture.alpha_bar_gp(:,:,1), historyPost);
verifyNotEqual(testCase, capture.alpha_bar_gp(:,:,1), exportedHistory);
verifyNotEqual(testCase, capture.f_alpha_gp(:,:,1), fAlpha);
verifyNotEqual(testCase, capture.alpha_bar_gp(:,:,1), historyPre);
end

function testRejectsPreCommitHistoryAsExportedSlice(testCase)
capture = emptyCapture();
[dNode, raw, historyPre, historyPost, ~, fAlpha, connectivity, shapeFunctions] = ...
    substepInputs(1);
verifyError(testCase, @() capture_toy_road_substep(capture, 1, dNode, raw, ...
    historyPre, historyPost, historyPre, fAlpha, connectivity, shapeFunctions), ...
    'toyRoadP0:InvalidCycleCapture');
end

function testRefusesIncompleteCaptureWithoutPublishing(testCase)
capture = captureFixtureSubstep(emptyCapture(), 1);
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
verifyEqual(testCase, shard.psi_active_gp(:,:,4), ...
    shard.g_gp(:,:,4).*shard.psi_raw_gp(:,:,4), 'AbsTol', 1e-12);
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
verifyEqual(testCase, {peak.field_slices.field}, ...
    {'d_node','d_gp','alpha_bar_gp','f_alpha_gp','psi_raw_gp','g_gp','psi_active_gp'});
verifyFalse(testCase, any(ismember(fieldnames(peak), ...
    {'d_node','d_gp','alpha_bar_gp','f_alpha_gp','psi_raw_gp','g_gp','psi_active_gp'})));

loaded = load(path, 'shard');
verifyEqual(testCase, loaded.shard, shard);
verifyEqual(testCase, h5HeaderOffset(path), 512);
end

function testPythonApprovedReaderRestoresShapesTypesAndOrder(testCase)
capture = filledCaptureWithNonCommutingGpMeans();
root = freshRoot(testCase);
export_toy_road_cycle_shard(capture, root, fixtureContract());
path = fullfile(root, 'substeps', 'cycle_0001.mat');
script = fullfile(root, 'assert_reader.py');
writeReaderAssertion(script);
python = pythonCommand();
command = sprintf('%s "%s" "%s" "%s"', python, script, ...
    testCase.TestData.producerDir, path);
[status, output] = system(command);
verifyEqual(testCase, status, 0, sprintf('Approved Python reader failed:\n%s', output));
end

function testNoClobberPreservesExistingShardAndCleansTemporary(testCase)
capture = filledCaptureWithNonCommutingGpMeans();
root = freshRoot(testCase);
export_toy_road_cycle_shard(capture, root, fixtureContract());
path = fullfile(root, 'substeps', 'cycle_0001.mat');
before = fileSha256(path);

verifyError(testCase, @() export_toy_road_cycle_shard( ...
    capture, root, fixtureContract()), 'toyRoadP0:PublicationClobber');
verifyEqual(testCase, fileSha256(path), before);
entries = dir(fullfile(root, 'substeps'));
verifyEqual(testCase, sort({entries(~[entries.isdir]).name}), {'cycle_0001.mat'});
end

function capture = emptyCapture()
[~, ~, state0] = fixtureState();
capture = init_toy_road_cycle_capture(1, [], state0);
end

function capture = filledCaptureWithNonCommutingGpMeans()
capture = emptyCapture();
for ordinal = 1:5
    capture = captureFixtureSubstep(capture, ordinal);
end
end

function capture = captureFixtureSubstep(capture, ordinal)
[dNode, raw, historyPre, historyPost, exportedHistory, fAlpha, ...
    connectivity, shapeFunctions] = substepInputs(ordinal);
capture = capture_toy_road_substep(capture, ordinal, dNode, raw, ...
    historyPre, historyPost, exportedHistory, fAlpha, connectivity, shapeFunctions);
end

function [dNode, raw, historyPre, historyPost, exportedHistory, fAlpha, ...
    connectivity, shapeFunctions] = substepInputs(ordinal)
[connectivity, shapeFunctions, state0] = fixtureState();
dNode = 0.01 * ordinal + (0:7).' * 0.001;
raw = ordinal * [1 3 2 5; 7 4 8 6];
historyIncrement = [0.10 0.11 0.12 0.13; 0.14 0.15 0.16 0.17];
historyPre = state0.alpha_bar_gp + (ordinal - 1) * historyIncrement;
historyPost = state0.alpha_bar_gp + ordinal * historyIncrement;
exportedHistory = historyPost;
fAlpha = carrara(historyPost);
end

function [connectivity, shapeFunctions, state0] = fixtureState()
connectivity = [1:4; 5:8];
a = 1 / sqrt(3);
points = [-a -a; a -a; a a; -a a];
shapeFunctions = zeros(4,4);
for gp = 1:4
    xi = points(gp,1);
    eta = points(gp,2);
    shapeFunctions(gp,:) = 0.25 * ...
        [(1-xi)*(1-eta), (1+xi)*(1-eta), ...
         (1+xi)*(1+eta), (1-xi)*(1+eta)];
end
state0 = struct('d_node', zeros(8,1), 'alpha_bar_gp', zeros(2,4));
end

function value = carrara(alpha)
value = min(1, (1 - ((alpha - 0.5) ./ (alpha + 0.5))).^2);
end

function contract = fixtureContract()
contract = struct('eta',0,'alpha_T',0.5,'p',2, ...
    'mesh_sha256',repmat('1',1,64), ...
    'element_ordering_id','q4_connectivity_1_based_v1', ...
    'gp_ordering_id','q4_2x2_native_order_v1', ...
    'state_semantics_id','five_substep_post_commit_history_v1', ...
    'runtime_lock_sha256',repmat('2',1,64), ...
    'family_contract_sha256',repmat('3',1,64), ...
    'case_physics_contract_sha256',repmat('4',1,64), ...
    'execution_input_lock_sha256',repmat('5',1,64));
end

function names = requiredShardFields()
names = {'cycle'; 'd_node'; 'd_gp'; 'alpha_bar_gp'; 'f_alpha_gp'; ...
    'psi_raw_gp'; 'g_gp'; 'psi_active_gp'; 'psi_raw_cyclemax_gp'; ...
    'substep_ordinal'; 'load_factor'; 'raw_step_zero_based'; 'branch'; ...
    'mesh_sha256'; 'element_ordering_id'; 'gp_ordering_id'; ...
    'state_semantics_id'; 'runtime_lock_sha256'; 'family_contract_sha256'; ...
    'case_physics_contract_sha256'; 'execution_input_lock_sha256'};
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

function digest = fileSha256(path)
fileId = fopen(path, 'rb');
assert(fileId >= 0, 'Cannot read %s.', path);
cleanup = onCleanup(@() fclose(fileId));
bytes = fread(fileId, Inf, '*uint8');
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(bytes);
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end

function offset = h5HeaderOffset(path)
fileId = fopen(path, 'rb');
assert(fileId >= 0, 'Cannot read %s.', path);
cleanup = onCleanup(@() fclose(fileId));
bytes = fread(fileId, 520, '*uint8').';
signature = uint8([137 72 68 70 13 10 26 10]);
index = strfind(bytes, signature);
assert(~isempty(index), 'MAT file does not contain an HDF5 signature.');
offset = index(1) - 1;
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
    "assert shard['d_node'].shape == (8, 5)"
    "for name in ('d_gp','alpha_bar_gp','f_alpha_gp','psi_raw_gp','g_gp','psi_active_gp'):"
    "    assert shard[name].shape == (2, 4, 5)"
    "    assert shard[name].dtype == np.float64"
    "assert shard['psi_raw_cyclemax_gp'].shape == (2, 4)"
    "assert shard['substep_ordinal'].shape == (1, 5)"
    "assert np.array_equal(shard['substep_ordinal'], [[1.,2.,3.,4.,5.]])"
    "assert np.array_equal(shard['load_factor'], [[.25,.5,.75,1.,0.]])"
    "assert np.array_equal(shard['raw_step_zero_based'], [[0.,1.,2.,3.,4.]])"
    "assert list(shard['branch'].reshape(-1)) == ['loading']*4 + ['unloading']"
    "expected = np.empty((2,4,5), dtype=np.float64)"
    "base = np.array([[1.,3.,2.,5.],[7.,4.,8.,6.]])"
    "for step in range(5): expected[:,:,step] = (step+1)*base"
    "assert np.array_equal(shard['psi_raw_gp'], expected)"
    "assert isinstance(shard['mesh_sha256'], str)"
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
