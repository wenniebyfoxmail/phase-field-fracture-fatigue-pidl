function tests = rebuiltMexQualificationReceiptTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
handoff = fileparts(fileparts(mfilename('fullpath')));
oldPath = path;
addpath(handoff);
testCase.addTeardown(@() path(oldPath));
end

function testWellFormedControlledArtifactsProduceBoundReceipt(testCase)
fixture = qualificationFixture(testCase);
receipt = validateFixture(fixture);
verifyTrue(testCase, receipt.passed);
verifyEqual(testCase, receipt.authorization_scope, ...
    'test_only_non_authorizing');
verifyFalse(testCase, isfile(fullfile(fixture.root, ...
    'FAMILY_QUALIFICATION_RECEIPT.json')));
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

function testSchemaCorrectSyntheticLockCannotAuthorizeProduction(testCase)
fixture = qualificationFixture(testCase);
verifyTrue(testCase, isfile(fixture.evidenceLock));
verifyError(testCase, @() validate_qualification_receipts(fixture.root, ...
    fixture.runtimeLock, fixture.runtimeRoot, fixture.sourceRoot, ...
    fixture.q2Lock, fixture.parentLock, fixture.parentRoot, ''), ...
    'rebuiltMexQualification:EvidenceLockUnsealed');
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
resealEvidenceLock(fixture);
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:InvalidMatArtifact');
end

function testRejectsChangedStateEvenWhenArtifactsAndLockAreRehashed(testCase)
fixture = qualificationFixture(testCase);
statePath = fullfile(fixture.root, 'Q2', 'Q2_CYCLE1_STATE.mat');
state = load(statePath);
state.d_elem(1) = state.d_elem(1) + 0.01;
save(statePath, '-struct', 'state', '-v7.3');
rehashQ2Artifact(fixture, 'state', statePath);
resealEvidenceLock(fixture);
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:MetricRecomputationMismatch');
end

function testRejectsRehashedQ2MetricsThatDifferFromRecomputation(testCase)
fixture = qualificationFixture(testCase);
metricsPath = fullfile(fixture.root, 'Q2', 'Q2_METRICS.mat');
loaded = load(metricsPath, 'metrics');
loaded.metrics.fields.damage.mae = 1e-4;
save(metricsPath, '-struct', 'loaded', '-v7.3');
q2Path = fullfile(fixture.root, 'Q2', 'Q2_RESULT.json');
q2 = jsondecode(fileread(q2Path)); q2.metrics = loaded.metrics;
details = dir(metricsPath);
q2.artifacts.metrics.sha256 = fileHash(metricsPath);
q2.artifacts.metrics.bytes = details.bytes;
writeJsonReplace(q2Path, q2); resealEvidenceLock(fixture);
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:MetricRecomputationMismatch');
end

function testRejectsRehashedQ1MetricsThatDifferFromComparator(testCase)
fixture = qualificationFixture(testCase);
metricsPath = fullfile(fixture.root, 'Q1', 'Q1_METRICS.mat');
loaded = load(metricsPath, 'metrics');
loaded.metrics.probe.relative_l2 = 5e-13;
save(metricsPath, '-struct', 'loaded', '-v7.3');
rehashQ1(fixture, loaded.metrics); resealEvidenceLock(fixture);
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:MetricRecomputationMismatch');
end

function testRejectsQ1ThresholdOrEmbeddedMetricMismatch(testCase)
fixture = qualificationFixture(testCase);
metricsPath = fullfile(fixture.root, 'Q1', 'Q1_METRICS.mat');
loaded = load(metricsPath, 'metrics');
loaded.metrics.probe.threshold = 1e-6;
save(metricsPath, '-struct', 'loaded', '-v7.3');
rehashQ1(fixture, loaded.metrics);
resealEvidenceLock(fixture);
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:MetricContractMismatch');

fixture = qualificationFixture(testCase);
q2Path = fullfile(fixture.root, 'Q2', 'Q2_RESULT.json');
q2 = jsondecode(fileread(q2Path));
q2.metrics.fields.active.passed = false;
writeJsonReplace(q2Path, q2);
resealEvidenceLock(fixture);
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:MetricContractMismatch');
end

function testMissingFailedAndBlockedReceiptsFailClosed(testCase)
fixture = qualificationFixture(testCase);
delete(fullfile(fixture.root, 'Q1', 'Q1_RECEIPT.json'));
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:ArtifactMismatch');

fixture = qualificationFixture(testCase);
q2Path = fullfile(fixture.root, 'Q2', 'Q2_RESULT.json');
q2 = jsondecode(fileread(q2Path));
q2.status = 'blocked'; q2.passed = false;
q2.blockers = {'blocked_missing_parent_active_field'};
writeJsonReplace(q2Path, q2);
resealEvidenceLock(fixture);
verifyError(testCase, @() validateFixture(fixture), ...
    'rebuiltMexQualification:Q2Blocked');
end

function testTestOnlyValidatorCannotPublishFamilyReceipt(testCase)
fixture = qualificationFixture(testCase);
outputPath = fullfile(fixture.root, 'FAMILY_QUALIFICATION_RECEIPT.json');
verifyError(testCase, @() validateFixture(fixture, outputPath), ...
    'rebuiltMexQualification:TestOnlyCannotPublish');
verifyFalse(testCase, isfile(outputPath));
end

function receipt = validateFixture(fixture, outputPath)
arguments
    fixture
    outputPath = ''
end
context = struct('evidence_lock_path', fixture.evidenceLock, ...
    'evidence_lock_sha256', fileHash(fixture.evidenceLock), ...
    'parent_receipt', fixture.parentReceipt, ...
    'q1_recomputed_metrics', fixture.q1RecomputedMetrics);
receipt = validate_qualification_receipts_test_only(fixture.root, ...
    fixture.runtimeLock, fixture.runtimeRoot, fixture.sourceRoot, ...
    fixture.q2Lock, fixture.parentLock, fixture.parentRoot, context);
if ~isempty(outputPath)
    error('rebuiltMexQualification:TestOnlyCannotPublish', ...
        'Test-only qualification cannot publish an authorizing receipt.');
end
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
    'mesh_ordering_sha256', meshHash, ...
    'replay_source_mesh_sha256', meshHash, ...
    'parent_vtk_mesh_sha256', repmat('6', 1, 64));
parentReceipt = q2ParentReceipt(identity);
mask_artifact = build_q2_parent_masks(parentReceipt);
identity.mask_set_sha256 = mask_artifact.mask_set_sha256;
state = q2State(identity);
save(fullfile(root, 'Q2', 'Q2_CYCLE1_STATE.mat'), '-struct', 'state', '-v7.3');
terminal = q2Terminal(identity);
writeJson(fullfile(root, 'Q2', 'Q2_CYCLE1_TERMINAL.json'), terminal);
candidate = q2Candidate(parentReceipt, state);
metrics = compare_q2_cycle1_fields(parentReceipt, candidate, mask_artifact);
save(fullfile(root, 'Q2', 'Q2_METRICS.mat'), 'metrics', '-v7.3');
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
evidenceLock = fullfile(root, 'QUALIFICATION_EVIDENCE_LOCK.json');
writeJson(evidenceLock, qualificationEvidenceLock(root, identity, ...
    sourceCommit, q1Result.input_sha256));
fixture = struct('root', root, 'runtimeLock', runtimeLock, ...
    'runtimeRoot', runtimeRoot, 'sourceRoot', sourceRoot, 'q2Lock', q2Lock, ...
    'parentLock', parentLock, 'sourceCommit', sourceCommit, ...
    'parentRoot', root, 'meshHash', meshHash, ...
    'evidenceLock', evidenceLock, 'parentReceipt', parentReceipt, ...
    'q1RecomputedMetrics', q1Metrics());
end

function parent = q2ParentReceipt(identity)
values = struct('damage',[0.1;0.2], 'history',[0.2;0.3], ...
    'fatigue_degradation',ones(2,1), 'raw',[0.3;0.4], ...
    'damage_degradation',[0.8;0.7], 'active',[0.24;0.28]);
names = fieldnames(values); fields = struct;
for index = 1:numel(names)
    fields.(names{index}) = struct('source', ['fixture:', names{index}], ...
        'values', values.(names{index}));
end
parent = struct('schema_version', ...
    'rebuilt_initial_mex_q2_parent_receipt_v2', 'status', 'ready', ...
    'blockers', {{}}, 'q2_input_lock_sha256', ...
    identity.q2_input_lock_sha256, 'parent_lock_sha256', ...
    identity.parent_lock_sha256, 'parent_cycle1_sha256', ...
    identity.parent_cycle1_sha256, 'parent_reference_id', ...
    'fixture_parent', 'mesh_ordering_sha256', ...
    identity.replay_source_mesh_sha256, 'replay_source_mesh_sha256', ...
    identity.replay_source_mesh_sha256, ...
    'replay_source_mesh_sha256_semantics', 'fixture_mesh_v1', ...
    'parent_vtk_mesh_sha256', identity.parent_vtk_mesh_sha256, ...
    'parent_vtk_mesh_sha256_semantics', 'fixture_vtk_v1', ...
    'num_elem', 2, 'fields', fields);
end

function candidate = q2Candidate(parent, state)
fields = struct( ...
    'damage', struct('source','native:d_elem','values',state.d_elem), ...
    'history', struct('source','native:alpha_bar_elem', ...
    'values',state.alpha_bar_elem), ...
    'fatigue_degradation', struct('source','native:f_alpha_elem', ...
    'values',state.f_alpha_elem), ...
    'raw', struct('source','native:psi_raw_elem','values',state.psi_raw_elem), ...
    'damage_degradation', struct('source','sealed_gp:mean_gp(g_gp)', ...
    'values',state.g_elem), ...
    'active', struct('source','sealed_gp:mean_gp(g_gp.*psi_raw_gp)', ...
    'values',state.psi_active_elem));
candidate = struct('parent_cycle1_sha256',parent.parent_cycle1_sha256, ...
    'parent_reference_id',parent.parent_reference_id, ...
    'mesh_ordering_sha256',state.mesh_ordering_sha256, ...
    'num_elem',parent.num_elem,'fields',fields);
end

function lock = qualificationEvidenceLock(root, identity, sourceCommit, inputHash)
relative = {'Q1/Q1_METRICS.mat','Q1/Q1_RESULT.json','Q1/Q1_RECEIPT.json', ...
    'Q2/Q2_CYCLE1_STATE.mat','Q2/Q2_CYCLE1_TERMINAL.json', ...
    'Q2/Q2_METRICS.mat','Q2/Q2_PARENT_MASKS.mat','Q2/Q2_RESULT.json'};
names = {'q1_metrics','q1_result','q1_receipt','q2_state','q2_terminal', ...
    'q2_metrics','q2_parent_masks','q2_result'};
artifacts = struct;
for index = 1:numel(names)
    artifacts.(names{index}) = lockArtifact(root, relative{index});
end
identities = identity;
identities.source_commit = sourceCommit;
identities.q1_input_sha256 = inputHash;
lock = orderfields(struct('schema_version', ...
    'rebuilt_mex_qualification_evidence_lock_v1', ...
    'sealed_after_real_task6_qualification', true, ...
    'identities', orderfields(identities), ...
    'artifacts', orderfields(artifacts)));
end

function value = lockArtifact(root, relativePath)
path = fullfile(root, strrep(relativePath, '/', filesep)); details = dir(path);
value = orderfields(struct('relative_path',relativePath, ...
    'sha256',fileHash(path),'bytes',details.bytes));
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

function resealEvidenceLock(fixture)
q2 = jsondecode(fileread(fullfile(fixture.root, 'Q2', 'Q2_RESULT.json')));
q1 = jsondecode(fileread(fullfile(fixture.root, 'Q1', 'Q1_RESULT.json')));
identity = struct('runtime_lock_sha256',q2.runtime_lock_sha256, ...
    'runtime_initial_sha256',q2.runtime_initial_sha256, ...
    'q2_input_lock_sha256',q2.q2_input_lock_sha256, ...
    'parent_lock_sha256',q2.parent_lock_sha256, ...
    'parent_cycle1_sha256',q2.parent_cycle1_sha256, ...
    'mask_set_sha256',q2.mask_set_sha256, ...
    'mesh_ordering_sha256',q2.mesh_ordering_sha256, ...
    'replay_source_mesh_sha256',q2.replay_source_mesh_sha256, ...
    'parent_vtk_mesh_sha256',q2.parent_vtk_mesh_sha256);
lock = qualificationEvidenceLock(fixture.root, identity, ...
    q2.source_commit, q1.input_sha256);
writeJsonReplace(fixture.evidenceLock, lock);
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
