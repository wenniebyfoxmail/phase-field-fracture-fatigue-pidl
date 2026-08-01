function tests = toyRoadFinalizeTest
tests = functiontests(localfunctions);
end

function setupOnce(testCase)
addpath(handoffDir());
testCase.addTeardown(@() rmpath(handoffDir()));
end

function testFinalizerDeeplyValidatesAndWritesSortedManifest(testCase)
[outputRoot, launchReceipt, dependencies, cleanup] = validPackage(); %#ok<ASGLU>

summary = finalizeFixture(outputRoot, "T2_material_state", ...
    launchReceipt, dependencies);

verifyTrue(testCase, summary.is_valid);
verifyEqual(testCase, summary.state_count, 4);
verifyTrue(testCase, isfile(fullfile(outputRoot, 'PRODUCER_PROVENANCE.json')));
verifyTrue(testCase, isfile(fullfile(outputRoot, 'VALIDATION_SUMMARY.json')));
manifestPath = fullfile(outputRoot, 'SHA256SUMS.txt');
verifyTrue(testCase, isfile(manifestPath));
lines = splitlines(strtrim(fileread(manifestPath)));
paths = extractAfter(lines, 66);
verifyEqual(testCase, paths, sort(paths));
verifyFalse(testCase, any(contains(lines, 'SHA256SUMS.txt')));

verified = finalize_toy_road_package( ...
    outputRoot, "T2_material_state", struct(), "verify_manifest");
verifyEqual(testCase, verified.file_count, numel(lines));
end

function testFinalizerRejectsIncompleteRun(testCase)
[outputRoot, launchReceipt, dependencies, cleanup] = ...
    validPackage('run_complete', false); %#ok<ASGLU>
verifyError(testCase, @() finalizeFixture( ...
    outputRoot, "T2_material_state", launchReceipt, dependencies), ...
    'toyRoad:PackageValidationFailed');
verifyNoFinalOutputs(testCase, outputRoot);
end

function testFinalizerRejectsNonconsecutiveStates(testCase)
[outputRoot, launchReceipt, dependencies, cleanup] = validPackage(); %#ok<ASGLU>
delete(fullfile(outputRoot, 'states', 'cycle_0002.mat'));
verifyError(testCase, @() finalizeFixture( ...
    outputRoot, "T2_material_state", launchReceipt, dependencies), ...
    'toyRoad:PackageValidationFailed');
verifyNoFinalOutputs(testCase, outputRoot);
end

function testFinalizerRejectsBadEventMetadata(testCase)
[outputRoot, launchReceipt, dependencies, cleanup] = ...
    validPackage('bad_event', true); %#ok<ASGLU>
verifyError(testCase, @() finalizeFixture( ...
    outputRoot, "T2_material_state", launchReceipt, dependencies), ...
    'toyRoad:PackageValidationFailed');
verifyNoFinalOutputs(testCase, outputRoot);
end

function testFinalizerRejectsWrongMeshHash(testCase)
[outputRoot, launchReceipt, dependencies, cleanup] = validPackage(); %#ok<ASGLU>
meshPath = fullfile(outputRoot, 'mesh_geometry.mat');
mesh = load(meshPath);
mesh.mesh_sha256 = "wrong";
delete(meshPath);
save(meshPath, '-struct', 'mesh', '-v7.3');
verifyError(testCase, @() finalizeFixture( ...
    outputRoot, "T2_material_state", launchReceipt, dependencies), ...
    'toyRoad:PackageValidationFailed');
verifyNoFinalOutputs(testCase, outputRoot);
end

function testFinalizerRejectsExtraAndMissingArtifacts(testCase)
[extraRoot, extraReceipt, extraDependencies, extraCleanup] = validPackage(); %#ok<ASGLU>
writeBytes(fullfile(extraRoot, 'unexpected.bin'), uint8(1));
verifyError(testCase, @() finalizeFixture( ...
    extraRoot, "T2_material_state", extraReceipt, extraDependencies), ...
    'toyRoad:PackageValidationFailed');

[missingRoot, missingReceipt, missingDependencies, missingCleanup] = validPackage(); %#ok<ASGLU>
delete(fullfile(missingRoot, 'state0_analysis.mat'));
verifyError(testCase, @() finalizeFixture( ...
    missingRoot, "T2_material_state", missingReceipt, missingDependencies), ...
    'toyRoad:PackageValidationFailed');

[directoryRoot, directoryReceipt, directoryDependencies, directoryCleanup] = ...
    validPackage(); %#ok<ASGLU>
mkdir(fullfile(directoryRoot, 'unexpected-empty-directory'));
verifyError(testCase, @() finalizeFixture( ...
    directoryRoot, "T2_material_state", directoryReceipt, directoryDependencies), ...
    'toyRoad:PackageValidationFailed');
verifyNoFinalOutputs(testCase, directoryRoot);
end

function testManifestVerificationRejectsTamperAndExtras(testCase)
[outputRoot, launchReceipt, dependencies, cleanup] = validPackage(); %#ok<ASGLU>
finalizeFixture(outputRoot, "T2_material_state", launchReceipt, dependencies);

runPath = fullfile(outputRoot, 'RUN_RESULT.json');
fileId = fopen(runPath, 'ab');
fileCleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, uint8(' '), 'uint8');
clear fileCleanup
verifyError(testCase, @() finalize_toy_road_package( ...
    outputRoot, "T2_material_state", struct(), "verify_manifest"), ...
    'toyRoad:ManifestVerificationFailed');

[extraRoot, extraReceipt, extraDependencies, extraCleanup] = validPackage(); %#ok<ASGLU>
finalizeFixture(extraRoot, "T2_material_state", extraReceipt, extraDependencies);
writeBytes(fullfile(extraRoot, 'late-extra.bin'), uint8(2));
verifyError(testCase, @() finalize_toy_road_package( ...
    extraRoot, "T2_material_state", struct(), "verify_manifest"), ...
    'toyRoad:ManifestVerificationFailed');
end

function testFinalizerAcceptsTask5WindowsCsvLineEndings(testCase)
[outputRoot, launchReceipt, dependencies, cleanup] = validPackage(); %#ok<ASGLU>
indexPath = fullfile(outputRoot, 'cycle_index.csv');
text = strrep(fileread(indexPath), newline, sprintf('\r\n'));
writeBytes(indexPath, unicode2native(text, 'UTF-8'));

summary = finalizeFixture( ...
    outputRoot, "T2_material_state", launchReceipt, dependencies);

verifyTrue(testCase, summary.is_valid);
end

function testFinalizerRejectsNonBooleanEventHit(testCase)
[outputRoot, launchReceipt, dependencies, cleanup] = validPackage(); %#ok<ASGLU>
indexPath = fullfile(outputRoot, 'cycle_index.csv');
text = fileread(indexPath);
text = regexprep(text, ',1,1,', ',2,1,', 'once');
writeBytes(indexPath, unicode2native(text, 'UTF-8'));

verifyError(testCase, @() finalizeFixture( ...
    outputRoot, "T2_material_state", launchReceipt, dependencies), ...
    'toyRoad:PackageValidationFailed');
verifyNoFinalOutputs(testCase, outputRoot);
end

function testFinalizerRejectsMalformedProvenanceHashReceipt(testCase)
[outputRoot, launchReceipt, dependencies, cleanup] = validPackage(); %#ok<ASGLU>
receipt = jsondecode(fileread(launchReceipt));
receipt.runtime_hashes(1).sha256 = 'not-a-sha256';
replaceJson(launchReceipt, receipt);

verifyError(testCase, @() finalizeFixture( ...
    outputRoot, "T2_material_state", launchReceipt, dependencies), ...
    'toyRoad:PackageValidationFailed');
verifyNoFinalOutputs(testCase, outputRoot);
end

function testFinalizerRejectsLockedParentMeshDimensionAndIdentityMutations(testCase)
mutations = {@removeParentNode, @mutateParentCoordinate, @mutateConnectivity};
for index = 1:numel(mutations)
    [outputRoot, launchReceipt, dependencies, cleanup] = validPackage(); %#ok<ASGLU>
    meshPath = fullfile(outputRoot, 'mesh_geometry.mat');
    mesh = load(meshPath);
    mesh = mutations{index}(mesh);
    replaceMat(meshPath, mesh);
    verifyError(testCase, @() finalizeFixture( ...
        outputRoot, "T2_material_state", launchReceipt, dependencies), ...
        'toyRoad:PackageValidationFailed');
    verifyNoFinalOutputs(testCase, outputRoot);
    clear cleanup
end
end

function testFinalizerRejectsT1MapMutationAfterParentIdentity(testCase)
[outputRoot, launchReceipt, dependencies, cleanup] = ...
    validPackage('case_id', "T1_initial_defect"); %#ok<ASGLU>
meshPath = fullfile(outputRoot, 'mesh_geometry.mat');
mesh = load(meshPath);
mesh.node_coords(1, 1) = mesh.node_coords(1, 1) + 1e-6;
mesh.mesh_sha256 = toy_road_mesh_sha256(mesh.node_coords, mesh.connectivity);
replaceMat(meshPath, mesh);

verifyError(testCase, @() finalizeFixture( ...
    outputRoot, "T1_initial_defect", launchReceipt, dependencies), ...
    'toyRoad:PackageValidationFailed');
verifyNoFinalOutputs(testCase, outputRoot);
end

function testFinalizerRejectsMeshAndStateQuadratureMismatch(testCase)
[meshRoot, meshReceipt, meshDependencies, meshCleanup] = validPackage(); %#ok<ASGLU>
meshPath = fullfile(meshRoot, 'mesh_geometry.mat');
mesh = load(meshPath);
mesh.quadrature_points(1, 1) = mesh.quadrature_points(1, 1) + 1e-6;
replaceMat(meshPath, mesh);
verifyError(testCase, @() finalizeFixture( ...
    meshRoot, "T2_material_state", meshReceipt, meshDependencies), ...
    'toyRoad:PackageValidationFailed');

[stateRoot, stateReceipt, stateDependencies, stateCleanup] = validPackage(); %#ok<ASGLU>
statePath = fullfile(stateRoot, 'states', 'cycle_0001.mat');
state = load(statePath);
state.quadrature_weights = 2 * state.quadrature_weights;
replaceMat(statePath, state);
verifyError(testCase, @() finalizeFixture( ...
    stateRoot, "T2_material_state", stateReceipt, stateDependencies), ...
    'toyRoad:PackageValidationFailed');
end

function testFinalizerRejectsSwappedDuplicateAndCaseCollidingReceiptPaths(testCase)
[swapRoot, swapReceipt, swapDependencies, swapCleanup] = validPackage(); %#ok<ASGLU>
receipt = jsondecode(fileread(swapReceipt));
paths = {receipt.griphfith_source_hashes(1:2).path};
receipt.griphfith_source_hashes(1).path = paths{2};
receipt.griphfith_source_hashes(2).path = paths{1};
replaceJson(swapReceipt, receipt);
verifyError(testCase, @() finalizeFixture( ...
    swapRoot, "T2_material_state", swapReceipt, swapDependencies), ...
    'toyRoad:PackageValidationFailed');

[duplicateRoot, duplicateReceipt, duplicateDependencies, duplicateCleanup] = ...
    validPackage(); %#ok<ASGLU>
receipt = jsondecode(fileread(duplicateReceipt));
receipt.parent_source_hashes(end + 1) = receipt.parent_source_hashes(1);
replaceJson(duplicateReceipt, receipt);
verifyError(testCase, @() finalizeFixture( ...
    duplicateRoot, "T2_material_state", duplicateReceipt, duplicateDependencies), ...
    'toyRoad:PackageValidationFailed');

[caseRoot, caseReceipt, caseDependencies, caseCleanup] = validPackage(); %#ok<ASGLU>
receipt = jsondecode(fileread(caseReceipt));
collision = receipt.runtime_hashes(1);
collision.path = upper(collision.path);
receipt.runtime_hashes(end + 1) = collision;
replaceJson(caseReceipt, receipt);
verifyError(testCase, @() finalizeFixture( ...
    caseRoot, "T2_material_state", caseReceipt, caseDependencies), ...
    'toyRoad:PackageValidationFailed');
end

function testFinalizerRejectsSourceCommitMismatch(testCase)
[outputRoot, launchReceipt, dependencies, cleanup] = validPackage(); %#ok<ASGLU>
snapshotPath = fullfile(outputRoot, 'INPUT_SNAPSHOT.json');
snapshot = jsondecode(fileread(snapshotPath));
snapshot.source_commit = repmat('b', 1, 40);
replaceJson(snapshotPath, snapshot);

verifyError(testCase, @() finalizeFixture( ...
    outputRoot, "T2_material_state", launchReceipt, dependencies), ...
    'toyRoad:PackageValidationFailed');
verifyNoFinalOutputs(testCase, outputRoot);
end

function testFinalizerRejectsPreexistingFinalOutputs(testCase)
names = ["PRODUCER_PROVENANCE.json" "VALIDATION_SUMMARY.json" "SHA256SUMS.txt"];
for index = 1:numel(names)
    [outputRoot, launchReceipt, dependencies, cleanup] = validPackage(); %#ok<ASGLU>
    writeBytes(fullfile(outputRoot, names(index)), uint8(1));
    verifyError(testCase, @() finalizeFixture( ...
        outputRoot, "T2_material_state", launchReceipt, dependencies), ...
        'toyRoad:PackageValidationFailed');
    clear cleanup
end
end

function testFinalizerRejectsReparsePointStateDirectory(testCase)
[outputRoot, launchReceipt, dependencies, cleanup] = validPackage(); %#ok<ASGLU>
realStates = fullfile(fileparts(outputRoot), [char(java.util.UUID.randomUUID) '-states']);
movefile(fullfile(outputRoot, 'states'), realStates);
statesPath = fullfile(outputRoot, 'states');
[status, message] = system(sprintf('cmd /c mklink /J "%s" "%s"', ...
    statesPath, realStates));
if status ~= 0
    rmdir(realStates, 's');
    assumeFail(testCase, 'Cannot create a Windows junction fixture: %s', message);
end
junctionCleanup = onCleanup(@() cleanupJunction(statesPath, realStates));

verifyError(testCase, @() finalizeFixture( ...
    outputRoot, "T2_material_state", launchReceipt, dependencies), ...
    'toyRoad:PackageValidationFailed');
verifyNoFinalOutputs(testCase, outputRoot);
end

function [outputRoot, launchReceipt, dependencies, cleanup] = validPackage(varargin)
options = struct('run_complete', true, 'bad_event', false, ...
    'case_id', "T2_material_state");
for index = 1:2:numel(varargin)
    options.(varargin{index}) = varargin{index + 1};
end
outputRoot = tempname;
mkdir(outputRoot);
cleanup = onCleanup(@() rmdir(outputRoot, 's'));

cfg = build_toy_road_case_config(options.case_id, handoffDir());
cfgSnapshot = rmfield(cfg, 'umax_for_cycle');
sourceCommit = currentSourceCommit();
lockPath = fullfile(handoffDir(), sprintf('%s_INPUT_LOCK.json', ...
    extractBefore(options.case_id, 3)));
lockHash = fileSha256(lockPath);
parentLockHash = fileSha256(fullfile(handoffDir(), 'PARENT_LOCK.json'));
snapshot = struct( ...
    'case_configuration', cfgSnapshot, 'case_id', cfg.case_id, ...
    'lock_sha256', lockHash, 'source_commit', sourceCommit, ...
    'fresh_state', true, 'line_search', false, 'cycle_jump', false, ...
    'normalized_substeps', [0.25 0.5 0.75 1.0 0.0]);
write_toy_road_json(fullfile(outputRoot, 'INPUT_SNAPSHOT.json'), snapshot);

[parentCoords, connectivity, quadraturePoints] = meshFixture();
coords = parentCoords;
meshTransferAudit = struct('applied', false);
if options.case_id == "T1_initial_defect"
    [coords, meshTransferAudit] = apply_t1_mesh_transfer( ...
        parentCoords, connectivity, cfg.physics.ell);
    meshTransferAudit.applied = true;
end
x = reshape(coords(connectivity, 1), size(connectivity));
y = reshape(coords(connectivity, 2), size(connectivity));
next = [2:4 1];
mesh = struct( ...
    'node_coords', coords, 'connectivity', connectivity, ...
    'element_material_ids', ones(size(connectivity, 1), 1), ...
    'element_centroids', [mean(x, 2) mean(y, 2)], ...
    'element_areas', 0.5 * abs(sum(x .* y(:, next) - y .* x(:, next), 2)), ...
    'quadrature_points', quadraturePoints, ...
    'quadrature_weights', ones(4, 1), ...
    'mesh_sha256', toy_road_mesh_sha256(coords, connectivity), ...
    'mesh_ordering_id', 'q4_node_connectivity_1_based_v1', ...
    'parent_node_coords', parentCoords, ...
    'mesh_transfer_audit', meshTransferAudit);
publish_toy_road_state_no_clobber(mesh, fullfile(outputRoot, 'mesh_geometry.mat'));

state0History = zeros(size(connectivity, 1), 4, 4);
state0History(:, :, 4) = 1.0;
state0 = struct( ...
    'node_coords', coords, 'connectivity', connectivity, ...
    'displ', zeros(2 * size(coords, 1), 1), ...
    'p_field', zeros(size(coords, 1), 1), ...
    'p_field_old', zeros(size(coords, 1), 1), ...
    'history_vars', state0History, ...
    'recovery_residual', 0.0, ...
    'state_semantics_id', 'fresh_hard_recovered_state0_v1');
publish_toy_road_state_no_clobber(state0, ...
    fullfile(outputRoot, 'state0_analysis.mat'));
initialStateMetadata = struct( ...
    'case_id', cfg.case_id, 'fresh_state', true, 'recovery_residual', 0.0, ...
    'fatigue_alpha_bar_initial', 0.0, ...
    'fatigue_driver_increment_initial', 0.0, ...
    'fatigue_degradation_initial', 1.0);
publish_toy_road_state_no_clobber(struct( ...
    'initial_state_metadata', initialStateMetadata), ...
    fullfile(outputRoot, 'initial_state_metadata.mat'));

eventState = struct();
rows = strings(4, 1);
header = ['cycle,Umax_N,peak_substep_ordinal,raw_step_1_based,' ...
    'branch,phase,file,mesh_sha256,event_hit,first_hit,' ...
    'consecutive_post_hit,confirmed'];
for cycle = 1:4
    state = export_toy_road_peak_state( ...
        peakInput(cycle, coords, connectivity, quadraturePoints, cfg), outputRoot);
    eventState = advance_toy_road_event(eventState, coords, connectivity, ...
        cycle, state.d_node);
    rows(cycle) = sprintf('%d,%.17g,%d,%d,%s,%s,%s,%s,%d,%s,%d,%s', ...
        state.cycle_index.cycle, state.cycle_index.Umax_N, ...
        state.cycle_index.peak_substep_ordinal, ...
        state.cycle_index.raw_step_1_based, state.cycle_index.branch, ...
        state.cycle_index.phase, state.cycle_index.file, ...
        state.cycle_index.mesh_sha256, eventState.hit, ...
        csvInteger(eventState.first_hit), eventState.consecutive_post_hit, ...
        csvInteger(eventState.confirmed));
end
writeText(fullfile(outputRoot, 'cycle_index.csv'), ...
    strjoin([string(header); rows], newline) + newline);

event = struct( ...
    'case_id', cfg.case_id, 'censor_cap', 150, 'confirmation_cycles', 3, ...
    'confirmed', 4, 'cycle_index_file', 'cycle_index.csv', ...
    'event_rule', cfg.event_contract.event_rule, 'first_hit', 1, ...
    'status', 'terminal_metadata', 'terminal_cycle', 4, ...
    'terminal_reason', 'confirmed', ...
    'terminal_state_file', 'states/cycle_0004.mat');
if options.bad_event
    event.confirmed = 3;
end
write_toy_road_json(fullfile(outputRoot, 'EVENT_METADATA.json'), event);
if options.run_complete
    runResult = struct( ...
        'case_id', cfg.case_id, 'complete', true, 'status', 'complete', ...
        'terminal_cycle', 4, 'terminal_reason', 'confirmed', ...
        'terminal_state_file', 'states/cycle_0004.mat');
else
    runResult = struct( ...
        'case_id', cfg.case_id, 'complete', false, 'status', 'failed', ...
        'error_identifier', 'toyRoadTest:Incomplete', ...
        'error_message', 'incomplete fixture');
end
write_toy_road_json(fullfile(outputRoot, 'RUN_RESULT.json'), runResult);

[sourceHashes, gripHashes, runtimeHashes, parentHashes] = ...
    provenanceHashFixtures();
receipt = struct( ...
    'schema_version', 'toy_road_launch_receipt_v1', ...
    'case_id', cfg.case_id, 'source_commit', sourceCommit, ...
    'source_root', sourceRoot(), ...
    'source_manifest_sha256', fileSha256(fullfile(handoffDir(), ...
        'SHA256SUMS.txt')), ...
    'source_hashes', sourceHashes, ...
    'case_lock_sha256', lockHash, ...
    'parent_lock_sha256', parentLockHash, ...
    'griphfith_commit', '355d4c83fefc2db88c32031a2dd2623b3de85c89', ...
    'griphfith_root', 'C:/fixture/griphfith', ...
    'griphfith_source_hashes', gripHashes, ...
    'runtime_hashes', runtimeHashes, ...
    'parent_root', 'C:/fixture/parent', ...
    'parent_source_hashes', parentHashes, ...
    'matlab_exit_code', 0);
launchReceipt = fullfile(outputRoot, 'LAUNCH_RECEIPT.json');
write_toy_road_json(launchReceipt, receipt);
dependencies = struct( ...
    'schema_version', 'toy_road_finalizer_test_dependencies_v1', ...
    'parent_mesh_contract', struct( ...
        'num_nodes', size(parentCoords, 1), ...
        'num_elem', size(connectivity, 1), ...
        'task4_parent_mesh_sha256', ...
            toy_road_mesh_sha256(parentCoords, connectivity), ...
        'quadrature_points', quadraturePoints, ...
        'quadrature_weights', ones(4, 1)));
end

function [source, grip, runtime, parent] = provenanceHashFixtures()
source = sourceManifestRecords();
grip = hashRecords( ...
    ["Scripts/fatigue_fracture/solve_fatigue_fracture.m" ...
     "Sources/+phase_field/+fem/+solver/newton_raphson.m" ...
     "Sources/+phase_field/+fem/+solver/+stag/post_iter_update.m" ...
     "Scripts/brittle_fracture/INPUT_SENS_tensile.m" ...
     "Scripts/fatigue_fracture/init_fatigue_fracture.m" ...
     "Sources/+phase_field/System.m" "Dependencies/meshes/sens_mesh.m"], ...
    ["ae1aa2ff4114c67b166e39b377e08a0d7e28761bb0afa038a388e1eb026e9252" ...
     "20afff63d79eeffd3e6a502b996485e47f64a3b550e19b396cd1bf90120ad76d" ...
     "c9ebc6e87ddc1e6340a6fe077903241656feedea5220488035fb49e3efe55831" ...
     "3cc4ba07cf4b0d5a556457567b719c633e65a3519e1a734ddea00c608c292353" ...
     "96365b7f0b6ecf02cd0e2209765310f29122f503b5c2272240f84fb24ea4098d" ...
     "383fe2566a63652b9287fec3172f4135800e7cb605efcc718e90abf3a54ec5fa" ...
     "dbf13237939425b61cde93b841ae2c24e7fccd291861df5508a34800bb9f4706"]);
runtime = hashRecords( ...
    ["Sources/+phase_field/+mex/+fem/+assembly/+equilibrium/initial.mexw64" ...
     "Sources/+phase_field/+mex/+fem/+assembly/+equilibrium/AMOR.mexw64" ...
     "Sources/+phase_field/+mex/+fem/+assembly/+pf/AT1_HISTORY_FATIGUE.mexw64" ...
     "CHOLMOD/MATLAB/cholmod2.mexw64"], ...
    ["589f3dc793694ea2916fbb6a21dd030bc4bc04ead3d91705e6e882b2d67ca340" ...
     "64abee69f2c441730dc2efa4047ac45ab1d1b40e20c4822ed6e992adcd6b19e7" ...
     "53e8fd0b229817b7c14c52a5b6afaa957692f475057b79b9a9a10195ccb92e60" ...
     "86a2f15543eda1f7223a1733d935d37e9e2f4f2c2d8db3c4adc2c0f675c27329"]);
parent = hashRecords( ...
    ["u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1/initial_state_metadata.mat" ...
     "u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1/state0_analysis.mat" ...
     "u012/pre_run_lock.mat" ...
     "u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1/psi_fields/cycle_0001.mat" ...
     "u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1/psi_fields/cycle_0083.mat" ...
     "u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1/psi_fields/cycle_0086.mat" ...
     "MANIFEST.csv" ...
     "u012/SENS_hard5_u012_eta0_formal_pidl_native_q4_v1/peak_load_c1.vtk"], ...
    ["0e0144b63ca93836c515b489b64ae768058588d7f2431d49c0b95607e35916d8" ...
     "91b8f89ba3a211f08f1b79def5d2d50a973798e988deedc5c5c7e3b64a98ef11" ...
     "6cc63d42e596ef5a96882a02c3b34bb8257ce83b4db97eaf78770c286a701f37" ...
     "72925ac353f766475862858befcc611307e71faa392eb774d7ce5aa8a40d74d9" ...
     "b0e6a7119b1c265197de88938e5f65d4e7069e199e104812463b3b911b4f77e9" ...
     "0ce0426012e0d8aa563650e5d45bdee7214d28502378c420593f4b889a317a13" ...
     "0b0152fd18ecb16496c4c8683ed44573bf4721544d1719ad79675668e4d68580" ...
     "acdc981269024cbb111f7d468c287f2d1ca09f3735131b56aca7fa2fbaec1615"]);
end

function records = hashRecords(paths, hashes)
records = repmat(struct('path', '', 'sha256', ''), numel(paths), 1);
for index = 1:numel(paths)
    records(index).path = char(paths(index));
    records(index).sha256 = char(hashes(index));
end
end

function records = sourceManifestRecords()
lines = splitlines(string(fileread(fullfile(handoffDir(), 'SHA256SUMS.txt'))));
lines(lines == "") = [];
records = repmat(struct('path', '', 'sha256', ''), numel(lines), 1);
for index = 1:numel(lines)
    token = regexp(char(lines(index)), '^([0-9a-f]{64})  (.+)$', ...
        'tokens', 'once');
    records(index).path = token{2};
    records(index).sha256 = token{1};
end
end

function result = finalizeFixture(outputRoot, caseId, launchReceipt, dependencies)
result = finalize_toy_road_package( ...
    outputRoot, caseId, launchReceipt, dependencies);
end

function value = currentSourceCommit()
[status, value] = system(sprintf('git -C "%s" rev-parse HEAD', sourceRoot()));
if status ~= 0
    error('toyRoadTest:GitFailed', 'Cannot resolve source commit.');
end
value = strtrim(value);
end

function value = sourceRoot()
value = strrep(fileparts(fileparts(handoffDir())), '\', '/');
end

function mesh = removeParentNode(mesh)
mesh.parent_node_coords(end, :) = [];
end

function mesh = mutateParentCoordinate(mesh)
mesh.parent_node_coords(1, 1) = mesh.parent_node_coords(1, 1) + 1e-6;
mesh.node_coords = mesh.parent_node_coords;
mesh.mesh_sha256 = toy_road_mesh_sha256(mesh.node_coords, mesh.connectivity);
end

function mesh = mutateConnectivity(mesh)
mesh.connectivity(1, :) = mesh.connectivity(1, [2 3 4 1]);
mesh.mesh_sha256 = toy_road_mesh_sha256(mesh.node_coords, mesh.connectivity);
end

function replaceMat(path, value)
delete(path);
save(path, '-struct', 'value', '-v7.3');
end

function replaceJson(path, value)
delete(path);
write_toy_road_json(path, value);
end

function cleanupJunction(junctionPath, targetPath)
if isfolder(junctionPath)
    system(sprintf('cmd /c rmdir "%s"', junctionPath));
end
if isfolder(targetPath)
    rmdir(targetPath, 's');
end
end

function input = peakInput(cycle, coords, connectivity, quadraturePoints, cfg)
damage = 0.1 * ones(size(coords, 1), 1);
damage(abs(coords(:, 1) - max(coords(:, 1))) <= 1e-12) = 0.96;
history = zeros(size(connectivity, 1), 4, 4);
history(:, :, 2) = 0.01 * cycle;
history(:, :, 4) = 1.0;
u = 2 * coords(:, 1) + 3 * coords(:, 2);
v = -coords(:, 1) + 4 * coords(:, 2);
input = struct( ...
    'displ', [u; v], 'p_field', damage, 'history_vars', history, ...
    'psi_raw_gp', ones(size(connectivity, 1), size(quadraturePoints, 1)), ...
    'node_coords', coords, ...
    'connectivity', connectivity, 'quadrature_points', quadraturePoints, ...
    'quadrature_weights', ones(4, 1), ...
    'reaction_vector', (1:(2 * size(coords, 1)))', ...
    'top_node_ids', find(abs(coords(:, 2) - max(coords(:, 2))) <= 1e-12), ...
    'bottom_node_ids', find(abs(coords(:, 2) - min(coords(:, 2))) <= 1e-12), ...
    'metadata', struct( ...
        'cycle', cycle, 'Umax_N', cfg.umax_for_cycle(cycle), ...
        'peak_substep_ordinal', 4, ...
        'n_substeps', 5, 'raw_step_1_based', 5 * (cycle - 1) + 4, ...
        'branch', 'loading_peak', 'phase', 'cycle_peak', ...
        'state_semantics_id', 'cycle_peak_coherent_v1', ...
        'mesh_ordering_id', 'q4_node_connectivity_1_based_v1', ...
        'state_ordering_id', 'component_blocked_u_then_v_v1'), ...
    'validation_tolerances', struct( ...
        'range', 1e-10, 'active_identity', 1e-12, ...
        'irreversibility', 1e-10));
end

function [coords, connectivity, quadraturePoints] = meshFixture()
x = [-0.5 -0.01 0 0.01 0.5];
y = [-0.01 0 0.01];
[xGrid, yGrid] = meshgrid(x, y);
coords = [xGrid(:) yGrid(:)];
connectivity = zeros((numel(x) - 1) * (numel(y) - 1), 4);
element = 0;
for row = 1:(numel(y) - 1)
    for column = 1:(numel(x) - 1)
        element = element + 1;
        lowerLeft = row + (column - 1) * numel(y);
        lowerRight = row + column * numel(y);
        connectivity(element, :) = [lowerLeft lowerRight ...
            lowerRight + 1 lowerLeft + 1];
    end
end
quadraturePoints = 1 / sqrt(3) * [-1 -1; 1 -1; 1 1; -1 1];
end

function value = csvInteger(number)
if isnan(number)
    value = '';
else
    value = sprintf('%d', number);
end
end

function verifyNoFinalOutputs(testCase, outputRoot)
verifyFalse(testCase, isfile(fullfile(outputRoot, 'PRODUCER_PROVENANCE.json')));
verifyFalse(testCase, isfile(fullfile(outputRoot, 'VALIDATION_SUMMARY.json')));
verifyFalse(testCase, isfile(fullfile(outputRoot, 'SHA256SUMS.txt')));
end

function digest = fileSha256(path)
bytes = readBytes(path);
hasher = java.security.MessageDigest.getInstance('SHA-256');
hasher.update(bytes);
digestBytes = typecast(hasher.digest(), 'uint8');
digest = lower(reshape(dec2hex(digestBytes, 2).', 1, []));
end

function value = readBytes(path)
fileId = fopen(path, 'rb');
if fileId < 0
    error('toyRoadTest:FixtureReadFailed', 'Cannot read fixture: %s', path);
end
cleanup = onCleanup(@() fclose(fileId));
value = fread(fileId, Inf, '*uint8');
end

function writeBytes(path, bytes)
fileId = fopen(path, 'wb');
if fileId < 0
    error('toyRoadTest:FixtureWriteFailed', 'Cannot write fixture: %s', path);
end
cleanup = onCleanup(@() fclose(fileId));
fwrite(fileId, bytes, 'uint8');
end

function writeText(path, text)
writeBytes(path, unicode2native(char(text), 'UTF-8'));
end

function value = handoffDir()
value = fileparts(fileparts(mfilename('fullpath')));
end
