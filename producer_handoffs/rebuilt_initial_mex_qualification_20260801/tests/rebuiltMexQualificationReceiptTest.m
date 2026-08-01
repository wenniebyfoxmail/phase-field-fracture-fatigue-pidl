function tests = rebuiltMexQualificationReceiptTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
handoff = fileparts(fileparts(mfilename('fullpath')));
addpath(handoff);
testCase.addTeardown(@() rmpath(handoff));
end

function testWellFormedControlledArtifactsProduceBoundReceipt(testCase)
fixture = qualificationFixture(testCase);
receipt = validateFixture(fixture);
verifyTrue(testCase, receipt.passed);
verifyEqual(testCase, receipt.runtime_initial_sha256, approvedHash());
verifyEqual(testCase, receipt.source_commit, fixture.sourceCommit);
verifyEqual(testCase, receipt.runtime_lock_sha256, fileHash(fixture.runtimeLock));
verifyEqual(testCase, receipt.q1_receipt_sha256, ...
    fileHash(fullfile(fixture.root, 'Q1', 'Q1_RECEIPT.json')));
verifyEqual(testCase, receipt.q2_receipt_sha256, ...
    fileHash(fullfile(fixture.root, 'Q2', 'Q2_RESULT.json')));
verifyEqual(testCase, receipt.parent_lock_sha256, fileHash(fixture.parentLock));
verifyEqual(testCase, receipt.mesh_ordering_sha256, fixture.meshHash);
end

function testRejectsNoncanonicalRuntimeLockEvenWithIdenticalBytes(testCase)
fixture = qualificationFixture(testCase);
copiedLock = fullfile(fixture.root, 'RUNTIME_LOCK.json');
copyfile(fixture.runtimeLock, copiedLock);
fixture.runtimeLock = copiedLock;
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:NoncanonicalRuntimeLock');
end

function testRejectsArbitraryTextMatEvenWhenRehashed(testCase)
fixture = qualificationFixture(testCase);
metricsPath = fullfile(fixture.root, 'Q2', 'Q2_METRICS.mat');
writeBytes(metricsPath, uint8('not a MAT file'));
rehashQ2Artifact(fixture, 'metrics', metricsPath);
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:InvalidMatArtifact');
end

function testRejectsRehashedFakeStateAndTerminalIdentity(testCase)
fixture = qualificationFixture(testCase);
statePath = fullfile(fixture.root, 'Q2', 'Q2_CYCLE1_STATE.mat');
state = load(statePath);
state.runtime_initial_sha256 = repmat('9', 1, 64);
save(statePath, '-struct', 'state', '-v7.3');
rehashQ2Artifact(fixture, 'state', statePath);
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:ArtifactIdentityMismatch');
end

function testRejectsQ1ThresholdOrEmbeddedMetricMismatch(testCase)
fixture = qualificationFixture(testCase);
metricsPath = fullfile(fixture.root, 'Q1', 'Q1_METRICS.mat');
loaded = load(metricsPath, 'metrics');
loaded.metrics.probe.threshold = 1e-6;
save(metricsPath, '-struct', 'loaded', '-v7.3');
rehashQ1(fixture, loaded.metrics);
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:MetricContractMismatch');

fixture = qualificationFixture(testCase);
q2Path = fullfile(fixture.root, 'Q2', 'Q2_RESULT.json');
q2 = jsondecode(fileread(q2Path));
q2.metrics.fields.active.passed = false;
writeJsonReplace(q2Path, q2);
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:MetricContractMismatch');
end

function testMissingFailedAndBlockedReceiptsFailClosed(testCase)
fixture = qualificationFixture(testCase);
delete(fullfile(fixture.root, 'Q1', 'Q1_RECEIPT.json'));
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:MissingQ1');

fixture = qualificationFixture(testCase);
q2Path = fullfile(fixture.root, 'Q2', 'Q2_RESULT.json');
q2 = jsondecode(fileread(q2Path));
q2.status = 'blocked'; q2.passed = false;
q2.blockers = {'blocked_missing_parent_active_field'};
writeJsonReplace(q2Path, q2);
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:Q2Blocked');
end

function testNoClobberPublication(testCase)
fixture = qualificationFixture(testCase);
outputPath = fullfile(fixture.root, 'FAMILY_QUALIFICATION_RECEIPT.json');
validateFixture(fixture, outputPath);
verifyTrue(testCase, isfile(outputPath));
verifyError(testCase, @() validateFixture(fixture, outputPath), ...
    'rebuiltMexQualification:OutputExists');
end

function receipt = validateFixture(fixture, outputPath)
arguments
    fixture
    outputPath = ''
end
receipt = validate_qualification_receipts(fixture.root, ...
    fixture.runtimeLock, fixture.runtimeRoot, fixture.sourceRoot, ...
    fixture.q2Lock, fixture.parentLock, outputPath);
end

function fixture = qualificationFixture(testCase)
folder = matlab.unittest.fixtures.TemporaryFolderFixture;
testCase.applyFixture(folder);
root = fullfile(folder.Folder, char(java.util.UUID.randomUUID));
mkdir(fullfile(root, 'Q1')); mkdir(fullfile(root, 'Q2'));
handoff = fileparts(fileparts(mfilename('fullpath')));
runtimeLock = fullfile(handoff, 'RUNTIME_LOCK.json');
runtimeRoot = fullfile(handoff, 'runtime');
sourceRoot = 'C:/q4diag/griphfith-f1b-355d4c83';
q2Lock = fullfile(handoff, 'Q2_INPUT_LOCK.json');
sourceCommit = '355d4c83fefc2db88c32031a2dd2623b3de85c89';
meshHash = repmat('d', 1, 64);
parentLock = fullfile(root, 'PARENT_LOCK.json');
writeJson(parentLock, struct('schema_version', 'parent_lock_fixture'));
runtimeHash = fileHash(runtimeLock);
q2LockHash = fileHash(q2Lock);
parentHash = fileHash(parentLock);

metrics = q1Metrics();
save(fullfile(root, 'Q1', 'Q1_METRICS.mat'), 'metrics', '-v7.3');
q1MetricsHash = fileHash(fullfile(root, 'Q1', 'Q1_METRICS.mat'));
q1Result = struct('schema_version', 'rebuilt_initial_mex_q1_result_v1', ...
    'passed', true, 'input_sha256', repmat('8', 1, 64), ...
    'runtime_lock_sha256', runtimeHash, ...
    'runtime_initial_sha256', approvedHash(), 'source_commit', sourceCommit, ...
    'metrics_sha256', q1MetricsHash);
writeJson(fullfile(root, 'Q1', 'Q1_RESULT.json'), q1Result);
q1Receipt = struct('schema_version', ...
    'rebuilt_initial_mex_q1_receipt_v1', 'passed', true, ...
    'input_sha256', q1Result.input_sha256, ...
    'runtime_lock_sha256', runtimeHash, ...
    'runtime_initial_sha256', approvedHash(), 'source_commit', sourceCommit, ...
    'source_clean', true, 'metrics', metrics, ...
    'metrics_sha256', q1MetricsHash, ...
    'result_sha256', fileHash(fullfile(root, 'Q1', 'Q1_RESULT.json')));
writeJson(fullfile(root, 'Q1', 'Q1_RECEIPT.json'), q1Receipt);

identity = struct('runtime_lock_sha256', runtimeHash, ...
    'runtime_initial_sha256', approvedHash(), 'source_commit', sourceCommit, ...
    'q2_input_lock_sha256', q2LockHash, 'parent_lock_sha256', parentHash, ...
    'parent_cycle1_sha256', repmat('5', 1, 64), ...
    'mask_set_sha256', repmat('7', 1, 64), ...
    'mesh_ordering_sha256', meshHash, ...
    'replay_source_mesh_sha256', meshHash, ...
    'parent_vtk_mesh_sha256', repmat('6', 1, 64));
state = q2State(identity);
save(fullfile(root, 'Q2', 'Q2_CYCLE1_STATE.mat'), '-struct', 'state', '-v7.3');
terminal = q2Terminal(identity);
writeJson(fullfile(root, 'Q2', 'Q2_CYCLE1_TERMINAL.json'), terminal);
metrics = q2Metrics(identity);
save(fullfile(root, 'Q2', 'Q2_METRICS.mat'), 'metrics', '-v7.3');
mask_artifact = q2Masks(identity);
save(fullfile(root, 'Q2', 'Q2_PARENT_MASKS.mat'), 'mask_artifact', '-v7.3');
artifacts = struct( ...
    'state', artifact(root, 'Q2_CYCLE1_STATE.mat'), ...
    'terminal', artifact(root, 'Q2_CYCLE1_TERMINAL.json'), ...
    'metrics', artifact(root, 'Q2_METRICS.mat'), ...
    'parent_masks', artifact(root, 'Q2_PARENT_MASKS.mat'));
artifacts.parent_masks.mask_set_sha256 = identity.mask_set_sha256;
q2 = struct('schema_version', 'rebuilt_initial_mex_q2_result_v2', ...
    'status', 'passed', 'passed', true, 'blockers', {{}}, ...
    'stage', 'cycle1_metric_gate', ...
    'runtime_lock_sha256', runtimeHash, ...
    'runtime_initial_sha256', approvedHash(), 'source_commit', sourceCommit, ...
    'q2_input_lock_sha256', q2LockHash, 'parent_lock_sha256', parentHash, ...
    'parent_cycle1_sha256', identity.parent_cycle1_sha256, ...
    'parent_reference_id', 'fixture_parent', ...
    'mesh_ordering_sha256', meshHash, 'replay_source_mesh_sha256', meshHash, ...
    'parent_vtk_mesh_sha256', identity.parent_vtk_mesh_sha256, ...
    'mask_set_sha256', identity.mask_set_sha256, ...
    'q2_terminal_status', 'q2_cycle1_diagnostic_complete', ...
    'family_terminal_eligible', false, 'metrics', metrics, ...
    'artifacts', artifacts);
writeJson(fullfile(root, 'Q2', 'Q2_RESULT.json'), q2);
fixture = struct('root', root, 'runtimeLock', runtimeLock, ...
    'runtimeRoot', runtimeRoot, 'sourceRoot', sourceRoot, 'q2Lock', q2Lock, ...
    'parentLock', parentLock, 'sourceCommit', sourceCommit, ...
    'meshHash', meshHash);
end

function metrics = q1Metrics()
indices = {'i_row','j_col','i_row_sig','j_col_sig', ...
    'i_row_eps','j_col_eps','i_row_pf','j_col_pf'};
indexOutputs = repmat(struct('name', '', 'exact', true), 8, 1);
for k = 1:8, indexOutputs(k).name = indices{k}; end
names = {'M_vector','eps_vector','sig0_vector'};
numerical = repmat(struct('name', '', 'reference_l2', 1, ...
    'relative_l2', 0, 'max_absolute', 0, 'identically_zero', false, ...
    'threshold', 1e-12), 3, 1);
for k = 1:3, numerical(k).name = names{k}; end
metrics = orderfields(struct('schema_version', ...
    'rebuilt_initial_mex_q1_metrics_v1', 'passed', true, ...
    'output_shapes', struct('K_vect',[1 1],'i_row',[1 1], ...
    'j_col',[1 1],'M_vector',[1 1],'i_row_sig',[1 1], ...
    'j_col_sig',[1 1],'eps_vector',[1 1],'i_row_eps',[1 1], ...
    'j_col_eps',[1 1],'sig0_vector',[1 1], ...
    'i_row_pf',[1 1],'j_col_pf',[1 1]), ...
    'index_outputs', indexOutputs, ...
    'stiffness', struct('shape',[2 2], 'reference_frobenius',1, ...
    'relative_frobenius',0, 'max_absolute',0, 'threshold',1e-12), ...
    'numerical_outputs', numerical, ...
    'probe', struct('name','deterministic_internal_force_probe', ...
    'top_y_value',0.03,'reference_l2',1,'relative_l2',0, ...
    'max_absolute',0,'threshold',1e-12)));
end

function metrics = q2Metrics(identity)
regular = struct('log10_mae',0,'log10_rmse',0,'log10_correlation',1, ...
    'support_count',2,'outside_absolute_mae',0, ...
    'outside_absolute_max_error',0,'absolute_only',false,'passed',true);
zeroVariance = regular;
zeroVariance.log10_correlation = 'not_applicable_zero_variance';
damage = struct('mae',0,'rmse',0,'correlation',1,'support_count',2, ...
    'outside_absolute_mae',0,'outside_absolute_max_error',0, ...
    'absolute_only',false,'passed',true);
fatigue = struct('absolute_mae',0,'absolute_max_error',0, ...
    'correlation','not_applicable_zero_variance','support_count',2, ...
    'outside_absolute_mae',0,'outside_absolute_max_error',0, ...
    'absolute_only',true,'passed',true);
fields = struct('damage',damage,'history',zeroVariance, ...
    'fatigue_degradation',fatigue,'raw',regular, ...
    'damage_degradation',regular,'active',regular);
metrics = orderfields(struct('schema_version', ...
    'rebuilt_initial_mex_q2_metrics_v1','passed',true, ...
    'parent_cycle1_sha256',identity.parent_cycle1_sha256, ...
    'mask_set_sha256',identity.mask_set_sha256, ...
    'log_transform','log10(max(q,0)+1e-14)','fields',fields));
end

function state = q2State(identity)
state = identity;
state.schema_version = 'rebuilt_initial_mex_q2_cycle1_state_v1';
state.cycle = 1; state.peak_substep_ordinal = 4;
state.element_ids = int64([1;2]); state.connectivity = [1 2 3 4;1 2 3 4];
state.d_elem = [0.1;0.2]; state.alpha_bar_elem = [0.2;0.3];
state.f_alpha_elem = ones(2,1); state.psi_raw_elem = [0.3;0.4];
state.g_elem = [0.8;0.7]; state.psi_active_elem = [0.24;0.28];
state.active_semantics = 'mean_gp(g_gp.*psi_raw_gp)';
state.element_ordering = 'native_mesh_element_row_order_1_based_v1';
state.family_terminal_eligible = false;
end

function terminal = q2Terminal(identity)
terminal = identity;
terminal.schema_version = 'rebuilt_initial_mex_q2_cycle1_terminal_v1';
terminal.status = 'q2_cycle1_diagnostic_complete'; terminal.cycle = 1;
terminal.peak_substep_ordinal = 4; terminal.rebuild_sys_after_recovery = false;
terminal.family_terminal_eligible = false;
terminal.state_file = 'Q2_CYCLE1_STATE.mat';
end

function masks = q2Masks(identity)
masks = identity;
masks.schema_version = 'rebuilt_initial_mex_q2_parent_masks_v2';
masks.num_elem = 2; masks.log_floor = 1e-14;
masks.negative_tolerance = 1e-14;
masks.outside_absolute_mae_limit = 1e-12;
masks.outside_absolute_max_error_limit = 1e-10;
masks.variance_tolerance = 1e-14;
end

function value = artifact(root, name)
path = fullfile(root, 'Q2', name);
details = dir(path);
value = struct('relative_path', name, 'sha256', fileHash(path), ...
    'bytes', details.bytes);
end

function rehashQ1(fixture, metrics)
metricsPath = fullfile(fixture.root, 'Q1', 'Q1_METRICS.mat');
resultPath = fullfile(fixture.root, 'Q1', 'Q1_RESULT.json');
receiptPath = fullfile(fixture.root, 'Q1', 'Q1_RECEIPT.json');
result = jsondecode(fileread(resultPath));
result.metrics_sha256 = fileHash(metricsPath); writeJsonReplace(resultPath,result);
receipt = jsondecode(fileread(receiptPath));
receipt.metrics_sha256 = result.metrics_sha256; receipt.metrics = metrics;
receipt.result_sha256 = fileHash(resultPath); writeJsonReplace(receiptPath,receipt);
end

function rehashQ2Artifact(fixture, field, path)
q2Path = fullfile(fixture.root, 'Q2', 'Q2_RESULT.json');
q2 = jsondecode(fileread(q2Path)); details = dir(path);
q2.artifacts.(field).sha256 = fileHash(path);
q2.artifacts.(field).bytes = details.bytes;
writeJsonReplace(q2Path, q2);
end

function writeJsonReplace(path, value)
if isfile(path), delete(path); end
writeJson(path, value);
end

function writeJson(path, value)
writeBytes(path, unicode2native([jsonencode(orderfields(value)), newline], 'UTF-8'));
end

function writeBytes(path, bytes)
fileId = fopen(path, 'wb'); cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, bytes, 'uint8');
end

function digest = fileHash(path)
fileId = fopen(path, 'rb'); cleanup = onCleanup(@() fclose(fileId));
md = java.security.MessageDigest.getInstance('SHA-256');
md.update(fread(fileId, Inf, '*uint8'));
digest = lower(reshape(dec2hex(typecast(md.digest(), 'uint8'), 2).', 1, []));
end

function value = approvedHash()
value = 'ce20943282a89407eb7a998fc06a40c2cce4e5167555835fa28427346fb630db';
end
